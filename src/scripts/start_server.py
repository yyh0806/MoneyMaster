import os
import uvicorn
from loguru import logger
from src.scripts.init_db import main as init_db

def main():
    """启动服务"""
    # 确保在项目根目录
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # 初始化数据库
    logger.info("初始化数据库...")
    init_db()
    
    # 启动服务
    logger.info("启动API服务...")
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main() 