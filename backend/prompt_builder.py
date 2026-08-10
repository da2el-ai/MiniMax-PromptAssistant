"""プロンプトの組み立て。

LLM には英語の自由記述部分だけを書かせ、書式が厳密に決まっている部分
(先頭の指示行、フィールド名、カット時刻、話者 ID、参照ラベル)はコード側で確定させる。
"""

from pathlib import Path

from models import GenerateRequest, Mode, RefAsset, Shot

TEMPLATE_DIR = Path(__file__).parent / "templates"

# 各方式のテンプレートに埋め込む共通ルールの差し込み位置
COMMON_MARKER = "{{COMMON_RULES}}"

# T2VA / I2VA / FL2VA / L2VA が出力するフィールド
SECTION_KEYS_STANDARD = (
  "integrated_multimodal_description",
  "overall_soundscape",
  "non_diegetic_music",
)

# RF2VA(フルリファレンスモード)が出力するフィールド
SECTION_KEYS_RF2VA = (
  "subject_definitions",
  "summary",
  "retention_analysis",
  "detailed_description",
  "overall_soundscape",
  "non_diegetic_music",
)

# 参照アセットの種類とラベル名の対応
ASSET_LABEL_NAMES = {"image": "Picture", "video": "Video", "audio": "Audio"}


def section_keys(mode: Mode) -> tuple[str, ...]:
  """方式が出力するフィールド名を返す。"""
  return SECTION_KEYS_RF2VA if mode is Mode.RF2VA else SECTION_KEYS_STANDARD


def main_field(mode: Mode) -> str:
  """本文にあたるフィールド名を返す。"""
  return "detailed_description" if mode is Mode.RF2VA else "integrated_multimodal_description"


def response_schema(mode: Mode) -> dict:
  """構造化出力用の JSON スキーマを返す。"""
  keys = section_keys(mode)
  return {
    "type": "object",
    "properties": {key: {"type": "string"} for key in keys},
    "required": list(keys),
    "additionalProperties": False,
  }


def format_timestamp(seconds: float) -> str:
  """秒を MM:SS.mmm 形式に整形する。"""
  total_ms = int(round(seconds * 1000))
  minutes, remainder_ms = divmod(total_ms, 60_000)
  secs, millis = divmod(remainder_ms, 1000)
  return f"{minutes:02d}:{secs:02d}.{millis:03d}"


def build_instruction(mode: Mode, duration_sec: float, shot_count: int) -> str:
  """先頭の指示行を組み立てる。ガイドで文面が固定されている部分。"""
  if mode is Mode.I2VA:
    return (
      "For the target video, at 0.00 seconds into the target video, "
      "<Picture 1> (from [Shot 1]) is fully referenced."
    )
  # 有効な尺は小数 2 桁で表記する
  duration = f"{duration_sec:.2f}"
  if mode is Mode.FL2VA:
    return (
      "How the reference pictures align with the target video — "
      "Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; "
      f"Picture 2 (from Shot {shot_count}) aligns with the {duration}-second mark of the target video."
    )
  if mode is Mode.L2VA:
    return (
      "How the reference pictures align with the target video — "
      f"<Picture 1> (from [Shot {shot_count}]) aligns with the {duration}-second mark "
      "of the target video."
    )
  # T2VA と RF2VA に指示行はない
  return ""


def resolve_cut_times(duration_sec: float, shots: list[Shot]) -> list[float | None]:
  """各ショットのカット時刻を確定する。

  Shot 1 は常に None。未指定のショットは、前後の確定値の間に均等配分する。
  LLM に時刻を考えさせるとフォーマット崩れの原因になるため、ここで確定させる。
  """
  count = len(shots)
  resolved: list[float | None] = [None] * count
  if count == 1:
    return resolved

  # 確定済みのアンカー。索引 0 は動画の先頭、索引 count は動画の末尾に対応する
  anchors: dict[int, float] = {0: 0.0, count: duration_sec}
  for index in range(1, count):
    specified = shots[index].cut_time_sec
    if specified is not None:
      anchors[index] = specified
      resolved[index] = specified

  anchor_indices = sorted(anchors)
  for position, low in enumerate(anchor_indices[:-1]):
    high = anchor_indices[position + 1]
    gap = high - low
    if gap <= 1:
      continue
    low_value = anchors[low]
    high_value = anchors[high]
    for index in range(low + 1, high):
      ratio = (index - low) / gap
      resolved[index] = low_value + (high_value - low_value) * ratio

  # ミリ秒に丸めたうえで、単調増加が崩れないように補正する
  previous = 0.0
  for index in range(1, count):
    value = resolved[index]
    if value is None:
      continue
    value = round(value, 3)
    if value <= previous:
      value = round(previous + 0.001, 3)
    resolved[index] = value
    previous = value
  return resolved


