from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime
import uuid

from .order import Order, OrderStatus, OrderType, OrderSide
from .position import Position
from .risk import RiskManager, RiskLimit
from .market_data import MarketDataManager
from src.trading.client import OKXClient

class TradingEngine:
    """交易引擎"""
    
    def __init__(self, client: OKXClient, risk_limit: RiskLimit):
        self.client = client
        self.risk_manager = RiskManager(risk_limit)
        self.market_data = MarketDataManager()
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.orders: Dict[str, Order] = {}       # order_id -> Order
        
    def create_order(self, 
                    symbol: str,
                    side: OrderSide,
                    order_type: OrderType,
                    quantity: Decimal,
                    price: Optional[Decimal] = None) -> tuple[Optional[Order], str]:
        """
        创建订单
        :return: (订单对象, 错误信息)
        """
        # 获取当前市场数据
        tick = self.market_data.ticks.get(symbol)
        if not tick:
            return None, "无可用市场数据"
            
        # 估算市场冲击
        impact = self.market_data.get_market_impact(symbol, quantity)
        if impact:
            # 如果市场冲击过大，可以考虑拒绝订单或调整价格
            if impact['price_impact'] > Decimal('0.01'):  # 价格影响超过1%
                return None, "市场冲击过大"
                
        # 检查市场波动性
        volatility = self.market_data.get_volatility(symbol)
        if volatility and volatility > Decimal('0.5'):  # 波动率超过50%
            return None, "市场波动性过高"
            
        # 检查流动性
        liquidity_score = self.market_data.get_liquidity_score(symbol)
        if liquidity_score and liquidity_score < Decimal('100'):
            return None, "市场流动性不足"
            
        # 生成客户端订单ID
        client_order_id = str(uuid.uuid4())
        
        # 创建订单对象
        order = Order(
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            client_order_id=client_order_id
        )
        
        # 风险检查
        position = self.positions.get(symbol)
        passed, reason = self.risk_manager.check_order(order, position, tick.last_price)
        if not passed:
            return None, reason
            
        # 发送订单
        try:
            response = self.client.place_order(
                instId=symbol,
                side=side.value,
                ordType=order_type.value,
                sz=str(quantity),
                px=str(price) if price else None
            )
            
            if response and 'data' in response:
                order_id = response['data'][0]['ordId']
                order.order_id = order_id
                order.status = OrderStatus.SUBMITTED
                self.orders[order_id] = order
                return order, ""
            else:
                return None, "下单失败"
                
        except Exception as e:
            return None, f"下单异常: {str(e)}"
            
    def cancel_order(self, order_id: str) -> tuple[bool, str]:
        """
        取消订单
        :return: (是否成功, 错误信息)
        """
        order = self.orders.get(order_id)
        if not order:
            return False, "订单不存在"
            
        if not order.can_cancel():
            return False, "订单状态不允许取消"
            
        try:
            response = self.client.cancel_order(
                instId=order.symbol,
                ordId=order.order_id
            )
            
            if response and 'data' in response:
                order.update_status(OrderStatus.CANCELLED)
                return True, ""
            else:
                return False, "取消订单失败"
                
        except Exception as e:
            return False, f"取消订单异常: {str(e)}"
            
    def update_position(self, symbol: str, trade_data: Dict):
        """
        更新持仓信息
        :param trade_data: 成交数据
        """
        # 获取或创建持仓对象
        position = self.positions.get(symbol)
        if not position:
            position = Position(symbol=symbol, quantity=Decimal('0'), avg_price=Decimal('0'))
            self.positions[symbol] = position
            
        # 更新持仓
        filled_quantity = Decimal(trade_data['fillSz'])
        filled_price = Decimal(trade_data['fillPx'])
        is_buy = trade_data['side'] == 'buy'
        
        position.update_position(filled_quantity, filled_price, is_buy)
        
        # 更新订单
        order_id = trade_data['ordId']
        order = self.orders.get(order_id)
        if order:
            order.update_fill(filled_quantity, filled_price)
            
        # 更新盈亏
        if not is_buy:  # 只在卖出时计算已实现盈亏
            pnl = position.realized_pnl
            passed, reason = self.risk_manager.update_pnl(pnl)
            if not passed:
                # TODO: 触发风险控制措施
                pass
                
    def update_market_data(self, symbol: str, data: Dict):
        """
        更新市场数据
        :param data: 市场数据字典，包含tick、candle、orderbook等数据
        """
        # 更新行情数据
        if 'tick' in data:
            tick = self.market_data.update_tick(symbol, data['tick'])
            
            # 更新持仓的未实现盈亏
            position = self.positions.get(symbol)
            if position:
                position.update_unrealized_pnl(tick.last_price)
                
                # 检查持仓风险
                passed, reason = self.risk_manager.check_position(position)
                if not passed:
                    # TODO: 触发风险控制措施
                    pass
                    
        # 更新K线数据
        if 'candle' in data:
            self.market_data.update_candle(symbol, data['candle'])
            
        # 更新订单簿
        if 'orderbook' in data:
            self.market_data.update_orderbook(symbol, data['orderbook'])
            
    def get_market_analysis(self, symbol: str) -> Dict:
        """
        获取市场分析数据
        :return: 市场分析结果
        """
        analysis = {
            'vwap': self.market_data.get_vwap(symbol),
            'volatility': self.market_data.get_volatility(symbol),
            'liquidity_score': self.market_data.get_liquidity_score(symbol),
            'trend': self.market_data.get_trend_strength(symbol)
        }
        
        # 添加基本市场数据
        tick = self.market_data.ticks.get(symbol)
        if tick:
            analysis.update({
                'last_price': tick.last_price,
                'bid_price': tick.bid_price,
                'ask_price': tick.ask_price,
                'volume_24h': tick.volume_24h,
                'high_24h': tick.high_24h,
                'low_24h': tick.low_24h
            })
            
        return analysis 