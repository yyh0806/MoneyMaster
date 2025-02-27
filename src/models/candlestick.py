from sqlalchemy import Column, String, BigInteger, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class CandlestickModel(Base):
    __tablename__ = 'candlesticks'
    
    # 组合主键
    symbol = Column(String(50), primary_key=True)
    interval = Column(String(20), primary_key=True)
    timestamp = Column(BigInteger, primary_key=True)
    
    # 数据字段
    open = Column(String(50), nullable=False)
    high = Column(String(50), nullable=False)
    low = Column(String(50), nullable=False)
    close = Column(String(50), nullable=False)
    volume = Column(String(50), nullable=False)
    
    # 创建索引以优化查询性能
    __table_args__ = (
        Index('idx_symbol_interval_timestamp', 'symbol', 'interval', 'timestamp'),
    )
    
    def to_candlestick(self) -> 'Candlestick':
        """转换为Candlestick对象"""
        from src.api.market_data import Candlestick
        return Candlestick(
            timestamp=self.timestamp,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume
        )
    
    @classmethod
    def from_candlestick(cls, symbol: str, interval: str, candlestick: 'Candlestick') -> 'CandlestickModel':
        """从Candlestick对象创建数据库模型"""
        return cls(
            symbol=symbol,
            interval=interval,
            timestamp=candlestick.timestamp,
            open=candlestick.open,
            high=candlestick.high,
            low=candlestick.low,
            close=candlestick.close,
            volume=candlestick.volume
        ) 