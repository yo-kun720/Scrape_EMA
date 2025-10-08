"""
PMDA新着情報ページ
"""
import streamlit as st
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

from scrapers.pmda_scraper import PMDAScraper
from shared.gpt_html import generate_html_from_articles
from config import DEFAULT_DAYS_BACK

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_pmda_news(days_back: int) -> str:
    """
    PMDA新着情報をスクレイピングしてHTMLを生成
    
    Args:
        days_back: 何日前からの情報を取得するか
        
    Returns:
        生成されたHTML文字列
    """
    try:
        # PMDAスクレイパーを初期化
        pmda_scraper = PMDAScraper()
        
        # 新着情報をスクレイピング
        articles = pmda_scraper.scrape_pmda_news(days_back)
        
        if not articles:
            logger.warning("No PMDA articles found")
            return generate_html_from_articles([], "PMDA")
        
        # HTMLを生成
        html_content = generate_html_from_articles(articles, "PMDA")
        return html_content
        
    except Exception as e:
        logger.error(f"Error in scrape_pmda_news: {e}")
        return f"<html><body><h1>エラーが発生しました</h1><p>{str(e)}</p></body></html>"

def main():
    """メイン関数"""
    st.set_page_config(
        page_title="PMDA新着情報",
        page_icon="🇯🇵",
        layout="wide"
    )
    
    st.title("🇯🇵 PMDA新着情報")
    st.markdown("**独立行政法人 医薬品医療機器総合機構 (PMDA) の新着情報を取得・要約します**")
    
    # サイドバーで設定
    st.sidebar.header("設定")
    
    # 対象期間の設定
    days_back = st.sidebar.slider(
        "対象期間（日数）",
        min_value=1,
        max_value=30,
        value=DEFAULT_DAYS_BACK,
        help="何日前からの情報を取得するかを設定します"
    )
    
    # プレビュー設定
    show_preview = st.sidebar.checkbox("HTMLプレビューを表示", value=True)
    
    # メインコンテンツ（縦並びレイアウト）
    st.subheader("📋 実行設定")
    st.info(f"""
    **対象期間**: {days_back}日前から現在まで
    
    **対象サイト**: [PMDA新着情報](https://www.pmda.go.jp/0017.html)
    
    **取得内容**:
    - 審査関連業務
    - 安全対策業務  
    - 健康被害救済業務
    - レギュラトリーサイエンス
    - 国際関係業務
    """)
    
    # 実行ボタン
    if st.button("🚀 PMDA新着情報を取得・要約", type="primary", use_container_width=True):
        with st.spinner("PMDA新着情報を取得中..."):
            try:
                # スクレイピング実行
                html_content = scrape_pmda_news(days_back)
                
                # セッション状態に保存
                st.session_state['pmda_html'] = html_content
                st.session_state['pmda_days_back'] = days_back
                
                st.success("✅ PMDA新着情報の取得・要約が完了しました！")
                
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")
                logger.error(f"Error in main: {e}")
    
    # 実行結果セクション
    st.subheader("📊 実行結果")
    
    if 'pmda_html' in st.session_state:
        st.success(f"✅ 最新の実行結果 (対象期間: {st.session_state.get('pmda_days_back', days_back)}日前)")
        
        # HTMLプレビュー
        if show_preview:
            st.subheader("📱 HTMLプレビュー")
            st.components.v1.html(
                st.session_state['pmda_html'],
                height=600,
                scrolling=True
            )
        
        # ダウンロードボタン
        st.download_button(
            label="💾 HTMLファイルをダウンロード",
            data=st.session_state['pmda_html'],
            file_name=f"pmda_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            use_container_width=True
        )
    else:
        st.info("👆 上記のボタンをクリックしてPMDA新着情報を取得してください")
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        <p>🇯🇵 PMDA新着情報取得・要約ツール | 
        <a href='https://www.pmda.go.jp/0017.html' target='_blank'>PMDA公式サイト</a> | 
        <a href='https://www.pmda.go.jp/' target='_blank'>PMDAホームページ</a></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
