import os
import sys
from loguru import logger
import uvicorn

# 配置日志
logger.remove()  # 移除默认的日志处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[strategy]}</cyan> | <level>{message}</level>",
    level="INFO"
)

# 创建带有默认strategy字段的日志记录器
server_logger = logger.bind(strategy="Server")

def main():
    """启动服务"""
    # 确保在项目根目录
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # 启动API服务
    server_logger.info("启动API服务...")
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="error"  # 将uvicorn的日志级别设置为error
    )

if __name__ == "__main__":
    main() 