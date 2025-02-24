"""OKX交易所异常类"""

class OKXError(Exception):
    """OKX交易所基础错误"""
    pass

class OKXAPIError(OKXError):
    """API调用错误"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

class OKXConnectionError(OKXError):
    """连接错误"""
    pass

class OKXAuthenticationError(OKXError):
    """认证错误"""
    pass

class OKXValidationError(OKXError):
    """数据验证错误"""
    pass

class OKXRateLimitError(OKXError):
    """请求频率限制错误"""
    def __init__(self, limit: int, reset_time: int):
        self.limit = limit
        self.reset_time = reset_time
        super().__init__(f"请求超过频率限制 {limit}/s，将在 {reset_time} 秒后重置")

class OKXWebSocketError(OKXError):
    """WebSocket错误"""
    pass

class OKXParseError(OKXError):
    """数据解析错误"""
    def __init__(self, data_type: str, data: str, error: str):
        self.data_type = data_type
        self.data = data
        self.error = error
        super().__init__(f"解析{data_type}数据失败: {error}, data={data}")

class OKXTimeoutError(OKXError):
    """请求超时错误"""
    def __init__(self, timeout: int):
        self.timeout = timeout
        super().__init__(f"请求超时 ({timeout}秒)")

class OKXInvalidSymbolError(OKXError):
    """无效的交易对错误"""
    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"无效的交易对: {symbol}")

class OKXInsufficientBalanceError(OKXError):
    """余额不足错误"""
    def __init__(self, required: str, available: str, currency: str):
        self.required = required
        self.available = available
        self.currency = currency
        super().__init__(f"余额不足: 需要 {required} {currency}，可用 {available} {currency}")

class OKXOrderError(OKXError):
    """订单操作错误"""
    def __init__(self, order_id: str, operation: str, reason: str):
        self.order_id = order_id
        self.operation = operation
        self.reason = reason
        super().__init__(f"订单{operation}失败 (ID: {order_id}): {reason}")

class OKXRequestError(OKXError):
    """OKX请求错误"""
    pass 