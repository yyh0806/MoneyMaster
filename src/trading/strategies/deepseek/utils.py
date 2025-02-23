"""工具函数模块"""

import sys
from loguru import logger

# 配置日志
logger.remove()  # 移除默认的日志处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[strategy]}</cyan> | <level>{message}</level>",
    level="INFO"
)

# 创建带有策略名称的上下文日志记录器
strategy_logger = logger.bind(strategy="DeepseekStrategy")

def get_default_analysis() -> dict:
    """获取默认的分析结果"""
    return {
        'analysis': '等待市场数据分析',
        'recommendation': '观望',
        'confidence': 0.0,
        'reasoning': '尚未进行分析',
        'market_trend': '未知',
        'support_price': None,
        'resistance_price': None,
        'risk_level': '未知',
        'timestamp': None
    } 