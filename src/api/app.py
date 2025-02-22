from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
from loguru import logger
import sys

from src.trading.client import OKXClient
from src.trading.strategies.simple_test import SimpleTestStrategy
from src.trading.strategies.deepseek_strategy import DeepseekStrategy
from src.trading.core.models import init_db, TradeRecord, StrategyState, StrategyStatus
from src.trading.core.strategy import StoppedState
from src.config import settings

# 配置日志
logger.remove()  # 移除默认的日志处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[strategy]}</cyan> | <level>{message}</level>",
    level="INFO"
)

# 创建带有默认strategy字段的日志记录器
app_logger = logger.bind(strategy="WebSocket")

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
strategies = {
    'simple_test': SimpleTestStrategy(
        client=okx_client,
        symbol="BTC-USDT",
        db_session=db_session
    ),
    'deepseek': DeepseekStrategy(
        client=okx_client,
        symbol="BTC-USDT",
        db_session=db_session,
        quantity=Decimal('0.01'),
        min_interval=30
    )
}

# 全局变量
strategy_tasks = {}

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
        app_logger.info(f"请求K线数据: symbol={symbol}, interval={interval}")
        response = okx_client.get_kline(
            instId=symbol,
            bar=interval,
            limit="100"  # 获取最近100根K线
        )
        app_logger.debug(f"OKX K线数据响应: {response}")
        
        if response.get('code') == '0':
            # 按时间正序排列
            data = sorted(response.get('data', []), key=lambda x: x[0])
            return {"code": "0", "msg": "", "data": data}
        else:
            error_msg = f"获取K线数据失败: {response.get('msg', '未知错误')}"
            app_logger.error(error_msg)
            return {"code": "1", "msg": error_msg, "data": []}
    except Exception as e:
        error_msg = f"获取K线数据异常: {str(e)}"
        app_logger.error(error_msg)
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
async def get_strategy_state(symbol: str = None, strategy_type: str = None):
    """获取策略状态"""
    try:
        if strategy_type and strategy_type in strategies:
            # 如果指定了策略类型，直接返回该策略的状态
            strategy = strategies[strategy_type]
            state_info = strategy.state_info
            # 确保状态是有效的枚举值
            if not isinstance(state_info.get('status'), str) or state_info['status'] not in [s.value for s in StrategyStatus]:
                state_info['status'] = StrategyStatus.STOPPED.value
            return [state_info]
        
        # 否则查询数据库获取所有策略状态
        query = db_session.query(StrategyState)
        if symbol:
            query = query.filter(StrategyState.symbol == symbol)
        if strategy_type:
            query = query.filter(StrategyState.strategy_name == strategy_type)
        states = query.all()
        
        result = []
        for state in states:
            # 确保状态是有效的枚举值
            status = state.status if state.status in [s.value for s in StrategyStatus] else StrategyStatus.STOPPED.value
            result.append({
                "strategy_name": state.strategy_name,
                "symbol": state.symbol,
                "position": float(state.position),
                "avg_entry_price": float(state.avg_entry_price),
                "unrealized_pnl": float(state.unrealized_pnl),
                "total_pnl": float(state.total_pnl),
                "total_commission": float(state.total_commission),
                "status": status,
                "last_error": state.last_error,
                "last_run_time": state.last_run_time.isoformat() if state.last_run_time else None,
                "updated_at": state.updated_at.isoformat()
            })
        return result
    except Exception as e:
        app_logger.error(f"获取策略状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy/start")
async def start_strategy(strategy_type: str = "deepseek"):
    """启动策略"""
    try:
        app_logger.info(f"收到启动策略请求: strategy_type={strategy_type}")
        app_logger.info(f"当前可用策略: {list(strategies.keys())}")
        
        if strategy_type not in strategies:
            error_msg = f"未知的策略类型: {strategy_type}"
            app_logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        strategy = strategies[strategy_type]
        app_logger.info(f"尝试启动策略 {strategy_type}, 当前状态: {strategy.current_state}")
        
        # 检查策略状态
        if strategy.is_running:
            error_msg = "策略已经在运行中"
            app_logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        try:
            await strategy.start()
            app_logger.info(f"策略 {strategy_type} start() 调用成功")
            await strategy.on_start()
            app_logger.info(f"策略 {strategy_type} on_start() 调用成功")
        except Exception as e:
            error_msg = f"启动策略过程中出错: {str(e)}"
            app_logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        state_info = strategy.state_info
        app_logger.info(f"策略 {strategy_type} 启动成功，新状态: {state_info}")
        
        return {"status": "success", "message": "策略已启动", "state": state_info}
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"启动策略失败: {str(e)}"
        app_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/strategy/stop")
async def stop_strategy(strategy_type: str = "deepseek"):
    """停止策略"""
    try:
        if strategy_type not in strategies:
            raise HTTPException(status_code=400, detail=f"未知的策略类型: {strategy_type}")
        
        strategy = strategies[strategy_type]
        app_logger.info(f"尝试停止策略 {strategy_type}, 当前状态: {strategy.current_state}")
        
        # 检查策略状态
        if not strategy.is_running:
            raise HTTPException(status_code=400, detail="策略未在运行中")
        
        # 停止策略
        await strategy.on_stop()
        await strategy.stop()
        
        # 获取最新状态
        state_info = strategy.state_info
        app_logger.info(f"策略 {strategy_type} 停止成功，新状态: {state_info['status']}")
        
        return {"status": "success", "message": "策略已停止", "state": state_info}
        
    except Exception as e:
        error_msg = f"停止策略失败: {str(e)}"
        app_logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

