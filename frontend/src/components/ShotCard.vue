<script setup lang="ts">
// ショット 1 つ分の入力。Shot 1 はカット時刻を持たない(ガイド仕様)
import DialogueList from '@/components/DialogueList.vue'
import type { Shot } from '@/types/api'

const props = defineProps<{
  shot: Shot
  index: number
}>()

const emit = defineEmits<{ remove: [] }>()

function onCutTimeInput(event: Event): void {
  const raw = (event.target as HTMLInputElement).value
  props.shot.cutTimeSec = raw === '' ? null : Number(raw)
}
</script>

<template>
  <div class="subcard">
    <div class="subcard__header">
      <div class="subcard__title">Shot {{ index + 1 }}</div>
      <button v-if="index > 0" type="button" class="btn btn--sm" @click="emit('remove')">
        削除
      </button>
    </div>

    <div v-if="index > 0" class="shot__cut-row">
      <input
        type="number"
        class="input input--plain input--sm shot__cut-input"
        step="0.1"
        min="0"
        placeholder="空欄なら自動配分"
        :value="shot.cutTimeSec ?? ''"
        @input="onCutTimeInput"
      />
      <div class="shot__cut-hint">
        カット時刻(秒)。空欄にすると、前後のショットとの間に均等配分されます
      </div>
    </div>
    <div v-else class="shot__note">
      Shot 1 にカット時刻はありません(動画の先頭から始まります)
    </div>

    <label class="field-label">内容の説明<span class="required">*</span></label>
    <textarea
      v-model="shot.description"
      class="input input--plain input--sm textarea shot__field"
      rows="3"
      placeholder="例: 雨の電車内で女性が手紙を読んでいる"
    ></textarea>

    <label class="field-label">カメラ指定</label>
    <input
      v-model="shot.camera"
      type="text"
      class="input input--plain input--sm"
      placeholder="例: ゆっくり右へ移動(空欄なら自動で決めます)"
    />

    <div class="shot__divider"></div>

    <DialogueList :dialogues="shot.dialogues" />
  </div>
</template>
