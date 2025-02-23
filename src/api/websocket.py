from fastapi import WebSocket
from typing import Dict, List
import json
from loguru import logger
import sys
import asyncio
from datetime import datetime
import time

# 配置日志
app_logger = logger.bind(strategy="WebSocket")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.broadcast_queues: Dict[str, asyncio.Queue] = {}  # 每个symbol一个队列
        self._broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_broadcasts = 100
        self.broadcast_semaphore = asyncio.Semaphore(self.max_concurrent_broadcasts)
        self.batch_size = 10  # 批量处理消息数量
        self.batch_timeout = 0.1  # 批量处理超时时间（秒）

    async def start_broadcast_worker(self, symbol: str):
        """为每个symbol启动独立的广播工作器"""
        if symbol not in self._broadcast_tasks or self._broadcast_tasks[symbol].done():
            if symbol not in self.broadcast_queues:
                self.broadcast_queues[symbol] = asyncio.Queue()
            self._broadcast_tasks[symbol] = asyncio.create_task(self._broadcast_worker(symbol))
            app_logger.info(f"{symbol} 广播工作器已启动")

    async def _broadcast_worker(self, symbol: str):
        """处理单个symbol的广播队列"""
        queue = self.broadcast_queues[symbol]
        batch = []
        last_process_time = time.time()

        while True:
            try:
                # 收集批量消息
                try:
                    # 等待第一条消息
                    message, timestamp = await asyncio.wait_for(
                        queue.get(),
                        timeout=self.batch_timeout
                    )
                    batch.append((message, timestamp))

                    # 尝试收集更多消息，但不等待
                    while len(batch) < self.batch_size:
                        try:
                            message, timestamp = queue.get_nowait()
                            batch.append((message, timestamp))
                        except asyncio.QueueEmpty:
                            break

                except asyncio.TimeoutError:
                    if not batch:  # 如果超时且没有消息，继续等待
                        continue

                if batch:
                    async with self.broadcast_semaphore:
                        await self._process_broadcast_batch(batch, symbol)
                    batch = []
                    last_process_time = time.time()

                await asyncio.sleep(0.001)  # 避免CPU过度使用

            except Exception as e:
                app_logger.error(f"广播工作器错误: {e}")
                batch = []  # 清空批次
                await asyncio.sleep(0.1)

    async def _process_broadcast_batch(self, batch: List[tuple], symbol: str):
        """批量处理广播消息"""
        if symbol not in self.active_connections:
            return

        broadcast_start = time.time()
        earliest_timestamp = min(timestamp for _, timestamp in batch)
        latest_message = batch[-1][0]  # 只发送最新的消息

        tasks = []
        disconnected = []

        # 并发发送消息给所有连接
        for connection in self.active_connections[symbol]:
            try:
                task = asyncio.create_task(connection.send_text(latest_message))
                tasks.append(task)
            except Exception as e:
                app_logger.error(f"创建发送任务失败: {e}")
                disconnected.append((connection, symbol))

        if tasks:
            # 使用gather而不是wait，更高效
            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                app_logger.error(f"批量发送消息失败: {e}")

        # 处理断开的连接
        for connection, sym in disconnected:
            await self.disconnect(connection, sym)

        broadcast_end = time.time()
        processing_time = (broadcast_end - earliest_timestamp) * 1000
        broadcast_time = (broadcast_end - broadcast_start) * 1000
        app_logger.info(f"广播性能 - 总延迟: {processing_time:.2f}ms, 广播耗时: {broadcast_time:.2f}ms, 批量大小: {len(batch)}")

    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = []
        self.active_connections[symbol].append(websocket)
        app_logger.info(f"新的WebSocket连接已建立: {symbol}")
        await self.start_broadcast_worker(symbol)

    async def broadcast_to_symbol(self, message: str, symbol: str):
        """广播消息到指定symbol的所有连接"""
        timestamp = time.time()
        if symbol in self.broadcast_queues:
            await self.broadcast_queues[symbol].put((message, timestamp))
        else:
            app_logger.warning(f"未找到 {symbol} 的广播队列")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            app_logger.error(f"发送个人消息失败: {e}")
            # 查找并断开失效的连接
            for symbol, connections in list(self.active_connections.items()):
                if websocket in connections:
                    await self.disconnect(websocket, symbol)
                    break

    async def disconnect(self, websocket: WebSocket, symbol: str):
        """异步断开连接"""
        try:
            if symbol in self.active_connections and websocket in self.active_connections[symbol]:
                self.active_connections[symbol].remove(websocket)
                if not self.active_connections[symbol]:
                    del self.active_connections[symbol]
                    # 清理相关资源
                    if symbol in self._broadcast_tasks:
                        self._broadcast_tasks[symbol].cancel()
                        del self._broadcast_tasks[symbol]
                    if symbol in self.broadcast_queues:
                        del self.broadcast_queues[symbol]
                try:
                    await websocket.close()
                except Exception:
                    pass
                app_logger.info(f"WebSocket连接已断开: {symbol}")
        except Exception as e:
            app_logger.error(f"断开连接时发生错误: {e}")

manager = ConnectionManager()

# 事件处理函数
async def handle_strategy_update(event_type: str, data: dict):
    """处理策略更新事件"""
    if event_type == 'strategy_update':
        try:
            # 添加时间戳
            data['timestamp'] = datetime.now().timestamp()
            
            # 序列化消息
            message = json.dumps(data)
            
            # 广播给所有相关连接
            await manager.broadcast_to_symbol(message, data['symbol'])
            
        except Exception as e:
            app_logger.error(f"处理策略更新事件失败: {e}")

# 在应用启动时订阅事件
def setup_event_handlers():
    """设置事件处理器"""
    from src.trading.core.strategy import event_bus
    event_bus.subscribe(handle_strategy_update) 