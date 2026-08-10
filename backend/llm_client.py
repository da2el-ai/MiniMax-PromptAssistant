"""llama-server(OpenAI 互換 API)クライアント。

サーバー実装やモデルのチャットテンプレートによって使える機能が異なるため、
構造化出力の指定方法と system ロールの扱いを段階的にフォールバックする。
成功した組み合わせはインスタンスに記憶し、次回以降はそれを直接使う。
"""

import json
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
  """LLM 呼び出しに失敗したときの例外。"""


def _extract_json(text: str) -> dict[str, Any]:
  """LLM の出力から JSON オブジェクトを取り出す。

  コードフェンスや前後の余計な文章が付いていても回収できるようにする。
  """
  stripped = text.strip()
  if stripped.startswith("```"):
    # ```json ... ``` のようなコードフェンスを剥がす
    lines = stripped.splitlines()
    if lines[0].startswith("```"):
      lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
      lines = lines[:-1]
    stripped = "\n".join(lines).strip()

  try:
    parsed = json.loads(stripped)
    if isinstance(parsed, dict):
      return parsed
  except json.JSONDecodeError:
    pass

  # 最初の { から対応する } までを走査して取り出す
  start = stripped.find("{")
  if start == -1:
    raise LLMError("LLM の応答に JSON が含まれていません")
  depth = 0
  in_string = False
  escaped = False
  for index in range(start, len(stripped)):
    char = stripped[index]
    if in_string:
      if escaped:
        escaped = False
      elif char == "\\":
        escaped = True
      elif char == '"':
        in_string = False
      continue
    if char == '"':
      in_string = True
    elif char == "{":
      depth += 1
    elif char == "}":
      depth -= 1
      if depth == 0:
        candidate = stripped[start : index + 1]
        try:
          parsed = json.loads(candidate)
        except json.JSONDecodeError as error:
          raise LLMError(f"LLM の応答の JSON を解析できませんでした: {error}") from error
        if isinstance(parsed, dict):
          return parsed
        raise LLMError("LLM の応答が JSON オブジェクトではありません")
  raise LLMError("LLM の応答の JSON が途中で終わっています(max_tokens 不足の可能性があります)")


