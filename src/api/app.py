from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
from loguru import logger
import sys

from src.trading.clients.okx.client import OKXClient
from src.trading.strategies.deepseek import DeepseekStrategy
from src.trading.core.models import init_db, TradeRecord, StrategyState, StrategyStatus
from src.trading.core.strategy import StoppedState
from src.trading.core.risk import RiskLimit
from src.config import settings
from .websocket import manager, setup_event_handlers

# 配置日志
logger.remove()  # 移除默认的日志处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
    level="INFO"
)

# 创建带有默认strategy字段的日志记录器
app_logger = logger.bind(name="WebSocket")

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
okx_client = OKXClient(
    symbol="BTC-USDT",
    api_key=settings.API_KEY,
    api_secret=settings.SECRET_KEY,
    passphrase=settings.PASSPHRASE,
    testnet=settings.USE_TESTNET
)

# 初始化数据库会话
db_session = init_db("sqlite:///trading.db")

# 初始化事件处理器
setup_event_handlers()

# 初始化WebSocket连接
@app.on_event("startup")
async def startup_event():
    """服务启动时初始化WebSocket连接"""
    app_logger.info("正在初始化WebSocket连接...")
    try:
        connected = await okx_client.connect()
        if connected:
            app_logger.info("WebSocket连接成功")
            # 预先订阅所有需要的数据
            symbol = okx_client.symbol
            await okx_client.subscribe_ticker(symbol)
            await okx_client.subscribe_orderbook(symbol)
            await okx_client.subscribe_trades(symbol)
            
            # 订阅K线周期
            intervals = ["1m", "5m", "15m", "30m", "1H", "4H", "1D"]
            for interval in intervals:
                try:
                    app_logger.info(f"订阅K线数据: {interval}")
                    await okx_client.subscribe_candlesticks(symbol, interval)
                    await asyncio.sleep(1)  # 添加延迟，避免请求过快
                except Exception as e:
                    app_logger.error(f"订阅K线数据失败 {interval}: {e}")
            app_logger.info("市场数据订阅成功")
            
            # 启动消息处理
            await okx_client.ws_client.start()
        else:
            app_logger.error("WebSocket连接失败")
    except Exception as e:
        app_logger.error(f"初始化WebSocket连接失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时断开WebSocket连接"""
    app_logger.info("正在关闭WebSocket连接...")
    try:
        await okx_client.disconnect()
        app_logger.info("WebSocket连接已关闭")
    except Exception as e:
        app_logger.error(f"关闭WebSocket连接失败: {e}")

# 创建策略实例
strategy = DeepseekStrategy(
    client=okx_client,
    symbol="BTC-USDT",
    db_session=db_session,
    risk_limit=RiskLimit(
        total_capital=Decimal('100000'),        # 总资金10万
        max_capital_usage=Decimal('0.8'),       # 最大使用80%
        reserve_capital=Decimal('10000'),       # 保留1万作为准备金
        max_position_value=Decimal('50000'),    # 最大持仓5万
        max_leverage=3,                         # 最大杠杆3倍
        min_margin_ratio=Decimal('0.1'),        # 最小保证金率10%
        max_daily_loss=Decimal('1000'),         # 最大日亏损1000
        max_order_value=Decimal('10000'),       # 单笔最大1万
        min_order_value=Decimal('100'),         # 单笔最小100
        price_deviation=Decimal('0.03')         # 价格偏离度3%
    ),
    quantity=Decimal('0.01'),
    min_interval=30,
    commission_rate=Decimal('0.001')
)

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
        balances = await okx_client.get_account_balance()
        return {
            "code": "0",
            "msg": "",
            "data": balances
        }
    except NotImplementedError as e:
        return {
            "code": "1",
            "msg": str(e),
            "data": None
        }
    except Exception as e:
        error_msg = f"获取账户余额失败: {e}"
        logger.error(error_msg)
        return {
            "code": "1",
            "msg": error_msg,
            "data": None
        }

@app.get("/api/market/price/{symbol}")
async def get_market_price(symbol: str):
    """获取市场价格"""
    try:
        data = await okx_client.get_market_price(symbol)
        if data:
            # 确保返回的数据格式正确
            return {
                "code": "0",
                "msg": "",
                "data": {
                    "symbol": symbol,
                    "last_price": data.get("last"),
                    "best_bid": data.get("best_bid"),
                    "best_ask": data.get("best_ask"),
                    "volume_24h": data.get("volume_24h"),
                    "high_24h": data.get("high_24h"),
                    "low_24h": data.get("low_24h"),
                    "timestamp": data.get("timestamp")
                }
            }
        return {
            "code": "1",
            "msg": "获取市场价格失败",
            "data": None
        }
    except Exception as e:
        error_msg = f"获取市场价格失败: {e}"
        logger.error(error_msg)
        return {
            "code": "1",
            "msg": error_msg,
            "data": None
        }

@app.get("/api/market/kline/{symbol}")
async def get_kline(
    symbol: str, 
    interval: str = "15m",
    start_time: int = None,
    end_time: int = None,
    limit: int = 200
):
    """获取K线数据
    
    Args:
        symbol: 交易对
        interval: K线周期，默认15分钟
        start_time: 开始时间戳（毫秒）
        end_time: 结束时间戳（毫秒）
        limit: 返回的K线数量限制，默认200
        
    Returns:
        返回指定时间范围内的K线数据
    """
    try:
        app_logger.info(f"请求K线数据: symbol={symbol}, interval={interval}, start_time={start_time}, end_time={end_time}, limit={limit}")
        
        # 如果没有指定时间范围，使用默认的时间范围
        if not end_time:
            end_time = int(datetime.now().timestamp() * 1000)
            
        if not start_time:
            # 根据interval和limit计算默认的start_time
            period_map = {
                "1m": 60,
                "5m": 300,
                "15m": 900,
                "1H": 3600,
                "4H": 14400,
                "1D": 86400
            }
            period_seconds = period_map.get(interval, 900)  # 默认15分钟
            start_time = end_time - (period_seconds * limit * 1000)
        
        # 获取K线数据
        candlesticks = await okx_client.get_candlesticks(
            symbol, 
            interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        app_logger.debug(f"获取到K线数据: {candlesticks}")
        
        if not candlesticks:
            return {
                "code": "1",
                "msg": "获取K线数据失败",
                "data": []
            }
            
        # 转换为前端需要的格式
        data = []
        for candle in candlesticks:
            data.append([
                int(candle.timestamp.timestamp() * 1000),  # 时间戳
                str(candle.open),                          # 开盘价
                str(candle.high),                          # 最高价
                str(candle.low),                           # 最低价
                str(candle.close),                         # 收盘价
                str(candle.volume),                        # 成交量
            ])
            
        # 按时间正序排列
        data.sort(key=lambda x: x[0])
            
        return {
            "code": "0",
            "msg": "",
            "data": data
        }
    except Exception as e:
        error_msg = f"获取K线数据异常: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "1",
            "msg": error_msg,
            "data": []
        }

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
    try:
        # 返回当前策略的状态
        state_info = strategy.state_info
        # 确保状态是有效的枚举值
        if not isinstance(state_info.get('status'), str) or state_info['status'] not in [s.value for s in StrategyStatus]:
            state_info['status'] = StrategyStatus.STOPPED.value
        return [state_info]
    except Exception as e:
        app_logger.error(f"获取策略状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy/start")
async def start_strategy():
    """启动策略"""
    try:
        app_logger.info("收到启动策略请求")
        
        # 检查策略状态
        if strategy.is_running:
            error_msg = "策略已经在运行中"
            app_logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        try:
            await strategy.start()
            app_logger.info("策略启动请求已发送")
            return {"status": "success", "message": "策略启动中"}
        except Exception as e:
            error_msg = f"启动策略失败: {str(e)}"
            app_logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"启动策略失败: {str(e)}"
        app_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/strategy/stop")
async def stop_strategy():
    """停止策略"""
    try:
        app_logger.info("尝试停止策略")
        
        # 检查策略状态
        if not strategy.is_running:
            raise HTTPException(status_code=400, detail="策略未在运行中")
        
        # 停止策略
        await strategy._on_stop()
        await strategy.stop()
        
        # 获取最新状态
        state_info = strategy.state_info
        app_logger.info(f"策略停止成功，新状态: {state_info['status']}")
        
        return {"status": "success", "message": "策略已停止", "state": state_info}
        
    except Exception as e:
        error_msg = f"停止策略失败: {str(e)}"
        app_logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

@app.post("/api/strategy/pause")
async def pause_strategy():
    """暂停策略"""
    try:
        app_logger.info("尝试暂停策略")
        
        # 检查策略状态
        if not strategy.is_running:
            raise HTTPException(status_code=400, detail="策略未在运行中，无法暂停")
        
        # 暂停策略
        await strategy.pause()
        
        # 获取最新状态
        state_info = strategy.state_info
        app_logger.info(f"策略暂停成功，新状态: {state_info['status']}")
        
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
        strategy.position = Decimal('0')
        strategy.avg_entry_price = Decimal('0')
        strategy.total_pnl = Decimal('0')
        strategy.total_commission = Decimal('0')
        
        return {"status": "success", "message": "历史记录已清空"}
    except Exception as e:
        logger.error(f"清空历史记录失败: {e}")
        db_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/market/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    try:
        await manager.connect(websocket, symbol)
        last_market_data = None
        
        while True:
            try:
                # 检查连接是否还在活跃状态
                if symbol not in manager.active_connections or websocket not in manager.active_connections[symbol]:
                    app_logger.warning(f"连接已不在活跃列表中: {symbol}")
                    break
                    
                # 获取完整的市场数据
                market_data = {
                    "ticker": await okx_client.get_ticker(symbol),
                    "orderbook": await okx_client.get_orderbook(symbol),
                    "trades": await okx_client.get_trades(symbol, limit=10)  # 最近10条成交
                }
                
                if market_data != last_market_data:
                    try:
                        # 检查连接状态
                        if websocket.client_state.DISCONNECTED:
                            app_logger.warning("连接已断开")
                            break
                            
                        await manager.send_personal_message(
                            json.dumps({
                                "code": "0",
                                "msg": "",
                                "data": market_data
                            }),
                            websocket
                        )
                        last_market_data = market_data
                    except Exception as e:
                        app_logger.error(f"发送市场数据失败: {e}")
                        break
                
                # 获取K线数据
                try:
                    kline_data = await okx_client.get_candlesticks(
                        symbol,
                        interval="15m",  # 默认使用15分钟K线
                        limit=1  # 只获取最新的一根K线
                    )
                    
                    if kline_data:
                        await manager.send_personal_message(
                            json.dumps({
                                "code": "0",
                                "msg": "",
                                "data": kline_data
                            }),
                            websocket
                        )
                except Exception as e:
                    app_logger.error(f"发送K线数据失败: {e}")
                
                await asyncio.sleep(1)
            except Exception as e:
                app_logger.error(f"WebSocket处理错误: {e}")
                if "cannot send after transport endpoint is closed" in str(e):
                    break
                await asyncio.sleep(1)
    except Exception as e:
        app_logger.error(f"WebSocket连接错误: {e}")
    finally:
        await manager.disconnect(websocket, symbol)

@app.websocket("/ws/strategy/{symbol}")
async def strategy_websocket_endpoint(websocket: WebSocket, symbol: str):
    try:
        await manager.connect(websocket, symbol)
        last_market_data = None
        last_analysis = None
        
        # 订阅市场数据
        await okx_client.subscribe_ticker(symbol)
        await okx_client.subscribe_orderbook(symbol)
        
        while True:
            try:
                if symbol not in manager.active_connections or websocket not in manager.active_connections[symbol]:
                    break
                    
                # 获取市场数据和策略状态
                market_data = await okx_client.get_market_price(symbol)
                strategy_state = strategy.state_info
                current_analysis = strategy.last_analysis
                
                # 格式化推理过程
                if current_analysis and 'reasoning' in current_analysis:
                    reasoning = current_analysis['reasoning']
                    if isinstance(reasoning, list):
                        # 格式化每个推理点
                        formatted_reasoning = []
                        for reason in reasoning:
                            # 清理文本并确保以句号结尾
                            cleaned_reason = reason.strip().rstrip('。') + '。'
                            formatted_reasoning.append(cleaned_reason)
                        
                        # 将推理过程转换为前端需要的格式
                        current_analysis['reasoning'] = '\n'.join(formatted_reasoning)
                
                # 构建完整的更新数据
                update_data = {
                    "market": market_data if market_data else {},
                    "strategy": strategy_state,
                    "analysis": current_analysis
                }
                
                # 检查数据是否有变化
                if (market_data != last_market_data or 
                    current_analysis != last_analysis):
                    try:
                        await manager.send_personal_message(
                            json.dumps(update_data),
                            websocket
                        )
                        last_market_data = market_data
                        last_analysis = current_analysis
                    except Exception as e:
                        app_logger.error(f"发送数据失败: {e}")
                
                await asyncio.sleep(1)
            except Exception as e:
                app_logger.error(f"WebSocket处理错误: {e}")
                if "cannot send after transport endpoint is closed" in str(e):
                    break
                await asyncio.sleep(1)
    except Exception as e:
        app_logger.error(f"WebSocket连接错误: {e}")
    finally:
        await manager.disconnect(websocket, symbol)

@app.get("/api/v5/market/history-candles")
async def get_history_candlesticks(
    instId: str,
    bar: str = "15m",
    limit: int = 200,
    before: Optional[int] = None
):
    """获取历史K线数据
    
    Args:
        instId: 产品ID
        bar: K线周期，如15m, 1H, 4H等
        limit: 返回的K线数量限制，默认200
        before: 时间戳（毫秒），返回该时间戳之前的数据
        
    Returns:
        返回指定时间范围内的K线数据
    """
    try:
        app_logger.info(f"请求历史K线数据: instId={instId}, bar={bar}, limit={limit}, before={before}")
        
        # 获取历史K线数据
        candlesticks = await okx_client.get_history_candlesticks(
            symbol=instId,
            interval=bar,
            limit=limit,
            end_time=before
        )
        
        app_logger.debug(f"获取到历史K线数据: {candlesticks}")
        
        if not candlesticks:
            return {
                "code": "1",
                "msg": "获取历史K线数据失败",
                "data": []
            }
            
        # 转换为前端需要的格式
        data = []
        for candle in candlesticks:
            data.append([
                int(candle.timestamp.timestamp() * 1000),  # 时间戳
                str(candle.open),                          # 开盘价
                str(candle.high),                          # 最高价
                str(candle.low),                           # 最低价
                str(candle.close),                         # 收盘价
                str(candle.volume),                        # 成交量
            ])
            
        # 按时间正序排列
        data.sort(key=lambda x: x[0])
            
        return {
            "code": "0",
            "msg": "",
            "data": data
        }
    except Exception as e:
        error_msg = f"获取历史K线数据异常: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "1",
            "msg": error_msg,
            "data": []
        }

@app.get("/api/market/full-history-kline/{symbol}")
async def get_full_history_kline(
    symbol: str,
    interval: str = "15m"
):
    """获取完整的历史K线数据
    
    Args:
        symbol: 交易对
        interval: K线周期，默认15分钟
        
    Returns:
        返回指定时间范围内的完整K线数据
    """
    try:
        app_logger.info(f"请求完整历史K线数据: symbol={symbol}, interval={interval}")
        
        # 获取完整的历史K线数据
        response = await okx_client.get_full_history_kline(symbol, interval)
        
        if response.get("code") == "0":
            app_logger.info(f"获取到{len(response['data'])}条历史K线数据")
        else:
            app_logger.warning(f"获取历史K线数据失败: {response.get('msg')}")
            
        return response
        
    except Exception as e:
        error_msg = f"获取历史K线数据异常: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "1",
            "msg": error_msg,
            "data": []
        } 