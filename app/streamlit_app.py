"""
Regulatory News Scraper - メインページ
EMA・FDA規制ニュースの統合スクレイピング・要約システム
"""
import streamlit as st

# ページ設定
st.set_page_config(
    page_title="Regulatory News Scraper",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #3498db, #e74c3c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .agency-card {
        background: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #3498db;
        transition: transform 0.3s ease;
    }
    .agency-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
    }
    .agency-title {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .agency-description {
        color: #7f8c8d;
        line-height: 1.6;
        margin-bottom: 1rem;
    }
    .feature-list {
        list-style: none;
        padding: 0;
    }
    .feature-list li {
        padding: 0.5rem 0;
        color: #27ae60;
    }
    .feature-list li:before {
        content: "✅ ";
        margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """メインアプリケーション"""
    
    # ヘッダー
    st.markdown('<h1 class="main-header">🏛️ Regulatory News Scraper</h1>', unsafe_allow_html=True)
    
    # サブタイトル
    st.markdown("""
    <div style="text-align: center; color: #7f8c8d; font-size: 1.2rem; margin-bottom: 3rem;">
        規制機関のニュース・ガイダンス文書を自動取得・要約する統合システム
    </div>
    """, unsafe_allow_html=True)
    
    # 機能概要
    st.markdown("### 🎯 システム概要")
    st.markdown("""
    このシステムは、主要な規制機関から最新のニュース・ガイダンス文書を自動取得し、
    ChatGPTを使用して日本語で要約・分析する統合プラットフォームです。
    """)
    
    # 対応機関
    st.markdown("### 🏛️ 対応規制機関")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="agency-card">
            <div class="agency-title">🇪🇺 European Medicines Agency (EMA)</div>
            <div class="agency-description">
                欧州医薬品庁の最新ニュース・ガイダンス文書を監視
            </div>
            <ul class="feature-list">
                <li>ニュース記事の自動取得</li>
                <li>Reflection paper等の関連文書ダウンロード</li>
                <li>ChatGPTによる詳細要約</li>
                <li>モバイルフレンドリーなHTML生成</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="agency-card">
            <div class="agency-title">🇺🇸 Food and Drug Administration (FDA)</div>
            <div class="agency-description">
                米国食品医薬品局のガイダンス文書を監視
            </div>
            <ul class="feature-list">
                <li>ガイダンス文書の自動取得</li>
                <li>文書タイプ・ステータス別フィルタリング</li>
                <li>PDF文書の自動要約</li>
                <li>コメント期間の追跡</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # 2行目
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("""
        <div class="agency-card">
            <div class="agency-title">🌍 World Health Organization (WHO)</div>
            <div class="agency-description">
                世界保健機関の最新ニュース・ガイドラインを監視
            </div>
            <ul class="feature-list">
                <li>グローバルヘルスニュースの自動取得</li>
                <li>疾病アウトブレイク情報</li>
                <li>健康政策・ガイドライン</li>
                <li>国際協力プログラムの追跡</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="agency-card">
            <div class="agency-title">🇯🇵 独立行政法人 医薬品医療機器総合機構 (PMDA)</div>
            <div class="agency-description">
                日本の医薬品・医療機器規制当局の新着情報を監視
            </div>
            <ul class="feature-list">
                <li>新着情報の自動取得</li>
                <li>審査・安全対策・救済業務の監視</li>
                <li>レギュラトリーサイエンス情報</li>
                <li>国際関係業務の追跡</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    
    # 使用方法
    st.markdown("### 📱 使用方法")
    st.markdown("""
    1. **左側のサイドバー**から監視したい規制機関を選択
    2. **対象期間**や**フィルタ条件**を設定
    3. **「記事を取得・要約」**ボタンをクリック
    4. 自動でスクレイピング → ChatGPT要約 → HTML生成が実行されます
    5. 生成されたHTMLをプレビュー・ダウンロードできます
    """)
    
    # 技術仕様
    st.markdown("### 🔧 技術仕様")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🕷️ スクレイピング**
        - BeautifulSoup4
        - 適切なUser-Agent設定
        - レート制限対応
        - エラー処理・再試行機能
        """)
    
    with col2:
        st.markdown("""
        **🤖 AI要約**
        - OpenAI GPT-3.5-turbo
        - 日本語での詳細要約
        - 要点リスト生成
        - 関連文書の統合要約
        """)
    
    with col3:
        st.markdown("""
        **📱 ユーザーインターフェース**
        - Streamlit
        - レスポンシブデザイン
        - リアルタイム進捗表示
        - HTMLプレビュー・ダウンロード
        """)
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #7f8c8d; font-size: 0.9em;">
        <p>🏛️ Regulatory News Scraper | 規制ニュース統合監視システム</p>
        <p>⚠️ 個人利用目的。各規制機関の利用規約に準拠しています。</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()