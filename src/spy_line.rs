use crate::config::Config;
use crate::output::Output;
use chrono::{DateTime, Utc};
use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
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

async fn spy_websocket_listen(self_arc: Arc<Mutex<SpyLine>>, _output: Arc<Mutex<Output>>, alpaca_key: &str, alpaca_secret: &str) {
	//Failed to connect: Http(Response { status: 403, version: HTTP/1.1, headers: {"date": "Sat, 13 Jan 2024 23:34:58 GMT", "content-type": "text/html", "content-length": "146", "connection": "keep-alive", "strict-transport-security": "max-age=15724800; includeSubDomains", "x-request-id": "4c6899bd9766d860988c3728a23a08e2"}, body: Some([60, 104, 116, 109, 108, 62, 13, 10, 60, 104, 101, 97, 100, 62, 60, 116, 105, 116, 108, 101, 62, 52, 48, 51, 32, 70, 111, 114, 98, 105, 100, 100, 101, 110, 60, 47, 116, 105, 116, 108, 101, 62, 60, 47, 104, 101, 97, 100, 62, 13, 10, 60, 98, 111, 100, 121, 62, 13, 10, 60, 99, 101, 110, 116, 101, 114, 62, 60, 104, 49, 62, 52, 48, 51, 32, 70, 111, 114, 98, 105, 100, 100, 101, 110, 60, 47, 104, 49, 62, 60, 47, 99, 101, 110, 116, 101, 114, 62, 13, 10, 60, 104, 114, 62, 60, 99, 101, 110, 116, 101, 114, 62, 110, 103, 105, 110, 120, 60, 47, 99, 101, 110, 116, 101, 114, 62, 13, 10, 60, 47, 98, 111, 100, 121, 62, 13, 10, 60, 47, 104, 116, 109, 108, 62, 13, 10]) })

	let url = url::Url::parse("wss://data.alpaca.markets/stream").unwrap();
	let (ws_stream, _) = connect_async(url).await.expect("Failed to connect");

	let (mut write, mut read) = ws_stream.split();

	let auth_message = json!({
		"action": "authenticate",
		"data": {
			"key_id": alpaca_key.to_owned(),
			"secret_key": alpaca_secret.to_owned()
		}
	})
	.to_string();

	write.send(Message::Text(auth_message)).await.unwrap();

	let listen_message = json!({
		"action": "listen",
		"data": {
			"streams": ["T.SPY"]
		}
	})
	.to_string();

	if let Some(message) = read.next().await {
		let message = message.unwrap();
		println!("Received a message: {:?}", message);

		if let Ok(msg) = message.to_text() {
			let msg: Value = serde_json::from_str(msg).unwrap();
			if msg["stream"] == "authorization" && msg["data"]["status"] == "authorized" {
				// Auth successful, subscribe to channels
				write.send(Message::Text(listen_message)).await.unwrap();
			}
		}
	}

	while let Some(message) = read.next().await {
		let message = message.unwrap();
		if message.is_text() || message.is_binary() {
			println!("Received a message: {:?}", message);
		}
	}
}
