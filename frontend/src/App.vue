<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

import { fetchHealth, generatePrompt } from '@/api/client'
import CommonFields from '@/components/CommonFields.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ImageDescFields from '@/components/ImageDescFields.vue'
import ModeSelector from '@/components/ModeSelector.vue'
import RefAssetList from '@/components/RefAssetList.vue'
import ResultPanel from '@/components/ResultPanel.vue'
import SavedPromptList from '@/components/SavedPromptList.vue'
import ShotList from '@/components/ShotList.vue'
import TitleField from '@/components/TitleField.vue'
import type { GenerateRequest } from '@/types/api'
import { createInitialRequest, normalizeAssetTag, requiredImageRoles } from '@/utils/form'
import {
  clearStorage,
  loadRequest,
  loadResult,
  loadSavedPrompts,
  loadTitle,
  normalizeRequest,
  saveRequest,
  saveResult,
  saveSavedPrompts,
  saveTitle,
  type SavedPrompt,
} from '@/utils/storage'

// 前回の入力内容があれば復元する
const form = reactive<GenerateRequest>(loadRequest() ?? createInitialRequest())

const savedResult = loadResult()
const prompt = ref(savedResult?.prompt ?? '')
const warnings = ref<string[]>(savedResult?.warnings ?? [])
const retries = ref(savedResult?.retries ?? 0)
const loading = ref(false)
const error = ref('')

// 保存機能。タイトルは入力の一部としてリロードをまたいで残す
const title = ref(loadTitle())
const savedPrompts = ref<SavedPrompt[]>(loadSavedPrompts())
const titleSaved = ref(false)
const titleError = ref('')

watch(title, (value) => saveTitle(value))

// 入力に変更があったら保存する。連続入力でも書き込みが増えすぎないよう少し待つ
const SAVE_DELAY_MS = 300
let saveTimer: number | undefined

watch(
  form,
  () => {
    if (saveTimer !== undefined) {
      window.clearTimeout(saveTimer)
    }
    saveTimer = window.setTimeout(() => saveRequest(form), SAVE_DELAY_MS)
  },
  { deep: true },
)

/** 保存待ちの変更をすぐ書き込む。 */
function flushSave(): void {
  if (saveTimer !== undefined) {
    window.clearTimeout(saveTimer)
    saveTimer = undefined
  }
  saveRequest(form)
}

// 疎通状態は起動時に一度だけ確認する。外部の従量課金 API でも
// 待機中に費用が発生しないよう、以降はボタン操作でのみ確認する
const llmOk = ref(false)
const llmChecking = ref(false)
const llmStatus = ref('接続を確認中…')

async function checkHealth(): Promise<void> {
  llmChecking.value = true
  llmStatus.value = '接続を確認中…'
  try {
    const health = await fetchHealth()
    llmOk.value = health.llm
    llmStatus.value = health.llm
      ? `LLM API に接続できます(${health.llmBaseUrl})`
      : `LLM API に接続できません(${health.llmBaseUrl}): ${health.detail}`
  } catch (caught) {
    llmOk.value = false
    llmStatus.value = `バックエンドに接続できません: ${(caught as Error).message}`
  } finally {
    llmChecking.value = false
  }
}

// 確認中はドットを中立色(既定色)のままにする
const connClass = computed(() => {
  if (llmChecking.value) {
    return ''
  }
  return llmOk.value ? 'conn--ok' : 'conn--ng'
})

// ショートカットからコピーを呼ぶために ResultPanel を参照する
const resultPanel = ref<InstanceType<typeof ResultPanel> | null>(null)

/**
 * Ctrl / Command + Enter で生成し、Alt / Option + Enter で生成結果をコピーする。
 */
function onKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter') {
    return
  }
  if (event.altKey) {
    event.preventDefault()
    void resultPanel.value?.copyPrompt()
    return
  }
  if (event.ctrlKey || event.metaKey) {
    event.preventDefault()
    if (!loading.value) {
      void submit()
    }
  }
}

onMounted(() => {
  void checkHealth()
  window.addEventListener('keydown', onKeydown)
  // 再読み込みや閉じる操作では onUnmounted が呼ばれないため、ここでも保存する
  window.addEventListener('beforeunload', flushSave)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('beforeunload', flushSave)
  flushSave()
})

