from dataclasses import dataclass
from typing import Dict, List, Optional
import asyncio
from datetime import datetime
import json
from decimal import Decimal
from loguru import logger

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
    def __init__(self):
        self._klines: Dict[str, Dict[str, List[Candlestick]]] = {}
        self._lock = asyncio.Lock()
        self.logger = logger.bind(name="KlineManager")
        
    async def init_klines(self, symbol: str, interval: str, klines: List[Candlestick]):
        """初始化K线数据"""
        async with self._lock:
            if symbol not in self._klines:
                self._klines[symbol] = {}
            self._klines[symbol][interval] = sorted(klines, key=lambda x: x.timestamp)
            self.logger.info(f"初始化 {symbol} {interval} K线数据，共 {len(klines)} 条")
    
    async def update_kline(self, symbol: str, interval: str, kline: Candlestick) -> bool:
        """更新K线数据，返回是否发生更新"""
        async with self._lock:
            if symbol not in self._klines or interval not in self._klines[symbol]:
                self._klines[symbol] = {interval: []}
                
            klines = self._klines[symbol][interval]
            updated = False
            
            if not klines:
                klines.append(kline)
                updated = True
            elif kline.timestamp > klines[-1].timestamp:
                # 新的K线
                klines.append(kline)
                # 保持最多1000条数据
                if len(klines) > 1000:
                    klines.pop(0)
                updated = True
            elif kline.timestamp == klines[-1].timestamp:
                # 更新现有K线
                last_kline = klines[-1]
                if (last_kline.close != kline.close or
                    last_kline.high != kline.high or
                    last_kline.low != kline.low or
                    last_kline.volume != kline.volume):
                    klines[-1] = kline
                    updated = True
                    
            return updated
    
    async def get_klines(self, symbol: str, interval: str) -> List[Candlestick]:
        """获取K线数据"""
        async with self._lock:
            if symbol not in self._klines or interval not in self._klines[symbol]:
                return []
            return self._klines[symbol][interval].copy()

# 创建全局实例
kline_manager = KlineManager() 