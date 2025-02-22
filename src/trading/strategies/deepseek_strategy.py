from decimal import Decimal
from typing import Dict, List
import numpy as np
from loguru import logger
import json
import asyncio
import websockets
import requests
import time
import sys
from ..core.strategy import BaseStrategy

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
    def __init__(self, client, symbol: str, db_session, 
                 quantity: Decimal = Decimal('0.01'),
                 min_interval: int = 30):  # 最小交易间隔30秒
        super().__init__(client, symbol, db_session)
        self.trade_quantity = quantity
        self.market_context = []
        self.max_context_length = 10  # 保留最近10条市场数据
        self.min_interval = min_interval  # 最小交易间隔（秒）
        self.last_trade_time = 0  # 上次交易时间
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model_name = "deepseek-r1:8b"
        self.last_analysis = None  # 保存最新的分析结果
        self.logger = strategy_logger  # 使用带有策略名称的日志记录器
        
        # 创建不使用代理的session
        self.session = requests.Session()
        self.session.trust_env = False  # 不使用环境变量中的代理设置
        self.session.proxies = {
            'http': None,
            'https': None
        }
    
    @property
    def state_info(self) -> dict:
        """获取策略状态信息"""
        base_info = super().state_info
        analysis_info = self.last_analysis if self.last_analysis else self._get_default_analysis()
        return {
            **base_info,
            "strategy_name": self.__class__.__name__,
            "symbol": self.symbol,
            "last_analysis": analysis_info,
            "last_trade_time": self.last_trade_time,
            "min_interval": self.min_interval,
            "trade_quantity": float(self.trade_quantity),
            "unrealized_pnl": float(self.calculate_unrealized_pnl())
        }
    
    async def run(self):
        """策略运行的主循环"""
        try:
            self.logger.info("策略开始运行")
            while self.is_running:
                market_data = self.client.get_market_price(self.symbol)
                await self.on_tick(market_data)
                # 更新状态到数据库
                self._save_state()
                await asyncio.sleep(1)  # 每秒检查一次
        except asyncio.CancelledError:
            self.logger.info("策略运行任务被取消")
        except Exception as e:
            error_msg = f"Strategy error: {str(e)}"
            self.logger.error(error_msg)
            self.handle_error(error_msg)
        finally:
            # 确保状态被保存
            self._save_state()
    
    async def on_start(self):
        """策略启动时的初始化"""
        try:
            self.logger.info("初始化策略")
            
            # 检查Ollama服务是否可用
            try:
                response = requests.get("http://localhost:11434/api/version", timeout=5)
                if response.status_code != 200:
                    raise Exception(f"Ollama服务返回错误状态码: {response.status_code}")
                self.logger.info("Ollama服务连接成功")
            except requests.exceptions.RequestException as e:
                raise Exception(f"无法连接到Ollama服务，请确保服务已启动: {str(e)}")
            
            # 检查模型是否可用
            try:
                response = requests.post(
                    self.ollama_url,
                    json={
                        "model": self.model_name,
                        "prompt": "test",
                        "stream": False
                    },
                    timeout=5
                )
                if response.status_code != 200:
                    raise Exception(f"模型调用失败，状态码: {response.status_code}")
                self.logger.info(f"模型 {self.model_name} 测试调用成功")
            except requests.exceptions.RequestException as e:
                raise Exception(f"模型调用测试失败: {str(e)}")
            
            self.market_context = []
            self.last_trade_time = 0
            self.last_analysis = None
            
            # 创建并启动策略运行任务
            self._task = asyncio.create_task(self.run())
            self.logger.info("策略初始化完成")
            
        except Exception as e:
            error_msg = f"策略初始化失败: {str(e)}"
            self.logger.error(error_msg)
            self.handle_error(error_msg)
            raise
    
    async def on_stop(self):
        """策略停止时的清理"""
        self.logger.info("清理策略")
        
        # 保存最终状态
        self._save_state()
    
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
            
            # 根据分析结果执行交易
            if analysis['confidence'] > 0.8:  # 只在信心度高于0.8时执行交易
                if analysis['recommendation'] == 'BUY' and self.position <= 0:
                    if self.position < 0:
                        self.buy(abs(self.position))  # 先平仓
                    self.buy(self.trade_quantity)
                    self.logger.info(f"执行买入 - 价格: {current_price}, 信心度: {analysis['confidence']}")
                    
                elif analysis['recommendation'] == 'SELL' and self.position >= 0:
                    if self.position > 0:
                        self.sell(self.position)  # 先平仓
                    self.sell(self.trade_quantity)
                    self.logger.info(f"执行卖出 - 价格: {current_price}, 信心度: {analysis['confidence']}")
            
        except Exception as e:
            self.logger.error(f"处理市场数据更新失败: {e}")
            self.handle_error(str(e))
    
    def update_market_context(self, new_data: Dict):
        """更新市场上下文"""
        self.market_context.append(new_data)
        if len(self.market_context) > self.max_context_length:
            self.market_context = self.market_context[-self.max_context_length:]
    
    async def analyze_market(self, current_price: float) -> Dict:
        """使用deepseek分析市场"""
        current_time = time.time()
        
        # 检查是否满足最小交易间隔
        if current_time - self.last_trade_time < self.min_interval:
            if self.last_analysis:
                return self.last_analysis
            return self._get_default_analysis()

        # 构建市场分析提示
        recent_data = self.market_context[-5:]  # 只使用最近5条数据
        if not recent_data:  # 如果没有市场数据，返回默认分析
            self.logger.warning("没有足够的市场数据进行分析")
            return self._get_default_analysis()

        market_status = "\n".join([
            f"时间: {data['data'][0]['ts']}, "
            f"价格: {data['data'][0]['last']}, "
            f"成交量: {data['data'][0]['vol24h']}"
            for data in recent_data
        ])

        prompt = f"""你是一个交易策略AI助手。请分析以下市场数据并提供交易建议。
请直接返回JSON格式数据，不要包含任何其他文字。JSON必须包含以下字段：
- analysis: 市场分析
- recommendation: 交易建议 (BUY/SELL/HOLD)
- confidence: 信心度 (0-1)
- reasoning: 详细推理过程

当前市场状态:
{market_status}

当前持仓: {self.position}
平均入场价: {self.avg_entry_price}
未实现盈亏: {self.calculate_unrealized_pnl()}
"""

        try:
            # 记录请求开始时间
            request_start_time = time.time()
            self.logger.info("开始调用Ollama API...")

            # 使用session调用Ollama API，设置更长的超时时间
            response = self.session.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=(5, 30)  # (连接超时, 读取超时)
            )
            
            # 计算请求耗时
            request_time = time.time() - request_start_time
            self.logger.info(f"Ollama API调用完成，耗时: {request_time:.2f}秒")
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                
                # 解析分析结果
                try:
                    # 尝试从response中提取JSON
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        json_data = json.loads(json_str)
                        
                        # 记录原始分析内容
                        self.logger.info(f"分析内容: {json_data.get('analysis', '')}")
                        self.logger.info(f"推理过程: {json_data.get('reasoning', '')}")
                        
                        # 更新最新分析结果
                        self.last_analysis = {
                            'analysis_content': json_data.get('analysis', ''),  # 分析内容
                            'recommendation': json_data.get('recommendation', 'HOLD'),  # 交易建议
                            'confidence': json_data.get('confidence', 0.7),  # 置信度
                            'reasoning': json_data.get('reasoning', ''),  # 推理过程
                            'error': False
                        }
                    else:
                        # 如果没有找到JSON，直接使用原始文本
                        self.logger.info(f"分析内容: {response_text}")
                        
                        self.last_analysis = {
                            'analysis_content': response_text,  # 使用原始文本作为分析内容
                            'recommendation': 'HOLD',  # 默认建议
                            'confidence': 0.7,  # 默认置信度
                            'reasoning': response_text,  # 使用原始文本作为推理过程
                            'error': False
                        }
                    
                    return self.last_analysis
                    
                except Exception as e:
                    error_msg = f"解析分析结果失败: {str(e)}"
                    self.logger.error(error_msg)
                    self.last_analysis = {
                        'analysis_content': '分析过程出错',
                        'recommendation': 'HOLD',
                        'confidence': 0,
                        'reasoning': error_msg,
                        'error': True
                    }
                    return self.last_analysis
                    
            else:
                self.logger.error(f"API请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
                return self._get_default_analysis()
                
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Ollama API请求超时 (已等待{e.timeout}秒)")
            return self._get_default_analysis()
        except Exception as e:
            self.logger.error(f"调用模型时出错: {str(e)}")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict:
        """返回默认的分析结果"""
        return {
            "analysis": "模型分析过程中出现错误，采用保守策略",
            "recommendation": "HOLD",
            "confidence": 0.0,
            "reasoning": "由于技术原因无法获取分析结果，为了安全起见，保持当前仓位不变",
            "error": True  # 添加错误标记
        } 