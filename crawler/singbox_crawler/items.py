import scrapy


class SingboxResourceItem(scrapy.Item):
    url = scrapy.Field()  # 资源链接 (ss://, vmess:// 等)
    protocol = scrapy.Field()  # 协议类型
    source = scrapy.Field()  # 来源网页
    crawl_time = scrapy.Field()
