# プロジェクト構成
# news_report_system/
# ├── main.py                # メインエントリーポイント
# ├── config.py              # 設定ファイル
# ├── models/                # データモデル
# ├── repositories/          # データアクセス層
# ├── services/              # ビジネスロジック
# ├── utils/                 # ユーティリティ
# └── ui/                    # ユーザーインターフェース


# main.py
import logging

from config import Config
from repositories.article_repository import ArticleRepository
from repositories.news_repository import NewsRepository
from repositories.topic_repository import TopicRepository
from services.app_service import AppService
from services.article_service import ArticleService
from services.note_poster_service import NotePosterService
from services.search_service import SearchService
from ui.app_ui import AppUI
from utils.db_utils import DatabaseManager


def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
    )


def init_services():
    """サービスの初期化"""
    # 設定の検証
    try:
        Config.validate()
    except ValueError as e:
        logging.error(f"設定エラー: {e}")
        exit(1)

    # データベース接続
    db_manager = DatabaseManager(Config.DB_PATH)

    # リポジトリ
    topic_repo = TopicRepository(db_manager)
    news_repo = NewsRepository(db_manager)
    article_repo = ArticleRepository(db_manager)

    # サービス
    search_service = SearchService(Config.OPENAI_API_KEY)
    article_service = ArticleService(Config.OPENAI_API_KEY)

    # Note投稿サービス（認証情報がある場合のみ）
    note_poster_service = None
    if Config.NOTE_EMAIL and Config.NOTE_PASSWORD:
        note_poster_service = NotePosterService(Config.NOTE_EMAIL, Config.NOTE_PASSWORD)

    # アプリケーションサービス
    app_service = AppService(
        topic_repo=topic_repo,
        news_repo=news_repo,
        article_repo=article_repo,
        search_service=search_service,
        article_service=article_service,
        note_poster_service=note_poster_service,
    )

    return app_service


def main():
    """メイン処理"""
    # ログ設定
    setup_logging()

    # サービス初期化
    app_service = init_services()

    # UIの初期化と起動
    app_ui = AppUI(app_service)
    app_ui.launch()


if __name__ == "__main__":
    main()
