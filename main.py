from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core import Core
from models import GenericFilter, VolumeRiskForm
import os
from dotenv import load_dotenv
load_dotenv()
from binance import AsyncClient, BinanceSocketManager

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def ping():
    return { 'data': 'pong' }


@app.post("/fractal/levels")
def get_fractal_levels(filter: GenericFilter):
    core = Core(filter.exchange)
    data = core.get_data(filter.symbol, filter.interval, filter.limit)
    return { 'data': core.detect_level_method_1(data) }


@app.post("/window/levels")
def get_window_levels(filter: GenericFilter):
    core = Core(filter.exchange)
    data = core.get_data(filter.symbol, filter.interval, filter.limit)
    return { 'data': core.detect_level_method_2(data) }


@app.post("/klines")
def get_klines(filter: GenericFilter):
    core = Core(filter.exchange)
    data = core.get_data_parsed(filter.symbol, filter.interval, filter.limit, filter.indicators)
    return { 'data': data }


@app.get("/symbols")
def get_symbols():
    core = Core()
    return { 'data': core.get_symbols() }


@app.post("/volume-risk")
def get_volume_by_risk(form: VolumeRiskForm):
    print(form)
    core = Core()
    data = core.get_volume_by_risk(form.volume, form.volatility_ptc, form.taker_fee, form.maker_fee)
    return { 'data': data }


@app.websocket("/ws/volume-at-time")
async def get_volume_at_time(websocket: WebSocket):
    await websocket.accept()
    SELL = 'SELL'
    BUY = 'BUY'
    sell_volume = 0
    buy_volume = 0
    volume = 0
    client = await AsyncClient.create(api_key=os.getenv("API_KEY_PROD"), api_secret=os.getenv("SECRET_KEY_PROD"))         
    try:
        resp = await websocket.receive_json()
        print('/ws/volume-at-time', resp)
        bm = BinanceSocketManager(client)
        ts = bm.trade_socket(symbol=resp['symbol'])
        async with ts as tscm:
            while True:
                res = await tscm.recv()
                volume = round(float(res['q']) * float(res['p']), 1)
                side = SELL if res['m'] else BUY
                if side == SELL:
                    sell_volume += volume
                else:
                    buy_volume += volume

                await websocket.send_json({
                    'symbol': res['s'],
                    'volume': volume,
                    'sell_volume': round(sell_volume, 1),
                    'buy_volume': round(buy_volume, 1),
                    'time': res['T']
                })
        await client.close_connection()
        
    except Exception as e:
        print('error:', e)
        await client.close_connection()


@app.websocket("/ws/klines")
async def get_volume_at_time(websocket: WebSocket):
    await websocket.accept()
    client = await AsyncClient.create(api_key=os.getenv("API_KEY_PROD"), api_secret=os.getenv("SECRET_KEY_PROD"))  
    klines_loop = True       
    try:
        resp = await websocket.receive_json()
        print('/ws/klines', resp)
        bm = BinanceSocketManager(client)
        ts = bm.kline_socket(symbol=resp['symbol'], interval=resp['interval'])
        async with ts as tscm:
            while klines_loop:
                res = await tscm.recv()                
                await websocket.send_json({
                    'open': res['k']['o'],
                    'high': res['k']['h'],
                    'low': res['k']['l'],
                    'close': res['k']['c'],
                    'volume': res['k']['v'],
                    'time': res['k']['T']
                })
            await client.close_connection()
        
    except Exception as e:
        print('error:', e)
        await websocket.close()
        await client.close_connection()
        
    