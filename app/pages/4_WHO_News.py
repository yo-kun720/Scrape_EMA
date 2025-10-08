"""
WHOニュースページ
"""
import streamlit as st
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

from scrapers.who_scraper import WHOScraper
from shared.gpt_html import generate_html_from_articles
from config import DEFAULT_DAYS_BACK

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def who_news_page():
    st.title("🌍 WHO News")
    st.markdown("WHO（World Health Organization）の最新ニュースを取得・要約します。")

    days_back = st.slider(
        "何日前までの情報を取得しますか？",
        min_value=1,
        max_value=30,
        value=DEFAULT_DAYS_BACK,
        help="指定した日数前までのニュースを取得します。"
    )
    
    # プレビュー設定
    show_preview = st.sidebar.checkbox("HTMLプレビューを表示", value=True)
    
    # メインコンテンツ（縦並びレイアウト）
    st.subheader("📋 実行設定")
    st.info(f"""
    **対象期間**: {days_back}日前から現在まで
    
    **対象サイト**: [WHO News](https://www.who.int/news)
    
    **取得内容**:
    - News releases
    - Statements
    - Feature stories
    - Events
    - その他WHO関連ニュース
    """)
    
    # 実行ボタン
    if st.button("🚀 WHOニュースを取得・要約", type="primary", use_container_width=True):
        with st.spinner("WHOニュースを取得中..."):
            try:
                # スクレイピング実行
                who_scraper = WHOScraper()
                documents = who_scraper.scrape_who_news(days_back)

                if documents:
                    st.success(f"{len(documents)}件のWHOニュースを取得しました。ChatGPTで要約中...")
                    html_content = generate_html_from_articles(documents, "WHO")
                    
                    # セッション状態に保存
                    st.session_state['who_html'] = html_content
                    st.session_state['who_days_back'] = days_back
                    
                    st.success("✅ WHOニュースの取得・要約が完了しました！")
                    
                else:
                    st.info("指定期間内に新しいWHOニュースは見つかりませんでした。")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")
                logger.error(f"Error in main: {e}")
    
    # 実行結果セクション
    st.subheader("📊 実行結果")
    
    if 'who_html' in st.session_state:
        st.success(f"✅ 最新の実行結果 (対象期間: {st.session_state.get('who_days_back', days_back)}日前)")
        
        # HTMLプレビュー
        if show_preview:
            st.subheader("📱 HTMLプレビュー")
            st.components.v1.html(
                st.session_state['who_html'],
                height=600,
                scrolling=True
            )
        
        # ダウンロードボタン
        st.download_button(
            label="💾 HTMLファイルをダウンロード",
            data=st.session_state['who_html'].encode("utf-8"),
            file_name=f"who_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            use_container_width=True
        )
    else:
        st.info("👆 上記のボタンをクリックしてWHOニュースを取得してください")
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        <p>© 2025 WHO News Scraper. All rights reserved.</p>
        <p>Data provided by World Health Organization (WHO).</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    who_news_page()
