# 開発ドキュメント

## 📋 プロジェクト概要

主要な規制機関（EMA, FDA, PMDA, WHO）の最新ニュースやガイダンス文書を自動でスクレイピングし、ChatGPTを用いて要約、モバイルフレンドリーなHTML形式で提供するStreamlitアプリケーション。

---

## 🏗️ アーキテクチャ

### ディレクトリ構造

```
Scrape_EMA/
├── app/
│   ├── config.py                    # 設定ファイル（APIキー、URL、セレクタ等）
│   ├── streamlit_app.py             # メインアプリ（トップページ）
│   ├── pages/                       # 各機関のページ
│   │   ├── 1_EMA_News.py           # EMAニュース
│   │   ├── 2_FDA_Guidance.py       # FDAガイダンス
│   │   ├── 3_PMDA_News.py          # PMDA新着情報
│   │   └── 4_WHO_News.py           # WHOニュース
│   ├── scrapers/                    # スクレイピングモジュール
│   │   ├── ema_scraper.py          # EMAスクレイパー（requests + BeautifulSoup）
│   │   ├── fda_scraper_selenium.py # FDAスクレイパー（Selenium）
│   │   ├── pmda_scraper.py         # PMDAスクレイパー（requests + BeautifulSoup）
│   │   └── who_scraper.py          # WHOスクレイパー（Selenium）
│   └── shared/                      # 共通モジュール
│       ├── gpt_html.py             # OpenAI API連携・HTML生成
│       └── pdf_summarizer.py       # PDF要約
├── .env                             # 環境変数（APIキー）※Gitignore
├── .streamlit/
│   ├── config.toml                 # Streamlit設定
│   └── secrets.toml.example        # Secrets設定例
├── launcher.py                      # デスクトップランチャー
├── create_app.sh                   # macOSアプリ作成スクリプト
└── packages.txt                    # Streamlit Cloud用システムパッケージ
```

---

## 🔑 重要な設定

### 環境変数

**`.env`ファイル:**
```bash
OPENAI_API_KEY=sk-proj-...
```

**Streamlit Cloud Secrets:**
```toml
OPENAI_API_KEY = "sk-proj-..."
```

### OpenAI設定

- **モデル**: `gpt-4o-mini`（`app/config.py`で設定）
- **Temperature**: `0.3`（指示に従いやすく）
- **Max Tokens**: `4000`

---

## 🕷️ スクレイピング仕様

### EMA（European Medicines Agency）

- **URL**: https://www.ema.europa.eu/en/news
- **方法**: `requests` + `BeautifulSoup`
- **特徴**: 
  - Reflection paper等の関連文書をダウンロード・要約
  - 静的ページなので高速

### FDA（Food and Drug Administration）

- **URL**: https://www.fda.gov/regulatory-information/search-fda-guidance-documents
- **方法**: `Selenium` + `BeautifulSoup`
- **特徴**:
  - JavaScriptで動的に読み込まれるテーブルをスクレイピング
  - `<div class="lcds-datatable">`内の`<tbody>`から情報取得
  - Issue Dateで期間フィルタリング
  - robots.txt遵守（30秒クロール遅延）

### PMDA（医薬品医療機器総合機構）

- **URL**: https://www.pmda.go.jp/0017.html
- **方法**: `requests` + `BeautifulSoup`
- **特徴**:
  - `<ul class="list__news">`から情報取得
  - `<p class="date">`で日付判定
  - `<p class="title">`でタイトル取得
  - `<p class="category category01">`でカテゴリ取得
  - 「採用」「調達」カテゴリは除外
  - 日本語日付パース（例：2025年10月8日）

### WHO（World Health Organization）

- **URL**: https://www.who.int/news
- **方法**: `Selenium` + `BeautifulSoup`
- **特徴**:
  - JavaScriptで動的に読み込まれるコンテンツ
  - `<div class="hubfiltering">`内の`<div class="list-view">`から取得
  - `<span class="timestamp">`で日付取得
  - WebDriverWait + 3秒待機で動的コンテンツ読み込み

---

## 🤖 AI要約の仕様

### プロンプト設計

**【最重要ルール】**
1. 記事タイトル（h2タグ）のみ英語のまま
2. それ以外のすべての内容は必ず日本語で記載
3. 英語の原文をそのままコピーすることは絶対禁止

### システムメッセージ

```
あなたは日本語の技術文書ライターです。
【最重要ルール】記事タイトル（h2タグ）のみ英語のまま、
それ以外のすべての内容（公開日、要点リスト、詳細要約、説明文、ラベル）は
必ず日本語で記載してください。
```

### HTML生成仕様

- **最大幅**: 1200px（モバイルフレンドリー）
- **インラインCSS**: 外部依存なし
- **構造**:
  - h1: 全体タイトル
  - h2: 各記事タイトル（英語）
  - h3: セクション見出し（日本語）
  - ul/li: 要点リスト（日本語）
  - p: 詳細要約（日本語）