/** 方式に関係のない項目を除いた送信用のデータを作る。 */
const payload = computed<GenerateRequest>(() => {
  const roles = requiredImageRoles(form.mode)
  return {
    mode: form.mode,
    durationSec: form.durationSec,
    style: form.style,
    shots: form.shots.map((shot, index) => ({
      // Shot 1 のカット時刻は常に null
      cutTimeSec: index === 0 ? null : shot.cutTimeSec,
      description: shot.description.trim(),
      camera: shot.camera.trim(),
      dialogues: shot.dialogues.map((dialogue) => ({
        speaker: dialogue.speaker.trim(),
        language: dialogue.language,
        text: dialogue.text.trim(),
        voiceover: dialogue.voiceover,
      })),
    })),
    onScreenTexts: form.onScreenTexts.map((text) => text.trim()).filter((text) => text !== ''),
    ambience: {
      none: form.ambience.none,
      note: form.ambience.none ? '' : form.ambience.note.trim(),
    },
    bgm: { none: form.bgm.none, note: form.bgm.none ? '' : form.bgm.note.trim() },
    images: form.images
      .filter((image) => roles.includes(image.role))
      .map((image) => ({ role: image.role, description: image.description.trim() })),
    refAssets:
      form.mode === 'rf2va'
        ? form.refAssets.map((asset) => ({
            kind: asset.kind,
            role: asset.role.trim(),
            description: asset.description.trim(),
            tag: normalizeAssetTag(asset.tag),
          }))
        : [],
  }
})

const requestJson = computed(() => JSON.stringify(payload.value, null, 2))

/** 送信前の入力チェック。問題があればメッセージを返す。 */
function validateForm(): string {
  if (!(form.durationSec > 0)) {
    return '尺は 0 より大きい値を入力してください。'
  }
  for (const role of requiredImageRoles(form.mode)) {
    const image = form.images.find((item) => item.role === role)
    if (!image?.description.trim()) {
      return '参照画像の説明を入力してください。'
    }
  }
  if (form.mode === 'rf2va') {
    // 参照タグはネイティブラベルと混在させられないので、全アセットで統一させる
    const tags = form.refAssets.map((asset) => normalizeAssetTag(asset.tag))
    if (tags.some((tag) => tag !== '') && tags.some((tag) => tag === '')) {
      return '参照タグを使う場合は、すべての参照アセットにタグを入力してください。'
    }
    for (const tag of tags) {
      if (tag !== '' && !/^[A-Za-z0-9_]+$/.test(tag)) {
        return `参照タグ「${tag}」は半角英数字とアンダースコアだけで指定してください。`
      }
      if (tag !== '' && tags.filter((item) => item === tag).length > 1) {
        return `参照タグ「@${tag}」が重複しています。`
      }
    }
  }
  for (const [index, shot] of form.shots.entries()) {
    if (!shot.description.trim()) {
      return `Shot ${index + 1} の内容の説明を入力してください。`
    }
    if (shot.cutTimeSec !== null && shot.cutTimeSec >= form.durationSec) {
      return `Shot ${index + 1} のカット時刻は尺(${form.durationSec} 秒)未満にしてください。`
    }
    for (const dialogue of shot.dialogues) {
      if (!dialogue.speaker.trim() || !dialogue.text.trim()) {
        return `Shot ${index + 1} のセリフに話者名と本文を入力してください。`
      }
    }
  }
  return ''
}

async function submit(): Promise<void> {
  const message = validateForm()
  if (message) {
    error.value = message
    prompt.value = ''
    warnings.value = []
    retries.value = 0
    return
  }

  loading.value = true
  error.value = ''
  warnings.value = []
  prompt.value = ''
  try {
    const response = await generatePrompt(payload.value)
    prompt.value = response.prompt
    warnings.value = response.warnings
    retries.value = response.retries
    saveResult({
      prompt: response.prompt,
      warnings: response.warnings,
      retries: response.retries,
      requestJson: requestJson.value,
    })
  } catch (caught) {
    error.value = (caught as Error).message
  } finally {
    loading.value = false
  }
}

/** 入力と生成結果を初期状態に戻す。保存プロンプトは残す。 */
function resetAll(): void {
  Object.assign(form, createInitialRequest(form.mode))
  title.value = ''
  prompt.value = ''
  warnings.value = []
  retries.value = 0
  error.value = ''
  titleError.value = ''
  clearStorage()
}

// ---- 保存プロンプト ----

// 「保存しました」表示を戻すためのタイマー
const SAVED_FLASH_MS = 1600
let flashTimer: number | undefined

function flashSaved(): void {
  titleSaved.value = true
  if (flashTimer !== undefined) {
    window.clearTimeout(flashTimer)
  }
  flashTimer = window.setTimeout(() => {
    titleSaved.value = false
  }, SAVED_FLASH_MS)
}

/** 今の入力と生成結果を、指定したタイトルで保存する。同名があれば置き換える。 */
function storePrompt(name: string): void {
  const entry: SavedPrompt = {
    title: name,
    // normalizeRequest は値を作り直すので、フォームと参照を共有しない
    request: normalizeRequest(form),
    prompt: prompt.value,
    warnings: [...warnings.value],
    retries: retries.value,
  }
  // 同名を取り除いてから先頭に置くことで、上書きしたものが最新として並ぶ
  const next = [entry, ...savedPrompts.value.filter((item) => item.title !== name)]
  if (!saveSavedPrompts(next)) {
    titleError.value = '保存できませんでした。ブラウザの保存領域が一杯の可能性があります。'
    return
  }
  savedPrompts.value = next
  titleError.value = ''
  flashSaved()
}

