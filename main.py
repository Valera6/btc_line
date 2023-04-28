import websocket, json, threading, time, requests, subprocess, os, sys, tempfile, concurrent.futures
import tkinter as tk

settings = {
    "comparison_limit": 1 # all comparisons will be done against the value {limit} hours ago.
}
#==========================================================

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)

additional_width = 120
SPY_width = 52
large_dimensions = (420, 210)
buffer_longs = ""
additional_line = None
large_window = None
SPY_window = None
update_ids = []
tempdir = tempfile.gettempdir()
json.dump(settings, open(os.path.join(tempdir,'settings.json'), 'w'))

def on_message(ws, message):
    global buffer_longs, market_open, market_close, SPY_window, SPY_show
    data = json.loads(message)
    if 'p' in data:
        price = float(data['p'])
        main_button.config(text=f"{price:.0f}|{buffer_longs}")
        main_line.lift()

    state = json.load(open(os.path.join(tempdir, 'spy_feed.json'), 'r'))[1]
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
            ws = websocket.WebSocketApp("wss://fstream.binance.com/ws/btcusdt@markPrice",
                                        on_message=on_message,
                                        on_open=on_open)
            ws.run_forever()
        except Exception as e:
            print(f"WebSocket error: {e}")
            time.sleep(1)
#---------------------------------------------------------- 

def get_percent_longs(symbol='btc', type='global'):
    symbol = symbol.upper()+'USDT'
    type = ('global', 'Account') if type == 'global' else ('top', 'Position')
    try:
        r = requests.get(f"https://fapi.binance.com/futures/data/{type[0]}LongShort{type[1]}Ratio?symbol={symbol}&period=5m&limit=1").json()
        longs = float(r[0]['longAccount'])
        longs = str(round(longs, 2))
        longs = longs[1:]
        if len(longs) == 2:
            longs += '0'

        return longs
    except Exception as e:
        print(f"Error getting LSR: {e}")
        return None
    
def get_open_interest(symbol='btc'):
    symbol = symbol.upper()+'USDT'
    limit = settings['comparison_limit']
    try:
        r = requests.get(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=5m&limit={limit*12+1}").json()
        def extract(i):
            open_interest = float(r[i]['sumOpenInterestValue'])
            open_interest = str(round(open_interest))
            open_interest = f"{open_interest[:-6]}"
            return float(open_interest)

        diff = extract(-1) - extract(0)
        # in second position is change from same time {limit} hours ago
        return f"{round(extract(-1))}{round(diff):+}M"
    except Exception as e:
        print(f"Error getting open interest: {e}")
        return None

first_update = True
def update():
    global additional_line, large_window
    global buffer_longs, update_ids, process, first_update
    call = get_percent_longs()
    if not call is None:
        buffer_longs = call
    #---------------------------------------------------------- 

    def additional_line_queue():
        longs = get_percent_longs(type='top')
        open_interest = get_open_interest()
        return longs, open_interest

    def update_additional_line():
        if additional_line is not None:
            global additional_button
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(additional_line_queue)
                longs, open_interest = future.result()
                additional_button.config(text=f"{longs}*{open_interest}")

    def large_window_queue(script_path):
        try:
            subprocess.run(["python", script_path], check=True)
        except Exception as e:
            print(f"Error executing {script_path}: {e}")

    def update_large_window():
        if large_window is not None:
            global large_label
            large_window_dir =  os.path.join(script_dir, "large_window")
            scripts = [os.path.join(large_window_dir, f) for f in os.listdir(large_window_dir) if f.endswith(".py")]

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(large_window_queue, script) for script in scripts]
                concurrent.futures.wait(futures)

            large = json.load(open(os.path.join(tempdir, 'large_window.json'), 'r'))
            text = ""
            for component in large:
                text+= f"{large[component]}\n"
            if large_window is not None:
                large_label.config(text=text)

    additional_button_thread = threading.Thread(target=update_additional_line, daemon=True)
    large_window_thread = threading.Thread(target=update_large_window, daemon=True)

    additional_button_thread.start()
    large_window_thread.start()
    #---------------------------------------------------------- 

    timestamp = json.load(open(os.path.join(tempdir, 'spy_feed.json'), 'r'))[0]
    if timestamp + 60 < time.time() and not first_update:
        try:
            process.terminate()
            print('streamSPY died; rebooting...')
        except:
            pass
        process = subprocess.Popen(['python', 'streamSPY.py', 'main'])
    schedule = True if len(update_ids) < 2 else False
    if len(update_ids) != 0:
        update_ids.pop(0)
    if schedule:
        update_ids.append(root.after(60000, update))
    first_update = False
