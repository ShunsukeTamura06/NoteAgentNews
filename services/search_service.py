# services/search_service.py
import asyncio
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from models.news_data import NewsData, NewsSource
from models.topic import Topic


class BaseSearchService(ABC):
    """検索サービスの基底クラス"""

    @abstractmethod
    async def search_topic(self, topic: Topic) -> NewsData:
        """
        トピックに関する情報を検索

        Args:
            topic: 検索するトピック

        Returns:
            NewsData: 収集されたニュースデータ
        """
        pass


class OpenAISearchService(BaseSearchService):
    """OpenAIのWeb検索機能を使用する検索サービス"""

    def __init__(self, api_key: Optional[str] = None):
        """
        検索サービスの初期化

        Args:
            api_key: OpenAI API キー（Noneの場合は環境変数から取得）
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)

    async def search_topic(self, topic: Topic) -> NewsData:
        """
        トピックに関する情報をOpenAI Web検索で取得

        Args:
            topic: 検索するトピック

        Returns:
            NewsData: 収集されたニュースデータ
        """
        logging.info(f"トピック「{topic.title}」の情報をOpenAI Web検索で検索します")

        # GPT-4でWeb検索を実行
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini-search-preview",
            web_search_options={
                "search_context_size": "high",
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

        # 検索結果から情報源と関連情報を抽出
        sources = []
        url_contents: Dict[str, str] = {}

        # 要約内容を全体の概要として保存
        summary_content = content

        # 各URLの引用を検出して関連情報を抽出
        if hasattr(message, "annotations") and message.annotations:
            # 先にすべてのURLを収集
            url_citations = []
            for annotation in message.annotations:
                if hasattr(annotation, "url_citation"):
                    url_citation = annotation.url_citation
                    url_citations.append(
                        {
                            "url": url_citation.url,
                            "title": url_citation.title,
                            "text": f"([{url_citation.title}]({url_citation.url}))",
                        }
                    )

            # 各URLに関連するテキストを抽出
            url_contents = self._extract_url_related_content(content, url_citations)

            # ソースリストを作成
            for annotation in message.annotations:
                if hasattr(annotation, "url_citation"):
                    url_citation = annotation.url_citation
                    url = url_citation.url

                    # URLに関連するコンテンツを取得（なければ概要の最初の部分を使用）
                    source_content = url_contents.get(
                        url, summary_content[:300] + "..."
                    )

                    sources.append(
                        NewsSource(
                            url=url,
                            title=url_citation.title,
                            content=source_content,
                        )
                    )

        # 情報源がない場合はコンテンツ全体を1つの情報源として扱う
        if not sources:
            sources.append(
                NewsSource(url="", title=topic.title, content=summary_content)
            )
        # 情報源はあるが、関連情報がない場合には最初のソースに全体概要を設定
        elif not any(url_contents.values()):
            sources[0] = NewsSource(
                url=sources[0].url,
                title=sources[0].title,
                content=summary_content,
            )

        return NewsData(topic_id=topic.id, sources=sources)

    def _extract_url_related_content(
        self, content: str, url_citations: List[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        テキスト内のURL引用から関連するコンテンツを抽出

        Args:
            content: 全体のテキスト内容
            url_citations: URL引用情報のリスト（url, title, text）

        Returns:
            Dict[str, str]: URLとそれに関連するコンテンツのマッピング
        """
        url_contents = {}

        # 各URLに対して
        for citation in url_citations:
            url = citation["url"]
            citation_text = citation["text"]

            # URL引用の位置を特定
            start_pos = content.find(citation_text)
            if start_pos == -1:
                continue

            # URL引用の前の文脈を抽出（最大200文字）
            context_start = max(0, start_pos - 200)
            context_end = start_pos + len(citation_text)

            # 引用の前の文章開始位置を見つける
            if context_start > 0:
                # 最後のピリオド、改行、または段落の開始を探す
                last_period = content.rfind(". ", context_start, start_pos)
                last_newline = content.rfind("\n", context_start, start_pos)
                last_break = max(last_period, last_newline)
                if last_break != -1:
                    context_start = last_break + 1

            # 最も近いURL引用を見つける
            next_citation_pos = len(content)
            for other_citation in url_citations:
                if other_citation["text"] == citation_text:
                    continue

                other_pos = content.find(other_citation["text"], context_end)
                if other_pos != -1 and other_pos < next_citation_pos:
                    next_citation_pos = other_pos

            # 次の引用までの範囲をURL関連コンテンツとする
            related_content = content[context_start:next_citation_pos].strip()

            # コンテンツが短すぎる場合、もう少し範囲を広げる
            if len(related_content) < 100 and next_citation_pos < len(content):
                # 次のピリオドまで拡張
                next_period = content.find(". ", next_citation_pos)
                if next_period != -1:
                    related_content = content[context_start : next_period + 1].strip()

            url_contents[url] = related_content

        return url_contents


# 検索エンジンの基底クラス（OpenManusのコードに基づく）
class WebSearchEngine:
    """Web検索エンジンの基底クラス"""

    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> list[dict]:
        """
        Perform a web search and return a list of URLs.

        Args:
            query (str): The search query to submit to the search engine.
            num_results (int, optional): The number of search results to return. Default is 10.
            args: Additional arguments.
            kwargs: Additional keyword arguments.

        Returns:
            List: A list of dict matching the search query.
        """
        raise NotImplementedError


