from typing import Dict, Optional, List, Any
from decimal import Decimal
import aiohttp
from loguru import logger
from datetime import datetime

from src.trading.base.client import ExchangeClient
from src.trading.base.models.market import (
    OrderBook, Ticker, Trade, Candlestick, MarketSnapshot
)
from .ws_client import OKXWebSocketClient
from .rest_client import OKXRestClient

class OKXClient(ExchangeClient):
    """OKX交易所客户端"""
    
    def __init__(self, 
                 symbol: str, 
                 api_key: Optional[str] = None, 
                 api_secret: Optional[str] = None, 
                 passphrase: Optional[str] = None,
                 testnet: bool = False):
        """初始化OKX客户端
        
        Args:
            symbol: 交易对
            api_key: API密钥
            api_secret: API密钥对应的密文
            passphrase: API密码
            testnet: 是否使用测试网
        """
        super().__init__(api_key, api_secret)
        self.symbol = symbol
        self.passphrase = passphrase
        self.testnet = testnet
        
        # 同时创建WebSocket和REST客户端
        self.ws_client = OKXWebSocketClient(symbol, testnet)
        self.rest_client = OKXRestClient(
            symbol=symbol,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            testnet=testnet
        )
        
    async def get_market_price(self, symbol: str) -> Dict:
        """获取市场价格数据
        
        Args:
            symbol: 交易对，例如 "BTC-USDT"
            
        Returns:
            Dict: {
                "symbol": str,          # 交易对
                "last": float,          # 最新价格
                "best_bid": float,      # 最优买价
                "best_ask": float,      # 最优卖价
                "volume_24h": float,    # 24小时成交量
                "high_24h": float,      # 24小时最高价
                "low_24h": float,       # 24小时最低价
                "timestamp": str        # 时间戳
            }
        """
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
            
        try:
            # 优先使用WebSocket数据
            ticker = await self.ws_client.get_ticker(symbol)
            if not ticker:
                # 如果WebSocket没有数据，使用REST API
                ticker = await self.rest_client.get_ticker(symbol)
                
            if not ticker:
                logger.error(f"获取市场价格失败: 无法获取Ticker数据")
                return None
                
            # 确保返回的数据格式正确
            return {
                "symbol": symbol,
                "last": float(ticker.get("last_price", 0)),
                "best_bid": float(ticker.get("best_bid", 0)),
                "best_ask": float(ticker.get("best_ask", 0)),
                "volume_24h": float(ticker.get("volume_24h", 0)),
                "high_24h": float(ticker.get("high_24h", 0)),
                "low_24h": float(ticker.get("low_24h", 0)),
                "timestamp": ticker.get("timestamp", datetime.now().isoformat())
            }
        except Exception as e:
            logger.error(f"获取市场价格失败: {e}")
            return None
        
    async def get_history_candlesticks(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Candlestick]:
        """获取历史K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: 返回的K线数量限制
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            
        Returns:
            List[Candlestick]: K线数据列表
        """
        try:
            response = await self.rest_client._request(
                'GET',
                '/api/v5/market/history-candles',
                params={
                    'instId': symbol,
                    'bar': interval,
                    'limit': limit,
                    'after': str(start_time) if start_time else None,
                    'before': str(end_time) if end_time else None
                }
            )
            
            if response.get('code') == '0' and response.get('data'):
                return [
                    self.rest_client.parser.parse_candlestick(candle_data, symbol, interval)
                    for candle_data in response['data']
                ]
            return []
        except Exception as e:
            logger.error(f"获取历史K线数据失败: {e}")
            return []
        
    async def get_kline(self, instId: str, bar: str = "1m", limit: str = "100") -> Dict:
        """获取K线数据
        
        Args:
            instId: 产品ID，例如 "BTC-USDT"
            bar: K线周期，例如 "1m", "5m", "15m", "1H", "4H", "1D"
            limit: 返回的结果集数量，最大值为100，默认值为100
            
        Returns:
            Dict: {
                "code": str,    # 状态码，"0"表示成功
                "msg": str,     # 错误信息
                "data": List    # K线数据
            }
        """
        try:
            if instId != self.symbol:
                raise ValueError(f"符号不匹配: {instId} != {self.symbol}")
                
            # 转换时间周期格式
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m",
                "1h": "1H", "4h": "4H", "1d": "1D"
            }
            interval = interval_map.get(bar.lower(), "15m")
                
            # 优先获取WebSocket数据
            candlesticks = await self.ws_client.get_candlesticks(instId, interval, int(limit))
            if not candlesticks:
                # 如果WebSocket没有数据，使用REST API
                candlesticks = await self.rest_client.get_candlesticks(instId, interval, int(limit))
                
            if not candlesticks:
                return {"code": "1", "msg": "获取K线数据失败", "data": []}
                
            data = []
            for candle in candlesticks:
                data.append([
                    int(candle.timestamp.timestamp() * 1000),  # 时间戳
                    str(candle.open),                          # 开盘价
                    str(candle.high),                         # 最高价
                    str(candle.low),                          # 最低价
                    str(candle.close),                        # 收盘价
                    str(candle.volume),                       # 成交量
                ])
                
            # 按时间正序排列
            data.sort(key=lambda x: x[0])
                
            return {
                "code": "0",
                "msg": "",
                "data": data
            }
        except Exception as e:
            return {
                "code": "1",
                "msg": str(e),
                "data": []
            }
        
    async def connect(self) -> bool:
        """连接交易所WebSocket"""
        return await self.ws_client.connect()
        
    async def disconnect(self):
        """断开WebSocket连接"""
        await self.ws_client.disconnect()
        
    async def get_orderbook(self, symbol: str) -> Optional[OrderBook]:
        """获取订单簿"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        # 优先使用WebSocket数据
        orderbook = await self.ws_client.get_orderbook(symbol)
        if not orderbook:
            # 如果WebSocket没有数据，使用REST API
            orderbook = await self.rest_client.get_orderbook(symbol)
        return orderbook
        
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """获取Ticker数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        # 优先使用WebSocket数据
        ticker = await self.ws_client.get_ticker(symbol)
        if not ticker:
            # 如果WebSocket没有数据，使用REST API
            ticker = await self.rest_client.get_ticker(symbol)
        return ticker
        
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """获取最近成交"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        # 优先使用WebSocket数据
        trades = await self.ws_client.get_trades(symbol, limit)
        if not trades:
            # 如果WebSocket没有数据，使用REST API
            trades = await self.rest_client.get_trades(symbol, limit)
        return trades
        
    async def get_candlesticks(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Candlestick]:
        """获取K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: 返回的K线数量限制
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            
        Returns:
            List[Candlestick]: K线数据列表
        """
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
            
        # 优先使用WebSocket数据
        candlesticks = await self.ws_client.get_candlesticks(
            symbol, 
            interval, 
            limit,
            start_time=start_time,
            end_time=end_time
        )
        
        if not candlesticks:
            # 如果WebSocket没有数据，使用REST API
            candlesticks = await self.rest_client.get_candlesticks(
                symbol,
                interval,
                limit,
                start_time=start_time,
                end_time=end_time
            )
            
        return candlesticks
        
    async def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """获取市场数据快照"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
            
        # 优先使用WebSocket数据
        snapshot = await self.ws_client.get_snapshot(symbol)
        if snapshot and snapshot.orderbook and snapshot.ticker:
            return snapshot
            
        # 如果WebSocket数据不完整，使用REST API
        orderbook = await self.rest_client.get_orderbook(symbol)
        ticker = await self.rest_client.get_ticker(symbol)
        trades = await self.rest_client.get_trades(symbol)
        
        return MarketSnapshot(
            symbol=symbol,
            timestamp=orderbook.timestamp if orderbook else None,
            orderbook=orderbook,
            ticker=ticker,
            trades=trades,
            candlesticks={}  # REST API模式下不缓存K线数据
        )
        
    async def subscribe_orderbook(self, symbol: str):
        """订阅订单簿数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        await self.ws_client.subscribe_orderbook(symbol)
        
    async def subscribe_ticker(self, symbol: str):
        """订阅Ticker数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        await self.ws_client.subscribe_ticker(symbol)
        
    async def subscribe_trades(self, symbol: str):
        """订阅成交数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        await self.ws_client.subscribe_trades(symbol)
        
    async def subscribe_candlesticks(self, symbol: str, interval: str):
        """订阅K线数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        await self.ws_client.subscribe_candlesticks(symbol, interval)
        
    # 以下方法都使用REST API
    async def place_order(self, symbol: str, side: str, order_type: str,
                         amount: Decimal, price: Optional[Decimal] = None) -> Dict:
        """下单"""
        if not self.api_key or not self.api_secret:
            raise ValueError("交易功能需要API密钥")
        return await self.rest_client.place_order(symbol, side, order_type, amount, price)
        
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """取消订单"""
        if not self.api_key or not self.api_secret:
            raise ValueError("交易功能需要API密钥")
        return await self.rest_client.cancel_order(symbol, order_id)
        
    async def get_order(self, symbol: str, order_id: str) -> Dict:
        """获取订单信息"""
        if not self.api_key or not self.api_secret:
            raise ValueError("交易功能需要API密钥")
        return await self.rest_client.get_order(symbol, order_id)
        
    async def get_open_orders(self, symbol: str) -> List[Dict]:
        """获取未完成订单"""
        if not self.api_key or not self.api_secret:
            raise ValueError("交易功能需要API密钥")
        return await self.rest_client.get_open_orders(symbol)
        
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """获取账户余额"""
        if not self.api_key or not self.api_secret:
            raise ValueError("账户功能需要API密钥")
        return await self.rest_client.get_account_balance()
        
    async def get_full_history_kline(self, instId: str, bar: str = "1m") -> Dict:
        """获取完整的历史K线数据
        
        Args:
            instId: 产品ID，例如 "BTC-USDT"
            bar: K线周期，例如 "1m", "5m", "15m", "1H", "4H", "1D"
            
        Returns:
            Dict: {
                "code": str,    # 状态码，"0"表示成功
                "msg": str,     # 错误信息
                "data": List    # K线数据
            }
        """
        try:
            if instId != self.symbol:
                raise ValueError(f"符号不匹配: {instId} != {self.symbol}")
                
            # 转换时间周期格式
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m",
                "1h": "1H", "4h": "4H", "1d": "1D"
            }
            interval = interval_map.get(bar.lower(), "15m")
            
            # 计算开始时间（例如：获取过去7天的数据）
            end_time = int(datetime.now().timestamp() * 1000)
            period_seconds = {
                "1m": 60,
                "5m": 300,
                "15m": 900,
                "1h": 3600,
                "4h": 14400,
                "1d": 86400
            }
            seconds = period_seconds.get(bar.lower(), 900)
            # 获取7天的数据
            start_time = end_time - (7 * 24 * 60 * 60 * 1000)
            
            # 使用REST API获取历史数据
            candlesticks = await self.rest_client.get_candlesticks(
                symbol=instId,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=1000  # 获取足够多的数据
            )
            
            if not candlesticks:
                return {"code": "1", "msg": "获取K线数据失败", "data": []}
                
            data = []
            for candle in candlesticks:
                data.append([
                    int(candle.timestamp.timestamp() * 1000),  # 时间戳
                    str(candle.open),                          # 开盘价
                    str(candle.high),                         # 最高价
                    str(candle.low),                          # 最低价
                    str(candle.close),                        # 收盘价
                    str(candle.volume),                       # 成交量
                ])
                
            # 按时间正序排列
            data.sort(key=lambda x: x[0])
                
            # 订阅WebSocket以获取实时更新
            await self.ws_client.subscribe_candlesticks(instId, interval)
                
            return {
                "code": "0",
                "msg": "",
                "data": data
            }
        except Exception as e:
            logger.error(f"获取完整历史K线数据失败: {e}")
            return {
                "code": "1",
                "msg": str(e),
                "data": []
            } 