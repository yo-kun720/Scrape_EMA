"""
OpenAI API連携とHTML生成機能
"""
import logging
import os
from typing import List, Dict
from dotenv import load_dotenv

import openai
from openai import OpenAI

from config import MODEL_NAME, OPENAI_API_KEY
from shared.pdf_summarizer import summarize_pdf_documents

# .envファイルを読み込む
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLGenerator:
    """OpenAI APIを使用してHTMLを生成するクラス"""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = MODEL_NAME
    
    def generate_email_html(self, articles: List[Dict[str, str]], source: str = "EMA") -> str:
        """
        記事リストからメール用HTMLを生成
        
        Args:
            articles: 記事のリスト
            source: データソース ("EMA" または "FDA")
            
        Returns:
            生成されたHTML文字列
        """
        if not articles:
            return self._generate_empty_html(source)
        
        try:
            # 関連文書がある記事を処理
            processed_articles = []
            for article in articles:
                if 'documents' in article and article['documents']:
                    # PDF文書を要約
                    summarized_docs = summarize_pdf_documents(article['documents'])
                    article['summarized_documents'] = summarized_docs
                processed_articles.append(article)
            
            prompt = self._build_prompt(processed_articles, source)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは日本語の技術文書ライターです。【最重要ルール】記事タイトル（h2タグ）のみ英語のまま、それ以外のすべての内容（公開日、要点リスト、詳細要約、説明文、ラベル）は必ず日本語で記載してください。英語の原文をそのままコピーすることは絶対禁止です。すべての内容を日本語に翻訳してください。例：「WHO has today launched」→「WHOは本日、立ち上げました」"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            html_content = response.choices[0].message.content.strip()
            
            # HTMLタグのみを抽出（余計な説明文を除去）
            if html_content.startswith('<html'):
                return html_content
            elif '<html' in html_content:
                start = html_content.find('<html')
                return html_content[start:]
            else:
                # HTMLタグがない場合はラップ
                return self._wrap_html(html_content, processed_articles, source)
                
        except Exception as e:
            logger.error(f"Error generating HTML: {e}")
            return self._generate_fallback_html(articles, source)
    
    def _build_prompt(self, articles: List[Dict[str, str]], source: str = "EMA") -> str:
        """プロンプトを構築"""
        articles_text = ""
        for i, article in enumerate(articles, 1):
            articles_text += f"""
記事{i}:
- タイトル: {article['title']}
- URL: {article['url']}
- 公開日: {article['published_at_iso']}"""
            
            # PMDAの場合はカテゴリ情報を追加
            if source == "PMDA" and 'category' in article:
                articles_text += f"\n- カテゴリ: {article['category']}"
            
            articles_text += f"""
- 要約: {article['summary_or_lead']}
- 本文: {article['first_paragraphs']}
"""
            
            # 関連文書の要約がある場合は追加
            if 'summarized_documents' in article and article['summarized_documents']:
                articles_text += "\n- 関連文書要約:\n"
                for doc in article['summarized_documents']:
                    articles_text += f"  * {doc['title']}: {doc['summary']}\n"
            
            articles_text += "\n"
        
        # データソースに応じてプロンプトを動的に生成
        if source == "FDA":
            source_name = "FDA（U.S. Food and Drug Administration）のガイダンス文書"
            data_source = "Data source: U.S. Food and Drug Administration (FDA)"
        elif source == "PMDA":
            source_name = "PMDA（独立行政法人 医薬品医療機器総合機構）の新着情報"
            data_source = "Data source: 独立行政法人 医薬品医療機器総合機構 (PMDA)"
        elif source == "WHO":
            source_name = "WHO（World Health Organization）のニュース記事"
            data_source = "Data source: World Health Organization (WHO)"
        else:
            source_name = "EMA（European Medicines Agency）のニュース記事"
            data_source = "Data source: European Medicines Agency (EMA)"

        prompt = f"""
以下の{source_name}を、詳細な要約を含むモバイルフレンドリーなHTMLに変換してください。

【最重要ルール - 絶対に守ってください】
1. 記事タイトル（h2タグ）のみ英語のまま
2. それ以外のすべての内容は必ず日本語で記載
3. 英語の原文をそのままコピーすることは絶対禁止
4. すべての要約・説明・ラベルは日本語に翻訳

【出力形式】
各記事について以下を含める:
- 記事タイトル（h2タグ、英語のまま）
- 公開日（日本語で「公開日: YYYY年MM月DD日」）
- カテゴリ（PMDAの場合のみ、日本語）
- 要点リスト（3-5項目、完全に日本語）
- 詳細要約文（2-3段落、完全に日本語）
- 関連文書がある場合は、その要約も完全に日本語

【技術要件】
- 見出し（h1, h2）と要点リストを使用
- 各記事をカード形式で表示
- インラインCSSでスタイリング（幅を広く設定：max-width: 1200px）
- モバイルフレンドリーなデザイン
- 安全なリンク（target="_blank" rel="noopener"）
- 最後に「{data_source}」と各記事URLを記載

【翻訳例】
英語: "WHO has today launched the Global Clinical Trials Forum"
日本語: "WHOは本日、グローバル臨床試験フォーラムを立ち上げました"

記事データ:
{articles_text}

出力は完全なHTMLドキュメント（<html>...</html>）のみを返してください。説明文は不要です。
"""
        return prompt
    
    def _wrap_html(self, content: str, articles: List[Dict[str, str]], source: str = "EMA") -> str:
        """コンテンツをHTMLでラップ"""
        source_urls = "\n".join([f"<li><a href='{article['url']}' target='_blank' rel='noopener'>{article['title']}</a></li>" for article in articles])
        
        # データソースに応じてタイトルとフッターを動的に生成
        if source == "FDA":
            title = "FDA Guidance Summary"
            data_source = "Data source: U.S. Food and Drug Administration (FDA)"
        elif source == "PMDA":
            title = "PMDA News Summary"
            data_source = "Data source: 独立行政法人 医薬品医療機器総合機構 (PMDA)"
        elif source == "WHO":
            title = "WHO News Summary"
            data_source = "Data source: World Health Organization (WHO)"
        else:
            title = "EMA News Summary"
            data_source = "Data source: European Medicines Agency (EMA)"
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .article {{ margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; background: #f8f9fa; }}
        .article h3 {{ margin: 0 0 10px 0; color: #2c3e50; }}
        .article .date {{ color: #7f8c8d; font-size: 0.9em; margin-bottom: 10px; }}
        .article .summary {{ margin: 10px 0; }}
        .article a {{ color: #3498db; text-decoration: none; }}
        .article a:hover {{ text-decoration: underline; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ecf0f1; font-size: 0.9em; color: #7f8c8d; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="container">
        {content}
        <div class="footer">
            <h3>{data_source}</h3>
            <p>記事URL:</p>
            <ul>
                {source_urls}
            </ul>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_empty_html(self, source: str = "EMA") -> str:
        """記事がない場合のHTML"""
        # データソースに応じてタイトルとフッターを動的に生成
        if source == "FDA":
            title = "FDA Guidance Summary"
            data_source = "Data source: U.S. Food and Drug Administration (FDA)"
            message = "指定期間内に新しいガイダンス文書は見つかりませんでした。"
        elif source == "PMDA":
            title = "PMDA News Summary"
            data_source = "Data source: 独立行政法人 医薬品医療機器総合機構 (PMDA)"
            message = "指定期間内に新しい情報は見つかりませんでした。"
        elif source == "WHO":
            title = "WHO News Summary"
            data_source = "Data source: World Health Organization (WHO)"
            message = "指定期間内に新しいニュースは見つかりませんでした。"
        else:
            title = "EMA News Summary"
            data_source = "Data source: European Medicines Agency (EMA)"
            message = "指定期間内に新しい記事は見つかりませんでした。"
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
        h1 {{ color: #2c3e50; }}
        p {{ color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>{message}</p>
        <div class="footer">
            <p>{data_source}</p>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_fallback_html(self, articles: List[Dict[str, str]], source: str = "EMA") -> str:
        """フォールバック用のHTML"""
        if not articles:
            return self._generate_empty_html(source)
        
        articles_html = ""
        for article in articles:
            articles_html += f"""
        <div class="article">
            <h3>{article['title']}</h3>
            <div class="date">{article['published_at_iso']}</div>
            <div class="summary">{article['summary_or_lead']}</div>
            <a href="{article['url']}" target="_blank" rel="noopener">記事を読む</a>
        </div>
"""
        
        source_urls = "\n".join([f"<li><a href='{article['url']}' target='_blank' rel='noopener'>{article['title']}</a></li>" for article in articles])
        
        # データソースに応じてタイトルとフッターを動的に生成
        if source == "FDA":
            title = "FDA Guidance Summary"
            data_source = "Data source: U.S. Food and Drug Administration (FDA)"
        elif source == "PMDA":
            title = "PMDA News Summary"
            data_source = "Data source: 独立行政法人 医薬品医療機器総合機構 (PMDA)"
        elif source == "WHO":
            title = "WHO News Summary"
            data_source = "Data source: World Health Organization (WHO)"
        else:
            title = "EMA News Summary"
            data_source = "Data source: European Medicines Agency (EMA)"
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .article {{ margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; background: #f8f9fa; }}
        .article h3 {{ margin: 0 0 10px 0; color: #2c3e50; }}
        .article .date {{ color: #7f8c8d; font-size: 0.9em; margin-bottom: 10px; }}
        .article .summary {{ margin: 10px 0; }}
        .article a {{ color: #3498db; text-decoration: none; }}
        .article a:hover {{ text-decoration: underline; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ecf0f1; font-size: 0.9em; color: #7f8c8d; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        {articles_html}
        <div class="footer">
            <h3>{data_source}</h3>
            <p>記事URL:</p>
            <ul>
                {source_urls}
            </ul>
        </div>
    </div>
</body>
</html>"""


def generate_html_from_articles(articles: List[Dict[str, str]], source: str = "EMA") -> str:
    """
    記事リストからHTMLを生成するメイン関数
    
    Args:
        articles: 記事のリスト
        source: データソース ("EMA" または "FDA")
        
    Returns:
        生成されたHTML文字列
    """
    generator = HTMLGenerator()
    return generator.generate_email_html(articles, source)
