from dataclasses import dataclass
from typing import Dict, List, Optional
import asyncio
from datetime import datetime
import json
from decimal import Decimal
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from src.models.candlestick import CandlestickModel, Base
from src.cache.redis_manager import RedisManager

@dataclass
class Candlestick:
    timestamp: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    
    def to_list(self) -> List:
        """转换为列表格式，用于前端显示"""
        return [
            self.timestamp,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume
        ]
    
    @classmethod
    def from_okx_candlestick(cls, candle) -> 'Candlestick':
        """从OKX K线数据转换"""
        return cls(
            timestamp=int(candle.timestamp.timestamp() * 1000),
            open=str(candle.open),
            high=str(candle.high),
            low=str(candle.low),
            close=str(candle.close),
            volume=str(candle.volume)
        )

class KlineManager:
    def __init__(self, db_url: str, redis_url: str):
        self._lock = asyncio.Lock()
        self.logger = logger.bind(name="KlineManager")
        
        # 初始化数据库连接
        self._engine = self._create_engine(db_url)
        self._async_session = sessionmaker(
            self._engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # 初始化Redis缓存
        self.redis_manager = RedisManager(redis_url)
        
    def _create_engine(self, db_url: str) -> AsyncEngine:
        """创建数据库引擎，配置连接池"""
        return create_async_engine(
            db_url,
            echo=False,
            poolclass=AsyncAdaptedQueuePool,
            pool_pre_ping=True,  # 自动检测断开的连接
            pool_size=20,  # 连接池大小
            max_overflow=10,  # 超过pool_size后最多可以创建的连接数
            pool_timeout=30,  # 等待连接的超时时间
            pool_recycle=1800,  # 连接重置时间（秒）
        )
        
    async def init_klines(self, symbol: str, interval: str, klines: List[Candlestick]):
        """初始化K线数据"""
        async with self._lock:
            # 保存到数据库
            async with self._async_session() as session:
                for kline in klines:
                    stmt = insert(CandlestickModel).values(
                        symbol=symbol,
                        interval=interval,
                        timestamp=kline.timestamp,
                        open=kline.open,
                        high=kline.high,
                        low=kline.low,
                        close=kline.close,
                        volume=kline.volume
                    ).on_conflict_do_update(
                        index_elements=['symbol', 'interval', 'timestamp'],
                        set_={
                            'open': kline.open,
                            'high': kline.high,
                            'low': kline.low,
                            'close': kline.close,
                            'volume': kline.volume
                        }
                    )
                    await session.execute(stmt)
                await session.commit()
            
            # 更新缓存
            await self.redis_manager.cache_klines(symbol, interval, klines)
            
            self.logger.info(f"初始化 {symbol} {interval} K线数据，共 {len(klines)} 条")
    
    async def update_kline(self, symbol: str, interval: str, kline: Candlestick) -> bool:
        """更新K线数据，返回是否发生更新"""
        async with self._lock:
            # 检查是否需要更新
            async with self._async_session() as session:
                # 查询现有数据
                stmt = select(CandlestickModel).where(
                    CandlestickModel.symbol == symbol,
                    CandlestickModel.interval == interval,
                    CandlestickModel.timestamp == kline.timestamp
                )
                result = await session.execute(stmt)
                existing_kline = result.scalar_one_or_none()
                
                # 检查是否需要更新
                updated = False
                if not existing_kline or (
                    existing_kline.close != kline.close or
                    existing_kline.high != kline.high or
                    existing_kline.low != kline.low or
                    existing_kline.volume != kline.volume
                ):
                    # 更新数据库
                    stmt = insert(CandlestickModel).values(
                        symbol=symbol,
                        interval=interval,
                        timestamp=kline.timestamp,
                        open=kline.open,
                        high=kline.high,
                        low=kline.low,
                        close=kline.close,
                        volume=kline.volume
                    ).on_conflict_do_update(
                        index_elements=['symbol', 'interval', 'timestamp'],
                        set_={
                            'open': kline.open,
                            'high': kline.high,
                            'low': kline.low,
                            'close': kline.close,
                            'volume': kline.volume
                        }
                    )
                    await session.execute(stmt)
                    await session.commit()
                    updated = True
                    
                    # 更新缓存
                    if updated:
                        await self.redis_manager.update_kline(symbol, interval, kline)
                    
            return updated
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 1000) -> List[Candlestick]:
        """获取K线数据，优先从缓存获取"""
        # 尝试从缓存获取
        cached_klines = await self.redis_manager.get_cached_klines(symbol, interval)
        if cached_klines:
            # 将缓存数据转换为Candlestick对象
            return [
                Candlestick(
                    timestamp=k['timestamp'],
                    open=k['open'],
                    high=k['high'],
                    low=k['low'],
                    close=k['close'],
                    volume=k['volume']
                ) for k in cached_klines[-limit:]  # 只返回最新的limit条数据
            ]
        
        # 如果缓存未命中，从数据库获取
        async with self._async_session() as session:
            stmt = select(CandlestickModel).where(
                CandlestickModel.symbol == symbol,
                CandlestickModel.interval == interval
            ).order_by(CandlestickModel.timestamp.desc()).limit(limit)
            
            result = await session.execute(stmt)
            db_klines = result.scalars().all()
            klines = [model.to_candlestick() for model in reversed(db_klines)]
            
            # 将数据库数据缓存到Redis
            if klines:
                await self.redis_manager.cache_klines(symbol, interval, klines)
            
            return klines
            
    async def close(self):
        """关闭连接"""
        await self._engine.dispose()
        await self.redis_manager.close()

# 创建全局实例
kline_manager = KlineManager(
    db_url="postgresql+asyncpg://moneymaster:moneymaster123@localhost/moneymaster",
    redis_url="redis://localhost"
)

async def init_db():
    async with kline_manager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 