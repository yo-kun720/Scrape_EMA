"""
EMA News Scraper - EMAニュースページ
"""
import logging
import os
from datetime import datetime
from typing import List, Dict

import streamlit as st
import tempfile
from dotenv import load_dotenv

# 環境変数を読み込み（親ディレクトリの.envファイルを指定）
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from scrapers.ema_scraper import scrape_ema_news
from shared.gpt_html import generate_html_from_articles
from config import DEFAULT_DAYS_BACK, OPENAI_API_KEY

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
    .info-message {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def validate_environment() -> bool:
    """環境変数の検証"""
    if not OPENAI_API_KEY:
        st.error("❌ OPENAI_API_KEY環境変数が設定されていません。")
        st.info("💡 .envファイルにOPENAI_API_KEYを設定してください。")
        return False
    return True


def display_article_preview(articles: List[Dict[str, str]]) -> None:
    """記事のプレビューを表示"""
    if not articles:
        st.warning("📭 指定期間内に記事が見つかりませんでした。")
        return
    
    st.subheader(f"📰 取得した記事 ({len(articles)}件)")
    
    for i, article in enumerate(articles, 1):
        with st.expander(f"{i}. {article['title'][:80]}..."):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**タイトル:** {article['title']}")
                st.write(f"**公開日:** {article['published_at_iso']}")
                st.write(f"**要約:** {article['summary_or_lead']}")
            
            with col2:
                st.link_button("🔗 記事を読む", article['url'])


def save_html_to_file(html_content: str) -> str:
    """HTMLコンテンツをファイルに保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ema_news_{timestamp}.html"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_path = f.name
    
    # プロジェクトディレクトリにコピー
    project_path = os.path.join(os.getcwd(), filename)
    with open(project_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return project_path


def main():
    """メインアプリケーション"""
    
    # ヘッダー
    st.markdown('<h1 class="main-header">🇪🇺 EMA News Scraper</h1>', unsafe_allow_html=True)
    
    # 環境変数チェック
    if not validate_environment():
        st.stop()
    
    # サイドバー設定
    st.sidebar.header("⚙️ 設定")
    
    # 対象期間
    days_back = st.sidebar.slider(
        "📅 対象期間（日数）",
        min_value=1,
        max_value=30,
        value=DEFAULT_DAYS_BACK,
        help="何日前からの記事を取得するか"
    )
    
    # プレビュー表示設定
    show_preview = st.sidebar.checkbox(
        "👁️ プレビュー表示",
        value=True,
        help="生成されたHTMLのプレビューを表示するか"
    )
    
    # メインコンテンツ
    st.markdown("### 🎯 使用方法")
    st.markdown("""
    1. 左側のサイドバーで対象期間を設定（デフォルト: 7日間）
    2. 「📰 記事を取得・要約」ボタンをクリック
    3. スクレイピング → ChatGPT要約 → HTML生成が自動実行されます
    4. 生成されたHTMLをプレビュー・ダウンロードできます
    
    **機能**: EMAニュースの自動取得とChatGPTによる詳細要約
    """)
    
    # 実行ボタン
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        run_button = st.button(
            "📰 記事を取得・要約",
            type="primary",
            use_container_width=True
        )
    
    if run_button:
        
        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: スクレイピング
            status_text.text("🔍 EMAニュースをスクレイピング中...")
            progress_bar.progress(25)
            
            articles = scrape_ema_news(days_back)
            
            if not articles:
                st.warning("📭 指定期間内に記事が見つかりませんでした。")
                st.stop()
            
            # Step 2: ChatGPT要約・HTML生成
            status_text.text("🤖 ChatGPTで記事を要約・HTML生成中...")
            progress_bar.progress(75)
            
            html_content = generate_html_from_articles(articles)
            
            progress_bar.progress(100)
            
            st.markdown('<div class="success-message">✅ 記事の取得・要約が完了しました！</div>', unsafe_allow_html=True)
            status_text.text("✅ 完了")
            
            # 統計情報
            st.success(f"""
            📊 **処理完了**
            - 取得記事数: {len(articles)}件
            - 対象期間: 過去{days_back}日間
            - ChatGPT要約: 完了
            - HTML生成: 完了
            """)
        
        except Exception as e:
            st.markdown('<div class="error-message">❌ エラーが発生しました。</div>', unsafe_allow_html=True)
            st.error(f"エラー詳細: {str(e)}")
            logger.error(f"Error in main process: {e}")
            status_text.text("❌ エラー")
        
        finally:
            progress_bar.empty()
    
    # プレビュー表示
    if show_preview and 'html_content' in locals():
        st.markdown("---")
        st.subheader("👁️ HTMLプレビュー")
        
        # HTMLファイル保存
        html_file_path = save_html_to_file(html_content)
        
        # プレビュー表示
        st.components.v1.html(html_content, height=600, scrolling=True)
        
        # ダウンロードボタン
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_data = f.read()
        
        st.download_button(
            label="💾 HTMLファイルをダウンロード",
            data=html_data,
            file_name=f"ema_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html"
        )
    
    # 記事プレビュー
    if 'articles' in locals() and articles:
        st.markdown("---")
        display_article_preview(articles)
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #7f8c8d; font-size: 0.9em;">
        <p>🇪🇺 EMA News Scraper | Data source: European Medicines Agency (EMA)</p>
        <p>🤖 ChatGPT要約機能付き | 個人利用目的。EMAのLegal noticeに基づき、出典を明示しています。</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
