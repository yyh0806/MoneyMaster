"""市场上下文管理模块"""

from typing import Dict, List
from .utils import strategy_logger

class MarketContextManager:
    """市场上下文管理器"""
    
    def __init__(self, max_context_length: int = 10):
        self.market_context: List[Dict] = []
        self.max_context_length = max_context_length
        self.logger = strategy_logger
        
    def update_context(self, new_data: Dict, kline_data: Dict) -> None:
        """更新市场上下文
        
        Args:
            new_data: 最新的市场数据
            kline_data: K线数据
        """
        try:
            current_data = new_data['data'][0]
            
            if kline_data.get('code') == '0' and kline_data.get('data'):
                kline = kline_data['data'][0]
                
                context_entry = {
                    'timestamp': current_data['ts'],
                    'price': float(current_data['last']),
                    'volume': float(current_data['vol24h']),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume_kline': float(kline[5])
                }
                
                self.market_context.append(context_entry)
                
                # 保持上下文长度在限制范围内
                if len(self.market_context) > self.max_context_length:
                    self.market_context = self.market_context[-self.max_context_length:]
                    
        except Exception as e:
            self.logger.error(f"更新市场上下文失败: {e}")
            
    def get_context(self) -> List[Dict]:
        """获取当前市场上下文"""
        return self.market_context
        
    def clear_context(self) -> None:
        """清空市场上下文"""
        self.market_context = [] 