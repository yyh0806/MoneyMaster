"""测试OKX WebSocket登录"""

import asyncio
import os
import sys
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.trading.clients.okx.ws_manager import OKXWebSocketManager
from src.trading.clients.okx.config import OKXConfig
from src.config import settings

# 配置日志
logger.remove()  # 移除默认的日志处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>OKX-Test</cyan> | <level>{message}</level>",
    level="DEBUG"
)

async def on_message(message):
    """消息处理回调"""
    logger.info(f"收到消息: {message}")

async def test_login():
    """测试WebSocket登录"""
    
    # 从环境变量获取API凭证
    api_key = settings.API_KEY
    api_secret = settings.SECRET_KEY
    passphrase = settings.PASSPHRASE
    
    logger.info(f"API Key: {api_key[:4]}...{api_key[-4:] if api_key else None}")
    
    if not all([api_key, api_secret, passphrase]):
        logger.error("请设置OKX_API_KEY、OKX_API_SECRET和OKX_PASSPHRASE环境变量")
        return
        
    # 创建WebSocket管理器
    ws_manager = OKXWebSocketManager(
        url=OKXConfig.WS_PUBLIC_TESTNET if settings.USE_TESTNET else OKXConfig.WS_PUBLIC_MAINNET,
        on_message=on_message,
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase
    )
    
    try:
        # 连接WebSocket (连接时会自动登录)
        logger.info("正在连接WebSocket...")
        connected = await ws_manager.connect()
        
        if not connected:
            logger.error("WebSocket连接失败")
            return
        
        logger.info("WebSocket连接成功，登录成功！")
            
        # 测试订阅数据
        logger.info("尝试订阅Ticker数据...")
        await ws_manager.subscribe("tickers", [{
            "channel": "tickers",
            "instId": "BTC-USDT"
        }])
        
        # 等待一段时间以观察日志
        logger.info("测试完成，等待10秒后关闭连接...")
        await asyncio.sleep(10)
        
    except Exception as e:
        logger.error(f"测试中发生错误: {e}")
    finally:
        # 断开连接
        await ws_manager.disconnect()
        logger.info("WebSocket连接已断开")

if __name__ == "__main__":
    asyncio.run(test_login()) 