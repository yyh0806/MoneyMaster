from typing import Dict, Optional

class TradeMixin:
    """交易相关的API"""
    
    def place_order(self, 
                    instId: str,
                    tdMode: str = 'cash',
                    side: str = 'buy',
                    ordType: str = 'limit',
                    sz: str = '1',
                    px: Optional[str] = None,
                    tgtCcy: Optional[str] = None) -> Dict:
        """
        下单
        :param instId: 产品ID，如 'BTC-USDT'
        :param tdMode: 交易模式，cash: 现货，isolated: 逐仓，cross: 全仓
        :param side: buy: 买入, sell: 卖出
        :param ordType: 订单类型，market: 市价单, limit: 限价单
        :param sz: 数量
        :param px: 价格，市价单不需要传
        :param tgtCcy: 市价单委托数量的类型，base_ccy: 交易货币，quote_ccy: 计价货币
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
        if tgtCcy:
            data['tgtCcy'] = tgtCcy
            
        return self._request('POST', '/api/v5/trade/order', data=data)
        
    def place_batch_orders(self, orders: list) -> Dict:
        """
        批量下单
        :param orders: 订单列表，每个订单的参数同place_order
        """
        return self._request('POST', '/api/v5/trade/batch-orders', data={'orders': orders})
        
    def cancel_order(self, instId: str, ordId: Optional[str] = None, clOrdId: Optional[str] = None) -> Dict:
        """
        撤销订单
        :param instId: 产品ID
        :param ordId: 订单ID
        :param clOrdId: 客户自定义订单ID
        """
        data = {'instId': instId}
        if ordId:
            data['ordId'] = ordId
        if clOrdId:
            data['clOrdId'] = clOrdId
            
        return self._request('POST', '/api/v5/trade/cancel-order', data=data)
        
    def cancel_batch_orders(self, orders: list) -> Dict:
        """
        批量撤销订单
        :param orders: 订单列表，每个订单的参数同cancel_order
        """
        return self._request('POST', '/api/v5/trade/cancel-batch-orders', data={'orders': orders})
        
    def amend_order(self,
                    instId: str,
                    ordId: Optional[str] = None,
                    clOrdId: Optional[str] = None,
                    reqId: Optional[str] = None,
                    newSz: Optional[str] = None,
                    newPx: Optional[str] = None) -> Dict:
        """
        修改订单
        :param instId: 产品ID
        :param ordId: 订单ID
        :param clOrdId: 客户自定义订单ID
        :param reqId: 客户自定义修改事件ID
        :param newSz: 修改的新数量
        :param newPx: 修改的新价格
        """
        data = {'instId': instId}
        if ordId:
            data['ordId'] = ordId
        if clOrdId:
            data['clOrdId'] = clOrdId
        if reqId:
            data['reqId'] = reqId
        if newSz:
            data['newSz'] = newSz
        if newPx:
            data['newPx'] = newPx
            
        return self._request('POST', '/api/v5/trade/amend-order', data=data)
        
    def get_order_details(self, instId: str, ordId: Optional[str] = None, clOrdId: Optional[str] = None) -> Dict:
        """
        获取订单信息
        :param instId: 产品ID
        :param ordId: 订单ID
        :param clOrdId: 客户自定义订单ID
        """
        params = {'instId': instId}
        if ordId:
            params['ordId'] = ordId
        if clOrdId:
            params['clOrdId'] = clOrdId
            
        return self._request('GET', '/api/v5/trade/order', params=params)
        
    def get_order_history(self,
                         instType: str,
                         instId: Optional[str] = None,
                         ordType: Optional[str] = None,
                         state: Optional[str] = None,
                         after: Optional[str] = None,
                         before: Optional[str] = None,
                         limit: str = '100') -> Dict:
        """
        获取历史订单记录
        :param instType: 产品类型
        :param instId: 产品ID
        :param ordType: 订单类型
        :param state: 订单状态
        :param after: 时间戳，前一次返回的最后一条数据的时间戳
        :param before: 时间戳，前一次返回的第一条数据的时间戳
        :param limit: 返回结果的数量限制，最大100，默认100
        """
        params = {
            'instType': instType,
            'limit': limit
        }
        if instId:
            params['instId'] = instId
        if ordType:
            params['ordType'] = ordType
        if state:
            params['state'] = state
        if after:
            params['after'] = after
        if before:
            params['before'] = before
            
        return self._request('GET', '/api/v5/trade/orders-history', params=params) 