"""アプリケーション設定。

環境変数で上書きできる。実行環境に依存する値をソースへ直接書かないこと。
起動時に .env を読み込む(既に設定されている環境変数のほうを優先する)。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/.env → プロジェクト直下の .env の順に読み込む。
# override=False なので、先に読み込んだ値と実際の環境変数が優先される。
_BACKEND_DIR = Path(__file__).parent
load_dotenv(_BACKEND_DIR / ".env", override=False)
load_dotenv(_BACKEND_DIR.parent / ".env", override=False)


def _env_str(key: str, default: str) -> str:
  return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
  raw = os.environ.get(key)
  if raw is None or raw.strip() == "":
    return default
  try:
    return int(raw)
  except ValueError:
    return default


def _env_float(key: str, default: float) -> float:
  raw = os.environ.get(key)
  if raw is None or raw.strip() == "":
    return default
  try:
    return float(raw)
  except ValueError:
    return default


def _env_bool(key: str, default: bool) -> bool:
  raw = os.environ.get(key)
  if raw is None or raw.strip() == "":
    return default
  return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
  """llama-server 接続と生成挙動の設定。"""

  def __init__(self) -> None:
    # llama-server(OpenAI 互換 API)のベース URL
    self.llm_base_url: str = _env_str("LLM_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")
    # llama-server は単一モデルを読み込むため、モデル名は任意の識別子でよい
    self.llm_model: str = _env_str("LLM_MODEL", "local-model")
    self.llm_api_key: str = _env_str("LLM_API_KEY", "")
    self.llm_timeout_sec: float = _env_float("LLM_TIMEOUT_SEC", 300.0)

    self.temperature: float = _env_float("LLM_TEMPERATURE", 0.7)
    self.top_p: float = _env_float("LLM_TOP_P", 0.9)
    self.max_tokens: int = _env_int("LLM_MAX_TOKENS", 4096)

    # 構造化出力の指定方法: json_schema / json_object / none
    # json_schema が使えないサーバーでは自動で段階的にフォールバックする
    self.response_format_mode: str = _env_str("LLM_RESPONSE_FORMAT", "json_schema")

    # 思考モード(reasoning_content)を無効化する。
    # 有効なままだと思考だけで max_tokens を使い切り、本文が空で返ることがある。
    # 対応していないサーバーでは自動で無効化なしにフォールバックする。
    self.disable_thinking: bool = _env_bool("LLM_DISABLE_THINKING", True)

    # 検証 NG 時の再生成回数の上限(初回生成は含まない)
    self.max_retries: int = _env_int("GENERATE_MAX_RETRIES", 3)

    # CORS 許可オリジン(カンマ区切り)。Vite 開発サーバーを既定で許可する
    self.cors_origins: list[str] = [
      origin.strip()
      for origin in _env_str(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
      ).split(",")
      if origin.strip()
    ]


settings = Settings()
