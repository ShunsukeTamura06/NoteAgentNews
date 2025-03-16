# models/news_data.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class NewsSource:
    """ニュースソースモデル"""

    url: str
    title: str
    content: str
    published_at: Optional[datetime] = None


@dataclass
class NewsData:
    """ニュースデータモデル"""

    id: Optional[int] = None
    topic_id: Optional[int] = None
    sources: List[NewsSource] = None
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.sources is None:
            self.sources = []
