import pytest
import asyncio
from datetime import datetime
from loguru import logger

from src.trading.core.market_data import MarketData, MarketSnapshot
from src.trading.base.market_ws_client import OrderBook, Ticker, Trade

@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_market_data_basic():
    """测试市场数据基本功能"""
    market = MarketData("BTC-USDT", "okx")
    
    try:
        # 启动服务
        await market.start()
        
        # 等待数据收集
        await asyncio.sleep(5)
        
        # 获取快照
        snapshot = market.get_snapshot()
        
        # 验证快照数据
        assert isinstance(snapshot, MarketSnapshot)
        assert snapshot.symbol == "BTC-USDT"
        
        # 验证各类数据
        if snapshot.orderbook:
            assert isinstance(snapshot.orderbook, OrderBook)
            assert len(snapshot.orderbook.asks) > 0
            assert len(snapshot.orderbook.bids) > 0
            
        if snapshot.ticker:
            assert isinstance(snapshot.ticker, Ticker)
            assert snapshot.ticker.last_price > 0
            
        assert isinstance(snapshot.trades, list)
        
    finally:
        await market.stop()

@pytest.mark.asyncio
async def test_market_data_callbacks():
    """测试市场数据回调功能"""
    market = MarketData("BTC-USDT", "okx")
    received_data = {
        "orderbook": [],
        "ticker": [],
        "trade": [],
        "snapshot": []
    }
    
    # 定义回调函数
    async def orderbook_callback(data: OrderBook):
        received_data["orderbook"].append(data)
        logger.info(f"收到订单簿数据: 最优买价={data.bids[0].price}, 最优卖价={data.asks[0].price}")
        
    async def ticker_callback(data: Ticker):
        received_data["ticker"].append(data)
        logger.info(f"收到Ticker数据: 最新价={data.last_price}")
        
    async def trade_callback(data: Trade):
        received_data["trade"].append(data)
        logger.info(f"收到成交数据: 价格={data.price}, 数量={data.size}")
        
    async def snapshot_callback(data: MarketSnapshot):
        received_data["snapshot"].append(data)
        logger.info("收到市场快照更新")
    
    try:
        # 注册回调
        market.register_orderbook_callback(orderbook_callback)
        market.register_ticker_callback(ticker_callback)
        market.register_trade_callback(trade_callback)
        market.register_snapshot_callback(snapshot_callback)
        
        # 启动服务
        await market.start()
        
        # 等待数据收集
        await asyncio.sleep(5)
        
        # 验证回调数据
        assert len(received_data["orderbook"]) > 0, "未收到订单簿数据"
        assert len(received_data["ticker"]) > 0, "未收到Ticker数据"
        assert len(received_data["snapshot"]) > 0, "未收到市场快照"
        
        # 验证价格计算
        mid_price = market.get_mid_price()
        spread = market.get_spread()
        
        if mid_price is not None:
            assert isinstance(mid_price, float)
            assert mid_price > 0
            
        if spread is not None:
            assert isinstance(spread, float)
            assert spread >= 0
            
    finally:
        await market.stop()

@pytest.mark.asyncio
async def test_market_data_error_handling():
    """测试市场数据错误处理"""
    # 测试不支持的交易所
    with pytest.raises(ValueError):
        MarketData("BTC-USDT", "unsupported")
        
    market = MarketData("BTC-USDT", "okx")
    
    # 测试错误的回调函数
    async def error_callback(data):
        raise Exception("测试回调错误")
        
    try:
        market.register_orderbook_callback(error_callback)
        await market.start()
        
        # 等待一段时间，确保错误被正确处理
        await asyncio.sleep(3)
        
        # 验证服务仍在运行
        assert market.get_snapshot() is not None
        
    finally:
        await market.stop()

if __name__ == "__main__":
    pytest.main(["-v", "test_market_data.py"]) 