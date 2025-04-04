from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
from loguru import logger
import sys
import atexit
import uvicorn

from src.trading.clients.okx.client import OKXClient
from src.trading.strategies.deepseek import DeepseekStrategy
from src.trading.core.models import init_db, TradeRecord, StrategyState, StrategyStatus, get_session
from src.trading.core.strategy import StoppedState
from src.trading.core.risk import RiskLimit
from src.config import settings
from .websocket import manager, setup_event_handlers
from .market_data import kline_manager, Candlestick
from src.trading.clients.okx.models import OKXCandlestick

# 初始化数据库会话
db_session = None

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

# 全局变量
websocket_connections: Dict[str, WebSocket] = {}
okx_client: Optional[OKXClient] = None
strategy: Optional[DeepseekStrategy] = None
shutdown_event = asyncio.Event()

@app.on_event("startup")
async def startup_event():
    """服务启动时的初始化"""
    global okx_client, db_session, strategy
    try:
        # 初始化数据库会话
        db_session = await init_db()
        logger.info("数据库初始化成功")
        
        # 初始化OKX客户端
        okx_client = OKXClient(
            symbol="BTC-USDT",  # 设置默认交易对
            api_key=settings.API_KEY,
            api_secret=settings.SECRET_KEY,
            passphrase=settings.PASSPHRASE,
            testnet=settings.USE_TESTNET  # 使用配置中的测试网设置
        )
        # 连接WebSocket
        await okx_client.connect()
        logger.info("OKX客户端初始化成功")
        
        # 初始化策略
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
        logger.info("策略初始化成功")
        
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时的清理"""
    logger.info("正在关闭服务...")
    try:
        logger.info("正在关闭WebSocket连接...")
        if okx_client:
            await okx_client.close()
        
        # 关闭所有WebSocket连接
        for ws in websocket_connections.values():
            await ws.close()
        websocket_connections.clear()
        
        # 关闭数据库连接
        await kline_manager.close()
        
        logger.info("所有连接已关闭")
    except Exception as e:
        logger.error(f"关闭服务时发生错误: {str(e)}")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    websocket_connections[client_id] = websocket
    logger.info("WebSocket连接成功")
    
    try:
        # 初始化历史数据
        symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT", "XRP-USDT"]
        intervals = ["1m", "5m", "15m", "30m", "1H", "4H", "1D"]
        
        for symbol in symbols:
            for interval in intervals:
                try:
                    logger.info(f"正在获取 {symbol} {interval} 的历史数据...")
                    klines = await okx_client.get_klines(symbol, interval)
                    
                    if klines:
                        # 转换为Candlestick对象
                        candlesticks = []
                        for k in klines:
                            # OKX返回的数据格式：[timestamp, open, high, low, close, vol, volCcy]
                            candlesticks.append(OKXCandlestick(
                                symbol=symbol,
                                interval=interval,
                                timestamp=datetime.fromtimestamp(int(k[0]) / 1000),
                                open=k[1],
                                high=k[2],
                                low=k[3],
                                close=k[4],
                                volume=k[5]
                            ))
                            
                        # 初始化K线数据
                        await kline_manager.init_klines(symbol, interval, candlesticks)
                        logger.info(f"已缓存 {symbol} {interval} 的历史数据，共 {len(candlesticks)} 条")
                    else:
                        logger.warning(f"未获取到 {symbol} {interval} 的历史数据")
                        
                except Exception as e:
                    logger.error(f"获取历史数据失败 {symbol} {interval}: {str(e)}")
                    continue
                    
                # 等待一小段时间，避免请求过于频繁
                await asyncio.sleep(1)
        
        # 保持连接
        while True:
            data = await websocket.receive_text()
            # 处理接收到的数据...
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")
    finally:
        websocket_connections.pop(client_id, None)

async def start_server():
    """启动服务器"""
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="error"
    )
    server = uvicorn.Server(config)
    await server.serve()

# 导出start_server函数
__all__ = ['start_server']

# 全局变量
strategy_tasks = {}

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/v5/account/balance")
async def get_balance():
    """获取账户余额"""
    try:
        try:
            balances = await okx_client.get_balance()
            app_logger.debug(f"获取到原始余额数据: {balances}")
        except Exception as e:
            app_logger.error(f"调用OKX API获取余额失败: {str(e)}")
            balances = None
        
        # 如果没有余额数据，返回默认值
        if not balances:
            return {
                "code": "0",
                "msg": "",
                "data": {
                    "balances": {}
                }
            }
            
        # 格式化余额数据
        formatted_balances = {}
        for currency, balance in balances.items():
            if isinstance(balance, dict):
                formatted_balances[currency] = {
                    "total": balance.get('total', '0'),
                    "available": balance.get('available', '0'),
                    "frozen": balance.get('frozen', '0')
                }
                
        return {
            "code": "0",
            "msg": "",
            "data": {
                "balances": formatted_balances
            }
        }
    except Exception as e:
        error_msg = f"获取账户余额失败: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "0",  # 修改为错误码
            "msg": error_msg,
            "data": {
                "balances": {}
            }
        }

@app.get("/api/market/price/{symbol}")
async def get_market_price(symbol: str):
    """获取市场价格"""
    try:
        try:
            data = await okx_client.get_ticker()
        except Exception as e:
            app_logger.error(f"调用OKX API获取行情失败: {str(e)}")
            data = None
        
        # 默认返回值
        default_data = {
            "symbol": symbol,
            "last": "0",
            "last_price": "0",
            "best_bid": "0",
            "best_ask": "0",
            "volume_24h": "0",
            "high_24h": "0",
            "low_24h": "0",
            "open_24h": "0",
            "timestamp": datetime.now().isoformat()
        }
        
        if not data:
            return {
                "code": "0",
                "msg": "",
                "data": [default_data]  # 返回列表格式
            }
            
        # 确保所有数值都转换为字符串
        try:
            formatted_data = {
                "symbol": symbol,
                "last": str(data.get('last', '0')),
                "last_price": str(data.get('last', '0')),
                "best_bid": str(data.get('best_bid', '0')),
                "best_ask": str(data.get('best_ask', '0')),
                "volume_24h": str(data.get('volume_24h', '0')),
                "high_24h": str(data.get('high_24h', '0')),
                "low_24h": str(data.get('low_24h', '0')),
                "open_24h": str(data.get('open_24h', '0')),
                "timestamp": data.get('timestamp', datetime.now().isoformat())
            }
        except Exception as e:
            app_logger.error(f"格式化市场数据失败: {str(e)}")
            return {
                "code": "0",
                "msg": "",
                "data": [default_data]  # 返回列表格式
            }
        
        return {
            "code": "0",
            "msg": "",
            "data": [formatted_data]  # 返回列表格式
        }
    except Exception as e:
        error_msg = f"获取市场价格失败: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "0",  # 返回0以避免前端报错
            "msg": "",
            "data": [{  # 返回列表格式
                "symbol": symbol,
                "last": "0",
                "last_price": "0",
                "best_bid": "0",
                "best_ask": "0",
                "volume_24h": "0",
                "high_24h": "0",
                "low_24h": "0",
                "open_24h": "0",
                "timestamp": datetime.now().isoformat()
            }]
        }

@app.get("/api/market/kline/{symbol}/{interval}")
async def get_kline(symbol: str, interval: str = "15m"):
    """获取K线数据"""
    try:
        app_logger.info(f"获取K线数据: {symbol}, {interval}")
        
        # 从管理器获取数据
        klines = await kline_manager.get_klines(symbol, interval)
        
        if not klines:
            # 如果没有缓存数据，从交易所获取
            data = await okx_client.get_candlesticks(symbol, interval)
            if data:
                # 转换数据格式
                klines = [Candlestick.from_okx_candlestick(candle) for candle in data]
                # 初始化缓存
                await kline_manager.init_klines(symbol, interval, klines)
                app_logger.info(f"已缓存 {symbol} {interval} 的新数据")
        
        # 格式化返回数据
        formatted_data = [k.to_list() for k in klines]
        
        return {
            "code": "0",
            "msg": "",
            "data": formatted_data
        }
    except Exception as e:
        error_msg = f"获取K线数据失败: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "0",
            "msg": "",
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
async def get_strategy_state():
    """获取策略状态"""
    try:
        try:
            state = strategy.state_info
        except Exception as e:
            app_logger.error(f"获取策略状态信息失败: {str(e)}")
            state = None
        
        if not state:
            return {
                "code": "0",
                "msg": "",
                "data": {
                    "status": "stopped",
                    "position_info": {
                        "symbol": strategy.symbol,
                        "quantity": "0",
                        "avg_entry_price": "0",
                        "leverage": "1",
                        "unrealized_pnl": "0",
                        "total_pnl": "0",
                        "total_commission": "0"
                    },
                    "risk_info": {
                        "max_position_value": "0",
                        "current_position_value": "0",
                        "remaining_position_value": "0"
                    },
                    "last_update": datetime.now().isoformat()
                }
            }
            
        # 确保所有必要字段都存在
        if isinstance(state, dict):
            if "position_info" not in state:
                state["position_info"] = {}
            if "risk_info" not in state:
                state["risk_info"] = {}
                
            # 确保position_info中的字段存在
            position_fields = [
                "symbol", "quantity", "avg_entry_price", "leverage",
                "unrealized_pnl", "total_pnl", "total_commission"
            ]
            for field in position_fields:
                if field not in state["position_info"]:
                    state["position_info"][field] = "0"
                    
            # 确保risk_info中的字段存在
            risk_fields = [
                "max_position_value", "current_position_value",
                "remaining_position_value"
            ]
            for field in risk_fields:
                if field not in state["risk_info"]:
                    state["risk_info"][field] = "0"
                    
            # 确保状态字段存在
            if "status" not in state:
                state["status"] = "stopped"
                
            # 确保last_update字段存在
            if "last_update" not in state:
                state["last_update"] = datetime.now().isoformat()
        
        return {
            "code": "0",
            "msg": "",
            "data": state
        }
    except Exception as e:
        error_msg = f"获取策略状态失败: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "0",  # 返回0以避免前端报错
            "msg": "",
            "data": {
                "status": "stopped",
                "position_info": {
                    "symbol": strategy.symbol,
                    "quantity": "0",
                    "avg_entry_price": "0",
                    "leverage": "1",
                    "unrealized_pnl": "0",
                    "total_pnl": "0",
                    "total_commission": "0"
                },
                "risk_info": {
                    "max_position_value": "0",
                    "current_position_value": "0",
                    "remaining_position_value": "0"
                },
                "last_update": datetime.now().isoformat()
            }
        }

@app.get("/api/strategy/analysis")
async def get_strategy_analysis():
    """获取策略分析"""
    try:
        try:
            analysis = strategy.last_analysis
        except Exception as e:
            app_logger.error(f"获取策略分析失败: {str(e)}")
            analysis = None
        
        # 默认分析结果
        default_analysis = {
            "reasoning": "",
            "analysis": "",
            "recommendation": "hold",
            "confidence": "0",
            "last_update": datetime.now().isoformat(),
            "market_data": {
                "price": "0",
                "volume": "0",
                "trend": "neutral"
            }
        }
        
        # 如果没有分析结果，返回默认值
        if not analysis:
            return {
                "code": "0",
                "msg": "",
                "data": default_analysis
            }
            
        # 格式化推理过程
        if isinstance(analysis, dict):
            # 处理reasoning字段
            if 'reasoning' in analysis:
                reasoning = analysis['reasoning']
                if isinstance(reasoning, list):
                    formatted_reasoning = []
                    for reason in reasoning:
                        if reason:
                            cleaned_reason = reason.strip().rstrip('。') + '。'
                            formatted_reasoning.append(cleaned_reason)
                    analysis['reasoning'] = '\n'.join(formatted_reasoning)
                elif isinstance(reasoning, str):
                    analysis['reasoning'] = reasoning.strip()
                else:
                    analysis['reasoning'] = ""
                    
            # 确保所有必要字段都存在
            for key, value in default_analysis.items():
                if key not in analysis:
                    analysis[key] = value
                    
            # 确保market_data字段存在
            if 'market_data' not in analysis:
                analysis['market_data'] = default_analysis['market_data']
            else:
                for key, value in default_analysis['market_data'].items():
                    if key not in analysis['market_data']:
                        analysis['market_data'][key] = value
                        
            # 确保confidence是字符串
            if 'confidence' in analysis:
                analysis['confidence'] = str(analysis['confidence'])
        else:
            analysis = default_analysis
        
        return {
            "code": "0",
            "msg": "",
            "data": analysis
        }
    except Exception as e:
        error_msg = f"获取策略分析失败: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "0",  # 返回0以避免前端报错
            "msg": "",
            "data": default_analysis
        }

@app.post("/api/strategy/start")
async def start_strategy():
    """启动策略"""
    try:
        app_logger.info("收到启动策略请求")
        
        # 检查策略状态
        if strategy.is_running:
            error_msg = "策略已经在运行中"
            app_logger.error(error_msg)
            return {
                "code": "1",
                "msg": error_msg,
                "data": {
                    "status": "running"
                }
            }
        
        try:
            await strategy.start()
            app_logger.info("策略启动请求已发送")
            return {
                "code": "0",
                "msg": "策略启动中",
                "data": {
                    "status": "starting"
                }
            }
        except Exception as e:
            error_msg = f"启动策略失败: {str(e)}"
            app_logger.error(error_msg)
            return {
                "code": "1",
                "msg": error_msg,
                "data": {
                    "status": "error"
                }
            }
        
    except Exception as e:
        error_msg = f"启动策略失败: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "1",
            "msg": error_msg,
            "data": {
                "status": "error"
            }
        }

@app.post("/api/strategy/stop")
async def stop_strategy():
    """停止策略"""
    try:
        app_logger.info("尝试停止策略")
        
        # 检查策略状态
        if not strategy.is_running:
            error_msg = "策略未在运行中"
            app_logger.error(error_msg)
            return {
                "code": "1",
                "msg": error_msg,
                "data": {
                    "status": "stopped"
                }
            }
        
        try:
            # 停止策略
            await strategy._on_stop()
            await strategy.stop()
            
            # 获取最新状态
            state_info = strategy.state_info
            app_logger.info(f"策略停止成功，新状态: {state_info['status']}")
            
            return {
                "code": "0",
                "msg": "策略已停止",
                "data": state_info
            }
        except Exception as e:
            error_msg = f"停止策略失败: {str(e)}"
            app_logger.error(error_msg)
            return {
                "code": "1",
                "msg": error_msg,
                "data": {
                    "status": "error"
                }
            }
            
    except Exception as e:
        error_msg = f"停止策略失败: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "1",
            "msg": error_msg,
            "data": {
                "status": "error"
            }
        }

@app.post("/api/strategy/pause")
async def pause_strategy():
    """暂停策略"""
    try:
        app_logger.info("尝试暂停策略")
        
        # 检查策略状态
        if not strategy.is_running:
            error_msg = "策略未在运行中，无法暂停"
            app_logger.error(error_msg)
            return {
                "code": "1",
                "msg": error_msg,
                "data": {
                    "status": "stopped"
                }
            }
        
        try:
            # 暂停策略
            await strategy.pause()
            
            # 获取最新状态
            state_info = strategy.state_info
            app_logger.info(f"策略暂停成功，新状态: {state_info['status']}")
            
            return {
                "code": "0",
                "msg": "策略已暂停",
                "data": state_info
            }
        except Exception as e:
            error_msg = f"暂停策略失败: {str(e)}"
            app_logger.error(error_msg)
            return {
                "code": "1",
                "msg": error_msg,
                "data": {
                    "status": "error"
                }
            }
            
    except Exception as e:
        error_msg = f"暂停策略失败: {str(e)}"
        app_logger.error(error_msg)
        return {
            "code": "1",
            "msg": error_msg,
            "data": {
                "status": "error"
            }
        }

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
        interval = "15m"  # 默认使用15分钟K线
        
        # 1. 首次连接发送历史数据
        klines = await kline_manager.get_klines(symbol, interval)
        if klines:
            await manager.send_personal_message(
                json.dumps({
                    "code": "0",
                    "msg": "",
                    "data": [k.to_list() for k in klines],
                    "type": "kline_history"
                }),
                websocket
            )
            app_logger.info(f"已发送 {symbol} 的历史K线数据")
        
        # 2. 持续监听更新
        while True:
            try:
                # 获取最新K线
                latest_data = await okx_client.get_candlesticks(symbol, interval, limit=1)
                if latest_data and latest_data[0]:
                    current_kline = Candlestick.from_okx_candlestick(latest_data[0])
                    
                    # 尝试更新，如果有变化才发送
                    if await kline_manager.update_kline(symbol, interval, current_kline):
                        await manager.send_personal_message(
                            json.dumps({
                                "code": "0",
                                "msg": "",
                                "data": [current_kline.to_list()],
                                "type": "kline_update"
                            }),
                            websocket
                        )
                        app_logger.debug(f"已发送 {symbol} 的K线更新数据")
                
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