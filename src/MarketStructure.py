import requests, json, threading, os, tempfile, pandas as pd, numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from IPython.display import Image

hours_selected = 24
timeframe = 5
script_dir = os.path.dirname(os.path.abspath(__file__))
tempdir = os.path.join(tempfile.gettempdir(), 'BTCline')

def get_historical_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}m"

    time_ago = datetime.now() - timedelta(hours=hours_selected)
    time_ago_ms = int(time_ago.timestamp() * 1000)
    url += f"&startTime={time_ago_ms}"

    raw_data = requests.get(url).json()
    df = pd.DataFrame(raw_data, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                         'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close'] = pd.to_numeric(df['close'])
    df.set_index('open_time', inplace=True, drop=False)
    df['return'] = df['close'].pct_change() + 1
    df.iloc[0, df.columns.get_loc('return')] = 1 # set first datapoint to one
    df['cumulative_return'] = df['return'].cumprod()
    df['variance'] = df['close'].var()
    return df


def plot_market_structure(symbols):
    def fetch_data(symbol, data):
        try:
            df = get_historical_data(symbol)
            data[symbol] = df
        except Exception as e:
            print(f"Failed to fetch data for symbol: {symbol}. Error: {str(e)}")
    data = {}
    threads = []
    for symbol in symbols:
        thread = threading.Thread(target=fetch_data, args=(symbol, data))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

    # <data-analysis>
    normalized_data = {symbol: df['close'] / df['close'].iloc[0] for symbol, df in data.items()}
    normalized_df = pd.DataFrame(normalized_data)
    normalized_df = normalized_df.apply(np.log)

    performance = normalized_df.iloc[-1] - normalized_df.iloc[0]
    top_performers = performance.nlargest(5).index
    bottom_performers = performance.nsmallest(5).index
    
    mean_values = normalized_df.mean(axis=1)
    deviations_df = normalized_df.sub(mean_values, axis=0)
    flattened_deviations = deviations_df.values.flatten()
    variance = np.var(flattened_deviations, ddof=1) #* works, but unconvinient sizing - too many .00s
    kurtosis = pd.Series(flattened_deviations).kurt() #! meaningless due to **4 thingie, that gets skewed immediately on any outliers
    
    correlation_matrix = normalized_df.corr()
    mean_correlation = correlation_matrix.mean().mean()  #! pretty sure this is a very shitty method
    # </data-analysis>

    fig = go.Figure()

    def add_trace(*args):
        y, name, line, legend = args
        fig.add_trace(
                go.Scatter(
                    x=normalized_df.index,
                    y=y,
                    mode='lines',
                    name=name,
                    line=line,
                    showlegend=legend
                )
            )
    def add_performers(column):
        symbol = column[:-4]
        symbol.replace('1000', '', 1)
        sign = f"{performance[column]:+}"[0]
        change = f"{round(100*performance[column], 2):.2f}"
        change = change[1:] if change[0]=='-' else change
        name = f"{symbol:<5}{sign}{change:>5}%"
        add_trace(normalized_df[column], name, dict(width=2), True)
    def add_empty(name):
        add_trace([1]*len(normalized_df.index), name, dict(width=0), True)

    # <plotting>
    for column in normalized_df.columns:
        if column not in top_performers and column not in bottom_performers and column != 'BTCUSDT':
            add_trace(normalized_df[column], '', dict(width=1, color='grey'), False)
    for column in top_performers:
        add_performers(column)
    add_trace(normalized_df['BTCUSDT'], f"~BTC~ {round(100*performance['BTCUSDT'], 2):>5}", dict(width=5, color='gold'), True)
    for column in bottom_performers[::-1]:
        add_performers(column)
    add_empty('')
    add_empty(f"V: {variance:.5f}")
    add_empty(f"K: {round(kurtosis, 1)}")
    add_empty(f"C: {round(mean_correlation, 2)}")
    # </plotting>
    
    fig.update_layout(template='plotly_dark', autosize=True, margin=dict(l=0, r=0, b=0, t=0), font={"family":"Courier New, monospace"})
    fig.update_xaxes(range=[normalized_df.index.min(), normalized_df.index.max()])
    fig.update_yaxes(range=[normalized_df.min().min(), normalized_df.max().max()])

    return fig

def main():
    symbols = json.load(open(os.path.join(tempdir, 'binance-perp-pairs.json')))

    fig = plot_market_structure(symbols)
    fig.write_image(os.path.join(tempdir, 'MarketStructure.png'))

if __name__ == "__main__":
    main()
