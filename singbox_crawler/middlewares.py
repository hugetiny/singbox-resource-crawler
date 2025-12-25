import logging
from scrapy.exceptions import NotConfigured

class SmartProxyMiddleware:
    """
    智能代理中间件：
    1. 自动识别请求是否需要代理（基于域名）。
    2. 如果代理请求失败，自动切换到直连模式。
    3. 如果直连请求失败，自动尝试挂载代理模式。
    """
    def __init__(self, proxy_url):
        self.proxy_url = proxy_url
        self.blocked_domains = ['github.com', 't.me', 'google.com', 'raw.githubusercontent.com', 'githubusercontent.com']
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        proxy_url = crawler.settings.get('PROXY_URL')
        if not proxy_url:
            raise NotConfigured
        return cls(proxy_url)

    def process_request(self, request, spider):
        # 如果已经标记了重试模式，则跳过初始判断
        if 'proxy_tried' in request.meta:
            return

        # 初始策略：特定域名走代理
        if any(domain in request.url for domain in self.blocked_domains):
            request.meta['proxy'] = self.proxy_url
            request.meta['using_proxy'] = True
        else:
            request.meta['using_proxy'] = False

    def process_exception(self, request, exception, spider):
        """
        当发生网络连接错误时触发逻辑切换
        """
        if request.meta.get('proxy_tried'):
            # 如果已经尝试过切换模式仍然失败，则彻底放弃，交给重试机制或记录失败
            return None

        request.meta['proxy_tried'] = True
        
        if request.meta.get('using_proxy'):
            self.logger.warning(f"Proxy unstable for {request.url}, switching to DIRECT...")
            if 'proxy' in request.meta:
                del request.meta['proxy']
            request.meta['using_proxy'] = False
        else:
            self.logger.warning(f"Direct connection failed for {request.url}, switching to PROXY...")
            request.meta['proxy'] = self.proxy_url
            request.meta['using_proxy'] = True
        
        # 返回 request 对象表示立即重新调度该请求
        request.dont_filter = True
        return request