- **出典表記**: フッターに自動挿入

---

## 🐛 既知の問題と解決策

### 1. OpenAI APIキーエラー

**問題**: `HTTP/1.1 401 Unauthorized`

**原因**:
- `.env`ファイルが読み込まれていない
- APIキーにタイポがある

**解決策**:
- `app/config.py`と`app/shared/gpt_html.py`に`load_dotenv()`を追加済み
- Streamlit Cloud Secrets対応済み

### 2. Seleniumが動作しない

**問題**: `ChromeDriver not found`

**解決策**:
- `webdriver-manager`が自動的にダウンロード
- Streamlit Cloud用に`packages.txt`でChromiumを指定

### 3. 日付パースエラー

**問題**: 日付形式が機関ごとに異なる

**解決策**:
- 複数の日付フォーマットを試行
- `python-dateutil`でロバストなパース
- Asia/Tokyoタイムゾーンで統一

### 4. 要約が英語のまま

**問題**: ChatGPTが英語で要約を返す

**解決策**:
- プロンプトを大幅に強化
- システムメッセージで明示的に指示
- Temperature を 0.3 に下げて指示に従いやすく

---

## 🚀 デプロイ方法

### ローカル実行

```bash
# 方法1: デスクトップアプリ（macOS）
./create_app.sh
# → デスクトップに「規制機関ニュース要約.app」が作成される

# 方法2: Pythonランチャー
python3 launcher.py

# 方法3: 従来の方法
source venv/bin/activate
cd app
streamlit run streamlit_app.py
```

### Streamlit Cloud

1. https://share.streamlit.io/ にアクセス
2. GitHubアカウントでサインイン
3. "New app" をクリック
4. リポジトリ: `yo-kun720/Scrape_EMA`
5. Branch: `main`
6. Main file path: `app/streamlit_app.py`
7. Secrets設定:
   ```toml
   OPENAI_API_KEY = "sk-proj-..."
   ```

---

## 📊 パフォーマンス

### スクレイピング速度

- **EMA**: 数秒〜数十秒（静的ページ）
- **FDA**: 1〜2分（Selenium使用）
- **PMDA**: 数秒〜数十秒（静的ページ）
- **WHO**: 1〜2分（Selenium使用）

### OpenAI API

- **応答時間**: 10〜30秒
- **リトライ**: 自動リトライ機能あり
- **コスト**: gpt-4o-miniで低コスト

---

## 🔧 メンテナンス

### CSSセレクタの更新

各機関のWebサイトが更新された場合、`app/config.py`のセレクタを修正：

```python
NEWS_CARD_SELECTORS = {
    'ema': 'div.views-row',
    'fda': 'tbody tr',
    'pmda': 'ul.list__news li',
    'who': 'div.list-view--item'
}
```

### 日付フォーマットの追加

新しい日付フォーマットが必要な場合、各スクレイパーの`_parse_date`メソッドを修正。

---

## 📚 依存パッケージ

主要パッケージ（`requirements.txt`）:

- `streamlit`: Web UI
- `requests`: HTTP通信
- `beautifulsoup4`: HTMLパース
- `selenium`: 動的ページスクレイピング
- `webdriver-manager`: ChromeDriver自動管理
- `openai`: OpenAI API
- `python-dateutil`: 日付パース
- `pytz`: タイムゾーン処理
- `PyPDF2`: PDF処理
- `python-dotenv`: 環境変数管理

---

## 🎯 今後の拡張案

1. **メール送信機能の有効化**
   - Gmail API認証の完了
   - 自動送信スケジュール

2. **データベース連携**
   - 過去の記事を保存
   - 重複チェック

3. **通知機能**
   - 新着記事のプッシュ通知
   - Slack/Discord連携

4. **フィルタリング機能**
   - キーワード検索
   - カテゴリフィルタ

5. **他の規制機関の追加**
   - Health Canada
   - TGA (Australia)
   - Swissmedic

---

## 📞 トラブルシューティング

### ログの確認

```bash
# ターミナルでログを確認
tail -f app/logs/*.log

# または、Streamlitアプリのログを直接確認
```

### デバッグモード

`app/config.py`でログレベルを変更:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📅 開発履歴

- **2025-10-08**: プロジェクト完成
  - 4機関対応完了
  - 日本語要約機能実装
  - デスクトップアプリ化
  - Streamlit Cloud対応
  - GitHubへプッシュ

---

## 🔗 リンク

- **GitHub**: https://github.com/yo-kun720/Scrape_EMA
- **Streamlit Cloud**: （デプロイ後にURLを追加）

---

このドキュメントは、次回Cursorを開いた時の参考資料として使用してください。
