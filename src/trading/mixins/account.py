from typing import Dict, Optional

class AccountMixin:
    """账户相关的API"""
    
    def get_account_balance(self) -> Dict:
        """获取账户余额"""
        return self._request('GET', '/account/balance')
        
    def get_positions(self, instType: Optional[str] = None, instId: Optional[str] = None) -> Dict:
        """
        获取持仓信息
        :param instType: 产品类型，MARGIN：币币杠杆，SWAP：永续合约，FUTURES：交割合约，OPTION：期权
        :param instId: 产品ID
        """
        params = {}
        if instType:
            params['instType'] = instType
        if instId:
            params['instId'] = instId
            
        return self._request('GET', '/account/positions', params=params)
        
    def get_account_config(self) -> Dict:
        """获取账户配置"""
        return self._request('GET', '/account/config')
        
    def get_account_position_risk(self) -> Dict:
        """获取账户持仓风险"""
        return self._request('GET', '/account/account-position-risk')
        
    def get_bills(self, 
                  instType: Optional[str] = None,
                  ccy: Optional[str] = None,
                  mgnMode: Optional[str] = None,
                  ctType: Optional[str] = None,
                  type: Optional[str] = None,
                  subType: Optional[str] = None,
                  after: Optional[str] = None,
                  before: Optional[str] = None,
                  limit: str = '100') -> Dict:
        """
        获取账单流水
        :param instType: 产品类型
        :param ccy: 币种
        :param mgnMode: 仓位类型，isolated：逐仓，cross：全仓
        :param ctType: linear：正向合约，inverse：反向合约
        :param type: 账单类型
        :param subType: 账单子类型
        :param after: 时间戳，返回该时间戳之前的数据
        :param before: 时间戳，返回该时间戳之后的数据
        :param limit: 分页返回的结果集数量，最大为100，默认100
        """
        params = {'limit': limit}
        
        if instType:
            params['instType'] = instType
        if ccy:
            params['ccy'] = ccy
        if mgnMode:
            params['mgnMode'] = mgnMode
        if ctType:
            params['ctType'] = ctType
        if type:
            params['type'] = type
        if subType:
            params['subType'] = subType
        if after:
            params['after'] = after
        if before:
            params['before'] = before
            
        return self._request('GET', '/account/bills', params=params) 