# Google検索エンジンの実装
class GoogleSearchEngine(WebSearchEngine):
    """Google検索エンジン"""

    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Google search engine."""
        try:
            from googlesearch import search

            results = []
            for url in search(query, num_results=num_results):
                results.append({"url": url, "title": ""})
            return results
        except Exception as e:
            logging.error(f"Google検索中にエラーが発生しました: {e}")
            return []


# DuckDuckGo検索エンジンの実装
class DuckDuckGoSearchEngine(WebSearchEngine):
    """DuckDuckGo検索エンジン"""

    def perform_search(self, query, num_results=10, *args, **kwargs):
        """DuckDuckGo search engine."""
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results):
                    results.append({"url": r["href"], "title": r["title"]})
            return results
        except Exception as e:
            logging.error(f"DuckDuckGo検索中にエラーが発生しました: {e}")
            return []


class WebSearchService(BaseSearchService):
    """OpenManusの検索機能をベースにした検索サービス"""

    def __init__(self, api_key: Optional[str] = None):
        """
        検索サービスの初期化

        Args:
            api_key: API キー（現在は使用していないが互換性のために残す）
        """
        # 検索エンジンの初期化
        self._search_engines = {
            "google": GoogleSearchEngine(),
            "duckduckgo": DuckDuckGoSearchEngine(),
        }

        # デフォルトの検索エンジン順序（設定からオーバーライド可能）
        self._engine_order = ["google", "duckduckgo"]

        # 環境設定があれば読み込む
        if os.environ.get("SEARCH_ENGINE"):
            preferred = os.environ.get("SEARCH_ENGINE").lower()
            if preferred in self._search_engines:
                # 優先エンジンを先頭に設定
                self._engine_order = [preferred] + [
                    e for e in self._engine_order if e != preferred
                ]

    async def search_topic(self, topic: Topic) -> NewsData:
        """
        トピックに関する情報を検索エンジンで取得

        Args:
            topic: 検索するトピック

        Returns:
            NewsData: 収集されたニュースデータ
        """
        logging.info(f"トピック「{topic.title}」の情報をWeb検索で取得します")

        # 検索クエリを作成
        query = topic.title
        if topic.description:
            query += f" {topic.description}"

        # Web検索を実行
        sources = []
        search_results = await self._perform_web_search(query)

        if search_results:
            # 検索結果からURLのみ取得してコンテンツは空で設定
            # これはLLMが後でコンテキストから必要な情報を抽出するため
            for result in search_results:
                url = result.get("url", "")
                title = result.get("title", "")

                # タイトルがない場合はURLから生成
                if not title:
                    title = url.split("/")[-1].replace("-", " ").capitalize() or "無題"

                # シンプルにURLからコンテンツを取得（必要に応じて）
                content = ""
                if url:
                    content = await self._fetch_content_from_url(url)

                if url and content:
                    sources.append(
                        NewsSource(
                            url=url,
                            title=title,
                            content=content,
                        )
                    )

        # 情報源がない場合の対応
        if not sources:
            logging.warning("検索エンジンから情報を取得できませんでした")
            sources.append(
                NewsSource(
                    url="",
                    title=topic.title,
                    content=f"トピック「{topic.title}」に関する情報を取得できませんでした。別の検索方法を試してください。",
                )
            )

        # ニュースデータの作成
        news_data = NewsData(topic_id=topic.id, sources=sources)
        logging.info(
            f"トピック「{topic.title}」の情報収集が完了しました（情報源: {len(sources)}件）"
        )

        return news_data

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
    )
    async def _perform_web_search(
        self, query: str, num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Web検索を実行（OpenManusと同様のロジック）

        Args:
            query: 検索クエリ
            num_results: 結果数

        Returns:
            List[Dict]: 検索結果のリスト
        """
        for engine_name in self._engine_order:
            if engine_name not in self._search_engines:
                continue

            engine = self._search_engines[engine_name]
            try:
                logging.info(f"{engine_name}で検索を実行します: {query}")
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    None,
                    lambda: list(engine.perform_search(query, num_results=num_results)),
                )

                if results:
                    logging.info(f"{engine_name}検索結果: {len(results)}件")
                    return results
            except Exception as e:
                logging.error(f"{engine_name}検索中にエラーが発生しました: {e}")

        return []

    async def _fetch_content_from_url(self, url: str) -> str:
        """
        URLからコンテンツを取得（シンプルな実装）

        Args:
            url: 対象URL

        Returns:
            str: 取得したコンテンツ（失敗した場合は空文字列）
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                logging.info(f"URLアクセス中: {url}")
                try:
                    await page.goto(url, timeout=30000)

                    # 単純にページの全テキストを取得する（LLMが必要な情報を抽出するため）
                    content = await page.evaluate("document.body.innerText")

                    # 不要な空白を削除する最小限の整形のみ
                    content = re.sub(r"\s+", " ", content).strip()

                    await browser.close()
                    return content
                except Exception as e:
                    logging.error(f"ページアクセス中にエラーが発生しました: {e}")
                    await browser.close()
                    return ""
        except Exception as e:
            logging.error(f"ブラウザ操作中にエラーが発生しました: {e}")
            return ""


class SearchServiceFactory:
    """検索サービスのファクトリクラス"""

    @staticmethod
    def create_service(
        service_type: str = "web", api_key: Optional[str] = None
    ) -> BaseSearchService:
        """
        指定された種類の検索サービスを作成

        Args:
            service_type: 検索サービスの種類 ("web" または "openai")
            api_key: API キー

        Returns:
            BaseSearchService: 作成された検索サービス
        """
        if service_type.lower() == "openai":
            return OpenAISearchService(api_key)
        else:
            return WebSearchService(api_key)


# デフォルトの検索サービスとしてWebSearchServiceを使用
SearchService = WebSearchService
