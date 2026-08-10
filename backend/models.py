"""API のリクエスト/レスポンス モデル。

docs/SPEC.md の「5. API 仕様」に対応する。
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
  """JSON では camelCase、Python 側では snake_case を使うための基底クラス。"""

  model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Mode(str, Enum):
  """生成方式。"""

  T2VA = "t2va"
  I2VA = "i2va"
  FL2VA = "fl2va"
  L2VA = "l2va"
  RF2VA = "rf2va"


class ImageRole(str, Enum):
  """参照画像の役割。"""

  FIRST = "first"  # 最初のフレーム
  LAST = "last"  # 最後のフレーム


class Dialogue(CamelModel):
  """セリフ 1 行。text は逐語で <d> 内に入るため翻訳・改変しない。"""

  speaker: str = Field(..., min_length=1, description="話者名。ショット間で同一人物なら同じ名前を使う")
  language: str = Field(default="Japanese", min_length=1, description="<d>[言語] に入る言語名(英語表記)")
  text: str = Field(..., min_length=1, description="セリフ本文。原文のまま保持される")
  voiceover: bool = Field(default=False, description="画面外のボイスオーバーかどうか")


class Shot(CamelModel):
  """ショット 1 つ分の入力。"""

  cut_time_sec: float | None = Field(
    default=None, ge=0, description="カット時刻(秒)。Shot 1 は常に None。None なら LLM が自動配分"
  )
  description: str = Field(..., min_length=1, description="内容の説明(日本語)")
  camera: str = Field(default="", description="カメラ指定(日本語)。未指定なら LLM に委ねる")
  dialogues: list[Dialogue] = Field(default_factory=list)


class SoundOption(CamelModel):
  """環境音 / BGM の指定。none = True なら N/A 固定。"""

  none: bool = Field(default=False, description="True なら N/A(環境音は完全な無音、BGM は無し)")
  note: str = Field(default="", description="希望内容(日本語)")


class ImageDesc(CamelModel):
  """参照画像の説明。ビジョンモデルは使わずユーザーが日本語で記述する。"""

  role: ImageRole
  description: str = Field(..., min_length=1, description="画像の内容説明(日本語)")


class AssetKind(str, Enum):
  """参照アセットの種類。ラベル(<Picture N> など)の割り当てに使う。"""

  IMAGE = "image"
  VIDEO = "video"
  AUDIO = "audio"


class RefAsset(CamelModel):
  """RF2VA の参照アセット。"""

  kind: AssetKind
  role: str = Field(default="", description="役割(日本語)")
  description: str = Field(default="", description="内容の説明(日本語)")


class GenerateRequest(CamelModel):
  """POST /api/generate のリクエスト。"""

  mode: Mode
  duration_sec: float = Field(..., gt=0, le=600, description="動画の尺(秒)")
  style: str = Field(default="auto", description="スタイル名または auto")
  shots: list[Shot] = Field(..., min_length=1)
  on_screen_texts: list[str] = Field(default_factory=list, description="画面内テキスト(原文のまま)")
  ambience: SoundOption = Field(default_factory=SoundOption)
  bgm: SoundOption = Field(default_factory=SoundOption)
  images: list[ImageDesc] = Field(default_factory=list)
  ref_assets: list[RefAsset] = Field(default_factory=list)

  @field_validator("shots")
  @classmethod
  def _validate_shots(cls, shots: list[Shot]) -> list[Shot]:
    # Shot 1 にカット時刻は付けない(ガイド仕様)
    if shots[0].cut_time_sec is not None:
      raise ValueError("Shot 1 にカット時刻は指定できません")
    # 指定されたカット時刻は単調増加でなければならない
    previous = 0.0
    for index, shot in enumerate(shots[1:], start=2):
      if shot.cut_time_sec is None:
        continue
      if shot.cut_time_sec <= previous:
        raise ValueError(f"Shot {index} のカット時刻は直前のショットより後にしてください")
      previous = shot.cut_time_sec
    return shots

  def model_post_init(self, _context: object) -> None:
    # 指定されたカット時刻が尺の範囲内かを確認する
    for index, shot in enumerate(self.shots[1:], start=2):
      if shot.cut_time_sec is not None and shot.cut_time_sec >= self.duration_sec:
        raise ValueError(f"Shot {index} のカット時刻は尺({self.duration_sec}秒)未満にしてください")


class GenerateResponse(CamelModel):
  """POST /api/generate のレスポンス。"""

  prompt: str = Field(..., description="完成した英語プロンプト全文")
  retries: int = Field(default=0, description="検証 NG による再生成回数")
  warnings: list[str] = Field(default_factory=list, description="注意が必要な点(日本語)")


class HealthResponse(CamelModel):
  """GET /api/health のレスポンス。"""

  backend: bool = True
  llm: bool = False
  llm_base_url: str = ""
  detail: str = ""
