import scrapy
import re
import pybase64
from datetime import datetime
from ..items import SingboxResourceItem
from ..database import Database

class UniversalSpider(scrapy.Spider):
    name = "universal"
    
    # 初始内置种子，仅在数据库为空时导入
    INITIAL_SOURCES = [
        'https://raw.githubusercontent.com/freefq/free/master/v2',
        'https://raw.githubusercontent.com/Pawdroid/Free-nodes/main/node.txt',
        'https://t.me/s/SSRSUB',
        'https://t.me/s/v2ray_free_conf',
        'https://www.google.com/search?q="vmess://" "vless://" "ss://"'
    ]

    PROTOCOL_PATTERNS = {
        'ss': r'ss://[a-zA-Z0-9+/=]+(?:#[^ \n\r\t<>"]+)?',
        'vmess': r'vmess://[a-zA-Z0-9+/=]+',
        'vless': r'vless://[a-f0-9-]+@[^ \n\r\t<>"]+',
        'trojan': r'trojan://[a-zA-Z0-9]+@[^ \n\r\t<>"]+',
        'tuic': r'tuic://[a-f0-9-]+:[^ \n\r\t<>"]+',
        'hysteria2': r'(?:hysteria2|hy2)://[a-zA-Z0-9-]+@[^ \n\r\t<>"]+',
        'hysteria': r'hysteria://[^ \n\r\t<>"]+',
        'wireguard': r'wireguard://[^ \n\r\t<>"]+',
        'ssh': r'ssh://[^ \n\r\t<>"]+',
        'clash_sub': r'https?://[^ \n\r\t<>"]+\.(?:yaml|yml)(?:\?[^ \n\r\t<>"]+)?',
        'singbox_sub': r'https?://[^ \n\r\t<>"]+\.json(?:\?[^ \n\r\t<>"]+)?'
    }

    def __init__(self, *args, **kwargs):
        super(UniversalSpider, self).__init__(*args, **kwargs)
        self.db = Database()
        # 确保初始种子入库
        for url in self.INITIAL_SOURCES:
            self.db.add_source(url)

    async def start(self):
        """Scrapy 2.13+ 推荐的异步启动方法"""
        # 仅爬取 6 小时内未爬取的活跃源，节省资源
        urls = self.db.get_sources_to_crawl(interval_hours=6)
        if not urls:
            self.logger.info("No sources to crawl at this moment.")
            return

        for url in urls:
            yield scrapy.Request(
                url=url, 
                callback=self.parse, 
                errback=self.handle_error,
                meta={'handle_httpstatus_list': [404], 'is_start_url': True}
            )

    def parse(self, response):
        # 1. 专门处理 404 (页面不存在)
        if response.status == 404:
            self.logger.warning(f"404 Not Found, removing source: {response.url}")
            self.db.mark_source_deleted(response.url)
            return

        # 2. 标记爬取成功
        self.db.update_source_stats(response.url, is_success=True)

        # 3. 提取内容
        raw_content = response.text
        
        # 提取资源
        yield from self.extract_from_text(raw_content, response.url)

        # 尝试 Base64 解码提取
        try:
            clean_content = "".join(raw_content.split())
            if len(clean_content) > 20 and all(c in 'A-Za-z0-9+/=' for c in clean_content[:20]):
                decoded = pybase64.b64decode(clean_content).decode('utf-8', errors='ignore')
                yield from self.extract_from_text(decoded, response.url)
        except:
            pass

        # 4. 发现新链接（自动扩充种子库）
        if response.headers.get('Content-Type', b'').startswith(b'text/html'):
            links = response.css('a::attr(href)').getall()
            for link in links:
                absolute_url = response.urljoin(link)
                if absolute_url.startswith('http') and any(d in absolute_url for d in ['github.com', 't.me', 'blogspot', 'v2ray', 'free']):
                    if not any(ext in absolute_url for ext in ['.png', '.jpg', '.css', '.js']):
                        self.db.add_source(absolute_url)

    def extract_from_text(self, text, source_url):
        for proto, pattern in self.PROTOCOL_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                item = SingboxResourceItem()
                item['url'] = match.strip()
                item['protocol'] = proto
                item['source'] = source_url
                item['crawl_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                yield item

    def handle_error(self, failure):
        url = failure.request.url
        self.logger.error(f"Network error on {url}: {str(failure.value)}")
        self.db.update_source_stats(url, is_success=False)
