#!/usr/bin/env python3
"""
デスクトップランチャー
ダブルクリックでStreamlitアプリを起動
"""
import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def main():
    # スクリプトのディレクトリを取得
    script_dir = Path(__file__).parent.absolute()
    app_dir = script_dir / "app"
    streamlit_app = app_dir / "streamlit_app.py"
    
    # 仮想環境のPythonパスを取得
    if sys.platform == "darwin" or sys.platform == "linux":
        python_path = script_dir / "venv" / "bin" / "python"
    else:  # Windows
        python_path = script_dir / "venv" / "Scripts" / "python.exe"
    
    # 仮想環境が存在しない場合はシステムのPythonを使用
    if not python_path.exists():
        python_path = sys.executable
    
    print("🚀 規制機関ニュース要約アプリを起動中...")
    print(f"📁 アプリケーションパス: {streamlit_app}")
    
    # Streamlitを起動
    try:
        # バックグラウンドでStreamlitを起動
        process = subprocess.Popen(
            [str(python_path), "-m", "streamlit", "run", str(streamlit_app)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(script_dir)
        )
        
        # アプリが起動するまで待機
        print("⏳ アプリケーションの起動を待っています...")
        time.sleep(5)
        
        # ブラウザを開く
        print("🌐 ブラウザを起動します...")
        webbrowser.open("http://localhost:8501")
        
        print("\n✅ アプリケーションが起動しました！")
        print("📱 ブラウザで http://localhost:8501 にアクセスしてください")
        print("\n⚠️  このウィンドウを閉じるとアプリケーションが終了します")
        print("🛑 終了するには Ctrl+C を押してください\n")
        
        # プロセスが終了するまで待機
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 アプリケーションを終了しています...")
        process.terminate()
        process.wait()
        print("✅ 終了しました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("\n💡 手動で起動する場合:")
        print(f"   cd {script_dir}")
        print("   source venv/bin/activate")
        print("   cd app")
        print("   streamlit run streamlit_app.py")
        sys.exit(1)

if __name__ == "__main__":
    main()
