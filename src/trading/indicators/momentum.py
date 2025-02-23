"""动量指标模块"""

import numpy as np
from typing import List
from .base import Indicator

class RSI(Indicator):
    """相对强弱指标"""
    
    def __init__(self, period: int = 14):
        """
        初始化RSI指标
        
        Args:
            period: RSI计算周期，默认14
        """
        self.period = period
        
    def calculate(self, prices: List[float]) -> float:
        """
        计算RSI值
        
        Args:
            prices: 价格序列
            
        Returns:
            float: RSI值
        """
        if len(prices) < self.period + 1:
            return 50.0  # 数据不足时返回中性值
            
        prices_array = np.array(prices)
        delta = np.diff(prices_array)
        gain = (delta > 0) * delta
        loss = (delta < 0) * -delta
        
        avg_gain = np.mean(gain[-self.period:])
        avg_loss = np.mean(loss[-self.period:])
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(float(rsi), 2)

class Momentum(Indicator):
    """价格动量指标"""
    
    def __init__(self, period: int = 10):
        """
        初始化动量指标
        
        Args:
            period: 动量计算周期，默认10
        """
        self.period = period
        
    def calculate(self, prices: List[float]) -> float:
        """
        计算价格动量
        
        Args:
            prices: 价格序列
            
        Returns:
            float: 动量值（百分比）
        """
        if len(prices) < self.period:
            return 0.0
            
        current_price = prices[-1]
        past_price = prices[-self.period]
        momentum = (current_price / past_price - 1) * 100
        
        return round(float(momentum), 2) 