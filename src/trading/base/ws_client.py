import asyncio
import json
from typing import Dict, Optional, Callable, Any
from abc import ABC, abstractmethod
import websockets
from loguru import logger

class WebSocketClient(ABC):
    """WebSocket基础客户端"""
    
    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self.connected = False
        self.callbacks: Dict[str, Callable] = {}
        self._running = False
        self._subscriptions = set()
        
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            self.ws = await websockets.connect(self.url)
            self.connected = True
            logger.info("WebSocket连接成功")
            return True
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return False
            
    async def disconnect(self):
        """断开WebSocket连接"""
        if self.connected and self.ws:
            self._running = False
            await self.ws.close()
            self.connected = False
            self._subscriptions.clear()
            logger.info("WebSocket连接已关闭")
            
    async def send_message(self, message: Dict):
        """发送消息"""
        if not self.connected:
            raise ConnectionError("WebSocket未连接")
        try:
            await self.ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise
            
    async def receive_message(self) -> Optional[Dict]:
        """接收消息"""
        if not self.connected:
            raise ConnectionError("WebSocket未连接")
        try:
            message = await self.ws.recv()
            return json.loads(message)
        except Exception as e:
            logger.error(f"接收消息失败: {e}")
            return None
            
    def register_callback(self, channel: str, callback: Callable[[Dict], Any]):
        """注册回调函数"""
        self.callbacks[channel] = callback
        
    async def _message_handler(self):
        """消息处理循环"""
        self._running = True
        while self._running and self.connected:
            try:
                message = await self.receive_message()
                if message:
                    await self._process_message(message)
            except Exception as e:
                logger.error(f"处理消息失败: {e}")
                await asyncio.sleep(1)  # 错误后等待一段时间再重试
                
    @abstractmethod
    async def _process_message(self, message: Dict):
        """处理接收到的消息"""
        pass
        
    async def start(self):
        """启动WebSocket客户端"""
        if not self.connected:
            await self.connect()
        asyncio.create_task(self._message_handler())
        
    async def subscribe(self, channel: str, **kwargs):
        """订阅频道"""
        subscription = self._get_subscription_key(channel, **kwargs)
        if subscription not in self._subscriptions:
            await self._subscribe(channel, **kwargs)
            self._subscriptions.add(subscription)
            
    async def unsubscribe(self, channel: str, **kwargs):
        """取消订阅"""
        subscription = self._get_subscription_key(channel, **kwargs)
        if subscription in self._subscriptions:
            await self._unsubscribe(channel, **kwargs)
            self._subscriptions.remove(subscription)
            
    @abstractmethod
    async def _subscribe(self, channel: str, **kwargs):
        """实际的订阅操作"""
        pass
        
    @abstractmethod
    async def _unsubscribe(self, channel: str, **kwargs):
        """实际的取消订阅操作"""
        pass
        
    def _get_subscription_key(self, channel: str, **kwargs) -> str:
        """生成订阅键"""
        key_parts = [channel]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return ":".join(key_parts)
        
    @property
    def subscriptions(self) -> set:
        """获取当前的订阅列表"""
        return self._subscriptions.copy() 