# repositories/topic_repository.py
from datetime import datetime
from typing import List, Optional

from models.topic import Topic
from utils.db_utils import DatabaseManager


class TopicRepository:
    """トピックのデータベース操作を行うリポジトリクラス"""

    def __init__(self, db_manager: DatabaseManager):
        """
        リポジトリの初期化

        Args:
            db_manager: データベース接続管理クラス
        """
        self.db_manager = db_manager

    def create(self, topic: Topic) -> Topic:
        """
        トピックを作成

        Args:
            topic: 作成するトピック

        Returns:
            Topic: 作成されたトピック（IDが設定される）
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            "INSERT INTO topics (title, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (topic.title, topic.description, now, now),
        )

        conn.commit()
        topic.id = cursor.lastrowid
        topic.created_at = datetime.fromisoformat(now)
        topic.updated_at = datetime.fromisoformat(now)

        return topic

    def get_by_id(self, topic_id: int) -> Optional[Topic]:
        """
        IDによるトピックの取得

        Args:
            topic_id: 取得するトピックのID

        Returns:
            Optional[Topic]: 見つかったトピック、または None
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return Topic(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_all(self) -> List[Topic]:
        """
        全トピックの取得

        Returns:
            List[Topic]: トピックのリスト
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM topics ORDER BY created_at DESC")
        rows = cursor.fetchall()

        return [
            Topic(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def update(self, topic: Topic) -> Topic:
        """
        トピックの更新

        Args:
            topic: 更新するトピック

        Returns:
            Topic: 更新されたトピック
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        topic.updated_at = datetime.fromisoformat(now)

        cursor.execute(
            "UPDATE topics SET title = ?, description = ?, updated_at = ? WHERE id = ?",
            (topic.title, topic.description, now, topic.id),
        )

        conn.commit()
        return topic

    def delete(self, topic_id: int) -> bool:
        """
        トピックの削除

        Args:
            topic_id: 削除するトピックのID

        Returns:
            bool: 削除が成功したかどうか
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        conn.commit()

        return cursor.rowcount > 0
