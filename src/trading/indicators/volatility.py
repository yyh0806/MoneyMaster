"""波动率指标模块"""

import numpy as np
from typing import List
from .base import Indicator

class Volatility(Indicator):
    """波动率指标"""
    
    def __init__(self, period: int = 20):
        """
        初始化波动率指标
        
        Args:
            period: 计算周期，默认20
        """
        self.period = period
        
    def calculate(self, prices: List[float]) -> float:
        """
        计算波动率
        
        Args:
            prices: 价格序列
            
        Returns:
            float: 波动率（百分比）
        """
        if len(prices) < self.period:
            return 0.0
            
        prices_array = np.array(prices[-self.period:])
        volatility = np.std(prices_array) / np.mean(prices_array) * 100
        
        return round(float(volatility), 2) 