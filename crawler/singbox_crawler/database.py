import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from queue import Empty, Full, Queue

from tenacity import retry, stop_after_attempt, wait_exponential

from .config import config


class Database:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path=None):
        if self._initialized:
            return
        # 获取项目根目录（从database.py向上3层：singbox_crawler -> crawler -> singbox_resource_crawler）
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # 使用项目根目录下的数据库文件
        self.db_path = db_path or os.path.join(project_root, getattr(config, "database_db_path", "data.db"))
        self.max_connections = getattr(config, "database_max_connections", 20)
        self.pool = Queue(maxsize=self.max_connections)
        self._init_db()
        self._migrate()
        self._initialized = True

    @contextmanager
    def _get_conn(self):
        conn = None
        try:
            # Try to get a connection from the pool
            try:
                conn = self.pool.get(block=False)
            except Empty:
                # If pool is empty, create a new one if we haven't reached the limit
                # In a real pool we would track count, but here we just create one
                # if the queue isn't providing one, and we rely on queue size for "idle" connections.
                # Since we can't easily track total active connections without a counter,
                # we'll implement a simple semaphore-like behavior with the Queue.
                # But for SQLite, let's just create a new connection if needed and not enforce strict
                # "blocking" if max is reached because we don't want to deadlock single thread.
                # However, to strictly follow "pool" logic:
                conn = sqlite3.connect(self.db_path)

            yield conn
        finally:
            if conn:
                # Return connection to pool if not full, else close it
                try:
                    self.pool.put_nowait(conn)
                except Full:
                    conn.close()

    def _init_db(self):
        with self._get_conn() as conn:
            # 1. 资源来源表 (Sources/Start URLs)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    added_at TEXT,
                    last_crawl_time TEXT,
                    status TEXT DEFAULT 'active',
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_status_code INTEGER,
                    last_checked TEXT
                )
            """
            )
            # 2. 爬取到的资源表 (Resources)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    protocol TEXT,
                    source TEXT,
                    crawl_time TEXT,
                    status TEXT DEFAULT 'pending',
                    last_checked TEXT,
                    server_region TEXT,
                    singbox_verified INTEGER DEFAULT 0,
                    location_verified INTEGER DEFAULT 0
                )
            """
            )
            # 3. 暂存订阅链接表 (Pending Subscriptions)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    protocol TEXT,
                    source TEXT,
                    crawl_time TEXT,
                    last_attempt_time TEXT,
                    attempt_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending'
                )
            """
            )
            conn.commit()

    def _migrate(self):
        """全面的数据库迁移逻辑"""
        with self._get_conn() as conn:
            # 迁移 sources 表
            cursor = conn.execute("PRAGMA table_info(sources)")
            columns = [column[1] for column in cursor.fetchall()]

            required_columns = {
                "added_at": "TEXT",
                "last_crawl_time": "TEXT",
                "status": "TEXT DEFAULT 'active'",
                "success_count": "INTEGER DEFAULT 0",
                "fail_count": "INTEGER DEFAULT 0",
                "last_status_code": "INTEGER",
                "last_checked": "TEXT",
            }

            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    print(
                        f"Migrating database: adding column {col_name} to sources table"
                    )
                    conn.execute(f"ALTER TABLE sources ADD COLUMN {col_name} {col_def}")

            # 迁移 resources 表
            cursor = conn.execute("PRAGMA table_info(resources)")
            resource_columns = [column[1] for column in cursor.fetchall()]

            # 确保 url 字段有 UNIQUE 约束
            try:
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_resources_url ON resources(url)"
                )
                print("Added unique index to resources.url")
            except Exception as e:
                print(f"Index already exists or error: {e}")

            # 添加 missing 的列
            resource_required_columns = {
                "source": "TEXT",
                "protocol": "TEXT",
                "crawl_time": "TEXT",
            }

            for col_name, col_def in resource_required_columns.items():
                if col_name not in resource_columns:
                    print(
                        f"Migrating database: adding column {col_name} to resources table"
                    )
                    conn.execute(
                        f"ALTER TABLE resources ADD COLUMN {col_name} {col_def}"
                    )

            # 确保 pending_subscriptions 表存在
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    protocol TEXT,
                    source TEXT,
                    crawl_time TEXT,
                    last_attempt_time TEXT,
                    attempt_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending'
                )
            """
            )

            conn.commit()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=10)
    )
    def add_source(self, url):
        if not url or not url.startswith("http"):
            return
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO sources (url, added_at)
                VALUES (?, ?)
            """,
                (url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()

    def get_source_id(self, url):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT id FROM sources WHERE url = ?", (url,))
            row = cursor.fetchone()
            return row[0] if row else None

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=10)
    )
    def get_sources_to_crawl(self, interval_hours=6):
        """获取活跃且超过间隔时间未爬取的源"""
        time_threshold = (datetime.now() - timedelta(hours=interval_hours)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT url FROM sources
                WHERE status = 'active'
                AND (last_crawl_time IS NULL OR last_crawl_time < ?)
            """,
                (time_threshold,),
            )
            return [row[0] for row in cursor.fetchall()]

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=10)
    )
    def mark_source_deleted(self, url):
        with self._get_conn() as conn:
            conn.execute("UPDATE sources SET status = 'deleted' WHERE url = ?", (url,))
            conn.commit()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=10)
    )
    def update_source_stats(self, url, is_success):
        with self._get_conn() as conn:
            if is_success:
                conn.execute(
                    """
                    UPDATE sources
                    SET success_count = success_count + 1,
                        last_crawl_time = ?,
                        fail_count = 0
                    WHERE url = ?
                """,
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), url),
                )
            else:
                conn.execute(
                    "UPDATE sources SET fail_count = fail_count + 1 WHERE url = ?",
                    (url,),
                )
            conn.commit()

    def _test_subscription_access(self, url):
        """测试订阅链接的可访问性"""
        import requests

        try:
            # 设置超时时间，避免长时间阻塞
            response = requests.head(url, timeout=10)
            # 返回200-399之间的状态码表示链接可访问
            return response.status_code >= 200 and response.status_code < 400
        except requests.RequestException as e:
            print(f"Subscription access test failed for {url}: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=10)
    )
    def save_resource(self, item, source_url):
        try:
            url = item["url"]
            protocol = item["protocol"]
            crawl_time = item["crawl_time"]

            with self._get_conn() as conn:
                # 检查是否已经存在
                cursor = conn.execute("SELECT id FROM resources WHERE url = ?", (url,))
                if cursor.fetchone():
                    # 已存在，跳过
                    return True

                # 检查是否已经在暂存表中
                cursor = conn.execute(
                    "SELECT id FROM pending_subscriptions WHERE url = ?", (url,)
                )
                if cursor.fetchone():
                    # 已存在于暂存表，跳过
                    return True

                # 对于订阅链接，测试可访问性
                if protocol in ["clash_sub", "singbox_sub"]:
                    is_accessible = self._test_subscription_access(url)
                    if is_accessible:
                        # 可访问，保存到resources表
                        conn.execute(
                            """
                            INSERT INTO resources (url, protocol, source, crawl_time)
                            VALUES (?, ?, ?, ?)
                        """,
                            (url, protocol, source_url, crawl_time),
                        )
                    else:
                        # 不可访问，保存到暂存表
                        conn.execute(
                            """
                            INSERT INTO pending_subscriptions (url, protocol, source, crawl_time, last_attempt_time, attempt_count)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (url, protocol, source_url, crawl_time, crawl_time, 1),
                        )
                else:
                    # 非订阅链接，直接保存到resources表
                    conn.execute(
                        """
                        INSERT INTO resources (url, protocol, source, crawl_time)
                        VALUES (?, ?, ?, ?)
                        """,
                        (url, protocol, source_url, crawl_time),
                    )

                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving resource: {e}")
            print(f"Item: {item}")
            print(f"Source URL: {source_url}")
            print(f"Database path: {self.db_path}")
            return False

    def process_pending_subscriptions(self):
        """处理暂存表中的订阅链接，重新测试可访问性"""
        with self._get_conn() as conn:
            # 获取所有状态为pending的订阅链接
            cursor = conn.execute(
                """
                SELECT id, url, protocol, source, crawl_time FROM pending_subscriptions
                WHERE status = 'pending'
            """
            )
            pending_subs = cursor.fetchall()

            for sub_id, url, protocol, source, crawl_time in pending_subs:
                try:
                    # 测试可访问性
                    is_accessible = self._test_subscription_access(url)
                    if is_accessible:
                        # 可访问，移到resources表
                        conn.execute(
                            """
                            INSERT INTO resources (url, protocol, source, crawl_time)
                            VALUES (?, ?, ?, ?)
                        """,
                            (url, protocol, source, crawl_time),
                        )
                        # 从暂存表中删除
                        conn.execute(
                            "DELETE FROM pending_subscriptions WHERE id = ?", (sub_id,)
                        )
                        print(f"Moved subscription from pending to resources: {url}")
                    else:
                        # 不可访问，更新尝试次数和时间
                        conn.execute(
                            """
                            UPDATE pending_subscriptions
                            SET last_attempt_time = ?, attempt_count = attempt_count + 1
                            WHERE id = ?
                        """,
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sub_id),
                        )
                        print(f"Updated pending subscription attempt: {url}")
                except Exception as e:
                    print(f"Error processing pending subscription {url}: {e}")

            conn.commit()
