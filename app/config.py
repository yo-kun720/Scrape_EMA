"""
設定ファイル
"""
import os
from typing import List
from dotenv import load_dotenv

# .envファイルを読み込む（ローカル環境用）
load_dotenv()

# OpenAI設定
MODEL_NAME = "gpt-4o-mini"  # 軽量モデルをデフォルトに

# Streamlit Cloud Secrets対応
try:
    import streamlit as st
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
except (ImportError, FileNotFoundError):
    # Streamlit環境でない場合、または secrets.toml がない場合
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# EMA設定
EMA_BASE_URL = "https://www.ema.europa.eu"
EMA_NEWS_URL = f"{EMA_BASE_URL}/en/news"

# FDA設定
FDA_BASE_URL = "https://www.fda.gov"
FDA_GUIDANCE_URL = f"{FDA_BASE_URL}/regulatory-information/search-fda-guidance-documents"
FDA_CRAWL_DELAY = 30  # FDA robots.txt compliance

# PMDA設定
PMDA_BASE_URL = "https://www.pmda.go.jp"
PMDA_NEWS_URL = f"{PMDA_BASE_URL}/0017.html"

DEFAULT_DAYS_BACK = 7

# スクレイピング設定
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_REQUESTS = 1.5

# タイムゾーン設定
TIMEZONE = "Asia/Tokyo"

# CSSセレクタ（冗長性を持たせる）
NEWS_CARD_SELECTORS = [
    ".ecl-card",
    ".news-card",
    ".article-card",
    "[class*='card']"
]

TITLE_SELECTORS = [
    ".ecl-card__title a",
    ".news-title a",
    "h3 a",
    "h2 a",
    ".title a"
]

DATE_SELECTORS = [
    ".ecl-card__meta",
    ".news-date",
    ".date",
    "[class*='date']",
    "time"
]

CONTENT_SELECTORS = [
    ".ecl-content-block__body p",
    ".news-content p",
    ".article-content p",
    ".content p",
    "main p"
]

# Gmail設定
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

# HTML生成設定
MAX_PARAGRAPHS_PER_ARTICLE = 3
MAX_ARTICLES_TO_PROCESS = 20

# ログ設定
LOG_LEVEL = "INFO"
