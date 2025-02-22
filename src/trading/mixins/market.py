from typing import Dict, Optional

class MarketMixin:
    """市场数据相关的API"""
    
    def get_market_price(self, instId: str) -> Dict:
        """获取市场价格"""
        return self._request('GET', '/market/ticker', params={'instId': instId})
        
    def get_kline(self, instId: str, bar: str = '1m', limit: str = '100', after: str = None, before: str = None) -> Dict:
        """
        获取K线数据
        :param instId: 产品ID
        :param bar: K线周期，如 1m/3m/5m/15m/30m/1H/2H/4H/6H/12H/1D/1W/1M/3M/6M/1Y
        :param limit: 返回结果的数量限制，最大值为300，默认100
        :param after: 时间戳，返回该时间戳之前的数据
        :param before: 时间戳，返回该时间戳之后的数据
        """
        params = {
            'instId': instId,
            'bar': bar,
            'limit': limit
        }
        if after:
            params['after'] = after
        if before:
            params['before'] = before
            
        return self._request('GET', '/market/candles', params=params)
        
    def get_orderbook(self, instId: str, sz: str = '1') -> Dict:
        """
        获取深度数据
        :param instId: 产品ID
        :param sz: 深度档位，最大400，即买卖各400档
        """
        params = {
            'instId': instId,
            'sz': sz
        }
        return self._request('GET', '/market/books', params=params)
        
    def get_trades(self, instId: str, limit: str = '100') -> Dict:
        """
        获取最近的成交数据
        :param instId: 产品ID
        :param limit: 返回结果的数量限制，最大值为500，默认100
        """
        params = {
            'instId': instId,
            'limit': limit
        }
        return self._request('GET', '/market/trades', params=params) 