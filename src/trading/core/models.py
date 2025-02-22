from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, create_engine, DECIMAL, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import Enum

Base = declarative_base()

class StrategyStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"
    PAUSED = "paused"

class TradeRecord(Base):
    __tablename__ = 'trade_records'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(String(50))
    symbol = Column(String(20))
    side = Column(String(4))  # BUY/SELL
    price = Column(DECIMAL(20, 8))
    quantity = Column(DECIMAL(20, 8))
    commission = Column(DECIMAL(20, 8))
    realized_pnl = Column(DECIMAL(20, 8))
    trade_time = Column(DateTime)
    strategy_name = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class StrategyState(Base):
    __tablename__ = 'strategy_states'
    
    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(50))
    symbol = Column(String(20))
    position = Column(DECIMAL(20, 8))
    avg_entry_price = Column(DECIMAL(20, 8))
    unrealized_pnl = Column(DECIMAL(20, 8))
    total_pnl = Column(DECIMAL(20, 8))
    total_commission = Column(DECIMAL(20, 8))
    status = Column(String(20), default=StrategyStatus.STOPPED.value)
    last_error = Column(Text)
    last_run_time = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)

class BalanceSnapshot(Base):
    __tablename__ = 'balance_snapshots'
    
    id = Column(Integer, primary_key=True)
    currency = Column(String(20))
    free_balance = Column(DECIMAL(20, 8))
    locked_balance = Column(DECIMAL(20, 8))
    snapshot_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

# 数据库连接和会话管理
def init_db(db_url):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session() 