from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
from loguru import logger
import sys

from .models import TradeRecord, StrategyState, StrategyStatus
from ..client import OKXClient

# 配置日志
logger.remove()  # 移除默认的日志处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[strategy]}</cyan> | <level>{message}</level>",
    level="INFO"
)

# 创建带有默认strategy字段的日志记录器
base_logger = logger.bind(strategy="BaseStrategy")

class StrategyStateBase(ABC):
    """策略状态基类"""
    def __init__(self):
        self.strategy = None
        self.logger = base_logger

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def pause(self):
        pass

    def _save_status(self, status: StrategyStatus, error: str = None):
        """保存策略状态到数据库"""
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
        
        state.status = status.value
        state.last_error = error
        state.last_run_time = datetime.utcnow()
        self.strategy.db_session.commit()
        self.logger.info(f"策略状态已更新: {status.value}")

class RunningState(StrategyStateBase):
    async def start(self):
        raise Exception("Strategy is already running")

    async def stop(self):
        self._save_status(StrategyStatus.STOPPED)
        self.strategy.set_state(StoppedState())
        self.logger.info("策略已停止")

    async def pause(self):
        self._save_status(StrategyStatus.PAUSED)
        self.strategy.set_state(PausedState())
        self.logger.info("策略已暂停")

class StoppedState(StrategyStateBase):
    async def start(self):
        self._save_status(StrategyStatus.RUNNING)
        self.strategy.set_state(RunningState())
        self.logger.info("策略已启动")

    async def stop(self):
        raise Exception("Strategy is already stopped")

    async def pause(self):
        raise Exception("Cannot pause a stopped strategy")

class PausedState(StrategyStateBase):
    async def start(self):
        self._save_status(StrategyStatus.RUNNING)
        self.strategy.set_state(RunningState())

    async def stop(self):
        self._save_status(StrategyStatus.STOPPED)
        self.strategy.set_state(StoppedState())

    async def pause(self):
        raise Exception("Strategy is already paused")

class ErrorState(StrategyStateBase):
    async def start(self):
        self._save_status(StrategyStatus.RUNNING)
        self.strategy.set_state(RunningState())

    async def stop(self):
        self._save_status(StrategyStatus.STOPPED)
        self.strategy.set_state(StoppedState())

    async def pause(self):
        raise Exception("Cannot pause an errored strategy")

