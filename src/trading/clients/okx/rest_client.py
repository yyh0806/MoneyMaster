from typing import Dict, Optional, List, Any
from decimal import Decimal
import aiohttp
import hmac
import base64
import json
import time
from datetime import datetime
from loguru import logger

from src.trading.base.models.market import (
    OrderBook, OrderBookLevel, Ticker, Trade, Candlestick, MarketSnapshot
)
from .parsers import OKXDataParser

class OKXRestClient:
    """OKX REST API客户端"""
    
    def __init__(self, 
                 symbol: str,
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None,
                 testnet: bool = False):
        """初始化OKX REST客户端
        
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
        self.parser = OKXDataParser()
        
        # 设置API基础URL
        self.base_url = "https://www.okx.com"
        if testnet:
            self.base_url = "https://www.okx.com/api/v5/simulated"
            
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
        """
        url = f"{self.base_url}{path}"
        headers = {
            'Content-Type': 'application/json'
        }
        
        if auth and self.api_key and self.api_secret:
            timestamp = self._get_timestamp()
            body = json.dumps(data) if data else ''
            sign = self._sign(timestamp, method, path, body)
            
            headers.update({
                'OK-ACCESS-KEY': self.api_key,
                'OK-ACCESS-SIGN': sign,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': self.passphrase or ''
            })
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        logger.error(f"API请求失败: status={response.status}, response={result}")
                        raise Exception(f"API请求失败: {result.get('msg', '')}")
                        
                    return result
        except Exception as e:
            logger.error(f"请求失败: {e}")
            raise
            
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """获取Ticker数据
        
        Args:
            symbol: 交易对
            
        Returns:
            Optional[Ticker]: Ticker数据对象
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/market/ticker',
                params={'instId': symbol}
            )
            
            if response.get('code') == '0' and response.get('data'):
                return self.parser.parse_ticker(response['data'][0], symbol)
            return None
        except Exception as e:
            logger.error(f"获取Ticker数据失败: {e}")
            return None
            
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Optional[OrderBook]:
        """获取订单簿
        
        Args:
            symbol: 交易对
            depth: 深度
            
        Returns:
            Optional[OrderBook]: 订单簿对象
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
            
            if response.get('code') == '0' and response.get('data'):
                return self.parser.parse_orderbook(response['data'][0], symbol)
            return None
        except Exception as e:
            logger.error(f"获取订单簿失败: {e}")
            return None
            
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """获取最近成交
        
        Args:
            symbol: 交易对
            limit: 返回的成交数量
            
        Returns:
            List[Trade]: 成交记录列表
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
            
            if response.get('code') == '0' and response.get('data'):
                return [
                    self.parser.parse_trade(trade_data, symbol)
                    for trade_data in response['data']
                ]
            return []
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
        try:
            # 转换时间周期格式
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
            
            if response.get('code') == '0' and response.get('data'):
                return [
                    self.parser.parse_candlestick(candle_data, symbol, interval)
                    for candle_data in response['data']
                ]
            return []
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return []
            
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """获取账户余额
        
        Returns:
            Dict[str, Decimal]: 币种余额映射
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/account/balance',
                auth=True
            )
            
            if response.get('code') == '0' and response.get('data'):
                balances = {}
                for currency in response['data'][0].get('details', []):
                    balances[currency['ccy']] = Decimal(currency['cashBal'])
                return balances
            return {}
        except Exception as e:
            logger.error(f"获取账户余额失败: {e}")
            return {}
            
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Optional[Decimal] = None
    ) -> Dict:
        """下单
        
        Args:
            symbol: 交易对
            side: 订单方向 (buy/sell)
            order_type: 订单类型 (limit/market)
            amount: 数量
            price: 价格（市价单可选）
            
        Returns:
            Dict: 订单信息
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
            
            if response.get('code') == '0':
                return response['data'][0]
            raise Exception(f"下单失败: {response.get('msg', '')}")
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
            
            return response.get('code') == '0'
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False
            
    async def get_order(self, symbol: str, order_id: str) -> Dict:
        """获取订单信息
        
        Args:
            symbol: 交易对
            order_id: 订单ID
            
        Returns:
            Dict: 订单信息
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
            
            if response.get('code') == '0' and response.get('data'):
                return response['data'][0]
            return {}
        except Exception as e:
            logger.error(f"获取订单信息失败: {e}")
            return {}
            
    async def get_open_orders(self, symbol: str) -> List[Dict]:
        """获取未完成订单
        
        Args:
            symbol: 交易对
            
        Returns:
            List[Dict]: 订单列表
        """
        try:
            response = await self._request(
                'GET',
                '/api/v5/trade/orders-pending',
                params={'instId': symbol},
                auth=True
            )
            
            if response.get('code') == '0':
                return response.get('data', [])
            return []
        except Exception as e:
            logger.error(f"获取未完成订单失败: {e}")
            return [] 