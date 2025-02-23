"""指标基类模块"""

from abc import ABC, abstractmethod
from typing import List, Union

class Indicator(ABC):
    """技术指标基类"""
    
    @abstractmethod
    def calculate(self, *args, **kwargs) -> Union[float, List[float]]:
        """
        计算指标值
        
        Returns:
            Union[float, List[float]]: 指标计算结果
        """
        pass 