"""
WHO News Scraper
"""
import logging
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pytz

from config import (
    USER_AGENT, REQUEST_TIMEOUT, SLEEP_BETWEEN_REQUESTS, TIMEZONE,
    MAX_PARAGRAPHS_PER_ARTICLE, MAX_ARTICLES_TO_PROCESS
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WHO設定
WHO_BASE_URL = "https://www.who.int"
WHO_NEWS_URL = f"{WHO_BASE_URL}/news"


class WHOScraper:
    """WHOニューススクレイパー"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.tz = pytz.timezone(TIMEZONE)
    
    def scrape_who_news(self, days_back: int) -> List[Dict[str, str]]:
        """
        WHOニュースをスクレイピングし、指定期間内のものを取得
        
        Args:
            days_back: 何日前からの情報を取得するか
            
        Returns:
            記事のリスト
        """
        cutoff_date = self.tz.localize(datetime.now()) - timedelta(days=days_back)
        logger.info(f"Scraping WHO news from {cutoff_date.strftime('%Y-%m-%d')}")
        
        try:
            news_items = self._get_news_items()
            if not news_items:
                logger.warning("No news items found")
                return []
            
            articles = []
            for i, news_item in enumerate(news_items[:MAX_ARTICLES_TO_PROCESS]):
                try:
                    url = news_item['url']
                    date_text = news_item['date_text']
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
                    
                    # 期間内かチェック（日付不明の場合は含める）
                    if date_text == '日付不明' or self._is_within_date_range(published_at, cutoff_date):
                        # 記事の詳細を取得
                        article_detail = self._scrape_article(url)
                        if article_detail:
                            article_detail['published_at'] = published_at
                            article_detail['published_at_iso'] = published_at.isoformat()
                            
                            articles.append(article_detail)
                            logger.info(f"Added article: {article_detail['title'][:50]}... (Date: {date_text})")
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
            logger.error(f"Error in scrape_who_news: {e}")
            return []
    
    def _get_news_items(self) -> List[Dict[str, str]]:
        """ニュース項目のURL一覧を取得（日付情報も含む）- Seleniumを使用して動的コンテンツを取得"""
        try:
            logger.info("Getting WHO news items with Selenium...")
            
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            
            # Seleniumの設定
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'user-agent={USER_AGENT}')
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                driver.get(WHO_NEWS_URL)
                
                # JavaScriptコンテンツの読み込みを待つ（最大20秒）
                logger.info("Waiting for dynamic content to load...")
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.hubfiltering'))
                )
                
                # さらに少し待つ
                time.sleep(3)
                
                # ページのHTMLを取得
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                news_items = []
                
                # 指定された方法でニュース項目を探す
                # 1. <div class="hubfiltering">を探す
                hubfiltering = soup.select_one('div.hubfiltering')
                if not hubfiltering:
                    logger.warning("No hubfiltering div found")
                    return []
                
                logger.info("Found hubfiltering div")
                
                # 2. 動的に読み込まれたリストビューを探す
                # 実際のHTML構造: <div class="list-view vertical-list vertical-list--image">
                listview = hubfiltering.select_one('div.list-view, div[class*="list-view"]')
                if not listview:
                    logger.warning("No list-view found in hubfiltering")
                    return []
                
                logger.info(f"Found list-view: {listview.get('class')}")
                
                # 3. リストアイテムを探す
                # 複数のセレクタを試す
                items = listview.select('div.list-view--item, div[class*="list-view--item"], div.vertical-list-item, div[class*="vertical-list-item"]')
                logger.info(f"Found {len(items)} list items")
                
                if not items:
                    logger.warning("No list items found")
                    return []
                
                for item in items:
                    try:
                        # 4. <a href>でURLを取得
                        link_element = item.select_one('a[href]')
                        if not link_element:
                            logger.warning("No link found in list-view--item")
                            continue
                        
                        href = link_element.get('href')
                        title = link_element.get_text(strip=True)
                        
                        if not href or not title or len(title) < 10:
                            logger.warning(f"Invalid link or title: href={href}, title={title[:50] if title else 'None'}")
                            continue
                        
                        # 5. 日付を抽出: <div class="table-cell info">内の<span class="timestamp">
                        date_text = '日付不明'
                        
                        # パターン1: <div class="table-cell info">内の<span class="timestamp">
                        info_div = item.select_one('div.table-cell.info')
                        if info_div:
                            timestamp = info_div.select_one('span.timestamp')
                            if timestamp:
                                date_text = timestamp.get_text(strip=True)
                                logger.info(f"Found date from table-cell.info timestamp: {date_text}")
                        
                        # パターン2: 直接<span class="timestamp">を探す
                        if date_text == '日付不明':
                            timestamp = item.select_one('span.timestamp, .timestamp, .date, .published, [class*="date"], [class*="time"]')
                            if timestamp:
                                date_text = timestamp.get_text(strip=True)
                                logger.info(f"Found date from direct timestamp: {date_text}")
                        
                        full_url = urljoin(WHO_BASE_URL, href)
                        
                        news_item = {
                            'url': full_url,
                            'date_text': date_text,
                            'title': title
                        }
                        
                        news_items.append(news_item)
                        logger.info(f"Found news item: {full_url} - {title[:50]}... (Date: {date_text})")
                    
                    except Exception as e:
                        logger.error(f"Error processing news item: {e}")
                        continue
                
                logger.info(f"Found {len(news_items)} total news items")
                return news_items
                
            finally:
                driver.quit()
                logger.info("Selenium driver closed")
            
        except Exception as e:
            logger.error(f"Error getting news items: {e}")
            return []
    
    def _parse_date_from_text(self, date_text: str) -> Optional[datetime]:
        """日付テキストからdatetimeオブジェクトを解析"""
        if not date_text or date_text == '日付不明':
            return None
        
        try:
            # 日付テキストをクリーンアップ
            date_text = date_text.strip()
            
            # 様々な日付形式に対応
            # 1. 標準的な日付形式を試す
            date_formats = [
                '%Y-%m-%d',      # 2025-10-08
                '%Y/%m/%d',      # 2025/10/08
                '%d/%m/%Y',      # 08/10/2025
                '%m/%d/%Y',      # 10/08/2025
                '%d-%m-%Y',      # 08-10-2025
                '%m-%d-%Y',      # 10-08-2025
                '%B %d, %Y',     # October 8, 2025
                '%d %B %Y',      # 8 October 2025
                '%Y年%m月%d日',   # 2025年10月8日
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_text, fmt).replace(tzinfo=self.tz)
                    logger.info(f"Successfully parsed date '{date_text}' with format '{fmt}' -> {parsed_date}")
                    return parsed_date
                except ValueError:
                    continue
            
            # 2. dateutilで柔軟に解析を試す
            parsed_date = date_parser.parse(date_text).replace(tzinfo=self.tz)
            logger.info(f"Successfully parsed date '{date_text}' with dateutil -> {parsed_date}")
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
                'related_documents': []
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
                if summary and len(summary) > 20:
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
                if summary and len(summary) > 20:
                    return summary[:300] + "..." if len(summary) > 300 else summary
        
        # フォールバック: 最初の段落
        paragraphs = soup.select('p')
        for p in paragraphs:
            summary = p.get_text(strip=True)
            if summary and len(summary) > 30:
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
            # 短すぎる段落を除外
            if text and len(text) > 30:
                content_text += text + "\n\n"
        
        if not content_text:
            # フォールバック: 全体のテキストから最初の部分を取得
            all_text = soup.get_text()
            lines = all_text.split('\n')
            filtered_lines = []
            for line in lines:
                line = line.strip()
                if line and len(line) > 30:
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
