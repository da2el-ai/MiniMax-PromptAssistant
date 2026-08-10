<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

import { fetchHealth, generatePrompt } from '@/api/client'
import ClearDialog from '@/components/ClearDialog.vue'
import CommonFields from '@/components/CommonFields.vue'
import ImageDescFields from '@/components/ImageDescFields.vue'
import ModeSelector from '@/components/ModeSelector.vue'
import RefAssetList from '@/components/RefAssetList.vue'
import ResultPanel from '@/components/ResultPanel.vue'
import ShotList from '@/components/ShotList.vue'
import type { GenerateRequest } from '@/types/api'
import { createInitialRequest, requiredImageRoles } from '@/utils/form'
import { clearStorage, loadRequest, loadResult, saveRequest, saveResult } from '@/utils/storage'

// 前回の入力内容があれば復元する
const form = reactive<GenerateRequest>(loadRequest() ?? createInitialRequest())

const savedResult = loadResult()
const prompt = ref(savedResult?.prompt ?? '')
const warnings = ref<string[]>(savedResult?.warnings ?? [])
const retries = ref(savedResult?.retries ?? 0)
const loading = ref(false)
const error = ref('')
const clearOpen = ref(false)

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

// 疎通状態は 5 秒間隔でポーリングして更新する
const HEALTH_INTERVAL_MS = 5000
const llmOk = ref(false)
const llmStatus = ref('確認中…')
let healthTimer: number | undefined

async function pollHealth(): Promise<void> {
  try {
    const health = await fetchHealth()
    llmOk.value = health.llm
    llmStatus.value = health.llm
      ? `llama-server に接続できます(${health.llmBaseUrl})`
      : `llama-server に接続できません(${health.llmBaseUrl}): ${health.detail}`
  } catch (caught) {
    llmOk.value = false
    llmStatus.value = `バックエンドに接続できません: ${(caught as Error).message}`
  }
}

/** Ctrl + Enter / Command + Enter で生成する。 */
function onKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault()
    if (!loading.value) {
      void submit()
    }
  }
}

onMounted(() => {
  void pollHealth()
  healthTimer = window.setInterval(() => void pollHealth(), HEALTH_INTERVAL_MS)
  window.addEventListener('keydown', onKeydown)
  // 再読み込みや閉じる操作では onUnmounted が呼ばれないため、ここでも保存する
  window.addEventListener('beforeunload', flushSave)
})

onUnmounted(() => {
  if (healthTimer !== undefined) {
    window.clearInterval(healthTimer)
  }
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

/** 入力と生成結果を初期状態に戻す。 */
function resetAll(): void {
  clearOpen.value = false
  Object.assign(form, createInitialRequest(form.mode))
  prompt.value = ''
  warnings.value = []
  retries.value = 0
  error.value = ''
  clearStorage()
}
</script>

<template>
  <header class="topbar">
    <div class="topbar__left">
      <h1 class="topbar__title">MiniMax-H3 プロンプト作成アシスタント</h1>
      <div class="conn" :class="llmOk ? 'conn--ok' : 'conn--ng'">
        <span class="conn__dot" aria-hidden="true"></span>
        <span class="conn__text">{{ llmStatus }}</span>
      </div>
    </div>
    <button type="button" class="btn" @click="clearOpen = true">入力をクリア</button>
  </header>

  <main class="main">
    <!-- form 要素にすると入力欄での Enter が生成を起動してしまうため div にする -->
    <div class="col col--form">
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
        :prompt="prompt"
        :warnings="warnings"
        :retries="retries"
        :loading="loading"
        :error="error"
        :request-json="requestJson"
        :tall="form.mode === 'rf2va'"
      />
    </div>
  </main>

  <ClearDialog v-if="clearOpen" @cancel="clearOpen = false" @confirm="resetAll" />
</template>
