"""市场分析模块"""

import json
import time
import asyncio
import aiohttp
from typing import Dict, Optional
from .utils import strategy_logger, get_default_analysis

class MarketAnalyzer:
    """市场分析器"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434/api/generate",
                 model_name: str = "deepseek-r1:8b",
                 analysis_interval: int = 30):
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.logger = strategy_logger
        self._analysis_lock = asyncio.Lock()
        self._last_analysis_time = 0
        self._analysis_interval = analysis_interval
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_analysis_result = get_default_analysis()  # 添加上一次的分析结果缓存
        
    async def initialize(self):
        """初始化分析器"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(trust_env=False)
            self.logger.info("创建新的 aiohttp session")
            
    async def cleanup(self):
        """清理资源"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self.logger.info("已关闭 aiohttp session")
            
    async def analyze_market(self, current_price: float, market_context: list) -> Dict:
        """分析市场状态
        
        Args:
            current_price: 当前价格
            market_context: 市场上下文数据
            
        Returns:
            Dict: 分析结果
        """
        try:
            # 记录输入数据
            self.logger.info("=== DeepSeek策略分析开始 ===")
            self.logger.info(f"当前价格: {current_price}")
            self.logger.info("市场上下文数据:")
            for idx, data in enumerate(market_context):
                self.logger.info(f"数据点 {idx + 1}:")
                for key, value in data.items():
                    self.logger.info(f"  {key}: {value}")
            
            # 检查分析间隔
            current_time = time.time()
            if current_time - self._last_analysis_time < self._analysis_interval:
                self.logger.info(f"分析间隔未到 (上次: {self._last_analysis_time}, 当前: {current_time}, 间隔: {self._analysis_interval})")
                self.logger.info("返回上一次的有效分析结果:")
                for key, value in self._last_analysis_result.items():
                    self.logger.info(f"{key}: {value}")
                return self._last_analysis_result  # 返回上一次的有效分析结果
                
            async with self._analysis_lock:
                if not self.session or self.session.closed:
                    self.logger.info("初始化新的会话")
                    await self.initialize()
                    
                # 构建提示信息
                prompt = self._build_analysis_prompt(current_price, market_context)
                self.logger.info("发送到Ollama的提示词:")
                self.logger.info(prompt)
                
                # 发送请求到Ollama
                self.logger.info(f"发送请求到Ollama (URL: {self.ollama_url}, 模型: {self.model_name})")
                async with self.session.post(
                    self.ollama_url,
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    }
                ) as response:
                    if response.status != 200:
                        self.logger.error(f"Ollama API请求失败: {response.status}")
                        return self._last_analysis_result  # 返回上一次的有效分析结果
                        
                    result = await response.json()
                    self.logger.info("Ollama响应:")
                    self.logger.info(result)
                    
                # 解析响应
                try:
                    analysis_text = result.get('response', '')
                    self.logger.info("解析前的响应文本:")
                    self.logger.info(analysis_text)
                    
                    analysis_result = self._parse_analysis_response(analysis_text)
                    self.logger.info("最终分析结果:")
                    for key, value in analysis_result.items():
                        self.logger.info(f"{key}: {value}")
                        
                    self._last_analysis_time = current_time
                    self._last_analysis_result = analysis_result  # 更新缓存的分析结果
                    self.logger.info("=== DeepSeek策略分析结束 ===\n")
                    return analysis_result
                except Exception as e:
                    self.logger.error(f"解析分析结果失败: {e}")
                    self.logger.info("=== DeepSeek策略分析异常结束 ===\n")
                    return self._last_analysis_result  # 返回上一次的有效分析结果
                    
        except Exception as e:
            self.logger.error(f"市场分析失败: {e}")
            self.logger.info("=== DeepSeek策略分析异常结束 ===\n")
            return self._last_analysis_result  # 返回上一次的有效分析结果
            
    def _build_analysis_prompt(self, current_price: float, market_context: list) -> str:
        """构建分析提示信息"""
        context_str = json.dumps(market_context, indent=2)
        return f"""作为一个专业的加密货币交易分析师，请分析以下市场数据并给出详细的交易建议：

