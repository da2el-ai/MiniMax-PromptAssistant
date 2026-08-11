"""FastAPI アプリ本体。"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import prompt_builder
from config import settings
from llm_client import LLMError, llm_client
from models import GenerateRequest, GenerateResponse, HealthResponse, Mode
from validator import normalize_sections, validate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# 接続先の取り違えにすぐ気付けるよう、起動時に設定値を出す
logger.info("LLM API 接続先: %s", settings.llm_base_url)

# ビルド済みフロントエンドの置き場所(npm run build の出力先)
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# 生成に対応している方式
SUPPORTED_MODES = {Mode.T2VA, Mode.I2VA, Mode.FL2VA, Mode.L2VA, Mode.RF2VA}

# 方式ごとに必須となる参照画像の役割
REQUIRED_IMAGE_ROLES: dict[Mode, tuple[str, ...]] = {
  Mode.I2VA: ("first",),
  Mode.FL2VA: ("first", "last"),
  Mode.L2VA: ("last",),
}

ROLE_LABELS = {"first": "最初のフレーム", "last": "最後のフレーム"}

app = FastAPI(
  title="MiniMax-H3 プロンプト作成アシスタント",
  description="日本語の入力から MiniMax-H3 用の英語プロンプトを生成する",
  version="0.2.0",
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.cors_origins,
  allow_credentials=False,
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
  """バックエンドと llama-server の疎通を返す。"""
  reachable, detail = await llm_client.health()
  return HealthResponse(
    backend=True, llm=reachable, llm_base_url=settings.llm_base_url, detail=detail
  )


def _check_required_inputs(request: GenerateRequest) -> None:
  """方式ごとの必須入力を確認する。"""
  provided = {
    image.role.value for image in request.images if image.description.strip()
  }
  for role in REQUIRED_IMAGE_ROLES.get(request.mode, ()):
    if role not in provided:
      raise HTTPException(
        status_code=422,
        detail=f"{request.mode.value.upper()} では{ROLE_LABELS[role]}の説明が必要です",
      )
  if request.mode is Mode.RF2VA and not request.ref_assets:
    raise HTTPException(status_code=422, detail="RF2VA では参照アセットを 1 件以上登録してください")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
  """日本語の入力から MiniMax-H3 用プロンプトを生成する。"""
  if request.mode not in SUPPORTED_MODES:
    raise HTTPException(
      status_code=501, detail=f"未対応の方式です(指定: {request.mode.value})"
    )
  _check_required_inputs(request)

  # 書式が厳密に決まっている部分を先に確定させる
  cut_times = prompt_builder.resolve_cut_times(request.duration_sec, request.shots)
  speaker_ids = prompt_builder.assign_speaker_ids(request.shots)
  asset_labels = (
    prompt_builder.assign_asset_labels(request.ref_assets) if request.mode is Mode.RF2VA else []
  )
  instruction = prompt_builder.build_instruction(
    request.mode, request.duration_sec, len(request.shots)
  )

  try:
    system_prompt = prompt_builder.load_system_prompt(request.mode)
  except FileNotFoundError as error:
    raise HTTPException(status_code=500, detail=str(error)) from error

  brief = prompt_builder.build_brief(request, cut_times, speaker_ids, asset_labels)
  messages: list[dict[str, str]] = [{"role": "user", "content": brief}]
  schema = prompt_builder.response_schema(request.mode)

  sections: dict[str, str] = {}
  warnings: list[str] = []
  violations: list[str] = []
  retries = 0

  for attempt in range(settings.max_retries + 1):
    retries = attempt
    try:
      raw = await llm_client.chat_json(system_prompt, messages, schema)
    except LLMError as error:
      raise HTTPException(status_code=502, detail=str(error)) from error

    sections = normalize_sections(
      request, {key: str(raw.get(key, "")) for key in raw}, instruction
    )
    violations, warnings = validate(request, sections, cut_times, speaker_ids, asset_labels)
    if not violations:
      logger.info("%s の生成に成功しました(再生成 %d 回)", request.mode.value, attempt)
      break

    logger.info("検証 NG(%d 件)。再生成します: %s", len(violations), violations)
    if attempt == settings.max_retries:
      break
    # 直前の出力と違反内容を渡して修正させる
    messages.append({"role": "assistant", "content": _to_json_text(sections)})
    messages.append({"role": "user", "content": prompt_builder.build_retry_message(violations)})

  if violations:
    warnings.append(
      f"検証に通らない箇所が {len(violations)} 件残っています(再生成 {settings.max_retries} 回)。"
      "内容を確認して手直ししてください。"
    )
    warnings += [f"未解決: {violation}" for violation in violations]

  prompt = prompt_builder.assemble_prompt(request.mode, sections, instruction)
  return GenerateResponse(prompt=prompt, retries=retries, warnings=warnings)


def _to_json_text(sections: dict[str, str]) -> str:
  """再生成時に直前の出力を assistant メッセージとして渡すための整形。"""
  return json.dumps(sections, ensure_ascii=False)


# ビルド済みフロントエンドの配信。ルート("/")への割り当ては上の API より後に行う
# 必要があるため、経路の定義がすべて済んだこの位置で登録する。
# 開発時は Vite 開発サーバーを使うため、dist がなくても API だけで動作させる。
if DIST_DIR.is_dir():
  app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
  logger.info("フロントエンドを配信します: %s", DIST_DIR)
else:
  logger.warning(
    "ビルド済みフロントエンドが見つかりません(%s)。API のみ提供します。"
    "画面を使うには frontend で npm install && npm run build を実行してください",
    DIST_DIR,
  )
