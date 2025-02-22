from loguru import logger
from src.trading.client import OKXClient

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
    
    return balance, btc_price

def test_market_data():
    """测试市场数据API"""
    client = OKXClient()
    
    # 测试获取K线数据
    logger.info("正在获取BTC-USDT K线数据...")
    kline = client.get_kline("BTC-USDT", bar="1m", limit="10")
    logger.info(f"K线数据: {kline}")
    
    # 测试获取深度数据
    logger.info("正在获取BTC-USDT深度数据...")
    depth = client.get_orderbook("BTC-USDT", sz="5")
    logger.info(f"深度数据: {depth}")
    
    return kline, depth

def test_account_info():
    """测试账户相关API"""
    client = OKXClient()
    
    # 测试获取持仓信息
    logger.info("正在获取持仓信息...")
    positions = client.get_positions()
    logger.info(f"持仓信息: {positions}")
    
    # 测试获取账户配置
    logger.info("正在获取账户配置...")
    config = client.get_account_config()
    logger.info(f"账户配置: {config}")
    
    return positions, config

if __name__ == "__main__":
    logger.info("开始API测试...")
    
    # 测试连接
    balance, price = test_connection()
    assert balance is not None, "获取账户余额失败"
    assert price is not None, "获取市场价格失败"
    
    # 测试市场数据
    kline, depth = test_market_data()
    assert kline is not None, "获取K线数据失败"
    assert depth is not None, "获取深度数据失败"
    
    # 测试账户信息
    positions, config = test_account_info()
    assert positions is not None, "获取持仓信息失败"
    assert config is not None, "获取账户配置失败"
    
    logger.info("API测试完成！") 