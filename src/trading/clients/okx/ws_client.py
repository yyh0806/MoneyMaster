from typing import Dict, Optional, List, Any
from datetime import datetime
from decimal import Decimal
from collections import OrderedDict
from loguru import logger
import json
import websockets
import asyncio

from .parsers import OKXDataParser
from .config import OKXConfig
from .exceptions import (
    OKXWebSocketError, OKXConnectionError,
    OKXValidationError, OKXParseError,
    OKXAuthenticationError
)
from .models import (
    OKXOrderBook, OKXOrderBookLevel, OKXTicker,
    OKXTrade, OKXCandlestick, OKXMarketSnapshot,
    OKXOrder, OKXBalance
)
from .ws_manager import OKXWebSocketManager

class OKXWebSocketClient:
    """OKX WebSocket客户端"""
    
    def __init__(self, 
                 symbol: str, 
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None,
                 testnet: bool = False):
        """初始化WebSocket客户端
        
        Args:
            symbol: 交易对
            api_key: API密钥
            api_secret: API密钥对应的密文
            passphrase: API密码
            testnet: 是否使用测试网
        """
        self.symbol = symbol
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.parser = OKXDataParser()
        
        # 创建WebSocket管理器
        self._ws_public = OKXWebSocketManager(
            url=OKXConfig.WS_PUBLIC_TESTNET if testnet else OKXConfig.WS_PUBLIC_MAINNET,
            on_message=self._handle_public_message,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase
        )
        
        self._ws_private = OKXWebSocketManager(
            url=OKXConfig.WS_PRIVATE_TESTNET if testnet else OKXConfig.WS_PRIVATE_MAINNET,
            on_message=self._handle_private_message,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase
        )
        
        self._ws_business = OKXWebSocketManager(
            url=OKXConfig.WS_BUSINESS_TESTNET if testnet else OKXConfig.WS_BUSINESS_MAINNET,
            on_message=self._handle_business_message,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase
        )
        
        # 存储最新数据
        self._orderbook: Optional[OKXOrderBook] = None
        self._ticker: Optional[OKXTicker] = None
        self._trades: OrderedDict[str, OKXTrade] = OrderedDict()
        self._candlesticks: Dict[str, OrderedDict[int, OKXCandlestick]] = {}
        
    async def connect(self) -> bool:
        """连接WebSocket"""
        try:
            public_connected = await self._ws_public.connect()
            private_connected = await self._ws_private.connect()
            business_connected = await self._ws_business.connect()
            return public_connected and private_connected and business_connected
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return False
            
    async def disconnect(self):
        """断开WebSocket连接"""
        await self._ws_public.disconnect()
        await self._ws_private.disconnect()
        await self._ws_business.disconnect()
        
    async def _handle_public_message(self, message: Dict):
        """处理公共频道消息"""
        try:
            if "event" in message:
                await self._handle_subscription_message(message)
                return
                
            channel = message.get("arg", {}).get("channel")
            if not channel:
                return
                
            data = message.get("data", [])
            if not data:
                return
                
            if channel == OKXConfig.TOPICS["TICKER"]:
                await self._handle_ticker(data[0])
            elif channel == OKXConfig.TOPICS["ORDERBOOK"]:
                await self._handle_orderbook(data[0])
            elif channel == OKXConfig.TOPICS["TRADES"]:
                await self._handle_trades(data)
                
        except Exception as e:
            logger.error(f"处理公共消息失败: {e}")
            
    async def _handle_business_message(self, message: Dict):
        """处理业务频道消息"""
        try:
            if "event" in message:
                await self._handle_subscription_message(message)
                return
                
            channel = message.get("arg", {}).get("channel")
            if not channel or not channel.startswith(OKXConfig.TOPICS["CANDLE"]):
                return
                
            data = message.get("data", [])
            if not data:
                return
                
            await self._handle_candlestick(channel, data[0])
                
        except Exception as e:
            logger.error(f"处理业务消息失败: {e}")
            
    async def _handle_subscription_message(self, message: Dict):
        """处理订阅消息"""
        event = message.get("event")
        channel = message.get("arg", {}).get("channel", "")
        
        if event == "subscribe":
            logger.info(f"订阅成功: {channel}")
        elif event == "unsubscribe":
            logger.info(f"取消订阅成功: {channel}")
        elif event == "error":
            logger.error(f"订阅错误: {message}")
            
    async def _handle_ticker(self, data: Dict):
        """处理Ticker数据"""
        try:
            self._ticker = OKXTicker(
                symbol=self.symbol,
                last_price=Decimal(data['last']),
                best_bid=Decimal(data['bidPx']),
                best_ask=Decimal(data['askPx']),
                volume_24h=Decimal(data['vol24h']),
                high_24h=Decimal(data['high24h']),
                low_24h=Decimal(data['low24h']),
                timestamp=datetime.fromtimestamp(int(data['ts']) / 1000),
                open_24h=Decimal(data.get('open24h', '0')),
                price_change_24h=Decimal(data.get('priceChange24h', '0')),
                price_change_percent_24h=float(data.get('priceChangePercent24h', '0'))
            )
        except Exception as e:
            raise OKXParseError("Ticker", str(data), str(e))
            
    async def _handle_orderbook(self, data: Dict):
        """处理订单簿数据"""
        try:
            asks = []
            bids = []
            
            # 处理卖单
            for level in data.get('asks', []):
                if len(level) >= 2 and Decimal(level[1]) > 0:
                    asks.append(OKXOrderBookLevel(
                        price=Decimal(level[0]),
                        size=Decimal(level[1]),
                        count=int(level[2]) if len(level) > 2 else 0
                    ))
            
            # 处理买单
            for level in data.get('bids', []):
                if len(level) >= 2 and Decimal(level[1]) > 0:
                    bids.append(OKXOrderBookLevel(
                        price=Decimal(level[0]),
                        size=Decimal(level[1]),
                        count=int(level[2]) if len(level) > 2 else 0
                    ))
            
            self._orderbook = OKXOrderBook(
                symbol=self.symbol,
                asks=asks,
                bids=bids,
                timestamp=datetime.fromtimestamp(int(data['ts']) / 1000),
                checksum=int(data.get('checksum', 0))
            )
            logger.debug(f"更新订单簿: asks={len(asks)}个, bids={len(bids)}个")
        except Exception as e:
            logger.error(f"处理订单簿数据失败: {e}, data={data}")
            raise OKXParseError("OrderBook", str(data), str(e))
            
    async def _handle_trades(self, data_list: List[Dict]):
        """处理成交数据"""
        try:
            for data in data_list:
                trade = OKXTrade(
                    symbol=self.symbol,
                    price=Decimal(data['px']),
                    size=Decimal(data['sz']),
                    side=data['side'],
                    timestamp=datetime.fromtimestamp(int(data['ts']) / 1000),
                    trade_id=data['tradeId'],
                    maker_order_id=data.get('makerOrderId'),
                    taker_order_id=data.get('takerOrderId')
                )
                self._trades[trade.trade_id] = trade
                
                # 保持最大缓存数量
                while len(self._trades) > OKXConfig.MAX_TRADE_CACHE:
                    self._trades.popitem(last=False)
                    
        except Exception as e:
            raise OKXParseError("Trade", str(data_list), str(e))
            
    async def _handle_candlestick(self, channel: str, data: List):
        """处理K线数据"""
        try:
            # 从channel中提取时间周期
            interval = channel.replace(OKXConfig.TOPICS["CANDLE"], "")
            
            candlestick = OKXCandlestick(
                symbol=self.symbol,
                interval=interval,
                timestamp=datetime.fromtimestamp(int(data[0]) / 1000),
                open=Decimal(data[1]),
                high=Decimal(data[2]),
                low=Decimal(data[3]),
                close=Decimal(data[4]),
                volume=Decimal(data[5]),
                volume_currency=Decimal(data[6]) if len(data) > 6 else None,
                trades_count=int(data[7]) if len(data) > 7 else None
            )
            
            # 初始化时间周期的缓存
            if interval not in self._candlesticks:
                self._candlesticks[interval] = OrderedDict()
                
            # 使用时间戳作为键存储K线数据
            ts = int(candlestick.timestamp.timestamp() * 1000)
            self._candlesticks[interval][ts] = candlestick
            
            # 保持最大缓存数量
            while len(self._candlesticks[interval]) > OKXConfig.MAX_KLINE_CACHE:
                self._candlesticks[interval].popitem(last=False)
                
        except Exception as e:
            raise OKXParseError("Candlestick", str(data), str(e))
            
    async def subscribe_basic_data(self):
        """订阅基础市场数据"""
        try:
            await self.subscribe_ticker(self.symbol)
            await self.subscribe_orderbook(self.symbol)
            await self.subscribe_trades(self.symbol)
        except Exception as e:
            logger.error(f"订阅基础数据失败: {e}")
            
    async def subscribe_private_data(self):
        """订阅私有数据"""
        try:
            await self.subscribe_orders(self.symbol)
            await self.subscribe_balance()
        except Exception as e:
            logger.error(f"订阅私有数据失败: {e}")
            
    async def subscribe_kline(self, interval: str):
        """订阅K线数据
        
        Args:
            interval: K线周期，如 "1m", "5m", "15m", "1h", "4h", "1d"
        """
        try:
            if interval not in OKXConfig.INTERVAL_MAP:
                raise OKXValidationError(f"不支持的时间周期: {interval}")
            await self.subscribe_candlesticks(self.symbol, interval)
        except Exception as e:
            logger.error(f"订阅K线数据失败: {e}")
            raise
            
    async def subscribe_ticker(self, symbol: str):
        """订阅Ticker数据"""
        if symbol != self.symbol:
            raise OKXValidationError(f"符号不匹配: {symbol} != {self.symbol}")
        await self._ws_public.subscribe("tickers", [{
            "channel": "tickers",
            "instId": symbol
        }])
        
    async def subscribe_trades(self, symbol: str):
        """订阅成交数据"""
        if symbol != self.symbol:
            raise OKXValidationError(f"符号不匹配: {symbol} != {self.symbol}")
        await self._ws_public.subscribe("trades", [{
            "channel": "trades",
            "instId": symbol
        }])
        
    async def subscribe_orderbook(self, symbol: str):
        """订阅订单簿数据"""
        if symbol != self.symbol:
            raise OKXValidationError(f"符号不匹配: {symbol} != {self.symbol}")
        await self._ws_public.subscribe("books", [{
            "channel": "books",
            "instId": symbol
        }])
        
    async def subscribe_orders(self, symbol: str):
        """订阅订单更新"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("订阅订单需要API密钥")
        await self._ws_private.subscribe(OKXConfig.TOPICS["ORDERS"], [{
            "channel": OKXConfig.TOPICS["ORDERS"],
            "instType": "SPOT",
            "instId": symbol,
            "algoId": ""
        }])
        
    async def subscribe_balance(self):
        """订阅账户余额更新"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("订阅余额需要API密钥")
        await self._ws_business.subscribe("account", [{
            "channel": "account",
        }])
        
    async def subscribe_account(self):
        """订阅账户信息更新"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("订阅账户信息需要API密钥")
        await self._ws_business.subscribe("account", [{
            "channel": "account",
            "ccy": ["BTC","USDT"]
        }])
        
    async def get_orderbook(self, symbol: str) -> Optional[OKXOrderBook]:
        """获取订单簿"""
        if symbol != self.symbol:
            raise OKXValidationError(f"符号不匹配: {symbol} != {self.symbol}")
        return self._orderbook
        
    async def get_ticker(self, symbol: str) -> Optional[OKXTicker]:
        """获取Ticker数据"""
        if symbol != self.symbol:
            raise OKXValidationError(f"符号不匹配: {symbol} != {self.symbol}")
        return self._ticker
        
    async def get_trades(self, symbol: str, limit: int = 100) -> List[OKXTrade]:
        """获取最近成交"""
        if symbol != self.symbol:
            raise OKXValidationError(f"符号不匹配: {symbol} != {self.symbol}")
        return list(self._trades.values())[-limit:]
        
    async def get_candlesticks(self, symbol: str, interval: str, limit: int = 100) -> List[OKXCandlestick]:
        """获取K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: 获取数量
            
        Returns:
            List[OKXCandlestick]: K线数据列表
        """
        if symbol != self.symbol:
            raise OKXValidationError(f"符号不匹配: {symbol} != {self.symbol}")
            
        if interval not in OKXConfig.INTERVAL_MAP:
            raise OKXValidationError(f"不支持的时间周期: {interval}")
            
        candlesticks = []
        if interval in self._candlesticks:
            candlesticks = list(self._candlesticks[interval].values())[-limit:]
        return candlesticks
        
    async def get_snapshot(self, symbol: str) -> OKXMarketSnapshot:
        """获取市场数据快照"""
        if symbol != self.symbol:
            raise OKXValidationError(f"符号不匹配: {symbol} != {self.symbol}")
            
        return OKXMarketSnapshot(
            symbol=symbol,
            timestamp=datetime.now(),
            orderbook=self._orderbook,
            ticker=self._ticker,
            trades=list(self._trades.values())[-10:],  # 最近10条成交
            candlesticks={
                interval: list(candles.values())
                for interval, candles in self._candlesticks.items()
            }
        )

    async def _process_message(self, message: Dict):
        """处理接收到的消息"""
        try:
            if "event" in message:
                await self._handle_subscription_message(message)
                return
                
            channel = message.get("arg", {}).get("channel")
            if not channel:
                return
                
            data = message.get("data", [])
            if not data:
                return
                
            if channel == OKXConfig.TOPICS["TICKER"]:
                await self._handle_ticker(data[0])
            elif channel == OKXConfig.TOPICS["ORDERBOOK"]:
                await self._handle_orderbook(data[0])
            elif channel == OKXConfig.TOPICS["TRADES"]:
                await self._handle_trades(data)
            elif channel.startswith(OKXConfig.TOPICS["CANDLE"]):
                await self._handle_candlestick(channel, data[0])
                
        except Exception as e:
            logger.error(f"处理消息失败: {e}")

    async def _subscribe(self, channel: str, **kwargs):
        """实际的订阅操作"""
        try:
            if channel.startswith(OKXConfig.TOPICS["CANDLE"]):
                await self._ws_business.subscribe(channel, kwargs)
            else:
                await self._ws_public.subscribe(channel, kwargs)
        except Exception as e:
            logger.error(f"订阅失败: channel={channel}, kwargs={kwargs}, error={e}")
            raise

    async def _unsubscribe(self, channel: str, **kwargs):
        """实际的取消订阅操作"""
        try:
            if channel.startswith(OKXConfig.TOPICS["CANDLE"]):
                await self._ws_business.unsubscribe(channel, kwargs)
            else:
                await self._ws_public.unsubscribe(channel, kwargs)
        except Exception as e:
            logger.error(f"取消订阅失败: channel={channel}, kwargs={kwargs}, error={e}")
            raise

    async def get_balance(self) -> Dict[str, OKXBalance]:
        """获取账户余额"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("获取余额需要API密钥")
        # TODO: 实现余额获取逻辑
        return {}
        
    async def place_order(self,
                         symbol: str,
                         side: str,
                         order_type: str,
                         amount: Decimal,
                         price: Optional[Decimal] = None,
                         client_order_id: Optional[str] = None) -> Optional[OKXOrder]:
        """下单
        
        Args:
            symbol: 交易对
            side: 订单方向 (buy/sell)
            order_type: 订单类型 (limit/market)
            amount: 数量
            price: 价格（市价单可选）
            client_order_id: 客户端订单ID
        """
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("下单需要API密钥")
            
        # TODO: 实现下单逻辑
        return None
        
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """取消订单"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("取消订单需要API密钥")
            
        # TODO: 实现取消订单逻辑
        return False
        
    async def get_order(self, symbol: str, order_id: str) -> Optional[OKXOrder]:
        """获取订单信息"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("获取订单信息需要API密钥")
            
        # TODO: 实现获取订单信息逻辑
        return None
        
    async def get_open_orders(self, symbol: str) -> List[OKXOrder]:
        """获取未完成订单"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("获取未完成订单需要API密钥")
            
        # TODO: 实现获取未完成订单逻辑
        return []

    async def subscribe_candlesticks(self, symbol: str, interval: str):
        """订阅K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
        """
        await self._ws_public.subscribe("candle", [{
            "channel": f"candle{interval}",
            "instId": symbol
        }])

    async def _handle_private_message(self, message: Dict):
        """处理私有频道消息"""
        try:
            if 'event' in message:
                await self._handle_subscription_message(message)
            else:
                channel = message.get('arg', {}).get('channel')
                if channel == 'orders':
                    await self._handle_order_update(message)
                elif channel == 'account':
                    await self._handle_account_update(message)
        except Exception as e:
            logger.error(f"处理私有消息失败: {e}")
            
    async def _handle_order_update(self, message: Dict):
        """处理订单更新消息"""
        try:
            data = message.get('data', [])
            for order_data in data:
                order = self.parser.parse_order(order_data)
                logger.info(f"订单更新: {order.order_id}, 状态: {order.status}")
        except Exception as e:
            logger.error(f"处理订单更新失败: {e}")
            
    async def _handle_account_update(self, message: Dict):
        """处理账户更新消息"""
        try:
            data = message.get('data', [])
            for balance_data in data:
                balance = self.parser.parse_balance(balance_data)
                logger.info(f"账户余额更新: {balance.currency}, 可用: {balance.available}")
        except Exception as e:
            logger.error(f"处理账户更新失败: {e}") 