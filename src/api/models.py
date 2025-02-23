from dataclasses import dataclass
from datetime import datetime

@dataclass
class Candlestick:
    """K线数据模型"""
    timestamp: datetime  # 时间戳
    open: float         # 开盘价
    high: float         # 最高价
    low: float          # 最低价
    close: float        # 收盘价
    volume: float       # 成交量 