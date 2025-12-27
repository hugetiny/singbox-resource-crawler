# Singbox Resource Crawler

## Project Overview

This project is a 7x24h crawler service that collects, validates, and manages Singbox proxy resources from various sources. It uses Scrapy framework to crawl proxy links, validates them using Singbox test tools, and stores them in a SQLite database.

## Project Structure

```
├── crawler/                      # Scrapy crawler implementation
│   ├── scrapy.cfg               # Scrapy configuration
│   └── singbox_crawler/        # Main crawler package
│       ├── __init__.py
│       ├── config.py              # Configuration using pydantic-settings
│       ├── database.py             # Database operations with retry mechanism
│       ├── items.py               # Scrapy item definitions
│       ├── middlewares.py          # Custom middlewares for proxies
│       ├── models.py              # Pydantic models for data validation
│       ├── pipelines.py            # Item processing pipelines
│       ├── settings.py             # Scrapy settings
│       └── spiders/               # Spider implementations
│           ├── __init__.py
│           └── universal_spider.py  # Main universal spider
├── scripts/                       # Utility scripts for maintenance and testing
│   ├── config.py              # Configuration module
│   └── update_server_region_fixed.py  # Update server region with all APIs
├── singbox_test/                 # Singbox testing tools
│   ├── download_singbox.py    # Download singbox binary
│   ├── sing-box.exe           # Singbox binary (Windows)
│   └── test_resources.py      # Test resources with singbox
├── tmp/                          # Temporary files directory
├── utils/                        # Utility functions
│   └── ip_verification/          # IP geolocation verification
│       └── ip_geo.py
├── windows/                      # Windows service installation
│   ├── install_service.bat
│   └── uninstall_service.bat
├── .env.example                  # Example environment variables
├── .gitignore                    # Git ignore rules
├── README.md                      # This file
├── requirements.txt               # Project dependencies
├── service_launcher.py            # Service launcher script
├── data.db                      # Production database (7x24h crawler)
└── test.db                      # Test database (for testing)
```

## Database Files

- **data.db** - Production database (used for 7x24h crawler)
- **test.db** - Test database (used for testing and development)

Both databases are located in the project root directory and have identical structure.

## Resource Status

The `status` field in the `resources` table indicates the current state of each resource:

- **pending**: Resource has been crawled but not yet validated
- **parsing_failed**: Resource URL parsing failed (invalid format or encoding error)
- **location_failed**: Resource URL parsing succeeded but IP geolocation failed
- **verified**: Resource has been validated successfully by singbox and IP geolocation test passed

## Core Components

### 1. Crawler Module (crawler/singbox_crawler/)
- **config.py**: Configuration management using pydantic-settings and python-dotenv
- **database.py**: SQLite database operations with tenacity retry mechanism
- **universal_spider.py**: Main spider that crawls proxy resources from various sources
- **pipelines.py**: Processes and validates crawled items using pydantic models
- **middlewares.py**: Custom middlewares for proxy management
- **items.py**: Scrapy item definitions
- **models.py**: Pydantic models for data validation

### 2. Service Launcher (service_launcher.py)
- Manages crawler service lifecycle
- Implements CPU and memory monitoring
- Handles automatic restart on failure
- Sends email notifications for critical events

### 3. Database (data.db / test.db)
Stores:
- Proxy resources with their protocol, source, and validation status
- Source URLs for crawling
- Statistics about source reliability
- API test results (api_ipinfo, api_ipapi_co, api_ipwho, api_ipgeolocation)
- Server region information

### 4. IP Verification (utils/ip_verification/)
- Validates server regions using multiple IP geolocation APIs
- Tests connection to proxy servers
- Updates resource status based on verification results

### 5. Singbox Testing (singbox_test/)
- **test_resources.py**: Tests proxy resources using sing-box binary
- **download_singbox.py**: Downloads the latest sing-box binary

## Key Features

1. **7x24h Crawling**: Continuously crawls proxy resources 7 days a week, 24 hours a day
2. **Resource Validation**: Validates proxy resources using Singbox test tools
3. **IP Geolocation**: Determines server regions using multiple APIs (ipinfo, ipapi_co, ipwho, ipgeolocation)
4. **Reliability Tracking**: Tracks source reliability based on crawl success rate
5. **Automatic Restart**: Restarts service on failure
6. **Email Notifications**: Sends notifications for critical events
7. **Configuration Management**: Uses pydantic for type-safe configuration
8. **Random User-Agent**: Uses scrapy-user-agents for rotating User-Agents
9. **Retry Mechanism**: Uses tenacity for reliable database operations
10. **Smart Proxy**: Automatically switches between proxy and direct connection based on success rate

