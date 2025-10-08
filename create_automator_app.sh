#!/bin/bash
# Automatorを使ってmacOSアプリケーションを作成

APP_NAME="規制機関ニュース要約"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Automatorアプリケーションを作成中..."
echo ""
echo "📋 手動で以下の手順を実行してください:"
echo ""
echo "1. Automatorを起動"
echo "   - Spotlight (Cmd+Space) で「Automator」と入力"
echo ""
echo "2. 「アプリケーション」を選択して「選択」をクリック"
echo ""
echo "3. 左側のアクションリストから「シェルスクリプトを実行」を検索"
echo ""
echo "4. 「シェルスクリプトを実行」を右側のワークフローエリアにドラッグ"
echo ""
echo "5. 以下のスクリプトをコピーして貼り付け:"
echo ""
echo "------- ここからコピー -------"
cat << 'EOF'
#!/bin/bash
cd "$HOME/Library/CloudStorage/OneDrive-SharedLibraries-国立研究開発法人国立国際医療研究センター/private - General/007_Cursor_prg/Scrape_EMA"
source venv/bin/activate
cd app
streamlit run streamlit_app.py &

# ブラウザを開く
sleep 5
open http://localhost:8501

# ターミナルウィンドウを表示
osascript -e 'tell application "Terminal" to activate'
EOF
echo "------- ここまでコピー -------"
echo ""
echo "6. ファイル → 保存 (Cmd+S)"
echo ""
echo "7. 保存場所: デスクトップまたはアプリケーションフォルダ"
echo "   名前: $APP_NAME"
echo ""
echo "8. 保存したアプリをダブルクリックで起動！"
echo ""
echo "✅ 完了後、デスクトップから起動できます"
