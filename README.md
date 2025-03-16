# プロジェクトの目的
- サラリーマンの副業として、ニュースを自動収集・分析し、高品質なレポートを生成して投稿するシステムを開発します。
- リアルタイム性と分かりやすさ、専門的な分析価値により、個人向けに月額200円のサブスクリプションサービスを提供し、月1万円の収入獲得を目指します。
- 記事は2日に1回のペースで投稿します。

## プロジェクト要件
- sqliteでデータを管理する

# 処理の流れ
・トピックを決定(人の手で入力「石破首相の10万円商品券配布問題」「地下鉄サリン事件」など。将来的には自動化。)
↓
テキスト
↓
・トピックの情報収集(Web search Toolなど)(正確な情報をできるだけ沢山収集する)
↓
テキスト
↓
・トピックの情報から記事作成
↓
Markdown形式テキスト
↓
・記事を改善(60点→100点)
↓
Markdown形式テキスト
↓
・記事をNoteに投稿

## 記事作成用のプロンプト
```
# 指示
- 提供されたニュースデータをもとに、2000〜3000文字程度の記事を作成してください。
- 記事は 小学生高学年～中学生でも理解できるレベル で書く一方、 ビジネスマン向け の内容になるようにしてください。
- 各段落には参考にしたソースのリンクを記載してください。
- 記事には「概要」「主な登場人物」「時系列」「主な争点」「影響と今後の展開」「まとめ」を含めてください。
- 記事は、最初に概要や結論を述べて、その後に詳細が続く形にしてください。
- 絵文字やアイコンを効果的に配置（✏️📌📝🔍📊など）することで、視覚的にも分かりやすくしてください。

# 記事データ
{news_data}
```

## 記事改善用のプロンプト
以下のプロンプト例を中心として、お金を稼ぐという本来の目的を実現するためのより良いプロンプトに改善してください。
```
今の記事が有料記事としての魅力度が60点とした場合、100点の記事を書いて

# 記事
{article}
```

# コードのルール
- SOLID原則に従い将来的な拡張や変更に対し堅牢にしてください。
- 型ヒントや日本語のDocStringを書いてください
- プロンプト、トピック、記事作成実行など全体を管理するGUIをgradioで作成してください。
- 記事をNoteに投稿プログラムは、以下のNote投稿プログラム例を参考にPlaywrightで作成してください。
- トピックの情報収集プログラムは、以下のWEB検索プログラム例を参考に作成してください。

## WEB検索プログラム例
```python
from openai import OpenAI

client = OpenAI()
completion = client.chat.completions.create(
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
            "role": "user",
            "content": "「色づく世界の明日から」というアニメは長崎が舞台ですが、どんな聖地があるか調べて教えてください",
        }
    ],
)

message = completion.choices[0].message
print(f"{message.content=}")
print()
for annotation in message.annotations:
    url_citation = annotation.url_citation
    print(f"[{url_citation.title}]({url_citation.url})")

```

