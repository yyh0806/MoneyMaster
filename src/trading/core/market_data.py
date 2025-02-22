from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Optional
import numpy as np
from collections import deque

@dataclass
class MarketTick:
    """市场行情数据"""
    symbol: str                # 交易对
    last_price: Decimal       # 最新价格
    bid_price: Decimal       # 买一价
    ask_price: Decimal       # 卖一价
    volume_24h: Decimal      # 24小时成交量
    high_24h: Decimal        # 24小时最高价
    low_24h: Decimal         # 24小时最低价
    timestamp: datetime      # 时间戳

@dataclass
class Candlestick:
    """K线数据"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

class MarketDataManager:
    """市场数据管理器"""
    
    def __init__(self, max_candles: int = 1000):
        self.max_candles = max_candles
        self.ticks: Dict[str, MarketTick] = {}  # symbol -> 最新行情
        self.candles: Dict[str, deque] = {}     # symbol -> K线队列
        self.orderbooks: Dict[str, Dict] = {}   # symbol -> 订单簿
        
    def update_tick(self, symbol: str, tick_data: Dict):
        """更新市场行情"""
        tick = MarketTick(
            symbol=symbol,
            last_price=Decimal(tick_data['last']),
            bid_price=Decimal(tick_data.get('bidPx', '0')),
            ask_price=Decimal(tick_data.get('askPx', '0')),
            volume_24h=Decimal(tick_data.get('vol24h', '0')),
            high_24h=Decimal(tick_data.get('high24h', '0')),
            low_24h=Decimal(tick_data.get('low24h', '0')),
            timestamp=datetime.now()
        )
        self.ticks[symbol] = tick
        return tick
        
    def update_candle(self, symbol: str, candle_data: List):
        """
        更新K线数据
        :param candle_data: [timestamp, open, high, low, close, volume, ...]
        """
        if symbol not in self.candles:
            self.candles[symbol] = deque(maxlen=self.max_candles)
            
        candle = Candlestick(
            timestamp=datetime.fromtimestamp(int(candle_data[0]) / 1000),
            open=Decimal(candle_data[1]),
            high=Decimal(candle_data[2]),
            low=Decimal(candle_data[3]),
            close=Decimal(candle_data[4]),
            volume=Decimal(candle_data[5])
        )
        self.candles[symbol].append(candle)
        return candle
        
    def update_orderbook(self, symbol: str, orderbook_data: Dict):
        """更新订单簿"""
        self.orderbooks[symbol] = {
            'bids': [(Decimal(price), Decimal(size)) for price, size in orderbook_data.get('bids', [])],
            'asks': [(Decimal(price), Decimal(size)) for price, size in orderbook_data.get('asks', [])]
        }
        
    def get_vwap(self, symbol: str, window: int = 20) -> Optional[Decimal]:
        """
        计算成交量加权平均价格(VWAP)
        :param window: 计算窗口大小
        """
        if symbol not in self.candles or len(self.candles[symbol]) < window:
            return None
            
        candles = list(self.candles[symbol])[-window:]
        total_volume = sum(c.volume for c in candles)
        if total_volume == 0:
            return None
            
        vwap = sum((c.close * c.volume) for c in candles) / total_volume
        return Decimal(str(vwap))
        
    def get_volatility(self, symbol: str, window: int = 20) -> Optional[Decimal]:
        """
        计算价格波动率
        :param window: 计算窗口大小
        """
        if symbol not in self.candles or len(self.candles[symbol]) < window:
            return None
            
        prices = [float(c.close) for c in list(self.candles[symbol])[-window:]]
        returns = np.diff(np.log(prices))
        volatility = np.std(returns, ddof=1) * np.sqrt(252)  # 年化波动率
        return Decimal(str(volatility))
        
    def get_liquidity_score(self, symbol: str) -> Optional[Decimal]:
        """计算流动性评分"""
        if symbol not in self.orderbooks:
            return None
            
        orderbook = self.orderbooks[symbol]
        
        # 计算买卖盘深度
        bid_depth = sum(size for _, size in orderbook['bids'][:5])
        ask_depth = sum(size for _, size in orderbook['asks'][:5])
        
        # 计算买卖价差
        spread = orderbook['asks'][0][0] - orderbook['bids'][0][0]
        mid_price = (orderbook['asks'][0][0] + orderbook['bids'][0][0]) / 2
        
        # 计算流动性评分 (深度/价差比率)
        liquidity_score = (bid_depth + ask_depth) / (spread / mid_price)
        return Decimal(str(liquidity_score))
        
    def get_trend_strength(self, symbol: str, window: int = 20) -> Optional[Dict[str, Decimal]]:
        """
        计算趋势强度指标
        :return: {'strength': 趋势强度, 'direction': 趋势方向(1: 上涨, -1: 下跌)}
        """
        if symbol not in self.candles or len(self.candles[symbol]) < window:
            return None
            
        candles = list(self.candles[symbol])[-window:]
        prices = [float(c.close) for c in candles]
        
        # 计算价格变化和波动
        price_change = prices[-1] - prices[0]
        volatility = np.std(prices)
        
        # 计算趋势强度
        strength = abs(price_change) / (volatility * np.sqrt(window))
        direction = 1 if price_change > 0 else -1
        
        return {
            'strength': Decimal(str(strength)),
            'direction': Decimal(str(direction))
        }
        
    def get_market_impact(self, symbol: str, order_size: Decimal) -> Optional[Dict[str, Decimal]]:
        """
        估算市场冲击成本
        :param order_size: 订单数量
        :return: {'price_impact': 价格影响, 'cost': 预计成本}
        """
        if symbol not in self.orderbooks:
            return None
            
        orderbook = self.orderbooks[symbol]
        remaining_size = order_size
        total_cost = Decimal('0')
        
        # 模拟吃单计算市场冲击
        for price, size in orderbook['asks']:
            if remaining_size <= 0:
                break
            matched_size = min(remaining_size, size)
            total_cost += matched_size * price
            remaining_size -= matched_size
            
        if remaining_size > 0:
            return None  # 订单簿深度不足
            
        avg_price = total_cost / order_size
        price_impact = (avg_price - orderbook['asks'][0][0]) / orderbook['asks'][0][0]
        
        return {
            'price_impact': price_impact,
            'cost': total_cost
        } 