class BaseStrategy(ABC):
    def __init__(self, 
                 client: OKXClient,
                 symbol: str,
                 db_session,
                 commission_rate: Decimal = Decimal('0.001')):
        self.client = client
        self.symbol = symbol
        self.db_session = db_session
        self.commission_rate = commission_rate
        self.position = Decimal('0')
        self.avg_entry_price = Decimal('0')
        self.total_pnl = Decimal('0')
        self.total_commission = Decimal('0')
        self._state = None
        self._is_running = False
        self._task = None
        self.logger = base_logger  # 使用带有strategy字段的日志记录器
        
        # 从数据库加载策略状态
        self._load_state()
        
        # 如果没有找到状态记录，设置为停止状态
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
        """获取策略是否在运行"""
        return self._is_running and self._state and isinstance(self._state, RunningState)
    
    @property
    def current_state(self) -> str:
        """获取当前状态"""
        if not self._state:
            return StrategyStatus.STOPPED.value
        
        # 使用状态映射确保返回正确的枚举值
        state_map = {
            'RunningState': StrategyStatus.RUNNING.value,
            'StoppedState': StrategyStatus.STOPPED.value,
            'PausedState': StrategyStatus.PAUSED.value,
            'ErrorState': StrategyStatus.ERROR.value
        }
        return state_map.get(self._state.__class__.__name__, StrategyStatus.STOPPED.value)
    
    @property
    def state_info(self) -> dict:
        """获取策略状态信息"""
        return {
            "strategy_name": self.__class__.__name__,
            "symbol": self.symbol,
            "is_running": self.is_running,
            "status": self.current_state,  # 这里直接使用 current_state，它已经确保返回有效的枚举值
            "position": float(self.position),
            "avg_entry_price": float(self.avg_entry_price),
            "total_pnl": float(self.total_pnl),
            "total_commission": float(self.total_commission),
            "unrealized_pnl": float(self.calculate_unrealized_pnl())
        }
    
    def set_state(self, state: StrategyStateBase):
        """设置策略状态"""
        self._state = state
        self._state.strategy = self

    async def start(self):
        """启动策略"""
        try:
            if self.is_running:
                raise Exception("Strategy is already running")
            
            # 确保之前的任务已经清理
            if self._task:
                self._task.cancel()
                self._task = None
            
            self._is_running = True
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
                raise Exception("Strategy is not running")
            
            self._is_running = False
            await self._state.stop()
            
            if self._task:
                self._task.cancel()
                self._task = None
                
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
                raise Exception("Cannot pause a stopped strategy")
            await self._state.pause()
            self.logger.info(f"{self.__class__.__name__} 策略已暂停")
        except Exception as e:
            self.logger.error(f"暂停策略失败: {str(e)}")
            raise

    async def resume(self):
        """恢复策略"""
        try:
            if self.is_running:
                raise Exception("Strategy is already running")
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
            
            # 根据数据库状态设置当前状态
            status_map = {
                StrategyStatus.RUNNING.value: RunningState(),
                StrategyStatus.STOPPED.value: StoppedState(),
                StrategyStatus.PAUSED.value: PausedState(),
                StrategyStatus.ERROR.value: ErrorState()
            }
            if state.status in status_map:
                self.set_state(status_map[state.status])
    
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
        
        try:
            self.db_session.commit()
            self.logger.debug(f"策略状态已保存: position={self.position}, avg_price={self.avg_entry_price}")
        except Exception as e:
            self.logger.error(f"保存策略状态失败: {e}")
            self.db_session.rollback()
            raise
    
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
        try:
            if self.position == 0:
                return Decimal('0')
            
            market_data = self.client.get_market_price(self.symbol)
            if not market_data or 'data' not in market_data or not market_data['data']:
                self.logger.error(f"获取市场价格失败: {market_data}")
                return Decimal('0')
                
            market_data_item = market_data['data'][0]
            if not isinstance(market_data_item, dict) or 'last' not in market_data_item:
                self.logger.error(f"无效的市场数据项: {market_data_item}")
                return Decimal('0')
                
            current_price = Decimal(str(market_data_item['last']))
            return (current_price - self.avg_entry_price) * self.position
        except Exception as e:
            self.logger.error(f"计算未实现盈亏失败: {str(e)}")
            return Decimal('0')
    
    def buy(self, quantity: Decimal, price: Optional[Decimal] = None):
        """执行买入操作"""
        if price is None:
            price = Decimal(str(self.client.get_market_price(self.symbol)['last']))
        
        # 手续费计算：确保为正值
        commission = abs(price * quantity * self.commission_rate)
        self.total_commission += commission
        
        realized_pnl = Decimal('0')
        if self.position < 0:  # 如果是空头平仓
            # 计算实现盈亏：(开仓价格 - 平仓价格) × 平仓数量
            closing_quantity = min(abs(self.position), quantity)
            realized_pnl = (self.avg_entry_price - price) * closing_quantity
            self.total_pnl += realized_pnl
        
        # 更新持仓均价
        if self.position + quantity != 0:
            self.avg_entry_price = (self.avg_entry_price * self.position + price * quantity) / (self.position + quantity)
        self.position += quantity
        
        # 记录交易
        self._record_trade('BUY', price, quantity, commission, realized_pnl)
        self._save_state()
        
        self.logger.info(f"买入 {quantity} {self.symbol} @ {price}, 手续费: {commission}, 实现盈亏: {realized_pnl}")
    
    def sell(self, quantity: Decimal, price: Optional[Decimal] = None):
        """执行卖出操作"""
        if price is None:
            price = Decimal(str(self.client.get_market_price(self.symbol)['last']))
        
        # 手续费计算：确保为正值
        commission = abs(price * quantity * self.commission_rate)
        self.total_commission += commission
        
        realized_pnl = Decimal('0')
        if self.position > 0:  # 如果是多头平仓
            # 计算实现盈亏：(平仓价格 - 开仓价格) × 平仓数量
            closing_quantity = min(self.position, quantity)
            realized_pnl = (price - self.avg_entry_price) * closing_quantity
            self.total_pnl += realized_pnl
        
        # 更新持仓均价
        if self.position - quantity != 0:
            self.avg_entry_price = (self.avg_entry_price * self.position - price * quantity) / (self.position - quantity)
        self.position -= quantity
        
        # 记录交易
        self._record_trade('SELL', price, quantity, commission, realized_pnl)
        self._save_state()
        
        self.logger.info(f"卖出 {quantity} {self.symbol} @ {price}, 手续费: {commission}, 实现盈亏: {realized_pnl}")
    
    @abstractmethod
    async def run(self):
        """策略运行的主循环"""
        pass
    
    @abstractmethod
    def on_tick(self, market_data: Dict):
        """处理市场数据更新"""
        pass
    
    @abstractmethod
    async def on_start(self):
        """策略启动时的初始化"""
        pass
    
    @abstractmethod
    async def on_stop(self):
        """策略停止时的清理"""
        pass 