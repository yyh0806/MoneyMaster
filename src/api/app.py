from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
from loguru import logger

from src.trading.client import OKXClient
from src.trading.strategies.ma_cross import MACrossStrategy
from src.trading.core.models import init_db, TradeRecord, StrategyState
from src.config import settings

app = FastAPI(title="MoneyMaster API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建OKX客户端实例
okx_client = OKXClient()

# 初始化数据库会话
db_session = init_db("sqlite:///trading.db")

# 创建策略实例
strategy = MACrossStrategy(
    client=okx_client,
    symbol="BTC-USDT",
    db_session=db_session,
    fast_period=5,
    slow_period=20,
    quantity=Decimal('0.001')
)

# 全局变量
strategy_task = None
is_strategy_running = False

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/account/balance")
async def get_balance():
    """获取账户余额"""
    try:
        response = okx_client.get_account_balance()
        if response.get('code') == '0' and response.get('data'):
            balances = {}
            for item in response['data'][0].get('details', []):
                balances[item['ccy']] = float(item.get('cashBal', 0))
            return balances
        return {}
    except Exception as e:
        logger.error(f"获取账户余额失败: {e}")
        return {}

@app.get("/api/market/price/{symbol}")
async def get_market_price(symbol: str):
    """获取市场价格"""
    return okx_client.get_market_price(symbol)

@app.get("/api/market/kline/{symbol}")
async def get_kline(symbol: str, interval: str = "1m", limit: str = "100"):
    """获取K线数据"""
    return okx_client.get_kline(symbol, bar=interval, limit=limit)

@app.get("/api/trades")
async def get_trades(symbol: str = None, limit: int = 100):
    """获取交易记录"""
    query = db_session.query(TradeRecord)
    if symbol:
        query = query.filter(TradeRecord.symbol == symbol)
    trades = query.order_by(TradeRecord.trade_time.desc()).limit(limit).all()
    
    return [{
        "trade_id": trade.trade_id,
        "symbol": trade.symbol,
        "side": trade.side,
        "price": float(trade.price),
        "quantity": float(trade.quantity),
        "commission": float(trade.commission),
        "realized_pnl": float(trade.realized_pnl),
        "trade_time": trade.trade_time.isoformat(),
        "strategy_name": trade.strategy_name
    } for trade in trades]

@app.get("/api/strategy/state")
async def get_strategy_state(symbol: str = None):
    """获取策略状态"""
    query = db_session.query(StrategyState)
    if symbol:
        query = query.filter(StrategyState.symbol == symbol)
    states = query.all()
    
    return [{
        "strategy_name": state.strategy_name,
        "symbol": state.symbol,
        "position": float(state.position),
        "avg_entry_price": float(state.avg_entry_price),
        "unrealized_pnl": float(state.unrealized_pnl),
        "total_pnl": float(state.total_pnl),
        "total_commission": float(state.total_commission),
        "updated_at": state.updated_at.isoformat()
    } for state in states]

@app.post("/api/strategy/start")
async def start_strategy():
    """启动策略"""
    global strategy_task, is_strategy_running
    
    if is_strategy_running:
        raise HTTPException(status_code=400, detail="Strategy is already running")
    
    async def run_strategy():
        global is_strategy_running
        logger.info("策略启动...")
        is_strategy_running = True
        
        while is_strategy_running:
            try:
                market_data = okx_client.get_market_price(strategy.symbol)
                logger.debug(f"获取到市场数据: {market_data}")
                
                strategy.on_tick(market_data)
                await asyncio.sleep(60)  # 每分钟执行一次
            except Exception as e:
                logger.error(f"Strategy error: {e}")
                await asyncio.sleep(5)
    
    strategy_task = asyncio.create_task(run_strategy())
    return {"status": "Strategy started"}

@app.post("/api/strategy/stop")
async def stop_strategy():
    """停止策略"""
    global strategy_task, is_strategy_running
    
    if not is_strategy_running:
        raise HTTPException(status_code=400, detail="Strategy is not running")
    
    is_strategy_running = False
    if strategy_task:
        strategy_task.cancel()
        strategy_task = None
    
    logger.info("策略停止")
    return {"status": "Strategy stopped"}

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/market/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(websocket)
    try:
        while True:
            # 获取市场数据和策略状态
            market_data = okx_client.get_market_price(symbol)
            strategy_state = db_session.query(StrategyState).filter_by(
                symbol=symbol,
                strategy_name=strategy.__class__.__name__
            ).first()
            
            # 组合数据
            data = {
                "market": market_data,
                "strategy": {
                    "position": float(strategy_state.position) if strategy_state else 0,
                    "avg_entry_price": float(strategy_state.avg_entry_price) if strategy_state else 0,
                    "unrealized_pnl": float(strategy_state.unrealized_pnl) if strategy_state else 0,
                    "total_pnl": float(strategy_state.total_pnl) if strategy_state else 0,
                    "total_commission": float(strategy_state.total_commission) if strategy_state else 0,
                    "is_running": is_strategy_running
                }
            }
            
            # 广播给所有连接的客户端
            await websocket.send_text(json.dumps(data))
            # 等待1秒
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket) 