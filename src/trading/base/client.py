from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from decimal import Decimal

from .models.market import OrderBook, Ticker, Trade, Candlestick, MarketSnapshot

class ExchangeClient(ABC):
    """交易所客户端基础接口"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        
    @abstractmethod
    async def connect(self) -> bool:
        """连接交易所"""
        pass
        
    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass
        
    @abstractmethod
    async def get_orderbook(self, symbol: str) -> OrderBook:
        """获取订单簿"""
        pass
        
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """获取Ticker数据"""
        pass
        
    @abstractmethod
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """获取最近成交"""
        pass
        
    @abstractmethod
    async def get_candlesticks(self, symbol: str, interval: str, limit: int = 100) -> List[Candlestick]:
        """获取K线数据"""
        pass
        
    @abstractmethod
    async def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """获取市场数据快照"""
        pass
        
    @abstractmethod
    async def subscribe_orderbook(self, symbol: str):
        """订阅订单簿数据"""
        pass
        
    @abstractmethod
    async def subscribe_ticker(self, symbol: str):
        """订阅Ticker数据"""
        pass
        
    @abstractmethod
    async def subscribe_trades(self, symbol: str):
        """订阅成交数据"""
        pass
        
    @abstractmethod
    async def subscribe_candlesticks(self, symbol: str, interval: str):
        """订阅K线数据"""
        pass
        
    @abstractmethod
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         amount: Decimal, price: Optional[Decimal] = None) -> Dict:
        """下单"""
        pass
        
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """取消订单"""
        pass
        
    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> Dict:
        """获取订单信息"""
        pass
        
    @abstractmethod
    async def get_open_orders(self, symbol: str) -> List[Dict]:
        """获取未完成订单"""
        pass
        
    @abstractmethod
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """获取账户余额"""
        pass 