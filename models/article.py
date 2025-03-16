# models/article.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """記事モデル"""

    id: Optional[int] = None
    topic_id: int = None
    news_data_id: Optional[int] = None
    title: str = ""
    content: str = ""
    improved_content: Optional[str] = None
    status: str = "draft"  # draft, improved, published
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    published_at: Optional[datetime] = None
