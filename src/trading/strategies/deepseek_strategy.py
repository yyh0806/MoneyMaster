from decimal import Decimal
from typing import Dict, List
import numpy as np
from loguru import logger
import json
import asyncio
import websockets
from ..core.strategy import BaseStrategy

class DeepseekStrategy(BaseStrategy):
    def __init__(self, client, symbol: str, db_session, 
                 quantity: Decimal = Decimal('0.01'),
                 websocket_port: int = 8765):
        super().__init__(client, symbol, db_session)
        self.trade_quantity = quantity
        self.websocket_port = websocket_port
        self.websocket = None
        self.market_context = []
        self.max_context_length = 10  # 保留最近10条市场数据
        
    async def send_thinking_process(self, process: Dict):
        """发送思考过程到前端"""
        if self.websocket is None:
            try:
                self.websocket = await websockets.connect(f'ws://localhost:{self.websocket_port}')
            except Exception as e:
                logger.error(f"Failed to connect to websocket: {e}")
                return
                
        try:
            await self.websocket.send(json.dumps(process))
        except Exception as e:
            logger.error(f"Failed to send thinking process: {e}")
            self.websocket = None
    
    def update_market_context(self, new_data: Dict):
        """更新市场上下文"""
        self.market_context.append(new_data)
        if len(self.market_context) > self.max_context_length:
            self.market_context = self.market_context[-self.max_context_length:]
    
    async def analyze_market(self, current_price: float) -> Dict:
        """使用deepseek分析市场"""
        context = "\n".join([
            f"时间: {data['data'][0]['ts']}, 价格: {data['data'][0]['last']}"
            for data in self.market_context
        ])
        
        prompt = f"""
        当前市场情况：
        {context}
        
        当前价格：{current_price}
        当前持仓：{self.position}
        
        请分析当前市场情况，并给出交易建议。考虑以下因素：
        1. 价格趋势
        2. 市场波动性
        3. 当前持仓情况
        4. 潜在风险
        
        请给出详细的分析过程和具体的交易建议（买入、卖出或持仓不变）。
        """
        
        # TODO: 实现与本地deepseek模型的交互
        # 这里需要实现与本地deepseek模型的具体交互逻辑
        # 临时返回示例响应
        return {
            "analysis": "市场分析过程...",
            "recommendation": "HOLD",
            "confidence": 0.7,
            "reasoning": "详细的推理过程..."
        }
    
    def on_tick(self, market_data: Dict):
        """
        策略主逻辑
        1. 更新市场上下文
        2. 使用deepseek分析市场
        3. 执行交易决策
        4. 发送思考过程到前端
        """
        try:
            if 'data' not in market_data or len(market_data['data']) == 0:
                logger.warning("No market data available")
                return
                
            current_price = float(market_data['data'][0]['last'])
            self.update_market_context(market_data)
            
            # 创建事件循环来运行异步操作
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 获取市场分析
            analysis = loop.run_until_complete(self.analyze_market(current_price))
            
            # 发送思考过程到前端
            thinking_process = {
                "timestamp": market_data['data'][0]['ts'],
                "current_price": current_price,
                "position": float(self.position),
                "analysis": analysis
            }
            loop.run_until_complete(self.send_thinking_process(thinking_process))
            
            # 根据分析结果执行交易
            if analysis['recommendation'] == 'BUY' and analysis['confidence'] > 0.8:
                if self.position <= 0:
                    if self.position < 0:
                        self.buy(abs(self.position))
                    self.buy(self.trade_quantity)
                    logger.info(f"Deepseek建议买入 - 价格: {current_price}, 信心度: {analysis['confidence']}")
                    
            elif analysis['recommendation'] == 'SELL' and analysis['confidence'] > 0.8:
                if self.position >= 0:
                    if self.position > 0:
                        self.sell(self.position)
                    self.sell(self.trade_quantity)
                    logger.info(f"Deepseek建议卖出 - 价格: {current_price}, 信心度: {analysis['confidence']}")
            
            loop.close()
            
        except Exception as e:
            logger.error(f"Strategy error: {e}")
            return 