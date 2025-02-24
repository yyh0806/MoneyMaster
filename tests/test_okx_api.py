import os
import time
import base64
import hmac
import json
from datetime import datetime
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class TestOKXAPI:
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.use_testnet = os.getenv('USE_TESTNET', 'true').lower() == 'true'
        
        # 设置基础URL
        self.base_url = 'https://www.okx.com' if not self.use_testnet else 'https://www.okx.com'
        
        # 设置代理
        self.use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
        if self.use_proxy:
            self.proxies = {
                'http': os.getenv('HTTP_PROXY'),
                'https': os.getenv('HTTPS_PROXY')
            }
        else:
            self.proxies = None

    def _get_timestamp(self):
        """获取ISO格式的UTC时间戳"""
        return datetime.utcnow().isoformat()[:-3] + 'Z'

    def _sign(self, timestamp, method, request_path, body=''):
        """生成签名"""
        message = timestamp + method + request_path + (body if body else '')
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()

    def _get_headers(self, method, request_path, body=''):
        """生成请求头"""
        timestamp = self._get_timestamp()
        sign = self._sign(timestamp, method, request_path, body)
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': sign,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        if self.use_testnet:
            headers['x-simulated-trading'] = '1'
            
        return headers

    def test_place_order(self):
        """测试下单接口"""
        # 请求路径
        request_path = '/api/v5/trade/order'
        method = 'POST'
        
        # 请求体
        body = {
            "instId": "BTC-USDT",
            "tdMode": "cash",
            "clOrdId": "b15",
            "side": "buy",
            "ordType": "limit",
            "px": "2.15",
            "sz": "2"
        }
        
        # 转换为JSON字符串
        body_str = json.dumps(body)
        
        # 获取请求头
        headers = self._get_headers(method, request_path, body_str)
        
        # 发送请求
        url = self.base_url + request_path
        response = requests.post(
            url,
            headers=headers,
            data=body_str,
            proxies=self.proxies
        )
        
        # 打印响应
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.json()

if __name__ == "__main__":
    # 创建测试实例并运行测试
    test = TestOKXAPI()
    test.test_place_order() 