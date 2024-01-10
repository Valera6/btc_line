import requests, pandas as pd, tempfile, tkinter as tk, os, json
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

tempdir = os.path.join(tempfile.gettempdir(), 'BTCline')

def create_fig(type):
    if type=='spot':
        url = 'https://api.binance.com/api/v3/klines'
        img_path = tempdir+'/SpotInflowFig.png'
        stats_path = tempdir+'/SpotInflowStats.json'
    else:
        url = 'https://fapi.binance.com/fapi/v1/klines'
        img_path = tempdir+'/FutsInflowFig.png'
        stats_path = tempdir+'/FutsInflowStats.json'
        
    params = {
        'symbol': 'BTCUSDT',
        'interval': '1d',
        'limit': 7
    }

    r = requests.get(url, params=params).json()

    df = pd.DataFrame()
    netInflows = []
    total_volume = 0
    for day in r:
        buys = float(day[-2])
        total = float(day[7])
        net = 2*buys-total
        # norm_net = net/total
        total_volume+=total

        netInflows.append(net)
    df['net_inflow'] = netInflows
    weekInflow = sum(netInflows)
    print(weekInflow, weekInflow/total_volume)
    df['timestamp'] = [x[0] for x in r]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    fig = Figure(figsize=(21, 4), dpi=4, facecolor='black')
    ax = fig.add_subplot(111, facecolor='black')
    colors = ['green' if _y >=0 else 'red' for _y in df['net_inflow']]
    ax.bar(df.index, df['net_inflow'], color=colors)

    ax.set_xticklabels([])
    ax.set_yticklabels([])
    fig.subplots_adjust(left=0, bottom=0, right=1, top=1)
    fig.savefig(img_path)
    
    stats = f"In: {round(weekInflow, -6)}\npT: {round(100*weekInflow/total_volume, 1)}%"
    json.dump(stats, open(stats_path, 'w'), indent=4)
    # return path
    
# todo have the class be defined here. Simple, right?
    
if __name__=='__main__':
    create_fig('spot')