## Getting Started

### Prerequisites

- Python 3.13+
- Singbox test tools
- API keys for IP geolocation services

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Set API keys in scripts/config.py:
   ```python
   API_KEYS = {
       "ipinfo": "your_ipinfo_key",
       "ipgeolocation": "your_ipgeolocation_key",
   }
   ```

### Running Service

1. Start service:
   ```bash
   python service_launcher.py
   ```

2. Run crawler manually:
   ```bash
   cd crawler && scrapy crawl universal
   ```

3. Update server regions:
   ```bash
   python scripts/update_server_region_fixed.py
   ```

4. Test resources with singbox:
   ```bash
   python singbox_test/test_resources.py
   ```

## Configuration

The project uses environment variables for configuration. Key variables include:

### Service Configuration
- `SERVICE_RESTART_DELAY_SEC`: Delay between service restarts (default: 30)
- `SERVICE_MAX_RESTART_ATTEMPTS`: Maximum restart attempts (default: 5)
- `SERVICE_CPU_LIMIT_PERCENT`: CPU usage limit (default: 50)
- `SERVICE_MEMORY_LIMIT_MB`: Memory usage limit (default: 1024)
- `SERVICE_GC_INTERVAL_HOURS`: Garbage collection interval (default: 2)

### Crawler Configuration
- `CRAWLER_MAX_CONCURRENT_REQUESTS`: Max concurrent requests (default: 5)
- `CRAWLER_DOWNLOAD_DELAY`: Download delay in seconds (default: 0.2)
- `CRAWLER_RETRY_TIMES`: Number of retry attempts (default: 2)
- `CRAWLER_RETRY_BACKOFF_FACTOR`: Retry backoff factor (default: 2.0)
- `CRAWLER_REQUEST_TIMEOUT`: Request timeout in seconds (default: 30)

### Database Configuration
- `DATABASE_MAX_CONNECTIONS`: Max database connections (default: 20)
- `DATABASE_DB_PATH`: Path to SQLite database file (default: data.db)
  - Use `test.db` for local development
  - Use `data.db` for production (7x24h crawler)

### Logging Configuration
- `LOGGING_LOG_LEVEL`: Log level (INFO, DEBUG, WARNING, ERROR)
- `LOGGING_LOG_FILE_PATH`: Log file path
- `LOGGING_MAX_FILE_SIZE_MB`: Max log file size (default: 100)
- `LOGGING_BACKUP_COUNT`: Number of log backups (default: 7)
- `LOGGING_EMAIL_ALERT_ENABLED`: Enable email alerts (default: true)

### Email Configuration
- `LOGGING_EMAIL_SMTP_SERVER`: SMTP server
- `LOGGING_EMAIL_SMTP_PORT`: SMTP port
- `LOGGING_EMAIL_USERNAME`: SMTP username
- `LOGGING_EMAIL_PASSWORD`: SMTP password
- `LOGGING_EMAIL_FROM_ADDR`: Sender email address
- `LOGGING_EMAIL_TO_ADDRS`: Recipient email address

### Monitoring Configuration
- `MONITORING_P99_RESPONSE_LIMIT_SEC`: P99 response limit (default: 2.0)

## Database Schema

### resources Table

```sql
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    protocol TEXT,
    source TEXT,
    crawl_time TEXT,
    status TEXT DEFAULT 'pending',
    last_checked TEXT,
    server_region TEXT,
    api_ipinfo INTEGER DEFAULT 0,
    api_ipapi_co INTEGER DEFAULT 0,
    api_ipwho INTEGER DEFAULT 0,
    api_ipgeolocation INTEGER DEFAULT 0,
    test_location TEXT
);
```

### sources Table

```sql
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
);
```

### pending_subscriptions Table

```sql
CREATE TABLE IF NOT EXISTS pending_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    protocol TEXT,
    source TEXT,
    crawl_time TEXT,
    last_attempt_time TEXT,
    attempt_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending'
);
```

## IP Geolocation APIs

The project uses multiple IP geolocation APIs to determine server regions:

1. **ipinfo.io**: Primary API (requires API key)
2. **ip-api.com**: Secondary API (free)
3. **ipgeolocation.io**: Tertiary API (requires API key)
4. **ipwho.is**: Fallback API (free)

All APIs are tested for each IP, and best result is selected based on completeness (country, city).

## Code Style

The project uses following tools for code style:
- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Code linting

## Maintenance Scripts

The `scripts/` directory contains maintenance scripts:

- `config.py`: Configuration module with API keys
- `update_server_region_fixed.py`: Updates server regions using all IP geolocation APIs

## License

This project is licensed under the MIT License.
