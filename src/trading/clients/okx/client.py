"""OKX交易所客户端"""

import hmac
import base64
import json
import time
from typing import Dict, Optional, List
from decimal import Decimal
from loguru import logger
import aiohttp
from datetime import datetime
import os
import ssl
from aiohttp import ClientTimeout

from .config import OKXConfig
from .exceptions import (
    OKXError, OKXValidationError,
    OKXAuthenticationError, OKXRequestError
)
from .models import (
    OKXOrderBook, OKXTicker, OKXTrade,
    OKXCandlestick, OKXOrder, OKXBalance
)
from .ws_client import OKXWebSocketClient

class OKXClient:
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
        self.symbol = symbol
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.testnet = testnet
        self.is_logged_in = False  # 添加登录状态跟踪
        self.last_login_time = None  # 记录上次登录时间
        
        # REST API基础URL
        self.rest_url = OKXConfig.REST_TESTNET_URL if testnet else OKXConfig.REST_MAINNET_URL
        
        # 设置代理
        self.use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
        if self.use_proxy:
            self.proxies = {
                'http': os.getenv('HTTP_PROXY'),
                'https': os.getenv('HTTPS_PROXY')
            }
        else:
            self.proxies = None
            
        # 创建WebSocket客户端
        self.ws = OKXWebSocketClient(
            symbol=symbol,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            testnet=testnet
        )
        
        # 配置SSL上下文
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # 创建连接器和session
        self.connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        self.timeout = ClientTimeout(total=30)
        self.session = None
        
    async def _ensure_session(self):
        """确保session已创建"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout
            )
        return self.session

    async def close(self):
        """关闭客户端连接"""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.ws:
            await self.ws.disconnect()
        if self.connector:
            await self.connector.close()
        
    def _get_timestamp(self) -> str:
        """获取ISO格式的时间戳"""
        return datetime.utcnow().isoformat()[:-3] + 'Z'
        
    def _sign(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """生成签名
        
        Args:
            timestamp: ISO格式的时间戳
            method: 请求方法 (GET/POST)
            request_path: 请求路径
            body: 请求体
        """
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("签名需要API密钥")
            
        message = timestamp + method + request_path + (body if body else '')
        mac = hmac.new(
            bytes(self.api_secret, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
        
    async def connect(self) -> bool:
        """连接交易所WebSocket并自动登录"""
        try:
            logger.info("正在连接OKX WebSocket并登录...")
            
            # 连接WebSocket
            connected = await self.ws.connect()
            if not connected:
                logger.error("WebSocket连接失败")
                return False
                
            # 更新登录状态
            self.is_logged_in = self.ws.is_logged_in
            if self.is_logged_in:
                self.last_login_time = datetime.now()
                logger.info("OKX WebSocket连接和登录成功")
            else:
                logger.warning("OKX WebSocket连接成功，但登录状态未确认")
                
            # 订阅基础市场数据
            await self.subscribe_basic_data()
            
            # 如果有API密钥，订阅私有数据
            if self.is_logged_in and all([self.api_key, self.api_secret, self.passphrase]):
                await self.subscribe_private_data()
                
            return connected
        except Exception as e:
            logger.error(f"OKX连接失败: {e}")
            return False
            
    async def ensure_login(self) -> bool:
        """确保已登录状态
        
        如果未登录或登录状态失效，会尝试重新登录
        
        Returns:
            bool: 是否成功确保登录状态
        """
        # 检查WebSocket是否已登录
        if not self.ws.is_connected or not self.ws.is_logged_in:
            logger.info("检测到未登录状态，正在尝试重新连接和登录...")
            return await self.connect()
            
        # 检查登录时间是否已过期（超过10分钟）
        if self.last_login_time and (datetime.now() - self.last_login_time).total_seconds() > 600:
            logger.info("登录状态可能已过期，正在尝试重新登录...")
            await self.disconnect()
            return await self.connect()
            
        return True
    
    async def _request(self, method: str, path: str, **kwargs) -> Dict:
        """发送HTTP请求
        
        在请求前确保已登录状态
        
        Args:
            method: 请求方法
            path: 请求路径
            **kwargs: 其他参数
            
        Returns:
            Dict: 响应数据
        """
        # 如果需要API密钥，确保已登录
        if all([self.api_key, self.api_secret, self.passphrase]):
            # 确保已登录（WebSocket登录状态会影响一些API的连接状态）
            await self.ensure_login()
            
        if not path.startswith('/'):
            path = '/' + path
            
        # 构建完整URL
        url = self.rest_url + path
        logger.debug(f"请求URL: {url}")
        
        # 准备请求数据
        data = kwargs.pop('data', {}) if 'data' in kwargs else {}
        params = kwargs.pop('params', {}) if 'params' in kwargs else {}
        logger.debug(f"请求参数: data={data}, params={params}")
        
        # 添加签名
        timestamp = self._get_timestamp()
        
        # 生成签名
        data_str = json.dumps(data) if data else ''
        sign = self._sign(timestamp, method, path, data_str)
        
        # 设置请求头
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': sign,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        # 添加模拟交易标识
        if self.testnet:
            headers['x-simulated-trading'] = '1'
        
        # 设置代理
        proxy = None
        if self.use_proxy:
            proxy = self.proxies['https']
        
        try:
            session = await self._ensure_session()
            
            if method.upper() == 'GET':
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    proxy=proxy,
                    verify_ssl=False
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"请求失败: status={response.status}, error={error_text}")
                        raise OKXRequestError(f"HTTP {response.status}: {error_text}")
                        
                    result = await response.json()
                    if result.get('code') != '0':
                        error_msg = result.get('msg', 'Unknown error')
                        logger.error(f"API返回错误: code={result.get('code')}, msg={error_msg}")
                        raise OKXError(f"API Error: {error_msg}")
                        
                    return result
                    
            elif method.upper() == 'POST':
                async with session.post(
                    url,
                    json=data,
                    headers=headers,
                    proxy=proxy,
                    verify_ssl=False
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"请求失败: status={response.status}, error={error_text}")
                        raise OKXRequestError(f"HTTP {response.status}: {error_text}")
                        
                    result = await response.json()
                    if result.get('code') != '0':
                        error_msg = result.get('msg', 'Unknown error')
                        logger.error(f"API返回错误: code={result.get('code')}, msg={error_msg}")
                        raise OKXError(f"API Error: {error_msg}")
                        
                    return result
                    
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP请求错误: {str(e)}")
            raise OKXRequestError(f"HTTP请求错误: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {str(e)}")
            raise OKXRequestError(f"JSON解析错误: {str(e)}")
        except Exception as e:
            logger.error(f"请求异常: {str(e)}")
            raise OKXRequestError(f"请求异常: {str(e)}")
            
    async def disconnect(self):
        """断开WebSocket连接"""
        await self.ws.disconnect()
        
    async def subscribe_basic_data(self):
        """订阅基础市场数据"""
        try:
            await self.ws.subscribe_ticker(self.symbol)
            await self.ws.subscribe_orderbook(self.symbol)
            await self.ws.subscribe_trades(self.symbol)
        except Exception as e:
            logger.error(f"订阅基础数据失败: {e}")
            
    async def subscribe_private_data(self):
        """订阅私有数据"""
        try:
            await self.ws.subscribe_orders(self.symbol)
            await self.ws.subscribe_balance()
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
            await self.ws.subscribe_candlesticks(self.symbol, interval)
        except Exception as e:
            logger.error(f"订阅K线数据失败: {e}")
            raise
            
    # 市场数据方法
    async def get_ticker(self) -> Dict:
        """获取市场行情数据"""
        try:
            response = await self._request('GET', '/api/v5/market/ticker', params={'instId': self.symbol})
            if not response or 'data' not in response:
                logger.error("获取市场行情响应格式错误")
                return {}
                
            data = response['data']
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.warning("市场行情数据为空")
                return {}
                
            # OKX返回的是一个列表，我们取第一个数据
            ticker_data = data[0]
            
            # 格式化数据
            return {
                'symbol': self.symbol,
                'last': ticker_data.get('last', '0'),
                'last_price': ticker_data.get('last', '0'),
                'best_bid': ticker_data.get('bidPx', '0'),
                'best_ask': ticker_data.get('askPx', '0'),
                'volume_24h': ticker_data.get('vol24h', '0'),
                'high_24h': ticker_data.get('high24h', '0'),
                'low_24h': ticker_data.get('low24h', '0'),
                'open_24h': ticker_data.get('open24h', '0'),
                'timestamp': datetime.fromtimestamp(int(ticker_data.get('ts', '0')) / 1000).isoformat()
            }
        except Exception as e:
            logger.error(f"获取市场行情失败: {str(e)}")
            return {}
            
    async def get_orderbook(self) -> Optional[OKXOrderBook]:
        """获取订单簿数据"""
        try:
            return await self.ws.get_orderbook(self.symbol)
        except Exception as e:
            logger.error(f"获取订单簿数据失败: {e}")
            return None
            
    async def get_recent_trades(self, limit: int = 100) -> List[OKXTrade]:
        """获取最近成交记录"""
        try:
            return await self.ws.get_trades(self.symbol, limit)
        except Exception as e:
            logger.error(f"获取成交记录失败: {e}")
            return []
            
    async def get_candlesticks(
        self,
        interval: str,
        limit: int = 100
    ) -> List[OKXCandlestick]:
        """获取K线数据
        
        Args:
            interval: K线周期，如 "1m", "5m", "15m", "1h", "4h", "1d"
            limit: 获取数量
        """
        try:
            return await self.ws.get_candlesticks(
                self.symbol,
                interval,
                limit
            )
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return []
            
    async def get_full_history_kline(self, symbol: str, interval: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[OKXCandlestick]:
        """获取完整的历史K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[OKXCandlestick]: K线数据列表
        """
        try:
            if interval not in OKXConfig.INTERVAL_MAP:
                raise OKXValidationError(f"不支持的时间周期: {interval}")
                
            # 构建请求参数
            params = {
                "instId": symbol,
                "bar": OKXConfig.INTERVAL_MAP[interval],
                "limit": "100"  # OKX单次最多返回100条数据
            }
            
            if start_time:
                params["before"] = str(int(start_time.timestamp() * 1000))
            if end_time:
                params["after"] = str(int(end_time.timestamp() * 1000))
                
            # 发送请求获取历史数据
            result = await self._request('GET', '/api/v5/market/history-candles', params=params)
            
            # 解析响应数据
            candlesticks = []
            for item in result:
                # OKX返回的数据格式：[timestamp, open, high, low, close, vol, volCcy]
                candlesticks.append(OKXCandlestick(
                    symbol=symbol,
                    interval=interval,
                    timestamp=datetime.fromtimestamp(int(item[0]) / 1000),
                    open_price=Decimal(item[1]),
                    high_price=Decimal(item[2]),
                    low_price=Decimal(item[3]),
                    close_price=Decimal(item[4]),
                    volume=Decimal(item[5]),
                    quote_volume=Decimal(item[6])
                ))
                
            return candlesticks
            
        except Exception as e:
            logger.error(f"获取历史K线数据失败: {e}")
            return []
            
    # 交易方法
    async def place_order(
        self,
        instId: str,
        tdMode: str,
        side: str,
        ordType: str,
        sz: str,
        px: Optional[str] = None,
        tgtCcy: Optional[str] = None,
        clOrdId: Optional[str] = None,
        tag: Optional[str] = None,
        reduceOnly: Optional[bool] = None,
    ) -> Optional[OKXOrder]:
        """下单
        
        Args:
            instId: 产品ID，如"BTC-USDT"
            tdMode: 交易模式，cash: 现货交易
            side: 订单方向，buy: 买, sell: 卖
            ordType: 订单类型，market: 市价单, limit: 限价单
            sz: 委托数量
            px: 委托价格，仅适用于限价单
            tgtCcy: 市价单委托数量的类型，base_ccy: 交易货币, quote_ccy: 计价货币
            clOrdId: 客户自定义订单ID
            tag: 订单标签
            reduceOnly: 是否仅减仓，true 或 false
        """
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("下单需要API密钥")
            
        try:
            # 按照固定顺序构建请求体
            data = {
                "instId": instId,
                "tdMode": tdMode,
                "side": side,
                "ordType": ordType,
                "sz": sz
            }
            
            # 按照固定顺序添加可选参数
            if px is not None:
                data["px"] = px
            if clOrdId is not None:
                data["clOrdId"] = clOrdId
            if tgtCcy is not None:
                data["tgtCcy"] = tgtCcy
            if tag is not None:
                data["tag"] = tag
            if reduceOnly is not None:
                data["reduceOnly"] = reduceOnly
            
            result = await self._request('POST', OKXConfig.API_PATHS['PLACE_ORDER'], data=data)
            
            if result and len(result) > 0:
                order_data = result[0]
                return OKXOrder(
                    symbol=instId,
                    order_id=order_data['ordId'],
                    client_order_id=order_data.get('clOrdId'),
                    price=Decimal(order_data.get('px', '0')),
                    size=Decimal(order_data['sz']),
                    type=ordType,
                    side=side,
                    status=order_data['state'],
                    timestamp=datetime.fromtimestamp(int(order_data['cTime']) / 1000) if order_data.get('cTime') else datetime.now(),
                    filled_size=Decimal(order_data.get('fillSz', '0')),
                    filled_price=Decimal(order_data['fillPx']) if order_data.get('fillPx') else None,
                    fee=Decimal(order_data['fee']) if order_data.get('fee') else None,
                    fee_currency=order_data.get('feeCcy')
                )
            logger.error("下单失败: 响应数据为空")
            return None
                
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return None
            
    async def cancel_order(self, instId: str, ordId: str) -> bool:
        """取消订单"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("取消订单需要API密钥")
            
        try:
            data = {
                'instId': instId,
                'ordId': ordId
            }
            await self._request('POST', '/api/v5/trade/cancel-order', data=data)
            return True
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False
            
    async def get_order(self, instId: str, ordId: str) -> Optional[OKXOrder]:
        """获取订单信息"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("获取订单信息需要API密钥")
            
        try:
            params = {
                'instId': instId,
                'ordId': ordId
            }
            result = await self._request('GET', '/api/v5/trade/order', params=params)
            
            if result and len(result) > 0:
                order_data = result[0]
                return OKXOrder(
                    order_id=order_data['ordId'],
                    client_order_id=order_data.get('clOrdId'),
                    symbol=instId,
                    side=order_data['side'],
                    type=order_data['ordType'],
                    price=Decimal(order_data['px']) if order_data.get('px') else None,
                    size=Decimal(order_data['sz']),
                    status=order_data['state'],
                    timestamp=datetime.fromtimestamp(int(order_data['cTime']) / 1000)
                )
            return None
            
        except Exception as e:
            logger.error(f"获取订单信息失败: {e}")
            return None
            
    async def get_balance(self) -> Dict[str, OKXBalance]:
        """获取账户余额"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise OKXAuthenticationError("获取余额需要API密钥")
            
        try:
            response = await self._request('GET', '/api/v5/account/balance')
            if not response or 'data' not in response:
                logger.error("获取账户余额响应格式错误")
                return {}
                
            balances = {}
            data = response['data']
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.warning("账户余额数据为空")
                return {}
                
            # OKX返回的是一个列表，我们取第一个账户的数据
            account_data = data[0]
            if 'details' not in account_data:
                logger.error("账户数据格式错误")
                return {}
                
            # 处理每个币种的余额
            for detail in account_data['details']:
                try:
                    currency = detail['ccy']
                    balances[currency] = {
                        'total_equity': detail.get('eq', '0'),
                        'available_balance': detail.get('availBal', '0'),
                        'position_margin': detail.get('frozenBal', '0'),
                        'order_margin': detail.get('ordFrozen', '0'),
                        'unrealized_pnl': detail.get('upl', '0'),
                        'margin_ratio': detail.get('mgnRatio', '0'),
                        'maint_margin_ratio': detail.get('mmr', '0'),
                        'initial_margin_ratio': detail.get('imr', '0')
                    }
                except Exception as e:
                    logger.error(f"处理币种{currency}余额数据失败: {str(e)}")
                    continue
                    
            return balances
        except Exception as e:
            logger.error(f"获取账户余额失败: {str(e)}")
            return {} 