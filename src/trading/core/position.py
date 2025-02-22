from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict

@dataclass
class Position:
    """持仓数据模型"""
    symbol: str                    # 交易对
    quantity: Decimal              # 持仓数量
    avg_price: Decimal            # 持仓均价
    unrealized_pnl: Decimal = Decimal('0')  # 未实现盈亏
    realized_pnl: Decimal = Decimal('0')    # 已实现盈亏
    margin: Decimal = Decimal('0')          # 保证金
    leverage: int = 1                       # 杠杆倍数
    last_update_time: datetime = datetime.now()  # 最后更新时间
    
    def update_position(self, 
                       filled_quantity: Decimal, 
                       filled_price: Decimal,
                       is_buy: bool):
        """
        更新持仓信息
        :param filled_quantity: 成交数量
        :param filled_price: 成交价格
        :param is_buy: 是否买入
        """
        if is_buy:
            # 买入，增加持仓
            if self.quantity == 0:
                # 新建仓位
                self.quantity = filled_quantity
                self.avg_price = filled_price
            else:
                # 现有仓位加仓
                total_cost = self.quantity * self.avg_price + filled_quantity * filled_price
                self.quantity += filled_quantity
                self.avg_price = total_cost / self.quantity
        else:
            # 卖出，减少持仓
            if filled_quantity > self.quantity:
                raise ValueError("卖出数量大于持仓数量")
                
            # 计算已实现盈亏
            realized_pnl = (filled_price - self.avg_price) * filled_quantity
            self.realized_pnl += realized_pnl
            
            # 更新持仓
            self.quantity -= filled_quantity
            # 如果完全平仓，重置均价
            if self.quantity == 0:
                self.avg_price = Decimal('0')
                
        self.last_update_time = datetime.now()
        
    def update_unrealized_pnl(self, current_price: Decimal):
        """
        更新未实现盈亏
        :param current_price: 当前市场价格
        """
        if self.quantity > 0:
            self.unrealized_pnl = (current_price - self.avg_price) * self.quantity
        else:
            self.unrealized_pnl = Decimal('0')
            
    @property
    def total_pnl(self) -> Decimal:
        """总盈亏（已实现 + 未实现）"""
        return self.realized_pnl + self.unrealized_pnl
        
    @property
    def position_value(self) -> Decimal:
        """持仓市值"""
        return self.quantity * self.avg_price
        
    @property
    def margin_ratio(self) -> Decimal:
        """保证金率"""
        return self.margin / self.position_value if self.position_value > 0 else Decimal('0') 