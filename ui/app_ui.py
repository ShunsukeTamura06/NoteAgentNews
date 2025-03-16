# ui/app_ui.py
import logging
from typing import Any, Dict, List, Tuple, Union

import gradio as gr

from config import Config
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

    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
        )

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

    def collect_news(self, topic_id: int) -> Dict[str, Any]:
        """
        ニュース収集UIハンドラ

        Args:
            topic_id: トピックID

        Returns:
            Dict: 処理結果
        """
        try:
            if not topic_id:
                return {"success": False, "message": "トピックを選択してください"}

            news_data = self.app_service.collect_news_for_topic(int(topic_id))
            return {
                "success": True,
                "message": f"トピックの情報を収集しました（情報源: {len(news_data.sources)}件）",
                "news_id": news_data.id,
            }
        except Exception as e:
            logging.error(
                f"ニュース収集中にエラーが発生しました: {str(e)}", exc_info=True
            )
            return {"success": False, "message": f"エラー: {str(e)}"}

    def create_article(self, topic_id: int) -> Dict[str, Any]:
        """
        記事作成UIハンドラ

        Args:
            topic_id: トピックID

        Returns:
            Dict: 処理結果
        """
        try:
            if not topic_id:
                return {"success": False, "message": "トピックを選択してください"}

            article = self.app_service.create_article_for_topic(int(topic_id))
            return {
                "success": True,
                "message": f"記事「{article.title}」を作成しました",
                "article_id": article.id,
                "article_content": article.content,
            }
        except Exception as e:
            logging.error(f"記事作成中にエラーが発生しました: {str(e)}", exc_info=True)
            return {"success": False, "message": f"エラー: {str(e)}"}

    def improve_article(self, article_id: Union[int, Dict[str, Any]]) -> Dict[str, Any]:
        """
        記事改善UIハンドラ

        Args:
            article_id: 記事ID (整数またはID情報を含む辞書)

        Returns:
            Dict: 処理結果
        """
        try:
            if not article_id:
                return {"success": False, "message": "記事を選択してください"}

            # article_id が辞書の場合は、idキーからIDを取得
            if isinstance(article_id, dict) and "article_id" in article_id:
                actual_id = article_id["article_id"]
            else:
                actual_id = article_id

            # 型変換
            improved_article = self.app_service.improve_article(int(actual_id))
            return {
                "success": True,
                "message": f"記事「{improved_article.title}」を改善しました",
                "article_id": improved_article.id,
                "improved_content": improved_article.improved_content,
            }
        except Exception as e:
            logging.error(f"記事改善中にエラーが発生しました: {str(e)}", exc_info=True)
            return {"success": False, "message": f"エラー: {str(e)}"}

    def post_to_note(self, article_id: Union[int, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Note投稿UIハンドラ

        Args:
            article_id: 記事ID (整数またはID情報を含む辞書)

        Returns:
            Dict: 処理結果
        """
        try:
            if not article_id:
                return {"success": False, "message": "記事を選択してください"}

            # article_id が辞書の場合は、idキーからIDを取得
            if isinstance(article_id, dict) and "article_id" in article_id:
                actual_id = article_id["article_id"]
            else:
                actual_id = article_id

            success = self.app_service.post_article_to_note(int(actual_id))
            if success:
                return {"success": True, "message": "記事をNoteに投稿しました"}
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

    def launch(self):
        """UIを起動"""
        with gr.Blocks(title="ニュース記事自動生成システム") as app:
            gr.Markdown("# 🗞️ ニュース記事自動生成システム")
            gr.Markdown(
                "サラリーマンの副業として、ニュースを自動収集・分析し、高品質なレポートを生成して投稿するシステムです。"
            )

            with gr.Tab("全自動処理"):
                with gr.Row():
                    with gr.Column(scale=2):
                        title_input = gr.Textbox(
                            label="トピックタイトル（例: 石破首相の10万円商品券配布問題）"
                        )
                        desc_input = gr.Textbox(label="トピック説明（任意）", lines=3)
                        note_post_checkbox = gr.Checkbox(
                            label="Noteに投稿する", value=False
                        )

                        run_btn = gr.Button("🚀 全プロセス実行", variant="primary")
                        status_output = gr.Markdown()

                    with gr.Column(scale=3):
                        article_output = gr.Markdown(
                            label="生成された記事", elem_id="article-output"
                        )

            with gr.Tab("ステップ実行"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("## 1. トピック作成")
                        step_title_input = gr.Textbox(label="トピックタイトル")
                        step_desc_input = gr.Textbox(
                            label="トピック説明（任意）", lines=2
                        )
                        create_topic_btn = gr.Button("トピック作成")
                        topic_status = gr.Markdown()

                        gr.Markdown("## 2. 情報収集")
                        topic_dropdown = gr.Dropdown(label="トピック選択")
                        refresh_topics_btn = gr.Button("トピック一覧更新")
                        collect_news_btn = gr.Button("情報収集実行")
                        news_status = gr.Markdown()

                        gr.Markdown("## 3. 記事作成")
                        create_article_btn = gr.Button("記事作成実行")
                        article_status = gr.Markdown()

                        gr.Markdown("## 4. 記事改善")
                        improve_article_btn = gr.Button("記事改善実行")
                        improve_status = gr.Markdown()

                        gr.Markdown("## 5. Note投稿")
                        post_note_btn = gr.Button("Noteに投稿")
                        post_status = gr.Markdown()

                    with gr.Column(scale=2):
                        step_article_output = gr.Markdown(
                            label="記事プレビュー", elem_id="step-article-output"
                        )

            # 辞書結果を文字列に変換する関数
            def format_topic_status(result: Dict[str, Any]) -> str:
                """辞書結果を文字列に変換"""
                if result.get("success"):
                    return f"✅ {result['message']}"
                else:
                    return f"❌ {result['message']}"

            # 全プロセス結果を文字列に変換する関数
            def format_full_process_result(result: Dict[str, Any]) -> Tuple[str, str]:
                """全プロセス結果を文字列に変換し、記事内容も返す"""
                message = result.get("message", "")
                if isinstance(message, list):
                    message = "\n".join(message)
                article_content = result.get("article_content", "")
                return message, article_content

            # 全自動処理
            run_btn.click(
                fn=lambda title, desc, post: format_full_process_result(
                    self.run_full_process(title, desc, post)
                ),
                inputs=[title_input, desc_input, note_post_checkbox],
                outputs=[status_output, article_output],
            )

            # ステップ実行
            create_topic_btn.click(
                fn=lambda title, desc: format_topic_status(
                    self.create_topic(title, desc)
                ),
                inputs=[step_title_input, step_desc_input],
                outputs=topic_status,
            )

            def update_topics_dropdown():
                topics = self.get_topics()
                return gr.update(
                    choices=[(f"{t['id']}: {t['title']}", t["id"]) for t in topics]
                )

            refresh_topics_btn.click(fn=update_topics_dropdown, outputs=topic_dropdown)

            collect_news_btn.click(
                fn=lambda topic_id: format_topic_status(self.collect_news(topic_id)),
                inputs=topic_dropdown,
                outputs=news_status,
            )

            def create_article_and_update(topic_id):
                """記事作成関数 - 記事IDを直接返すよう修正"""
                result = self.create_article(topic_id)
                message = format_topic_status(result)  # 表示用メッセージを生成
                content = (
                    result.get("article_content", "") if result.get("success") else ""
                )

                # 記事IDを直接取得する（辞書全体を渡さない）
                article_id = None
                if result.get("success") and "article_id" in result:
                    article_id = result["article_id"]

                return message, content, article_id

            # 記事IDを保持するための状態変数
            article_id_state = gr.State(None)

            create_article_btn.click(
                fn=create_article_and_update,
                inputs=topic_dropdown,
                outputs=[article_status, step_article_output, article_id_state],
            )

            def improve_article_and_update(article_id):
                """記事改善関数 - article_idの型チェックを追加"""
                if not article_id:
                    return "❌ 記事が選択されていません", ""

                # article_id が辞書の場合に処理
                if isinstance(article_id, dict) and "article_id" in article_id:
                    article_id = article_id["article_id"]

                try:
                    result = self.improve_article(article_id)
                    message = format_topic_status(result)
                    content = (
                        result.get("improved_content", "")
                        if result.get("success")
                        else ""
                    )
                    return message, content
                except Exception as e:
                    logging.error(f"記事改善処理でエラー: {str(e)}", exc_info=True)
                    return f"❌ エラー: {str(e)}", ""

            improve_article_btn.click(
                fn=improve_article_and_update,
                inputs=article_id_state,
                outputs=[improve_status, step_article_output],
            )

            def post_to_note_and_update(article_id):
                """Note投稿関数 - article_idの型チェックを追加"""
                if not article_id:
                    return "❌ 記事が選択されていません"

                # article_id が辞書の場合に処理
                if isinstance(article_id, dict) and "article_id" in article_id:
                    article_id = article_id["article_id"]

                try:
                    result = self.post_to_note(article_id)
                    return format_topic_status(result)
                except Exception as e:
                    logging.error(f"記事投稿処理でエラー: {str(e)}", exc_info=True)
                    return f"❌ エラー: {str(e)}"

            post_note_btn.click(
                fn=post_to_note_and_update,
                inputs=article_id_state,
                outputs=post_status,
            )

            # 初期化時にトピック一覧を更新

        # Gradioアプリを起動
        app.launch(share=False)
