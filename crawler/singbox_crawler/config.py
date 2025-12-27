import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 加载环境变量
load_dotenv()


class Config(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_nested_delimiter="_")

    # Service Configuration
    service_restart_delay_sec: int = 30
    service_max_restart_attempts: int = 5
    service_cpu_limit_percent: int = 50
    service_memory_limit_mb: int = 1024
    service_gc_interval_hours: int = 2

    # Crawler Configuration
    crawler_max_concurrent_requests: int = 5
    crawler_download_delay: float = 0.2
    crawler_retry_times: int = 2
    crawler_retry_backoff_factor: float = 2
    crawler_request_timeout: int = 30

    # Database Configuration
    database_max_connections: int = 20
    database_db_path: str = "test.db"

    # Logging Configuration
    logging_log_level: str = "INFO"
    logging_log_file_path: str = "crawler/logs/crawler.log"
    logging_max_file_size_mb: int = 100
    logging_backup_count: int = 7
    logging_email_alert_enabled: bool = True

    # Email Configuration
    logging_email_smtp_server: str
    logging_email_smtp_port: int
    logging_email_username: str
    logging_email_password: str
    logging_email_from_addr: str
    logging_email_to_addrs: str

    # Monitoring Configuration
    monitoring_p99_response_limit_sec: float = 2


# 全局配置实例
config = Config()
