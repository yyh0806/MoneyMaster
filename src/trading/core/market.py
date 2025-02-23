from typing import Dict, Optional, List, Callable, Any
from datetime import datetime
from decimal import Decimal
from loguru import logger
import asyncio
from collections import defaultdict

from src.trading.base.models.market import (
    OrderBook, Ticker, Trade, Candlestick, MarketSnapshot
)
from src.trading.clients.okx.ws_client import OKXWebSocketClient

class MarketDataManager:
    """市场数据管理器"""
    
    def __init__(self):
        self._clients: Dict[str, Dict[str, Any]] = {}  # exchange -> {symbol -> client}
        self._snapshots: Dict[str, Dict[str, MarketSnapshot]] = defaultdict(dict)  # exchange -> {symbol -> snapshot}
        self._callbacks = defaultdict(lambda: defaultdict(list))  # exchange -> {symbol -> [callbacks]}
        
    async def add_market(self, exchange: str, symbol: str, testnet: bool = False):
        """添加市场"""
        if exchange not in self._clients:
            self._clients[exchange] = {}
            
        if symbol in self._clients[exchange]:
            logger.warning(f"市场已存在: {exchange}/{symbol}")
            return
            
        # 创建客户端
        client = self._create_client(exchange, testnet)
        self._clients[exchange][symbol] = {
            "client": client,
            "symbol": symbol
        }
        
        # 创建快照
        self._snapshots[exchange][symbol] = MarketSnapshot(
            symbol=symbol,
            timestamp=datetime.now(),
            trades=[],
            candlesticks={}
        )
        
    def _create_client(self, exchange: str, testnet: bool = False):
        """创建交易所客户端"""
        if exchange.lower() == "okx":
            return OKXWebSocketClient(testnet)
        else:
            raise ValueError(f"不支持的交易所: {exchange}")
            
    async def start(self, exchange: str, symbol: str):
        """启动市场数据服务"""
        if exchange not in self._clients or symbol not in self._clients[exchange]:
            raise ValueError(f"市场不存在: {exchange}/{symbol}")
            
        client_info = self._clients[exchange][symbol]
        client = client_info["client"]
        
        try:
            # 连接WebSocket
            await client.connect()
            
            # 注册回调
            await self._setup_callbacks(exchange, symbol)
            
            # 启动消息处理
            await client.start()
            
            logger.info(f"市场数据服务启动成功: {exchange}/{symbol}")
            
        except Exception as e:
            logger.error(f"市场数据服务启动失败: {exchange}/{symbol} - {e}")
            raise
            
    async def stop(self, exchange: str, symbol: str):
        """停止市场数据服务"""
        if exchange in self._clients and symbol in self._clients[exchange]:
            try:
                client = self._clients[exchange][symbol]["client"]
                await client.disconnect()
                logger.info(f"市场数据服务已停止: {exchange}/{symbol}")
            except Exception as e:
                logger.error(f"市场数据服务停止失败: {exchange}/{symbol} - {e}")
                
    async def stop_all(self):
        """停止所有市场数据服务"""
        for exchange in self._clients:
            for symbol in self._clients[exchange]:
                await self.stop(exchange, symbol)
                
    async def _setup_callbacks(self, exchange: str, symbol: str):
        """设置回调函数"""
        client = self._clients[exchange][symbol]["client"]
        
        # 注册订单簿回调
        await client.subscribe("books", instId=symbol)
        client.register_callback("books", 
            lambda msg: self._handle_orderbook(exchange, symbol, msg))
            
        # 注册Ticker回调
        await client.subscribe("tickers", instId=symbol)
        client.register_callback("tickers",
            lambda msg: self._handle_ticker(exchange, symbol, msg))
            
        # 注册成交回调
        await client.subscribe("trades", instId=symbol)
        client.register_callback("trades",
            lambda msg: self._handle_trades(exchange, symbol, msg))
            
    async def _handle_orderbook(self, exchange: str, symbol: str, message: Dict):
        """处理订单簿数据"""
        try:
            if "data" in message and len(message["data"]) > 0:
                client = self._clients[exchange][symbol]["client"]
                orderbook = client._parse_orderbook(message["data"][0])
                
                # 更新快照
                snapshot = self._snapshots[exchange][symbol]
                snapshot.orderbook = orderbook
                snapshot.timestamp = orderbook.timestamp
                
                # 触发回调
                await self._trigger_callbacks(exchange, symbol, "orderbook", orderbook)
                await self._trigger_callbacks(exchange, symbol, "snapshot", snapshot)
                
        except Exception as e:
            logger.error(f"处理订单簿数据失败: {e}")
            
    async def _handle_ticker(self, exchange: str, symbol: str, message: Dict):
        """处理Ticker数据"""
        try:
            if "data" in message and len(message["data"]) > 0:
                client = self._clients[exchange][symbol]["client"]
                ticker = client._parse_ticker(message["data"][0])
                
                # 更新快照
                snapshot = self._snapshots[exchange][symbol]
                snapshot.ticker = ticker
                snapshot.timestamp = ticker.timestamp
                
                # 触发回调
                await self._trigger_callbacks(exchange, symbol, "ticker", ticker)
                await self._trigger_callbacks(exchange, symbol, "snapshot", snapshot)
                
        except Exception as e:
            logger.error(f"处理Ticker数据失败: {e}")
            
    async def _handle_trades(self, exchange: str, symbol: str, message: Dict):
        """处理成交数据"""
        try:
            if "data" in message:
                client = self._clients[exchange][symbol]["client"]
                
                for trade_data in message["data"]:
                    trade = client._parse_trade(trade_data)
                    
                    # 更新快照
                    snapshot = self._snapshots[exchange][symbol]
                    snapshot.trades.append(trade)
                    snapshot.timestamp = trade.timestamp
                    
                    # 保持最近1000条成交记录
                    if len(snapshot.trades) > 1000:
                        snapshot.trades = snapshot.trades[-1000:]
                        
                    # 触发回调
                    await self._trigger_callbacks(exchange, symbol, "trade", trade)
                    await self._trigger_callbacks(exchange, symbol, "snapshot", snapshot)
                    
        except Exception as e:
            logger.error(f"处理成交数据失败: {e}")
            
    async def _trigger_callbacks(self, exchange: str, symbol: str, event: str, data: Any):
        """触发回调函数"""
        callbacks = self._callbacks[exchange][symbol].get(event, [])
        for callback in callbacks:
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
                
    def register_callback(self, exchange: str, symbol: str, event: str, 
                         callback: Callable[[Any], Any]):
        """注册回调函数"""
        self._callbacks[exchange][symbol][event].append(callback)
        
    def get_snapshot(self, exchange: str, symbol: str) -> Optional[MarketSnapshot]:
        """获取市场数据快照"""
        return self._snapshots.get(exchange, {}).get(symbol)
        
    def get_orderbook(self, exchange: str, symbol: str) -> Optional[OrderBook]:
        """获取订单簿"""
        snapshot = self.get_snapshot(exchange, symbol)
        return snapshot.orderbook if snapshot else None
        
    def get_ticker(self, exchange: str, symbol: str) -> Optional[Ticker]:
        """获取Ticker"""
        snapshot = self.get_snapshot(exchange, symbol)
        return snapshot.ticker if snapshot else None
        
    def get_trades(self, exchange: str, symbol: str) -> List[Trade]:
        """获取成交记录"""
        snapshot = self.get_snapshot(exchange, symbol)
        return snapshot.trades.copy() if snapshot else []
        
    def get_mid_price(self, exchange: str, symbol: str) -> Optional[Decimal]:
        """获取中间价格"""
        snapshot = self.get_snapshot(exchange, symbol)
        return snapshot.mid_price if snapshot else None
        
    def get_spread(self, exchange: str, symbol: str) -> Optional[Decimal]:
        """获取买卖价差"""
        snapshot = self.get_snapshot(exchange, symbol)
        return snapshot.spread if snapshot else None 