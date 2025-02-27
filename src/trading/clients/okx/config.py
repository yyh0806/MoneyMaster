"""OKX配置"""

class OKXConfig:
    """OKX配置类"""
    
    # REST API
    REST_MAINNET_URL = "https://www.okx.com"  # 主网
    REST_TESTNET_URL = "https://www.okx.com"  # 测试网，使用主网域名
    
    # WebSocket
    WS_PUBLIC_MAINNET_URL = "wss://ws.okx.com:8443/ws/v5/public"  # 主网公共频道
    WS_PRIVATE_MAINNET_URL = "wss://ws.okx.com:8443/ws/v5/private"  # 主网私有频道
    WS_PUBLIC_TESTNET_URL = "wss://wspap.okx.com:8443/ws/v5/public"  # 测试网公共频道
    WS_PRIVATE_TESTNET_URL = "wss://wspap.okx.com:8443/ws/v5/private"  # 测试网私有频道
    
    # API版本
    API_VERSION = "v5"
    
    # 请求限制
    RATE_LIMITS = {
        "PUBLIC": 20,  # 每秒请求数
        "PRIVATE": 5   # 每秒请求数
    }
    
    # WebSocket配置
    WS_PING_INTERVAL = 20  # 心跳间隔（秒）
    WS_PING_TIMEOUT = 10   # 心跳超时（秒）
    WS_CLOSE_TIMEOUT = 10  # 关闭超时（秒）
    
    # 重试配置
    MAX_RETRIES = 3        # 最大重试次数
    RETRY_DELAY = 1        # 重试延迟（秒）
    
    # 订单类型
    ORDER_TYPES = {
        "MARKET": "market",  # 市价单
        "LIMIT": "limit",    # 限价单
        "POST_ONLY": "post_only",  # 只做maker单
        "FOK": "fok",        # 全部成交或立即取消
        "IOC": "ioc"         # 立即成交并取消剩余
    }
    
    # 订单方向
    ORDER_SIDES = {
        "BUY": "buy",    # 买入
        "SELL": "sell"   # 卖出
    }
    
    # 持仓方向
    POSITION_SIDES = {
        "LONG": "long",   # 多头
        "SHORT": "short"  # 空头
    }
    
    # 保证金模式
    MARGIN_MODES = {
        "ISOLATED": "isolated",  # 逐仓
        "CROSS": "cross"        # 全仓
    }
    
    # 订单状态
    ORDER_STATUS = {
        "PENDING": "pending",          # 等待成交
        "PARTIALLY_FILLED": "partial",  # 部分成交
        "FILLED": "filled",            # 完全成交
        "CANCELLED": "cancelled",      # 已取消
        "FAILED": "failed"            # 失败
    }
    
    # API路径
    API_PATHS = {
        "PLACE_ORDER": "trade/order",
        "CANCEL_ORDER": "trade/cancel-order",
        "GET_ORDER": "trade/order",
        "GET_PENDING_ORDERS": "trade/orders-pending",
        "GET_BALANCE": "account/balance",
        "GET_TICKER": "market/ticker"
    }
    
    # WebSocket配置
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