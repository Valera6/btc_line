import websocket, json, threading, time, requests, subprocess, os, sys, tempfile, concurrent.futures, signal, inspect
import tkinter as tk
from PIL import Image, ImageTk
from ValeraLib import load

debug = True
# ==========================================================

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)


additional_width = 120
SPY_width = 52
large_dimensions = (420, 220)
buffer_longs = ""
additional_line = None
large_window = None
settings_button = None
SPY_window = None
MS_window = None
large_resize_ids = []
tempdir = os.path.join(tempfile.gettempdir(), "BTCline")
if not os.path.exists(tempdir):
	os.mkdir(tempdir)
src_dir = os.path.join(script_dir, "src")
os.environ["SRC_DIR"] = src_dir
display = json.load(open(os.path.join(src_dir, "display.json"), "r"))
# <settings>
default_settings = display["default_settings"]


def reset_settings():
	json.dump(default_settings, open(os.path.join(tempdir, "settings.json"), "w"))


if not os.path.exists(os.path.join(tempdir, "settings.json")):
	reset_settings()
settings = json.load(open(os.path.join(tempdir, "settings.json")))
if not settings.keys() == default_settings.keys():
	reset_settings()
for i, s in enumerate(settings):
	if isinstance(s, dict):
		if not s.keys() == default_settings[i].keys():
			reset_settings()
settings = json.load(open(os.path.join(tempdir, "settings.json")))
# </settings>
try:
	keys = json.load(open(os.path.join(script_dir, "my_keys.json"), "r"))
except:
	keys = json.load(open(os.path.join(script_dir, "keys.json"), "r"))
json.dump(keys, open(os.path.join(tempdir, "keys.json"), "w"))


def save_binance_perp_coins_to_tempdir():
	from Valera import bnpc

	bnpc(dump=True)
	binance_perp_coins = json.load(open(os.path.join(src_dir, "binance-perp-pairs.json"), "r"))
	if isinstance(binance_perp_coins, list):
		json.dump(binance_perp_coins, open(os.path.join(tempdir, "binance-perp-pairs.json"), "w"))


t = threading.Thread(target=save_binance_perp_coins_to_tempdir)
t.daemon = True
t.start()


def sigterm_handler(signum, frame):
	global process
	process.send_signal(signal.SIGTERM)
	os.kill(os.getpid(), signal.SIGTERM)


signal.signal(signal.SIGTERM, sigterm_handler)


def on_message(ws, message):
	global buffer_longs, market_open, market_close, SPY_window, SPY_show
	data = json.loads(message)
	if "p" in data:
		price = float(data["p"])
		main_button.config(text=f"{price:.0f}|{buffer_longs}")
		main_line.lift()

	state = json.load(open(os.path.join(tempdir, "spy_feed.json"), "r"))[1]
	if state:
		SPY_show(state)
	else:
		if SPY_window is not None:
			SPY_window.destroy()
			SPY_window = None


def on_open(ws):
	print("Connection established")


def connect_to_binance():
	while True:
		try:
			ws = websocket.WebSocketApp("wss://fstream.binance.com/ws/btcusdt@markPrice", on_message=on_message, on_open=on_open)
			ws.run_forever()
		except Exception as e:
			print(f"WebSocket error: {e}")
			time.sleep(1)


# ----------------------------------------------------------


def format_now_then(now, then, dot=0):
	settings = json.load(open(os.path.join(tempdir, "settings.json"), "r"))

	now = float(now)
	change = now - float(then)

	now = str(round(now, dot))
	if len(now) == 1:
		now += ".00"
	if len(now) == 3:
		now += "0"

	change = round(change, dot)
	change = f"{change:+}"
	change = change[0] + change[2:] if change[1] == "0" else change

	if dot <= 0:
		cut = -2 + dot
		now = now[:cut]
		change = change[:cut]
	if len(change) == 1:  # meaning it is just '+' or '-', because actual value of 0 has been cut out
		change = "~0"

	format = f"{now}{change}" if settings["comparison_limit"] else f"{now}"
	return format


def get_percent_longs(symbol="btc", type="global"):
	symbol = symbol.upper() + "USDT"
	type = ("global", "Account") if type == "global" else ("top", "Position")
	try:
		r = requests.get(f"https://fapi.binance.com/futures/data/{type[0]}LongShort{type[1]}Ratio?symbol={symbol}&period=5m&limit=1").json()
		longs = float(r[0]["longAccount"])
		longs = str(round(longs, 2))
		longs = longs[1:]
		if len(longs) == 2:
			longs += "0"

		return longs
	except Exception as e:
		print(f"Error getting LSR: {e}")
		return None


first_update = True
update_counter = 0


