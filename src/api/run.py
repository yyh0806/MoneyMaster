import uvicorn
from loguru import logger
import sys
from pathlib import Path

# 添加项目根目录到Python路径
root_path = str(Path(__file__).parent.parent.parent)
sys.path.append(root_path)

if __name__ == "__main__":
    logger.info("启动API服务...")
    uvicorn.run("src.api.app:app", 
                host="0.0.0.0", 
                port=8000, 
                reload=True,
                reload_dirs=["src"]) 