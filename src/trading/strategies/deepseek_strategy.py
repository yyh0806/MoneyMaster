from decimal import Decimal
from typing import Dict, List, Optional
import numpy as np
from loguru import logger
import json
import asyncio
import aiohttp
import websockets
import requests
import time
import sys
from ..core.strategy import BaseStrategy
from ..core.risk import RiskLimit
from ..core.order import Order, OrderSide

# 配置日志
logger.remove()  # 移除默认的日志处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[strategy]}</cyan> | <level>{message}</level>",
    level="INFO"
)

# 创建带有策略名称的上下文日志记录器
strategy_logger = logger.bind(strategy="DeepseekStrategy")

class DeepseekStrategy(BaseStrategy):
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
        # 在调用父类初始化前，先初始化自己的属性
        self.trade_quantity = quantity
        self.market_context = []
        self.max_context_length = 10  # 保留最近10条市场数据
        self.last_trade_time = 0
        self.last_analysis = self._get_default_analysis()
        self.min_interval = min_interval
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model_name = "deepseek-r1:8b"
        self.logger = strategy_logger
        self._analysis_lock = asyncio.Lock()
        self._last_analysis_time = 0
        self._analysis_interval = 30  # 分析间隔（秒）
        self.session = None
        
        # 最后调用父类初始化
        super().__init__(client, symbol, db_session, risk_limit, commission_rate)
    
    @property
    def state_info(self) -> dict:
        """获取策略状态信息"""
        base_info = super().state_info
        analysis_info = self.last_analysis if self.last_analysis else self._get_default_analysis()
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
            "last_analysis": analysis_info,
            "last_trade_time": self.last_trade_time,
            "min_interval": self.min_interval,
            "trade_quantity": float(self.trade_quantity),
            "position_info": position_info
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
            
            # 创建新的 session
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(trust_env=False)
                self.logger.info("创建新的 aiohttp session")
            
            # 先设置初始状态
            self.market_context = []
            self.last_trade_time = 0
            self.last_analysis = self._get_default_analysis()
            self._last_analysis_time = 0
            
            # 保存状态到数据库，触发前端更新
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
            # 关闭aiohttp会话
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
                self.logger.info("已关闭 aiohttp session")
        except Exception as e:
            self.logger.error(f"关闭session时发生错误: {e}")
        
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
            self.update_market_context(market_data)
            
            # 获取市场分析
            analysis = await self.analyze_market(current_price)
            # 更新最新分析结果
            self.last_analysis = analysis
            
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
    
    def update_market_context(self, new_data: Dict):
        """更新市场上下文"""
        # 提取当前K线数据
        try:
            current_data = new_data['data'][0]
            kline_data = self.client.get_kline(
                instId=self.symbol,
                bar="1m",  # 使用1分钟K线
                limit="1"  # 只获取最新的一根K线
            )
            
            if kline_data.get('code') == '0' and kline_data.get('data'):
                # K线数据格式: [timestamp, open, high, low, close, vol, volCcy]
                latest_kline = kline_data['data'][0]
                volume = float(latest_kline[5])  # 当前K线的交易量
                
                market_info = {
                    'ts': current_data['ts'],
                    'price': current_data['last'],
                    'volume': volume,  # 使用当前K线的交易量
                    'high': latest_kline[2],
                    'low': latest_kline[3]
                }
                
                self.market_context.append(market_info)
                if len(self.market_context) > self.max_context_length:
                    self.market_context = self.market_context[-self.max_context_length:]
            else:
                self.logger.warning("无法获取K线数据")
                
        except Exception as e:
            self.logger.error(f"更新市场上下文失败: {str(e)}")
    
    async def analyze_market(self, current_price: float) -> Dict:
        """使用deepseek分析市场"""
        current_time = time.time()
        
        # 使用锁来防止并发分析请求
        async with self._analysis_lock:
            # 检查是否需要进行新的分析
            if current_time - self._last_analysis_time < self._analysis_interval:
                return self.last_analysis

            # 更新最后分析时间
            self._last_analysis_time = current_time

            # 如果session已关闭，创建新的session
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(trust_env=False)
                self.logger.info("重新创建 aiohttp session")

            # 构建市场分析提示
            recent_data = self.market_context[-5:]
            if not recent_data:
                return self._get_default_analysis()

            market_status = "\n".join([
                f"时间: {data['ts']}, "
                f"价格: {data['price']}, "
                f"交易量: {data['volume']}, "
                f"最高: {data['high']}, "
                f"最低: {data['low']}"
                for data in recent_data
            ])

            capital_info = self.capital_info
            risk_info = self.risk_manager.get_risk_info()
            position_info = self.position

            prompt = f"""你是一个专业的交易策略AI分析师。请分析以下市场数据并提供交易建议。

严格按照以下JSON格式返回，必须包含所有字段，且内容必须详尽：

示例格式：
{{
    "analysis": "BTC价格在96500附近震荡，成交量保持稳定，短期走势呈现盘整态势。价格支撑位在96000，阻力位在97000。",
    "recommendation": "持有",
    "confidence": 0.75,
    "reasoning": "1. 价格波动幅度较小，表明市场处于观望状态。2. 成交量没有明显异常，表明当前价格区间较为合理。3. 技术指标显示中性。建议继续观察，等待更明确的信号。"
}}

注意事项：
1. analysis字段必须包含详细的市场分析，至少50个字
2. recommendation字段只能是"买入"、"卖出"或"持有"三个值之一
3. confidence必须是0到1之间的数字
4. reasoning字段必须详细说明推理过程，至少包含3点理由

当前市场状态:
{market_status}

当前持仓信息:
- 持仓数量: {position_info.quantity}
- 平均入场价: {position_info.avg_price}
- 未实现盈亏: {self.calculate_unrealized_pnl()}
- 总盈亏: {self.total_pnl}
- 持仓市值: {position_info.position_value}
- 杠杆倍数: {position_info.leverage}

资金状况:
- 总资金: {capital_info['total_capital']}
- 已用资金: {capital_info['used_capital']}
- 剩余可用: {capital_info['remaining_capital']}
- 单笔最大交易: {capital_info['max_single_trade']}

风险限制:
- 最大持仓市值: {risk_info['max_position_value']}
- 最大杠杆倍数: {risk_info['max_leverage']}
- 最小保证金率: {risk_info['min_margin_ratio']}
- 最大日亏损: {risk_info['max_daily_loss']}

请基于以上数据进行分析，必须严格按照示例格式返回JSON。不要返回任何其他内容。
"""

            try:
                # 使用asyncio创建一个新的事件循环来运行API调用
                async with self.session.post(
                    self.ollama_url,
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=aiohttp.ClientTimeout(total=40)  # 设置40秒超时
                ) as response:
                    result = await response.json()
                    response_text = result.get('response', '')

                    try:
                        # 尝试从response中提取JSON
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            json_str = response_text[json_start:json_end]
                            
                            try:
                                # 预处理 JSON 字符串
                                # 1. 移除所有换行符和多余的空格
                                json_str = ' '.join(json_str.split())
                                # 2. 确保字段名和值都使用双引号
                                json_str = json_str.replace("'", '"')
                                # 3. 只移除真正的控制字符，保留中文和其他有效字符
                                json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in '\n\r\t')
                                
                                # 记录处理后的 JSON 字符串
                                self.logger.info(f"处理后的JSON字符串: {json_str}")
                                
                                json_data = json.loads(json_str)
                                
                                # 规范化recommendation字段
                                raw_recommendation = str(json_data.get('recommendation', '持有')).strip()
                                recommendation = '持有'  # 默认值
                                if '买入' in raw_recommendation:
                                    recommendation = '买入'
                                elif '卖出' in raw_recommendation:
                                    recommendation = '卖出'
                                
                                # 确保所有字段都是字符串类型
                                analysis_text = str(json_data.get('analysis', '')).strip()
                                reasoning_text = str(json_data.get('reasoning', '')).strip()
                                
                                # 记录原始分析内容
                                self.logger.info(f"分析内容: {analysis_text}")
                                self.logger.info(f"推理过程: {reasoning_text}")
                                self.logger.info(f"交易建议: {recommendation}")
                                
                                # 更新最新分析结果
                                self.last_analysis = {
                                    'analysis': analysis_text,
                                    'recommendation': recommendation,
                                    'confidence': min(max(float(json_data.get('confidence', 0.7)), 0), 1),  # 确保在0-1之间
                                    'reasoning': reasoning_text,
                                    'error': False,
                                    'timestamp': time.time()
                                }
                                
                                # 立即广播状态更新
                                await self._save_state()
                                
                                return self.last_analysis
                                
                            except json.JSONDecodeError as e:
                                self.logger.error(f"JSON解析错误: {str(e)}\n原始字符串: {json_str}")
                                return self._get_default_analysis()
                                
                    except Exception as e:
                        self.logger.error(f"解析分析结果失败: {str(e)}")
                        return self._get_default_analysis()
                        
            except asyncio.TimeoutError:
                self.logger.error("Ollama API请求超时")
                return self._get_default_analysis()
            except Exception as e:
                self.logger.error(f"调用模型时出错: {str(e)}")
                return self._get_default_analysis()
    
    def _validate_trade_params(self, quantity: Decimal, price: Optional[Decimal] = None) -> tuple[bool, str]:
        """验证交易参数"""
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
                price=price,
                order_type="MARKET"  # 默认使用市价单
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
    
    def _get_default_analysis(self) -> Dict:
        """返回默认的分析结果"""
        return {
            "analysis": "",
            "recommendation": "持有",
            "confidence": 0.0,
            "reasoning": "正在收集市场数据...",
            "error": True,
            "timestamp": time.time()
        } 