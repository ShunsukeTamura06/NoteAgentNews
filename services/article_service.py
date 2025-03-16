# services/article_service.py
import logging
import os
from typing import Optional

from openai import OpenAI

from models.article import Article
from models.news_data import NewsData
from models.topic import Topic


class ArticleService:
    """記事の作成と改善を担当するサービス"""

    def __init__(self, api_key: Optional[str] = None):
        """
        記事サービスの初期化

        Args:
            api_key: OpenAI API キー（Noneの場合は環境変数から取得）
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)

        # 記事作成用のプロンプト
        self.article_prompt = """
        # 指示
        - 提供されたニュースデータをもとに、2000〜3000文字程度の記事を作成してください。
        - 記事は 小学生高学年～中学生でも理解できるレベル で書く一方、 ビジネスマン向け の内容になるようにしてください。
        - 各段落には参考にしたソースのリンクを記載してください。
        - 記事には「概要」「主な登場人物」「時系列」「主な争点」「影響と今後の展開」「まとめ」を含めてください。
        - 記事は、最初に概要や結論を述べて、その後に詳細が続く形にしてください。
        - 絵文字やアイコンを効果的に配置（✏️📌📝🔍📊など）することで、視覚的にも分かりやすくしてください。

        # 記事データ
        {news_data}
        """

        # 記事改善用のプロンプト
        self.improve_prompt = """
        # 指示
        現在の記事は有料記事としての価値が60点程度です。以下の点を改善して、100点の価値ある記事に仕上げてください：

        1. 専門的な分析を追加し、深い洞察を提供する
        2. データや具体例を追加して説得力を高める
        3. ビジネスパーソンにとって実用的な視点や提案を盛り込む
        4. 読みやすさ、視覚的な魅力をさらに高める
        5. 記事の構成や流れを最適化する

        改善後の記事は、単なる情報提供ではなく「この記事を読んで良かった」と思える価値を提供するものにしてください。
        Markdown形式で記事全体を提供してください。

        # 記事
        {article}
        """

    def create_article_from_news(self, topic: Topic, news_data: NewsData) -> Article:
        """
        ニュースデータから記事を作成

        Args:
            topic: 記事のトピック
            news_data: ニュースデータ

        Returns:
            Article: 作成された記事
        """
        logging.info(f"トピック「{topic.title}」の記事を作成します")

        # ニュースデータを文字列に変換
        news_text = ""
        for i, source in enumerate(news_data.sources):
            news_text += f"情報源 {i + 1}:\n"
            news_text += f"タイトル: {source.title}\n"
            news_text += f"URL: {source.url}\n"
            news_text += f"内容: {source.content}\n\n"

        # GPT-4を使用して記事を生成
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "あなたは優秀なビジネスライターです。与えられた情報から分かりやすく魅力的な記事を作成します。",
                },
                {
                    "role": "user",
                    "content": self.article_prompt.format(news_data=news_text),
                },
            ],
        )

        content = response.choices[0].message.content

        # 記事のタイトルは最初の行から取得（# で始まる行）
        lines = content.split("\n")
        title = topic.title
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        return Article(
            topic_id=topic.id,
            news_data_id=news_data.id,
            title=title,
            content=content,
            status="draft",
        )

    def improve_article(self, article: Article) -> Article:
        """
        記事を改善

        Args:
            article: 改善する記事

        Returns:
            Article: 改善された記事
        """
        logging.info(f"記事「{article.title}」を改善します")

        # GPT-4を使用して記事を改善
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "あなたは優秀なビジネスエディターです。記事の質を向上させて、より価値の高いコンテンツにします。",
                },
                {
                    "role": "user",
                    "content": self.improve_prompt.format(article=article.content),
                },
            ],
        )

        improved_content = response.choices[0].message.content

        # 更新された記事を返す
        article.improved_content = improved_content
        article.status = "improved"

        return article
