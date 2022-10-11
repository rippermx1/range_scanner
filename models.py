from pydantic import BaseModel

from constants import EXCHANGE_BINANCE

class GenericFilter(BaseModel):
    symbol: str
    interval: str
    limit: int
    indicators: bool = False
    exchange: str = EXCHANGE_BINANCE

class VolumeRiskForm(BaseModel):
    volume: int
    volatility_ptc: float    
    taker_fee: float
    maker_fee: float