from decimal import Decimal
from typing import Dict
from datetime import datetime, timedelta
from loguru import logger
import random

from ..core.strategy import BaseStrategy

class SimpleTestStrategy(BaseStrategy):
    def __init__(self, client, symbol: str, db_session):
        super().__init__(client, symbol, db_session)
        self.trade_quantity = Decimal('0.001')  # 小数量测试
        self.last_trade_time = None
        
    def on_tick(self, market_data: Dict):
        """
        简单的测试策略:
        每30秒随机执行一次买卖操作
        """
        try:
            # 验证市场数据格式
            if not isinstance(market_data, dict):
                logger.error(f"无效的市场数据格式: {market_data}")
                return
                
            if 'data' not in market_data or not market_data['data']:
                logger.error(f"市场数据中没有data字段: {market_data}")
                return
                
            market_data_item = market_data['data'][0]
            if not isinstance(market_data_item, dict) or 'last' not in market_data_item:
                logger.error(f"无效的市场数据项: {market_data_item}")
                return
            
            current_time = datetime.utcnow()
            current_price = Decimal(str(market_data_item['last']))
            
            logger.info(f"当前价格: {current_price}")
            
            # 如果是第一次执行或者距离上次交易已经超过30秒
            if not self.last_trade_time or (current_time - self.last_trade_time) >= timedelta(seconds=30):
                # 随机决定买入还是卖出
                action = random.choice(['BUY', 'SELL'])
                
                if action == 'BUY':
                    logger.info(f"随机买入信号，价格: {current_price}")
                    self.buy(self.trade_quantity, current_price)
                else:
                    logger.info(f"随机卖出信号，价格: {current_price}")
                    self.sell(self.trade_quantity, current_price)
                    
                self.last_trade_time = current_time
                
        except Exception as e:
            error_msg = f"Strategy error: {str(e)}"
            logger.error(error_msg)
            self.handle_error(error_msg) 