def update():
	global additional_line, large_window
	global buffer_longs, process, first_update, update_counter
	settings = json.load(open(os.path.join(tempdir, "settings.json"), "r"))
	call = get_percent_longs()
	if not call is None:
		buffer_longs = call

	if debug:
		current_frame = inspect.currentframe()
		caller_frame = inspect.getouterframes(current_frame, 2)
		caller = caller_frame[1][3]
		if not caller == "schedule_update":
			print(f"DEBUG: update() called by {caller}")
	# ----------------------------------------------------------

	def additional_line_queue():
		longs = f"{get_percent_longs(type='top')}*"
		open_interest = ""
		if settings["additional_line"]["OI"]:
			from src.additional_line import get_open_interest

			tuple = get_open_interest(settings)
			open_interest = f"{format_now_then(tuple[0], tuple[1])}M"
		volume = ""
		if settings["additional_line"]["volume"]:
			volume = ",V:" if settings["label_data"] else ","
			from src.additional_line import get_volume

			tuple = get_volume(settings)
			volume += f"{format_now_then(tuple[0], tuple[1], -6)}M"
		return longs, open_interest, volume

	def update_additional_line():
		if additional_line is not None:
			global additional_frame, additional_button
			with concurrent.futures.ThreadPoolExecutor() as executor:
				future = executor.submit(additional_line_queue)
				array = future.result()

			text = ""
			for element in array:
				text += f"{element}"
			if additional_line is not None:
				global additional_frame, additional_button
				additional_button.config(text=text)
				if settings["additional_line"]["inflows"] == True:
					global inflows_label
					inflows_label.Refresh()

				width = additional_frame.winfo_reqwidth()
				height = additional_line.winfo_height()
				additional_line.geometry(f"{width}x{height}")

	def large_window_queue(script_path):
		try:
			subprocess.run(["python", script_path], check=True)
		except Exception as e:
			print(f"Error executing {script_path}: {e}")

	def update_large_window():
		MS_plot_resize()
		if large_window is not None:
			large_window_dir = os.path.join(src_dir, "large_window")
			global large_window_config
			scripts = [os.path.join(large_window_dir, f) for f in os.listdir(large_window_dir) if (f.endswith(".py") and f[:-3] in large_window_config)]

			with concurrent.futures.ThreadPoolExecutor() as executor:
				futures = [executor.submit(large_window_queue, script) for script in scripts]
				concurrent.futures.wait(futures)

			large_config()

	additional_button_thread = threading.Thread(target=update_additional_line, daemon=True)
	large_window_thread = threading.Thread(target=update_large_window, daemon=True)

	additional_button_thread.start()
	large_window_thread.start()
	# ----------------------------------------------------------

	timestamp = json.load(open(os.path.join(tempdir, "spy_feed.json"), "r"))[0]
	if timestamp + 60 < time.time() and not first_update:
		try:
			process.terminate()
			print("streamSPY died; rebooting...")
		except:
			pass
		process = subprocess.Popen(["python", "src/streamSPY.py", "main"])
	first_update = False
	update_counter += 1
	if update_counter == 14:
		subprocess.Popen(["python", "src/tiny_graphics/Inflows.py", "main"])
	if update_counter == 15:
		update_counter = 0
		subprocess.Popen(["python", "src/MarketStructure.py", "main"])


def schedule_update():
	global root
	update()
	root.after(60000, schedule_update)


def large_config():
	global large_window, large_label, display
	config = json.load(open(os.path.join(tempdir, "large_window.json"), "r"))
	settings = json.load(open(os.path.join(tempdir, "settings.json"), "r"))
	labels = display["large_window"]["labels"]
	text = ""
	for component in config:
		if settings["large_window"][component]:
			lines = config[component].splitlines()
			if settings["label_data"]:
				lines.insert(labels[component]["pos"], labels[component]["text"])
			text += "\n".join(lines)
			text += "\n"
	text = text[:-1] if text.endswith("\n") else text
	text = " " + text if not text.startswith(" ") else text  # dealing with the settings icon
	if large_window is not None:
		large_label.config(text=text, font=("Courier", settings["font_size"]))

		width = large_label.winfo_reqwidth()
		height = large_label.winfo_reqheight()
		large_window.geometry(f"{width}x{height}")


# ----------------------------------------------------------


class Window:  # todo // but acctually is it even needed?
	def resizeImg(self):
		pass


# <methods> #? how do I drop them into a separate file
def StatsPopup(master, text):
	window = tk.Toplevel(root)
	window.config(bg="black")
	window.resizable(0, 0)
	window.overrideredirect(True)
	window.attributes("-topmost", True)

	label = tk.Label(window, font="Adobe 12", text=text, fg="blue", bg="white")
	label.pack(anchor="w")
	window.geometry(f"{label.winfo_reqwidth()}x{label.winfo_reqheight()}+{master.winfo_x()}+{master.winfo_y()+master.winfo_height()}")
	return window