## Note投稿プログラム例
```python
import os
import time
import logging
import argparse
import re
import pyperclip
from playwright.sync_api import sync_playwright

class NoteMarkdownPoster:
    """
    Markdownファイルの記事をnoteに投稿するツール
    ・Markdownファイルから記事を読み込み、セクションごとにnoteに投稿します
    ・見出しと段落を適切に処理します
    """

    def __init__(self, email: str, password: str):
        """
        :param email: noteアカウントのメールアドレス
        :param password: noteアカウントのパスワード
        """
        self.email = email
        self.password = password
        self.browser = None
        self.context = None
        self.page = None
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    def login(self):
        """
        noteにログインし、セッションを確立します
        """
        logging.info("noteへのログインを開始します")
        self.page.goto("https://note.com/login")
        self.page.wait_for_selector("#email", timeout=10000)
        self.page.wait_for_selector("#password", timeout=10000)
        time.sleep(1)
        self.page.fill("#email", self.email)
        self.page.fill("#password", self.password)
        self.page.click('button:has(div:has-text("ログイン"))')
        self.page.wait_for_load_state("networkidle")
        logging.info("✅ noteにログイン成功")

    def parse_markdown(self, markdown_path):
        """
        Markdownファイルを解析して、タイトルとセクションに分割します
        
        :param markdown_path: Markdownファイルのパス
        :return: (タイトル, セクションのリスト)
        """
        logging.info(f"Markdownファイルを解析中: {markdown_path}")
        
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 最初の# で始まる行をタイトルとして扱う
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            # タイトル行を除外
            content = content.replace(title_match.group(0), '', 1).strip()
        else:
            # タイトルが見つからない場合はファイル名を使用
            title = os.path.basename(markdown_path).replace('.md', '')
            
        logging.info(f"記事タイトル: {title}")
        
        # セクションに分割（見出しと段落）
        sections = []
        
        # 見出しのパターン
        heading_pattern = re.compile(r'^(#{1,3}) (.+)$', re.MULTILINE)
        
        # セクションを抽出
        last_pos = 0
        for match in heading_pattern.finditer(content):
            # 前のセクションの終わりから現在の見出しの前までをパラグラフとして追加
            paragraph_content = content[last_pos:match.start()].strip()
            if paragraph_content:
                sections.append({
                    'type': 'paragraph',
                    'content': paragraph_content
                })
            
            # 見出しを追加
            heading_level = len(match.group(1))
            heading_text = match.group(2).strip()
            sections.append({
                'type': f'heading{heading_level}',
                'content': heading_text
            })
            
            last_pos = match.end()
        
        # 最後のセクション
        if last_pos < len(content):
            paragraph_content = content[last_pos:].strip()
            if paragraph_content:
                sections.append({
                    'type': 'paragraph',
                    'content': paragraph_content
                })
        
        logging.info(f"セクション数: {len(sections)}")
        return title, sections

    def _post_paragraph(self, content: str):
        """
        段落テキストをnoteに投稿します
        """
        logging.info(f"📝 段落を入力中: {content[:30]}...")
        pyperclip.copy(content)
        self.page.keyboard.press("Control+V")
        self.page.keyboard.press("Enter")
        self.page.keyboard.press("Enter")
        time.sleep(0.5)

    def _post_heading(self, content: str, level: int):
        """
        見出しをnoteに投稿します
        """
        logging.info(f"📝 見出し{level}を入力中: {content}")
        
        # クリップボードにコピー
        pyperclip.copy(content)
        
        # 貼り付け
        self.page.keyboard.press("Control+V")
        self.page.keyboard.press("Enter")
        
        # 見出しとして設定
        if level == 1:
            # 見出し1は自動的に設定されることが多い
            pass
        elif level == 2:
            # 見出し2に設定
            self.page.keyboard.press("ArrowUp")
            self.page.keyboard.press("Control+Alt+2")
        elif level == 3:
            # 見出し3に設定
            self.page.keyboard.press("ArrowUp")
            self.page.keyboard.press("Control+Alt+3")
            
        time.sleep(0.5)

    def _handle_section(self, section):
        """
        セクションタイプに応じて適切な投稿処理を行います
        """
        section_type = section['type']
        content = section['content']
        
        if section_type == 'paragraph':
            self._post_paragraph(content)
        elif section_type.startswith('heading'):
            level = int(section_type[-1])
            self._post_heading(content, level)
        else:
            logging.warning(f"⚠️ 未知のセクションタイプ '{section_type}' をスキップします")

    def create_and_post_article(self, title, sections):
        """
        noteの新規記事作成ページに遷移し、セクションごとに投稿します
        
        :param title: 記事のタイトル
        :param sections: 記事のセクションリスト
        """
        logging.info("📝 noteの新規記事作成ページにアクセス中...")
        self.page.goto("https://note.com/notes/new")
        self.page.wait_for_load_state("networkidle")
        
        # タイトル入力
        self.page.fill('textarea[placeholder="記事タイトル"]', title)
        self.page.keyboard.press("Enter")
        time.sleep(0.5)
        logging.info(f"📝 記事タイトル '{title}' を入力しました")

        # セクションごとに処理
        for section in sections:
            self._handle_section(section)

        # 記事を下書き保存
        logging.info("💾 記事を下書きとして保存します")
        self.page.click("button:has-text('保存')")
        self.page.wait_for_load_state("networkidle")
        logging.info("✅ 記事の下書き保存が完了しました")
        time.sleep(2)

    def run(self, markdown_path):
        """
        Playwrightの起動から記事投稿までを統括的に実行します
        
        :param markdown_path: 投稿するMarkdownファイルのパス
        """
        logging.info(f"🚀 {markdown_path} から記事投稿プロセスを開始します")
        
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=False)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()

            try:
                # Markdownファイルを解析
                title, sections = self.parse_markdown(markdown_path)
                
                # ログインして記事投稿
                self.login()
                self.create_and_post_article(title, sections)
                
                logging.info("✅ 記事投稿プロセスが完了しました")
            except Exception as e:
                logging.error(f"❌ エラー: {e}")
            finally:
                self.context.close()
                self.browser.close()
                logging.info("🚀 Playwright処理が正常に完了しました")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Markdownファイルからnoteに記事を自動投稿するツール')
    parser.add_argument('markdown_path', help='投稿するMarkdownファイルのパス')
    parser.add_argument('email', help='noteのログインメールアドレス')
    parser.add_argument('password', help='noteのログインパスワード')
    
    args = parser.parse_args()
    
    poster = NoteMarkdownPoster(args.email, args.password)
    poster.run(args.markdown_path)
```