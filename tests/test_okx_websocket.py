import pytest
import asyncio
import json
from datetime import datetime
from loguru import logger

from src.trading.clients.okx_websocket import OKXWebSocketClient

@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_websocket_connection():
    """测试WebSocket连接功能"""
    client = OKXWebSocketClient("BTC-USDT")
    try:
        # 测试连接
        connected = await client.connect()
        assert connected, "WebSocket连接失败"
        
        # 测试断开连接
        await client.disconnect()
        assert not client.connected, "WebSocket未正确断开连接"
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise

@pytest.mark.asyncio
async def test_orderbook_subscription():
    """测试订单簿订阅功能"""
    client = OKXWebSocketClient("BTC-USDT")
    received_data = []
    
    async def orderbook_callback(message):
        """订单簿数据回调函数"""
        if "data" in message:  # 只处理数据消息
            received_data.append(message)
            logger.info(f"收到订单簿数据: {message}")
    
    try:
        # 连接WebSocket
        assert await client.connect(), "WebSocket连接失败"
        
        # 订阅订单簿
        await client.subscribe_orderbook(orderbook_callback)
        
        # 启动消息处理
        await client.start()
        
        # 等待接收数据
        start_time = datetime.now()
        while len(received_data) < 3:  # 等待接收3条消息
            await asyncio.sleep(1)
            if (datetime.now() - start_time).seconds > 30:  # 30秒超时
                break
        
        # 验证数据
        assert len(received_data) > 0, "未收到订单簿数据"
        
        # 验证数据结构
        for message in received_data:
            assert "data" in message, "数据格式错误"
            for book_data in message["data"]:
                assert "asks" in book_data and "bids" in book_data, "数据缺少买卖盘信息"
                if len(book_data["asks"]) > 0:
                    assert len(book_data["asks"][0]) >= 2, "卖单数据格式错误"
                if len(book_data["bids"]) > 0:
                    assert len(book_data["bids"][0]) >= 2, "买单数据格式错误"
            
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise
        
    finally:
        await client.disconnect()

@pytest.mark.asyncio
async def test_realtime_price():
    """测试实时价格获取功能"""
    client = OKXWebSocketClient("BTC-USDT")
    try:
        # 连接WebSocket
        assert await client.connect(), "WebSocket连接失败"
        
        # 订阅订单簿（需要先订阅才能获取实时价格）
        await client.subscribe_orderbook()
        
        # 启动消息处理
        await client.start()
        
        # 等待一段时间让数据接收
        await asyncio.sleep(2)
        
        # 获取实时价格
        price = await client.get_realtime_price()
        
        # 验证价格
        assert price is not None, "未能获取实时价格"
        assert isinstance(price, float), "价格格式错误"
        assert price > 0, "价格值异常"
        
        logger.info(f"获取到的实时价格: {price}")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise
        
    finally:
        await client.disconnect()

if __name__ == "__main__":
    pytest.main(["-v", "test_okx_websocket.py"]) 