# utils/db_utils.py
import logging
import sqlite3
from typing import TypeVar

T = TypeVar("T")


class DatabaseManager:
    """SQLiteデータベース管理クラス"""

    def __init__(self, db_path: str = "news_reports.db"):
        """
        データベース管理クラスの初期化

        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self.conn = None
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """
        SQLite接続を取得

        Returns:
            sqlite3.Connection: データベース接続
        """
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close_connection(self) -> None:
        """データベース接続を閉じる"""
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def initialize_database(self) -> None:
        """データベースのテーブルを初期化"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # トピックテーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        # ニュースデータテーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            sources TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (topic_id) REFERENCES topics (id)
        )
        """)

        # 記事テーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            news_data_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            improved_content TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            published_at TEXT,
            FOREIGN KEY (topic_id) REFERENCES topics (id),
            FOREIGN KEY (news_data_id) REFERENCES news_data (id)
        )
        """)

        conn.commit()
        logging.info("データベースの初期化が完了しました")
