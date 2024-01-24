use anyhow::{Context, Result};
use serde::Deserialize;
use std::convert::TryFrom;
use v_utils::io::ExpandedPath;

#[derive(Deserialize, Clone, Debug)]
pub struct Config {
	pub comparison_offset_h: usize,
	pub spy: Spy,
	pub output: String,
}

#[derive(Deserialize, Clone, Debug)]
pub struct Spy {
	pub alpaca_key: String,
	pub alpaca_secret: String,
}

impl TryFrom<ExpandedPath> for Config {
	type Error = anyhow::Error;

	fn try_from(path: ExpandedPath) -> Result<Self> {
		let config_str = std::fs::read_to_string(&path).with_context(|| format!("Failed to read config file at {:?}", path))?;

		let config: Config = toml::from_str(&config_str)
			.with_context(|| "The config file is not correctly formatted TOML\nand/or\n is missing some of the required fields")?;

		anyhow::ensure!(config.comparison_offset_h <= 24, "comparison limits above a day are not supported");

		Ok(config)
	}
}
