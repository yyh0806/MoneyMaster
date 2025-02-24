"""OKX REST API客户端"""

import hmac
import base64
import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, List, Any
import aiohttp
from loguru import logger

from .config import OKXConfig
from .exceptions import (
    OKXAPIError, OKXConnectionError, OKXTimeoutError,
    OKXAuthenticationError, OKXValidationError
)
from .models import (
    OKXOrderBook, OKXOrderBookLevel, OKXTicker,
    OKXTrade, OKXCandlestick, OKXBalance, OKXOrder
)

class OKXRESTBase:
    """OKX REST API基类"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None,
                 testnet: bool = False):
        """初始化REST API基类
        
        Args:
            api_key: API密钥
            api_secret: API密钥对应的密文
            passphrase: API密码
            testnet: 是否使用测试网
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.testnet = testnet
        self.base_url = OKXConfig.REST_TESTNET_URL if testnet else OKXConfig.REST_MAINNET_URL
        
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
            
        Returns:
            str: Base64编码的签名
        """
        if not self.api_secret:
            return ''
            
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.api_secret, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode('utf-8')
        
    async def _request(self, 
                      method: str, 
                      path: str, 
                      params: Optional[Dict] = None, 
                      data: Optional[Dict] = None,
                      auth: bool = False) -> Dict:
        """发送HTTP请求
        
        Args:
            method: 请求方法 (GET/POST)
            path: API路径
            params: URL参数
            data: POST数据
            auth: 是否需要认证
            
        Returns:
            Dict: API响应
            
        Raises:
            OKXConnectionError: 连接错误
            OKXTimeoutError: 请求超时
            OKXAPIError: API错误
        """
        url = f"{self.base_url}{path}"
        headers = {
            'Content-Type': 'application/json'
        }
        
        if auth:
            if not all([self.api_key, self.api_secret, self.passphrase]):
                raise OKXAuthenticationError("缺少API认证信息")
                
            timestamp = self._get_timestamp()
            body = json.dumps(data) if data else ''
            sign = self._sign(timestamp, method, path, body)
            
            headers.update({
                'OK-ACCESS-KEY': self.api_key,
                'OK-ACCESS-SIGN': sign,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': self.passphrase
            })
            
        try:
            timeout = aiohttp.ClientTimeout(total=OKXConfig.REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        raise OKXAPIError(
                            code=str(response.status),
                            message=result.get('msg', '未知错误')
                        )
                        
                    if result.get('code') != OKXConfig.SUCCESS_CODE:
                        raise OKXAPIError(
                            code=result.get('code', '-1'),
                            message=result.get('msg', '未知错误')
                        )
                        
                    return result
                    
        except aiohttp.ClientTimeout:
            raise OKXTimeoutError(timeout=OKXConfig.REQUEST_TIMEOUT)
        except aiohttp.ClientError as e:
            raise OKXConnectionError(f"连接错误: {str(e)}")
        except Exception as e:
            logger.error(f"请求失败: {e}")
            raise

class OKXMarketAPI(OKXRESTBase):
    """OKX市场数据API"""
    
    async def get_ticker(self, symbol: str) -> OKXTicker:
        """获取Ticker数据
        
        Args:
            symbol: 交易对
            
        Returns:
            OKXTicker: Ticker数据对象
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/market/ticker',
                params={'instId': symbol}
            )
            
            if not response.get('data'):
                raise OKXValidationError(f"无效的交易对: {symbol}")
                
            data = response['data'][0]
            return OKXTicker(
                symbol=symbol,
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
        except (OKXAPIError, OKXValidationError):
            raise
        except Exception as e:
            logger.error(f"获取Ticker数据失败: {e}")
            raise
            
    async def get_orderbook(self, symbol: str, depth: int = 20) -> OKXOrderBook:
        """获取订单簿
        
        Args:
            symbol: 交易对
            depth: 深度
            
        Returns:
            OKXOrderBook: 订单簿对象
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/market/books',
                params={
                    'instId': symbol,
                    'sz': depth
                }
            )
            
            if not response.get('data'):
                raise OKXValidationError(f"无效的交易对: {symbol}")
                
            data = response['data'][0]
            
            asks = [
                OKXOrderBookLevel(
                    price=Decimal(level[0]),
                    size=Decimal(level[1]),
                    count=int(level[3]) if len(level) > 3 else 0
                )
                for level in data['asks']
                if Decimal(level[1]) > 0
            ]
            
            bids = [
                OKXOrderBookLevel(
                    price=Decimal(level[0]),
                    size=Decimal(level[1]),
                    count=int(level[3]) if len(level) > 3 else 0
                )
                for level in data['bids']
                if Decimal(level[1]) > 0
            ]
            
            return OKXOrderBook(
                symbol=symbol,
                asks=asks,
                bids=bids,
                timestamp=datetime.fromtimestamp(int(data['ts']) / 1000),
                checksum=int(data.get('checksum', 0))
            )
        except (OKXAPIError, OKXValidationError):
            raise
        except Exception as e:
            logger.error(f"获取订单簿失败: {e}")
            raise
            
    async def get_trades(self, symbol: str, limit: int = 100) -> List[OKXTrade]:
        """获取最近成交
        
        Args:
            symbol: 交易对
            limit: 返回的成交数量
            
        Returns:
            List[OKXTrade]: 成交记录列表
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/market/trades',
                params={
                    'instId': symbol,
                    'limit': limit
                }
            )
            
            if not response.get('data'):
                return []
                
            trades = []
            for trade_data in response['data']:
                trades.append(OKXTrade(
                    symbol=symbol,
                    price=Decimal(trade_data['px']),
                    size=Decimal(trade_data['sz']),
                    side=trade_data['side'],
                    timestamp=datetime.fromtimestamp(int(trade_data['ts']) / 1000),
                    trade_id=trade_data['tradeId'],
                    maker_order_id=trade_data.get('makerOrderId'),
                    taker_order_id=trade_data.get('takerOrderId')
                ))
            return trades
        except Exception as e:
            logger.error(f"获取成交记录失败: {e}")
            return []
            
    async def get_candlesticks(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[OKXCandlestick]:
        """获取K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: 返回的K线数量限制
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            
        Returns:
            List[OKXCandlestick]: K线数据列表
        """
        try:
            bar = OKXConfig.INTERVAL_MAP.get(interval.lower())
            if not bar:
                raise OKXValidationError(f"不支持的时间周期: {interval}")
                
            params = {
                'instId': symbol,
                'bar': bar,
                'limit': limit
            }
            
            if start_time:
                params['after'] = str(start_time)
            if end_time:
                params['before'] = str(end_time)
                
            response = await self._request(
                'GET',
                '/api/v5/market/candles',
                params=params
            )
            
            if not response.get('data'):
                return []
                
            candlesticks = []
            for candle_data in response['data']:
                candlesticks.append(OKXCandlestick(
                    symbol=symbol,
                    interval=interval,
                    timestamp=datetime.fromtimestamp(int(candle_data[0]) / 1000),
                    open=Decimal(candle_data[1]),
                    high=Decimal(candle_data[2]),
                    low=Decimal(candle_data[3]),
                    close=Decimal(candle_data[4]),
                    volume=Decimal(candle_data[5]),
                    volume_currency=Decimal(candle_data[6]) if len(candle_data) > 6 else None,
                    trades_count=int(candle_data[7]) if len(candle_data) > 7 else None
                ))
            return candlesticks
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return []

class OKXTradeAPI(OKXRESTBase):
    """OKX交易API"""
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Optional[Decimal] = None
    ) -> OKXOrder:
        """下单
        
        Args:
            symbol: 交易对
            side: 订单方向 (buy/sell)
            order_type: 订单类型 (limit/market)
            amount: 数量
            price: 价格（市价单可选）
            
        Returns:
            OKXOrder: 订单信息
        """
        try:
            data = {
                'instId': symbol,
                'tdMode': 'cash',
                'side': side.lower(),
                'ordType': order_type.lower(),
                'sz': str(amount)
            }
            
            if price:
                data['px'] = str(price)
                
            response = await self._request(
                'POST',
                '/api/v5/trade/order',
                data=data,
                auth=True
            )
            
            order_data = response['data'][0]
            return OKXOrder(
                symbol=symbol,
                order_id=order_data['ordId'],
                client_order_id=order_data.get('clOrdId'),
                price=price or Decimal('0'),
                size=amount,
                type=order_type,
                side=side,
                status=order_data['state'],
                timestamp=datetime.fromtimestamp(int(order_data['ts']) / 1000)
            )
        except Exception as e:
            logger.error(f"下单失败: {e}")
            raise
            
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """取消订单
        
        Args:
            symbol: 交易对
            order_id: 订单ID
            
        Returns:
            bool: 是否成功
        """
        try:
            response = await self._request(
                'POST',
                '/api/v5/trade/cancel-order',
                data={
                    'instId': symbol,
                    'ordId': order_id
                },
                auth=True
            )
            return True
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False
            
    async def get_order(self, symbol: str, order_id: str) -> Optional[OKXOrder]:
        """获取订单信息
        
        Args:
            symbol: 交易对
            order_id: 订单ID
            
        Returns:
            Optional[OKXOrder]: 订单信息
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/trade/order',
                params={
                    'instId': symbol,
                    'ordId': order_id
                },
                auth=True
            )
            
            if not response.get('data'):
                return None
                
            order_data = response['data'][0]
            return OKXOrder(
                symbol=symbol,
                order_id=order_data['ordId'],
                client_order_id=order_data.get('clOrdId'),
                price=Decimal(order_data['px']),
                size=Decimal(order_data['sz']),
                type=order_data['ordType'],
                side=order_data['side'],
                status=order_data['state'],
                timestamp=datetime.fromtimestamp(int(order_data['ts']) / 1000),
                filled_size=Decimal(order_data.get('fillSz', '0')),
                filled_price=Decimal(order_data['fillPx']) if order_data.get('fillPx') else None,
                fee=Decimal(order_data['fee']) if order_data.get('fee') else None,
                fee_currency=order_data.get('feeCcy')
            )
        except Exception as e:
            logger.error(f"获取订单信息失败: {e}")
            return None
            
    async def get_open_orders(self, symbol: str) -> List[OKXOrder]:
        """获取未完成订单
        
        Args:
            symbol: 交易对
            
        Returns:
            List[OKXOrder]: 订单列表
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/trade/orders-pending',
                params={'instId': symbol},
                auth=True
            )
            
            orders = []
            for order_data in response.get('data', []):
                orders.append(OKXOrder(
                    symbol=symbol,
                    order_id=order_data['ordId'],
                    client_order_id=order_data.get('clOrdId'),
                    price=Decimal(order_data['px']),
                    size=Decimal(order_data['sz']),
                    type=order_data['ordType'],
                    side=order_data['side'],
                    status=order_data['state'],
                    timestamp=datetime.fromtimestamp(int(order_data['ts']) / 1000),
                    filled_size=Decimal(order_data.get('fillSz', '0')),
                    filled_price=Decimal(order_data['fillPx']) if order_data.get('fillPx') else None,
                    fee=Decimal(order_data['fee']) if order_data.get('fee') else None,
                    fee_currency=order_data.get('feeCcy')
                ))
            return orders
        except Exception as e:
            logger.error(f"获取未完成订单失败: {e}")
            return []

