import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# OKX API配置
API_KEY = os.getenv('OKX_API_KEY')
SECRET_KEY = os.getenv('OKX_SECRET_KEY')
PASSPHRASE = os.getenv('OKX_PASSPHRASE')

# API配置
API_URL = 'https://www.okx.com/api/v5'  # 实盘API地址
TESTNET_API_URL = 'https://www.okx.com/api/v5'  # 模拟盘API地址

# 是否使用测试网络
USE_TESTNET = os.getenv('USE_TESTNET', 'true').lower() == 'true'

# 代理配置
USE_PROXY = False  # 禁用代理
HTTP_PROXY = 'http://127.0.0.1:7890'
HTTPS_PROXY = 'http://127.0.0.1:7890'

# 交易配置
TRADE_MODE = os.getenv('TRADE_MODE', 'test')  # 'test' 或 'live'
DEFAULT_LEVERAGE = int(os.getenv('DEFAULT_LEVERAGE', '1'))

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')

# 数据库配置
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///moneymaster.db')  # 默认使用SQLite
DATABASE_ECHO = os.getenv('DATABASE_ECHO', 'false').lower() == 'true'  # 是否打印SQL语句 