# </methods>


def lower_window(window):
	def lower_and_raise():
		window.attributes("-topmost", False)
		window.lower()
		time.sleep(3)
		try:  # we might've closed the window during the sleep
			window.attributes("-topmost", True)
			window.lift()
		except:
			pass

	threading.Thread(target=lower_and_raise, daemon=True).start()


def SPY_show(state):
	global SPY_window, SPY_label
	if SPY_window is None:
		SPY_window = tk.Toplevel(root)
		SPY_window.config(bg="black")
		SPY_window.geometry(f"{SPY_width}x{main_line.winfo_height()}+{main_line.winfo_x()}+{main_line.winfo_y()+main_line.winfo_height()}")
		SPY_window.resizable(0, 0)
		SPY_window.overrideredirect(True)
		SPY_window.attributes("-topmost", True)

		SPY_label = tk.Button(SPY_window, font="Adobe 12", text="", fg="green", bg="black", command=lambda: lower_window(SPY_window))
		SPY_label.pack(anchor="w")
	output = f"{state:.2f}"
	SPY_label.config(text=output)
	SPY_window.lift()


def settings_on_save():
	large_config()
	update()


def _large_on_resize():
	global large_window, large_label
	settings = json.load(open(os.path.join(tempdir, "settings.json"), "r"))
	if large_label.cget("text") == "":
		pass
	else:
		reqwidth = large_label.winfo_reqwidth()
		reqheight = large_label.winfo_reqheight()
		width_change = large_window.winfo_width() / reqwidth
		height_change = large_window.winfo_height() / reqheight
		change_font = round(settings["font_size"] * max(width_change, height_change))
		if change_font != settings["font_size"]:
			settings["font_size"] = change_font
			json.dump(settings, open(os.path.join(tempdir, "settings.json"), "w"))
			large_config()
	MS_plot_resize()


def _large_window_on_close():
	global large_window, large_label, settings, settings_button, MS_button
	if large_window is not None:
		large_window.destroy()
		large_window = None
	if settings_button is not None:
		settings_button.destroy()
		settings_button = None
	close_MS()


def close_MS():
	global MS_window, MS_plot
	if MS_window:
		MS_plot.pack_forget()
		MS_window.destroy()
		MS_window = None


def MS_plot_resize():
	global MS_window, MS_plot, large_window
	if MS_window:
		img = MS_window.img
		ratio = img.width / img.height
		large_window.update()
		geometry_str = large_window.winfo_geometry()
		l_width = int(geometry_str.split("x")[0])
		l_height = int(geometry_str.split("x")[1].split("+")[0])
		l_x = int(geometry_str.split("+")[1])
		l_y = int(geometry_str.split("+")[2])

		ms_width = l_width
		ms_height = int(ms_width / ratio)
		img = img.resize((ms_width, ms_height))
		tk_img = ImageTk.PhotoImage(img)

		MS_window.geometry(f"{ms_width}x{ms_height}+{l_x+8}+{l_y+l_height+30}")  # the additions are to account for the title (haven't found a built-in way)

		MS_plot.configure(image=tk_img)
		MS_plot.image = tk_img


def MS_button_on_click():
	global MS_window, MS_plot
	if MS_window is None:
		MS_window = tk.Toplevel(root)
		MS_window.config(bg="black")
		MS_window.resizable(0, 0)
		MS_window.overrideredirect(True)
		MS_window.attributes("-topmost", True)

		MS_window.img = Image.open(os.path.join(tempdir, "MarketStructure.png"))

		MS_plot = tk.Button(MS_window, command=close_MS)
		MS_plot.pack()

		MS_plot_resize()
	else:
		close_MS()


