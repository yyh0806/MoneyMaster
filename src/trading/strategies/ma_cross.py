from decimal import Decimal
from typing import Dict, List
import numpy as np
from loguru import logger

from ..core.strategy import BaseStrategy

class MACrossStrategy(BaseStrategy):
    def __init__(self, client, symbol: str, db_session, 
                 fast_period: int = 5, slow_period: int = 20,
                 quantity: Decimal = Decimal('0.01')):
        super().__init__(client, symbol, db_session)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.trade_quantity = quantity
        self.prices: List[float] = []
    
    def calculate_ma(self, period: int) -> float:
        """计算移动平均线"""
        if len(self.prices) < period:
            return float('nan')
        return np.mean(self.prices[-period:])
    
    def on_tick(self, market_data: Dict):
        """
        策略主逻辑
        1. 当快线上穿慢线时，开多仓
        2. 当快线下穿慢线时，开空仓
        """
        try:
            # OKX API返回格式处理
            if 'data' in market_data and len(market_data['data']) > 0:
                current_price = float(market_data['data'][0]['last'])
            else:
                logger.warning("No market data available")
                return
                
            self.prices.append(current_price)
            
            # 确保有足够的数据计算均线
            if len(self.prices) < self.slow_period:
                return
            
            # 保持价格列表长度，避免内存无限增长
            if len(self.prices) > self.slow_period * 2:
                self.prices = self.prices[-self.slow_period * 2:]
            
            # 计算均线
            fast_ma = self.calculate_ma(self.fast_period)
            slow_ma = self.calculate_ma(self.slow_period)
            
            # 获取前一个周期的均线值
            prev_fast_ma = self.calculate_ma(self.fast_period-1)
            prev_slow_ma = self.calculate_ma(self.slow_period-1)
            
            # 均线交叉信号
            if np.isnan(fast_ma) or np.isnan(slow_ma) or np.isnan(prev_fast_ma) or np.isnan(prev_slow_ma):
                return
            
            logger.info(f"当前价格: {current_price:.2f}, 快线: {fast_ma:.2f}, 慢线: {slow_ma:.2f}")
            
            # 快线上穿慢线
            if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
                if self.position <= 0:  # 如果当前没有多仓或者持有空仓
                    logger.info(f"均线金叉，买入信号 - 快线: {fast_ma:.2f}, 慢线: {slow_ma:.2f}")
                    # 如果有空仓，先平仓
                    if self.position < 0:
                        self.buy(abs(self.position))
                    # 开多仓
                    self.buy(self.trade_quantity)
            
            # 快线下穿慢线
            elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
                if self.position >= 0:  # 如果当前没有空仓或者持有多仓
                    logger.info(f"均线死叉，卖出信号 - 快线: {fast_ma:.2f}, 慢线: {slow_ma:.2f}")
                    # 如果有多仓，先平仓
                    if self.position > 0:
                        self.sell(self.position)
                    # 开空仓
                    self.sell(self.trade_quantity)
        except Exception as e:
            logger.error(f"Strategy error: {e}")
            return 