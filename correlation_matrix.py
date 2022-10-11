import pandas as pd
from binance.client import Client
import os
from dotenv import load_dotenv
load_dotenv()
import numpy as np
from database import Database

client = Client(os.getenv('API_KEY_PROD'), os.getenv('SECRET_KEY_PROD'))

info = client.get_exchange_info()


symbols = [x['symbol'] for x in info['symbols']]
relevant = [symbol for symbol in symbols if symbol.endswith('USDT')]
exclude = ['UP', 'DOWN', 'BEAR', 'BULL']
relevant = [symbol for symbol in relevant if all(excludes not in symbol for excludes in exclude)]


def get_daily_data(symbol, historical=True):
    interval = "365 days ago UTC" if historical else "1 day ago UTC"
    frame = pd.DataFrame(client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, interval))

    if len(frame) > 0:
        frame = frame.iloc[:, :5]
        frame.columns = ['Time', 'Open', 'High', 'Low', 'Close']
        frame = frame.set_index('Time')
        frame.index = pd.to_datetime(frame.index, unit='ms')
        frame = frame.astype(float)
        return frame


engine = Database().get_engine()
dfs = []
relevant_used = []
historical = True
''' for coin in relevant:
    df = get_daily_data(coin, historical=historical)
    if df is not None and len(df) >= 365 if historical else 1:
        print(coin)
        dfs.append(df)
        relevant_used.append(coin)   

mergeddf = pd.concat(dict(zip(relevant_used, dfs)), axis=1)
closesdf: pd.DataFrame = mergeddf.loc[:, mergeddf.columns.get_level_values(1).isin(['Close'])]
closesdf.columns = closesdf.columns.droplevel(1)

closesdf.to_sql('close_historical', con=engine, if_exists='replace', index=True) '''

df = pd.read_sql('close_historical', con=engine, index_col='Time')

logretdf = np.log(df.pct_change() + 1)
logretdf.corr()
print(logretdf.corr())

import seaborn as sns
import matplotlib.pyplot as plt


specific_coins = ['BTCUSDT', 'ETHUSDT', 'LTCUSDT', 'BCHUSDT', 'EOSUSDT', 'XRPUSDT', 'ADAUSDT', 'XLMUSDT', 'TRXUSDT']
df = logretdf[specific_coins].corr()

df_corr = logretdf.corr()
largest = df_corr['BTCUSDT'].nlargest(10)
smallest = df_corr['BTCUSDT'].nsmallest(10)
print(largest)
print(smallest)

''' fig, ax = plt.subplots(figsize=(11, 9))
sns.heatmap(df, cmap="viridis", cbar_kws={"shrink": .8})
plt.show() '''


''' Valor de r	Fuerza de relación
-1,0 A -0,5 o 1,0 a 0,5	Fuerte
-0,5 A -0,3 o 0,3 a 0,5	Moderada
-0,3 A -0,1 o 0,1 a 0,3	Débil
-0,1 A 0,1	Ninguna o muy débil '''