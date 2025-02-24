"""OKX客户端测试"""

import os
import pytest
import pytest_asyncio
import asyncio
from decimal import Decimal
from dotenv import load_dotenv
from loguru import logger
import time

from src.trading.clients.okx.client import OKXClient
from src.trading.clients.okx.exceptions import OKXAuthenticationError

# 加载环境变量
load_dotenv(verbose=True)

# 测试配置
SYMBOL = "BTC-USDT"
API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_SECRET_KEY")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")
USE_TESTNET = os.getenv("USE_TESTNET", "true").lower() == "true"

logger.info(f"测试配置: SYMBOL={SYMBOL}, USE_TESTNET={USE_TESTNET}")
logger.info(f"API配置: KEY={API_KEY}, SECRET={'*' * len(API_SECRET) if API_SECRET else None}, PASSPHRASE={'*' * len(PASSPHRASE) if PASSPHRASE else None}")

@pytest_asyncio.fixture
async def okx_client():
    """创建OKX客户端实例"""
    client = OKXClient(
        symbol=SYMBOL,
        api_key=API_KEY,
        api_secret=API_SECRET,
        passphrase=PASSPHRASE,
        testnet=USE_TESTNET
    )
    
    logger.info("正在连接WebSocket...")
    connected = await client.connect()
    assert connected, "WebSocket连接失败"
    logger.info("WebSocket连接成功")
    
    # 等待数据订阅完成
    logger.info("正在订阅基础数据...")
    await client.subscribe_basic_data()
    await asyncio.sleep(2)  # 等待数据接收
    logger.info("基础数据订阅完成")
    
    yield client
    
    # 清理
    logger.info("正在关闭客户端连接...")
    await client.close()
    logger.info("客户端连接已关闭")

@pytest.mark.skipif(
    not all([os.getenv("OKX_API_KEY"), os.getenv("OKX_SECRET_KEY"), os.getenv("OKX_PASSPHRASE")]),
    reason="需要API密钥"
)
@pytest.mark.asyncio
async def test_spot_trading(okx_client):
    """测试现货交易功能"""
    # 获取账户余额
    balances = await okx_client.get_balance()
    assert isinstance(balances, dict)
    logger.info(f"账户余额: {balances}")
    
    # 获取当前市场价格
    ticker = await okx_client.get_ticker()
    assert ticker is not None
    current_price = ticker.last_price
    logger.info(f"当前{okx_client.symbol}价格: {current_price}")
    
    # 测试限价买单 - 比当前价格低1%
    buy_price = float(current_price) * 0.99
    buy_size = "0.001"  # BTC最小下单量
    
    logger.info(f"准备下限价买单: 价格={buy_price}, 数量={buy_size}")
    # 测试限价买单
    limit_buy_order = await okx_client.place_order(
        instId=okx_client.symbol,
        tdMode="cash",      # 现货交易
        side="buy",         # 买入方向
        ordType="limit",    # 限价单
        sz=buy_size,        # 委托数量
        px=str(buy_price),  # 委托价格
        clOrdId=f"test_limit_buy_{int(time.time())}"  # 客户端订单ID需要加上时间戳
    )
    assert isinstance(limit_buy_order.order_id, str)
    logger.info(f"限价买单创建成功: {limit_buy_order.order_id}")
    
    # 获取订单详情
    order_info = await okx_client.get_order(
        instId=okx_client.symbol,
        ordId=limit_buy_order.order_id
    )
    assert order_info is not None
    assert order_info.order_id == limit_buy_order.order_id
    assert order_info.status in ["live", "partially_filled"]
    logger.info(f"订单状态: {order_info.status}")
    
    # 取消订单
    cancelled = await okx_client.cancel_order(
        instId=okx_client.symbol,
        ordId=limit_buy_order.order_id
    )
    assert cancelled is True
    logger.info(f"订单已取消: {limit_buy_order.order_id}")
    
    # 验证订单已被取消
    await asyncio.sleep(1)
    cancelled_order = await okx_client.get_order(
        instId=okx_client.symbol,
        ordId=limit_buy_order.order_id
    )
    assert cancelled_order.status == "cancelled"
    logger.info("订单已成功取消")

