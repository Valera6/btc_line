import requests, json

def get_open_interest(settings, symbol='btc'):
    symbol = symbol.upper()+'USDT'
    limit = settings['comparison_limit']
    try:
        r = requests.get(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=5m&limit={limit*12+1}").json()
        def extract(i):
            open_interest = float(r[i]['sumOpenInterestValue'])
            open_interest = str(round(open_interest))
            open_interest = f"{open_interest[:-6]}"
            return float(open_interest)
        
        return extract(-1), extract(0)
    except Exception as e:
        print(f"Error getting open interest: {e}")
        return None, None

def get_volume(settings):
    limit = settings['comparison_limit']
    r = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=5m&limit={limit*12+288}").json()


    now, then = 0, 0
    for i, k in enumerate(r):
        if i<288:
            now += float(k[7])
        if i>=limit*12:
            then += float(k[7])

    return now, then
