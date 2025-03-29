# config.py
import os

from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()


class Config:
    """アプリケーション設定"""

    # データベース設定
    DB_PATH = os.getenv("DB_PATH", "news_reports.db")

    # OpenAI API設定
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Note設定
    NOTE_EMAIL = os.getenv("NOTE_EMAIL")
    NOTE_PASSWORD = os.getenv("NOTE_PASSWORD")

    # 検索サービス設定
    SEARCH_SERVICE_TYPE = os.getenv(
        "SEARCH_SERVICE_TYPE", "web"
    )  # "web" または "openai"
    SEARCH_ENGINE = os.getenv("SEARCH_ENGINE", "google")  # "google" または "duckduckgo"

    # アプリケーション設定
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """設定の検証"""
        required_env_vars = ["OPENAI_API_KEY"]

        missing_vars = [var for var in required_env_vars if not getattr(cls, var)]

        if missing_vars:
            raise ValueError(f"環境変数が設定されていません: {', '.join(missing_vars)}")

        if cls.NOTE_EMAIL and not cls.NOTE_PASSWORD:
            raise ValueError(
                "NOTE_EMAIL が設定されている場合は NOTE_PASSWORD も設定する必要があります"
            )

        # 検索サービス設定の検証
        if cls.SEARCH_SERVICE_TYPE not in ["web", "openai"]:
            raise ValueError(
                f"無効な SEARCH_SERVICE_TYPE: {cls.SEARCH_SERVICE_TYPE}。'web' または 'openai' を指定してください。"
            )

        if cls.SEARCH_ENGINE not in ["google", "duckduckgo"]:
            raise ValueError(
                f"無効な SEARCH_ENGINE: {cls.SEARCH_ENGINE}。'google' または 'duckduckgo' を指定してください。"
            )
