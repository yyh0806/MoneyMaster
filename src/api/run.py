import uvicorn
from loguru import logger

if __name__ == "__main__":
    logger.info("启动API服务...")
    uvicorn.run("app:app", 
                host="0.0.0.0", 
                port=8000, 
                reload=True,
                reload_dirs=["src"],
                app_dir="src/api") 