# models/topic.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Topic:
    """トピックモデル"""

    id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
