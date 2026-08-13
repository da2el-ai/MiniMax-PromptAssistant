// 入力内容と直前の生成結果を localStorage に保存・復元する
//
// 保存データは古い版が残っている可能性があるため、復元時に必ず形を検査して
// 不正な値は初期値で補う。壊れたデータで画面が表示できなくなるのを防ぐ。

import {
  ASSET_KINDS,
  MODES,
  type AssetKind,
  type Dialogue,
  type GenerateRequest,
  type ImageDesc,
  type ImageRole,
  type Mode,
  type RefAsset,
  type Shot,
  type SoundOption,
} from '@/types/api'
import { createInitialRequest } from '@/utils/form'

const FORM_KEY = 'minimax-prompt-assistant:form:v1'
const RESULT_KEY = 'minimax-prompt-assistant:result:v1'
const SAVED_KEY = 'minimax-prompt-assistant:saved:v1'
const TITLE_KEY = 'minimax-prompt-assistant:title:v1'

export interface SavedResult {
  prompt: string
  warnings: string[]
  retries: number
  requestJson: string
}

/** タイトルを付けて保存したプロンプト 1 件分。 */
export interface SavedPrompt {
  title: string
  request: GenerateRequest
  /** 生成結果。まだ生成していない状態で保存した場合は空 */
  prompt: string
  warnings: string[]
  retries: number
}

const VALID_MODES = new Set<string>(MODES.map((mode) => mode.value))
const VALID_ROLES = new Set<string>(['first', 'last'])
const VALID_KINDS = new Set<string>(ASSET_KINDS.map((kind) => kind.value))

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asNullableNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function toDialogue(raw: unknown): Dialogue {
  const record = isRecord(raw) ? raw : {}
  return {
    speaker: asString(record.speaker),
    language: asString(record.language, 'Japanese'),
    text: asString(record.text),
    voiceover: asBoolean(record.voiceover),
  }
}

function toShot(raw: unknown): Shot {
  const record = isRecord(raw) ? raw : {}
  return {
    cutTimeSec: asNullableNumber(record.cutTimeSec),
    description: asString(record.description),
    camera: asString(record.camera),
    dialogues: asArray(record.dialogues).map(toDialogue),
  }
}

function toSoundOption(raw: unknown): SoundOption {
  const record = isRecord(raw) ? raw : {}
  return { none: asBoolean(record.none), note: asString(record.note) }
}

function toImageDesc(raw: unknown): ImageDesc | null {
  const record = isRecord(raw) ? raw : {}
  const role = asString(record.role)
  if (!VALID_ROLES.has(role)) {
    return null
  }
  return { role: role as ImageRole, description: asString(record.description) }
}

function toRefAsset(raw: unknown): RefAsset {
  const record = isRecord(raw) ? raw : {}
  const kind = asString(record.kind)
  return {
    kind: (VALID_KINDS.has(kind) ? kind : 'image') as AssetKind,
    role: asString(record.role),
    description: asString(record.description),
    // tag は後から追加した項目。古い保存データには存在しない
    tag: asString(record.tag),
  }
}

/** 保存データを現在の形に整える。壊れていれば初期値で補う。
 *
 * 値をすべて作り直すため、結果は元データと参照を共有しない。保存プロンプトを
 * フォームへ復元するときは、この性質を使ってディープコピー代わりに使う。
 */
export function normalizeRequest(raw: unknown): GenerateRequest {
  const fallback = createInitialRequest()
  if (!isRecord(raw)) {
    return fallback
  }

  const mode = asString(raw.mode)
  const shots = asArray(raw.shots).map(toShot)
  const images = asArray(raw.images)
    .map(toImageDesc)
    .filter((image) => image !== null)

  return {
    mode: VALID_MODES.has(mode) ? (mode as Mode) : fallback.mode,
    durationSec: asNumber(raw.durationSec, fallback.durationSec),
    style: asString(raw.style, fallback.style),
    // ショットは最低 1 つ必要
    shots: shots.length > 0 ? shots : fallback.shots,
    onScreenTexts: asArray(raw.onScreenTexts).map((text) => asString(text)),
    ambience: toSoundOption(raw.ambience),
    bgm: toSoundOption(raw.bgm),
    images,
    refAssets: asArray(raw.refAssets).map(toRefAsset),
  }
}

export function loadRequest(): GenerateRequest | null {
  try {
    const saved = window.localStorage.getItem(FORM_KEY)
    return saved === null ? null : normalizeRequest(JSON.parse(saved))
  } catch {
    // 壊れたデータは無視して初期状態から始める
    return null
  }
}

export function saveRequest(request: GenerateRequest): void {
  try {
    window.localStorage.setItem(FORM_KEY, JSON.stringify(request))
  } catch {
    // 保存領域が使えない場合(プライベートモードなど)は保存をあきらめる
  }
}

export function loadResult(): SavedResult | null {
  try {
    const saved = window.localStorage.getItem(RESULT_KEY)
    if (saved === null) {
      return null
    }
    const raw: unknown = JSON.parse(saved)
    if (!isRecord(raw)) {
      return null
    }
    return {
      prompt: asString(raw.prompt),
      warnings: asArray(raw.warnings).map((warning) => asString(warning)),
      retries: asNumber(raw.retries, 0),
      requestJson: asString(raw.requestJson),
    }
  } catch {
    return null
  }
}

export function saveResult(result: SavedResult): void {
  try {
    window.localStorage.setItem(RESULT_KEY, JSON.stringify(result))
  } catch {
    // 保存できなくても生成自体には影響しない
  }
}

function toSavedPrompt(raw: unknown): SavedPrompt | null {
  const record = isRecord(raw) ? raw : {}
  const title = asString(record.title).trim()
  // タイトルは一覧の見出しであり同名判定のキーでもあるため、空の行は捨てる
  if (title === '') {
    return null
  }
  return {
    title,
    request: normalizeRequest(record.request),
    prompt: asString(record.prompt),
    warnings: asArray(record.warnings).map((warning) => asString(warning)),
    retries: asNumber(record.retries, 0),
  }
}

/** 保存プロンプトの一覧を読み込む。先頭が最新。 */
export function loadSavedPrompts(): SavedPrompt[] {
  try {
    const saved = window.localStorage.getItem(SAVED_KEY)
    if (saved === null) {
      return []
    }
    return asArray(JSON.parse(saved))
      .map(toSavedPrompt)
      .filter((item) => item !== null)
  } catch {
    return []
  }
}

/** 保存プロンプトの一覧を書き込む。容量オーバーなどで書けなければ false を返す。
 *
 * 利用者が意図して押した保存が失敗したことは伝える必要があるため、
 * ほかの保存関数と違って結果を返す。
 */
export function saveSavedPrompts(items: SavedPrompt[]): boolean {
  try {
    window.localStorage.setItem(SAVED_KEY, JSON.stringify(items))
    return true
  } catch {
    return false
  }
}

export function loadTitle(): string {
  try {
    return asString(window.localStorage.getItem(TITLE_KEY))
  } catch {
    return ''
  }
}

export function saveTitle(title: string): void {
  try {
    window.localStorage.setItem(TITLE_KEY, title)
  } catch {
    // 保存領域が使えない場合(プライベートモードなど)は保存をあきらめる
  }
}

/** 入力・生成結果・タイトルを消す。保存プロンプトは意図的に残す。 */
export function clearStorage(): void {
  try {
    window.localStorage.removeItem(FORM_KEY)
    window.localStorage.removeItem(RESULT_KEY)
    window.localStorage.removeItem(TITLE_KEY)
  } catch {
    // 何もしない
  }
}
