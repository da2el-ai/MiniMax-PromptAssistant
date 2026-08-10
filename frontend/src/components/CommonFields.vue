<script setup lang="ts">
// 全方式に共通する入力項目
import { STYLE_OPTIONS, type GenerateRequest } from '@/types/api'

const props = defineProps<{ form: GenerateRequest }>()

function onDurationInput(event: Event): void {
  const raw = (event.target as HTMLInputElement).value
  props.form.durationSec = raw === '' ? 0 : Number(raw)
}

function addOnScreenText(): void {
  props.form.onScreenTexts.push('')
}

function removeOnScreenText(index: number): void {
  props.form.onScreenTexts.splice(index, 1)
}
</script>

<template>
  <section class="card">
    <div class="card__label">共通設定</div>

    <div class="grid-2">
      <div>
        <label class="field-label">尺(秒)<span class="required">*</span></label>
        <input
          type="number"
          class="input"
          step="0.1"
          min="0.1"
          :value="form.durationSec"
          @input="onDurationInput"
        />
      </div>
      <div>
        <label class="field-label">スタイル</label>
        <select v-model="form.style" class="input select">
          <option v-for="option in STYLE_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </div>
    </div>

    <div class="divider"></div>

    <label class="field-label">画面内テキスト</label>
    <div class="hint hint--block">
      看板・字幕など、画面に実際に映る文字。原文のまま引用符に入ります
    </div>
    <div class="stack stack--tight">
      <div v-for="(_, index) in form.onScreenTexts" :key="index" class="row">
        <input
          v-model="form.onScreenTexts[index]"
          type="text"
          class="input"
          placeholder="例: 定休日"
        />
        <button type="button" class="btn--icon" title="削除" @click="removeOnScreenText(index)">
          ×
        </button>
      </div>
      <button type="button" class="btn--add" @click="addOnScreenText">+ テキストを追加</button>
    </div>

    <div class="divider"></div>

    <div class="stack">
      <div>
        <div class="field-label--row">
          <label class="field-label">環境音</label>
          <label class="checkbox">
            <input v-model="form.ambience.none" type="checkbox" />なし(N/A)
          </label>
        </div>
        <input
          v-model="form.ambience.note"
          type="text"
          class="input"
          :disabled="form.ambience.none"
          placeholder="例: 雨音と電車の走行音(空欄なら内容から自動生成)"
        />
        <div class="hint hint--top">「なし」は完全な無音を指定する意味になります</div>
      </div>
      <div>
        <div class="field-label--row">
          <label class="field-label">BGM</label>
          <label class="checkbox">
            <input v-model="form.bgm.none" type="checkbox" />なし(N/A)
          </label>
        </div>
        <input
          v-model="form.bgm.note"
          type="text"
          class="input"
          :disabled="form.bgm.none"
          placeholder="例: 静かなピアノ、スローテンポ"
        />
      </div>
    </div>
  </section>
</template>
