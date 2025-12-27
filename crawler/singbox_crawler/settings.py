from .config import config

BOT_NAME = "singbox_crawler"

SPIDER_MODULES = ["singbox_crawler.spiders"]
NEWSPIDER_MODULE = "singbox_crawler.spiders"

# --- 7x24 稳定性与资源优化 ---
ROBOTSTXT_OBEY = False
LOG_LEVEL = getattr(config, "logging_log_level", "INFO")
# LOG_FILE = getattr(config, 'logging_log_file_path', 'logs/crawler.log')
# We log to stdout so NSSM can handle rotation and file management
LOG_FILE = None


# 开启持久化支持，允许暂停后继续（NSSM 重启后能接着爬）
JOBDIR = "crawls/universal-1"

# 爬取限制
DEPTH_LIMIT = 3
# CONCURRENT_REQUESTS = getattr(config, 'crawler_max_concurrent_requests', 5)
# Rate limiting effectively via Download Delay
# 5 requests per second -> 0.2s delay
DOWNLOAD_DELAY = getattr(config, "crawler_download_delay", 0.2)
CONCURRENT_REQUESTS_PER_DOMAIN = getattr(config, "crawler_max_concurrent_requests", 5)
CONCURRENT_REQUESTS_PER_IP = getattr(config, "crawler_max_concurrent_requests", 5)

# 自动限速
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# 重试机制
RETRY_ENABLED = True
RETRY_TIMES = getattr(config, "crawler_retry_times", 2)
# Exponential backoff
RETRY_BACKOFF_FACTOR = getattr(config, "crawler_retry_backoff_factor", 2)

# Memory Limit (Scrapy built-in)
# Scrapy will close the spider if memory usage exceeds this.
# NSSM or our launcher will then restart it.
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = getattr(config, "service_memory_limit_mb", 1024)
MEMUSAGE_NOTIFY_MAIL = (
    [getattr(config, "logging_email_to_addrs", "")]
    if getattr(config, "logging_email_to_addrs", "")
    else []
)

# Email Settings
MAIL_FROM = getattr(config, "logging_email_from_addr")
MAIL_HOST = getattr(config, "logging_email_smtp_server")
MAIL_PORT = getattr(config, "logging_email_smtp_port")
MAIL_USER = getattr(config, "logging_email_username")
MAIL_PASS = getattr(config, "logging_email_password")
MAIL_TLS = True
MAIL_SSL = False

# --- 智能代理配置 ---
# 用户本地代理地址
PROXY_URL = "http://127.0.0.1:12334"

DOWNLOADER_MIDDLEWARES = {
    # 启用scrapy-user-agents中间件，用于生成随机User-Agent
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
    # 移除默认的User-Agent中间件
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    # 暂时禁用代理中间件，因为代理连接不稳定
    # "singbox_crawler.middlewares.SmartProxyMiddleware": 100,
    # "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": 110,
}

# 配置scrapy-user-agents
# 使用现代浏览器的User-Agent
RANDOM_UA_TYPE = "random"
RANDOM_UA_MIN_CRAWL_DELAY = 0.1
RANDOM_UA_MAX_CRAWL_DELAY = 0.5

# 管道
ITEM_PIPELINES = {
    "singbox_crawler.pipelines.SingboxCrawlerPipeline": 300,
}

# Extensions
EXTENSIONS = {
    "scrapy.extensions.memusage.MemoryUsage": 50,
    "scrapy.extensions.corestats.CoreStats": 500,
    "scrapy.extensions.closespider.CloseSpider": 500,
}

# 爬虫运行时间限制（秒）
CLOSESPIDER_TIMEOUT = 300  # 5分钟
CLOSESPIDER_ITEMCOUNT = None  # 不限制爬取的项目数
CLOSESPIDER_PAGECOUNT = None  # 不限制爬取的页面数
CLOSESPIDER_ERRORCOUNT = None  # 不限制错误数

# 默认请求头
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}
