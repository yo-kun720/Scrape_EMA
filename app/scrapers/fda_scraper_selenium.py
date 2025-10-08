"""
FDA Guidance Documents Scraper using Selenium for JavaScript-rendered content
"""
import logging
import re
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from config import (
    FDA_BASE_URL, FDA_GUIDANCE_URL, USER_AGENT, REQUEST_TIMEOUT,
    FDA_CRAWL_DELAY, MAX_ARTICLES_TO_PROCESS
)

logger = logging.getLogger(__name__)

class FDAScraperSelenium:
    def __init__(self):
        self.tz = pytz.timezone('Asia/Tokyo')
        self.driver = None
        self._setup_driver()

    def _setup_driver(self):
        """Selenium WebDriverをセットアップ"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # ブラウザを非表示で実行
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={USER_AGENT}')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # ChromeDriverを自動でダウンロード・管理
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 自動化検出を回避
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Selenium WebDriver setup completed")
        except Exception as e:
            logger.error(f"Error setting up Selenium WebDriver: {e}")
            raise

    def __del__(self):
        """デストラクタでWebDriverをクリーンアップ"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def scrape_fda_guidance(self, days_back: int) -> List[Dict[str, str]]:
        """
        FDAガイダンス文書をスクレイピングし、指定期間内のものを取得
        """
        cutoff_date = self.tz.localize(datetime.now()) - timedelta(days=days_back)
        logger.info(f"Scraping FDA guidance documents from {cutoff_date.strftime('%Y-%m-%d')}")

        try:
            # まず検索結果テーブルからURLと日付のペアを取得
            table_data = self._get_guidance_data_from_table()
            
            documents = []
            
            # テーブルから取得したデータを処理
            for url, table_date in table_data:
                try:
                    logger.info(f"Processing table data for: {url}")
                    logger.info(f"Table date: {table_date}")
                    logger.info(f"Cutoff date: {cutoff_date}")
                    
                    # 日付がNoneの場合は個別ページから取得
                    if table_date is None:
                        logger.info("No table date available, scraping individual page...")
                        document = self._scrape_document(url)
                        if document and self._is_within_date_range(document['published_at'], cutoff_date):
                            documents.append(document)
                            logger.info(f"Added document (individual page): {document['title'][:50]}...")
                        else:
                            logger.info(f"Skipped document (individual page): {url}")
                    else:
                        # テーブルの日付で期間判定
                        logger.info(f"Within range: {self._is_within_date_range(table_date, cutoff_date)}")
                        
                        if self._is_within_date_range(table_date, cutoff_date):
                            # テーブルの日付が有効な場合は、個別ページから詳細を取得
                            document = self._scrape_document(url)
                            if document:
                                # テーブルの日付を使用（より正確）
                                document['published_at'] = table_date
                                document['published_at_iso'] = table_date.isoformat()
                                documents.append(document)
                                logger.info(f"Added document with table date: {document['title'][:50]}...")
                            else:
                                logger.warning(f"Failed to parse document details for: {url}")
                        else:
                            logger.info(f"Skipped old document (table date): {url}")
                    
                    logger.info(f"Waiting {FDA_CRAWL_DELAY} seconds (FDA robots.txt compliance)...")
                    time.sleep(FDA_CRAWL_DELAY)
                    
                except Exception as e:
                    logger.error(f"Error processing table data for {url}: {e}")
                    continue
            
            # テーブルからデータが取得できない場合は、従来の方法を使用
            if not documents:
                logger.info("No documents found from table, using fallback method...")
                guidance_urls = self._get_guidance_urls()
                if not guidance_urls:
                    logger.warning("No guidance document URLs found")
                    return []

                for i, url in enumerate(guidance_urls[:MAX_ARTICLES_TO_PROCESS]):
                    try:
                        logger.info(f"Scraping document {i+1}/{min(len(guidance_urls), MAX_ARTICLES_TO_PROCESS)}: {url}")
                        document = self._scrape_document(url)
                        if document:
                            logger.info(f"Document parsed - Title: {document['title'][:50]}...")
                            logger.info(f"Document parsed - Date: {document['published_at']}")
                            logger.info(f"Cutoff date: {cutoff_date}")
                            logger.info(f"Within range: {self._is_within_date_range(document['published_at'], cutoff_date)}")

                            if self._is_within_date_range(document['published_at'], cutoff_date):
                                documents.append(document)
                                logger.info(f"Added document: {document['title'][:50]}...")
                            else:
                                logger.info(f"Skipped old document: {document['title'][:50]}...")
                        else:
                            logger.warning(f"Failed to parse document: {url}")

                        if i < len(guidance_urls) - 1:
                            logger.info(f"Waiting {FDA_CRAWL_DELAY} seconds (FDA robots.txt compliance)...")
                            time.sleep(FDA_CRAWL_DELAY)

                    except Exception as e:
                        logger.error(f"Error scraping document {url}: {e}")
                        continue

            logger.info(f"Successfully scraped {len(documents)} documents within date range")
            return documents

        except Exception as e:
            logger.error(f"Error in scrape_fda_guidance: {e}")
            return []

    def _get_guidance_urls(self) -> List[str]:
        """ガイダンス文書のURL一覧を取得（Selenium使用）"""
        try:
            logger.info("Getting guidance URLs using Selenium...")
            
            # FDAの検索ページにアクセス
            self.driver.get(FDA_GUIDANCE_URL)
            
            # ページの読み込みを待つ
            wait = WebDriverWait(self.driver, 15)
            
            # ページが完全に読み込まれるまで待つ
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)  # JavaScriptの実行を待つ
            except TimeoutException:
                logger.warning("Timeout waiting for page load")
            
            # ページのHTMLを取得
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            urls = []
            
            # 検索結果テーブルから直接URLを抽出
            table_urls = self._extract_urls_from_table(soup)
            if table_urls:
                urls.extend(table_urls)
                logger.info(f"Found {len(table_urls)} URLs from search results table")
            
            # テーブルから取得できない場合は、従来の方法を使用
            if not urls:
                logger.info("No URLs found in table, using fallback method...")
                guidance_selectors = [
                    'a[href*="/guidance-documents/"]',
                    'a[href*="/regulatory-information/"]',
                    '.lcds-section-nav__link',
                    'a[href*="guidance"]',
                    'a[href*="document"]'
                ]
                
                for selector in guidance_selectors:
                    links = soup.select(selector)
                    logger.info(f"Selector '{selector}' found {len(links)} links")
                    
                    for link in links:
                        href = link.get('href')
                        link_text = link.get_text(strip=True)
                        if href and self._is_guidance_document_url(href):
                            full_url = urljoin(FDA_BASE_URL, href)
                            if full_url not in urls:
                                urls.append(full_url)
                                logger.info(f"Found guidance URL: {full_url} - {link_text[:50]}...")
            
            # 特定のガイダンス文書カテゴリページも追加
            category_urls = [
                "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/search-general-and-cross-cutting-topics-guidance-documents",
                "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/advisory-committee-guidance-documents",
                "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/import-and-export-guidance-documents",
                "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cross-cutting-guidance-documents"
            ]
            
            for category_url in category_urls:
                if category_url not in urls:
                    urls.append(category_url)
                    logger.info(f"Added category URL: {category_url}")
            
            # 実際に存在する最近のガイダンス文書URLも追加（事前チェック付き）
            recent_guidance_urls = [
                "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-system-software-guidance-industry-and-food-and-drug",
                "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e20-adaptive-designs-clinical-trials",
                "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-trial-endpoints-development-cancer-drugs-and-biologics-guidance-industry",
                "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/real-world-evidence-program"
            ]
            
            for recent_url in recent_guidance_urls:
                if recent_url not in urls:
                    # URLの存在を事前チェック
                    if self._check_url_exists(recent_url):
                        urls.append(recent_url)
                        logger.info(f"Added valid recent guidance URL: {recent_url}")
                    else:
                        logger.warning(f"Skipped invalid URL: {recent_url}")
            
            logger.info(f"Total guidance URLs found: {len(urls)}")
            return urls

        except Exception as e:
            logger.error(f"Error getting guidance URLs with Selenium: {e}")
            return []

    def _is_guidance_document_url(self, url: str) -> bool:
        """ガイダンス文書のURLかどうか判定"""
        if not url:
            return False

        # まず、ガイダンス文書のパターンをチェック
        guidance_patterns = [
            r'/search-fda-guidance-documents/',  # 最も重要なパターン
            r'/guidance-documents/', 
            r'/regulatory-information/search-fda-guidance-documents/',
            r'/drugs/guidance-compliance-regulatory-information/',
            r'/medical-devices/device-regulation-and-guidance/',
            r'/food/guidance-documents-regulatory-information/',
            r'/vaccines/guidance-documents/', 
            r'/tobacco-products/guidance-documents/',
            r'/radiation-emitting-products/guidance-documents/',
            r'/biologics/guidance-documents/', 
            r'/animal-veterinary/guidance-documents/'
        ]
        
        # ガイダンス文書のパターンに一致するかチェック
        is_guidance = any(re.search(pattern, url, re.I) for pattern in guidance_patterns)
        
        if not is_guidance:
            return False
        
        # ガイダンス文書でも除外すべきパターン
        exclude_patterns = [
            r'/apology_objects/', r'/user/', r'/admin/', r'/comment/',
            r'/filter/', r'/node/', r'/file/', r'/taxonomy/', r'\.pdf$',
            r'javascript:', r'mailto:', r'#$', r'^/$', r'/media/', r'/images/',
            r'/css/', r'/js/', r'/sites/', r'/themes/', r'/modules/', r'/libraries/',
            r'/core/', r'/profiles/', r'/contact$', r'/about$', r'/news$',
            r'^/search$',  # /search のみを除外（/search-fda-guidance-documents/ は除外しない）
        ]
        
        if any(re.search(pattern, url, re.I) for pattern in exclude_patterns):
            return False
        
        return True

    def _scrape_document(self, url: str) -> Optional[Dict[str, str]]:
        """個別ガイダンス文書をスクレイピング（Selenium使用）"""
        try:
            logger.info(f"Scraping document with Selenium: {url}")
            
            # ページにアクセス
            self.driver.get(url)
            
            # ページの読み込みを待つ
            wait = WebDriverWait(self.driver, 10)
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except TimeoutException:
                logger.warning(f"Timeout loading page: {url}")
            
            # ページのHTMLを取得
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            title = self._extract_title(soup)
            if not title:
                logger.warning(f"No title found for: {url}")
                return None

            published_at = self._extract_date(soup)
            if not published_at:
                logger.warning(f"No date found for: {url}")
                return None

            content = self._extract_content(soup)
            documents = []  # FDA guidance documents often link to PDFs directly

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
            logger.error(f"Error scraping document {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """タイトルを抽出"""
        selectors = [
            'h1.fda-page-title',
            'h1.page-title',
            'h1',
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
                    # Page Not Foundエラーをチェック
                    if any(phrase in title.lower() for phrase in ['page not found', 'not available', 'error', '404']):
                        logger.warning(f"Page Not Found detected in title: {title}")
                        return None
                    return title
        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """公開日を抽出"""
        # まず、FDAの検索結果テーブルから日付を探す
        table_selectors = [
            'table tr td:nth-child(3)',  # Issue Date列
            'table tr td[data-label*="Issue"]',
            'table tr td[data-label*="Date"]',
            '.issue-date',
            '.date-issued'
        ]
        
        for selector in table_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and re.match(r'\d{1,2}/\d{1,2}/\d{4}', text):
                    try:
                        parsed_date = date_parser.parse(text).replace(tzinfo=self.tz)
                        if parsed_date.year <= datetime.now().year:  # 未来の日付を除外
                            logger.info(f"Found date in table: {text} -> {parsed_date}")
                            return parsed_date
                    except:
                        continue

        # 標準的な日付セレクタ
        selectors = [
            '.field--name-field-date', '.field--name-created', '.date-display-single',
            '.field--name-field-published-date', 'time[datetime]', '.published-date',
            '.field--name-field-issue-date', '.issue-date',
            'meta[property="article:published_time"]', 'meta[property="og:updated_time"]',
            '.date', '.publish-date', '.created-date', '.updated-date',
            '[class*="date"]', '[class*="time"]'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                datetime_attr = element.get('datetime')
                if datetime_attr:
                    try:
                        parsed_date = date_parser.parse(datetime_attr).replace(tzinfo=self.tz)
                        if parsed_date.year <= datetime.now().year:  # 未来の日付を除外
                            return parsed_date
                    except:
                        pass

                text = element.get_text(strip=True)
                if text:
                    try:
                        parsed_date = date_parser.parse(text).replace(tzinfo=self.tz)
                        if parsed_date.year <= datetime.now().year:  # 未来の日付を除外
                            return parsed_date
                    except:
                        pass

        # より柔軟な日付抽出を試す（MM/DD/YYYY形式を優先）
        all_text = soup.get_text()
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY形式を優先
            r'\b(\d{4}-\d{1,2}-\d{1,2})\b',
            r'\b(\w+ \d{1,2}, \d{4})\b',
            r'\b(\d{1,2} \w+ \d{4})\b'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, all_text)
            for match in matches:
                try:
                    parsed_date = date_parser.parse(match).replace(tzinfo=self.tz)
                    if parsed_date.year <= datetime.now().year:  # 未来の日付を除外
                        # 最近の日付（過去2年以内）を優先
                        if parsed_date.year >= datetime.now().year - 2:
                            logger.info(f"Found date with pattern {pattern}: {match} -> {parsed_date}")
                            return parsed_date
                except:
                    continue

        # フォールバック: 現在時刻
        logger.warning("No valid date found, using current time as fallback")
        return datetime.now(self.tz)

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """本文を抽出"""
        selectors = [
            '.field--name-body',
            '.region-content',
            '.node__content',
            '.block-system-main-block',
            'div[property="schema:text"]',
            'div.content'
        ]
        
        paragraphs = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for p in elements:
                    text = p.get_text(separator='\n', strip=True)
                    if text and len(text) > 50:
                        paragraphs.append(text)
                if paragraphs:
                    break

        if not paragraphs:
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    paragraphs.append(text)

        return '\n\n'.join(paragraphs) if paragraphs else "Content not available"

    def _is_within_date_range(self, article_date: datetime, cutoff_date: datetime) -> bool:
        """記事が指定期間内かチェック"""
        return article_date >= cutoff_date

    def _extract_urls_from_table(self, soup: BeautifulSoup) -> List[str]:
        """検索結果テーブルからURLを抽出"""
        urls = []
        try:
            # テーブル行を探す
            table_rows = soup.select('table tr, tbody tr, .table tr')
            logger.info(f"Found {len(table_rows)} table rows")
            
            for row in table_rows:
                # Summary列（最初の列）のリンクを探す
                summary_cell = row.select_one('td:first-child, th:first-child')
                if summary_cell:
                    link = summary_cell.select_one('a')
                    if link:
                        href = link.get('href')
                        link_text = link.get_text(strip=True)
                        if href and self._is_guidance_document_url(href):
                            full_url = urljoin(FDA_BASE_URL, href)
                            if full_url not in urls:
                                urls.append(full_url)
                                logger.info(f"Found table URL: {full_url} - {link_text[:50]}...")
            
            # テーブルが見つからない場合は、より一般的なセレクタを試す
            if not urls:
                logger.info("No table found, trying alternative selectors...")
                # 検索結果のリンクを探す
                result_links = soup.select('a[href*="/regulatory-information/search-fda-guidance-documents/"]')
                for link in result_links:
                    href = link.get('href')
                    link_text = link.get_text(strip=True)
                    if href and self._is_guidance_document_url(href) and 'search-fda-guidance-documents' in href:
                        full_url = urljoin(FDA_BASE_URL, href)
                        if full_url not in urls:
                            urls.append(full_url)
                            logger.info(f"Found result URL: {full_url} - {link_text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error extracting URLs from table: {e}")
        
        return urls

    def _get_guidance_data_from_table(self) -> List[tuple]:
        """検索結果テーブルからURLと日付のペアを取得"""
        table_data = []
        try:
            logger.info("Getting guidance data from search results table...")
            
            # FDAの検索ページにアクセス
            self.driver.get(FDA_GUIDANCE_URL)
            
            # ページの読み込みを待つ
            wait = WebDriverWait(self.driver, 15)
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)  # JavaScriptの実行を待つ
            except TimeoutException:
                logger.warning("Timeout waiting for page load")
            
            # ページのHTMLを取得
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 実際のHTML構造に基づいて<div class="lcds-datatable">内の<tbody>を探す
            datatable = soup.select_one('div.lcds-datatable')
            if not datatable:
                logger.warning("No lcds-datatable found, trying alternative selectors...")
                # フォールバック: 一般的なテーブル行を探す
                table_rows = soup.select('table tr, tbody tr, .table tr')
            else:
                tbody = datatable.select_one('tbody')
                if not tbody:
                    logger.warning("No tbody found in lcds-datatable, trying alternative selectors...")
                    table_rows = datatable.select('tr')
                else:
                    table_rows = tbody.select('tr')
            
            logger.info(f"Found {len(table_rows)} table rows")
            
            for idx, row in enumerate(table_rows):
                try:
                    # デバッグ: 行の構造を確認
                    row_text = row.get_text(strip=True)[:100]
                    logger.info(f"Processing row {idx+1}: {row_text}...")
                    
                    # 全てのtd要素を取得
                    all_tds = row.select('td')
                    logger.info(f"Row {idx+1} has {len(all_tds)} td elements")
                    
                    # 各tdの内容を確認
                    for td_idx, td in enumerate(all_tds):
                        td_classes = td.get('class', [])
                        td_tabindex = td.get('tabindex')
                        td_text = td.get_text(strip=True)[:50]
                        logger.info(f"  TD {td_idx+1}: classes={td_classes}, tabindex={td_tabindex}, text={td_text}")
                    
                    # 日付を抽出（<td class="sorting_1">）
                    date_element = row.select_one('td.sorting_1')
                    if not date_element:
                        logger.info(f"Row {idx+1}: No td.sorting_1 found, trying date pattern search...")
                        # フォールバック: 他の日付セルを探す
                        date_cells = row.select('td')
                        date_element = None
                        for cell in date_cells:
                            cell_text = cell.get_text(strip=True)
                            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                                date_element = cell
                                logger.info(f"Row {idx+1}: Found date by pattern: {cell_text}")
                                break
                        
                        if not date_element:
                            logger.info(f"Row {idx+1}: No date found, skipping")
                            continue
                    else:
                        logger.info(f"Row {idx+1}: Found td.sorting_1 with date: {date_element.get_text(strip=True)}")
                    
                    date_text = date_element.get_text(strip=True)
                    if not date_text:
                        logger.info(f"Row {idx+1}: Date text is empty, skipping")
                        continue
                    
                    # URLを抽出（<td tabindex="0">内の<a href>）
                    tabindex_cell = row.select_one('td[tabindex="0"]')
                    if not tabindex_cell:
                        logger.info(f"Row {idx+1}: No td[tabindex='0'] found, trying link search...")
                        # フォールバック: 他のリンクセルを探す
                        link_cells = row.select('td a[href]')
                        if not link_cells:
                            logger.info(f"Row {idx+1}: No links found, skipping")
                            continue
                        url_element = link_cells[0]
                        logger.info(f"Row {idx+1}: Found link by fallback: {url_element.get('href')}")
                    else:
                        logger.info(f"Row {idx+1}: Found td[tabindex='0']")
                        url_element = tabindex_cell.select_one('a[href]')
                        if not url_element:
                            logger.info(f"Row {idx+1}: No link in tabindex cell, skipping")
                            continue
                        logger.info(f"Row {idx+1}: Found link in tabindex cell: {url_element.get('href')}")
                    
                    href = url_element.get('href')
                    link_text = url_element.get_text(strip=True)
                    
                    if href and self._is_guidance_document_url(href):
                        full_url = urljoin(FDA_BASE_URL, href)
                        
                        # 日付を解析
                        try:
                            parsed_date = date_parser.parse(date_text).replace(tzinfo=self.tz)
                            table_data.append((full_url, parsed_date))
                            logger.info(f"✓ Successfully added table data: {full_url} - {parsed_date} - {link_text[:50]}...")
                        except Exception as e:
                            logger.warning(f"Failed to parse date '{date_text}' for {full_url}: {e}")
                            # 日付が解析できない場合は個別ページから取得
                            table_data.append((full_url, None))
                    else:
                        logger.info(f"Row {idx+1}: URL not a guidance document: {href}")
                
                except Exception as e:
                    logger.error(f"Error processing table row {idx+1}: {e}")
                    continue
            
            # テーブルが見つからない場合は、より一般的なセレクタを試す
            if not table_data:
                logger.info("No table data found, trying alternative selectors...")
                # 検索結果のリンクを探す
                result_links = soup.select('a[href*="/regulatory-information/search-fda-guidance-documents/"]')
                for link in result_links:
                    href = link.get('href')
                    link_text = link.get_text(strip=True)
                    if href and self._is_guidance_document_url(href) and 'search-fda-guidance-documents' in href:
                        full_url = urljoin(FDA_BASE_URL, href)
                        # 日付は個別ページから取得する必要がある
                        table_data.append((full_url, None))
                        logger.info(f"Found result URL (no table date): {full_url} - {link_text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error getting guidance data from table: {e}")
        
        logger.info(f"Found {len(table_data)} guidance documents from table")
        return table_data

    def _extract_date_from_table_row(self, row: BeautifulSoup, url: str) -> Optional[datetime]:
        """テーブル行から日付を抽出"""
        try:
            # Issue Date列（3番目の列）を探す
            date_cell = row.select_one('td:nth-child(3), th:nth-child(3)')
            if date_cell:
                date_text = date_cell.get_text(strip=True)
                if date_text and re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_text):
                    try:
                        parsed_date = date_parser.parse(date_text).replace(tzinfo=self.tz)
                        logger.info(f"Found table date for {url}: {date_text} -> {parsed_date}")
                        return parsed_date
                    except Exception as e:
                        logger.warning(f"Failed to parse table date '{date_text}': {e}")
            
            # 他の列も試す
            for i in range(1, 8):  # 最大7列までチェック
                cell = row.select_one(f'td:nth-child({i}), th:nth-child({i})')
                if cell:
                    cell_text = cell.get_text(strip=True)
                    if cell_text and re.match(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                        try:
                            parsed_date = date_parser.parse(cell_text).replace(tzinfo=self.tz)
                            logger.info(f"Found date in column {i} for {url}: {cell_text} -> {parsed_date}")
                            return parsed_date
                        except Exception as e:
                            logger.warning(f"Failed to parse date '{cell_text}' in column {i}: {e}")
            
        except Exception as e:
            logger.error(f"Error extracting date from table row for {url}: {e}")
        
        return None

    def _check_url_exists(self, url: str) -> bool:
        """URLの存在をチェック"""
        try:
            # ヘッドリクエストでURLの存在を確認
            response = self.driver.execute_script("""
                var xhr = new XMLHttpRequest();
                xhr.open('HEAD', arguments[0], false);
                xhr.send();
                return xhr.status;
            """, url)
            
            if response == 200:
                return True
            else:
                logger.warning(f"URL check failed for {url}: status {response}")
                return False
        except Exception as e:
            logger.warning(f"Error checking URL {url}: {e}")
            return False
