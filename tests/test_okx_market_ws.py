import pytest
import asyncio
from datetime import datetime
from loguru import logger

from src.trading.clients.okx_market_ws import OKXMarketWebSocketClient
from src.trading.base.market_ws_client import OrderBook, Ticker, Trade

@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_orderbook_subscription():
    """测试订单簿订阅"""
    client = OKXMarketWebSocketClient("BTC-USDT")
    received_data = []
    
    async def orderbook_callback(orderbook: OrderBook):
        """订单簿数据回调"""
        received_data.append(orderbook)
        logger.info(f"收到订单簿数据: 最优买价={orderbook.bids[0].price}, 最优卖价={orderbook.asks[0].price}")
    
    try:
        # 连接并订阅
        await client.connect()
        await client.subscribe_orderbook(orderbook_callback)
        await client.start()
        
        # 等待数据
        start_time = datetime.now()
        while len(received_data) < 3:  # 等待3条数据
            await asyncio.sleep(1)
            if (datetime.now() - start_time).seconds > 30:
                break
                
        # 验证数据
        assert len(received_data) > 0, "未收到订单簿数据"
        for orderbook in received_data:
            assert isinstance(orderbook, OrderBook), "数据类型错误"
            assert len(orderbook.asks) > 0, "卖单为空"
            assert len(orderbook.bids) > 0, "买单为空"
            assert orderbook.asks[0].price > orderbook.bids[0].price, "买卖价格异常"
            
    finally:
        await client.disconnect()

@pytest.mark.asyncio
async def test_ticker_subscription():
    """测试Ticker订阅"""
    client = OKXMarketWebSocketClient("BTC-USDT")
    received_data = []
    
    async def ticker_callback(ticker: Ticker):
        """Ticker数据回调"""
        received_data.append(ticker)
    
    try:
        # 连接并订阅
        await client.connect()
        await client.subscribe_ticker(ticker_callback)
        await client.start()
        
        # 等待数据
        start_time = datetime.now()
        while len(received_data) < 3:
            await asyncio.sleep(1)
            if (datetime.now() - start_time).seconds > 30:
                break
                
        # 验证数据
        assert len(received_data) > 0, "未收到Ticker数据"
        for ticker in received_data:
            assert isinstance(ticker, Ticker), "数据类型错误"
            assert ticker.last_price > 0, "最新价格异常"
            assert ticker.volume_24h >= 0, "成交量异常"
            
    finally:
        await client.disconnect()

@pytest.mark.asyncio
async def test_trades_subscription():
    """测试成交数据订阅"""
    client = OKXMarketWebSocketClient("BTC-USDT")
    received_data = []
    
    async def trade_callback(trade: Trade):
        """成交数据回调"""
        received_data.append(trade)
        logger.info(f"收到成交数据: 价格={trade.price}, 数量={trade.size}, 方向={trade.side}")
    
    try:
        # 连接并订阅
        await client.connect()
        await client.subscribe_trades(trade_callback)
        await client.start()
        
        # 等待数据
        start_time = datetime.now()
        while len(received_data) < 3:
            await asyncio.sleep(1)
            if (datetime.now() - start_time).seconds > 30:
                break
                
        # 验证数据
        assert len(received_data) > 0, "未收到成交数据"
        for trade in received_data:
            assert isinstance(trade, Trade), "数据类型错误"
            assert trade.price > 0, "价格异常"
            assert trade.size > 0, "数量异常"
            assert trade.side in ["buy", "sell"], "交易方向异常"
            
    finally:
        await client.disconnect()

@pytest.mark.asyncio
async def test_market_snapshot():
    """测试市场数据快照"""
    client = OKXMarketWebSocketClient("BTC-USDT")
    
    try:
        # 连接并订阅所有数据
        await client.connect()
        await client.subscribe_orderbook()
        await client.subscribe_ticker()
        await client.subscribe_trades()
        await client.start()
        
        # 等待数据收集
        await asyncio.sleep(5)
        
        # 获取快照
        snapshot = await client.get_snapshot()
        
        # 验证快照数据
        assert "orderbook" in snapshot, "快照缺少订单簿数据"
        assert "ticker" in snapshot, "快照缺少Ticker数据"
        assert "trades" in snapshot, "快照缺少成交数据"
        
        if snapshot["orderbook"]:
            assert isinstance(snapshot["orderbook"], OrderBook)
        if snapshot["ticker"]:
            assert isinstance(snapshot["ticker"], Ticker)
        if snapshot["trades"]:
            assert all(isinstance(trade, Trade) for trade in snapshot["trades"])
            
    finally:
        await client.disconnect()

if __name__ == "__main__":
    pytest.main(["-v", "test_okx_market_ws.py"]) 