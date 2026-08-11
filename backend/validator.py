"""生成結果のフォーマット検証。

docs/SPEC.md の「7. 検証ルール」に対応する。
violations が空でなければ、その内容を LLM に伝えて再生成する。
warnings は再生成せずに利用者へ伝える注意点。
"""

import re

from models import GenerateRequest, Mode
from prompt_builder import format_timestamp, main_field, section_keys

SHOT_MARKER_RE = re.compile(r"\[Shot\s*(\d+)\]")
TIMESTAMP_RE = re.compile(r"^\s*At\s+(\d{2}:\d{2}\.\d{3})\s*,")
DIALOGUE_RE = re.compile(r"<d>(.*?)</d>", re.DOTALL)
LANGUAGE_TAG_RE = re.compile(r"^\s*\[[^\]\n]+\]")
VOICEOVER_PHRASE = "says in an off-screen voiceover"

# RF2VA の参照ラベル。<d> や <scenetrans> のようなタグとは形が違う
LABEL_RE = re.compile(r"<(Subject|Picture|Video|Audio)\s+(\d+)>")
# retention_analysis の 1 行(例: <Subject 1> (appears in ...): fully_preserved - ...)
RETENTION_LINE_RE = re.compile(
  r"^<(Subject|Picture|Video|Audio)\s+(\d+)>[^:]*:\s*([A-Za-z_]+)", re.MULTILINE
)
TASK_TYPE_RE = re.compile(r"^\s*\[([^\]]+)\]")

VISIBLE_MARKERS = {"fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference"}
AUDIO_MARKERS = {"fully_copy", "partially_copy", "reference", "weak_reference"}
TASK_TYPES = {
  "keyframe completion",
  "reference generation",
  "video editing",
  "video continuation",
  "audio reuse",
  "audio reference",
}


def _strip_field_name(key: str, value: str) -> str:
  """LLM が値の中にフィールド名を含めてしまった場合に取り除く。"""
  stripped = value.strip()
  prefix = f"{key}:"
  if stripped.lower().startswith(prefix.lower()):
    stripped = stripped[len(prefix) :].strip()
  return stripped


def normalize_sections(
  request: GenerateRequest, sections: dict[str, str], instruction: str
) -> dict[str, str]:
  """検証前に値を整える。N/A 指定はコード側で強制する。"""
  keys = section_keys(request.mode)
  normalized: dict[str, str] = {}
  for key in keys:
    value = sections.get(key)
    normalized[key] = _strip_field_name(key, value if isinstance(value, str) else "")

  body_key = main_field(request.mode)
  body = normalized[body_key]
  # LLM が先頭の指示行まで書いてしまった場合は取り除く
  if instruction and body.startswith(instruction):
    body = body[len(instruction) :].strip()
  if request.mode is Mode.RF2VA:
    # スタイル文とショットが行ごとに並ぶ形なので改行を残す
    normalized[body_key] = re.sub(r"\n{2,}", "\n", body).strip()
  else:
    # 本文は 1 段落にまとめる
    normalized[body_key] = re.sub(r"\s*\n+\s*", " ", body).strip()

  for key in ("overall_soundscape", "non_diegetic_music"):
    normalized[key] = re.sub(r"\s*\n+\s*", " ", normalized[key]).strip()

  # 「なし」指定は N/A に強制置換する
  if request.ambience.none:
    normalized["overall_soundscape"] = "N/A"
  if request.bgm.none:
    normalized["non_diegetic_music"] = "N/A"
  return normalized


