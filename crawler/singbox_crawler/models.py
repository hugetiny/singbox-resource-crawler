from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ResourceItem(BaseModel):
    url: str = Field(..., description="资源链接")
    protocol: str = Field(..., description="协议类型")
    source: str = Field(..., description="来源网页")
    crawl_time: str = Field(..., description="爬取时间")

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "ss://base64string@example.com:8388",
                "protocol": "ss",
                "source": "https://example.com",
                "crawl_time": "2025-12-27 12:00:00",
            }
        }
    }
