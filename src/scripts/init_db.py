from src.trading.core.models import Base, init_db

def main():
    """初始化数据库"""
    db_session = init_db("sqlite:///trading.db")
    print("数据库初始化完成！")

if __name__ == "__main__":
    main() 