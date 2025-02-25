"""OKX WebSocket连接管理器"""

import asyncio
import json
import websockets
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from loguru import logger
import hmac
import base64
import requests

from .config import OKXConfig
from .exceptions import OKXWebSocketError, OKXConnectionError, OKXAuthenticationError

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
        self.is_logged_in = False  # 添加登录状态跟踪
        
        self._ping_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self.last_ping_time: Optional[datetime] = None
        self.last_message_time: Optional[datetime] = None  # 添加最后接收消息时间
        
        # 消息处理队列
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._process_task: Optional[asyncio.Task] = None
        
    def _get_timestamp(self) -> str:
        """获取符合OKX要求的时间戳格式
        
        返回整数格式的Unix时间戳，单位为秒
        """
        # OKX要求的格式是整数格式的Unix时间戳（秒）
        now = int(datetime.utcnow().timestamp())
        return str(now)
        
    def _sign(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """生成签名
        
        Args:
            timestamp: 整数格式的Unix时间戳（秒）
            method: 请求方法 (GET/POST)
            request_path: 请求路径
            body: 请求体
            
        Returns:
            str: Base64编码的签名
        """
        if not self.api_secret:
            raise OKXAuthenticationError("缺少API密钥")
            
        message = timestamp + method + request_path + (body or '')
        mac = hmac.new(
            bytes(self.api_secret, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        d = mac.digest()
        return base64.b64encode(d).decode('utf-8')
        
    async def login(self) -> bool:
        """WebSocket API登录
        
        Returns:
            bool: 登录是否成功
        """
        # 如果已经登录成功，直接返回
        if self.is_logged_in:
            logger.info("已经登录，跳过重复登录")
            return True
            
        if not all([self.api_key, self.api_secret, self.passphrase]):
            logger.warning("缺少API密钥，跳过登录")
            return False
            
        try:
            # 获取服务器时间（如果失败会返回本地时间）
            server_time = self._get_server_time()
            logger.info(f"使用登录时间戳: {server_time}")
            
            # 准备登录参数
            sign = self._sign(server_time, 'GET', '/users/self/verify')
            
            # 构建登录消息，确保格式与示例完全匹配
            login_message = {
                "op": "login",
                "args": [{
                    "apiKey": self.api_key,
                    "passphrase": self.passphrase,
                    "timestamp": server_time,
                    "sign": sign
                }]
            }
            
            # 发送登录请求
            await self.send(login_message)
            logger.info("WebSocket登录请求已发送")
            
            # 等待登录响应
            for _ in range(5):  # 最多等待5秒
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    # 检查登录响应
                    if data.get('event') == 'login':
                        if data.get('code') == '0':
                            logger.info("WebSocket登录成功")
                            self.is_logged_in = True  # 标记登录成功
                            return True
                        else:
                            logger.error(f"WebSocket登录失败: {data}")
                            return False
                    elif data.get('event') == 'error':
                        logger.error(f"WebSocket登录错误: {data}")
                        return False
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"处理登录响应时发生错误: {e}")
                    return False
                    
            logger.error("WebSocket登录超时")
            return False
            
        except Exception as e:
            logger.error(f"WebSocket登录失败: {e}")
            return False
            
    def _get_server_time(self) -> str:
        """从OKX REST API获取服务器时间
        
        Returns:
            str: 服务器时间（Unix时间戳，单位秒）
        """
        try:
            # 使用OKX时间同步API
            endpoints = [
                'https://www.okx.com/api/v5/public/time',
                'https://aws.okx.com/api/v5/public/time'  # 备用API
            ]
            
            headers = {
                'User-Agent': 'OKX-Python-SDK',
                'Accept': 'application/json'
            }
            
            for endpoint in endpoints:
                try:
                    response = requests.get(
                        endpoint, 
                        headers=headers,
                        timeout=3,
                        verify=True
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('code') == '0' and 'data' in data:
                            # 返回Unix时间戳（秒）
                            ts = data['data'][0]['ts']
                            # 从毫秒转换为秒
                            timestamp = str(int(int(ts) / 1000))
                            return timestamp
                except Exception as e:
                    logger.warning(f"尝试获取服务器时间失败 ({endpoint}): {e}")
                    continue
                    
            # 如果所有API端点都失败，则获取本地时间
            logger.warning("所有API端点获取服务器时间都失败，使用本地时间")
            return self._get_timestamp()
        except Exception as e:
            logger.error(f"获取服务器时间失败: {e}")
            # 返回本地时间作为后备
            return self._get_timestamp()
        
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            self.ws = await websockets.connect(self.url)
            self.is_connected = True
            self.last_message_time = datetime.now()  # 重置最后消息时间
            
            # 如果有API密钥，先进行登录
            if all([self.api_key, self.api_secret, self.passphrase]):
                login_success = await self.login()
                if not login_success:
                    logger.error("WebSocket登录失败，断开连接")
                    await self.disconnect()
                    return False
            
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
        self.is_logged_in = False  # 重置登录状态
        
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
                
    async def _handle_disconnect(self):
        """处理断开连接"""
        # 先取消所有任务
        for task in [self._ping_task, self._receive_task, self._process_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # 关闭WebSocket连接
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"关闭WebSocket连接失败: {e}")
            finally:
                self.ws = None

        # 重置状态
        self.is_connected = False
        self.is_logged_in = False

        # 如果需要重连
        if self.should_reconnect:
            logger.info(f"尝试重新连接WebSocket，延迟{self.reconnect_delay}秒")
            await asyncio.sleep(self.reconnect_delay)
            await self.connect()

    async def _ping_loop(self):
        """心跳循环"""
        while self.is_connected:
            try:
                # 检查上次消息接收时间，如果超过25秒未收到消息，发送心跳
                if self.last_message_time:
                    time_since_last_message = (datetime.now() - self.last_message_time).total_seconds()
                    if time_since_last_message < 25:
                        # 如果最近收到消息，等待到25秒时再发送ping
                        wait_time = 25 - time_since_last_message
                        await asyncio.sleep(wait_time)
                    
                # 发送ping
                if self.ws and self.is_connected:
                    await self.ws.send('ping')
                    self.last_ping_time = datetime.now()
                    logger.debug("已发送ping心跳")
                    
                    # 不等待pong响应，让消息接收循环处理它
                    # 只需要确保在合理时间内收到任何消息即可
                    await asyncio.sleep(5)  # 等待5秒
                    
                    # 检查是否在发送ping后收到过任何消息
                    if self.last_message_time:
                        time_since_ping = (datetime.now() - self.last_ping_time).total_seconds()
                        if time_since_ping > 10:  # 如果超过10秒没有收到任何消息
                            logger.warning("超过10秒未收到任何消息，可能需要重连")
                            await self._handle_disconnect()
                            break
                            
                # 计算下次ping的等待时间
                next_wait_time = max(5, min(25, self.ping_interval - 5))  # 确保不超过25秒，不少于5秒
                await asyncio.sleep(next_wait_time)
                    
            except asyncio.CancelledError:
                logger.info("心跳循环已取消")
                break
            except Exception as e:
                logger.error(f"发送心跳失败: {e}")
                await self._handle_disconnect()
                break
                
    async def _receive_loop(self):
        """消息接收循环"""
        while True:
            try:
                if not self.is_connected or not self.ws:
                    await asyncio.sleep(0.1)
                    continue

                message = await self.ws.recv()
                await self._message_queue.put(message)
                self.last_message_time = datetime.now()

            except asyncio.CancelledError:
                logger.info("消息接收循环已取消")
                break
            except websockets.ConnectionClosed:
                logger.error("WebSocket连接已关闭")
                await self._handle_disconnect()
                break
            except Exception as e:
                logger.error(f"接收消息时发生错误: {e}")
                await self._handle_disconnect()
                break

    async def _process_loop(self):
        """消息处理循环"""
        while True:
            try:
                # 获取消息
                message = await self._message_queue.get()
                
                # 处理pong响应
                if message == 'pong':
                    logger.debug("从队列中处理pong响应")
                    continue
                    
                # 处理JSON消息
                try:
                    data = json.loads(message)
                    
                    # 设置最后接收消息时间
                    self.last_message_time = datetime.now()
                    
                    # 如果是登录响应，更新登录状态
                    if data.get('event') == 'login':
                        if data.get('code') == '0':
                            self.is_logged_in = True
                        else:
                            self.is_logged_in = False
                            logger.error(f"登录失败: {data}")
                            
                    # 调用消息处理回调
                    if callable(self.on_message):
                        await self.on_message(data)
                except json.JSONDecodeError:
                    # 非JSON消息且不是pong（前面已经过滤了pong）
                    logger.warning(f"收到非JSON消息: {message}")
            except asyncio.CancelledError:
                logger.info("消息处理循环已取消")
                break
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}")
                
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