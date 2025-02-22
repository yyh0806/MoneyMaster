from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
from loguru import logger

from .models import TradeRecord, StrategyState, BalanceSnapshot
from ..client import OKXClient

class BaseStrategy(ABC):
    def __init__(self, 
                 client: OKXClient,
                 symbol: str,
                 db_session,
                 commission_rate: Decimal = Decimal('0.001')):  # 默认0.1%手续费
        self.client = client
        self.symbol = symbol
        self.db_session = db_session
        self.commission_rate = commission_rate
        self.position = Decimal('0')
        self.avg_entry_price = Decimal('0')
        self.total_pnl = Decimal('0')
        self.total_commission = Decimal('0')
        
        # 从数据库加载策略状态
        self._load_state()
    
    def _load_state(self):
        """从数据库加载策略状态"""
        state = self.db_session.query(StrategyState).filter_by(
            strategy_name=self.__class__.__name__,
            symbol=self.symbol
        ).first()
        
        if state:
            self.position = state.position
            self.avg_entry_price = state.avg_entry_price
            self.total_pnl = state.total_pnl
            self.total_commission = state.total_commission
    
    def _save_state(self):
        """保存策略状态到数据库"""
        state = self.db_session.query(StrategyState).filter_by(
            strategy_name=self.__class__.__name__,
            symbol=self.symbol
        ).first()
        
        if not state:
            state = StrategyState(
                strategy_name=self.__class__.__name__,
                symbol=self.symbol
            )
            self.db_session.add(state)
        
        state.position = self.position
        state.avg_entry_price = self.avg_entry_price
        state.unrealized_pnl = self.calculate_unrealized_pnl()
        state.total_pnl = self.total_pnl
        state.total_commission = self.total_commission
        state.updated_at = datetime.utcnow()
        
        self.db_session.commit()
    
    def _record_trade(self, side: str, price: Decimal, quantity: Decimal, 
                     commission: Decimal, realized_pnl: Decimal = Decimal('0')):
        """记录交易"""
        trade = TradeRecord(
            trade_id=f"{datetime.utcnow().timestamp()}",
            symbol=self.symbol,
            side=side,
            price=price,
            quantity=quantity,
            commission=commission,
            realized_pnl=realized_pnl,
            trade_time=datetime.utcnow(),
            strategy_name=self.__class__.__name__
        )
        self.db_session.add(trade)
        self.db_session.commit()
    
    def calculate_unrealized_pnl(self) -> Decimal:
        """计算未实现盈亏"""
        if self.position == 0:
            return Decimal('0')
        
        current_price = Decimal(str(self.client.get_market_price(self.symbol)['last']))
        return (current_price - self.avg_entry_price) * self.position
    
    def buy(self, quantity: Decimal, price: Optional[Decimal] = None):
        """执行买入操作"""
        if price is None:
            price = Decimal(str(self.client.get_market_price(self.symbol)['last']))
        
        commission = price * quantity * self.commission_rate
        self.total_commission += commission
        
        if self.position < 0:  # 如果是空头平仓
            realized_pnl = (self.avg_entry_price - price) * min(abs(self.position), quantity)
            self.total_pnl += realized_pnl
        else:
            realized_pnl = Decimal('0')
        
        # 更新持仓均价
        if self.position + quantity != 0:
            self.avg_entry_price = (self.avg_entry_price * self.position + price * quantity) / (self.position + quantity)
        self.position += quantity
        
        # 记录交易
        self._record_trade('BUY', price, quantity, commission, realized_pnl)
        self._save_state()
        
        logger.info(f"买入 {quantity} {self.symbol} @ {price}, 手续费: {commission}, 实现盈亏: {realized_pnl}")
    
    def sell(self, quantity: Decimal, price: Optional[Decimal] = None):
        """执行卖出操作"""
        if price is None:
            price = Decimal(str(self.client.get_market_price(self.symbol)['last']))
        
        commission = price * quantity * self.commission_rate
        self.total_commission += commission
        
        if self.position > 0:  # 如果是多头平仓
            realized_pnl = (price - self.avg_entry_price) * min(self.position, quantity)
            self.total_pnl += realized_pnl
        else:
            realized_pnl = Decimal('0')
        
        # 更新持仓均价
        if self.position - quantity != 0:
            self.avg_entry_price = (self.avg_entry_price * self.position - price * quantity) / (self.position - quantity)
        self.position -= quantity
        
        # 记录交易
        self._record_trade('SELL', price, quantity, commission, realized_pnl)
        self._save_state()
        
        logger.info(f"卖出 {quantity} {self.symbol} @ {price}, 手续费: {commission}, 实现盈亏: {realized_pnl}")
    
    @abstractmethod
    def on_tick(self, market_data: Dict):
        """
        策略主逻辑，由子类实现
        :param market_data: 市场数据
        """
        pass 