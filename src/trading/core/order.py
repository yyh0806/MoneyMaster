from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

class OrderType(Enum):
    """订单类型"""
    MARKET = "market"  # 市价单
    LIMIT = "limit"    # 限价单

class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"    # 买入
    SELL = "sell"  # 卖出

class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"       # 等待中
    SUBMITTED = "submitted"   # 已提交
    PARTIAL = "partial"       # 部分成交
    FILLED = "filled"        # 完全成交
    CANCELLED = "cancelled"   # 已取消
    FAILED = "failed"        # 失败

@dataclass
class Order:
    """订单数据模型"""
    symbol: str                       # 交易对
    order_type: OrderType            # 订单类型
    side: OrderSide                  # 买卖方向
    quantity: Decimal                # 数量
    price: Optional[Decimal] = None  # 价格（市价单可为空）
    status: OrderStatus = OrderStatus.PENDING  # 订单状态
    order_id: Optional[str] = None   # 订单ID
    client_order_id: Optional[str] = None  # 客户端订单ID
    created_at: datetime = datetime.now()  # 创建时间
    updated_at: datetime = datetime.now()  # 更新时间
    filled_quantity: Decimal = Decimal('0')  # 已成交数量
    filled_price: Optional[Decimal] = None   # 成交均价
    
    def is_active(self) -> bool:
        """判断订单是否活跃"""
        return self.status in {OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL}
    
    def can_cancel(self) -> bool:
        """判断订单是否可以取消"""
        return self.is_active()
    
    def update_status(self, status: OrderStatus):
        """更新订单状态"""
        self.status = status
        self.updated_at = datetime.now()
        
    def update_fill(self, filled_quantity: Decimal, filled_price: Decimal):
        """更新成交信息"""
        self.filled_quantity += filled_quantity
        if self.filled_price is None:
            self.filled_price = filled_price
        else:
            # 计算新的成交均价
            total_quantity = self.filled_quantity
            old_amount = (total_quantity - filled_quantity) * self.filled_price
            new_amount = filled_quantity * filled_price
            self.filled_price = (old_amount + new_amount) / total_quantity
            
        # 更新订单状态
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIAL
            
        self.updated_at = datetime.now() 