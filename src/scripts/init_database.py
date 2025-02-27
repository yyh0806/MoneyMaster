import asyncio
from src.api.market_data import init_db
from loguru import logger

async def main():
    try:
        await init_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 