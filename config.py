# config.py
import json
import logging
import os
from typing import Any, Dict

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

    # アプリケーション設定
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # 設定ファイルパス
    SETTINGS_FILE = "app_settings.json"

    @classmethod
    def validate(cls):
        """
        設定の検証

        Raises:
            ValueError: 必須設定が不足している場合
        """
        required_env_vars = ["OPENAI_API_KEY"]

        missing_vars = [var for var in required_env_vars if not getattr(cls, var)]

        if missing_vars:
            raise ValueError(f"環境変数が設定されていません: {', '.join(missing_vars)}")

        if cls.NOTE_EMAIL and not cls.NOTE_PASSWORD:
            raise ValueError(
                "NOTE_EMAIL が設定されている場合は NOTE_PASSWORD も設定する必要があります"
            )

    @classmethod
    def load_from_file(cls) -> Dict[str, Any]:
        """
        設定ファイルから設定を読み込む

        Returns:
            Dict[str, Any]: 読み込んだ設定
        """
        if not os.path.exists(cls.SETTINGS_FILE):
            return {}

        try:
            with open(cls.SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                return settings
        except Exception as e:
            logging.error(f"設定ファイルの読み込みに失敗しました: {e}")
            return {}

    @classmethod
    def save_to_file(cls, settings: Dict[str, Any]) -> bool:
        """
        設定をファイルに保存

        Args:
            settings: 保存する設定

        Returns:
            bool: 保存が成功したか
        """
        try:
            with open(cls.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"設定ファイルの保存に失敗しました: {e}")
            return False

    @classmethod
    def update(cls, settings: Dict[str, Any]) -> bool:
        """
        設定を更新

        Args:
            settings: 更新する設定

        Returns:
            bool: 更新が成功したか
        """
        # 環境変数を更新
        for key, value in settings.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
                os.environ[key] = str(value) if value is not None else ""

        # 設定ファイルに保存
        return cls.save_to_file(settings)

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """
        全ての設定を取得

        Returns:
            Dict[str, Any]: 全設定
        """
        return {
            "DB_PATH": cls.DB_PATH,
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
            "NOTE_EMAIL": cls.NOTE_EMAIL,
            "NOTE_PASSWORD": cls.NOTE_PASSWORD,
            "LOG_LEVEL": cls.LOG_LEVEL,
        }
