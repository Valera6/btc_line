import requests, aiohttp, asyncio, tempfile, json, os


most_longed = 10
most_shorted = 10
debug = False
#========================================================== 

tempdir = os.path.join(tempfile.gettempdir(), 'BTCline')
settings = json.load(open(os.path.join(tempdir, 'settings.json')))
limit = settings['comparison_limit']

def format_now_then(now, then, dot=(0, 0)):
    settings = json.load(open(os.path.join(tempdir,'settings.json'), 'r'))

    now = float(now)
    change = now - float(then)

    now = str(round(now, dot[0]))

    change = round(change, dot[1])
    change = f"{change:+}"
    change = change[0]+change[2:] if change[1] == '0' else change

    while '.' in change and change[-1] in ['0', '.']:
        change = change[:-1]

    if dot[0] <= 0:
        now_cut = -2+dot[0]
        now = now[:now_cut]
    if dot[1] <= 0:
        change_cut = -2+dot[1]
        change = change[:change_cut]
    if len(change) == 1: # meaning it is just '+' or '-', because actual value of 0 has been cut out
        change = '  ~'

    format = f"{now}{change}" if settings['comparison_limit'] else f"{now}"
    return format

futures_pairs = json.load(open(os.path.join(tempdir, 'binance-perp-pairs.json')))
async def get_ratio(session, symbol):
    try:
        async with session.get(f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period=5m&limit={limit*12 +1}") as resp:
            r = await resp.json()
            now = r[0]['longShortRatio']
            then = r[-1]['longShortRatio']
            """if r_now[2] == '.': # if number is >= 10, it would overwise be output as '11.'
                r_now[2] == ' '
            now = r_now[:3]""" # supposedly can handle it with format_now_then(now, then, 1)
            if not now[:3].lower() == 'inf':
                ratios.append({
                    "symbol": symbol[:-4],
                    "values": (now, then)
                    })
    except:
        pass

ratios = []
async def main(symbols):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for symbol in symbols:
            task = asyncio.create_task(get_ratio(session, symbol))
            tasks.append(task)

        await asyncio.gather(*tasks)
        sorted_ratios = sorted(ratios, key=lambda x: float(x['values'][0]))
        
        result_string = ''
        for r in range(most_longed):
            def extract_values(index):
                element = sorted_ratios[index]

                symbol = element['symbol']+':'

                values = element['values']
                format = format_now_then(values[0], values[1], dot=(1, 2))

                return symbol, format
            # l and s for most longed and most shorted
            s_symbol, s_format = extract_values(r)
            l_symbol, l_format = extract_values(-r-1)


            second_row = f"  ├{s_symbol:<9} {s_format}" if r < most_shorted else ''
            result_string += f"  ├{l_symbol:<9} {l_format:<8}{second_row}\n"
        result_string = result_string[:-1]
        
        large_window = json.load(open(os.path.join(tempdir,'large_window.json'), 'r'))
        large_window['LSRoutliers'] = result_string
        json.dump(large_window, open(os.path.join(tempdir,'large_window.json'), 'w'))

if __name__=='__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(futures_pairs))

    if debug:
        lw = json.load(open(os.path.join(tempdir, 'large_window.json')))
        result = lw['LSRoutliers']
        print(result)