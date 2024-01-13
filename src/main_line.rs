use anyhow::{anyhow, Result};
use futures_util::StreamExt;
use reqwest;
use serde_json::Value;
use std::sync::{Arc, Mutex};
use tokio_tungstenite::connect_async;

#[derive(Default, Debug)]
pub struct MainLine {
	pub btcusdt: Option<f32>,
	pub percent_longs: Option<f32>,
}
impl MainLine {
	pub fn display(&self) -> String {
		let btcusdt_display = self.btcusdt.map_or("None".to_string(), |v| format!("{:.0}", v));
		let percent_longs_display = self.percent_longs.map_or("".to_string(), |v| format!("|{:.2}", v));
		format!("{}{}", btcusdt_display, percent_longs_display)
	}
}

pub async fn binance_websocket_listen(main_line: Arc<Mutex<MainLine>>) {
	let address = "wss://fstream.binance.com/ws/btcusdt@markPrice";
	let url = url::Url::parse(address).unwrap();
	let (ws_stream, _) = connect_async(url).await.expect("Failed to connect");
	let (_, read) = ws_stream.split();

	read.for_each(|message| {
		let main_line = main_line.clone(); // Cloning the Arc for each iteration
		async move {
			let data = message.unwrap().into_data();
			match serde_json::from_slice::<Value>(&data) {
				Ok(json) => {
					if let Some(price_str) = json.get("p") {
						let price: f32 = price_str.as_str().unwrap().parse().unwrap();
						let main_line_str: String;
						{
							let mut main_line = main_line.lock().unwrap();
							main_line.btcusdt = Some(price);
							main_line_str = main_line.display();
						}
						println!("{}", main_line_str);
					}
				}
				Err(e) => {
					println!("Failed to parse message as JSON: {}", e);
				}
			}
		}
	})
	.await;
}

impl MainLine {
	pub async fn websocket(self_arc: Arc<Mutex<MainLine>>) {
		loop {
			let handle = binance_websocket_listen(self_arc.clone());

			handle.await;
			{
				let mut lock = self_arc.lock().unwrap();
				lock.btcusdt = None;
			}
			eprintln!("Restarting Binance Websocket in 30 seconds...");
			tokio::time::sleep(tokio::time::Duration::from_secs(30)).await;
		}
	}

	pub async fn collect(self_arc: Arc<Mutex<MainLine>>) {
		let percent_longs_handler = get_percent_longs("BTCUSDT", PercentLongsScope::Global);

		let percent_longs: Option<f32> = match percent_longs_handler.await {
			Ok(percent_longs) => Some(percent_longs as f32),
			Err(e) => {
				eprintln!("Failed to get LSR: {}", e);
				None
			}
		};

		let mut self_lock = self_arc.lock().unwrap();
		self_lock.percent_longs = percent_longs;
	}
}

#[allow(dead_code)]
enum PercentLongsScope {
	Global,
	Top,
}
impl PercentLongsScope {
	fn request_url_insertions_tuple(&self) -> (String, String) {
		match self {
			PercentLongsScope::Global => ("global".to_string(), "Account".to_string()),
			PercentLongsScope::Top => ("top".to_string(), "Position".to_string()),
		}
	}
}
async fn get_percent_longs(symbol_str: &str, type_: PercentLongsScope) -> Result<f64> {
	let mut symbol = symbol_str.to_uppercase();
	if !symbol.contains("USDT") {
		symbol = format!("{}USDT", symbol);
	}

	let (ins_0, ins_1) = type_.request_url_insertions_tuple();

	let url = format!(
		"https://fapi.binance.com/futures/data/{}LongShort{}Ratio?symbol={}&period=5m&limit=1",
		ins_0, ins_1, symbol
	);

	let resp = reqwest::get(&url).await?;
	let json: Vec<Value> = resp.json().await?;
	if let Some(long_account_str) = json.get(0).and_then(|item| item["longAccount"].as_str()) {
		long_account_str
			.parse::<f64>()
			.map_err(|e| anyhow!("Failed to parse 'longAccount' as f64: {}", e))
	} else {
		Err(anyhow!("'longAccount' field missing or not a string in response: {:?}", json))
	}
}