def assign_speaker_ids(shots: list[Shot]) -> dict[str, str]:
  """話者名に登場順で S1, S2 … を割り当てる。"""
  mapping: dict[str, str] = {}
  for shot in shots:
    for dialogue in shot.dialogues:
      name = dialogue.speaker.strip()
      if name and name not in mapping:
        mapping[name] = f"S{len(mapping) + 1}"
  return mapping


def assign_asset_labels(assets: list[RefAsset]) -> list[str]:
  """参照アセットに種類ごとの連番ラベル(<Picture 1> など)を割り当てる。"""
  counters: dict[str, int] = {}
  labels: list[str] = []
  for asset in assets:
    # Enum のまま引くと str のキーに一致しないため value を使う
    name = ASSET_LABEL_NAMES.get(asset.kind.value, "Picture")
    counters[name] = counters.get(name, 0) + 1
    labels.append(f"<{name} {counters[name]}>")
  return labels


def load_system_prompt(mode: Mode) -> str:
  """方式に対応するシステムプロンプトを読み込み、共通ルールを差し込む。"""
  path = TEMPLATE_DIR / f"{mode.value}.md"
  if not path.exists():
    raise FileNotFoundError(f"テンプレートが見つかりません: {path.name}")
  template = path.read_text(encoding="utf-8")
  if COMMON_MARKER in template:
    common = (TEMPLATE_DIR / "_common.md").read_text(encoding="utf-8")
    template = template.replace(COMMON_MARKER, common.strip())
  return template


def _sound_section(title: str, option, fallback: str, silence_note: str) -> str:
  if option.none:
    return f"## {title}\n{silence_note}"
  if option.note.strip():
    return f"## {title}\nRequested by the user (Japanese): {option.note.strip()}"
  return f"## {title}\n{fallback}"


def _image_section(request: GenerateRequest) -> list[str]:
  """方式ごとの参照画像の説明を組み立てる。"""
  lines: list[str] = []
  descriptions = {image.role.value: image.description.strip() for image in request.images}

  if request.mode is Mode.I2VA:
    lines.append("## First frame — <Picture 1>, at 0.00 seconds, belongs to [Shot 1]")
    lines.append(f"Description (Japanese): {descriptions.get('first', 'not provided.')}")
  elif request.mode is Mode.FL2VA:
    lines.append("## First frame — Picture 1, at 0.00 seconds, the opening of [Shot 1]")
    lines.append(f"Description (Japanese): {descriptions.get('first', 'not provided.')}")
    lines.append("")
    lines.append("## Last frame — Picture 2, the very end of the final shot")
    lines.append(f"Description (Japanese): {descriptions.get('last', 'not provided.')}")
  elif request.mode is Mode.L2VA:
    lines.append("## Last frame — <Picture 1>, the very end of the final shot")
    lines.append(f"Description (Japanese): {descriptions.get('last', 'not provided.')}")
    lines.append(
      "This image is the ending, not the opening. Infer a plausible earlier state and converge on it."
    )
  return lines


def _asset_section(request: GenerateRequest, asset_labels: list[str]) -> list[str]:
  """RF2VA の参照アセット一覧を組み立てる。"""
  lines: list[str] = ["## Reference assets — use exactly these labels and numbers"]
  if not request.ref_assets:
    lines.append("No reference assets were provided.")
    return lines
  for asset, label in zip(request.ref_assets, asset_labels):
    role = asset.role.strip() or "not specified"
    description = asset.description.strip() or "not provided"
    lines.append(f"- {label} — role (Japanese): {role} — content (Japanese): {description}")
  return lines


