# Singbox Resource Crawler - Project Optimization Plan

## 1. Project Overview

The Singbox Resource Crawler is a web crawler built with Scrapy that collects singbox resources. The project has been successfully pushed to GitHub at [https://github.com/hugetiny/singbox-resource-crawler](https://github.com/hugetiny/singbox-resource-crawler).

## 2. Current Project Structure

```
singbox_resource_crawler/
├── crawls/                      # Crawler runtime data
├── singbox_crawler/             # Main project code
│   ├── spiders/                 # Scrapy spiders
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── database.py              # Database operations
│   ├── items.py                 # Data models
│   ├── middlewares.py           # Scrapy middlewares
│   ├── pipelines.py             # Data processing pipelines
│   └── settings.py              # Scrapy settings
├── config.json                  # Configuration file
├── crawler_data.db              # SQLite database
├── debug_test.py                # Debugging script
├── install_service.bat          # NSSM service installation script
├── requirements.txt             # Project dependencies
├── resources.jsonl              # Output data file
├── scrapy.cfg                   # Scrapy configuration
├── service_launcher.py          # Service launcher script
├── test_email.py                # Email testing script
├── uninstall_service.bat        # Service uninstallation script
└── validate_env.py              # Environment validation script
```

## 3. Optimization Plan

### 3.1 Code Quality Improvements

| Issue | Description | Solution | Priority |
|-------|-------------|----------|----------|
| **Code Organization** | Improve module structure and separation of concerns | Restructure code into logical modules, extract common functionality | High |
| **Documentation** | Add docstrings and README | Create comprehensive README with setup instructions | High |
| **Type Hints** | Add type hints for better IDE support | Add type annotations to all functions and methods | Medium |
| **Error Handling** | Enhance error handling and logging | Add more specific exception handling and detailed logging | High |

### 3.2 Performance Optimization

| Issue | Description | Solution | Priority |
|-------|-------------|----------|----------|
| **Concurrency** | Optimize Scrapy concurrency settings | Adjust CONCURRENT_REQUESTS, DOWNLOAD_DELAY based on target sites | High |
| **Memory Management** | Improve memory usage in service_launcher | Add more aggressive memory monitoring and garbage collection | Medium |
| **Database Optimization** | Optimize SQLite queries and indexing | Add appropriate indexes to database tables | Medium |

### 3.3 Feature Enhancements

| Feature | Description | Implementation Plan | Priority |
|---------|-------------|---------------------|----------|
| **Configuration Management** | Improve configuration handling | Implement a more robust config system with validation | High |
| **Multiple Spider Support** | Support for running multiple spiders | Enhance service launcher to manage multiple spiders | Medium |
| **Web Dashboard** | Add a web interface for monitoring | Create a simple web dashboard using Flask or FastAPI | Low |
| **API Integration** | Add API endpoints for data access | Implement REST API for querying collected resources | Low |

### 3.4 Reliability Improvements

| Issue | Description | Solution | Priority |
|-------|-------------|----------|----------|
| **Robustness** | Make crawler more resilient to website changes | Implement more robust selectors and fallback mechanisms | High |
| **Monitoring** | Enhance monitoring capabilities | Add more metrics and health checks | Medium |
| **Backup** | Add automatic data backup | Implement regular backup of database and output files | Medium |

## 4. Implementation Timeline

### Phase 1: Code Quality & Documentation (2 weeks)

| Task | Duration | Assigned To |
|------|----------|-------------|
| Restructure codebase | 3 days | Developer |
| Add comprehensive docstrings | 2 days | Developer |
| Create detailed README.md | 2 days | Developer |
| Add type hints | 3 days | Developer |
| Enhance error handling | 2 days | Developer |

### Phase 2: Performance & Reliability (2 weeks)

| Task | Duration | Assigned To |
|------|----------|-------------|
| Optimize Scrapy settings | 3 days | Developer |
| Improve memory management | 2 days | Developer |
| Optimize database queries | 2 days | Developer |
| Implement robust selectors | 3 days | Developer |
| Enhance monitoring | 2 days | Developer |

### Phase 3: Feature Enhancements (3 weeks)

| Task | Duration | Assigned To |
|------|----------|-------------|
| Improve configuration management | 3 days | Developer |
| Add multiple spider support | 4 days | Developer |
| Implement automatic backup | 2 days | Developer |
| Create web dashboard (basic) | 5 days | Developer |
| Add API endpoints | 3 days | Developer |

### Phase 4: Testing & Deployment (1 week)

| Task | Duration | Assigned To |
|------|----------|-------------|
| Unit testing | 3 days | Developer |
| Integration testing | 2 days | Developer |
| Performance testing | 2 days | Developer |

## 5. NSSM Manual Setup Instructions

### Prerequisites

- Windows 11 operating system
- Python 3.13 installed
- NSSM (Non-Sucking Service Manager) installed
- Administrator privileges

### Step-by-Step Setup

1. **Open Command Prompt as Administrator**
   - Press `Win + X` and select "Windows Terminal (Admin)"
   - Or search for "Command Prompt" in Start Menu, right-click and select "Run as administrator"

2. **Navigate to Project Directory**
   ```cmd
   cd C:\Users\huget\StudioProjects\myscrapy\singbox_resource_crawler
   ```

3. **Create Logs Directory**
   ```cmd
   mkdir -p logs
   ```

4. **Install NSSM Service**
   ```cmd
   nssm install SingboxCrawler "C:\Users\huget\AppData\Local\Programs\Python\Python313\python.exe" "C:\Users\huget\StudioProjects\myscrapy\singbox_resource_crawler\service_launcher.py"
   ```

5. **Configure Service Settings**
   ```cmd
   REM Set working directory
   nssm set SingboxCrawler AppDirectory "C:\Users\huget\StudioProjects\myscrapy\singbox_resource_crawler"

   REM Set service description
   nssm set SingboxCrawler Description "Singbox 7x24 Resource Crawler Service"

   REM Set startup type to automatic
   nssm set SingboxCrawler Start SERVICE_AUTO_START

   REM Configure logging
   nssm set SingboxCrawler AppStdout "C:\Users\huget\StudioProjects\myscrapy\singbox_resource_crawler\logs\service.log"
   nssm set SingboxCrawler AppStderr "C:\Users\huget\StudioProjects\myscrapy\singbox_resource_crawler\logs\service_error.log"
   nssm set SingboxCrawler AppRotateFiles 1
   nssm set SingboxCrawler AppRotateOnline 1
   nssm set SingboxCrawler AppRotateSeconds 86400
   nssm set SingboxCrawler AppRotateBytes 104857600

   REM Set restart policy
   nssm set SingboxCrawler AppThrottle 30000

   REM Set process priority
   nssm set SingboxCrawler AppPriority BELOW_NORMAL_PRIORITY_CLASS
   ```

6. **Start the Service**
   ```cmd
   nssm start SingboxCrawler
   ```

7. **Verify Service Status**
   ```cmd
   nssm status SingboxCrawler
   ```

### Service Management Commands

- **Start Service**: `nssm start SingboxCrawler`
- **Stop Service**: `nssm stop SingboxCrawler`
- **Restart Service**: `nssm restart SingboxCrawler`
- **View Service Status**: `nssm status SingboxCrawler`
- **Uninstall Service**: `nssm remove SingboxCrawler confirm`

## 6. Monitoring and Maintenance

### Log Monitoring

- Service logs: `logs/service.log`
- Error logs: `logs/service_error.log`

### Database Backup

```cmd
REM Create backup of database
copy crawler_data.db crawler_data_$(date +"%Y%m%d").bak
```

### Performance Monitoring

- Check CPU and memory usage using Task Manager
- Monitor log files for any errors or warnings
- Periodically check the output file `resources.jsonl` for new data

## 7. Future Roadmap

- [ ] Implement distributed crawling capabilities
- [ ] Add support for more resource types
- [ ] Implement machine learning for content classification
- [ ] Add support for Docker deployment
- [ ] Implement CI/CD pipeline for automated testing and deployment

## 8. Contact Information

- Project Repository: https://github.com/hugetiny/singbox-resource-crawler
- Maintainer: huget
- Email: huget@example.com
