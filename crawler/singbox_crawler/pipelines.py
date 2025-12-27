from datetime import datetime

from .database import Database
from .models import ResourceItem


class SingboxCrawlerPipeline:
    def __init__(self):
        self.db = Database()

    def process_item(self, item, spider):
        # 使用pydantic模型验证数据
        try:
            validated_item = ResourceItem(**dict(item))
            item_dict = validated_item.model_dump()
            spider.logger.info(f"Validated item: {item_dict}")
        except Exception as e:
            spider.logger.error(f"Item validation failed: {e}, item: {dict(item)}")
            return item

        # 存储资源，并关联来源 URL
        source_url = item.get("source")
        success = self.db.save_resource(dict(item), source_url)

        # 只要找到了资源，就说明这个源是有效的
        if success:
            self.db.update_source_stats(source_url, is_success=True)

        return item
