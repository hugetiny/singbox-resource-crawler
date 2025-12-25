import sys
import os

def check_env():
    print("--- Environment Validation ---")
    try:
        import scrapy
        print("[OK] Scrapy is installed.")
    except ImportError:
        print("[ERROR] Scrapy is NOT installed. Run: pip install scrapy")

    try:
        import pybase64
        print("[OK] pybase64 is installed.")
    except ImportError:
        print("[ERROR] pybase64 is NOT installed. Run: pip install pybase64")

    # Check project structure
    files_to_check = [
        'scrapy.cfg',
        'singbox_crawler/database.py',
        'singbox_crawler/spiders/universal_spider.py',
        'run_crawler.py'
    ]
    
    for f in files_to_check:
        if os.path.exists(f):
            print(f"[OK] Found {f}")
        else:
            print(f"[MISSING] {f}")

    print("\n--- Testing Database ---")
    try:
        from singbox_crawler.database import Database
        db = Database('test_val.db')
        db.add_source('https://example.com')
        sources = db.get_active_sources()
        if 'https://example.com' in sources:
            print("[OK] Database CRUD works.")
        os.remove('test_val.db')
    except Exception as e:
        print(f"[ERROR] Database test failed: {e}")

if __name__ == "__main__":
    check_env()
