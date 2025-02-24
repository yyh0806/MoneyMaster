"""OKX WebSocket连接管理器"""

import asyncio
import json
import websockets
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from loguru import logger

from .config import OKXConfig
from .exceptions import OKXWebSocketError, OKXConnectionError

class OKXWebSocketManager:
    """OKX WebSocket连接管理器"""
    
    def __init__(self, 
                 url: str,
                 on_message: Callable[[Dict], None],
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None,
                 ping_interval: int = OKXConfig.WS_PING_INTERVAL,
                 reconnect_delay: int = OKXConfig.WS_RECONNECT_DELAY):
        """初始化WebSocket管理器
        
        Args:
            url: WebSocket连接URL
            on_message: 消息处理回调函数
            api_key: API密钥
            api_secret: API密钥对应的密文
            passphrase: API密码
            ping_interval: 心跳间隔（秒）
            reconnect_delay: 重连延迟（秒）
        """
        self.url = url
        self.on_message = on_message
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.ping_interval = ping_interval
        self.reconnect_delay = reconnect_delay
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.should_reconnect = True
        
        self._ping_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self.last_ping_time: Optional[datetime] = None
        
        # 消息处理队列
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._process_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            self.ws = await websockets.connect(self.url)
            self.is_connected = True
            
            # 启动心跳和消息处理任务
            self._ping_task = asyncio.create_task(self._ping_loop())
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._process_task = asyncio.create_task(self._process_loop())
            
            # 重新订阅之前的频道
            await self._resubscribe()
            
            logger.info(f"WebSocket已连接: {self.url}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            self.is_connected = False
            return False
            
    async def disconnect(self):
        """断开WebSocket连接"""
        self.should_reconnect = False
        self.is_connected = False
        
        # 取消所有任务
        for task in [self._ping_task, self._receive_task, self._process_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
        # 关闭WebSocket连接
        if self.ws:
            await self.ws.close()
            self.ws = None
            
        logger.info("WebSocket已断开连接")
        
    async def reconnect(self):
        """重新连接"""
        if not self.should_reconnect:
            return
            
        logger.info(f"尝试重新连接WebSocket，延迟{self.reconnect_delay}秒")
        await asyncio.sleep(self.reconnect_delay)
        
        for attempt in range(OKXConfig.WS_MAX_RETRIES):
            try:
                if await self.connect():
                    return
            except Exception as e:
                logger.error(f"重连尝试 {attempt + 1}/{OKXConfig.WS_MAX_RETRIES} 失败: {e}")
            await asyncio.sleep(self.reconnect_delay)
            
        raise OKXConnectionError("WebSocket重连失败，已达到最大重试次数")
        
    async def send(self, data: Dict):
        """发送消息
        
        Args:
            data: 要发送的消息数据
        """
        if not self.is_connected:
            raise OKXWebSocketError("WebSocket未连接")
            
        try:
            message = json.dumps(data)
            await self.ws.send(message)
            logger.debug(f"已发送消息: {message}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            await self.reconnect()
            
    async def subscribe(self, channel: str, args: Any):
        """订阅频道
        
        Args:
            channel: 频道名称
            args: 订阅参数
        """
        if not self.is_connected:
            raise OKXWebSocketError("WebSocket未连接")
            
        try:
            message = {
                "op": "subscribe",
                "args": args if isinstance(args, list) else [args]
            }
            await self.send(message)
        except Exception as e:
            logger.error(f"订阅失败: {e}")
            raise
            
    async def unsubscribe(self, channel: str, args: Dict[str, Any]):
        """取消订阅频道
        
        Args:
            channel: 频道名称
            args: 订阅参数
        """
        subscription_key = f"{channel}:{json.dumps(args, sort_keys=True)}"
        if subscription_key in self._subscriptions:
            del self._subscriptions[subscription_key]
            
            if self.is_connected:
                await self.send({
                    "op": "unsubscribe",
                    "args": [{"channel": channel, **args}]
                })
                
    async def _ping_loop(self):
        """心跳循环"""
        while self.is_connected:
            try:
                await asyncio.sleep(self.ping_interval)
                await self.ws.ping()
                self.last_ping_time = datetime.now()
                logger.debug("已发送心跳")
            except Exception as e:
                logger.error(f"发送心跳失败: {e}")
                await self.reconnect()
                
    async def _receive_loop(self):
        """消息接收循环"""
        while self.is_connected:
            try:
                message = await self.ws.recv()
                # 将消息放入队列
                await self._message_queue.put(message)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭")
                await self.reconnect()
                break
            except Exception as e:
                logger.error(f"接收消息时发生错误: {e}")
                await self.reconnect()
                
    async def _process_loop(self):
        """消息处理循环"""
        while True:
            try:
                # 从队列获取消息
                message = await self._message_queue.get()
                
                try:
                    data = json.loads(message)
                    await self.on_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"解析消息失败: {e}, message={message}")
                except Exception as e:
                    logger.error(f"处理消息时发生错误: {e}, message={message}")
                finally:
                    self._message_queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"消息处理循环发生错误: {e}")
                await asyncio.sleep(1)
                
    async def _resubscribe(self):
        """重新订阅所有频道"""
        for subscription in self._subscriptions.values():
            try:
                await self.subscribe(subscription["channel"], subscription["args"])
                # 添加短暂延迟，避免请求过于频繁
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"重新订阅失败: channel={subscription['channel']}, error={e}")
                
    def get_subscription_info(self) -> List[Dict[str, Any]]:
        """获取所有订阅信息"""
        return [
            {
                "channel": sub["channel"],
                "args": sub["args"],
                "timestamp": sub["timestamp"].isoformat()
            }
            for sub in self._subscriptions.values()
        ] 