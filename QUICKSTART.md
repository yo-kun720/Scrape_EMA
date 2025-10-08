# ⚡ クイックスタートガイド

次回Cursorを開いた時に、このファイルを参照してください。

---

## 🚀 アプリの起動方法

### 方法1: デスクトップアプリ（最も簡単）

```bash
# デスクトップアプリを作成（初回のみ）
./create_app.sh

# デスクトップの「規制機関ニュース要約.app」をダブルクリック
```

### 方法2: コマンドライン

```bash
source venv/bin/activate
cd app
streamlit run streamlit_app.py
```

### 方法3: Pythonランチャー

```bash
python3 launcher.py
```

---

## 📝 重要なファイル

### 設定ファイル

- **`app/config.py`**: すべての設定（URL、セレクタ、APIキー等）
- **`.env`**: OpenAI APIキー（機密情報）
- **`.streamlit/config.toml`**: Streamlit設定

### スクレイパー

- **`app/scrapers/ema_scraper.py`**: EMA（静的ページ）
- **`app/scrapers/fda_scraper_selenium.py`**: FDA（Selenium）
- **`app/scrapers/pmda_scraper.py`**: PMDA（静的ページ）
- **`app/scrapers/who_scraper.py`**: WHO（Selenium）

### AI要約

- **`app/shared/gpt_html.py`**: OpenAI API連携
  - モデル: `gpt-4o-mini`
  - Temperature: `0.3`
  - タイトルは英語、内容は日本語

---

## 🔧 よくある修正

### 1. OpenAI APIキーの変更

```bash
# .envファイルを編集
nano .env

# または
echo 'OPENAI_API_KEY=新しいキー' > .env
```

### 2. スクレイピング対象期間の変更

`app/config.py`:
```python
DEFAULT_DAYS_BACK = 7  # この値を変更
```

### 3. CSSセレクタの修正

各機関のWebサイトが変更された場合、`app/config.py`を修正:

```python
NEWS_CARD_SELECTORS = {
    'ema': 'div.views-row',      # EMA
    'fda': 'tbody tr',            # FDA
    'pmda': 'ul.list__news li',  # PMDA
    'who': 'div.list-view--item' # WHO
}
```

### 4. OpenAIモデルの変更

`app/config.py`:
```python
MODEL_NAME = "gpt-4o-mini"  # または "gpt-4", "gpt-3.5-turbo" など
```

---

## 🐛 トラブルシューティング

### エラー: `OPENAI_API_KEY environment variable is required`

**解決策**:
```bash
# .envファイルを確認
cat .env

# APIキーが正しいか確認
# 必要に応じて修正
```

### エラー: `ChromeDriver not found`

**解決策**:
```bash
# webdriver-managerが自動的にダウンロードするまで待つ
# または、手動でインストール
pip install --upgrade webdriver-manager
```

### エラー: `No news items found`

**解決策**:
- 対象期間を広げる（例：14日間）
- CSSセレクタが正しいか確認
- 機関のWebサイトが変更されていないか確認

---

## 📦 Git操作

### 変更をコミット

```bash
git add .
git commit -m "メッセージ"
git push origin main
```

### 最新版を取得

```bash
git pull origin main
```

---

## 🌐 デプロイ

### Streamlit Cloud

1. https://share.streamlit.io/
2. "New app"
3. Repository: `yo-kun720/Scrape_EMA`
4. Main file: `app/streamlit_app.py`
5. Secrets: `OPENAI_API_KEY = "..."`

---

## 📞 サポート

### ログの確認

```bash
# Streamlitアプリのログを確認
# ターミナルに表示されます
```

### デバッグ

`app/config.py`でログレベルを変更:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 💡 Tips

1. **スクレイピングが遅い場合**
   - `SLEEP_BETWEEN_REQUESTS`を短くする（ただし、サーバー負荷に注意）
   - `MAX_ARTICLES_TO_PROCESS`を減らす

2. **要約が英語の場合**
   - `app/shared/gpt_html.py`のプロンプトを確認
   - Temperatureを下げる（現在0.3）

3. **HTMLの幅を変更したい場合**
   - `app/shared/gpt_html.py`の`max-width: 1200px`を変更

---

このガイドを参照して、次回も簡単に開発を再開できます！🎉
