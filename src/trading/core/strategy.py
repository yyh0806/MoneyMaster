from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
from loguru import logger
import sys
import asyncio

from .models import TradeRecord, StrategyState, StrategyStatus
from .risk import RiskManager, RiskLimit, Position
from .order import Order, OrderSide
from ..clients.okx import OKXClient

# 配置日志
logger.remove()  # 移除默认的日志处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[strategy]}</cyan> | <level>{message}</level>",
    level="INFO"
)

# 创建事件总线
class EventBus:
    def __init__(self):
        self.subscribers = []

    async def publish(self, event_type: str, data: dict):
        for subscriber in self.subscribers:
            try:
                await subscriber(event_type, data)
            except Exception as e:
                logger.error(f"事件处理错误: {e}")

    def subscribe(self, callback):
        self.subscribers.append(callback)

# 全局事件总线实例
event_bus = EventBus()

class StrategyStateBase(ABC):
    """策略状态基类"""
    def __init__(self):
        self.strategy = None
        self.logger = logger.bind(strategy="BaseStrategy")

    @abstractmethod
    async def start(self):
        """启动策略"""
        pass

    @abstractmethod
    async def stop(self):
        """停止策略"""
        pass

    @abstractmethod
    async def pause(self):
        """暂停策略"""
        pass

    def _save_status(self, status: StrategyStatus, error: str = None):
        """保存策略状态到数据库"""
        try:
            state = self.strategy.db_session.query(StrategyState).filter_by(
                strategy_name=self.strategy.__class__.__name__,
                symbol=self.strategy.symbol
            ).first()
            
            if not state:
                state = StrategyState(
                    strategy_name=self.strategy.__class__.__name__,
                    symbol=self.strategy.symbol,
                    position=Decimal('0'),
                    avg_entry_price=Decimal('0'),
                    unrealized_pnl=Decimal('0'),
                    total_pnl=Decimal('0'),
                    total_commission=Decimal('0')
                )
                self.strategy.db_session.add(state)
            
            # 更新状态
            state.status = status.value
            state.last_error = error
            state.last_run_time = datetime.utcnow()
            self.strategy.db_session.commit()
            
            # 立即更新策略实例的状态
            self.strategy._is_running = status == StrategyStatus.RUNNING
            
            # 获取完整的状态信息
            strategy_info = self.strategy.state_info
            market_data = self.strategy.client.get_market_price(self.strategy.symbol)
            
            # 发布状态更新事件
            asyncio.create_task(event_bus.publish(
                'strategy_update',
                {
                    'symbol': self.strategy.symbol,
                    'strategy_info': strategy_info,
                    'market_data': market_data
                }
            ))
            
            self.logger.info(f"策略状态已更新并广播: {status.value}")
        except Exception as e:
            self.logger.error(f"保存策略状态失败: {str(e)}")
            self.strategy.db_session.rollback()
            raise

class RunningState(StrategyStateBase):
    """运行状态"""
    async def start(self):
        raise Exception("策略已经在运行中")

    async def stop(self):
        self._save_status(StrategyStatus.STOPPED)
        self.strategy.set_state(StoppedState())
        self.logger.info("策略已停止")

    async def pause(self):
        self._save_status(StrategyStatus.PAUSED)
        self.strategy.set_state(PausedState())
        self.logger.info("策略已暂停")

class StoppedState(StrategyStateBase):
    """停止状态"""
    async def start(self):
        self._save_status(StrategyStatus.RUNNING)
        self.strategy.set_state(RunningState())
        self.logger.info("策略已启动")

    async def stop(self):
        raise Exception("策略已经停止")

    async def pause(self):
        raise Exception("无法暂停已停止的策略")

class PausedState(StrategyStateBase):
    """暂停状态"""
    async def start(self):
        self._save_status(StrategyStatus.RUNNING)
        self.strategy.set_state(RunningState())
        self.logger.info("策略已恢复运行")

    async def stop(self):
        self._save_status(StrategyStatus.STOPPED)
        self.strategy.set_state(StoppedState())
        self.logger.info("策略已停止")

    async def pause(self):
        raise Exception("策略已经暂停")

class ErrorState(StrategyStateBase):
    """错误状态"""
    async def start(self):
        self._save_status(StrategyStatus.RUNNING)
        self.strategy.set_state(RunningState())
        self.logger.info("策略已从错误状态恢复")

    async def stop(self):
        self._save_status(StrategyStatus.STOPPED)
        self.strategy.set_state(StoppedState())
        self.logger.info("策略已停止")

    async def pause(self):
        raise Exception("错误状态的策略无法暂停")

