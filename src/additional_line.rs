use crate::config::Config;
use crate::utils::NowThen;
use anyhow::{anyhow, Result};
use reqwest;
use serde::Deserialize;

//TODO!: implement tiny graphics
#[derive(Default, Debug)]
pub struct AdditionalLine {
	open_interest_change: Option<NowThen>,
	btc_volume_change: Option<NowThen>,
}

impl AdditionalLine {
	pub fn display(&self, _config: &Config) -> String {
		let oi = self.open_interest_change.as_ref().map_or("None".to_string(), |v| format!("{}", v));
		let v = self.btc_volume_change.as_ref().map_or("None".to_string(), |v| format!("{}", v));
		//TODO!: add labels only if this option is on
		format!("OI:{} V:{}", oi, v)
	}

	pub async fn collect(&mut self, config: &Config) {
		let comparison_offset_h = config.comparison_offset_h;

		let client = reqwest::Client::new();
		let open_interest_change_handler = get_open_interest_change(&client, "BTCUSDT", comparison_offset_h);
		let btc_volume_change_handler = get_btc_volume_change(&client, comparison_offset_h);

		self.open_interest_change = match open_interest_change_handler.await {
			Ok(open_interest_change) => Some(open_interest_change),
			Err(e) => {
				eprintln!("Failed to get Open Interest: {}", e);
				None
			}
		};
		self.btc_volume_change = match btc_volume_change_handler.await {
			Ok(btc_volume_change) => Some(btc_volume_change),
			Err(e) => {
				eprintln!("Failed to get BTC Volume: {}", e);
				None
			}
		};
	}
}

async fn get_open_interest_change(client: &reqwest::Client, symbol: &str, comparison_offset_h: usize) -> Result<NowThen> {
	let url = format!(
		"https://fapi.binance.com/futures/data/openInterestHist?symbol={}&period=5m&limit={}",
		symbol,
		comparison_offset_h * 12 + 1
	);

	let response = client.get(&url).send().await?;
	if response.status().is_success() {
		let json_string = response.text().await?;
		let r: Vec<OpenInterestHist> = serde_json::from_str(&json_string)?;

		let now: f64 = r[0].sumOpenInterestValue.parse()?;
		let then: f64 = r[r.len() - 1].sumOpenInterestValue.parse()?;

		Ok(NowThen { now, then })
	} else {
		Err(anyhow!("Failed to get Open Interest Change: {}", response.status()))
	}
}

async fn get_btc_volume_change(client: &reqwest::Client, comparison_offset_h: usize) -> Result<NowThen> {
	let url = format!(
		"https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=5m&limit={}",
		comparison_offset_h * 12 + 288
	);

	let response = client.get(&url).send().await?;
	if response.status().is_success() {
		let json_string = response.text().await?;
		let r: Vec<Kline> = serde_json::from_str(&json_string)?;

		let split = r.split_at(288);
		let now: f64 = split.0.iter().map(|v| v.quote_asset_volume.parse::<f64>().unwrap()).sum();
		let then: f64 = split.1.iter().map(|v| v.quote_asset_volume.parse::<f64>().unwrap()).sum();

		Ok(NowThen { now, then })
	} else {
		Err(anyhow!("Failed to get BTC Volume: {}", response.status()))
	}
}

#[derive(Deserialize, Debug)]
#[allow(non_snake_case, dead_code)]
struct OpenInterestHist {
	symbol: String,
	sumOpenInterest: String,
	sumOpenInterestValue: String,
	timestamp: i64,
}

#[derive(Deserialize, Debug)]
#[allow(non_snake_case, dead_code)]
struct Kline {
	open_time: i64,
	open: String,
	high: String,
	low: String,
	close: String,
	volume: String,
	close_time: i64,
	quote_asset_volume: String,
	number_of_trades: usize,
	taker_buy_base_asset_volume: String,
	taker_buy_quote_asset_volume: String,
	ignore: String,
}