#---------------------------------------------------------- 

def SPY_show(state):
    global SPY_window, SPY_label
    if SPY_window is None:
        SPY_window = tk.Toplevel(root)
        SPY_window.config(bg='black')
        SPY_window.geometry(f'{SPY_width}x{main_line.winfo_height()}+{main_line.winfo_x()}+{main_line.winfo_y()+main_line.winfo_height()}')
        SPY_window.resizable(0, 0)
        SPY_window.overrideredirect(True)
        SPY_window.attributes('-topmost', True)

        SPY_label = tk.Label(SPY_window, font="Adobe 12", text='', fg='green', bg='black')
        SPY_label.pack(anchor='w')
    output = f"{round(state, 2)}"
    output = output+'0' if len(output) <6 else output
    SPY_label.config(text=f"{round(state, 2)}")
    SPY_window.lift()

def _large_window_on_close():
    global large_window, large_label
    if large_window is not None:
        large_window.destroy()
        large_window = None
def additional_click(*args):
    global large_window, large_label
    if large_window is None:
        large_window = tk.Toplevel(root)
        large_window.config(bg='black')
        large_window.geometry(f'{large_dimensions[0]}x{large_dimensions[1]}+{main_line.winfo_x()+main_line.winfo_width()}+{main_line.winfo_y()+additional_line.winfo_height()}') 
        large_window.attributes('-topmost', True)
        large_window.title('Market Info')

        large_label = tk.Label(large_window, font=("Courier", 12), justify='left', text='', fg='green', bg='black')
        large_label.pack(anchor='w')
        large_window.protocol("WM_DELETE_WINDOW", _large_window_on_close)

        """TODO: also open scrolling window for the volumes script (change it so it a) plots logarithmic
                values, b) has bg='whit' c) move to negative coordinates, so opens only if there is a 
                second monitor connected on the left d) modify the code, so we 1) approximate function
                of average daily volume depending on MC 2) include this market-general calculation
                into the script."""
        update()
    else:
        large_window.destroy()
        large_window = None

def main_click(*args):
    global additional_line, additional_button, large_window
    if additional_line is None:
        additional_line = tk.Toplevel(root)
        additional_line.config(bg='black')
        additional_line.geometry(f'{additional_width}x{main_line.winfo_height()}+{main_line.winfo_x()+main_line.winfo_width()}+{main_line.winfo_y()}')
        additional_line.resizable(0, 0)
        additional_line.overrideredirect(True)
        additional_line.attributes('-topmost', True)

        additional_button = tk.Button(additional_line, font="Adobe 12", justify='left', text='', fg='green', bg='black', command=additional_click)
        additional_button.pack(anchor='w')
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
main_line.config(bg='black')
main_line.geometry('70x16')
main_line.resizable(0, 0)
main_line.attributes('-topmost', True)
main_line.overrideredirect(True)

main_button = tk.Button(main_line, font="Adobe 12", justify='left', text='', fg='green', bg='black', command=main_click)
main_button.pack()

t = threading.Thread(target=connect_to_binance)
t.daemon = True
t.start()
process = subprocess.Popen(['python', 'streamSPY.py', 'main'])
json.dump({'LSRoutliers': ''}, open(os.path.join(tempdir,'large_window.json'), 'w'))

root.after(0, update)
root.mainloop()
