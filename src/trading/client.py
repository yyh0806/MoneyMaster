from typing import Dict, Optional
import hmac
import base64
import json
from datetime import datetime
from loguru import logger

from src.config import settings
from src.utils.http_client import HTTPClient
from src.trading.mixins.market import MarketMixin
from src.trading.mixins.account import AccountMixin
from src.trading.mixins.trade import TradeMixin

class OKXClient(HTTPClient, MarketMixin, AccountMixin, TradeMixin):
    """OKX交易所API客户端"""
    
    def __init__(self):
        """初始化OKX客户端"""
        self.api_key = settings.API_KEY
        self.secret_key = settings.SECRET_KEY
        self.passphrase = settings.PASSPHRASE
        self.is_testnet = settings.USE_TESTNET
        
        # 设置基础URL
        base_url = "https://www.okx.com"
        
        # 设置代理
        proxies = None
        if settings.USE_PROXY:
            proxies = {
                'http': settings.HTTP_PROXY,
                'https': settings.HTTPS_PROXY
            }
            
        super().__init__(base_url, proxies)
            
    def _get_timestamp(self) -> str:
        """获取ISO格式的时间戳"""
        return datetime.utcnow().isoformat()[:-3] + 'Z'
        
    def _sign(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """生成签名"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
        
    def _prepare_auth_headers(self, method: str, path: str, body: Dict = None) -> Dict:
        """准备认证请求头"""
        timestamp = self._get_timestamp()
        body_str = json.dumps(body) if body else ''
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self._sign(timestamp, method, path, body_str),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        if self.is_testnet:
            headers['x-simulated-trading'] = '1'
            
        return headers
        
    def _request(self, method: str, path: str, params: Dict = None, data: Dict = None) -> Dict:
        """发送认证请求"""
        headers = self._prepare_auth_headers(method, path, data)
        return super().request(method, path, headers=headers, params=params, data=data)
            
    def get_account_balance(self) -> Dict:
        """获取账户余额"""
        return self._request('GET', '/api/v5/account/balance')
            
    def place_order(self, 
                    instId: str,
                    tdMode: str = 'cash',
                    side: str = 'buy',
                    ordType: str = 'limit',
                    sz: str = '1',
                    px: Optional[str] = None) -> Dict:
        """
        下单
        :param instId: 产品ID，如 'BTC-USDT'
        :param tdMode: 交易模式，cash: 现货
        :param side: buy: 买入, sell: 卖出
        :param ordType: 订单类型，market: 市价单, limit: 限价单
        :param sz: 数量
        :param px: 价格，市价单不需要传
        """
        data = {
            'instId': instId,
            'tdMode': tdMode,
            'side': side,
            'ordType': ordType,
            'sz': sz
        }
        if px:
            data['px'] = px
            
        return self._request('POST', '/api/v5/trade/order', data=data)
            
    def get_market_price(self, instId: str) -> Dict:
        """获取市场价格"""
        return self._request('GET', '/api/v5/market/ticker', params={'instId': instId}) 