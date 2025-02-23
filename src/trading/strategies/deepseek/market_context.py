"""市场上下文管理模块"""

from typing import Dict, List
from decimal import Decimal
from ...indicators import RSI, VWAP, Volatility, Momentum, VolumeTrend
from .utils import strategy_logger

class MarketContextManager:
    """市场上下文管理器"""
    
    def __init__(self, max_context_length: int = 10):
        self.market_context: List[Dict] = []
        self.max_context_length = max_context_length
        self.logger = strategy_logger
        self.price_history = []  # 用于计算技术指标的价格历史
        self.volume_history = []  # 用于计算成交量指标的历史数据
        
        # 初始化技术指标
        self.indicators = {
            'rsi': RSI(period=14),
            'vwap': VWAP(),
            'volatility': Volatility(period=20),
            'momentum': Momentum(period=10),
            'volume_trend': VolumeTrend(period=20)
        }
        
    def calculate_technical_indicators(self, prices: List[float], volumes: List[float]) -> Dict:
        """计算技术指标"""
        if len(prices) < 20:  # 确保有足够的数据点
            return {}
            
        indicators = {}
        try:
            # 计算各项技术指标
            indicators['rsi'] = self.indicators['rsi'].calculate(prices)
            indicators['vwap'] = self.indicators['vwap'].calculate(prices, volumes)
            indicators['volatility'] = self.indicators['volatility'].calculate(prices)
            indicators['momentum'] = self.indicators['momentum'].calculate(prices)
            indicators['volume_trend'] = self.indicators['volume_trend'].calculate(volumes)
            
        except Exception as e:
            self.logger.error(f"计算技术指标失败: {e}")
            
        return indicators
        
    def update_context(self, new_data: Dict, kline_data: Dict) -> None:
        """更新市场上下文
        
        Args:
            new_data: 最新的市场数据
            kline_data: K线数据
        """
        try:
            current_data = new_data['data'][0]
            current_price = float(current_data['last'])
            
            if kline_data.get('code') == '0' and kline_data.get('data'):
                kline = kline_data['data'][0]
                # 使用1分钟K线的成交量，而不是24小时成交量
                current_volume = float(kline[5])  # K线数据中的成交量
                
                # 更新价格和成交量历史
                self.price_history.append(current_price)
                self.volume_history.append(current_volume)
                
                # 保持历史数据在合理范围内
                max_history = 50  # 用于计算技术指标的历史数据点数
                if len(self.price_history) > max_history:
                    self.price_history = self.price_history[-max_history:]
                    self.volume_history = self.volume_history[-max_history:]
                
                # 计算技术指标
                technical_indicators = {}
                if len(self.price_history) >= 20:
                    technical_indicators = self.calculate_technical_indicators(
                        self.price_history,
                        self.volume_history
                    )
                
                # 构建上下文条目，只包含最必要的K线数据和技术指标
                context_entry = {
                    'timestamp': current_data['ts'],
                    'price': current_price,
                    'volume': current_volume,
                    'price_change': round((current_price - float(kline[1])) / float(kline[1]) * 100, 2),  # 相对开盘价的变化百分比
                    **technical_indicators  # 添加技术指标
                }
                
                self.market_context.append(context_entry)
                
                # 保持上下文长度在限制范围内
                if len(self.market_context) > self.max_context_length:
                    self.market_context = self.market_context[-self.max_context_length:]
                    
                # 记录日志
                self.logger.info(f"更新市场上下文: 价格={current_price}, 1分钟成交量={current_volume}")
                if technical_indicators:
                    self.logger.info("技术指标:")
                    for indicator, value in technical_indicators.items():
                        self.logger.info(f"  {indicator}: {value}")
                    
        except Exception as e:
            self.logger.error(f"更新市场上下文失败: {e}")
            
    def get_context(self) -> List[Dict]:
        """获取当前市场上下文"""
        return self.market_context
        
    def clear_context(self) -> None:
        """清空市场上下文"""
        self.market_context = []
        self.price_history = []
        self.volume_history = [] 