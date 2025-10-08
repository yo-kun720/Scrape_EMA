"""
EMAニューススクレイピング機能
"""
import logging
import time
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pytz

from config import (
    EMA_BASE_URL, EMA_NEWS_URL, USER_AGENT, REQUEST_TIMEOUT,
    SLEEP_BETWEEN_REQUESTS, TIMEZONE, NEWS_CARD_SELECTORS,
    TITLE_SELECTORS, DATE_SELECTORS, CONTENT_SELECTORS,
    MAX_PARAGRAPHS_PER_ARTICLE, MAX_ARTICLES_TO_PROCESS
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EMANewsScraper:
    """EMAニューススクレイパー"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        self.tz = pytz.timezone(TIMEZONE)
    
    def get_news_articles(self, days_back: int = 7) -> List[Dict[str, str]]:
        """
        指定日数分のニュース記事を取得
        
        Args:
            days_back: 遡る日数
            
        Returns:
            記事のリスト（タイトル、URL、日付、要約、本文）
        """
        cutoff_date = datetime.now(self.tz) - timedelta(days=days_back)
        articles = []
        
        try:
            # ニュース一覧ページを取得
            news_urls = self._get_news_urls()
            logger.info(f"Found {len(news_urls)} news URLs")
            
            for i, url in enumerate(news_urls[:MAX_ARTICLES_TO_PROCESS]):
                try:
                    article = self._scrape_article(url)
                    if article and self._is_within_date_range(article['published_at'], cutoff_date):
                        articles.append(article)
                        logger.info(f"Added article: {article['title'][:50]}...")
                    elif article:
                        logger.info(f"Skipped old article: {article['title'][:50]}...")
                    
                    # サーバ負荷配慮
                    time.sleep(SLEEP_BETWEEN_REQUESTS)
                    
                except Exception as e:
                    logger.error(f"Error scraping article {url}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(articles)} articles within date range")
            return articles
            
        except Exception as e:
            logger.error(f"Error in get_news_articles: {e}")
            return []
    
    def _get_news_urls(self) -> List[str]:
        """ニュース一覧から記事URLを取得"""
        urls = []
        
        try:
            response = self.session.get(EMA_NEWS_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 複数のセレクタを試す
            for selector in NEWS_CARD_SELECTORS:
                cards = soup.select(selector)
                if cards:
                    logger.info(f"Found {len(cards)} cards with selector: {selector}")
                    break
            
            if not cards:
                # フォールバック: リンクを直接探す
                cards = soup.find_all('a', href=True)
                cards = [card for card in cards if '/en/news/' in card.get('href', '')]
            
            for card in cards:
                link = card.find('a', href=True) if card.name != 'a' else card
                if link:
                    href = link.get('href')
                    if href and '/en/news/' in href:
                        full_url = urljoin(EMA_BASE_URL, href)
                        if full_url not in urls:
                            urls.append(full_url)
            
            return urls
            
        except Exception as e:
            logger.error(f"Error getting news URLs: {e}")
            return []
    
    def _scrape_article(self, url: str) -> Optional[Dict[str, str]]:
        """個別記事をスクレイピング"""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトル取得
            title = self._extract_title(soup)
            if not title:
                return None
            
            # 日付取得
            published_at = self._extract_date(soup)
            if not published_at:
                return None
            
            # 本文取得
            content = self._extract_content(soup)
            
            # 関連文書をダウンロード（Reflection paperなどの場合）
            documents = []
            if any(keyword in title.lower() for keyword in ['reflection paper', 'guideline', 'consultation', 'draft']):
                documents = self._download_related_documents(soup, url)
            
            return {
                'title': title,
                'url': url,
                'published_at': published_at,
                'published_at_iso': published_at.isoformat(),
                'summary_or_lead': content[:200] + "..." if len(content) > 200 else content,
                'first_paragraphs': content,
                'documents': documents
            }
            
        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """タイトルを抽出"""
        for selector in TITLE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # フォールバック
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """日付を抽出"""
        for selector in DATE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                if element.get('datetime'):
                    date_text = element.get('datetime')
                
                try:
                    # 日付をパース
                    parsed_date = date_parser.parse(date_text)
                    
                    # タイムゾーン情報がない場合はUTCと仮定
                    if parsed_date.tzinfo is None:
                        parsed_date = pytz.utc.localize(parsed_date)
                    
                    # ローカルタイムゾーンに変換
                    return parsed_date.astimezone(self.tz)
                    
                except Exception as e:
                    logger.warning(f"Could not parse date '{date_text}': {e}")
                    continue
        
        # フォールバック: 現在時刻
        return datetime.now(self.tz)
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """本文を抽出"""
        paragraphs = []
        
        for selector in CONTENT_SELECTORS:
            elements = soup.select(selector)
            if elements:
                for p in elements[:MAX_PARAGRAPHS_PER_ARTICLE]:
                    text = p.get_text(strip=True)
                    if text and len(text) > 50:  # 短すぎる段落は除外
                        paragraphs.append(text)
                break
        
        # フォールバック: 一般的な段落タグ
        if not paragraphs:
            for p in soup.find_all('p')[:MAX_PARAGRAPHS_PER_ARTICLE]:
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    paragraphs.append(text)
        
        return '\n\n'.join(paragraphs) if paragraphs else "Content not available"
    
    def _download_related_documents(self, soup: BeautifulSoup, article_url: str) -> List[Dict[str, str]]:
        """関連文書をダウンロード"""
        documents = []
        
        try:
            # Related documentsセクションを探す
            related_section = soup.find('h3', string=re.compile(r'Related documents', re.I))
            if not related_section:
                return documents
            
            # 関連文書のリンクを取得
            document_links = related_section.find_next('ul')
            if not document_links:
                return documents
            
            for link in document_links.find_all('a', href=True):
                href = link.get('href')
                if href and (href.endswith('.pdf') or 'download' in href.lower()):
                    doc_url = urljoin(EMA_BASE_URL, href)
                    doc_title = link.get_text(strip=True)
                    
                    # PDFをダウンロード
                    try:
                        response = self.session.get(doc_url, timeout=REQUEST_TIMEOUT)
                        if response.status_code == 200:
                            # ファイル名を生成
                            filename = f"document_{len(documents)}_{doc_title[:50]}.pdf"
                            filepath = os.path.join(os.getcwd(), filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(response.content)
                            
                            documents.append({
                                'title': doc_title,
                                'url': doc_url,
                                'filepath': filepath,
                                'size': len(response.content)
                            })
                            
                            logger.info(f"Downloaded document: {doc_title}")
                            
                    except Exception as e:
                        logger.error(f"Error downloading document {doc_url}: {e}")
                        continue
                    
                    # サーバ負荷配慮
                    time.sleep(SLEEP_BETWEEN_REQUESTS)
        
        except Exception as e:
            logger.error(f"Error extracting related documents: {e}")
        
        return documents
    
    def _is_within_date_range(self, article_date: datetime, cutoff_date: datetime) -> bool:
        """記事が指定期間内かチェック"""
        return article_date >= cutoff_date


def scrape_ema_news(days_back: int = 7) -> List[Dict[str, str]]:
    """
    EMAニュースをスクレイピングするメイン関数
    
    Args:
        days_back: 遡る日数
        
    Returns:
        記事のリスト
    """
    scraper = EMANewsScraper()
    return scraper.get_news_articles(days_back)
