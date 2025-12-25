from .database import Database
from datetime import datetime

class SingboxCrawlerPipeline:
    def __init__(self):
        self.db = Database()

    def process_item(self, item, spider):
        # 存储资源，并关联来源 URL
        source_url = item.get('source')
        success = self.db.save_resource(item, source_url)
        
        # 只要找到了资源，就说明这个源是有效的
        if success:
            self.db.update_source_stats(source_url, is_success=True)
            
        return item