class BaseStrategy(ABC):
    """
    交易策略基类
    
    职责：
    1. 管理策略生命周期（启动、停止、暂停）
    2. 维护策略状态
    3. 提供交易操作接口
    4. 处理数据持久化
    5. 提供风险控制接口
    
    使用方式：
    1. 继承此类创建具体策略
    2. 实现必要的抽象方法
    3. 使用提供的接口进行交易操作
    """
    
    def __init__(self, 
                 client: OKXClient,
                 symbol: str,
                 db_session,
                 risk_limit: RiskLimit,
                 commission_rate: Decimal = Decimal('0.001')):
        """
        初始化策略
        
        Args:
            client: 交易客户端
            symbol: 交易对
            db_session: 数据库会话
            risk_limit: 风险限制配置
            commission_rate: 手续费率
        """
        # 基础配置
        self.client = client
        self.symbol = symbol
        self.db_session = db_session
        self.commission_rate = commission_rate
        
        # 风险管理器
        self.risk_manager = RiskManager(risk_limit)
        
        # 交易相关状态
        self.position = Position(
            symbol=symbol,
            quantity=Decimal('0'),
            avg_price=Decimal('0'),
            leverage=1
        )
        self.total_pnl = Decimal('0')
        self.total_commission = Decimal('0')
        
        # 运行状态
        self._state = None
        self._is_running = False
        self._task = None
        self.logger = logger.bind(strategy=self.__class__.__name__)
        
        # 初始化状态
        self._initialize_state()

    def _initialize_state(self):
        """初始化策略状态"""
        # 从数据库加载状态
        self._load_state()
        
        # 如果没有状态记录，设置为停止状态
        if not self._state:
            self.set_state(StoppedState())
            self._state._save_status(StrategyStatus.STOPPED)
        
        # 确保初始状态为停止
        if self.current_state != StrategyStatus.STOPPED.value:
            self.logger.warning(f"策略初始化时状态不是停止状态，强制设置为停止状态")
            self.set_state(StoppedState())
            self._state._save_status(StrategyStatus.STOPPED)
            self._is_running = False
            if self._task:
                self._task.cancel()
                self._task = None

    @property
    def is_running(self) -> bool:
        """策略是否在运行"""
        return self._is_running and self._state and isinstance(self._state, RunningState)

    @property
    def current_state(self) -> str:
        """当前状态"""
        if not self._state:
            return StrategyStatus.STOPPED.value
        
        state_map = {
            'RunningState': StrategyStatus.RUNNING.value,
            'StoppedState': StrategyStatus.STOPPED.value,
            'PausedState': StrategyStatus.PAUSED.value,
            'ErrorState': StrategyStatus.ERROR.value
        }
        return state_map.get(self._state.__class__.__name__, StrategyStatus.STOPPED.value)

    @property
    def state_info(self) -> dict:
        """策略状态信息"""
        return {
            "strategy_name": self.__class__.__name__,
            "symbol": self.symbol,
            "is_running": self.is_running,
            "status": self.current_state,
            "position": float(self.position.quantity),
            "avg_entry_price": float(self.position.avg_price),
            "total_pnl": float(self.total_pnl),
            "total_commission": float(self.total_commission),
            "unrealized_pnl": float(self.calculate_unrealized_pnl()),
            "position_value": float(self.position.position_value),
            "risk_info": self.risk_manager.get_risk_info()
        }

    @property
    def capital_info(self) -> dict:
        """获取策略资金信息"""
        risk_info = self.risk_manager.get_risk_info()
        position_value = self.position.position_value if hasattr(self.position, 'position_value') else Decimal('0')
        
        return {
            "total_capital": risk_info["total_capital"],
            "max_available": risk_info["max_available_capital"],
            "used_capital": risk_info["used_capital"],
            "remaining_capital": risk_info["remaining_capital"],
            "current_position_value": float(position_value),
            "max_position_allowed": risk_info["max_position_capital"],
            "max_single_trade": risk_info["max_single_order"],
            "total_pnl": float(self.total_pnl),
            "unrealized_pnl": float(self.calculate_unrealized_pnl()),
            "total_commission": float(self.total_commission)
        }

    def get_max_cost(self) -> Decimal:
        """获取策略最大资金使用限制"""
        return self.risk_manager.risk_limit.max_position_capital

    def get_current_cost(self) -> Decimal:
        """获取当前已使用资金"""
        return self.position.position_value if hasattr(self.position, 'position_value') else Decimal('0')

    def get_remaining_cost(self) -> Decimal:
        """获取剩余可用资金"""
        return self.get_max_cost() - self.get_current_cost()

    def update_position_value(self):
        """更新持仓市值"""
        current_value = self.get_current_cost()
        self.risk_manager.update_used_capital(current_value)

    def set_state(self, state: StrategyStateBase):
        """设置策略状态"""
        self._state = state
        self._state.strategy = self
        self._state.logger = self.logger

    async def start(self):
        """启动策略"""
        try:
            if self.is_running:
                raise Exception("策略已经在运行中")
            
            # 清理之前的任务
            if self._task:
                self._task.cancel()
                self._task = None
            
            # 调用策略特定的初始化
            await self._on_start()
            
            # 创建运行任务
            self._task = asyncio.create_task(self.run())
            
            # 更新状态
            self._is_running = True
            
            # 更新状态并广播（只广播一次）
            await self._state.start()
            
            self.logger.info(f"{self.__class__.__name__} 策略已启动")
        except Exception as e:
            self._is_running = False
            if self._task:
                self._task.cancel()
                self._task = None
            self.logger.error(f"启动策略失败: {str(e)}")
            raise

    async def stop(self):
        """停止策略"""
        try:
            if not self.is_running:
                raise Exception("策略未在运行")
            
            # 调用策略特定的清理
            await self._on_stop()
            
            self._is_running = False
            await self._state.stop()
            
            if self._task:
                self._task.cancel()
                self._task = None
            
            # 立即广播状态更新
            asyncio.create_task(event_bus.publish(
                'strategy_update',
                {
                    'symbol': self.symbol,
                    'strategy_info': self.state_info,
                    'market_data': self.client.get_market_price(self.symbol)
                }
            ))
            
            self.logger.info(f"{self.__class__.__name__} 策略已停止")
        except Exception as e:
            # 确保策略被完全停止
            self._is_running = False
            if self._task:
                self._task.cancel()
                self._task = None
            self.set_state(StoppedState())
            self._state._save_status(StrategyStatus.STOPPED)
            self.logger.error(f"停止策略时发生错误: {str(e)}")
            raise

    async def pause(self):
        """暂停策略"""
        try:
            if not self.is_running:
                raise Exception("无法暂停未运行的策略")
            await self._state.pause()
            self.logger.info(f"{self.__class__.__name__} 策略已暂停")
        except Exception as e:
            self.logger.error(f"暂停策略失败: {str(e)}")
            raise

    async def resume(self):
        """恢复策略"""
        try:
            if self.is_running:
                raise Exception("策略已经在运行")
            self._is_running = True
            await self.start()
            self.logger.info(f"{self.__class__.__name__} 策略已恢复")
        except Exception as e:
            self._is_running = False
            self.logger.error(f"恢复策略失败: {str(e)}")
            raise

    def handle_error(self, error: str):
        """处理策略错误"""
        try:
            self._is_running = False
            if self._task:
                self._task.cancel()
                self._task = None
            self._state._save_status(StrategyStatus.ERROR, error)
            self.set_state(ErrorState())
            self.logger.error(f"{self.__class__.__name__} 策略发生错误: {error}")
        except Exception as e:
            self.logger.error(f"处理错误时发生异常: {str(e)}")
            # 确保策略被停止
            self._is_running = False
            if self._task:
                self._task.cancel()
                self._task = None
            self.set_state(StoppedState())
            self._state._save_status(StrategyStatus.STOPPED)

    def _record_trade(self, side: str, price: Decimal, quantity: Decimal, 
                     commission: Decimal, realized_pnl: Decimal = Decimal('0')):
        """记录交易"""
        try:
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
            self.logger.info(f"交易记录已保存: {side} {quantity} @ {price}")
        except Exception as e:
            self.logger.error(f"保存交易记录失败: {str(e)}")
            self.db_session.rollback()
            raise

    def _validate_trade_params(self, quantity: Decimal, price: Optional[Decimal] = None) -> tuple[bool, str]:
        """
        验证交易参数
        
        Args:
            quantity: 交易数量
            price: 交易价格
            
        Returns:
            tuple[bool, str]: (是否验证通过, 错误信息)
        """
        try:
            if quantity <= 0:
                return False, "交易数量必须大于0"
            
            if price is not None and price <= 0:
                return False, "价格必须大于0"
            
            # 创建订单对象
            order = Order(
                symbol=self.symbol,
                side=OrderSide.BUY if quantity > 0 else OrderSide.SELL,
                quantity=abs(quantity),
                price=price
            )
            
            # 使用风险管理器验证订单
            is_valid, reason = self.risk_manager.check_order(
                order=order,
                position=self.position,
                market_price=self.get_market_price()
            )
            
            if not is_valid:
                self.logger.warning(f"订单未通过风险检查: {reason}")
                return False, reason
                
            return True, ""
        except Exception as e:
            self.logger.error(f"交易参数验证失败: {str(e)}")
            return False, str(e)

    def get_market_price(self) -> Decimal:
        """获取市场价格"""
        try:
            market_data = self.client.get_market_price(self.symbol)
            if not market_data or 'data' not in market_data or not market_data['data']:
                raise ValueError("无法获取市场价格")
                
            market_data_item = market_data['data'][0]
            if not isinstance(market_data_item, dict) or 'last' not in market_data_item:
                raise ValueError("无效的市场数据格式")
                
            return Decimal(str(market_data_item['last']))
        except Exception as e:
            self.logger.error(f"获取市场价格失败: {str(e)}")
            raise

    def calculate_unrealized_pnl(self) -> Decimal:
        """计算未实现盈亏"""
        try:
            if self.position.quantity == 0:
                return Decimal('0')
            
            current_price = self.get_market_price()
            return (current_price - self.position.avg_price) * self.position.quantity
        except Exception as e:
            self.logger.error(f"计算未实现盈亏失败: {str(e)}")
            return Decimal('0')

    def buy(self, quantity: Decimal, price: Optional[Decimal] = None):
        """
        执行买入操作
        
        Args:
            quantity: 买入数量
            price: 买入价格，如果为None则使用市场价
        """
        try:
            # 验证交易参数
            is_valid, reason = self._validate_trade_params(quantity, price)
            if not is_valid:
                raise ValueError(reason)
                
            if price is None:
                price = self.get_market_price()
            
            # 计算手续费
            commission = abs(price * quantity * self.commission_rate)
            self.total_commission += commission
            
            # 计算平仓盈亏
            realized_pnl = Decimal('0')
            if self.position.quantity < 0:  # 如果是空头平仓
                closing_quantity = min(abs(self.position.quantity), quantity)
                realized_pnl = (self.position.avg_price - price) * closing_quantity
                self.total_pnl += realized_pnl
            
            # 更新持仓
            old_position = self.position.quantity
            old_avg_price = self.position.avg_price
            
            # 更新持仓均价
            if old_position + quantity != 0:
                new_avg_price = (old_avg_price * old_position + price * quantity) / (old_position + quantity)
            else:
                new_avg_price = Decimal('0')
            
            # 创建新的Position对象
            self.position = Position(
                symbol=self.symbol,
                quantity=old_position + quantity,
                avg_price=new_avg_price,
                leverage=self.position.leverage
            )
            
            # 检查持仓风险
            is_valid, reason = self.risk_manager.check_position(self.position)
            if not is_valid:
                # 如果不通过风险检查，回滚持仓
                self.position = Position(
                    symbol=self.symbol,
                    quantity=old_position,
                    avg_price=old_avg_price,
                    leverage=self.position.leverage
                )
                raise ValueError(f"持仓未通过风险检查: {reason}")
            
            # 更新盈亏
            is_valid, reason = self.risk_manager.update_pnl(realized_pnl)
            if not is_valid:
                self.logger.warning(f"盈亏超过限制: {reason}")
            
            # 记录交易
            self._record_trade('BUY', price, quantity, commission, realized_pnl)
            self._save_state()
            
            self.logger.info(f"买入 {quantity} {self.symbol} @ {price}, 手续费: {commission}, 实现盈亏: {realized_pnl}")
        except Exception as e:
            self.logger.error(f"买入操作失败: {str(e)}")
            raise

    def sell(self, quantity: Decimal, price: Optional[Decimal] = None):
        """
        执行卖出操作
        
        Args:
            quantity: 卖出数量
            price: 卖出价格，如果为None则使用市场价
        """
        try:
            # 验证交易参数
            is_valid, reason = self._validate_trade_params(quantity, price)
            if not is_valid:
                raise ValueError(reason)
                
            if price is None:
                price = self.get_market_price()
            
            # 计算手续费
            commission = abs(price * quantity * self.commission_rate)
            self.total_commission += commission
            
            # 计算平仓盈亏
            realized_pnl = Decimal('0')
            if self.position.quantity > 0:  # 如果是多头平仓
                closing_quantity = min(self.position.quantity, quantity)
                realized_pnl = (price - self.position.avg_price) * closing_quantity
                self.total_pnl += realized_pnl
            
            # 更新持仓
            old_position = self.position.quantity
            old_avg_price = self.position.avg_price
            
            # 更新持仓均价
            if old_position - quantity != 0:
                new_avg_price = (old_avg_price * old_position - price * quantity) / (old_position - quantity)
            else:
                new_avg_price = Decimal('0')
            
            # 创建新的Position对象
            self.position = Position(
                symbol=self.symbol,
                quantity=old_position - quantity,
                avg_price=new_avg_price,
                leverage=self.position.leverage
            )
            
            # 检查持仓风险
            is_valid, reason = self.risk_manager.check_position(self.position)
            if not is_valid:
                # 如果不通过风险检查，回滚持仓
                self.position = Position(
                    symbol=self.symbol,
                    quantity=old_position,
                    avg_price=old_avg_price,
                    leverage=self.position.leverage
                )
                raise ValueError(f"持仓未通过风险检查: {reason}")
            
            # 更新盈亏
            is_valid, reason = self.risk_manager.update_pnl(realized_pnl)
            if not is_valid:
                self.logger.warning(f"盈亏超过限制: {reason}")
            
            # 记录交易
            self._record_trade('SELL', price, quantity, commission, realized_pnl)
            self._save_state()
            
            self.logger.info(f"卖出 {quantity} {self.symbol} @ {price}, 手续费: {commission}, 实现盈亏: {realized_pnl}")
        except Exception as e:
            self.logger.error(f"卖出操作失败: {str(e)}")
            raise

    async def _save_state(self):
        """保存策略状态到数据库"""
        try:
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
            
            state.position = self.position.quantity
            state.avg_entry_price = self.position.avg_price
            state.unrealized_pnl = self.calculate_unrealized_pnl()
            state.total_pnl = self.total_pnl
            state.total_commission = self.total_commission
            state.updated_at = datetime.utcnow()
            
            self.db_session.commit()
            
            # 立即广播状态更新
            await event_bus.publish(
                'strategy_update',
                {
                    'symbol': self.symbol,
                    'strategy_info': self.state_info,
                    'market_data': self.client.get_market_price(self.symbol)
                }
            )
            
            self.logger.debug(f"策略状态已保存: position={self.position.quantity}, avg_price={self.position.avg_price}")
        except Exception as e:
            self.logger.error(f"保存策略状态失败: {str(e)}")
            self.db_session.rollback()
            raise

    def _load_state(self):
        """从数据库加载策略状态"""
        try:
            state = self.db_session.query(StrategyState).filter_by(
                strategy_name=self.__class__.__name__,
                symbol=self.symbol
            ).first()
            
            if state:
                self.position = Position(
                    symbol=self.symbol,
                    quantity=state.position,
                    avg_price=state.avg_entry_price,
                    leverage=1  # 从数据库加载时默认杠杆为1
                )
                self.total_pnl = state.total_pnl
                self.total_commission = state.total_commission
                
                # 根据数据库状态设置当前状态
                status_map = {
                    StrategyStatus.RUNNING.value: RunningState(),
                    StrategyStatus.STOPPED.value: StoppedState(),
                    StrategyStatus.PAUSED.value: PausedState(),
                    StrategyStatus.ERROR.value: ErrorState()
                }
                if state.status in status_map:
                    self.set_state(status_map[state.status])
        except Exception as e:
            self.logger.error(f"加载策略状态失败: {str(e)}")
            # 设置为停止状态
            self.set_state(StoppedState())

    @abstractmethod
    async def _on_start(self):
        """
        策略启动时的初始化
        子类必须实现此方法来进行策略特定的初始化
        """
        pass

    @abstractmethod
    async def _on_stop(self):
        """
        策略停止时的清理
        子类必须实现此方法来进行策略特定的清理工作
        """
        pass

    @abstractmethod
    async def run(self):
        """
        策略运行的主循环
        子类必须实现此方法来定义策略的主要逻辑
        """
        pass

    @abstractmethod
    async def on_tick(self, market_data: Dict):
        """
        处理市场数据更新
        子类必须实现此方法来处理市场数据
        
        Args:
            market_data: 市场数据
        """
        pass 