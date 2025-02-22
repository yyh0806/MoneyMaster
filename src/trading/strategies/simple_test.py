from decimal import Decimal
from typing import Dict
from datetime import datetime, timedelta
from loguru import logger

from ..core.strategy import BaseStrategy

class SimpleTestStrategy(BaseStrategy):
    def __init__(self, client, symbol: str, db_session):
        super().__init__(client, symbol, db_session)
        self.trade_quantity = Decimal('0.001')  # 小数量测试
        self.price_history = []
        
    def get_price_n_minutes_ago(self, minutes: int) -> Decimal:
        """获取n分钟前的价格"""
        target_time = datetime.utcnow() - timedelta(minutes=minutes)
        for timestamp, price in reversed(self.price_history):
            if timestamp <= target_time:
                return price
        return None
        
    def on_tick(self, market_data: Dict):
        """
        简单的测试策略:
        1. 价格上涨超过1%买入
        2. 价格下跌超过1%卖出
        """
        try:
            if 'data' not in market_data or not market_data['data']:
                logger.warning("无效的市场数据")
                return
                
            current_price = Decimal(str(market_data['data'][0]['last']))
            current_time = datetime.utcnow()
            
            # 更新价格历史
            self.price_history.append((current_time, current_price))
            # 只保留最近60分钟的数据
            self.price_history = [(t, p) for t, p in self.price_history 
                                if current_time - t <= timedelta(hours=1)]
            
            # 获取1分钟前的价格
            prev_price = self.get_price_n_minutes_ago(1)
            if not prev_price:
                return
                
            price_change = (current_price - prev_price) / prev_price
            
            logger.info(f"当前价格: {current_price}, 价格变化: {price_change:.2%}")
            
            if price_change > Decimal('0.01'):  # 上涨超过1%
                if self.position <= 0:
                    logger.info("价格上涨超过1%，买入信号")
                    self.buy(self.trade_quantity)
                    
            elif price_change < Decimal('-0.01'):  # 下跌超过1%
                if self.position >= 0:
                    logger.info("价格下跌超过1%，卖出信号")
                    self.sell(self.trade_quantity)
                    
        except Exception as e:
            error_msg = f"Strategy error: {str(e)}"
            logger.error(error_msg)
            self.handle_error(error_msg) 