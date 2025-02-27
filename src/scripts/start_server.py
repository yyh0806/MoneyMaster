import asyncio
import sys
import os
from loguru import logger
import uvicorn
from src.api.app import app  # 直接导入app实例

async def main():
    try:
        # 启动服务器
        logger.info("正在启动服务器...")
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="error"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # 设置日志格式
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <white>{message}</white>",
        level="INFO"
    )
    
    # 运行服务器
    asyncio.run(main()) 