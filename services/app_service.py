# services/app_service.py
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.article import Article
from models.news_data import NewsData
from models.topic import Topic
from repositories.article_repository import ArticleRepository
from repositories.news_repository import NewsRepository
from repositories.topic_repository import TopicRepository
from services.article_service import ArticleService
from services.note_poster_service import NotePosterService
from services.search_service import SearchService


class AppService:
    """アプリケーション全体の処理を統括するサービス"""

    def __init__(
        self,
        topic_repo: TopicRepository,
        news_repo: NewsRepository,
        article_repo: ArticleRepository,
        search_service: SearchService,
        article_service: ArticleService,
        note_poster_service: Optional[NotePosterService] = None,
    ):
        """
        アプリケーションサービスの初期化

        Args:
            topic_repo: トピックリポジトリ
            news_repo: ニュースリポジトリ
            article_repo: 記事リポジトリ
            search_service: 検索サービス
            article_service: 記事サービス
            note_poster_service: Note投稿サービス（任意）
        """
        self.topic_repo = topic_repo
        self.news_repo = news_repo
        self.article_repo = article_repo
        self.search_service = search_service
        self.article_service = article_service
        self.note_poster_service = note_poster_service

    def create_topic(self, title: str, description: Optional[str] = None) -> Topic:
        """
        トピックを作成

        Args:
            title: トピックのタイトル
            description: トピックの説明（任意）

        Returns:
            Topic: 作成されたトピック
        """
        topic = Topic(title=title, description=description)
        return self.topic_repo.create(topic)

    def get_topics(self) -> List[Topic]:
        """
        全トピックを取得

        Returns:
            List[Topic]: トピックのリスト
        """
        return self.topic_repo.get_all()

    def collect_news_for_topic(self, topic_id: int) -> NewsData:
        """
        トピックに関するニュースを収集

        Args:
            topic_id: トピックID

        Returns:
            NewsData: 収集されたニュースデータ
        """
        topic = self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise ValueError(f"トピックID {topic_id} が見つかりません")

        news_data = self.search_service.search_topic(topic)
        return self.news_repo.create(news_data)

    def create_article_for_topic(self, topic_id: int) -> Article:
        """
        トピックの記事を作成

        Args:
            topic_id: トピックID

        Returns:
            Article: 作成された記事
        """
        topic = self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise ValueError(f"トピックID {topic_id} が見つかりません")

        # 既存のニュースデータを取得
        news_data = self.news_repo.get_by_topic_id(topic_id)
        if not news_data:
            # ニュースデータがなければ収集
            news_data = self.collect_news_for_topic(topic_id)

        # 記事を作成
        article = self.article_service.create_article_from_news(topic, news_data)
        return self.article_repo.create(article)

    def improve_article(self, article_id: int) -> Article:
        """
        記事を改善

        Args:
            article_id: 記事ID

        Returns:
            Article: 改善された記事
        """
        article = self.article_repo.get_by_id(article_id)
        if not article:
            raise ValueError(f"記事ID {article_id} が見つかりません")

        improved_article = self.article_service.improve_article(article)
        return self.article_repo.update(improved_article)

    def post_article_to_note(self, article_id: int) -> bool:
        """
        記事をNoteに投稿

        Args:
            article_id: 記事ID

        Returns:
            bool: 投稿が成功したかどうか
        """
        if not self.note_poster_service:
            raise ValueError("Note投稿サービスが設定されていません")

        article = self.article_repo.get_by_id(article_id)
        if not article:
            raise ValueError(f"記事ID {article_id} が見つかりません")

        success = self.note_poster_service.post_article(article)
        if success:
            article.status = "published"
            article.published_at = datetime.now()
            self.article_repo.update(article)

        return success

    def run_full_process(
        self,
        topic_title: str,
        topic_description: Optional[str] = None,
        post_to_note: bool = False,
    ) -> Dict[str, Any]:
        """
        トピック作成から記事投稿までの全プロセスを実行

        Args:
            topic_title: トピックのタイトル
            topic_description: トピックの説明（任意）
            post_to_note: Noteに投稿するかどうか

        Returns:
            Dict: プロセスの結果情報
        """
        result = {
            "success": True,
            "messages": [],
            "topic": None,
            "news_data": None,
            "article": None,
            "improved_article": None,
            "note_posted": False,
        }

        try:
            # 1. トピック作成
            topic = self.create_topic(topic_title, topic_description)
            result["topic"] = topic
            result["messages"].append(f"トピック「{topic.title}」を作成しました")

            # 2. ニュース収集
            news_data = self.collect_news_for_topic(topic.id)
            result["news_data"] = news_data
            result["messages"].append(
                f"トピック「{topic.title}」の情報を収集しました（情報源: {len(news_data.sources)}件）"
            )

            # 3. 記事作成
            article = self.create_article_for_topic(topic.id)
            result["article"] = article
            result["messages"].append(f"記事「{article.title}」を作成しました")

            # 4. 記事改善
            improved_article = self.improve_article(article.id)
            result["improved_article"] = improved_article
            result["messages"].append(f"記事「{improved_article.title}」を改善しました")

            # 5. Noteに投稿（オプション）
            if post_to_note and self.note_poster_service:
                note_posted = self.post_article_to_note(improved_article.id)
                result["note_posted"] = note_posted
                if note_posted:
                    result["messages"].append(
                        f"記事「{improved_article.title}」をNoteに投稿しました"
                    )
                else:
                    result["messages"].append("Noteへの投稿に失敗しました")

        except Exception as e:
            result["success"] = False
            result["messages"].append(f"エラー: {str(e)}")
            logging.error(
                f"プロセス実行中にエラーが発生しました: {str(e)}", exc_info=True
            )

        return result
