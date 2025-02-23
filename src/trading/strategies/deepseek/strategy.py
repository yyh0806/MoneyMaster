"""DeepSeek策略实现"""

from decimal import Decimal
from typing import Dict
import time
import asyncio
from loguru import logger

from ...core.strategy import BaseStrategy
from ...core.risk import RiskLimit
from .market_context import MarketContextManager
from .analyzer import MarketAnalyzer
from .utils import strategy_logger, get_default_analysis

class DeepseekStrategy(BaseStrategy):
    """基于DeepSeek模型的交易策略"""
    
    def __init__(self, client, symbol: str, db_session, risk_limit: RiskLimit,
                 quantity: Decimal = Decimal('0.01'),
                 min_interval: int = 30,  # 最小交易间隔30秒
                 commission_rate: Decimal = Decimal('0.001')):
        """
        初始化策略
        
        Args:
            client: 交易客户端
            symbol: 交易对
            db_session: 数据库会话
            risk_limit: 风险限制配置
            quantity: 每次交易数量
            min_interval: 最小交易间隔（秒）
            commission_rate: 手续费率
        """
        # 初始化组件
        self.market_context = MarketContextManager()
        self.analyzer = MarketAnalyzer()
        self.logger = strategy_logger
        
        # 交易相关参数
        self.trade_quantity = quantity
        self.min_interval = min_interval
        self.last_trade_time = 0
        self.last_analysis = get_default_analysis()  # 添加last_analysis属性
        
        # 调用父类初始化
        super().__init__(client, symbol, db_session, risk_limit, commission_rate)
    
    @property
    def state_info(self) -> dict:
        """获取策略状态信息"""
        base_info = super().state_info
        capital_info = self.capital_info
        risk_info = self.risk_manager.get_risk_info()
        
        # 获取持仓和风险信息
        position_info = {
            "盈亏信息": {
                "当前持仓": float(self.position.quantity),
                "持仓均价": float(self.position.avg_price),
                "持仓市值": float(self.position.position_value),
                "未实现盈亏": float(self.calculate_unrealized_pnl()),
                "总盈亏": float(self.total_pnl),
                "总手续费": float(self.total_commission)
            },
            "资金信息": {
                "总资金": float(capital_info['total_capital']),
                "已用资金": float(capital_info['used_capital']),
                "剩余可用": float(capital_info['remaining_capital']),
                "单笔最大交易": float(capital_info['max_single_trade'])
            },
            "风险信息": {
                "杠杆倍数": float(self.position.leverage),
                "最大持仓市值": float(risk_info['max_position_value']),
                "最大杠杆倍数": risk_info['max_leverage'],
                "最小保证金率": float(risk_info['min_margin_ratio']),
                "最大日亏损": float(risk_info['max_daily_loss'])
            }
        }
        
        return {
            **base_info,
            "strategy_name": self.__class__.__name__,
            "symbol": self.symbol,
            "last_trade_time": self.last_trade_time,
            "min_interval": self.min_interval,
            "trade_quantity": float(self.trade_quantity),
            "position_info": position_info,
            "last_analysis": self.last_analysis  # 添加last_analysis到状态信息中
        }
    
    async def run(self):
        """策略运行的主循环"""
        try:
            self.logger.info("策略开始运行")
            while self.is_running:
                market_data = self.client.get_market_price(self.symbol)
                await self.on_tick(market_data)
                # 更新状态到数据库
                await self._save_state()
                await asyncio.sleep(1)  # 每秒检查一次
        except asyncio.CancelledError:
            self.logger.info("策略运行任务被取消")
        except Exception as e:
            error_msg = f"Strategy error: {str(e)}"
            self.logger.error(error_msg)
            self.handle_error(error_msg)
        finally:
            # 确保状态被保存
            await self._save_state()
    
    async def _on_start(self):
        """策略启动时的初始化"""
        try:
            self.logger.info("初始化策略")
            
            # 初始化分析器
            await self.analyzer.initialize()
            
            # 设置初始状态
            self.market_context.clear_context()
            self.last_trade_time = 0
            self.last_analysis = get_default_analysis()  # 重置分析结果
            
            # 保存状态到数据库
            await self._save_state()
            
            self.logger.info("策略初始化完成")
            
        except Exception as e:
            error_msg = f"策略初始化失败: {str(e)}"
            self.logger.error(error_msg)
            self.handle_error(error_msg)
            raise
    
    async def _on_stop(self):
        """策略停止时的清理"""
        self.logger.info("清理策略")
        
        try:
            # 清理分析器资源
            await self.analyzer.cleanup()
            # 重置分析结果
            self.last_analysis = get_default_analysis()
        except Exception as e:
            self.logger.error(f"清理资源时发生错误: {e}")
        
        # 保存最终状态
        await self._save_state()
    
    async def on_tick(self, market_data: Dict):
        """处理市场数据更新"""
        try:
            if not self.is_running:
                return
                
            if 'data' not in market_data or len(market_data['data']) == 0:
                self.logger.warning("No market data available")
                return
                
            current_price = float(market_data['data'][0]['last'])
            
            # 获取K线数据
            kline_data = self.client.get_kline(
                instId=self.symbol,
                bar="1m",  # 使用1分钟K线
                limit="1"  # 只获取最新的一根K线
            )
            
            # 更新市场上下文
            self.market_context.update_context(market_data, kline_data)
            
            # 获取市场分析
            analysis = await self.analyzer.analyze_market(
                current_price,
                self.market_context.get_context()
            )
            
            # 更新最新分析结果
            self.last_analysis = analysis  # 更新last_analysis
            
            # 检查是否满足最小交易间隔
            current_time = time.time()
            if current_time - self.last_trade_time < self.min_interval:
                return
            
            # 获取资金信息
            capital_info = self.capital_info
            remaining_capital = Decimal(str(capital_info["remaining_capital"]))
            max_single_trade = Decimal(str(capital_info["max_single_trade"]))
            
            # 计算实际可交易数量
            trade_value = self.trade_quantity * Decimal(str(current_price))
            if trade_value > max_single_trade:
                adjusted_quantity = max_single_trade / Decimal(str(current_price))
                self.logger.info(f"交易数量已调整: {self.trade_quantity} -> {adjusted_quantity} (受单笔交易限制)")
                self.trade_quantity = adjusted_quantity
            
            # 根据分析结果执行交易
            if analysis['confidence'] > 0.8:  # 只在信心度高于0.8时执行交易
                try:
                    if analysis['recommendation'] == '买入' and self.position.quantity <= 0:
                        # 检查是否有足够的资金
                        if trade_value > remaining_capital:
                            self.logger.warning(f"资金不足，无法执行买入操作: 需要 {trade_value}，可用 {remaining_capital}")
                            return
                            
                        if self.position.quantity < 0:
                            self.buy(abs(self.position.quantity))  # 先平仓
                        self.buy(self.trade_quantity)
                        self.last_trade_time = current_time
                        self.logger.info(f"执行买入 - 价格: {current_price}, 信心度: {analysis['confidence']}")
                        
                    elif analysis['recommendation'] == '卖出' and self.position.quantity >= 0:
                        if self.position.quantity > 0:
                            self.sell(self.position.quantity)  # 先平仓
                        self.sell(self.trade_quantity)
                        self.last_trade_time = current_time
                        self.logger.info(f"执行卖出 - 价格: {current_price}, 信心度: {analysis['confidence']}")
                        
                    # 更新持仓市值
                    self.update_position_value()
                    
                except ValueError as e:
                    self.logger.warning(f"交易执行失败: {str(e)}")
                    
            else:
                self.logger.debug(f"信心度不足，保持观望: {analysis['confidence']}")
            
        except Exception as e:
            self.logger.error(f"处理市场数据更新失败: {e}")
            self.handle_error(str(e)) 