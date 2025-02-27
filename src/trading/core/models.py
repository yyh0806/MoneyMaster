from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, create_engine, DECIMAL, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import Enum
from src.config import settings

Base = declarative_base()

# 数据库引擎和会话工厂
engine = None
Session = None

def get_engine():
    """获取数据库引擎，如果不存在则创建"""
    global engine
    if engine is None:
        engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO
        )
    return engine

def get_session():
    """获取数据库会话工厂，如果不存在则创建"""
    global Session
    if Session is None:
        Session = sessionmaker(bind=get_engine())
    return Session

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
    
    # 资金管理相关字段
    initial_capital = Column(DECIMAL(20, 8))  # 初始资金
    current_capital = Column(DECIMAL(20, 8))  # 当前总资金
    available_capital = Column(DECIMAL(20, 8))  # 可用资金
    max_position_size = Column(DECIMAL(20, 8))  # 最大持仓比例
    max_single_trade_size = Column(DECIMAL(20, 8))  # 单次交易最大比例

class BalanceSnapshot(Base):
    __tablename__ = 'balance_snapshots'
    
    id = Column(Integer, primary_key=True)
    currency = Column(String(20))
    free_balance = Column(DECIMAL(20, 8))
    locked_balance = Column(DECIMAL(20, 8))
    snapshot_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

async def init_db():
    """初始化数据库"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return get_session()() 