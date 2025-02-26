"""OKX交易所数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

@dataclass
class OKXOrderBookLevel:
    """订单簿档位"""
    price: Decimal
    size: Decimal
    count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "price": str(self.price),
            "size": str(self.size),
            "count": self.count
        }

@dataclass
class OKXOrderBook:
    """订单簿"""
    symbol: str
    asks: List[OKXOrderBookLevel]
    bids: List[OKXOrderBookLevel]
    timestamp: datetime
    checksum: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "asks": [ask.to_dict() for ask in self.asks],
            "bids": [bid.to_dict() for bid in self.bids],
            "timestamp": self.timestamp.isoformat(),
            "checksum": self.checksum
        }

@dataclass
class OKXTicker:
    """Ticker数据"""
    symbol: str
    last_price: Decimal
    best_bid: Decimal
    best_ask: Decimal
    volume_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    timestamp: datetime
    open_24h: Optional[Decimal] = None
    price_change_24h: Optional[Decimal] = None
    price_change_percent_24h: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "last_price": str(self.last_price),
            "best_bid": str(self.best_bid),
            "best_ask": str(self.best_ask),
            "volume_24h": str(self.volume_24h),
            "high_24h": str(self.high_24h),
            "low_24h": str(self.low_24h),
            "timestamp": self.timestamp.isoformat(),
            "open_24h": str(self.open_24h) if self.open_24h else None,
            "price_change_24h": str(self.price_change_24h) if self.price_change_24h else None,
            "price_change_percent_24h": self.price_change_percent_24h
        }

@dataclass
class OKXTrade:
    """成交数据"""
    symbol: str
    price: Decimal
    size: Decimal
    side: str
    timestamp: datetime
    trade_id: str
    maker_order_id: Optional[str] = None
    taker_order_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": str(self.price),
            "size": str(self.size),
            "side": self.side,
            "timestamp": self.timestamp.isoformat(),
            "trade_id": self.trade_id,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id
        }

@dataclass
class OKXCandlestick:
    """K线数据模型"""
    symbol: str
    interval: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Optional[Decimal] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": self.timestamp.isoformat(),
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "volume": str(self.volume),
            "quote_volume": str(self.quote_volume) if self.quote_volume else None
        }

@dataclass
class OKXBalance:
    """账户余额"""
    currency: str
    total: Decimal
    available: Decimal
    frozen: Decimal
    margin: Optional[Decimal] = None
    debt: Optional[Decimal] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency": self.currency,
            "total": str(self.total),
            "available": str(self.available),
            "frozen": str(self.frozen),
            "margin": str(self.margin) if self.margin else None,
            "debt": str(self.debt) if self.debt else None
        }

@dataclass
class OKXOrder:
    """订单信息"""
    symbol: str
    order_id: str
    client_order_id: Optional[str]
    price: Decimal
    size: Decimal
    type: str
    side: str
    status: str
    timestamp: datetime
    filled_size: Decimal = Decimal('0')
    filled_price: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    fee_currency: Optional[str] = None
    leverage: Optional[int] = None
    margin_mode: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "price": str(self.price),
            "size": str(self.size),
            "type": self.type,
            "side": self.side,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "filled_size": str(self.filled_size),
            "filled_price": str(self.filled_price) if self.filled_price else None,
            "fee": str(self.fee) if self.fee else None,
            "fee_currency": self.fee_currency,
            "leverage": self.leverage,
            "margin_mode": self.margin_mode
        }

@dataclass
class OKXMarketSnapshot:
    """市场数据快照"""
    symbol: str
    timestamp: datetime
    orderbook: Optional[OKXOrderBook] = None
    ticker: Optional[OKXTicker] = None
    trades: List[OKXTrade] = field(default_factory=list)
    candlesticks: Dict[str, List[OKXCandlestick]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "orderbook": self.orderbook.to_dict() if self.orderbook else None,
            "ticker": self.ticker.to_dict() if self.ticker else None,
            "trades": [trade.to_dict() for trade in self.trades],
            "candlesticks": {
                interval: [candle.to_dict() for candle in candles]
                for interval, candles in self.candlesticks.items()
            }
        } 