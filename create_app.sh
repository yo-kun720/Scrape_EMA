#!/bin/bash
# AppleScriptを使ってmacOSアプリケーションを自動作成

APP_NAME="規制機関ニュース要約"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$HOME/Desktop/$APP_NAME.app"

echo "🚀 デスクトップアプリケーションを作成中..."

# AppleScriptを作成
APPLESCRIPT=$(cat << EOF
on run
    set projectPath to "$SCRIPT_DIR"
    
    tell application "Terminal"
        activate
        do script "cd '" & projectPath & "' && source venv/bin/activate && cd app && streamlit run streamlit_app.py"
    end tell
    
    delay 5
    
    tell application "Safari"
        activate
        open location "http://localhost:8501"
    end tell
end run
EOF
)

# AppleScriptをアプリケーションとして保存
echo "$APPLESCRIPT" | osacompile -o "$APP_PATH"

if [ -f "$APP_PATH/Contents/MacOS/applet" ]; then
    echo "✅ アプリケーションの作成完了！"
    echo ""
    echo "📱 デスクトップに「$APP_NAME.app」が作成されました"
    echo ""
    echo "🎯 使用方法:"
    echo "   1. デスクトップの「$APP_NAME.app」をダブルクリック"
    echo "   2. Terminalウィンドウが開き、アプリが起動します"
    echo "   3. 自動的にSafariでアプリが開きます"
    echo ""
    echo "⚠️  注意:"
    echo "   - 初回起動時は「開発元を確認できません」と表示される場合があります"
    echo "   - その場合は、右クリック → 「開く」を選択してください"
    echo ""
    echo "🛑 終了方法:"
    echo "   - Terminalウィンドウで Ctrl+C を押す"
    echo "   - または、Terminalを終了する"
else
    echo "❌ アプリケーションの作成に失敗しました"
    exit 1
fi
