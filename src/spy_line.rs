use crate::config::Config;
use crate::output::Output;
use chrono::{DateTime, Utc};
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::{Arc, Mutex};
use tokio_tungstenite::{connect_async, tungstenite::Message};

#[derive(Default, Debug)]
pub struct SpyLine {
	pub spy_price: Option<f64>,
	//TODO!: have another loop that updates spy_price to None if last timestamp is more than 60s old.
	last_message_timestamp: DateTime<Utc>,
}

impl SpyLine {
	pub fn display(&self, _config: &Config) -> String {
		self.spy_price.map_or_else(|| "".to_string(), |v| format!("{:.2}", v))
	}

	pub async fn websocket(self_arc: Arc<Mutex<Self>>, config: Config, output: Arc<Mutex<Output>>) {
		let alpaca_key = &config.spy.alpaca_key;
		let alpaca_secret = &config.spy.alpaca_secret;
		loop {
			let handle = spy_websocket_listen(self_arc.clone(), output.clone(), alpaca_key, alpaca_secret);

			handle.await;
			{
				let mut lock = self_arc.lock().unwrap();
				lock.spy_price = None;
			}
			eprintln!("Restarting Spy Websocket in 30 seconds...");
			tokio::time::sleep(tokio::time::Duration::from_secs(30)).await;
		}
	}
}

//TODO!!!: handle connection reconnect on spy websocket
async fn spy_websocket_listen(self_arc: Arc<Mutex<SpyLine>>, _output: Arc<Mutex<Output>>, alpaca_key: &str, alpaca_secret: &str) {
	let url = url::Url::parse("wss://stream.data.alpaca.markets/v2/iex").unwrap();
	let (ws_stream, _) = connect_async(url).await.expect("Failed to connect");

	let (mut write, mut read) = ws_stream.split();

	let auth_message = json!({
		"action": "auth",
		"key": alpaca_key.to_owned(),
		"secret": alpaca_secret.to_owned()
	})
	.to_string();

	if let Some(message) = read.next().await {
		let message = message.unwrap();
		println!("Connected Message: {:?}", message);
		assert_eq!(message, Message::Text("[{\"T\":\"success\",\"msg\":\"connected\"}]".to_string()));

		write.send(Message::Text(auth_message)).await.unwrap();
	}

	let listen_message = json!({
		"action":"subscribe",
		"trades":["SPY"]
	})
	.to_string();

	if let Some(message) = read.next().await {
		let message = message.unwrap();
		println!("Authenticated Message: {:?}", message);
		assert_eq!(message, Message::Text("[{\"T\":\"success\",\"msg\":\"authenticated\"}]".to_string()));

		write.send(Message::Text(listen_message)).await.unwrap();
	}

	if let Some(message) = read.next().await {
		let message = message.unwrap();
		println!("Subscription Message: {:?}", message);
		assert_eq!(message, Message::Text("[{\"T\":\"subscription\",\"trades\":[\"SPY\"],\"quotes\":[],\"bars\":[],\"updatedBars\":[],\"dailyBars\":[],\"statuses\":[],\"lulds\":[],\"corrections\":[\"SPY\"],\"cancelErrors\":[\"SPY\"]}]".to_string()));
	}

	let refresh_arc = self_arc.clone();
	tokio::spawn(async move {
		loop {
			if refresh_arc.lock().unwrap().last_message_timestamp < Utc::now() - chrono::Duration::seconds(10 * 60) {
				if refresh_arc.lock().unwrap().spy_price.is_some() {
					refresh_arc.lock().unwrap().spy_price = None;
				}
			}
			tokio::time::sleep(tokio::time::Duration::from_secs(5 * 60)).await;
		}
	});

	while let Some(message) = read.next().await {
		let message = message.unwrap();
		println!("Message: {:?}", &message);

		match message {
			Message::Ping(ref data) if data.is_empty() => {
				println!("We got pinged");
			}
			Message::Text(ref contents) => match serde_json::from_str::<AlpacaTrade>(contents) {
				Ok(alpaca_trade) => {
					println!("LETS GOOOOO: {:?}", alpaca_trade);
					if alpaca_trade.symbol == "SPY" {
						let mut lock = self_arc.lock().unwrap();
						lock.spy_price = Some(alpaca_trade.trade_price);
						lock.last_message_timestamp = Utc::now();
					}
				}
				Err(e) => {
					eprintln!("Text but not a quote: {:?}", e);
				}
			},
			_ => {
				println!("Some Other Message: {:?}", message);
			}
		}
	}
}

#[derive(Serialize, Deserialize, Debug)]
pub struct AlpacaTrade {
	#[serde(rename = "T")]
	pub message_type: String, // Always "t" for trade endpoint
	#[serde(rename = "S")]
	pub symbol: String,
	#[serde(rename = "i")]
	pub trade_id: i32,
	#[serde(rename = "x")]
	pub exchange_code: String,
	#[serde(rename = "p")]
	pub trade_price: f64, // Assuming "number" is a floating point number
	#[serde(rename = "s")]
	pub trade_size: i32,
	#[serde(rename = "c")]
	pub trade_condition: Vec<String>, // Assuming "array" is a vector of strings
	#[serde(rename = "t")]
	pub timestamp: String, // Consider using a more specific type like chrono::DateTime if you need to manipulate dates
	#[serde(rename = "z")]
	pub tape: String,
}