def build_brief(
  request: GenerateRequest,
  cut_times: list[float | None],
  speaker_ids: dict[str, str],
  asset_labels: list[str],
) -> str:
  """ユーザー入力を LLM 向けのブリーフに整形する。"""
  lines: list[str] = ["# Brief", ""]
  lines.append(f"Video duration: {request.duration_sec:.2f} seconds")
  if request.style == "auto":
    if request.mode is Mode.T2VA:
      lines.append("Visual style: not specified — choose the style that fits the content below.")
    elif request.mode is Mode.RF2VA:
      lines.append(
        "Visual style: not specified — derive it from the reference assets described below."
      )
    else:
      lines.append(
        "Visual style: not specified — derive it from the frame descriptions below."
      )
  else:
    lines.append(f"Visual style: {request.style}")
  lines.append(f"Number of shots: {len(request.shots)}")
  lines.append("")

  # 参照情報(方式によって内容が変わる)
  reference_lines = (
    _asset_section(request, asset_labels)
    if request.mode is Mode.RF2VA
    else _image_section(request)
  )
  if reference_lines:
    lines += reference_lines
    lines.append("")

  # 話者 ID の対応表
  if speaker_ids:
    lines.append("## Speaker IDs — use exactly these IDs")
    for name, speaker_id in speaker_ids.items():
      lines.append(f"({speaker_id}) = {name}")
    lines.append("")

  # ショットごとの指示
  lines.append("## Shots")
  for index, shot in enumerate(request.shots):
    number = index + 1
    lines.append("")
    if number == 1:
      lines.append(f"### [Shot {number}] — no timestamp")
    else:
      timestamp = format_timestamp(cut_times[index] or 0.0)
      lines.append(
        f"### [Shot {number}] — must begin exactly with: [Shot {number}] At {timestamp}, "
      )
    lines.append(f"Content (Japanese): {shot.description.strip()}")
    if shot.camera.strip():
      lines.append(f"Camera (Japanese): {shot.camera.strip()}")
    else:
      lines.append("Camera: not specified — choose a motion that fits the action.")
    if shot.dialogues:
      lines.append("Dialogue — reproduce each line verbatim inside <d>, never translate it:")
      for dialogue in shot.dialogues:
        speaker_id = speaker_ids.get(dialogue.speaker.strip(), "S1")
        kind = "off-screen voiceover" if dialogue.voiceover else "on-screen speech"
        lines.append(
          f'- ({speaker_id}) {dialogue.speaker.strip()}, {kind}: '
          f'<d>[{dialogue.language.strip()}] {dialogue.text.strip()}</d>'
        )
    else:
      lines.append("Dialogue: none in this shot.")
  lines.append("")

  # 画面内テキスト
  texts = [text.strip() for text in request.on_screen_texts if text.strip()]
  if texts:
    lines.append("## On-screen text — must appear verbatim inside double quotation marks")
    for text in texts:
      lines.append(f'- "{text}"')
    lines.append("")

  # 音声関連
  lines.append(
    _sound_section(
      "Ambience (overall_soundscape)",
      request.ambience,
      "Not specified — derive it from the shot content.",
      "The user requests complete silence. Output exactly `N/A` for overall_soundscape.",
    )
  )
  lines.append("")
  lines.append(
    _sound_section(
      "Non-diegetic music",
      request.bgm,
      "Not specified — choose something that fits, or use `N/A` if music would not suit the scene.",
      "The user requests no non-diegetic music. Output exactly `N/A` for non_diegetic_music.",
    )
  )
  lines.append("")
  keys = ", ".join(f"`{key}`" for key in section_keys(request.mode))
  lines.append(f"Now return the JSON object with these keys: {keys}.")
  return "\n".join(lines)


def build_retry_message(violations: list[str]) -> str:
  """検証で見つかった違反を LLM に伝え直すメッセージ。"""
  listed = "\n".join(f"- {violation}" for violation in violations)
  return (
    "Your previous output violated the required format. Fix these problems and return the "
    "corrected JSON object with the same keys. Keep everything that was already correct.\n\n"
    f"{listed}"
  )


def assemble_prompt(mode: Mode, sections: dict[str, str], instruction: str) -> str:
  """指示行とフィールド名を付けて完成プロンプトを組み立てる。"""
  if mode is Mode.RF2VA:
    # フルリファレンスモードはフィールド名の次の行から本文が始まる
    body = "\n\n".join(f"{key}:\n{sections[key].strip()}" for key in section_keys(mode))
  else:
    body = "\n\n".join(f"{key}: {sections[key].strip()}" for key in section_keys(mode))
  return f"{instruction}\n\n{body}" if instruction else body
