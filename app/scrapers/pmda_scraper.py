"""
PMDA新着情報スクレイパー
"""
import logging
import re
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pytz
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

from config import (
    USER_AGENT, REQUEST_TIMEOUT, SLEEP_BETWEEN_REQUESTS, TIMEZONE,
    MAX_PARAGRAPHS_PER_ARTICLE, MAX_ARTICLES_TO_PROCESS
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PMDA設定
PMDA_BASE_URL = "https://www.pmda.go.jp"
PMDA_NEWS_URL = f"{PMDA_BASE_URL}/0017.html"


class PMDAScraper:
    """PMDA新着情報スクレイパー"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.tz = pytz.timezone(TIMEZONE)
    
    def scrape_pmda_news(self, days_back: int) -> List[Dict[str, str]]:
        """
        PMDA新着情報をスクレイピングし、指定期間内のものを取得
        
        Args:
            days_back: 何日前からの情報を取得するか
            
        Returns:
            記事のリスト
        """
        cutoff_date = self.tz.localize(datetime.now()) - timedelta(days=days_back)
        logger.info(f"Scraping PMDA news from {cutoff_date.strftime('%Y-%m-%d')}")
        
        try:
            news_items = self._get_news_urls()
            if not news_items:
                logger.warning("No news items found")
                return []
            
            articles = []
            for i, news_item in enumerate(news_items[:MAX_ARTICLES_TO_PROCESS]):
                try:
                    url = news_item['url']
                    date_text = news_item['date_text']
                    category = news_item['category']
                    title = news_item['title']
                    
                    logger.info(f"Processing article {i+1}/{min(len(news_items), MAX_ARTICLES_TO_PROCESS)}: {url}")
                    
                    # 日付を解析
                    published_at = self._parse_date_from_text(date_text)
                    if not published_at:
                        logger.warning(f"Could not parse date '{date_text}', using current time")
                        published_at = datetime.now(self.tz)
                    
                    logger.info(f"Article date: {published_at}")
                    logger.info(f"Cutoff date: {cutoff_date}")
                    logger.info(f"Within range: {self._is_within_date_range(published_at, cutoff_date)}")
                    
                    # 期間内かチェック
                    if self._is_within_date_range(published_at, cutoff_date):
                        # 記事の詳細を取得
                        article_detail = self._scrape_article(url)
                        if article_detail:
                            # カテゴリ情報を追加
                            article_detail['category'] = category
                            article_detail['published_at'] = published_at
                            article_detail['published_at_iso'] = published_at.isoformat()
                            
                            articles.append(article_detail)
                            logger.info(f"Added article: {article_detail['title'][:50]}... (Category: {category})")
                        else:
                            logger.warning(f"Failed to scrape article details: {url}")
                    else:
                        logger.info(f"Skipped old article: {title[:50]}... (Date: {published_at.strftime('%Y-%m-%d')})")
                    
                    if i < len(news_items) - 1:
                        logger.info(f"Waiting {SLEEP_BETWEEN_REQUESTS} seconds...")
                        time.sleep(SLEEP_BETWEEN_REQUESTS)
                
                except Exception as e:
                    logger.error(f"Error processing article {news_item.get('url', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(articles)} articles within date range")
            return articles
            
        except Exception as e:
            logger.error(f"Error in scrape_pmda_news: {e}")
            return []
    
    def _get_news_urls(self) -> List[Dict[str, str]]:
        """新着情報のURL一覧を取得（日付とカテゴリ情報も含む）"""
        try:
            logger.info("Getting PMDA news URLs...")
            
            response = self.session.get(PMDA_NEWS_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            news_items = []
            
            # 実際のHTML構造に基づいて<ul class="list__news">を探す
            news_lists = soup.select('ul.list__news')
            logger.info(f"Found {len(news_lists)} news lists")
            
            for news_list in news_lists:
                items = news_list.select('li')
                logger.info(f"News list has {len(items)} items")
                
                for item in items:
                    try:
                        # 日付を抽出
                        date_element = item.select_one('p.date')
                        if not date_element:
                            continue
                        
                        date_text = date_element.get_text(strip=True)
                        logger.info(f"Found date: {date_text}")
                        
                        # カテゴリを抽出
                        category_element = item.select_one('p.category')
                        category = category_element.get_text(strip=True) if category_element else ""
                        logger.info(f"Found category: {category}")
                        
                        # カテゴリフィルタリング（採用と調達を除外）
                        if category in ['採用', '調達']:
                            logger.info(f"Skipping item due to category: {category}")
                            continue
                        
                        # タイトルを抽出（<p class="title">から）
                        title_element = item.select_one('p.title')
                        title = title_element.get_text(strip=True) if title_element else ""
                        
                        # リンクを抽出
                        link_element = item.select_one('a[href]')
                        if not link_element:
                            continue
                        
                        href = link_element.get('href')
                        
                        if href and self._is_news_url(href, title):
                            full_url = urljoin(PMDA_BASE_URL, href)
                            
                            news_item = {
                                'url': full_url,
                                'date_text': date_text,
                                'category': category,
                                'title': title
                            }
                            
                            news_items.append(news_item)
                            logger.info(f"Found news item: {full_url} - {title[:50]}... (Date: {date_text}, Category: {category})")
                    
                    except Exception as e:
                        logger.error(f"Error processing news item: {e}")
                        continue
            
            # フォールバック: 一般的なリストから探す
            if not news_items:
                logger.info("No news items found in ul.list__news, trying general lists...")
                general_lists = soup.select('ul li, ol li')
                logger.info(f"Found {len(general_lists)} general list items")
                
                for item in general_lists:
                    try:
                        item_text = item.get_text(strip=True)
                        
                        # 日付パターンを含む項目を探す
                        if re.search(r'\d{4}年\d{1,2}月\d{1,2}日', item_text):
                            # タイトルを抽出（<p class="title">から）
                            title_element = item.select_one('p.title')
                            title = title_element.get_text(strip=True) if title_element else ""
                            
                            # この項目内のリンクを探す
                            links = item.select('a')
                            for link in links:
                                href = link.get('href')
                                
                                if href and self._is_news_url(href, title):
                                    full_url = urljoin(PMDA_BASE_URL, href)
                                    
                                    news_item = {
                                        'url': full_url,
                                        'date_text': '日付不明',
                                        'category': 'その他',
                                        'title': title
                                    }
                                    
                                    news_items.append(news_item)
                                    logger.info(f"Found news item (fallback): {full_url} - {title[:50]}...")
                    
                    except Exception as e:
                        logger.error(f"Error processing fallback item: {e}")
                        continue
            
            logger.info(f"Found {len(news_items)} total news items")
            return news_items
            
        except Exception as e:
            logger.error(f"Error getting news URLs: {e}")
            return []
    
    def _is_news_url(self, url: str, text: str) -> bool:
        """ニュースURLかどうか判定"""
        if not url or not text:
            return False
        
        # 除外パターン
        exclude_patterns = [
            '/english/',
            '/sitemap',
            '/contact',
            '/privacy',
            '/accessibility',
            '/site-policy',
            '/link',
            '/search',
            '/user/',
            '.pdf$',
            '.doc$',
            '.docx$',
            '.xls$',
            '.xlsx$',
            'javascript:',
            'mailto:',
            '#',
            'apology_objects'
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # テキストの長さチェック（短すぎるものは除外）
        if len(text) < 10:
            return False
        
        # PMDAの内部リンクかチェック
        if url.startswith('/') or 'pmda.go.jp' in url:
            return True
        
        return False
    
    def _extract_date_from_item(self, item) -> Optional[str]:
        """リスト項目から日付を抽出"""
        # 日付パターンを探す
        date_patterns = [
            r'\b(\d{4}年\d{1,2}月\d{1,2}日)\b',  # 2025年10月7日
            r'\b(\d{4}/\d{1,2}/\d{1,2})\b',      # 2025/10/7
            r'\b(\d{4}-\d{1,2}-\d{1,2})\b',      # 2025-10-7
        ]
        
        item_text = item.get_text()
        for pattern in date_patterns:
            matches = re.findall(pattern, item_text)
            if matches:
                return matches[0]
        
        return None
    
    def _parse_date_from_text(self, date_text: str) -> Optional[datetime]:
        """日付テキストからdatetimeオブジェクトを解析"""
        if not date_text or date_text == '日付不明':
            return None
        
        try:
            # 日本語の日付形式に対応 (例: 2025年10月7日)
            if '年' in date_text and '月' in date_text and '日' in date_text:
                # 2025年10月7日 -> 2025-10-7
                date_text = date_text.replace('年', '-').replace('月', '-').replace('日', '')
                parsed_date = date_parser.parse(date_text).replace(tzinfo=self.tz)
                return parsed_date
            else:
                # その他の形式も試す
                parsed_date = date_parser.parse(date_text).replace(tzinfo=self.tz)
                return parsed_date
        except Exception as e:
            logger.warning(f"Could not parse date '{date_text}': {e}")
            return None
    
    def _scrape_article(self, url: str) -> Optional[Dict[str, str]]:
        """個別記事をスクレイピング"""
        try:
            logger.info(f"Scraping article: {url}")
            
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトルを抽出
            title = self._extract_title(soup)
            if not title:
                logger.warning(f"No title found for {url}")
                return None
            
            # 要約・リード文を抽出
            summary = self._extract_summary(soup)
            
            # 本文の最初の数段落を抽出
            first_paragraphs = self._extract_content(soup)
            
            return {
                'title': title,
                'url': url,
                'summary_or_lead': summary,
                'first_paragraphs': first_paragraphs,
                'related_documents': []  # PMDAでは関連文書は通常ない
            }
            
        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """タイトルを抽出"""
        selectors = [
            'h1',
            '.page-title',
            '.article-title',
            '.news-title',
            'title',
            'meta[property="og:title"]',
            'meta[name="dcterms.title"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    title = element.get('content', '').strip()
                else:
                    title = element.get_text(strip=True)
                
                if title and len(title) > 10:
                    # エラーページをチェック
                    if any(phrase in title.lower() for phrase in ['page not found', 'not available', 'error', '404']):
                        logger.warning(f"Error page detected in title: {title}")
                        return None
                    return title
        
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """公開日を抽出"""
        # 日付セレクタ
        date_selectors = [
            '.date',
            '.publish-date',
            '.created-date',
            '.updated-date',
            '.news-date',
            '.article-date',
            'time[datetime]',
            'meta[property="article:published_time"]',
            'meta[property="og:updated_time"]',
            'meta[name="dcterms.created"]',
            'meta[name="dcterms.modified"]'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                # datetime属性をチェック
                datetime_attr = element.get('datetime')
                if datetime_attr:
                    try:
                        parsed_date = date_parser.parse(datetime_attr).replace(tzinfo=self.tz)
                        return parsed_date
                    except:
                        pass
                
                # テキストから日付を抽出
                text = element.get_text(strip=True)
                if text:
                    try:
                        parsed_date = date_parser.parse(text).replace(tzinfo=self.tz)
                        return parsed_date
                    except:
                        pass
        
        # より柔軟な日付抽出を試す
        all_text = soup.get_text()
        date_patterns = [
            r'\b(\d{4}年\d{1,2}月\d{1,2}日)\b',  # 日本語形式
            r'\b(\d{4}/\d{1,2}/\d{1,2})\b',      # YYYY/MM/DD
            r'\b(\d{4}-\d{1,2}-\d{1,2})\b',      # YYYY-MM-DD
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',      # MM/DD/YYYY
            r'\b(\w+ \d{1,2}, \d{4})\b',         # Month DD, YYYY
            r'\b(\d{1,2} \w+ \d{4})\b'           # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, all_text)
            for match in matches:
                try:
                    parsed_date = date_parser.parse(match).replace(tzinfo=self.tz)
                    # 未来の日付を除外
                    if parsed_date.year <= datetime.now().year:
                        logger.info(f"Found date with pattern {pattern}: {match} -> {parsed_date}")
                        return parsed_date
                except:
                    continue
        
        # フォールバック: 現在時刻
        logger.warning("No valid date found, using current time as fallback")
        return datetime.now(self.tz)
    
    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """要約・リード文を抽出"""
        # メタタグから要約を取得
        meta_selectors = [
            'meta[name="description"]',
            'meta[property="og:description"]',
            'meta[name="keywords"]'
        ]
        
        for selector in meta_selectors:
            element = soup.select_one(selector)
            if element:
                summary = element.get('content', '').strip()
                if summary and len(summary) > 20 and "医薬品・医療機器・再生医療等製品の承認審査・安全対策・健康被害救済の3つの業務を行う組織" not in summary:
                    return summary
        
        # コンテンツエリアから要約を抽出
        content_selectors = [
            '.summary',
            '.lead',
            '.excerpt',
            '.abstract',
            '.description',
            '.content p:first-of-type',
            '.main-content p:first-of-type',
            'article p:first-of-type',
            'main p:first-of-type'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                summary = element.get_text(strip=True)
                if summary and len(summary) > 20 and "医薬品・医療機器・再生医療等製品の承認審査・安全対策・健康被害救済の3つの業務を行う組織" not in summary:
                    return summary[:300] + "..." if len(summary) > 300 else summary
        
        # フォールバック: 最初の段落
        paragraphs = soup.select('p')
        for p in paragraphs:
            summary = p.get_text(strip=True)
            if summary and len(summary) > 30 and "医薬品・医療機器・再生医療等製品の承認審査・安全対策・健康被害救済の3つの業務を行う組織" not in summary:
                return summary[:300] + "..." if len(summary) > 300 else summary
        
        return "要約情報がありません。"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """本文の最初の数段落を抽出"""
        content_selectors = [
            '.content',
            '.article-content',
            '.news-content',
            '.main-content',
            '.body',
            'article',
            'main'
        ]
        
        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
        
        if not content_element:
            content_element = soup
        
        # 段落を抽出
        paragraphs = content_element.select('p')
        content_text = ""
        
        for i, p in enumerate(paragraphs[:MAX_PARAGRAPHS_PER_ARTICLE]):
            text = p.get_text(strip=True)
            # 短すぎる段落や一般的な説明文を除外
            if (text and len(text) > 30 and 
                "医薬品・医療機器・再生医療等製品の承認審査・安全対策・健康被害救済の3つの業務を行う組織" not in text and
                "独立行政法人 医薬品医療機器総合機構" not in text and
                "PMDAについて" not in text):
                content_text += text + "\n\n"
        
        if not content_text:
            # フォールバック: 全体のテキストから最初の部分を取得
            all_text = soup.get_text()
            # 一般的な説明文を除外
            lines = all_text.split('\n')
            filtered_lines = []
            for line in lines:
                line = line.strip()
                if (line and len(line) > 30 and 
                    "医薬品・医療機器・再生医療等製品の承認審査・安全対策・健康被害救済の3つの業務を行う組織" not in line and
                    "独立行政法人 医薬品医療機器総合機構" not in line):
                    filtered_lines.append(line)
                    if len(filtered_lines) >= 3:  # 最初の3行まで
                        break
            
            content_text = '\n\n'.join(filtered_lines)
            if len(content_text) > 500:
                content_text = content_text[:500] + "..."
        
        return content_text.strip()
    
    def _is_within_date_range(self, article_date: datetime, cutoff_date: datetime) -> bool:
        """記事が指定期間内かチェック"""
        return article_date >= cutoff_date
