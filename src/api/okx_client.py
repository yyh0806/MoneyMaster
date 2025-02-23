from typing import List, Optional
from datetime import datetime
import aiohttp
from loguru import logger
from dataclasses import dataclass
from src.config import settings

@dataclass
class Candlestick:
    """K线数据模型"""
    timestamp: datetime  # 时间戳
    open: float         # 开盘价
    high: float         # 最高价
    low: float          # 最低价
    close: float        # 收盘价
    volume: float       # 成交量

class OKXClient:
    def __init__(self, rest_url: str):
        """初始化OKX客户端
        
        Args:
            rest_url: REST API的基础URL
        """
        self.rest_url = rest_url.rstrip('/')  # 移除末尾的斜杠
        logger.info(f"初始化OKX客户端: rest_url={self.rest_url}")
        
        # 配置代理
        self.proxy = None
        if settings.USE_PROXY:
            self.proxy = settings.HTTP_PROXY
            logger.info(f"使用代理: {self.proxy}")
        
    async def get_history_candlesticks(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 200,
        end_time: Optional[int] = None
    ) -> List[Candlestick]:
        """获取历史K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: 返回的K线数量限制
            end_time: 结束时间戳（毫秒）
            
        Returns:
            List[Candlestick]: K线数据列表
        """
        try:
            # 转换时间间隔格式
            interval_map = {
                "1m": "1m",
                "3m": "3m", 
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1H",
                "2h": "2H",
                "4h": "4H",
                "6h": "6H",
                "12h": "12H",
                "1d": "1D",
                "1w": "1W",
                "1M": "1M"
            }
            
            okx_interval = interval_map.get(interval)
            if not okx_interval:
                raise ValueError(f"不支持的时间间隔: {interval}")
                
            # 构造请求参数
            params = {
                "instId": symbol,
                "bar": okx_interval,
                "limit": str(limit)
            }
            if end_time:
                params["before"] = str(end_time)
                
            url = f"{self.rest_url}/market/candles"  # 使用正确的API路径
            logger.info(f"请求历史K线数据: url={url}, params={params}")
                
            # 发送请求
            async with aiohttp.ClientSession() as session:
                # 添加代理配置
                if self.proxy:
                    logger.info(f"使用代理发送请求: {self.proxy}")
                    
                async with session.get(
                    url,
                    params=params,
                    proxy=self.proxy
                ) as response:
                    if response.status != 200:
                        raise Exception(f"请求失败: {response.status}")
                        
                    data = await response.json()
                    logger.debug(f"收到响应: {data}")
                    
                    if not data or data.get("code") != "0":
                        raise Exception(f"获取数据失败: {data}")
                        
                    # 解析数据
                    candlesticks = []
                    for item in data["data"]:
                        # OKX API返回的数据格式：
                        # [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                        timestamp = datetime.fromtimestamp(int(item[0]) / 1000)
                        candlestick = Candlestick(
                            timestamp=timestamp,
                            open=float(item[1]),
                            high=float(item[2]),
                            low=float(item[3]),
                            close=float(item[4]),
                            volume=float(item[5])
                        )
                        candlesticks.append(candlestick)
                        
                    # 按时间正序排列
                    candlesticks.sort(key=lambda x: x.timestamp)
                    return candlesticks
                    
        except Exception as e:
            logger.error(f"获取历史K线数据失败: {e}")
            return [] 