class LLMClient:
  """llama-server への HTTP クライアント。"""

  def __init__(self) -> None:
    self._format_mode: str = settings.response_format_mode
    self._merge_system: bool = False
    self._no_thinking: bool = settings.disable_thinking
    # 一度成功した組み合わせを再探索しないためのフラグ
    self._variant_fixed: bool = False

  def _headers(self) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
      headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    return headers

  def _build_messages(
    self, system: str, messages: list[dict[str, str]], merge_system: bool
  ) -> list[dict[str, str]]:
    if not merge_system:
      return [{"role": "system", "content": system}, *messages]
    # system ロール非対応のテンプレート向けに最初の user メッセージへ統合する
    merged = [dict(message) for message in messages]
    if merged and merged[0]["role"] == "user":
      merged[0]["content"] = f"{system}\n\n---\n\n{merged[0]['content']}"
      return merged
    return [{"role": "user", "content": system}, *merged]

  def _build_payload(
    self,
    system: str,
    messages: list[dict[str, str]],
    schema: dict[str, Any] | None,
    format_mode: str,
    merge_system: bool,
    no_thinking: bool,
  ) -> dict[str, Any]:
    payload: dict[str, Any] = {
      "model": settings.llm_model,
      "messages": self._build_messages(system, messages, merge_system),
      "temperature": settings.temperature,
      "top_p": settings.top_p,
      "max_tokens": settings.max_tokens,
      "stream": False,
    }
    if no_thinking:
      # 思考モードを止める。テンプレートが対応していない場合は無視されるか 400 になる
      payload["chat_template_kwargs"] = {"enable_thinking": False}
    if schema is not None and format_mode == "json_schema":
      payload["response_format"] = {
        "type": "json_schema",
        "json_schema": {"name": "prompt_sections", "strict": True, "schema": schema},
      }
    elif schema is not None and format_mode == "json_object":
      payload["response_format"] = {"type": "json_object"}
    return payload

  def _variants(self, schema: dict[str, Any] | None) -> list[tuple[str, bool, bool]]:
    """試行する (構造化出力モード, system 統合, 思考無効化) を優先順に返す。"""
    if self._variant_fixed:
      return [(self._format_mode, self._merge_system, self._no_thinking)]

    format_chain = ["json_schema", "json_object", "none"]
    if schema is None:
      format_chain = ["none"]
    elif settings.response_format_mode in format_chain:
      # 設定された方式から始めて、順に緩いものへ落とす
      format_chain = format_chain[format_chain.index(settings.response_format_mode) :]

    # 思考は無効化を優先し、対応していなければ有効のまま試す
    thinking_chain = [True, False] if settings.disable_thinking else [False]

    variants: list[tuple[str, bool, bool]] = []
    for format_mode in format_chain:
      for no_thinking in thinking_chain:
        for merge_system in (False, True):
          variants.append((format_mode, merge_system, no_thinking))
    return variants

  async def chat_json(
    self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
  ) -> dict[str, Any]:
    """チャット補完を実行し、JSON オブジェクトとして解析した結果を返す。"""
    try:
      return await self._chat_json_once(system, messages, schema)
    except LLMError:
      if not self._variant_fixed:
        raise
      # 記憶していた組み合わせが通用しなくなった場合は、もう一度すべて試す
      logger.warning("記憶していた設定で失敗しました。全パターンを再探索します")
      self._variant_fixed = False
      return await self._chat_json_once(system, messages, schema)

  async def _chat_json_once(
    self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
  ) -> dict[str, Any]:
    last_error: Exception | None = None
    truncated = False

    async with httpx.AsyncClient(timeout=settings.llm_timeout_sec) as client:
      for format_mode, merge_system, no_thinking in self._variants(schema):
        payload = self._build_payload(
          system, messages, schema, format_mode, merge_system, no_thinking
        )
        try:
          response = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
          )
        except httpx.RequestError as error:
          # 接続自体に失敗した場合はフォールバックしても無意味なので即座に打ち切る
          raise LLMError(
            f"llama-server({settings.llm_base_url})に接続できません: {error}"
          ) from error

        if response.status_code >= 400:
          last_error = LLMError(
            f"llama-server がエラーを返しました(HTTP {response.status_code}): {response.text[:500]}"
          )
          logger.warning(
            "LLM 呼び出し失敗 (format=%s, merge_system=%s, no_thinking=%s, status=%s)。"
            "設定を変えて再試行します",
            format_mode,
            merge_system,
            no_thinking,
            response.status_code,
          )
          continue

        try:
          body = response.json()
          choice = body["choices"][0]
          message = choice["message"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
          last_error = LLMError(f"llama-server の応答形式が想定と異なります: {error}")
          continue

        finish_reason = choice.get("finish_reason")
        if finish_reason == "length":
          truncated = True

        content = message.get("content") or ""
        if not content.strip():
          # 思考モードが有効だと本文が空で、reasoning_content 側に出力が入ることがある
          content = message.get("reasoning_content") or ""

        try:
          result = _extract_json(content)
        except LLMError as error:
          last_error = error
          logger.warning(
            "JSON 解析に失敗 (format=%s, merge_system=%s, no_thinking=%s, finish_reason=%s): %s",
            format_mode,
            merge_system,
            no_thinking,
            finish_reason,
            error,
          )
          continue

        # 成功した組み合わせを記憶する
        self._format_mode = format_mode
        self._merge_system = merge_system
        self._no_thinking = no_thinking
        self._variant_fixed = True
        return result

    detail = str(last_error) if last_error else "LLM 呼び出しに失敗しました"
    if truncated:
      detail += (
        f"(生成が max_tokens={settings.max_tokens} で打ち切られています。"
        "LLM_MAX_TOKENS を増やすか、ショット数を減らしてください)"
      )
    raise LLMError(detail)

  async def health(self) -> tuple[bool, str]:
    """llama-server との疎通を確認する。

    /v1/models と、llama-server 固有の /health の両方を試す。
    バージョンやビルドによって使えるエンドポイントが異なるため。
    """
    base = settings.llm_base_url
    candidates = [f"{base}/models"]
    if base.endswith("/v1"):
      candidates.append(f"{base[:-3].rstrip('/')}/health")

    last_detail = "不明なエラー"
    async with httpx.AsyncClient(timeout=10.0) as client:
      for url in candidates:
        try:
          response = await client.get(url, headers=self._headers())
        except httpx.RequestError as error:
          last_detail = f"接続できません: {error}"
          continue
        if response.status_code < 400:
          return True, "ok"
        last_detail = f"{url} が HTTP {response.status_code} を返しました"
    return False, last_detail


llm_client = LLMClient()
