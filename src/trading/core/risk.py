from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime, timedelta

from .position import Position
from .order import Order, OrderSide

@dataclass
class RiskLimit:
    """风险限制配置"""
    max_position_value: Decimal     # 最大持仓市值
    max_leverage: int              # 最大杠杆倍数
    min_margin_ratio: Decimal      # 最小保证金率
    max_daily_loss: Decimal        # 最大日亏损
    max_order_value: Decimal       # 单笔订单最大价值
    min_order_value: Decimal       # 单笔订单最小价值
    price_deviation: Decimal       # 价格偏离度限制（相对于市场价格）
    
    # 资金限制相关
    total_capital: Decimal         # 策略总资金
    max_capital_usage: Decimal     # 最大资金使用比例
    reserve_capital: Decimal       # 保证金准备金
    
    @property
    def max_available_capital(self) -> Decimal:
        """最大可用资金"""
        return self.total_capital * self.max_capital_usage - self.reserve_capital
        
    @property
    def max_position_capital(self) -> Decimal:
        """最大持仓资金"""
        return min(self.max_position_value, self.max_available_capital)

class RiskManager:
    """风险管理器"""
    
    def __init__(self, risk_limit: RiskLimit):
        self.risk_limit = risk_limit
        self.daily_pnl = Decimal('0')
        self.last_pnl_reset = datetime.now()
        self.used_capital = Decimal('0')  # 当前已使用资金
        
    def reset_daily_pnl(self):
        """重置每日盈亏"""
        now = datetime.now()
        if now.date() > self.last_pnl_reset.date():
            self.daily_pnl = Decimal('0')
            self.last_pnl_reset = now
            
    def check_order(self, 
                    order: Order, 
                    position: Optional[Position],
                    market_price: Decimal) -> tuple[bool, str]:
        """
        检查订单风险
        :return: (是否通过, 原因)
        """
        # 检查订单价值
        order_value = order.quantity * (order.price or market_price)
        if order_value > self.risk_limit.max_order_value:
            return False, "订单价值超过限制"
        if order_value < self.risk_limit.min_order_value:
            return False, "订单价值低于最小限制"
            
        # 检查价格偏离度
        if order.price:
            deviation = abs(order.price - market_price) / market_price
            if deviation > self.risk_limit.price_deviation:
                return False, "价格偏离度过大"
                
        # 检查持仓限制
        if position:
            # 计算新持仓市值
            new_position_value = position.position_value
            if order.side == OrderSide.BUY:
                new_position_value += order_value
            else:
                new_position_value -= order_value
                
            if new_position_value > self.risk_limit.max_position_value:
                return False, "持仓市值超过限制"
                
        return True, ""
        
    def check_position(self, position: Position) -> tuple[bool, str]:
        """
        检查持仓风险
        :return: (是否通过, 原因)
        """
        # 检查杠杆倍数
        if position.leverage > self.risk_limit.max_leverage:
            return False, "杠杆倍数超过限制"
            
        # 检查保证金率
        if position.margin_ratio < self.risk_limit.min_margin_ratio:
            return False, "保证金率低于限制"
            
        # 检查持仓市值
        if position.position_value > self.risk_limit.max_position_value:
            return False, "持仓市值超过限制"
            
        return True, ""
        
    def update_pnl(self, pnl: Decimal) -> tuple[bool, str]:
        """
        更新并检查盈亏
        :return: (是否通过, 原因)
        """
        self.reset_daily_pnl()
        self.daily_pnl += pnl
        
        # 检查日亏损限制
        if self.daily_pnl < -self.risk_limit.max_daily_loss:
            return False, "达到每日最大亏损限制"
            
        return True, ""

    def get_risk_info(self) -> dict:
        """获取风险信息"""
        return {
            "total_capital": float(self.risk_limit.total_capital),
            "max_available_capital": float(self.risk_limit.max_available_capital),
            "used_capital": float(self.used_capital),
            "remaining_capital": float(self.risk_limit.max_available_capital - self.used_capital),
            "max_position_value": float(self.risk_limit.max_position_value),
            "max_position_capital": float(self.risk_limit.max_position_capital),
            "max_leverage": self.risk_limit.max_leverage,
            "min_margin_ratio": float(self.risk_limit.min_margin_ratio),
            "max_daily_loss": float(self.risk_limit.max_daily_loss),
            "current_daily_pnl": float(self.daily_pnl),
            "max_single_order": float(self.risk_limit.max_order_value),
            "min_single_order": float(self.risk_limit.min_order_value)
        }
    
    def update_used_capital(self, position_value: Decimal):
        """更新已使用资金"""
        self.used_capital = position_value 