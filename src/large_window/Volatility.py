import asyncio, json, tempfile, os, time, datetime
from aiohttp import ClientSession

event = asyncio.Event()
tempdir = os.path.join(tempfile.gettempdir(), 'BTCline')
settings = json.load(open(os.path.join(tempdir, 'settings.json')))
keys = json.load(open(os.path.join(tempdir, 'keys.json')))

async def get_VIX(session):
    try:
        limit = settings['comparison_limit']
        key = keys['twelvedata']['key']

        async def get_last_close():
            try:
                url = f'https://api.twelvedata.com/quote?symbol=VIX:CBOE&apikey={key}'
                async with session.get(url) as response:
                    r = await response.json()

                global VIX_closed_hours_ago, VIX_close
                VIX_closed_hours_ago = (time.time() - int(r["timestamp"])) / 3600
                VIX_close = float(r["close"])

                event.set()
                return VIX_close
            except:
                return None

        async def get_then():
            url = f'https://api.twelvedata.com/time_series?symbol=VIX:CBOE&interval=1h&outputsize={limit+1}&apikey={key}'
            async with session.get(url) as response:
                r = await response.json()

            try:
                points = r['values']
            except:
                print('failed to get the VIX history')
                print(r)
                return None
            then = datetime.datetime.now() - datetime.timedelta(hours=limit)
            distance = abs(then - datetime.datetime.strptime(points[0]['datetime'], "%Y-%m-%d %H:%M:%S"))
            closest_i = 0
            for i, p in enumerate(points):
                datetime_obj = datetime.datetime.strptime(p['datetime'], "%Y-%m-%d %H:%M:%S")
                if abs(then - datetime_obj) < distance:
                    distance = abs(then - datetime_obj)
                    closest_i = i

            await event.wait() # waiting for get_last_close()
            global VIX_closed_hours_ago, VIX_close
            if VIX_closed_hours_ago is None or VIX_closed_hours_ago > limit:
                return VIX_close
            return float(points[closest_i]['close'])

        last_close = await get_last_close()
        change = last_close - await get_then() if limit else None
        if change:
            change = f"{round(change, 2):+}"
            if change[0] == '0':
                change = change[1:]
        format = f"{last_close}{change}" if change else f"{last_close}"

        return format
    except Exception as e:
        print(e)
        return str(None)

async def get_BVOL(session):
    global settings
    limit = settings['comparison_limit']
    url = f"https://www.bitmex.com/api/v1/trade?symbol=.BVOL24H&count={limit*12+1}&reverse=true"
    async with session.get(url) as r:
        r = await r.json()

    now = r[0]['price']
    change = now - r[-1]['price']

    now = str(round(now, 2))
    if len(now) == 1:
        now += '.00'
    if len(now) == 3:
        now += '0'

    change = f"{round(change, 2):+}"
    change = change[0]+change[2:] if change[1] == '0' else change

    format = f"{now}{change}"
    return format

async def main():
    async with ClientSession() as session:
        vix, bvol = await asyncio.gather(get_VIX(session), get_BVOL(session))
        out = vix + ', ' + bvol
        # TODO: add greeks

        config = json.load(open(os.path.join(tempdir, 'large_window.json'), 'r'))
        config['Volatility'] = out
        json.dump(config, open(os.path.join(tempdir, 'large_window.json'), 'w'))

asyncio.run(main())

# https://www.delta.exchange/app/options_analytics