# ui/app_ui.py
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import gradio as gr

from config import Config
from models.article import Article
from services.app_service import AppService


class AppUI:
    """Gradioによるユーザーインターフェース"""

    def __init__(self, app_service: AppService):
        """
        UIの初期化

        Args:
            app_service: アプリケーションサービス
        """
        self.app_service = app_service
        self.setup_logging()

        # ステップ実行の状態管理
        self.current_topic_id = None
        self.current_news_id = None
        self.current_article_id = None
        self.current_improved_article_id = None

        # 設定ファイルパス
        self.settings_file = "app_settings.json"
        self.load_settings()

    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
        )

    def load_settings(self) -> Dict[str, str]:
        """
        設定を読み込む

        Returns:
            Dict: 設定情報
        """
        default_settings = {
            "OPENAI_API_KEY": Config.OPENAI_API_KEY or "",
            "NOTE_EMAIL": Config.NOTE_EMAIL or "",
            "NOTE_PASSWORD": Config.NOTE_PASSWORD or "",
            "DB_PATH": Config.DB_PATH or "news_reports.db",
            "LOG_LEVEL": Config.LOG_LEVEL or "INFO",
        }

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    saved_settings = json.load(f)
                    # デフォルト設定をアップデート
                    default_settings.update(saved_settings)
            except Exception as e:
                logging.error(f"設定ファイル読み込み中にエラーが発生しました: {str(e)}")

        self.settings = default_settings
        return self.settings

    def save_settings(self, settings: Dict[str, str]) -> Dict[str, Any]:
        """
        設定を保存する

        Args:
            settings: 保存する設定

        Returns:
            Dict: 処理結果
        """
        try:
            # 設定を更新
            self.settings.update(settings)

            # 設定ファイルに保存
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)

            # 環境変数を更新（現在のプロセスのみ）
            os.environ["OPENAI_API_KEY"] = settings.get("OPENAI_API_KEY", "")
            os.environ["NOTE_EMAIL"] = settings.get("NOTE_EMAIL", "")
            os.environ["NOTE_PASSWORD"] = settings.get("NOTE_PASSWORD", "")
            os.environ["DB_PATH"] = settings.get("DB_PATH", "news_reports.db")
            os.environ["LOG_LEVEL"] = settings.get("LOG_LEVEL", "INFO")

            # Configクラスの値も更新
            Config.OPENAI_API_KEY = settings.get("OPENAI_API_KEY", "")
            Config.NOTE_EMAIL = settings.get("NOTE_EMAIL", "")
            Config.NOTE_PASSWORD = settings.get("NOTE_PASSWORD", "")
            Config.DB_PATH = settings.get("DB_PATH", "news_reports.db")
            Config.LOG_LEVEL = settings.get("LOG_LEVEL", "INFO")

            return {
                "success": True,
                "message": "設定を保存しました。新しい設定を適用するには、アプリケーションを再起動してください。",
            }
        except Exception as e:
            logging.error(f"設定保存中にエラーが発生しました: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"設定保存中にエラーが発生しました: {str(e)}",
            }

    def create_topic(self, title: str, description: str) -> Dict[str, Any]:
        """
        トピックを作成するUIハンドラ

        Args:
            title: トピックのタイトル
            description: トピックの説明

        Returns:
            Dict: 処理結果
        """
        try:
            if not title:
                return {
                    "success": False,
                    "message": "トピックのタイトルを入力してください",
                }

            topic = self.app_service.create_topic(title, description)
            # 現在のトピックIDを保存
            self.current_topic_id = topic.id

            return {
                "success": True,
                "message": f"トピック「{topic.title}」を作成しました（ID: {topic.id}）",
                "topic_id": topic.id,
            }
        except Exception as e:
            logging.error(
                f"トピック作成中にエラーが発生しました: {str(e)}", exc_info=True
            )
            return {"success": False, "message": f"エラー: {str(e)}"}

    def get_topics(self) -> List[Dict[str, Any]]:
        """
        トピックリストを取得するUIハンドラ

        Returns:
            List[Dict]: トピックリスト
        """
        try:
            topics = self.app_service.get_topics()
            return [
                {
                    "id": topic.id,
                    "title": topic.title,
                    "description": topic.description or "",
                    "created_at": topic.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for topic in topics
            ]
        except Exception as e:
            logging.error(
                f"トピック取得中にエラーが発生しました: {str(e)}", exc_info=True
            )
            return []

    async def collect_news(self, topic_id: Optional[int] = None) -> Dict[str, Any]:
        """
        ニュース収集UIハンドラ

        Args:
            topic_id: トピックID（Noneの場合は現在のトピックIDを使用）

        Returns:
            Dict: 処理結果
        """
        try:
            # トピックIDが指定されていない場合は現在のIDを使用
            if topic_id is None:
                topic_id = self.current_topic_id

            if not topic_id:
                return {"success": False, "message": "トピックを選択してください"}

            # ここで await を追加して非同期処理の完了を待つ
            news_data = await self.app_service.collect_news_for_topic(int(topic_id))

            # 現在のニュースIDを保存
            self.current_news_id = news_data.id
            # トピックIDも更新
            self.current_topic_id = int(topic_id)

            return {
                "success": True,
                "message": f"トピックの情報を収集しました（情報源: {len(news_data.sources)}件）",
                "news_id": news_data.id,
                "topic_id": topic_id,
            }
        except Exception as e:
            logging.error(
                f"ニュース収集中にエラーが発生しました: {str(e)}", exc_info=True
            )
            return {"success": False, "message": f"エラー: {str(e)}"}

    def format_topic_status(self, result):
        """トピック作成結果をフォーマット"""
        if result.get("success"):
            return f"✅ {result['message']}"
        else:
            return f"❌ {result['message']}"

    async def collect_news_with_progress(self, topic_id):
        """
        プログレスバー付きのニュース収集関数

        Args:
            topic_id: トピックID

        Returns:
            str: 結果メッセージ
        """
        result = await self.collect_news(topic_id)
        return self.format_topic_status(result)

    async def create_article(self, topic_id: Optional[int] = None) -> Dict[str, Any]:
        """
        記事作成UIハンドラ

        Args:
            topic_id: トピックID（Noneの場合は現在のトピックIDを使用）

        Returns:
            Dict: 処理結果
        """
        try:
            # トピックIDが指定されていない場合は現在のIDを使用
            if topic_id is None:
                topic_id = self.current_topic_id

            if not topic_id:
                return {"success": False, "message": "トピックを選択してください"}

            # await を追加して非同期処理の完了を待つ
            article = await self.app_service.create_article_for_topic(int(topic_id))

            # 現在の記事IDを保存
            self.current_article_id = article.id
            # トピックIDも更新
            self.current_topic_id = int(topic_id)

            return {
                "success": True,
                "message": f"記事「{article.title}」を作成しました",
                "article_id": article.id,
                "article_content": article.content,
                "topic_id": topic_id,
            }
        except Exception as e:
            logging.error(f"記事作成中にエラーが発生しました: {str(e)}", exc_info=True)
            return {"success": False, "message": f"エラー: {str(e)}"}

    async def improve_article(
        self,
        article_id: Optional[Union[int, Dict[str, Any]]] = None,
        topic_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        記事改善UIハンドラ

        Args:
            article_id: 記事ID（Noneの場合はトピックから記事を取得）
            topic_id: トピックID（article_idがNoneの場合に使用）

        Returns:
            Dict: 処理結果
        """
        try:
            # 記事IDが指定されていない場合はトピックから取得
            if article_id is None:
                if topic_id is None:
                    topic_id = self.current_topic_id

                if not topic_id:
                    return {
                        "success": False,
                        "message": "トピックまたは記事を選択してください",
                    }

                # トピックに関連する最新の記事を取得
                articles = self.app_service.article_repo.get_by_topic_id(int(topic_id))
                if not articles:
                    return {
                        "success": False,
                        "message": f"トピックID {topic_id} に関連する記事が見つかりません",
                    }
                article_id = articles[0].id

            # article_id が辞書の場合は、idキーからIDを取得
            if isinstance(article_id, dict) and "article_id" in article_id:
                actual_id = article_id["article_id"]
            else:
                actual_id = article_id

            if not actual_id:
                return {"success": False, "message": "記事を選択してください"}

            # 型変換
            improved_article = self.app_service.improve_article(int(actual_id))
            # 改善済み記事IDを保存
            self.current_improved_article_id = improved_article.id
            # 記事IDも更新
            self.current_article_id = improved_article.id
            # トピックIDも更新
            self.current_topic_id = improved_article.topic_id

            return {
                "success": True,
                "message": f"記事「{improved_article.title}」を改善しました",
                "article_id": improved_article.id,
                "improved_content": improved_article.improved_content,
                "topic_id": improved_article.topic_id,
            }
        except Exception as e:
            logging.error(f"記事改善中にエラーが発生しました: {str(e)}", exc_info=True)
            return {"success": False, "message": f"エラー: {str(e)}"}

    def post_to_note(
        self,
        article_id: Optional[Union[int, Dict[str, Any]]] = None,
        topic_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Note投稿UIハンドラ

        Args:
            article_id: 記事ID（Noneの場合はトピックから記事を取得）
            topic_id: トピックID（article_idがNoneの場合に使用）

        Returns:
            Dict: 処理結果
        """
        try:
            # 記事IDが指定されていない場合はトピックから取得
            if article_id is None:
                if topic_id is None:
                    topic_id = self.current_topic_id

                if not topic_id:
                    return {
                        "success": False,
                        "message": "トピックまたは記事を選択してください",
                    }

                # トピックに関連する最新の記事を取得
                articles = self.app_service.article_repo.get_by_topic_id(int(topic_id))
                if not articles:
                    return {
                        "success": False,
                        "message": f"トピックID {topic_id} に関連する記事が見つかりません",
                    }
                article_id = articles[0].id

            # article_id が辞書の場合は、idキーからIDを取得
            if isinstance(article_id, dict) and "article_id" in article_id:
                actual_id = article_id["article_id"]
            else:
                actual_id = article_id

            if not actual_id:
                return {"success": False, "message": "記事を選択してください"}

            # Noteの認証情報確認
            if not Config.NOTE_EMAIL or not Config.NOTE_PASSWORD:
                return {
                    "success": False,
                    "message": "Note投稿には認証情報の設定が必要です。設定タブから設定してください。",
                }

            success = self.app_service.post_article_to_note(int(actual_id))
            if success:
                # 記事の情報を取得して返す
                article = self.app_service.article_repo.get_by_id(int(actual_id))
                return {
                    "success": True,
                    "message": f"記事「{article.title}」をNoteに投稿しました",
                    "article_id": actual_id,
                    "topic_id": article.topic_id,
                }
            else:
                return {"success": False, "message": "Noteへの投稿に失敗しました"}
        except Exception as e:
            logging.error(f"Note投稿中にエラーが発生しました: {str(e)}", exc_info=True)
            return {"success": False, "message": f"エラー: {str(e)}"}

    def run_full_process(
        self, title: str, description: str, post_to_note: bool
    ) -> Dict[str, Any]:
        """
        全プロセス実行UIハンドラ

        Args:
            title: トピックのタイトル
            description: トピックの説明
            post_to_note: Noteに投稿するかどうか

        Returns:
            Dict: プロセスの結果情報
        """
        try:
            if not title:
                return {
                    "success": False,
                    "message": "トピックのタイトルを入力してください",
                }

            result = self.app_service.run_full_process(title, description, post_to_note)

            # 結果のフォーマット
            article = result.get("improved_article") or result.get("article")
            content = None
            if article:
                content = (
                    article.improved_content
                    if article.improved_content
                    else article.content
                )

                # 状態を更新
                self.current_topic_id = article.topic_id
                self.current_article_id = article.id
                if article.improved_content:
                    self.current_improved_article_id = article.id

            return {
                "success": result["success"],
                "message": "\n".join(result["messages"]),
                "article_content": content,
            }
        except Exception as e:
            logging.error(
                f"全プロセス実行中にエラーが発生しました: {str(e)}", exc_info=True
            )
            return {"success": False, "message": f"エラー: {str(e)}"}

    def get_step_status(self) -> Dict[str, Any]:
        """
        ステップの状態を取得

        Returns:
            Dict: 各ステップの状態
        """
        statuses = {
            "topic_selected": self.current_topic_id is not None,
            "news_collected": self.current_news_id is not None,
            "article_created": self.current_article_id is not None,
            "article_improved": self.current_improved_article_id is not None,
        }

        return statuses

    def get_article_by_id(self, article_id: int) -> Optional[Article]:
        """
        IDから記事を取得

        Args:
            article_id: 記事ID

        Returns:
            Optional[Article]: 記事オブジェクトまたはNone
        """
        try:
            return self.app_service.article_repo.get_by_id(article_id)
        except Exception as e:
            logging.error(f"記事取得中にエラーが発生しました: {str(e)}", exc_info=True)
            return None

    def get_topic_details(self, topic_id: int) -> Dict[str, Any]:
        """
        トピックの詳細情報を取得

        Args:
            topic_id: トピックID

        Returns:
            Dict: トピック情報
        """
        try:
            topic = self.app_service.topic_repo.get_by_id(topic_id)
            if not topic:
                return {
                    "success": False,
                    "message": f"トピックID {topic_id} が見つかりません",
                }

            # トピックに関連する記事を取得
            articles = self.app_service.article_repo.get_by_topic_id(topic_id)

            # ニュースデータを取得
            news_data = self.app_service.news_repo.get_by_topic_id(topic_id)

            return {
                "success": True,
                "topic": {
                    "id": topic.id,
                    "title": topic.title,
                    "description": topic.description,
                    "created_at": topic.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "has_news": news_data is not None,
                "articles": [
                    {
                        "id": article.id,
                        "title": article.title,
                        "status": article.status,
                        "created_at": article.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    for article in articles
                ],
            }
        except Exception as e:
            logging.error(
                f"トピック詳細取得中にエラーが発生しました: {str(e)}", exc_info=True
            )
            return {"success": False, "message": f"エラー: {str(e)}"}

    def launch(self):
        """UIを起動"""
        with gr.Blocks(title="ニュース記事自動生成システム") as app:
            # 状態変数
            current_article_content = gr.State(value="")
            current_topic_id = gr.State(value=None)

            gr.Markdown("# 🗞️ ニュース記事自動生成システム")
            gr.Markdown(
                "サラリーマンの副業として、ニュースを自動収集・分析し、高品質なレポートを生成して投稿するシステムです。"
            )

            with gr.Tabs() as tabs:
                # 全自動処理タブ
                with gr.TabItem("全自動処理", id="tab_auto"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            with gr.Group():
                                gr.Markdown("## 📝 トピック情報")
                                title_input = gr.Textbox(
                                    label="トピックタイトル",
                                    placeholder="例: 石破首相の10万円商品券配布問題",
                                )
                                desc_input = gr.Textbox(
                                    label="トピック説明（任意）",
                                    placeholder="トピックに関する詳細情報があれば入力してください",
                                    lines=3,
                                )
                                note_post_checkbox = gr.Checkbox(
                                    label="処理完了後にNoteに投稿する", value=False
                                )

                            with gr.Group():
                                gr.Markdown("## 🚀 処理実行")
                                with gr.Row():
                                    run_btn = gr.Button(
                                        "全プロセス実行", variant="primary", size="lg"
                                    )
                                    clear_btn = gr.Button("フォームをクリア", size="lg")

                                with gr.Row():
                                    status_output = gr.Markdown()

                        with gr.Column(scale=3):
                            gr.Markdown("## 📄 生成記事プレビュー")
                            article_output = gr.Markdown(
                                label="生成された記事",
                                elem_id="article-output",
                                elem_classes=["article-preview"],
                            )

                # ステップ実行タブ
                with gr.TabItem("ステップ実行", id="tab_step"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            # ステップ1: トピック作成/選択
                            with gr.Group():
                                gr.Markdown("## 1️⃣ トピック作成/選択")
                                with gr.Group():
                                    gr.Markdown("### 新規トピック作成")
                                    step_title_input = gr.Textbox(
                                        label="トピックタイトル",
                                        placeholder="例: 地下鉄サリン事件",
                                    )
                                    step_desc_input = gr.Textbox(
                                        label="トピック説明（任意）",
                                        placeholder="トピックに関する説明（任意）",
                                        lines=2,
                                    )
                                    create_topic_btn = gr.Button(
                                        "トピック作成", variant="primary"
                                    )
                                    topic_status = gr.Markdown()

                                with gr.Group():
                                    gr.Markdown("### 既存トピック選択")
                                    with gr.Row():
                                        topic_dropdown = gr.Dropdown(
                                            label="トピック選択"
                                        )
                                        refresh_topics_btn = gr.Button(
                                            "更新", size="sm"
                                        )

                                    topic_info = gr.Markdown()

                            # ステップ2: 情報収集
                            with gr.Group():
                                gr.Markdown("## 2️⃣ 情報収集")
                                with gr.Group():
                                    collect_news_btn = gr.Button(
                                        "情報収集実行", variant="primary"
                                    )
                                    news_status = gr.Markdown()

                            # ステップ3: 記事作成
                            with gr.Group():
                                gr.Markdown("## 3️⃣ 記事作成")
                                with gr.Group():
                                    create_article_btn = gr.Button(
                                        "記事作成実行", variant="primary"
                                    )
                                    article_status = gr.Markdown()

                            # ステップ4: 記事改善
                            with gr.Group():
                                gr.Markdown("## 4️⃣ 記事改善")
                                with gr.Group():
                                    improve_article_btn = gr.Button(
                                        "記事改善実行", variant="primary"
                                    )
                                    improve_status = gr.Markdown()

                            # ステップ5: Note投稿
                            with gr.Group():
                                gr.Markdown("## 5️⃣ Note投稿")
                                with gr.Group():
                                    post_note_btn = gr.Button(
                                        "Noteに投稿", variant="primary"
                                    )
                                    post_status = gr.Markdown()

                        with gr.Column(scale=2):
                            gr.Markdown("## 📄 記事プレビュー")
                            step_article_output = gr.Markdown(
                                label="記事プレビュー",
                                elem_id="step-article-output",
                                elem_classes=["article-preview"],
                            )

                # 設定タブ
                with gr.TabItem("設定", id="tab_settings"):
                    with gr.Group():
                        gr.Markdown("## ⚙️ アプリケーション設定")

                        with gr.Row():
                            with gr.Column():
                                # OpenAI API設定
                                gr.Markdown("### OpenAI API設定")
                                openai_api_key = gr.Textbox(
                                    label="OpenAI APIキー",
                                    placeholder="sk-...",
                                    type="password",
                                    value=self.settings.get("OPENAI_API_KEY", ""),
                                )

                                # Note設定
                                gr.Markdown("### Note設定")
                                note_email = gr.Textbox(
                                    label="Noteメールアドレス",
                                    placeholder="example@example.com",
                                    value=self.settings.get("NOTE_EMAIL", ""),
                                )
                                note_password = gr.Textbox(
                                    label="Noteパスワード",
                                    type="password",
                                    value=self.settings.get("NOTE_PASSWORD", ""),
                                )

                            with gr.Column():
                                # データベース設定
                                gr.Markdown("### データベース設定")
                                db_path = gr.Textbox(
                                    label="データベースパス",
                                    placeholder="news_reports.db",
                                    value=self.settings.get(
                                        "DB_PATH", "news_reports.db"
                                    ),
                                )

                                # ログ設定
                                gr.Markdown("### ログ設定")
                                log_level = gr.Dropdown(
                                    label="ログレベル",
                                    choices=[
                                        "DEBUG",
                                        "INFO",
                                        "WARNING",
                                        "ERROR",
                                        "CRITICAL",
                                    ],
                                    value=self.settings.get("LOG_LEVEL", "INFO"),
                                )

                        # 保存ボタン
                        save_settings_btn = gr.Button("設定を保存", variant="primary")
                        settings_status = gr.Markdown()

            # スタイル設定
            gr.Markdown("""
            <style>
            .article-preview {
                max-height: 600px;
                overflow-y: auto;
                padding: 15px;
                border: 1px solid #e1e1e1;
                border-radius: 4px;
                background-color: #fcfcfc;
            }
            </style>
            """)

            # イベントハンドラー設定
            # 全自動処理タブ
            def format_full_process_result(result):
                """全プロセス結果を文字列に変換し、記事内容も返す"""
                message = result.get("message", "")
                if isinstance(message, list):
                    message = "\n".join(message)
                article_content = result.get("article_content", "")
                return message, article_content

            run_btn.click(
                fn=lambda title, desc, post: format_full_process_result(
                    self.run_full_process(title, desc, post)
                ),
                inputs=[title_input, desc_input, note_post_checkbox],
                outputs=[status_output, article_output],
            )

            clear_btn.click(
                fn=lambda: ("", "", False),
                outputs=[title_input, desc_input, note_post_checkbox],
            )

            # ステップ実行タブ

            def update_topic_info(topic_id):
                """トピック情報を更新"""
                if not topic_id:
                    return "", None

                result = self.get_topic_details(topic_id)
                if not result.get("success"):
                    return (
                        f"❌ {result.get('message', 'トピック情報の取得に失敗しました')}",
                        None,
                    )

                topic = result["topic"]
                articles = result.get("articles", [])
                has_news = result.get("has_news", False)

                info = f"**トピック**: {topic['title']}\n\n"
                if topic["description"]:
                    info += f"**説明**: {topic['description']}\n\n"
                info += f"**作成日時**: {topic['created_at']}\n\n"

                info += f"**ニュースデータ**: {'あり' if has_news else 'なし'}\n\n"

                if articles:
                    info += "**関連記事**:\n"
                    for article in articles:
                        status_emoji = (
                            "📝"
                            if article["status"] == "draft"
                            else "✨"
                            if article["status"] == "improved"
                            else "🌐"
                            if article["status"] == "published"
                            else "❓"
                        )
                        info += f"- {status_emoji} {article['title']} ({article['status']})\n"
                else:
                    info += "**関連記事**: なし\n"

                # 現在のトピックIDを更新
                self.current_topic_id = topic_id

                return info, topic_id

            # トピック作成
            create_topic_btn.click(
                fn=lambda title, desc: (
                    self.format_topic_status(self.create_topic(title, desc)),
                    self.current_topic_id,
                ),
                inputs=[step_title_input, step_desc_input],
                outputs=[topic_status, current_topic_id],
            )

            # トピック選択変更時
            topic_dropdown.change(
                fn=update_topic_info,
                inputs=topic_dropdown,
                outputs=[topic_info, current_topic_id],
            )

            # トピックリスト更新
            def update_topics_dropdown():
                topics = self.get_topics()
                return gr.update(
                    choices=[(f"{t['id']}: {t['title']}", t["id"]) for t in topics]
                )

            refresh_topics_btn.click(fn=update_topics_dropdown, outputs=topic_dropdown)

            # ニュース収集
            collect_news_btn.click(
                fn=self.collect_news_with_progress,
                inputs=current_topic_id,
                outputs=news_status,
            )

            # 記事作成
            async def create_article_with_progress(topic_id):
                """
                記事作成関数（プログレスバー付き）
                """
                result = await self.create_article(topic_id)
                message = self.format_topic_status(result)
                content = (
                    result.get("article_content", "") if result.get("success") else ""
                )
                return message, content

            create_article_btn.click(
                fn=create_article_with_progress,
                inputs=current_topic_id,
                outputs=[article_status, step_article_output],
            )

            # 記事改善
            async def improve_article_with_topic(topic_id):
                result = await self.improve_article(topic_id=topic_id)
                message = self.format_topic_status(result)
                content = (
                    result.get("improved_content", "") if result.get("success") else ""
                )
                return message, content

            improve_article_btn.click(
                fn=improve_article_with_topic,
                inputs=current_topic_id,
                outputs=[improve_status, step_article_output],
            )

            # Note投稿
            def post_to_note_with_topic(topic_id):
                result = self.post_to_note(topic_id=topic_id)
                return self.format_topic_status(result)

            post_note_btn.click(
                fn=post_to_note_with_topic,
                inputs=current_topic_id,
                outputs=post_status,
            )

            # 設定保存
            def save_settings_handler(api_key, email, password, db, log_level):
                settings = {
                    "OPENAI_API_KEY": api_key,
                    "NOTE_EMAIL": email,
                    "NOTE_PASSWORD": password,
                    "DB_PATH": db,
                    "LOG_LEVEL": log_level,
                }
                result = self.save_settings(settings)
                if result.get("success"):
                    return f"✅ {result['message']}"
                else:
                    return f"❌ {result['message']}"

            save_settings_btn.click(
                fn=save_settings_handler,
                inputs=[openai_api_key, note_email, note_password, db_path, log_level],
                outputs=settings_status,
            )

            # 初期化時にトピック一覧を更新
            app.load(fn=update_topics_dropdown, outputs=topic_dropdown)

        # Gradioアプリを起動
        app.launch(share=False)
