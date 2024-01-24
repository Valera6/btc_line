use crate::config::Config;
use anyhow::Result;

#[derive(Debug)]
pub struct Output {
	config: Config,
	pub main_line_str: String,
	pub spy_line_str: String,
	pub additional_line_str: String,
}

impl Output {
	pub fn out(&self) -> Result<()> {
		if self.config.output == "eww".to_owned() {
			std::process::Command::new("sh")
				.arg("-c")
				.arg(format!("eww update btc_line_main_str=\"{}\"", self.main_line_str))
				.status()
				.expect("eww daemon is not running");
			std::process::Command::new("sh")
				.arg("-c")
				.arg(format!("eww update btc_line_spy_str=\"{}\"", self.spy_line_str))
				.status()
				.expect("eww daemon is not running");
			std::process::Command::new("sh")
				.arg("-c")
				.arg(format!("eww update btc_line_additional_str=\"{}\"", self.additional_line_str))
				.status()
				.expect("eww daemon is not running");
		}
		Ok(())
	}

	pub fn new(config: Config) -> Self {
		Self {
			config,
			main_line_str: "".to_string(),
			spy_line_str: "".to_string(),
			additional_line_str: "".to_string(),
		}
	}
}
