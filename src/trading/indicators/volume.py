"""成交量指标模块"""

import numpy as np
from typing import List
from .base import Indicator

class VWAP(Indicator):
    """成交量加权平均价格"""
    
    def calculate(self, prices: List[float], volumes: List[float]) -> float:
        """
        计算VWAP
        
        Args:
            prices: 价格序列
            volumes: 成交量序列
            
        Returns:
            float: VWAP值
        """
        if len(prices) != len(volumes) or len(prices) == 0:
            return 0.0
            
        prices_array = np.array(prices)
        volumes_array = np.array(volumes)
        
        vwap = np.sum(prices_array * volumes_array) / np.sum(volumes_array)
        return round(float(vwap), 2)

class VolumeTrend(Indicator):
    """成交量趋势指标"""
    
    def __init__(self, period: int = 20):
        """
        初始化成交量趋势指标
        
        Args:
            period: 计算周期，默认20
        """
        self.period = period
        
    def calculate(self, volumes: List[float]) -> float:
        """
        计算成交量趋势
        
        Args:
            volumes: 成交量序列
            
        Returns:
            float: 成交量趋势值（相对于均值的百分比）
        """
        if len(volumes) < self.period:
            return 0.0
            
        volumes_array = np.array(volumes)
        volume_ma = np.mean(volumes_array[-self.period:])
        current_volume = volumes_array[-1]
        
        volume_trend = (current_volume / volume_ma - 1) * 100
        return round(float(volume_trend), 2) 