/** 保存ボタンの入口。同名があれば上書き確認をはさむ。 */
function requestSave(): void {
  const name = title.value.trim()
  if (name === '') {
    titleError.value = 'タイトルを入力してください。'
    return
  }
  titleError.value = ''
  if (savedPrompts.value.some((item) => item.title === name)) {
    dialog.value = { kind: 'overwrite', name }
    return
  }
  storePrompt(name)
}

/** 保存プロンプトを入力とタイトルと生成結果に復元する。 */
function restoreSaved(index: number): void {
  const item = savedPrompts.value[index]
  if (!item) {
    return
  }
  Object.assign(form, normalizeRequest(item.request))
  title.value = item.title
  prompt.value = item.prompt
  warnings.value = [...item.warnings]
  retries.value = item.retries
  error.value = ''
  titleError.value = ''
  // リロードしたときに復元した内容と食い違わないよう、直前の結果も更新する
  saveResult({
    prompt: item.prompt,
    warnings: item.warnings,
    retries: item.retries,
    requestJson: requestJson.value,
  })
}

function removeSaved(index: number): void {
  const next = savedPrompts.value.filter((_, position) => position !== index)
  saveSavedPrompts(next)
  savedPrompts.value = next
}

// ---- 確認ダイアログ ----

type DialogState =
  | { kind: 'clear' }
  | { kind: 'overwrite'; name: string }
  | { kind: 'remove'; index: number }

const dialog = ref<DialogState | null>(null)

const dialogProps = computed(() => {
  const current = dialog.value
  if (current === null) {
    return null
  }
  if (current.kind === 'clear') {
    return {
      title: '入力をクリアしますか?',
      body:
        '入力内容と生成結果が初期状態に戻ります。この操作は取り消せません。' +
        '保存プロンプトは残ります。',
      confirmLabel: 'クリアする',
      danger: true,
    }
  }
  if (current.kind === 'overwrite') {
    return {
      title: '上書きしますか?',
      body: `「${current.name}」はすでに保存されています。今の入力と生成結果で上書きします。`,
      confirmLabel: '上書きする',
      danger: false,
    }
  }
  const target = savedPrompts.value[current.index]
  return {
    title: '保存プロンプトを削除しますか?',
    body: `「${target?.title ?? ''}」を削除します。この操作は取り消せません。`,
    confirmLabel: '削除する',
    danger: true,
  }
})

function confirmDialog(): void {
  const current = dialog.value
  dialog.value = null
  if (current === null) {
    return
  }
  if (current.kind === 'clear') {
    resetAll()
  } else if (current.kind === 'overwrite') {
    storePrompt(current.name)
  } else {
    removeSaved(current.index)
  }
}
</script>

<template>
  <header class="topbar">
    <div class="topbar__left">
      <h1 class="topbar__title">MiniMax-H3 プロンプト作成アシスタント</h1>
      <div class="conn" :class="connClass">
        <span class="conn__dot" aria-hidden="true"></span>
        <span class="conn__text">{{ llmStatus }}</span>
      </div>
    </div>
    <div class="topbar__actions">
      <button type="button" class="btn" :disabled="llmChecking" @click="checkHealth">
        {{ llmChecking ? '確認中…' : '接続確認' }}
      </button>
      <button type="button" class="btn" @click="dialog = { kind: 'clear' }">入力をクリア</button>
    </div>
  </header>

  <main class="main">
    <!-- form 要素にすると入力欄での Enter が生成を起動してしまうため div にする -->
    <div class="col col--form">
      <TitleField v-model="title" :saved="titleSaved" :error="titleError" @save="requestSave" />
      <ModeSelector v-model="form.mode" />
      <CommonFields :form="form" />
      <ImageDescFields :images="form.images" :mode="form.mode" />
      <RefAssetList v-if="form.mode === 'rf2va'" :assets="form.refAssets" />
      <ShotList :shots="form.shots" :mode="form.mode" />
    </div>

    <div class="col col--result">
      <button type="button" class="btn--generate" :disabled="loading" @click="submit">
        <span v-if="loading" class="spinner" aria-hidden="true"></span>
        <span>{{ loading ? '生成中…' : 'プロンプトを生成' }}</span>
        <span v-if="!loading" class="btn__shortcut">Ctrl / ⌘ + Enter</span>
      </button>

      <ResultPanel
        ref="resultPanel"
        :prompt="prompt"
        :warnings="warnings"
        :retries="retries"
        :loading="loading"
        :error="error"
        :request-json="requestJson"
        :tall="form.mode === 'rf2va'"
      />

      <SavedPromptList
        :items="savedPrompts"
        @restore="restoreSaved"
        @remove="dialog = { kind: 'remove', index: $event }"
      />
    </div>
  </main>

  <ConfirmDialog
    v-if="dialogProps"
    v-bind="dialogProps"
    @cancel="dialog = null"
    @confirm="confirmDialog"
  />
</template>
