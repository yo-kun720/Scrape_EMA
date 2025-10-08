#!/bin/bash
# macOS用アプリケーションバンドルを作成

APP_NAME="規制機関ニュース要約"
APP_DIR="$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

echo "🚀 macOSアプリケーションバンドルを作成中..."

# 既存のアプリを削除
if [ -d "$APP_DIR" ]; then
    echo "📁 既存のアプリを削除..."
    rm -rf "$APP_DIR"
fi

# ディレクトリ構造を作成
echo "📂 ディレクトリ構造を作成..."
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Info.plistを作成
echo "📝 Info.plistを作成..."
cat > "$CONTENTS_DIR/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>規制機関ニュース要約</string>
    <key>CFBundleDisplayName</key>
    <string>規制機関ニュース要約</string>
    <key>CFBundleIdentifier</key>
    <string>com.scrape-ema.app</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# ランチャースクリプトを作成
echo "🔧 ランチャースクリプトを作成..."
cat > "$MACOS_DIR/launcher" << 'EOF'
#!/bin/bash
# アプリケーションのディレクトリに移動
cd "$(dirname "$0")/../../.."

# Pythonランチャーを実行
python3 launcher.py
EOF

chmod +x "$MACOS_DIR/launcher"

# プロジェクトファイルをコピー
echo "📦 プロジェクトファイルをコピー..."
cp -r app "$RESOURCES_DIR/"
cp launcher.py "$RESOURCES_DIR/"
cp requirements.txt "$RESOURCES_DIR/"
cp .env "$RESOURCES_DIR/" 2>/dev/null || echo "⚠️  .envファイルが見つかりません"

# 仮想環境をコピー（オプション）
# echo "📦 仮想環境をコピー..."
# cp -r venv "$RESOURCES_DIR/"

echo "✅ アプリケーションバンドルの作成完了！"
echo ""
echo "📱 使用方法:"
echo "   1. '$APP_DIR' をダブルクリック"
echo "   2. または、Applicationsフォルダにドラッグ&ドロップ"
echo ""
echo "⚠️  注意:"
echo "   - 初回起動時は「開発元を確認できません」と表示される場合があります"
echo "   - その場合は、右クリック → 「開く」を選択してください"
echo "   - または、システム環境設定 → セキュリティとプライバシー で許可してください"