@app.post("/api/strategy/pause")
async def pause_strategy(strategy_type: str = "deepseek"):
    """暂停策略"""
    try:
        if strategy_type not in strategies:
            raise HTTPException(status_code=400, detail=f"未知的策略类型: {strategy_type}")
        
        strategy = strategies[strategy_type]
        app_logger.info(f"尝试暂停策略 {strategy_type}, 当前状态: {strategy.current_state}")
        
        # 检查策略状态
        if not strategy.is_running:
            raise HTTPException(status_code=400, detail="策略未在运行中，无法暂停")
        
        # 暂停策略
        await strategy.pause()
        
        # 获取最新状态
        state_info = strategy.state_info
        app_logger.info(f"策略 {strategy_type} 暂停成功，新状态: {state_info['status']}")
        
        return {"status": "success", "message": "策略已暂停", "state": state_info}
        
    except Exception as e:
        error_msg = f"暂停策略失败: {str(e)}"
        app_logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

@app.post("/api/clear_history")
async def clear_history():
    """清空所有历史记录"""
    try:
        # 清空交易记录
        db_session.query(TradeRecord).delete()
        
        # 重置策略状态的计数器，但保持运行状态不变
        states = db_session.query(StrategyState).all()
        for state in states:
            state.position = Decimal('0')
            state.avg_entry_price = Decimal('0')
            state.unrealized_pnl = Decimal('0')
            state.total_pnl = Decimal('0')
            state.total_commission = Decimal('0')
            state.last_error = None
            # 不修改 status，保持原有状态
        
        # 提交更改
        db_session.commit()
        
        # 重置策略实例的计数器，但不改变状态
        for strategy in strategies.values():
            strategy.position = Decimal('0')
            strategy.avg_entry_price = Decimal('0')
            strategy.total_pnl = Decimal('0')
            strategy.total_commission = Decimal('0')
        
        return {"status": "success", "message": "历史记录已清空"}
    except Exception as e:
        logger.error(f"清空历史记录失败: {e}")
        db_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = app_logger  # 使用带有strategy字段的日志记录器

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"新的WebSocket连接已建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                await websocket.send_text(message)
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            self.disconnect(websocket)  # 移除await，因为disconnect不是异步函数

manager = ConnectionManager()

@app.websocket("/ws/market/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(websocket)
    try:
        last_data = None
        while True:  # 改为无限循环
            if websocket not in manager.active_connections:  # 检查连接是否还活着
                break
                
            try:
                # 获取市场数据
                market_data = okx_client.get_market_price(symbol)
                if not market_data:  # 检查市场数据是否有效
                    continue
                    
                # 获取所有策略的状态
                strategy_states = []
                for strategy_name, strategy in strategies.items():
                    if strategy.symbol == symbol:
                        strategy_states.append(strategy.state_info)
                
                # 组合数据
                current_data = {
                    "market": market_data,
                    "strategies": strategy_states
                }
                
                # 只有数据变化时才推送
                if current_data != last_data:
                    if websocket in manager.active_connections:  # 再次检查连接是否存活
                        await manager.send_personal_message(json.dumps(current_data), websocket)
                        last_data = current_data
                
                await asyncio.sleep(1)
            except Exception as e:
                app_logger.error(f"WebSocket处理错误: {e}")
                if "cannot send after transport endpoint is closed" in str(e):
                    break  # 如果连接已关闭，退出循环
                db_session.rollback()
                await asyncio.sleep(1)
    except Exception as e:
        app_logger.error(f"WebSocket连接错误: {e}")
    finally:
        manager.disconnect(websocket)

@app.websocket("/ws/strategy/{symbol}")
async def strategy_websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(websocket)
    
    # 初始化策略
    strategy_type = 'deepseek'  # 假设使用 deepseek 策略
    if strategy_type not in strategies:
        app_logger.error(f"Unknown strategy type: {strategy_type}")
        manager.disconnect(websocket)
        return
    
    strategy = strategies[strategy_type]
    
    try:
        last_data = None
        while True:  # 改为无限循环
            if websocket not in manager.active_connections:  # 检查连接是否还活着
                break
                
            try:
                # 获取市场数据和策略状态
                market_data = okx_client.get_market_price(symbol)
                if not market_data:  # 检查市场数据是否有效
                    continue
                    
                strategy_info = strategy.state_info
                
                # 获取最新的分析结果
                analysis_data = strategy.last_analysis or {
                    'analysis_content': '等待AI分析...',
                    'recommendation': 'HOLD',
                    'confidence': 0,
                    'reasoning': '正在收集市场数据...',
                    'error': False
                }
                
                # 组合数据
                current_data = {
                    "market": market_data,
                    "strategy": strategy_info,
                    "analysis": analysis_data
                }
                
                # 只有数据变化时才推送
                if current_data != last_data:
                    if websocket in manager.active_connections:  # 再次检查连接是否存活
                        await manager.send_personal_message(json.dumps(current_data), websocket)
                        last_data = current_data
                
                await asyncio.sleep(1)
            except Exception as e:
                app_logger.error(f"WebSocket处理错误: {e}")
                if "cannot send after transport endpoint is closed" in str(e):
                    break  # 如果连接已关闭，退出循环
                db_session.rollback()
                await asyncio.sleep(1)
    except Exception as e:
        app_logger.error(f"WebSocket连接错误: {e}")
    finally:
        manager.disconnect(websocket) 