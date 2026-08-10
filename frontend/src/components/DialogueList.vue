<script setup lang="ts">
// セリフ行の追加・削除。本文は逐語で <d> に入るため翻訳されない
import { computed } from 'vue'

import { LANGUAGE_OPTIONS, type Dialogue } from '@/types/api'

const props = defineProps<{ dialogues: Dialogue[] }>()

const hint = computed(() =>
  props.dialogues.length === 0
    ? 'このショットにセリフはありません。入力した本文はそのままの言語で保持されます'
    : '同じ人物には同じ話者名を使ってください。話者 ID(S1, S2 …)は登場順に自動で割り当てられます',
)

function addDialogue(): void {
  props.dialogues.push({ speaker: '', language: 'Japanese', text: '', voiceover: false })
}

function removeDialogue(index: number): void {
  props.dialogues.splice(index, 1)
}
</script>

<template>
  <div>
    <div class="dialogue__title">セリフ</div>
    <div class="hint hint--block">{{ hint }}</div>
    <div class="stack stack--tight">
      <div v-for="(dialogue, index) in dialogues" :key="index" class="dialogue__row">
        <input
          v-model="dialogue.speaker"
          type="text"
          class="input input--plain input--sm dialogue__speaker"
          placeholder="話者名(例: 女性)"
        />
        <select
          v-model="dialogue.language"
          class="input input--plain input--sm select dialogue__lang"
        >
          <option v-for="language in LANGUAGE_OPTIONS" :key="language" :value="language">
            {{ language }}
          </option>
        </select>
        <input
          v-model="dialogue.text"
          type="text"
          class="input input--plain input--sm dialogue__text"
          placeholder="セリフ本文(原文のまま保持されます)"
        />
        <label class="checkbox">
          <input v-model="dialogue.voiceover" type="checkbox" />画面外
        </label>
        <button type="button" class="btn--icon" title="削除" @click="removeDialogue(index)">
          ×
        </button>
      </div>
      <button type="button" class="btn--add btn--add-on-white" @click="addDialogue">
        + セリフを追加
      </button>
    </div>
  </div>
</template>
