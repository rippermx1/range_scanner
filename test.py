import ccxt
import os
from pandas import DataFrame

ftx = ccxt.ftx({
    'apiKey': os.getenv("API_KEY_FTX"),
    'secret': os.getenv("SECRET_KEY_FTX")
})

ftx.load_markets()


def get_swap_symbols(exchange):
    return [i['id'] for i in exchange.fetch_markets() if i['swap'] and i['active']]




binance = ccxt.binance({
    'apiKey': os.getenv("FUTURES_API_KEY_BINANCE"),
    'secret': os.getenv("FUTURES_SECRET_KEY_BINANCE"),
    'options': {
        'defaultType': 'future',
    }
})
binance.load_markets()

symbols = get_swap_symbols(binance)

for symbol in symbols:
    print(symbol)
    try:
        data = DataFrame(binance.fetch_ohlcv(symbol, '1d', limit=1000), columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        print(data)
    except Exception as e:
        print(e)


