pub mod config;
mod main_line;
mod spy_line;
pub mod utils;
use clap::{Args, Parser, Subcommand};
use config::Config;
use utils::ExpandedPath;

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
	#[command(subcommand)]
	command: Commands,
	#[arg(long, default_value = "~/.config/btc_line.toml")]
	config: ExpandedPath,
}

#[derive(Subcommand)]
enum Commands {
	/// Toggle additional line
	Toggle(NoArgs),
}
#[derive(Args)]
struct NoArgs {}

use std::sync::{Arc, Mutex};

#[tokio::main]
async fn main() {
	let cli = Cli::parse();
	let config = match Config::try_from(cli.config) {
		Ok(cfg) => cfg,
		Err(e) => {
			eprintln!("Error: {}", e);
			std::process::exit(1);
		}
	};

	//TODO!: impl toggle subcommand

	let main_line = Arc::new(Mutex::new(main_line::MainLine::default()));
	let spy_line = Arc::new(Mutex::new(spy_line::SpyLine::default()));

	let _ = tokio::spawn(main_line::MainLine::websocket(main_line.clone(), config.clone()));
	let _ = tokio::spawn(spy_line::SpyLine::websocket(spy_line.clone(), config.clone()));
	let mut cycle = 0;
	loop {
		// start collecting all lines simultaneously
		let main_line_handler = main_line::MainLine::collect(main_line.clone());
		// ...

		// Await everything
		let _ = main_line_handler.await;
		// ...

		// Display everything
		println!("{}", main_line.lock().unwrap().display(&config));

		cycle += 1;
		if cycle == 16 {
			cycle = 1; // rolls to 1, so I can make special cases for 0
		}
		tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
	}
}
