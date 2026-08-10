"""アプリケーションの起動スクリプト。

    uv run serve.py

仮想環境の作成と依存の導入は uv が自動で行うため、事前準備は不要。
ビルド済みフロントエンドがあれば、バックエンドが同じポートで配信する。
"""

import argparse
import threading
import webbrowser
from pathlib import Path

import uvicorn

# backend 内はフラットなインポート構成のため、その階層を import 対象に加える
BACKEND_DIR = Path(__file__).parent / "backend"


def _browser_url(host: str, port: int) -> str:
  """ブラウザで開く URL を組み立てる。"""
  # 全アドレス待ち受けの指定はそのまま開けないので、ループバックに読み替える
  hostname = "127.0.0.1" if host in ("0.0.0.0", "::") else host
  return f"http://{hostname}:{port}"


def main() -> None:
  parser = argparse.ArgumentParser(
    description="MiniMax-H3 プロンプト作成アシスタントを起動する"
  )
  parser.add_argument("--host", default="127.0.0.1", help="待ち受けアドレス(既定: 127.0.0.1)")
  parser.add_argument("--port", type=int, default=8000, help="待ち受けポート(既定: 8000)")
  parser.add_argument(
    "--no-browser", action="store_true", help="起動時にブラウザを開かない"
  )
  args = parser.parse_args()

  url = _browser_url(args.host, args.port)
  if not args.no_browser:
    # サーバーが応答できるようになってから開く
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

  print(f"MiniMax-H3 プロンプト作成アシスタント: {url}")
  uvicorn.run("main:app", host=args.host, port=args.port, app_dir=str(BACKEND_DIR))


if __name__ == "__main__":
  main()
