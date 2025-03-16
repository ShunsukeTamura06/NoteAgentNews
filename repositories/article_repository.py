# repositories/article_repository.py
from datetime import datetime
from typing import List, Optional

from models.article import Article
from utils.db_utils import DatabaseManager


class ArticleRepository:
    """記事のデータベース操作を行うリポジトリクラス"""

    def __init__(self, db_manager: DatabaseManager):
        """
        リポジトリの初期化

        Args:
            db_manager: データベース接続管理クラス
        """
        self.db_manager = db_manager

    def create(self, article: Article) -> Article:
        """
        記事を作成

        Args:
            article: 作成する記事

        Returns:
            Article: 作成された記事（IDが設定される）
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            "INSERT INTO articles (topic_id, news_data_id, title, content, improved_content, status, created_at, updated_at, published_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                article.topic_id,
                article.news_data_id,
                article.title,
                article.content,
                article.improved_content,
                article.status,
                now,
                now,
                article.published_at.isoformat() if article.published_at else None,
            ),
        )

        conn.commit()
        article.id = cursor.lastrowid
        article.created_at = datetime.fromisoformat(now)
        article.updated_at = datetime.fromisoformat(now)

        return article

    def get_by_id(self, article_id: int) -> Optional[Article]:
        """
        IDによる記事の取得

        Args:
            article_id: 取得する記事のID

        Returns:
            Optional[Article]: 見つかった記事、または None
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return Article(
            id=row["id"],
            topic_id=row["topic_id"],
            news_data_id=row["news_data_id"],
            title=row["title"],
            content=row["content"],
            improved_content=row["improved_content"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            published_at=datetime.fromisoformat(row["published_at"])
            if row["published_at"]
            else None,
        )

    def get_by_topic_id(self, topic_id: int) -> List[Article]:
        """
        トピックIDによる記事の取得

        Args:
            topic_id: 取得する記事のトピックID

        Returns:
            List[Article]: 見つかった記事のリスト
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM articles WHERE topic_id = ? ORDER BY created_at DESC",
            (topic_id,),
        )
        rows = cursor.fetchall()

        return [
            Article(
                id=row["id"],
                topic_id=row["topic_id"],
                news_data_id=row["news_data_id"],
                title=row["title"],
                content=row["content"],
                improved_content=row["improved_content"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                published_at=datetime.fromisoformat(row["published_at"])
                if row["published_at"]
                else None,
            )
            for row in rows
        ]

    def update(self, article: Article) -> Article:
        """
        記事の更新

        Args:
            article: 更新する記事

        Returns:
            Article: 更新された記事
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        article.updated_at = datetime.fromisoformat(now)

        cursor.execute(
            "UPDATE articles SET title = ?, content = ?, improved_content = ?, status = ?, updated_at = ?, published_at = ? WHERE id = ?",
            (
                article.title,
                article.content,
                article.improved_content,
                article.status,
                now,
                article.published_at.isoformat() if article.published_at else None,
                article.id,
            ),
        )

        conn.commit()
        return article

    def delete(self, article_id: int) -> bool:
        """
        記事の削除

        Args:
            article_id: 削除する記事のID

        Returns:
            bool: 削除が成功したかどうか
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        conn.commit()

        return cursor.rowcount > 0
