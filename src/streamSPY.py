import os, json, time, logging, threading, tempfile
from alpaca_trade_api.stream import Stream

log = logging.getLogger(__name__)

tempdir = os.path.join(tempfile.gettempdir(), 'BTCline')

keys = json.load(open(os.path.join(tempdir, 'keys.json'), 'r'))
API_KEY = keys['alpaca']['key']
API_SECRET = keys['alpaca']['secret']
os.environ['APCA_API_KEY_ID'] = API_KEY
os.environ['APCA_API_SECRET_KEY'] = API_SECRET

shared_data_path = os.path.join(tempdir, 'spy_feed.json')
if not os.path.exists(shared_data_path):
    json.dump((time.time(), None), open(shared_data_path, 'w'))

async def dump_data(t):
    json.dump((time.time(), t['p']), open(shared_data_path, 'w'))

def drop_timestamp(interval):
    while True:
        last_timestamp = json.load(open(shared_data_path, 'r'))[0]
        if last_timestamp + interval < time.time():
            json.dump((time.time(), None), open(shared_data_path, 'w'))
        time.sleep(interval)

def main():
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    feed = 'iex'
    stream = Stream(data_feed=feed, raw_data=True)
    stream.subscribe_trades(dump_data, 'SPY')

    @stream.on_status("*")
    async def _(status):
        print('status', status)

    timestamp_thread = threading.Thread(target=drop_timestamp, args=(30,))
    timestamp_thread.start()

    stream.run()

if __name__ == "__main__":
    main()
