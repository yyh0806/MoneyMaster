from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

@dataclass
class OrderBookLevel:
    """订单簿档位数据"""
    price: Decimal
    size: Decimal
    count: int = 0
    orders: List[str] = field(default_factory=list)

@dataclass
class OrderBook:
    """订单簿数据"""
    symbol: str
    asks: List[OrderBookLevel]
    bids: List[OrderBookLevel]
    timestamp: datetime
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """获取中间价格"""
        if self.asks and self.bids:
            return (self.asks[0].price + self.bids[0].price) / 2
        return None
    
    @property
    def spread(self) -> Optional[Decimal]:
        """获取买卖价差"""
        if self.asks and self.bids:
            return self.asks[0].price - self.bids[0].price
        return None

@dataclass
class Trade:
    """成交数据"""
    symbol: str
    price: Decimal
    size: Decimal
    side: str  # buy/sell
    timestamp: datetime
    trade_id: Optional[str] = None

@dataclass
class Ticker:
    """Ticker数据"""
    symbol: str
    last_price: Decimal
    best_bid: Decimal
    best_ask: Decimal
    volume_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    timestamp: datetime

@dataclass
class Candlestick:
    """K线数据"""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    interval: str  # 1m, 5m, 15m, 1h, 4h, 1d, etc.

@dataclass
class MarketSnapshot:
    """市场数据快照"""
    symbol: str
    timestamp: datetime
    orderbook: Optional[OrderBook] = None
    ticker: Optional[Ticker] = None
    trades: List[Trade] = field(default_factory=list)
    candlesticks: dict[str, List[Candlestick]] = field(default_factory=dict)  # interval -> candlesticks
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """获取中间价格"""
        return self.orderbook.mid_price if self.orderbook else None
    
    @property
    def spread(self) -> Optional[Decimal]:
        """获取买卖价差"""
        return self.orderbook.spread if self.orderbook else None 