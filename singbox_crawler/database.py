import sqlite3
import os
from datetime import datetime, timedelta
from queue import Queue, Empty, Full
from contextlib import contextmanager
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
        self.db_path = db_path or config.get('database.db_path', 'crawler_data.db')
        self.max_connections = config.get('database.max_connections', 20)
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
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    added_at TEXT,
                    last_crawl_time TEXT,
                    status TEXT DEFAULT 'active',
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0
                )
            ''')
            # 2. 爬取到的资源表 (Resources)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    protocol TEXT,
                    source_id INTEGER,
                    crawl_time TEXT,
                    FOREIGN KEY (source_id) REFERENCES sources (id)
                )
            ''')
            conn.commit()

    def _migrate(self):
        """全面的数据库迁移逻辑"""
        with self._get_conn() as conn:
            cursor = conn.execute("PRAGMA table_info(sources)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 定义所有应有的列及其类型
            required_columns = {
                'added_at': 'TEXT',
                'last_crawl_time': 'TEXT',
                'status': "TEXT DEFAULT 'active'",
                'success_count': 'INTEGER DEFAULT 0',
                'fail_count': 'INTEGER DEFAULT 0'
            }
            
            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    print(f"Migrating database: adding column {col_name} to sources table")
                    conn.execute(f"ALTER TABLE sources ADD COLUMN {col_name} {col_def}")
            
            conn.commit()

    def add_source(self, url):
        if not url or not url.startswith('http'): return
        with self._get_conn() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO sources (url, added_at) 
                VALUES (?, ?)
            ''', (url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

    def get_source_id(self, url):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT id FROM sources WHERE url = ?", (url,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_sources_to_crawl(self, interval_hours=6):
        """获取活跃且超过间隔时间未爬取的源"""
        time_threshold = (datetime.now() - timedelta(hours=interval_hours)).strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            cursor = conn.execute('''
                SELECT url FROM sources 
                WHERE status = 'active' 
                AND (last_crawl_time IS NULL OR last_crawl_time < ?)
            ''', (time_threshold,))
            return [row[0] for row in cursor.fetchall()]

    def mark_source_deleted(self, url):
        with self._get_conn() as conn:
            conn.execute("UPDATE sources SET status = 'deleted' WHERE url = ?", (url,))
            conn.commit()

    def update_source_stats(self, url, is_success):
        with self._get_conn() as conn:
            if is_success:
                conn.execute('''
                    UPDATE sources 
                    SET success_count = success_count + 1, 
                        last_crawl_time = ?, 
                        fail_count = 0 
                    WHERE url = ?
                ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), url))
            else:
                conn.execute('UPDATE sources SET fail_count = fail_count + 1 WHERE url = ?', (url,))
            conn.commit()

    def save_resource(self, item, source_url):
        source_id = self.get_source_id(source_url)
        with self._get_conn() as conn:
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO resources (url, protocol, source_id, crawl_time)
                    VALUES (?, ?, ?, ?)
                ''', (item['url'], item['protocol'], source_id, item['crawl_time']))
                conn.commit()
                return True
            except:
                return False
