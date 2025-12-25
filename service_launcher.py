import os
import sys
import time
import subprocess
import logging
import logging.handlers
import smtplib
import psutil
import gc
from email.mime.text import MIMEText
from datetime import datetime
from singbox_crawler.config import config

# Configuration
LOG_FILE = config.get('logging.log_file_path', 'logs/service.log')
MAX_LOG_BYTES = config.get('logging.max_file_size_mb', 100) * 1024 * 1024
BACKUP_COUNT = config.get('logging.backup_count', 7)
CPU_LIMIT = config.get('service.cpu_limit_percent', 50)
MEMORY_LIMIT_MB = config.get('service.memory_limit_mb', 1024)
GC_INTERVAL = config.get('service.gc_interval_hours', 2) * 3600

# Email Config
EMAIL_ENABLED = config.get('logging.email_alert_enabled', False)
SMTP_SERVER = config.get('logging.email_config.smtp_server')
SMTP_PORT = config.get('logging.email_config.smtp_port')
USERNAME = config.get('logging.email_config.username')
PASSWORD = config.get('logging.email_config.password')
FROM_ADDR = config.get('logging.email_config.from_addr')
TO_ADDRS = config.get('logging.email_config.to_addrs')

def setup_logging():
    # We rely on NSSM to capture stdout/stderr and handle log rotation.
    # This ensures all logs (launcher + scrapy) are in one place and rotated correctly.
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    logger = logging.getLogger('ServiceLauncher')
    logger.setLevel(logging.INFO)
    
    # Log to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

def send_email_alert(subject, body):
    if not EMAIL_ENABLED or not TO_ADDRS:
        return
    
    msg = MIMEText(body)
    msg['Subject'] = f"[Crawler Alert] {subject}"
    msg['From'] = FROM_ADDR
    msg['To'] = ", ".join(TO_ADDRS)
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(USERNAME, PASSWORD)
            server.sendmail(FROM_ADDR, TO_ADDRS, msg.as_string())
        logger.info("Email alert sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")

def monitor_process(process):
    """Monitor the subprocess for memory and CPU usage."""
    try:
        proc = psutil.Process(process.pid)
        
        # Check Memory
        mem_info = proc.memory_info()
        mem_usage_mb = mem_info.rss / 1024 / 1024
        if mem_usage_mb > MEMORY_LIMIT_MB:
            logger.warning(f"Process memory usage {mem_usage_mb:.2f}MB exceeded limit {MEMORY_LIMIT_MB}MB. Restarting...")
            process.terminate()
            return False

        # Check CPU (Just logging for now, as hard limiting CPU in Python is tricky without OS tools)
        # NSSM can set priority, but we can't easily throttle CPU % from here without suspending/resuming.
        # We rely on Scrapy settings (download delay) to keep CPU low.
        cpu_percent = proc.cpu_percent(interval=0.1)
        if cpu_percent > CPU_LIMIT:
            logger.warning(f"High CPU usage detected: {cpu_percent}%")

    except psutil.NoSuchProcess:
        return False
    return True

def run_crawler():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    cmd = [sys.executable, "-m", "scrapy.cmdline", "crawl", "universal"]
    
    start_time = time.time()
    
    logger.info("Starting crawler process...")
    process = subprocess.Popen(cmd)
    
    while process.poll() is None:
        if not monitor_process(process):
            # Process was killed by monitor
            break
        time.sleep(5)
        
    return_code = process.returncode
    duration = time.time() - start_time
    
    if return_code == 0:
        logger.info(f"Crawler finished successfully in {duration:.2f}s")
    else:
        logger.error(f"Crawler exited with error code {return_code}")
        # Send alert if it wasn't a manual termination (which would be -15 or 1)
        if return_code != 0 and return_code is not None:
             send_email_alert("Crawler Failed", f"Crawler process exited with code {return_code}")

def main():
    logger.info("Singbox Crawler Service Started.")
    
    last_gc_time = time.time()
    
    while True:
        try:
            # 1. Run the crawler
            run_crawler()
            
            # 2. GC Handling
            if time.time() - last_gc_time > GC_INTERVAL:
                logger.info("Performing mandatory GC...")
                gc.collect()
                last_gc_time = time.time()
            
            # 3. Sleep before next run
            # The user asked for "7x24", but the spider runs periodically.
            # If the spider finishes (no more URLs or done), we wait.
            # 5 minutes sleep
            logger.info("Sleeping for 5 minutes...")
            time.sleep(300)
            
        except KeyboardInterrupt:
            logger.info("Service stopping by user request.")
            break
        except Exception as e:
            logger.error(f"Critical Service Error: {e}", exc_info=True)
            send_email_alert("Service Crashed", str(e))
            # Wait a bit before retrying the loop to avoid rapid restart loops
            time.sleep(30)

if __name__ == "__main__":
    main()
