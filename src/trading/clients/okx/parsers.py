from typing import Dict, List
from datetime import datetime
from decimal import Decimal
from loguru import logger

from src.trading.base.models.market import (
    OrderBook, OrderBookLevel, Ticker, Trade, Candlestick
)

class OKXDataParser:
    """OKX数据解析器"""
    
    @staticmethod
    def parse_orderbook(data: Dict, symbol: str) -> Dict:
        """解析订单簿数据
        
        Args:
            data: 订单簿数据
            symbol: 交易对
            
        Returns:
            Dict: 订单簿数据字典
        """
        asks = [
            {
                "price": str(Decimal(str(level[0]))),
                "size": str(Decimal(str(level[1]))),
                "count": int(level[3]) if len(level) > 3 else 0
            }
            for level in data.get("asks", [])
            if Decimal(str(level[1])) > 0  # 只保留数量大于0的订单
        ]
        
        bids = [
            {
                "price": str(Decimal(str(level[0]))),
                "size": str(Decimal(str(level[1]))),
                "count": int(level[3]) if len(level) > 3 else 0
            }
            for level in data.get("bids", [])
            if Decimal(str(level[1])) > 0  # 只保留数量大于0的订单
        ]
        
        timestamp = int(data["ts"])
        dt = datetime.fromtimestamp(timestamp / 1000)
        
        return {
            "symbol": symbol,
            "asks": asks,
            "bids": bids,
            "timestamp": dt.isoformat()
        }
        
    @staticmethod
    def parse_ticker(data: Dict, symbol: str) -> Dict:
        """解析Ticker数据
        
        Args:
            data: Ticker数据
            symbol: 交易对
            
        Returns:
            Dict: Ticker数据字典
        """
        dt = datetime.fromtimestamp(int(data["ts"]) / 1000)
        return {
            "symbol": symbol,
            "last_price": str(Decimal(str(data["last"]))),
            "best_bid": str(Decimal(str(data["bidPx"]))),
            "best_ask": str(Decimal(str(data["askPx"]))),
            "volume_24h": str(Decimal(str(data["vol24h"]))),
            "high_24h": str(Decimal(str(data["high24h"]))),
            "low_24h": str(Decimal(str(data["low24h"]))),
            "timestamp": dt.isoformat()
        }
        
    @staticmethod
    def parse_trade(data: Dict, symbol: str) -> Dict:
        """解析成交数据
        
        Args:
            data: 成交数据
            symbol: 交易对
            
        Returns:
            Dict: 成交数据字典
        """
        dt = datetime.fromtimestamp(int(data["ts"]) / 1000)
        return {
            "symbol": symbol,
            "price": str(Decimal(str(data["px"]))),
            "size": str(Decimal(str(data["sz"]))),
            "side": data["side"],
            "timestamp": dt.isoformat(),
            "trade_id": data.get("tradeId")
        }
        
    @staticmethod
    def parse_candlestick(data: List, symbol: str, interval: str) -> Candlestick:
        """解析K线数据
        
        Args:
            data: K线数据列表，格式为:
                [
                    ts,         # 开始时间，Unix时间戳（毫秒）
                    o,          # 开盘价格
                    h,          # 最高价格
                    l,          # 最低价格
                    c,         # 收盘价格
                    vol,       # 交易量
                    volCcy,    # 交易额
                    volCcyQuote,# 交易额，以计价货币计量
                    confirm    # 是否确认
                ]
            symbol: 交易对
            interval: 时间周期
            
        Returns:
            Candlestick: K线数据对象
        """
        try:
            # 确保数据完整性
            if len(data) < 6:
                raise ValueError(f"K线数据不完整: {data}")
            
            # 转换时间戳（毫秒）为datetime对象
            timestamp = datetime.fromtimestamp(int(data[0]) / 1000)
            
            # 返回Candlestick对象
            return Candlestick(
                symbol=symbol,
                interval=interval,
                timestamp=timestamp,
                open=Decimal(str(data[1])),
                high=Decimal(str(data[2])),
                low=Decimal(str(data[3])),
                close=Decimal(str(data[4])),
                volume=Decimal(str(data[5]))
            )
            
        except (IndexError, ValueError, TypeError) as e:
            logger.error(f"解析K线数据失败: {e}, 数据: {data}")
            raise 