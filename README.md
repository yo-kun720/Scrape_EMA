# 📰 規制機関ニュース要約アプリ

主要な規制機関（EMA, FDA, PMDA, WHO）の最新ニュースやガイダンス文書を自動でスクレイピングし、ChatGPTを用いて要約、モバイルフレンドリーなHTML形式で提供するStreamlitアプリケーションです。

## 🎯 機能

- **多機関対応**: EMA, FDA, PMDA, WHOの4つの規制機関を監視
- **自動スクレイピング**: 各機関のサイトから直近7日間の記事を自動取得
- **AI生成HTML**: OpenAI APIでモバイルフレンドリーなHTMLを生成
- **日本語要約**: 記事タイトルは英語のまま、内容は日本語で要約
- **Streamlit UI**: マルチページの直感的なWebインターフェース
- **出典表記**: 各機関の利用規約に準拠した出典表記を自動挿入

## 🚀 クイックスタート

### デプロイ方法

#### Streamlit Cloudでデプロイ（推奨）

1. **GitHubリポジトリの準備**
   - このリポジトリをGitHubにプッシュ済みであることを確認

2. **Streamlit Cloudにアクセス**
   - [https://share.streamlit.io/](https://share.streamlit.io/) にアクセス
   - GitHubアカウントでサインイン

3. **アプリをデプロイ**
   - "New app" をクリック
   - リポジトリ: `yo-kun720/Scrape_EMA`
   - Branch: `main`
   - Main file path: `app/streamlit_app.py`

4. **Secretsを設定**
   - デプロイ後、"Settings" → "Secrets" に移動
   - 以下を追加：
     ```toml
     OPENAI_API_KEY = "your_openai_api_key_here"
     ```

5. **デプロイ完了**
   - 自動的にアプリがビルド・デプロイされます
   - 公開URLが発行されます

### デスクトップアプリとして起動（macOS）

最も簡単な方法：

```bash
# デスクトップアプリを作成
./create_app.sh
```

これで、デスクトップに「**規制機関ニュース要約.app**」が作成されます。
ダブルクリックするだけで起動できます！

### 1. ローカル環境セットアップ

```bash
# 仮想環境を作成・有効化
python -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate     # Windows

# 依存関係をインストール
pip install -r requirements.txt
```

### 2. 環境変数設定

`.env`ファイルを作成し、OpenAI APIキーを設定：

```bash
cp .env.example .env
# .envファイルを編集してOPENAI_API_KEYを設定
```

### 3. Gmail API設定

1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. Gmail APIを有効化
3. OAuth 2.0認証情報を作成
4. `credentials.json`をダウンロードしてプロジェクトルートに配置

### 4. アプリケーション起動

```bash
streamlit run app/streamlit_app.py
```

## 📋 使用方法

1. **機関選択**: 左側のサイドバーから監視したい規制機関を選択
2. **期間設定**: 取得する記事の期間を設定（デフォルト: 7日間）
3. **記事取得**: 「記事を取得・要約」ボタンをクリック
4. **自動処理**: スクレイピング → ChatGPT要約 → HTML生成が自動実行
5. **結果確認**: 生成されたHTMLをプレビュー・ダウンロード可能

## 🏗️ プロジェクト構成

```
Scrape_EMA/
├── app/
│   ├── __init__.py
│   ├── config.py                    # 設定ファイル
│   ├── streamlit_app.py             # メインStreamlitアプリ
│   ├── pages/                       # 各機関のページ
│   │   ├── 1_EMA_News.py           # EMAニュース
│   │   ├── 2_FDA_Guidance.py       # FDAガイダンス
│   │   ├── 3_PMDA_News.py          # PMDA新着情報
│   │   └── 4_WHO_News.py           # WHOニュース
│   ├── scrapers/                    # スクレイピングモジュール
│   │   ├── ema_scraper.py          # EMAスクレイパー
│   │   ├── fda_scraper_selenium.py # FDAスクレイパー（Selenium）
│   │   ├── pmda_scraper.py         # PMDAスクレイパー
│   │   └── who_scraper.py          # WHOスクレイパー
│   └── shared/                      # 共通モジュール
│       ├── gpt_html.py             # OpenAI API連携
│       └── pdf_summarizer.py       # PDF要約
├── requirements.txt                 # 依存関係
├── .env.example                    # 環境変数テンプレート
├── credentials.json                # Gmail API認証情報（要配置）
└── README.md
```

## ⚙️ 設定

### 主要設定（app/config.py）

- `MODEL_NAME`: OpenAIモデル（デフォルト: gpt-3.5-turbo）
- `DEFAULT_DAYS_BACK`: デフォルト取得期間（7日）
- `SLEEP_BETWEEN_REQUESTS`: リクエスト間隔（1.5秒）
- `REQUEST_TIMEOUT`: リクエストタイムアウト（30秒）

### 環境変数

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## 🔧 技術仕様

### 使用技術

- **Python 3.10+**
- **Streamlit**: マルチページWeb UI
- **requests + BeautifulSoup**: 静的ページスクレイピング
- **Selenium + WebDriverManager**: 動的ページスクレイピング
- **OpenAI API**: HTML生成（gpt-4o-mini）
- **python-dateutil + pytz**: 日時処理

### 対応機関・スクレイピング仕様

- **EMA**: https://www.ema.europa.eu/en/news
- **FDA**: https://www.fda.gov/regulatory-information/search-fda-guidance-documents（Selenium使用）
- **PMDA**: https://www.pmda.go.jp/0017.html
- **WHO**: https://www.who.int/news（Selenium使用）

### 共通仕様

- **User-Agent**: 明示的なブラウザ識別子
- **レート制限**: 1.5秒間隔でリクエスト
- **エラー処理**: 個別記事の失敗時も継続処理
- **日時処理**: Asia/Tokyoタイムゾーンで統一
- **robots.txt遵守**: 各サイトの利用規約に準拠

### HTML生成仕様

- **モバイルフレンドリー**: レスポンシブデザイン（最大幅1200px）
- **インラインCSS**: 外部依存なし
- **日本語要約**: 記事タイトルは英語、内容は日本語で要約
- **出典表記**: フッターに自動挿入
- **安全なリンク**: target="_blank" rel="noopener"

## 🛡️ セキュリティ・ポリシー

- **個人利用目的**: 商用利用は想定外
- **出典表記**: 各機関の利用規約に準拠
- **サーバ負荷配慮**: 適切な間隔でリクエスト
- **データ最小化**: 画像・ロゴは取得しない
- **カテゴリフィルタリング**: PMDAでは「採用」「調達」を除外

## 🐛 トラブルシューティング

### よくある問題

1. **OpenAI APIキーエラー**
   ```
   ❌ OPENAI_API_KEY環境変数が設定されていません
   ```
   → `.env`ファイルにAPIキーを設定

2. **Gmail認証エラー**
   ```
   FileNotFoundError: credentials.json not found
   ```
   → Google Cloud Consoleから認証情報をダウンロード

3. **スクレイピングエラー**
   ```
   Error scraping article
   ```
   → ネットワーク接続とEMAサイトの状態を確認

### ログ確認

```bash
# 詳細ログを確認
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
streamlit run app/streamlit_app.py
```

## 📝 ライセンス

このプロジェクトは個人利用目的です。各規制機関（EMA, FDA, PMDA, WHO）の利用規約に従ってご利用ください。

## 🤝 貢献

バグ報告や機能要望は、GitHubのIssuesでお知らせください。

## 📞 サポート

技術的な問題については、ログファイルとエラーメッセージを添えてお問い合わせください。