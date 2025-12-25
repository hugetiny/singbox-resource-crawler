from .config import config

BOT_NAME = 'singbox_crawler'

SPIDER_MODULES = ['singbox_crawler.spiders']
NEWSPIDER_MODULE = 'singbox_crawler.spiders'

# --- 7x24 稳定性与资源优化 ---
ROBOTSTXT_OBEY = False
LOG_LEVEL = config.get('logging.log_level', 'INFO')
# LOG_FILE = config.get('logging.log_file_path', 'logs/crawler.log')
# We log to stdout so NSSM can handle rotation and file management
LOG_FILE = None


# 开启持久化支持，允许暂停后继续（NSSM 重启后能接着爬）
JOBDIR = 'crawls/universal-1'

# 爬取限制
DEPTH_LIMIT = 3
# CONCURRENT_REQUESTS = config.get('crawler.max_concurrent_requests', 5)
# Rate limiting effectively via Download Delay
# 5 requests per second -> 0.2s delay
DOWNLOAD_DELAY = config.get('crawler.download_delay', 0.2)
CONCURRENT_REQUESTS_PER_DOMAIN = config.get('crawler.max_concurrent_requests', 5)
CONCURRENT_REQUESTS_PER_IP = config.get('crawler.max_concurrent_requests', 5)

# 自动限速
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# 重试机制
RETRY_ENABLED = True
RETRY_TIMES = config.get('crawler.retry_times', 2)
# Exponential backoff
RETRY_BACKOFF_FACTOR = config.get('crawler.retry_backoff_factor', 2)

# Memory Limit (Scrapy built-in)
# Scrapy will close the spider if memory usage exceeds this. 
# NSSM or our launcher will then restart it.
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = config.get('service.memory_limit_mb', 1024)
MEMUSAGE_NOTIFY_MAIL = config.get('logging.email_config.to_addrs', [])

# Email Settings
MAIL_FROM = config.get('logging.email_config.from_addr')
MAIL_HOST = config.get('logging.email_config.smtp_server')
MAIL_PORT = config.get('logging.email_config.smtp_port')
MAIL_USER = config.get('logging.email_config.username')
MAIL_PASS = config.get('logging.email_config.password')
MAIL_TLS = True
MAIL_SSL = False

# --- 智能代理配置 ---
# 用户本地代理地址
PROXY_URL = 'http://127.0.0.1:12334'

DOWNLOADER_MIDDLEWARES = {
    # 启用我们自定义的智能代理中间件
    'singbox_crawler.middlewares.SmartProxyMiddleware': 100,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
}

# 管道
ITEM_PIPELINES = {
    'singbox_crawler.pipelines.SingboxCrawlerPipeline': 300,
}

# Extensions
EXTENSIONS = {
    'scrapy.extensions.memusage.MemoryUsage': 50,
    'scrapy.extensions.corestats.CoreStats': 500,
}

# 默认请求头
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
}
