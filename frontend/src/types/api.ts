// バックエンド API の型定義。docs/SPEC.md「5. API 仕様」と一致させる

export type Mode = 't2va' | 'i2va' | 'fl2va' | 'l2va' | 'rf2va'

export type ImageRole = 'first' | 'last'

export type AssetKind = 'image' | 'video' | 'audio'

export interface Dialogue {
  speaker: string
  language: string
  text: string
  voiceover: boolean
}

export interface Shot {
  cutTimeSec: number | null
  description: string
  camera: string
  dialogues: Dialogue[]
}

export interface SoundOption {
  none: boolean
  note: string
}

export interface ImageDesc {
  role: ImageRole
  description: string
}

export interface RefAsset {
  kind: AssetKind
  role: string
  description: string
}

export interface GenerateRequest {
  mode: Mode
  durationSec: number
  style: string
  shots: Shot[]
  onScreenTexts: string[]
  ambience: SoundOption
  bgm: SoundOption
  images: ImageDesc[]
  refAssets: RefAsset[]
}

export interface GenerateResponse {
  prompt: string
  retries: number
  warnings: string[]
}

export interface HealthResponse {
  backend: boolean
  llm: boolean
  llmBaseUrl: string
  detail: string
}

// 方式の一覧
export const MODES: { value: Mode; label: string; description: string }[] = [
  { value: 't2va', label: 'T2VA(テキストのみ)', description: '参照画像なし。文章だけから映像を組み立てる' },
  { value: 'i2va', label: 'I2VA(最初のフレーム)', description: '1 枚目を動画の最初のフレームとして使う' },
  { value: 'fl2va', label: 'FL2VA(最初と最後のフレーム)', description: '最初と最後を指定し、その間の変化を描く' },
  { value: 'l2va', label: 'L2VA(最後のフレーム)', description: '最後の 1 枚に着地するように組み立てる' },
  { value: 'rf2va', label: 'RF2VA(フルリファレンス)', description: '画像・動画・音声を複数参照する高度なモード' },
]

// バックエンドが生成に対応している方式。未対応の方式は選べるが生成するとエラーになる
export const SUPPORTED_MODES: Mode[] = ['t2va', 'i2va', 'fl2va', 'l2va', 'rf2va']

// スタイルの選択肢。auto は参照画像の説明から推定させる
export const STYLE_OPTIONS: { value: string; label: string }[] = [
  { value: 'auto', label: '自動(参照から推定)' },
  { value: 'Cinematic', label: 'Cinematic' },
  { value: 'live-action', label: 'live-action(実写)' },
  { value: '2D-animated', label: '2D-animated(2Dアニメ)' },
  { value: '3D CG', label: '3D CG' },
  { value: 'claymation', label: 'claymation(クレイアニメ)' },
  { value: 'watercolor', label: 'watercolor(水彩)' },
  { value: 'vintage film', label: 'vintage film(古いフィルム)' },
]

// セリフの言語タグ。<d>[言語] に入る英語表記
export const LANGUAGE_OPTIONS = ['Japanese', 'English', 'Chinese', 'Korean'] as const

// RF2VA の参照アセット
export const ASSET_KINDS: { value: AssetKind; label: string }[] = [
  { value: 'image', label: '画像' },
  { value: 'video', label: '動画' },
  { value: 'audio', label: '音声' },
]

export const ASSET_ROLES: Record<AssetKind, string[]> = {
  image: [
    '人物の外見参照',
    'シーン・背景参照',
    '衣装・小道具参照',
    'スタイル参照',
    '最初のフレーム',
    '最後のフレーム',
    'ストーリーボード',
  ],
  video: ['編集元の動画', '継続元の動画', '動きの参照', 'カメラワークの参照', '人物の外見参照'],
  audio: ['声質の参照', 'BGM をそのまま使う', 'セリフ・歌詞の流用', '効果音の参照', 'リズムの参照'],
}