def _check_shots(request: GenerateRequest, body: str, cut_times: list[float | None]) -> list[str]:
  violations: list[str] = []
  matches = list(SHOT_MARKER_RE.finditer(body))
  expected_count = len(request.shots)

  if not matches:
    violations.append("The description contains no [Shot N] marker. It must start with [Shot 1].")
    return violations

  if request.mode is Mode.RF2VA:
    # フルリファレンスモードは [Shot 1] の前にスタイル文を置く
    if body.lstrip().startswith("[Shot 1]"):
      violations.append(
        "In full-reference mode the style must be established in one or two sentences "
        "before [Shot 1], on their own line."
      )
  elif not body.lstrip().startswith("[Shot 1]"):
    violations.append("The description must begin with the literal marker [Shot 1].")

  numbers = [int(match.group(1)) for match in matches]
  if numbers != list(range(1, expected_count + 1)):
    violations.append(
      f"The shot markers must be exactly [Shot 1] through [Shot {expected_count}] in order, "
      f"each appearing once. Found: {numbers}."
    )
    return violations

  for index, match in enumerate(matches):
    number = index + 1
    tail = body[match.end() :]
    timestamp_match = TIMESTAMP_RE.match(tail)
    if number == 1:
      if timestamp_match:
        violations.append("[Shot 1] must not carry a timestamp. Remove the 'At ...,' after it.")
      continue

    expected = format_timestamp(cut_times[index] or 0.0)
    if not timestamp_match:
      violations.append(
        f"[Shot {number}] must be followed immediately by 'At {expected},' in MM:SS.mmm format."
      )
      continue
    actual = timestamp_match.group(1)
    if actual != expected:
      violations.append(
        f"[Shot {number}] must use the exact cut time 'At {expected},' but it used 'At {actual},'."
      )
  return violations


def _normalized_dialogue_haystack(blocks: list[str]) -> str:
  """セリフ照合用に、言語タグと空白と特殊タグを取り除いて連結する。"""
  cleaned: list[str] = []
  for block in blocks:
    text = LANGUAGE_TAG_RE.sub("", block)
    text = text.replace("<scenetrans>", "").replace("<cutoff>", "")
    cleaned.append(re.sub(r"\s+", "", text))
  return "".join(cleaned)


def _check_dialogues(request: GenerateRequest, body: str, speaker_ids: dict[str, str]) -> list[str]:
  violations: list[str] = []

  open_count = body.count("<d>")
  close_count = body.count("</d>")
  if open_count != close_count:
    violations.append(
      f"The <d> tags are unbalanced: {open_count} opening and {close_count} closing tags."
    )
    return violations

  blocks = [match.group(1) for match in DIALOGUE_RE.finditer(body)]
  expected_dialogues = [dialogue for shot in request.shots for dialogue in shot.dialogues]

  if not expected_dialogues:
    if blocks:
      violations.append("The brief contains no dialogue, so the description must not use <d> tags.")
    return violations

  for block in blocks:
    if not LANGUAGE_TAG_RE.match(block):
      snippet = block.strip()[:40]
      violations.append(
        f'Every <d> block must start with a language tag such as [English]. Missing in: "{snippet}".'
      )

  haystack = _normalized_dialogue_haystack(blocks)
  for dialogue in expected_dialogues:
    text = dialogue.text.strip()
    exact = any(text in block for block in blocks)
    if not exact and re.sub(r"\s+", "", text) not in haystack:
      violations.append(
        f'The dialogue line must be reproduced verbatim inside <d>, untranslated: "{text}".'
      )

  # 話者 ID がすべて使われているか
  for name, speaker_id in speaker_ids.items():
    if f"({speaker_id}" not in body:
      violations.append(
        f"The speaker ID ({speaker_id}) for {name} does not appear in the description."
      )

  # ボイスオーバーの定型表現
  if any(dialogue.voiceover for dialogue in expected_dialogues) and VOICEOVER_PHRASE not in body:
    violations.append(
      f'A voiceover line requires the exact phrase "{VOICEOVER_PHRASE}" before its <d> block, '
      "followed by a statement that the character's lips remain closed."
    )
  return violations


def _check_on_screen_texts(request: GenerateRequest, body: str) -> list[str]:
  violations: list[str] = []
  for text in request.on_screen_texts:
    stripped = text.strip()
    if stripped and f'"{stripped}"' not in body:
      violations.append(
        f'The on-screen text must appear verbatim in double quotation marks: "{stripped}".'
      )
  return violations