当前价格: {current_price}

最近的市场数据:
{context_str}

请以JSON格式返回以下信息：
{{
    "analysis": "详细的市场分析，至少50个字，包含价格走势、成交量、市场情绪等关键信息",
    "recommendation": "买入/卖出/观望",
    "confidence": 0.0-1.0,
    "reasoning": ["理由1", "理由2", "理由3"],  # 至少包含3点具体理由
    "market_trend": "上涨/下跌/震荡",
    "support_price": 支撑价位,
    "resistance_price": 阻力价位,
    "risk_level": "高/中/低"
}}

注意事项：
1. analysis字段必须包含详细的市场分析，至少50个字
2. recommendation字段只能是"买入"、"卖出"或"观望"三个值之一
3. confidence必须是0到1之间的数字
4. reasoning字段必须是一个列表，包含至少3点具体理由，每点理由都要有数据支持
5. 所有价格相关的字段必须基于实际的市场数据进行分析"""
        
    def _parse_analysis_response(self, response_text: str) -> Dict:
        """解析分析响应"""
        try:
            self.logger.info("开始解析响应...")
            # 提取JSON部分
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx == -1 or end_idx == -1:
                self.logger.error("响应中未找到JSON数据")
                return get_default_analysis()
                
            json_str = response_text[start_idx:end_idx + 1]
            self.logger.info("提取的JSON字符串:")
            self.logger.info(json_str)
            
            analysis = json.loads(json_str)
            self.logger.info("解析后的JSON对象:")
            self.logger.info(analysis)
            
            # 验证必要字段
            required_fields = ['analysis', 'recommendation', 'confidence', 'reasoning',
                             'market_trend', 'support_price', 'resistance_price',
                             'risk_level']
            self.logger.info("验证必要字段...")
            for field in required_fields:
                if field not in analysis:
                    self.logger.error(f"缺少必要字段: {field}")
                    return get_default_analysis()
                    
            # 验证字段内容
            self.logger.info("验证字段内容...")
            if len(analysis['analysis']) < 50:
                self.logger.warning(f"市场分析内容过短，长度: {len(analysis['analysis'])}")
                
            if analysis['recommendation'] not in ['买入', '卖出', '观望']:
                self.logger.error(f"无效的推荐操作: {analysis['recommendation']}")
                return get_default_analysis()
                
            if not isinstance(analysis['confidence'], (int, float)) or \
               not 0 <= analysis['confidence'] <= 1:
                self.logger.error(f"无效的信心度值: {analysis['confidence']}")
                return get_default_analysis()
                
            # 验证推理过程
            self.logger.info("验证推理过程...")
            if not isinstance(analysis['reasoning'], list):
                self.logger.info(f"推理过程不是列表格式，当前类型: {type(analysis['reasoning'])}")
                # 如果reasoning不是列表，尝试将字符串转换为列表
                if isinstance(analysis['reasoning'], str):
                    self.logger.info("尝试将字符串转换为列表")
                    reasons = [r.strip() for r in analysis['reasoning'].split('.') if r.strip()]
                    analysis['reasoning'] = reasons
                    self.logger.info(f"转换后的推理列表: {reasons}")
                else:
                    self.logger.error("无效的推理过程格式")
                    return get_default_analysis()
                    
            if len(analysis['reasoning']) < 3:
                self.logger.error(f"推理过程不够详细，当前理由数量: {len(analysis['reasoning'])}")
                return get_default_analysis()
                
            # 添加时间戳
            analysis['timestamp'] = time.time()
            self.logger.info("验证完成，返回分析结果")
            
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            return get_default_analysis()
        except Exception as e:
            self.logger.error(f"解析分析响应失败: {e}")
            return get_default_analysis() 