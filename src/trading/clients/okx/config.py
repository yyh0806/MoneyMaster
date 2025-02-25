"""OKX交易所配置"""

class OKXConfig:
    """OKX交易所配置类"""
    
    # REST API endpoints
    REST_MAINNET_URL = "https://www.okx.com"
    REST_TESTNET_URL = "https://www.okx.com"  # 测试网使用相同的URL，通过header区分
    
    # WebSocket endpoints
    WS_PUBLIC_MAINNET = "wss://ws.okx.com:8443/ws/v5/public"
    WS_PRIVATE_MAINNET = "wss://ws.okx.com:8443/ws/v5/private"
    WS_BUSINESS_MAINNET = "wss://ws.okx.com:8443/ws/v5/business"
    WS_PUBLIC_TESTNET = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
    WS_PRIVATE_TESTNET = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
    WS_BUSINESS_TESTNET = "wss://wspap.okx.com:8443/ws/v5/business?brokerId=9999"
    
    # API路径
    API_PATHS = {
        "PLACE_ORDER": "/api/v5/trade/order",
        "CANCEL_ORDER": "/api/v5/trade/cancel-order",
        "GET_ORDER": "/api/v5/trade/order",
        "GET_PENDING_ORDERS": "/api/v5/trade/orders-pending",
        "GET_BALANCE": "/api/v5/account/balance"
    }
    
    # WebSocket配置
    WS_PING_INTERVAL = 25  # 心跳间隔（秒），修改为25秒，确保不超过官方建议的30秒
    WS_RECONNECT_DELAY = 5  # 重连延迟（秒）
    WS_MAX_RETRIES = 5     # 最大重试次数，增加到5次
    
    # 时间周期映射
    INTERVAL_MAP = {
        "1m": "1m", "3m": "3m", "5m": "5m",
        "15m": "15m", "30m": "30m",
        "1H": "1H", "2H": "2H", "4H": "4H",
        "6H": "6H", "12H": "12H",
        "1D": "1D", "1W": "1W", "1M": "1M"
    }
    
    # 数据缓存配置
    MAX_TRADE_CACHE = 1000    # 最大成交缓存数量
    MAX_ORDERBOOK_LEVELS = 200  # 最大订单簿深度
    MAX_KLINE_CACHE = 1000    # 每个周期最大K线缓存数量
    
    # API限制
    RATE_LIMIT_PER_SECOND = 20  # 每秒请求限制
    MAX_CONNECTIONS = 5        # 最大连接数
    
    # API请求超时设置
    REQUEST_TIMEOUT = 10  # 请求超时时间（秒）
    
    # API响应状态码
    SUCCESS_CODE = "0"
    
    # WebSocket订阅主题
    TOPICS = {
        "TICKER": "tickers",
        "ORDERBOOK": "books",  # 默认深度
        "ORDERBOOK5": "books5",  # 5档深度
        "ORDERBOOK50": "books50",  # 50档深度
        "TRADES": "trades",
        "CANDLE": "candle",
        "ORDERS": "orders",  # 订单频道
        "POSITIONS": "positions",  # 持仓频道
        "BALANCE": "account-balance",  # 账户余额频道，修正为官方API名称
        "ACCOUNT": "account"  # 账户频道
    } 