def _check_rf2va(sections: dict[str, str], asset_labels: list[str]) -> list[str]:
  """フルリファレンスモード固有の検証。"""
  violations: list[str] = []
  definitions = sections["subject_definitions"]

  # 定義済みラベル。<Picture N> が別ラベルの出典としてのみ書かれる場合もあるため、
  # 行頭に限らず subject_definitions 内のどこかに現れていれば定義済みとみなす
  defined = {match.group(0) for match in LABEL_RE.finditer(definitions)}
  if not defined:
    violations.append(
      "subject_definitions must define at least one reference label such as <Subject 1>."
    )

  # 与えたアセットのラベルがすべて定義されているか
  for label in asset_labels:
    if label not in defined:
      violations.append(f"The reference asset {label} is missing from subject_definitions.")

  # 他のセクションで使われるラベルは定義済みでなければならない
  for key in ("summary", "retention_analysis", "detailed_description"):
    for match in LABEL_RE.finditer(sections[key]):
      label = match.group(0)
      if label not in defined:
        violations.append(f"{label} is used in {key} but never defined in subject_definitions.")
        break

  # summary の先頭はタスク種別
  summary = sections["summary"]
  task_match = TASK_TYPE_RE.match(summary)
  if not task_match:
    violations.append(
      "summary must begin with a square-bracketed task-type prefix, for example "
      "[reference generation]."
    )
  else:
    for part in task_match.group(1).split("+"):
      value = part.strip()
      if value not in TASK_TYPES:
        violations.append(
          f'"{value}" is not a valid task type. Use only: {", ".join(sorted(TASK_TYPES))}.'
        )
  if LABEL_RE.search(summary) is None and defined:
    violations.append("summary must refer to the reference labels defined in subject_definitions.")

  # retention_analysis の関係マーカー
  retention = sections["retention_analysis"]
  entries = list(RETENTION_LINE_RE.finditer(retention))
  if not entries:
    violations.append(
      "retention_analysis must contain one line per reference label, for example "
      "<Subject 1> (appears in [Shot 1]): fully_preserved - ..."
    )
  for match in entries:
    label_type = match.group(1)
    marker = match.group(3)
    allowed = AUDIO_MARKERS if label_type == "Audio" else VISIBLE_MARKERS
    if marker not in allowed:
      violations.append(
        f'"{marker}" is not a valid relationship marker for <{label_type} {match.group(2)}>. '
        f'Use one of: {", ".join(sorted(allowed))}.'
      )
  return violations


def validate(
  request: GenerateRequest,
  sections: dict[str, str],
  cut_times: list[float | None],
  speaker_ids: dict[str, str],
  asset_labels: list[str],
) -> tuple[list[str], list[str]]:
  """検証を実行し、(violations, warnings) を返す。"""
  violations: list[str] = []
  warnings: list[str] = []

  for key in section_keys(request.mode):
    if not sections.get(key, "").strip():
      violations.append(f"The field `{key}` is empty. It must contain text.")
  if violations:
    return violations, warnings

  body = sections[main_field(request.mode)]
  violations += _check_shots(request, body, cut_times)
  violations += _check_dialogues(request, body, speaker_ids)
  violations += _check_on_screen_texts(request, body)
  if request.mode is Mode.RF2VA:
    violations += _check_rf2va(sections, asset_labels)

  # 警告(再生成はしない)
  if not request.ambience.none and sections["overall_soundscape"].strip() == "N/A":
    warnings.append(
      "overall_soundscape が N/A になっています。完全な無音を意図していない場合は再生成してください。"
    )
  if request.mode is Mode.FL2VA and len(request.shots) > 1:
    warnings.append(
      "FL2VA は単一ショットが推奨です。複数ショットでは最初と最後の補間が意図どおりにならないことがあります。"
    )
  return violations, warnings
