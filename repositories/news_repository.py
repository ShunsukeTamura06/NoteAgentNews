# repositories/news_repository.py
import json
from datetime import datetime
from typing import Optional

from models.news_data import NewsData, NewsSource
from utils.db_utils import DatabaseManager


class NewsRepository:
    """ニュースデータのデータベース操作を行うリポジトリクラス"""

    def __init__(self, db_manager: DatabaseManager):
        """
        リポジトリの初期化

        Args:
            db_manager: データベース接続管理クラス
        """
        self.db_manager = db_manager

    def create(self, news_data: NewsData) -> NewsData:
        """
        ニュースデータを作成

        Args:
            news_data: 作成するニュースデータ

        Returns:
            NewsData: 作成されたニュースデータ（IDが設定される）
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        sources_json = json.dumps(
            [
                {
                    "url": source.url,
                    "title": source.title,
                    "content": source.content,
                    "published_at": source.published_at.isoformat()
                    if source.published_at
                    else None,
                }
                for source in news_data.sources
            ],
            ensure_ascii=False,
        )

        cursor.execute(
            "INSERT INTO news_data (topic_id, sources, created_at) VALUES (?, ?, ?)",
            (news_data.topic_id, sources_json, now),
        )

        conn.commit()
        news_data.id = cursor.lastrowid
        news_data.created_at = datetime.fromisoformat(now)

        return news_data

    def get_by_id(self, news_id: int) -> Optional[NewsData]:
        """
        IDによるニュースデータの取得

        Args:
            news_id: 取得するニュースデータのID

        Returns:
            Optional[NewsData]: 見つかったニュースデータ、または None
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM news_data WHERE id = ?", (news_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        sources_data = json.loads(row["sources"])
        sources = [
            NewsSource(
                url=src["url"],
                title=src["title"],
                content=src["content"],
                published_at=datetime.fromisoformat(src["published_at"])
                if src["published_at"]
                else None,
            )
            for src in sources_data
        ]

        return NewsData(
            id=row["id"],
            topic_id=row["topic_id"],
            sources=sources,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_by_topic_id(self, topic_id: int) -> Optional[NewsData]:
        """
        トピックIDによるニュースデータの取得

        Args:
            topic_id: 取得するニュースデータのトピックID

        Returns:
            Optional[NewsData]: 見つかったニュースデータ、または None
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM news_data WHERE topic_id = ? ORDER BY created_at DESC",
            (topic_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        sources_data = json.loads(row["sources"])
        sources = [
            NewsSource(
                url=src["url"],
                title=src["title"],
                content=src["content"],
                published_at=datetime.fromisoformat(src["published_at"])
                if src["published_at"]
                else None,
            )
            for src in sources_data
        ]

        return NewsData(
            id=row["id"],
            topic_id=row["topic_id"],
            sources=sources,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def delete(self, news_id: int) -> bool:
        """
        ニュースデータの削除

        Args:
            news_id: 削除するニュースデータのID

        Returns:
            bool: 削除が成功したかどうか
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM news_data WHERE id = ?", (news_id,))
        conn.commit()

        return cursor.rowcount > 0
