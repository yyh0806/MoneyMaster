import pytest
import asyncio
import websockets
import json
from loguru import logger
import os
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()

class OkxMarketTest:
    def __init__(self, symbol="BTC-USDT"):
        self.symbol = symbol
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.connected = False
        
    async def connect(self):
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.connected = True
            logger.info("WebSocket连接成功")
            return True
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return False

    async def subscribe_orderbook(self):
        try:
            subscribe_msg = {
                "op": "subscribe",
                "args": [{
                    "channel": "books",
                    "instId": self.symbol
                }]
            }
            await self.ws.send(json.dumps(subscribe_msg))
            logger.info(f"已发送订阅请求: {self.symbol}")
        except Exception as e:
            logger.error(f"订阅失败: {e}")
            raise

    async def close(self):
        if self.connected and self.ws:
            await self.ws.close()
            self.connected = False
            logger.info("WebSocket连接已关闭")

@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_okx_market_subscription():
    """测试OKX行情订阅功能"""
    try:
        # 创建测试实例
        market = OkxMarketTest("BTC-USDT")
        
        # 连接WebSocket
        assert await market.connect(), "WebSocket连接失败"
        
        # 订阅行情
        await market.subscribe_orderbook()
        
        # 接收和验证数据
        message_count = 0
        start_time = datetime.now()
        
        while message_count < 5:  # 接收5条消息后退出
            try:
                message = await asyncio.wait_for(market.ws.recv(), timeout=5.0)
                data = json.loads(message)
                
                logger.info(f"收到数据: {data}")
                
                # 验证数据结构
                if "data" in data:
                    assert isinstance(data["data"], list), "数据格式错误"
                    if len(data["data"]) > 0:
                        book_data = data["data"][0]
                        # 验证关键字段
                        assert "asks" in book_data, "未找到卖单数据"
                        assert "bids" in book_data, "未找到买单数据"
                        assert len(book_data["asks"]) > 0, "卖单数据为空"
                        assert len(book_data["bids"]) > 0, "买单数据为空"
                        
                        # 打印当前最优价格
                        best_ask = float(book_data["asks"][0][0])
                        best_bid = float(book_data["bids"][0][0])
                        logger.info(f"当前最优卖价: {best_ask}, 最优买价: {best_bid}")
                        
                        message_count += 1
                
            except asyncio.TimeoutError:
                logger.warning("接收数据超时")
                break
            
            # 设置最大运行时间为30秒
            if (datetime.now() - start_time).seconds > 30:
                logger.warning("测试运行时间超过30秒")
                break
        
        # 验证是否收到足够的数据
        assert message_count > 0, "未收到任何有效数据"
        logger.info(f"成功接收 {message_count} 条数据")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise
        
    finally:
        # 清理资源
        await market.close()

if __name__ == "__main__":
    pytest.main(["-v", "test_okx_market.py"])