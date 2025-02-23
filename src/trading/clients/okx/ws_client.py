from typing import Dict, Optional, List, Any
from datetime import datetime
from decimal import Decimal
from loguru import logger
import json
import websockets
import asyncio

from src.trading.base.ws_client import WebSocketClient
from src.trading.base.client import ExchangeClient
from src.trading.base.models.market import (
    OrderBook, OrderBookLevel, Ticker, Trade, Candlestick, MarketSnapshot
)
from .parsers import OKXDataParser

class OKXWebSocketClient(WebSocketClient, ExchangeClient):
    """OKX WebSocket客户端"""
    
    def __init__(self, symbol: str, testnet: bool = False):
        self.symbol = symbol
        self.parser = OKXDataParser()
        self.public_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.business_url = "wss://ws.okx.com:8443/ws/v5/business"
        if testnet:
            self.public_url += "?brokerId=9999"
        super().__init__(self.public_url)
        
        # 存储最新数据
        self._orderbook = None
        self._ticker = None
        self._trades = []
        self._candlesticks = {}
        
        # WebSocket连接
        self._public_ws = None
        self._business_ws = None
        
    async def connect(self) -> bool:
        """连接交易所"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 连接公共频道
                self._public_ws = await websockets.connect(self.public_url)
                # 连接业务频道
                self._business_ws = await websockets.connect(self.business_url)
                logger.info("WebSocket连接已建立")
                
                # 启动消息接收任务
                asyncio.create_task(self._receive_messages(self._public_ws))
                asyncio.create_task(self._receive_messages(self._business_ws))
                
                return True
            except Exception as e:
                retry_count += 1
                logger.error(f"WebSocket连接失败 (尝试 {retry_count}/{max_retries}): {e}")
                await asyncio.sleep(1)  # 等待1秒后重试
                
        logger.error("WebSocket连接失败，已达到最大重试次数")
        return False
            
    async def _receive_messages(self, websocket):
        """接收WebSocket消息"""
        try:
            while True:
                message = await websocket.recv()
                logger.debug(f"收到WebSocket消息: {message}")
                await self._process_message(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
        except Exception as e:
            logger.error(f"接收消息时发生错误: {e}")
            
    async def send_message(self, message: Dict, url: str):
        """发送消息到指定的WebSocket URL"""
        try:
            if url == self.public_url and self._public_ws:
                await self._public_ws.send(json.dumps(message))
            elif url == self.business_url and self._business_ws:
                await self._business_ws.send(json.dumps(message))
            else:
                logger.error(f"无效的WebSocket URL: {url}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise
            
    async def disconnect(self):
        """断开连接"""
        if self._public_ws:
            await self._public_ws.close()
        if self._business_ws:
            await self._business_ws.close()
        logger.info("WebSocket连接已断开")
        
    async def _process_message(self, message: Dict):
        """处理接收到的消息"""
        channel = message.get("arg", {}).get("channel", "")
        
        # 所有消息都使用DEBUG级别
        logger.debug(f"收到WebSocket消息: {message}")
        
        try:
            if "event" in message:
                # 处理订阅确认消息
                await self._handle_subscription_message(message)
            elif "arg" in message and "data" in message:
                # 处理数据消息
                channel = message["arg"]["channel"]
                await self._handle_data_message(channel, message["data"])
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            
    async def _handle_subscription_message(self, message: Dict):
        """处理订阅确认消息"""
        try:
            event = message.get("event")
            channel = message.get("arg", {}).get("channel", "")
            
            # 所有订阅消息都使用DEBUG级别
            logger.debug(f"处理订阅消息: event={event}, channel={channel}, message={message}")
            
            if event == "subscribe":
                logger.debug(f"订阅成功: {message}")
            elif event == "unsubscribe":
                logger.debug(f"取消订阅成功: {message}")
            elif event == "error":
                logger.error(f"订阅错误: {message}")
        except Exception as e:
            logger.error(f"处理订阅确认消息时发生错误: {e}")
            
    async def _handle_data_message(self, channel: str, data: List[Dict]):
        """处理数据消息
        
        Args:
            channel: 频道名称
            data: 数据列表
        """
        try:
            if channel.startswith("candle"):
                # 处理K线数据
                interval = channel.split("candle")[1]  # 例如：candle1m -> 1m
                for item in data:
                    try:
                        candlestick = self.parser.parse_candlestick(item, self.symbol, interval)
                        if interval not in self._candlesticks:
                            self._candlesticks[interval] = {}
                        # 使用毫秒级时间戳作为键
                        ts = int(candlestick.timestamp.timestamp() * 1000)
                        self._candlesticks[interval][ts] = candlestick
                    except Exception as e:
                        logger.error(f"解析K线数据失败: {e}, 原始数据={item}")
                        
            elif channel == "books":
                # 处理订单簿数据
                try:
                    orderbook = self.parser.parse_orderbook(data[0], self.symbol)
                    self._orderbook = orderbook
                except Exception as e:
                    logger.error(f"解析订单簿数据失败: {e}, 原始数据={data[0]}")
                    
            elif channel == "tickers":
                # 处理Ticker数据
                try:
                    ticker = self.parser.parse_ticker(data[0], self.symbol)
                    self._ticker = ticker
                except Exception as e:
                    logger.error(f"解析Ticker数据失败: {e}, 原始数据={data[0]}")
                    
            elif channel == "trades":
                # 处理成交数据
                try:
                    for trade_data in data:
                        trade = self.parser.parse_trade(trade_data, self.symbol)
                        self._trades.append(trade)
                    # 只保留最近的100条成交记录
                    self._trades = self._trades[-100:]
                except Exception as e:
                    logger.error(f"解析成交数据失败: {e}, 原始数据={data}")
                    
        except Exception as e:
            logger.error(f"处理WebSocket数据失败: {e}")
            
    async def _subscribe(self, channel: str, **kwargs):
        """实际的订阅操作"""
        subscribe_msg = {
            "op": "subscribe",
            "args": [{
                "channel": channel,
                "instId": self.symbol,
                **kwargs
            }]
        }
        # 添加日志记录
        logger.info(f"订阅请求: URL={self.url}, 参数={subscribe_msg}")
        await self.send_message(subscribe_msg, self.url)
        
    async def _unsubscribe(self, channel: str, **kwargs):
        """实际的取消订阅操作"""
        unsubscribe_msg = {
            "op": "unsubscribe",
            "args": [{
                "channel": channel,
                "instId": self.symbol,
                **kwargs
            }]
        }
        # 添加日志记录
        logger.info(f"取消订阅请求: URL={self.url}, 参数={unsubscribe_msg}")
        await self.send_message(unsubscribe_msg, self.url)
        
    # 实现ExchangeClient接口
    async def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """获取订单簿"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        return self._orderbook
        
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """获取Ticker数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        return self._ticker
        
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """获取最近成交"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        return self._trades[-limit:]
        
    async def get_candlesticks(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Candlestick]:
        """获取K线数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
            
        if interval not in self._candlesticks:
            return []
            
        # 获取所有时间戳
        timestamps = sorted(self._candlesticks[interval].keys(), reverse=True)
        
        # 根据时间范围筛选
        if end_time:
            timestamps = [ts for ts in timestamps if ts <= end_time]
        if start_time:
            timestamps = [ts for ts in timestamps if ts >= start_time]
            
        # 获取指定数量的K线数据
        selected_timestamps = timestamps[:limit]
        
        # 返回K线数据
        candlesticks = [self._candlesticks[interval][ts] for ts in selected_timestamps]
        return candlesticks
        
    async def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """获取市场数据快照"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
            
        # 将字典格式的candlesticks转换为MarketSnapshot需要的格式
        candlesticks_dict = {}
        for interval, data in self._candlesticks.items():
            candlesticks_dict[interval] = list(data.values())
            
        return MarketSnapshot(
            symbol=symbol,
            timestamp=datetime.now(),
            orderbook=self._orderbook,
            ticker=self._ticker,
            trades=self._trades[-10:],  # 最近10条成交
            candlesticks=candlesticks_dict
        )
        
    async def subscribe_orderbook(self, symbol: str):
        """订阅订单簿数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        await self.subscribe("books")
        
    async def subscribe_ticker(self, symbol: str):
        """订阅Ticker数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        await self.subscribe("tickers")
        
    async def subscribe_trades(self, symbol: str):
        """订阅成交数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
        await self.subscribe("trades")
        logger.debug(f"已订阅交易数据: symbol={symbol}")  # 降级为DEBUG
        
    async def subscribe_candlesticks(self, symbol: str, interval: str):
        """订阅K线数据"""
        if symbol != self.symbol:
            raise ValueError(f"符号不匹配: {symbol} != {self.symbol}")
            
        # OKX的K线频道格式为 "candle{bar}"
        # 参考: https://www.okx.com/docs-v5/zh/#websocket-api-public-channel-candlesticks-channel
        interval_map = {
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1H",
            "2h": "2H",
            "4h": "4H",
            "6h": "6H",
            "12h": "12H",
            "1d": "1D",
            "1w": "1W",
            "1M": "1M"
        }
        
        bar = interval_map.get(interval.lower())
        if not bar:
            raise ValueError(f"不支持的时间周期: {interval}")
            
        channel = f"candle{bar}"
        logger.info(f"订阅K线数据: symbol={symbol}, interval={interval}, channel={channel}")
        
        # 初始化该时间周期的K线数据列表
        if interval not in self._candlesticks:
            self._candlesticks[interval] = {}
            
        # 使用业务频道订阅K线数据
        subscribe_msg = {
            "op": "subscribe",
            "args": [{
                "channel": channel,
                "instId": symbol
            }]
        }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 确保WebSocket连接存在
                if not self._business_ws:
                    logger.error("业务WebSocket未连接")
                    await self.connect()
                    
                # 发送订阅请求
                await self.send_message(subscribe_msg, self.business_url)
                logger.info(f"K线数据订阅请求已发送: {subscribe_msg}")
                
                # 等待确认订阅成功
                await asyncio.sleep(1)
                return
                
            except Exception as e:
                retry_count += 1
                logger.error(f"订阅K线数据失败 (尝试 {retry_count}/{max_retries}): {e}")
                await asyncio.sleep(1)
                
        raise Exception("订阅K线数据失败，已达到最大重试次数")

    # 以下方法需要认证，暂不实现
    async def place_order(self, symbol: str, side: str, order_type: str,
                         amount: Decimal, price: Optional[Decimal] = None) -> Dict:
        raise NotImplementedError("交易功能需要认证")
        
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        raise NotImplementedError("交易功能需要认证")
        
    async def get_order(self, symbol: str, order_id: str) -> Dict:
        raise NotImplementedError("交易功能需要认证")
        
    async def get_open_orders(self, symbol: str) -> List[Dict]:
        raise NotImplementedError("交易功能需要认证")
        
    async def get_account_balance(self) -> Dict[str, Decimal]:
        raise NotImplementedError("账户功能需要认证")

    def _parse_orderbook(self, data: Dict, symbol: Optional[str] = None) -> OrderBook:
        """解析订单簿数据"""
        asks = [
            OrderBookLevel(
                price=Decimal(level[0]),
                size=Decimal(level[1]),
                count=int(level[3])
            )
            for level in data["asks"]
            if Decimal(level[1]) > 0  # 只保留数量大于0的订单
        ]
        
        bids = [
            OrderBookLevel(
                price=Decimal(level[0]),
                size=Decimal(level[1]),
                count=int(level[3])
            )
            for level in data["bids"]
            if Decimal(level[1]) > 0  # 只保留数量大于0的订单
        ]
        
        return OrderBook(
            symbol=symbol or self.symbol,  # 如果没有提供symbol，使用当前实例的symbol
            asks=asks,
            bids=bids,
            timestamp=datetime.fromtimestamp(int(data["ts"]) / 1000)
        )
        
    def _parse_ticker(self, data: Dict) -> Ticker:
        """解析Ticker数据"""
        return Ticker(
            symbol=data["instId"],
            last_price=Decimal(data["last"]),
            best_bid=Decimal(data["bidPx"]),
            best_ask=Decimal(data["askPx"]),
            volume_24h=Decimal(data["vol24h"]),
            high_24h=Decimal(data["high24h"]),
            low_24h=Decimal(data["low24h"]),
            timestamp=datetime.fromtimestamp(int(data["ts"]) / 1000)
        )
        
    def _parse_trade(self, data: Dict) -> Trade:
        """解析成交数据"""
        return Trade(
            symbol=data["instId"],
            price=Decimal(data["px"]),
            size=Decimal(data["sz"]),
            side=data["side"],
            timestamp=datetime.fromtimestamp(int(data["ts"]) / 1000),
            trade_id=data.get("tradeId")
        )
        
    def _update_orderbook(self, new_orderbook: OrderBook):
        """更新订单簿数据"""
        # 更新时间戳
        self._orderbook.timestamp = new_orderbook.timestamp
        
        # 更新卖单
        for ask in new_orderbook.asks:
            # 移除数量为0的订单
            if ask.size == 0:
                self._orderbook.asks = [a for a in self._orderbook.asks if a.price != ask.price]
            else:
                # 更新或添加新订单
                updated = False
                for i, existing_ask in enumerate(self._orderbook.asks):
                    if existing_ask.price == ask.price:
                        self._orderbook.asks[i] = ask
                        updated = True
                        break
                if not updated:
                    self._orderbook.asks.append(ask)
                    
        # 更新买单
        for bid in new_orderbook.bids:
            # 移除数量为0的订单
            if bid.size == 0:
                self._orderbook.bids = [b for b in self._orderbook.bids if b.price != bid.price]
            else:
                # 更新或添加新订单
                updated = False
                for i, existing_bid in enumerate(self._orderbook.bids):
                    if existing_bid.price == bid.price:
                        self._orderbook.bids[i] = bid
                        updated = True
                        break
                if not updated:
                    self._orderbook.bids.append(bid)
                    
        # 按价格排序
        self._orderbook.asks.sort(key=lambda x: x.price)
        self._orderbook.bids.sort(key=lambda x: x.price, reverse=True) 