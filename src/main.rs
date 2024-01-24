mod additional_line;
pub mod config;
mod main_line;
pub mod output;
mod spy_line;
pub mod utils;
use clap::{Args, Parser, Subcommand};
use config::Config;
use output::Output;
use std::sync::{Arc, Mutex};
use v_utils::io::ExpandedPath;

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
	/// Start the program
	Start(NoArgs),
	/// Toggle additional line
	Toggle(NoArgs),
}
#[derive(Args)]
struct NoArgs {}

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

	match cli.command {
		Commands::Start(_) => {
			let output = Arc::new(Mutex::new(Output::new(config.clone())));

			let main_line = Arc::new(Mutex::new(main_line::MainLine::default()));
			let spy_line = Arc::new(Mutex::new(spy_line::SpyLine::default()));
			let mut additional_line = additional_line::AdditionalLine::default();

			let _ = tokio::spawn(main_line::MainLine::websocket(main_line.clone(), config.clone(), output.clone()));
			let _ = tokio::spawn(spy_line::SpyLine::websocket(spy_line.clone(), config.clone(), output.clone()));
			let mut cycle = 0;
			loop {
				{
					let main_line_handler = main_line::MainLine::collect(main_line.clone());
					let additional_line_handler = additional_line.collect(&config);

					let _ = main_line_handler.await;
					let _ = additional_line_handler.await;
				}

				{
					let mut output_lock = output.lock().unwrap();
					output_lock.main_line_str = main_line.lock().unwrap().display(&config);
					output_lock.additional_line_str = additional_line.display(&config);
					output_lock.out().unwrap();
				}

				cycle += 1;
				if cycle == 16 {
					cycle = 1; // rolls to 1, so I can make special cases for 0
				}
				tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
			}
		}
		Commands::Toggle(_) => {
			unimplemented!();
		}
	}
}
