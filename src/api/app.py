from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
from datetime import datetime
import asyncio

from src.trading.client import OKXClient
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

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/account/balance")
async def get_balance():
    """获取账户余额"""
    return okx_client.get_account_balance()

@app.get("/api/market/price/{symbol}")
async def get_market_price(symbol: str):
    """获取市场价格"""
    return okx_client.get_market_price(symbol)

@app.get("/api/market/kline/{symbol}")
async def get_kline(symbol: str, interval: str = "1m", limit: str = "100"):
    """获取K线数据"""
    return okx_client.get_kline(symbol, bar=interval, limit=limit)

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
            # 获取市场数据
            market_data = okx_client.get_market_price(symbol)
            # 广播给所有连接的客户端
            await websocket.send_text(json.dumps(market_data))
            # 等待1秒
            await asyncio.sleep(1)
    except Exception as e:
        manager.disconnect(websocket) 