def create_MS_button(master):
	icon = tk.PhotoImage(file=os.path.join(src_dir, "icons/ms.png"))
	icon = icon.subsample(icon.width() // 17, icon.height() // 17)
	MS_button = tk.Button(master, image=icon, bg="black", padx=0, pady=0, borderwidth=0, command=MS_button_on_click)
	MS_button.image = icon
	MS_button.place(x=0, y=17, width=17, height=17)


def additional_click(*args):
	global large_window, large_label, large_last_resize_timestamp, large_creation_timestamp
	if large_window is None:
		settings = json.load(open(os.path.join(tempdir, "settings.json")))
		large_window = tk.Toplevel(root)
		large_window.config(bg="black")
		large_window.geometry(f"{large_dimensions[0]}x{large_dimensions[1]}+{main_line.winfo_x()+main_line.winfo_width()}+{main_line.winfo_y()+additional_line.winfo_height()}")
		large_window.attributes("-topmost", True)
		large_window.title("Market Info")

		large_label = tk.Button(
			large_window, font=("Courier", settings["font_size"]), justify="left", text="", fg="green", bg="black", command=lambda: lower_window(large_window)
		)  # using lambda: because the command= expects a function with no arguments
		large_label.pack(anchor="w")

		from src.settings_button import create_settings_button, open_settings_window

		global settings_button
		settings_button = create_settings_button(large_window)
		settings_button.config(command=lambda: open_settings_window(settings_on_save))

		create_MS_button(large_window)

		def on_resize(*args):
			global large_resize_ids
			schedule = True if len(large_resize_ids) < 2 else False
			if len(large_resize_ids) != 0:
				large_resize_ids.pop(0)
			if schedule:
				large_resize_ids.append(large_window.after(1000, _large_on_resize))

		large_window.protocol("WM_DELETE_WINDOW", _large_window_on_close)
		large_window.bind("<Configure>", on_resize)

		"""TODO: also open scrolling window for the volumes script (change it so it a) plots logarithmic
                values, b) has bg='white' c) move to negative coordinates, so opens only if there is a 
                second monitor connected on the left d) modify the code, so we 1) approximate function
                of average daily volume depending on MC 2) include this market-general calculation
                into the script."""
		update()
		if settings["MarketStructure"] == True:
			MS_button_on_click()
	else:
		_large_window_on_close()


class InflowsLabel:  # make it inherit from TinyGraphics label/window class
	def __init__(self, master):
		self.img_path = os.path.join(tempdir, "SpotInflowFig.png")
		self.stats_path = os.path.join(tempdir, "SpotInflowStats.json")
		self.label = tk.Label(master, image=None, borderwidth=0, highlightthickness=0, anchor="nw")
		self.label.pack(side="left")
		self.x0y0x1y1 = "0x0x0x0"  # todo

		self.stats_text = None
		self.stats_window = None

		self.label.bind("<Enter>", self.MouseEnter)
		self.label.bind("<Leave>", self.MouseLeave)
		self.Refresh()

	def MouseEnter(self, *args):
		if self.stats_window == None:
			self.stats_window = StatsPopup(self.label, self.stats_text)

	def MouseLeave(self, *args):
		self.stats_window.destroy()
		self.stats_window = None

	def Refresh(self):
		print("requested image refresh")
		img = Image.open(self.img_path)
		pngInflows = ImageTk.PhotoImage(img)
		self.label.config(image=pngInflows)
		self.label.image = pngInflows

		stats = load(self.stats_path)
		self.stats_text = stats


def main_click(*args):
	global additional_line, additional_frame, additional_button, large_window
	if additional_line is None:
		settings = json.load(open(os.path.join(tempdir, "settings.json")))
		additional_line = tk.Toplevel(root)
		additional_line.config(bg="black")
		additional_line.geometry(f"{additional_width}x{main_line.winfo_height()}+{main_line.winfo_x()+main_line.winfo_width()}+{main_line.winfo_y()}")
		additional_line.resizable(0, 0)
		additional_line.overrideredirect(True)
		additional_line.attributes("-topmost", True)

		additional_frame = tk.Frame(additional_line)
		additional_frame.pack()

		additional_button = tk.Button(additional_frame, font="Adobe 12", justify="left", text="", fg="green", bg="black", command=additional_click)
		additional_button.pack(side="left")

		if settings["additional_line"]["inflows"] == True:
			global inflows_label
			inflows_label = InflowsLabel(additional_frame)
			inflows_label.Refresh()
		update()
	else:
		additional_line.destroy()
		additional_line = None
		if large_window:
			large_window.destroy()
			large_window = None


root = tk.Tk()
root.withdraw()

main_line = tk.Toplevel(root)
main_line.config(bg="black")
main_line.geometry("70x16")
main_line.resizable(0, 0)
main_line.attributes("-topmost", True)
main_line.overrideredirect(True)

main_button = tk.Button(main_line, font="Adobe 12", justify="left", text="", fg="green", bg="black", command=main_click)
main_button.pack()

t = threading.Thread(target=connect_to_binance)
t.daemon = True
t.start()
process = subprocess.Popen(["python", "src/streamSPY.py", "main"])
large_window_config = {}
for key in settings["large_window"].keys():
	if settings["large_window"][key] == True:
		large_window_config[key] = ""
json.dump(large_window_config, open(os.path.join(tempdir, "large_window.json"), "w"))
subprocess.Popen(["python", "src/tiny_graphics/Inflows.py", "main"])
subprocess.Popen(["python", "src/MarketStructure.py", "main"])

root.after(0, schedule_update)
root.mainloop()
