<script setup lang="ts">
// 生成結果の表示・コピー・デバッグ表示
import { ref } from 'vue'

const props = defineProps<{
  prompt: string
  warnings: string[]
  retries: number
  loading: boolean
  error: string
  requestJson: string
  tall: boolean
}>()

// どのボタンでコピーしたかを覚えて、表示を切り替える
const copiedKey = ref<'prompt' | 'json' | ''>('')
const debugOpen = ref(false)

async function copyText(text: string, key: 'prompt' | 'json'): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    copiedKey.value = key
    window.setTimeout(() => {
      if (copiedKey.value === key) {
        copiedKey.value = ''
      }
    }, 1600)
  } catch {
    copiedKey.value = ''
  }
}
</script>

<template>
  <section class="card result">
    <div class="result__header">
      <div class="card__label">生成結果</div>
      <button
        v-if="prompt"
        type="button"
        class="btn btn--copy"
        @click="copyText(prompt, 'prompt')"
      >
        {{ copiedKey === 'prompt' ? 'コピーしました' : '結果をコピー' }}
      </button>
    </div>

    <p v-if="!loading && !prompt && !error" class="result__empty">
      入力を埋めて「プロンプトを生成」を押してください<br />(Ctrl / ⌘ + Enter でも生成できます)
    </p>

    <p v-if="loading" class="result__loading">生成中… 3〜30 秒ほどかかります</p>

    <p v-if="error" class="result__error">{{ error }}</p>

    <ul v-if="prompt && warnings.length > 0" class="result__warnings">
      <li v-for="(warning, index) in warnings" :key="index">{{ warning }}</li>
    </ul>

    <div v-if="prompt && retries > 0" class="result__retries">
      形式の検証に通すため {{ retries }} 回再生成しました
    </div>

    <pre v-if="prompt" class="result__text" :class="{ 'result__text--tall': tall }">{{
      prompt
    }}</pre>

    <div class="debug">
      <div class="debug__header">
        <button type="button" class="debug__toggle" @click="debugOpen = !debugOpen">
          <span class="debug__caret">{{ debugOpen ? '▼' : '▶' }}</span>デバッグ: 送信パラメーター
        </button>
        <button
          v-if="debugOpen"
          type="button"
          class="debug__copy"
          @click="copyText(props.requestJson, 'json')"
        >
          {{ copiedKey === 'json' ? 'コピーしました' : 'JSON をコピー' }}
        </button>
      </div>
      <pre v-if="debugOpen" class="debug__json">{{ requestJson }}</pre>
    </div>
  </section>
</template>
