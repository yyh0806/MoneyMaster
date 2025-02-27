from typing import List, Optional
import json
from redis.asyncio import Redis
from loguru import logger

class RedisManager:
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.logger = logger.bind(name="RedisManager")
        
    def _get_kline_key(self, symbol: str, interval: str) -> str:
        """生成K线缓存的key"""
        return f"kline:{symbol}:{interval}"
    
    async def cache_klines(self, symbol: str, interval: str, klines: List['Candlestick'], expire_seconds: int = 3600) -> None:
        """缓存K线数据"""
        key = self._get_kline_key(symbol, interval)
        # 将K线数据转换为JSON字符串列表
        kline_data = [
            {
                'timestamp': k.timestamp,
                'open': k.open,
                'high': k.high,
                'low': k.low,
                'close': k.close,
                'volume': k.volume
            } for k in klines
        ]
        
        try:
            await self.redis.set(key, json.dumps(kline_data), ex=expire_seconds)
            self.logger.debug(f"缓存K线数据 {symbol} {interval}, 共{len(klines)}条")
        except Exception as e:
            self.logger.error(f"缓存K线数据失败: {str(e)}")
    
    async def get_cached_klines(self, symbol: str, interval: str) -> Optional[List[dict]]:
        """获取缓存的K线数据"""
        key = self._get_kline_key(symbol, interval)
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            self.logger.error(f"获取缓存K线数据失败: {str(e)}")
        return None
    
    async def update_kline(self, symbol: str, interval: str, kline: 'Candlestick') -> None:
        """更新单条K线数据"""
        cached_klines = await self.get_cached_klines(symbol, interval)
        if not cached_klines:
            return
            
        # 更新或添加新的K线
        kline_data = {
            'timestamp': kline.timestamp,
            'open': kline.open,
            'high': kline.high,
            'low': kline.low,
            'close': kline.close,
            'volume': kline.volume
        }
        
        updated = False
        for i, k in enumerate(cached_klines):
            if k['timestamp'] == kline.timestamp:
                cached_klines[i] = kline_data
                updated = True
                break
                
        if not updated:
            cached_klines.append(kline_data)
            cached_klines.sort(key=lambda x: x['timestamp'])
            
        # 保持最新的1000条数据
        if len(cached_klines) > 1000:
            cached_klines = cached_klines[-1000:]
            
        await self.cache_klines(symbol, interval, [kline])
        
    async def close(self):
        """关闭Redis连接"""
        await self.redis.close() 