class OKXAccountAPI(OKXRESTBase):
    """OKX账户API"""
    
    async def get_account_balance(self) -> Dict[str, OKXBalance]:
        """获取账户余额
        
        Returns:
            Dict[str, OKXBalance]: 币种余额映射
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/account/balance',
                auth=True
            )
            
            balances = {}
            for currency in response['data'][0].get('details', []):
                balances[currency['ccy']] = OKXBalance(
                    currency=currency['ccy'],
                    total=Decimal(currency['cashBal']),
                    available=Decimal(currency['availBal']),
                    frozen=Decimal(currency['frozenBal']),
                    margin=Decimal(currency.get('marginBal', '0')),
                    debt=Decimal(currency.get('debtBal', '0'))
                )
            return balances
        except Exception as e:
            logger.error(f"获取账户余额失败: {e}")
            return {}

class OKXRestClient:
    """OKX REST客户端"""
    
    def __init__(self,
                 symbol: str,
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None,
                 testnet: bool = False):
        """初始化REST客户端
        
        Args:
            symbol: 交易对
            api_key: API密钥
            api_secret: API密钥对应的密文
            passphrase: API密码
            testnet: 是否使用测试网
        """
        self.symbol = symbol
        self.market = OKXMarketAPI(api_key, api_secret, passphrase, testnet)
        self.trade = OKXTradeAPI(api_key, api_secret, passphrase, testnet)
        self.account = OKXAccountAPI(api_key, api_secret, passphrase, testnet) 