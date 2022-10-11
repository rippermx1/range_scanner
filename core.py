from binance import Client
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

from constants import EXCHANGE_BINANCE, EXCHANGE_FTX
load_dotenv()
import pandas_ta as ta
import ccxt

class Core:
    
    def __init__(self, exchange=EXCHANGE_BINANCE):
        self.symbol = 'BTCUSDT'
        self.interval = '1m'
        self.limit = 1000

        if exchange == EXCHANGE_BINANCE:
            self.exchange = ccxt.binance({
                'apiKey': os.getenv("FUTURES_API_KEY_BINANCE"),
                'secret': os.getenv("FUTURES_SECRET_KEY_BINANCE"),
                'options': {
                    'defaultType': 'future',
                }
            })
        elif exchange == EXCHANGE_FTX:
            self.exchange = ccxt.ftx({
                'apiKey': os.getenv("API_KEY_FTX"),
                'secret': os.getenv("SECRET_KEY_FTX")                
            })

    def get_data(self, symbol, interval, limit=1000, indicators=False):
        data = pd.DataFrame(self.exchange.fetch_ohlcv(symbol, interval, limit=limit))
        data.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        data[['Open','High','Low','Close', 'Volume']] = data[['Open','High','Low','Close', 'Volume']].astype(float)
        # print(data)
        data['Time'] = pd.to_datetime(data['Time'], unit='ms')
        data = data.set_index('Time')
        if indicators:
            data['sma_200'] = ta.sma(data['Close'], 200)
            data['sma_50'] = ta.sma(data['Close'], 50)
            data['ema_13'] = ta.ema(data['Close'], 13)            
        if interval == '5m':
            data['vwap'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])            
        
        return data.dropna()
    
    def get_data_parsed(self, symbol, interval, limit=1000, indicators=False):
        df = self.get_data(symbol, interval, limit, indicators)
        data = []
        for index, row in df.iterrows():
            if indicators:
                row = {
                    'time': index, 
                    'open': row['Open'], 
                    'high': row['High'], 
                    'low': row['Low'], 
                    'close': row['Close'],
                    'sma_200': row['sma_200'],
                    'sma_50': row['sma_50'],
                    'ema_13': row['ema_13'],
                }                             
            else: 
                row = {
                    'time': index, 
                    'open': row['Open'], 
                    'high': row['High'], 
                    'low': row['Low'], 
                    'close': row['Close'],
                    'vwap': row['vwap']         
                }
            data.append(row)
        return data

    # to make sure the new level area does not exist already
    def is_far_from_level(self, value, levels, df):    
        ave =  np.mean(df['High'] - df['Low'])    
        return np.sum([abs(value-level)<ave for _,level in levels])==0

    # determine bullish fractal 
    def is_support(self, df,i):  
        cond1 = df['Low'][i] < df['Low'][i-1]   
        cond2 = df['Low'][i] < df['Low'][i+1]   
        cond3 = df['Low'][i+1] < df['Low'][i+2]   
        cond4 = df['Low'][i-1] < df['Low'][i-2]  
        return (cond1 and cond2 and cond3 and cond4) 
    # determine bearish fractal
    def is_resistance(self, df,i):  
        cond1 = df['High'][i] > df['High'][i-1]   
        cond2 = df['High'][i] > df['High'][i+1]   
        cond3 = df['High'][i+1] > df['High'][i+2]   
        cond4 = df['High'][i-1] > df['High'][i-2]  
        return (cond1 and cond2 and cond3 and cond4)

    #method 1: fractal candlestick pattern
    def detect_level_method_1(self, df):
        levels = []
        parsed = []
        for i in range(2, df.shape[0] - 2):
            if self.is_support(df, i):
                l = df['Low'][i]
                if self.is_far_from_level(l, levels, df):
                    levels.append((df.index[i], l))
                    parsed.append({
                        'time': df.index[i], 
                        'value': l,
                        'type': 'support'
                        })
            elif self.is_resistance(df, i):
                l = df['High'][i]
                if self.is_far_from_level(l, levels, df):
                    levels.append((df.index[i], l))
                    parsed.append({
                        'time': df.index[i], 
                        'value': l,
                        'type': 'resistance'
                        })
        return parsed    

    #method 2: window shifting method
    def detect_level_method_2(self, df):
        levels = []
        max_list = []
        min_list = []
        parsed = []
        for i in range(5, len(df)-5):
            high_range = df['High'][i-5:i+4]
            current_max = high_range.max()
            if current_max not in max_list:
                max_list = []
            max_list.append(current_max)
            if len(max_list) == 5 and self.is_far_from_level(current_max, levels, df):
                levels.append((high_range.idxmax(), current_max))
                parsed.append({
                        'time': high_range.idxmax(), 
                        'value': current_max,
                        'type': 'resistance'
                        })
            
            low_range = df['Low'][i-5:i+5]
            current_min = low_range.min()
            if current_min not in min_list:
                min_list = []
            min_list.append(current_min)
            if len(min_list) == 5 and self.is_far_from_level(current_min, levels, df):
                levels.append((low_range.idxmin(), current_min))
                parsed.append({
                        'time': low_range.idxmin(), 
                        'value': current_min,
                        'type': 'support'
                        })
        return parsed
    
    def get_symbols(self):
        exclude = ['UP', 'DOWN', 'BEAR', 'BULL']
        symbols = self.client.get_exchange_info()['symbols']
        symbols = [s['symbol'] for s in symbols if s['quoteAsset'] == 'USDT']
        symbols = [symbol for symbol in symbols if all(excludes not in symbol for excludes in exclude)]
        return symbols

    def get_volume_by_risk(self, volume, volatility_ptc, max_trades = 10, taker_fee = 0.0007, maker_fee = 0.0002):
        summary = []
        for i in range(max_trades):
            trx_group = []
            volume_to_use = round(float((volume/volatility_ptc)/(i+1)), 2)
            max_loss = round(float(volume_to_use * volatility_ptc/100), 2)
            for _ in range(0, i + 1):
                taker_fee_usd = round(float(volume_to_use * taker_fee), 2)
                maker_fee_usd = round(float(volume_to_use * maker_fee), 2)
                trx = {
                    'volume_to_use': volume_to_use,
                    'max_loss': max_loss,
                    'taker_fee': taker_fee_usd,
                    'maker_fee': maker_fee_usd
                }
                trx_group.append(trx)
            summary.append({
                'id': i + 1,
                'trx_group': trx_group
            })
        return summary