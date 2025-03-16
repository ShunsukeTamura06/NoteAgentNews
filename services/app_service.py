# services/app_service.py
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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

        # ステップ実行状態の追跡
        self.step_status = {
            "topic_created": False,
            "news_collected": False,
            "article_created": False,
            "article_improved": False,
            "article_published": False,
        }

        # 現在のオブジェクトID
        self.current_topic_id = None
        self.current_news_id = None
        self.current_article_id = None

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
        created_topic = self.topic_repo.create(topic)

        # 実行状態を更新
        self.step_status["topic_created"] = True
        self.current_topic_id = created_topic.id
        self.step_status["news_collected"] = False
        self.step_status["article_created"] = False
        self.step_status["article_improved"] = False
        self.step_status["article_published"] = False

        return created_topic

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

        # 既存のニュースデータを取得
        existing_news = self.news_repo.get_by_topic_id(topic_id)
        if existing_news:
            logging.info(f"トピックID {topic_id} の既存ニュースデータを使用します")

            # 実行状態を更新
            self.step_status["topic_created"] = True
            self.current_topic_id = topic_id
            self.step_status["news_collected"] = True
            self.current_news_id = existing_news.id

            return existing_news

        # 新規にニュースデータを収集
        news_data = self.search_service.search_topic(topic)
        created_news = self.news_repo.create(news_data)

        # 実行状態を更新
        self.step_status["topic_created"] = True
        self.current_topic_id = topic_id
        self.step_status["news_collected"] = True
        self.current_news_id = created_news.id

        return created_news

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

        # ニュースデータの確認と収集
        news_data = self.news_repo.get_by_topic_id(topic_id)
        if not news_data:
            # ニュースデータがなければ収集
            news_data = self.collect_news_for_topic(topic_id)

        # 既存の記事を確認
        existing_articles = self.article_repo.get_by_topic_id(topic_id)
        if existing_articles:
            # 最新の記事を返す
            latest_article = existing_articles[0]

            # 実行状態を更新
            self.step_status["topic_created"] = True
            self.current_topic_id = topic_id
            self.step_status["news_collected"] = True
            self.current_news_id = news_data.id
            self.step_status["article_created"] = True
            self.current_article_id = latest_article.id
            self.step_status["article_improved"] = (
                latest_article.improved_content is not None
            )
            self.step_status["article_published"] = latest_article.status == "published"

            logging.info(
                f"トピックID {topic_id} の既存記事を使用します（ID: {latest_article.id}）"
            )
            return latest_article

        # 新規に記事を作成
        article = self.article_service.create_article_from_news(topic, news_data)
        created_article = self.article_repo.create(article)

        # 実行状態を更新
        self.step_status["topic_created"] = True
        self.current_topic_id = topic_id
        self.step_status["news_collected"] = True
        self.current_news_id = news_data.id
        self.step_status["article_created"] = True
        self.current_article_id = created_article.id

        return created_article

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

        # 記事が既に改善されている場合
        if article.improved_content:
            logging.info(f"記事ID {article_id} は既に改善されています")

            # 実行状態を更新
            self.step_status["topic_created"] = True
            self.current_topic_id = article.topic_id
            self.step_status["news_collected"] = True
            self.step_status["article_created"] = True
            self.current_article_id = article_id
            self.step_status["article_improved"] = True

            return article

        # 記事を改善
        improved_article = self.article_service.improve_article(article)
        updated_article = self.article_repo.update(improved_article)

        # 実行状態を更新
        self.step_status["topic_created"] = True
        self.current_topic_id = article.topic_id
        self.step_status["news_collected"] = True
        self.step_status["article_created"] = True
        self.current_article_id = article_id
        self.step_status["article_improved"] = True

        return updated_article

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

        # 記事が既に投稿済みの場合
        if article.status == "published":
            logging.info(f"記事ID {article_id} は既に投稿済みです")

            # 実行状態を更新
            self.step_status["topic_created"] = True
            self.current_topic_id = article.topic_id
            self.step_status["news_collected"] = True
            self.step_status["article_created"] = True
            self.current_article_id = article_id
            self.step_status["article_improved"] = article.improved_content is not None
            self.step_status["article_published"] = True

            return True

        # 記事を投稿
        success = self.note_poster_service.post_article(article)
        if success:
            article.status = "published"
            article.published_at = datetime.now()
            self.article_repo.update(article)

            # 実行状態を更新
            self.step_status["topic_created"] = True
            self.current_topic_id = article.topic_id
            self.step_status["news_collected"] = True
            self.step_status["article_created"] = True
            self.current_article_id = article_id
            self.step_status["article_improved"] = article.improved_content is not None
            self.step_status["article_published"] = True

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

    def get_step_status(self) -> Dict[str, bool]:
        """
        各ステップの実行状態を取得

        Returns:
            Dict[str, bool]: 各ステップの実行状態
        """
        return self.step_status.copy()

    def check_topic_exists(self, topic_id: int) -> Tuple[bool, Optional[str]]:
        """
        トピックの存在を確認

        Args:
            topic_id: トピックID

        Returns:
            Tuple[bool, Optional[str]]: (存在するか, エラーメッセージ)
        """
        try:
            topic = self.topic_repo.get_by_id(topic_id)
            return topic is not None, None
        except Exception as e:
            return False, str(e)

    def check_news_exists(self, topic_id: int) -> Tuple[bool, Optional[str]]:
        """
        ニュースデータの存在を確認

        Args:
            topic_id: トピックID

        Returns:
            Tuple[bool, Optional[str]]: (存在するか, エラーメッセージ)
        """
        try:
            news_data = self.news_repo.get_by_topic_id(topic_id)
            return news_data is not None, None
        except Exception as e:
            return False, str(e)

    def check_article_exists(
        self, topic_id: int
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        記事の存在を確認

        Args:
            topic_id: トピックID

        Returns:
            Tuple[bool, Optional[str], Optional[int]]: (存在するか, エラーメッセージ, 記事ID)
        """
        try:
            articles = self.article_repo.get_by_topic_id(topic_id)
            if not articles:
                return False, None, None
            return True, None, articles[0].id
        except Exception as e:
            return False, str(e), None

    def check_improved_article_exists(
        self, article_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        改善済み記事の存在を確認

        Args:
            article_id: 記事ID

        Returns:
            Tuple[bool, Optional[str]]: (存在するか, エラーメッセージ)
        """
        try:
            article = self.article_repo.get_by_id(article_id)
            if not article:
                return False, "記事が見つかりません"
            return article.improved_content is not None, None
        except Exception as e:
            return False, str(e)
