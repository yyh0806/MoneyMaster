import pytest
import asyncio
from datetime import datetime, timedelta
from src.api.okx_client import OKXClient
from src.config import settings

@pytest.mark.asyncio
async def test_get_history_candlesticks():
    """测试获取历史K线数据"""
    # 初始化客户端
    client = OKXClient(rest_url=settings.API_URL)
    
    # 测试参数
    symbol = "BTC-USDT"
    interval = "15m"
    limit = 10
    
    try:
        # 调用API获取历史K线数据
        candlesticks = await client.get_history_candlesticks(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        # 验证返回的数据
        assert len(candlesticks) > 0, "应该返回至少一条K线数据"
        
        # 验证第一条K线数据的格式
        first_candle = candlesticks[0]
        assert isinstance(first_candle.timestamp, datetime), "timestamp应该是datetime类型"
        assert isinstance(first_candle.open, float), "open应该是float类型"
        assert isinstance(first_candle.high, float), "high应该是float类型"
        assert isinstance(first_candle.low, float), "low应该是float类型"
        assert isinstance(first_candle.close, float), "close应该是float类型"
        assert isinstance(first_candle.volume, float), "volume应该是float类型"
        
        # 验证数据的有效性
        assert first_candle.high >= first_candle.low, "最高价应该大于等于最低价"
        assert first_candle.high >= first_candle.open, "最高价应该大于等于开盘价"
        assert first_candle.high >= first_candle.close, "最高价应该大于等于收盘价"
        assert first_candle.low <= first_candle.open, "最低价应该小于等于开盘价"
        assert first_candle.low <= first_candle.close, "最低价应该小于等于收盘价"
        assert first_candle.volume >= 0, "成交量应该大于等于0"
        
        # 验证时间顺序
        timestamps = [c.timestamp for c in candlesticks]
        assert timestamps == sorted(timestamps), "K线数据应该按时间正序排列"
        
        # 验证时间间隔
        if len(candlesticks) > 1:
            time_diff = candlesticks[1].timestamp - candlesticks[0].timestamp
            expected_interval = timedelta(minutes=15)  # 15分钟间隔
            assert abs(time_diff - expected_interval) < timedelta(seconds=1), "时间间隔应该是15分钟"
            
        print(f"测试通过！获取到{len(candlesticks)}条K线数据")
        for candle in candlesticks[:3]:  # 打印前3条数据
            print(f"时间: {candle.timestamp}, 开: {candle.open}, 高: {candle.high}, "
                  f"低: {candle.low}, 收: {candle.close}, 量: {candle.volume}")
            
    except Exception as e:
        pytest.fail(f"测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_get_history_candlesticks()) 