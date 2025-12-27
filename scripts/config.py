"""
通用配置模块
所有脚本都从这里读取配置，确保数据库路径一致
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量获取数据库路径，默认为data.db
DATABASE_DB_PATH = os.environ.get("DATABASE_DB_PATH", "data.db")

# 如果数据库路径不是绝对路径，则相对于项目根目录
if not os.path.isabs(DATABASE_DB_PATH):
    DATABASE_DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATABASE_DB_PATH
    )

# API配置
API_KEYS = {
    "ipinfo": "ce5247e9a4c234",
    "ipgeolocation": "88b0c372ab2f41cdbb418802838d33b8",
}

# 线程锁
from threading import Lock
cache_lock = Lock()
ip_cache = {}
