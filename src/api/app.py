from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
from loguru import logger

from src.trading.client import OKXClient
from src.trading.strategies.simple_test import SimpleTestStrategy
from src.trading.core.models import init_db, TradeRecord, StrategyState, StrategyStatus
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
strategy = SimpleTestStrategy(
    client=okx_client,
    symbol="BTC-USDT",
    db_session=db_session
)

# 全局变量
strategy_task = None

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
async def get_kline(symbol: str, interval: str = "15m"):
    """获取K线数据"""
    try:
        logger.info(f"请求K线数据: symbol={symbol}, interval={interval}")
        response = okx_client.get_kline(
            instId=symbol,
            bar=interval,
            limit="100"  # 获取最近100根K线
        )
        logger.debug(f"OKX K线数据响应: {response}")
        
        if response.get('code') == '0':
            # 按时间正序排列
            data = sorted(response.get('data', []), key=lambda x: x[0])
            return {"code": "0", "msg": "", "data": data}
        else:
            error_msg = f"获取K线数据失败: {response.get('msg', '未知错误')}"
            logger.error(error_msg)
            return {"code": "1", "msg": error_msg, "data": []}
    except Exception as e:
        error_msg = f"获取K线数据异常: {str(e)}"
        logger.error(error_msg)
        return {"code": "1", "msg": error_msg, "data": []}

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
        "status": state.status,
        "last_error": state.last_error,
        "last_run_time": state.last_run_time.isoformat() if state.last_run_time else None,
        "updated_at": state.updated_at.isoformat()
    } for state in states]

@app.post("/api/strategy/start")
async def start_strategy():
    """启动策略"""
    global strategy_task
    
    try:
        await strategy.start()
        
        async def run_strategy():
            while True:
                try:
                    market_data = okx_client.get_market_price(strategy.symbol)
                    logger.info(f"策略执行中，市场数据: {market_data}")
                    strategy.on_tick(market_data)
                    await asyncio.sleep(60)  # 每分钟执行一次
                except Exception as e:
                    error_msg = f"Strategy error: {str(e)}"
                    logger.error(error_msg)
                    strategy.handle_error(error_msg)
                    await asyncio.sleep(5)
        
        if strategy_task:
            strategy_task.cancel()
        strategy_task = asyncio.create_task(run_strategy())
        
        # 确保状态已更新到数据库
        db_session.commit()
        return {"status": "Strategy started"}
    except Exception as e:
        logger.error(f"启动策略失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/strategy/stop")
async def stop_strategy():
    """停止策略"""
    global strategy_task
    
    try:
        await strategy.stop()
        if strategy_task:
            strategy_task.cancel()
            strategy_task = None
        
        # 确保状态已更新到数据库
        db_session.commit()
        return {"status": "Strategy stopped"}
    except Exception as e:
        logger.error(f"停止策略失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/strategy/pause")
async def pause_strategy():
    """暂停策略"""
    try:
        await strategy.pause()
        # 确保状态已更新到数据库
        db_session.commit()
        return {"status": "Strategy paused"}
    except Exception as e:
        logger.error(f"暂停策略失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"新的WebSocket连接已建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            await self.disconnect(websocket)

manager = ConnectionManager()

@app.websocket("/ws/market/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(websocket)
    try:
        last_data = None
        while websocket in manager.active_connections:
            try:
                # 获取市场数据和策略状态
                market_data = okx_client.get_market_price(symbol)
                strategy_state = db_session.query(StrategyState).filter_by(
                    symbol=symbol,
                    strategy_name=strategy.__class__.__name__
                ).first()
                
                if not strategy_state:
                    # 如果没有找到状态记录，创建一个新的
                    strategy_state = StrategyState(
                        strategy_name=strategy.__class__.__name__,
                        symbol=symbol,
                        position=Decimal('0'),
                        avg_entry_price=Decimal('0'),
                        unrealized_pnl=Decimal('0'),
                        total_pnl=Decimal('0'),
                        total_commission=Decimal('0'),
                        status=StrategyStatus.STOPPED.value
                    )
                    db_session.add(strategy_state)
                    db_session.commit()
                
                # 组合数据
                current_data = {
                    "market": market_data,
                    "strategy": {
                        "position": float(strategy_state.position),
                        "avg_entry_price": float(strategy_state.avg_entry_price),
                        "unrealized_pnl": float(strategy_state.unrealized_pnl),
                        "total_pnl": float(strategy_state.total_pnl),
                        "total_commission": float(strategy_state.total_commission),
                        "status": strategy_state.status,
                        "last_error": strategy_state.last_error,
                        "last_run_time": strategy_state.last_run_time.isoformat() if strategy_state.last_run_time else None
                    }
                }
                
                # 只有数据变化时才推送
                if current_data != last_data:
                    await manager.send_personal_message(json.dumps(current_data), websocket)
                    last_data = current_data
                
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"WebSocket处理错误: {e}")
                # 如果是数据库错误，尝试重新连接
                db_session.rollback()
                await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        manager.disconnect(websocket) 