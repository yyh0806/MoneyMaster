import asyncio
from src.api.market_data import kline_manager, init_db
from loguru import logger

async def test_connections():
    try:
        # 初始化数据库
        await init_db()
        logger.info("数据库初始化成功")
        
        # 测试Redis连接
        await kline_manager.redis_manager.redis.ping()
        logger.info("Redis连接成功")
        
        # 关闭连接
        await kline_manager.close()
        logger.info("连接关闭成功")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_connections()) 