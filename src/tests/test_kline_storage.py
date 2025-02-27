import asyncio
from datetime import datetime, timedelta
from src.api.market_data import kline_manager, Candlestick
from loguru import logger

async def test_kline_storage():
    try:
        # 创建测试数据
        symbol = "BTC-USDT"
        interval = "1m"
        now = datetime.now()
        test_klines = [
            Candlestick(
                timestamp=int((now - timedelta(minutes=i)).timestamp() * 1000),
                open=str(40000 + i),
                high=str(40100 + i),
                low=str(39900 + i),
                close=str(40050 + i),
                volume=str(1000 + i)
            )
            for i in range(10)
        ]
        
        # 测试初始化K线数据
        logger.info("测试初始化K线数据...")
        await kline_manager.init_klines(symbol, interval, test_klines)
        
        # 测试从数据库读取数据
        logger.info("测试从数据库读取数据...")
        db_klines = await kline_manager.get_klines(symbol, interval, limit=5)
        logger.info(f"从数据库读取到 {len(db_klines)} 条数据")
        
        # 测试从缓存读取数据
        logger.info("测试从缓存读取数据...")
        cache_klines = await kline_manager.get_klines(symbol, interval, limit=5)
        logger.info(f"从缓存读取到 {len(cache_klines)} 条数据")
        
        # 测试更新单条K线
        logger.info("测试更新单条K线...")
        update_kline = Candlestick(
            timestamp=test_klines[0].timestamp,
            open=str(41000),
            high=str(41100),
            low=str(40900),
            close=str(41050),
            volume=str(2000)
        )
        updated = await kline_manager.update_kline(symbol, interval, update_kline)
        logger.info(f"K线更新状态: {updated}")
        
        # 再次读取数据验证更新
        logger.info("验证更新结果...")
        updated_klines = await kline_manager.get_klines(symbol, interval, limit=5)
        first_kline = updated_klines[0]
        logger.info(f"更新后的第一条K线: close={first_kline.close}, volume={first_kline.volume}")
        
        # 关闭连接
        await kline_manager.close()
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_kline_storage()) 