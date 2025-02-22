from src.trading.client import OKXClient
from loguru import logger

def test_connection():
    """测试与OKX的连接"""
    client = OKXClient()
    
    # 测试获取账户信息
    logger.info("正在获取账户信息...")
    balance = client.get_account_balance()
    logger.info(f"账户信息: {balance}")
    
    # 测试获取BTC-USDT市场价格
    logger.info("正在获取BTC-USDT市场价格...")
    btc_price = client.get_market_price("BTC-USDT")
    logger.info(f"BTC-USDT价格信息: {btc_price}")

if __name__ == "__main__":
    test_connection() 