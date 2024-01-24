#[derive(Debug, Clone)]
pub struct NowThen {
	pub now: f64,
	pub then: f64,
}

impl std::fmt::Display for NowThen {
	fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
		let diff = self.now - self.then;

		let precision_of_base_number = match diff {
			_ if diff.abs() * 5.0 > self.now.abs() => 2,
			_ if diff.abs() * 25.0 > self.then.abs() => 1,
			_ => 0,
		};

		let (now_f, now_suffix) = format_large_number(self.now);
		let (diff_f, diff_suffix) = format_large_number(diff);
		let now_suffix = if now_suffix == diff_suffix { "" } else { now_suffix };

		let diff_raw = if diff > 0.0 { format!("+{:.2}", diff_f) } else { format!("{}", diff_f) };
		let diff_str = format!("{}{}", diff_raw, diff_suffix);
		let now_raw = format!("{:.*}", precision_of_base_number, now_f);
		let now_str = format!("{}{}", now_raw, now_suffix);

		write!(f, "{}{}", now_str, diff_str)
	}
}

fn format_large_number(mut n: f64) -> (f64, &'static str) {
	let suffix = match n {
		_ if n > 1_000_000_000_000_000.0 => {
			n /= 1_000_000_000_000_000.0;
			"Q"
		}
		_ if n > 1_000_000_000_000.0 => {
			n /= 1_000_000_000_000.0;
			"T"
		}
		_ if n > 1_000_000_000.0 => {
			n /= 1_000_000_000.0;
			"B"
		}
		_ if n > 1_000_000.0 => {
			n /= 1_000_000.0;
			"M"
		}
		_ if n > 1_000.0 => {
			n /= 1_000.0;
			"K"
		}
		_ => "",
	};
	(n, suffix)
}
