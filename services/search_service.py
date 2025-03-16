# services/search_service.py
import logging
import os
from typing import Optional

from openai import OpenAI

from models.news_data import NewsData, NewsSource
from models.topic import Topic


class SearchService:
    """トピックに関する情報をWeb検索するサービス"""

    def __init__(self, api_key: Optional[str] = None):
        """
        検索サービスの初期化

        Args:
            api_key: OpenAI API キー（Noneの場合は環境変数から取得）
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)

    def search_topic(self, topic: Topic) -> NewsData:
        """
        トピックに関する情報をWeb検索

        Args:
            topic: 検索するトピック

        Returns:
            NewsData: 収集されたニュースデータ
        """
        logging.info(f"トピック「{topic.title}」の情報を検索します")

        # GPT-4でWeb検索を実行
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini-search-preview",
            web_search_options={
                "search_context_size": "medium",
                "user_location": {
                    "type": "approximate",
                    "approximate": {
                        "country": "JP",
                        "timezone": "Asia/Tokyo",
                    },
                },
            },
            messages=[
                {
                    "role": "system",
                    "content": """
                    あなたは優秀なリサーチツールです。与えられたトピックについて情報収集をしてください。
                    以下の要素が特に重要です：
                    1. 概要 - トピックの基本情報
                    2. 主な登場人物 - 関連する人物や組織
                    3. 時系列 - いつ何が起きたのか
                    4. 主な争点 - 問題点や議論されている事項
                    5. 影響と今後の展開 - 社会的影響や予測される未来
                    
                    できるだけ正確な情報を集め、各情報には信頼できるソースを引用してください。
                    """,
                },
                {
                    "role": "user",
                    "content": f"「{topic.title}」について調査して、詳細な情報を提供してください。{topic.description or ''}",
                },
            ],
        )

        message = completion.choices[0].message
        content = message.content

        # 検索結果から情報源を抽出
        sources = []

        if hasattr(message, "annotations") and message.annotations:
            for annotation in message.annotations:
                if hasattr(annotation, "url_citation"):
                    url_citation = annotation.url_citation
                    sources.append(
                        NewsSource(
                            url=url_citation.url,
                            title=url_citation.title,
                            content=content,
                        )
                    )

        # 情報源がない場合はコンテンツ全体を1つの情報源として扱う
        if not sources:
            sources.append(NewsSource(url="", title=topic.title, content=content))

        return NewsData(topic_id=topic.id, sources=sources)
