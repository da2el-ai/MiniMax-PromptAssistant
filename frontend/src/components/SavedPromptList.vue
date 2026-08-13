<script setup lang="ts">
// 保存したプロンプトの一覧。新しいものが上に並ぶ
import type { SavedPrompt } from '@/utils/storage'

defineProps<{ items: SavedPrompt[] }>()

const emit = defineEmits<{ restore: [index: number]; remove: [index: number] }>()
</script>

<template>
  <section class="card">
    <div class="card__label">保存プロンプト</div>

    <p v-if="items.length === 0" class="result__empty">
      保存したプロンプトはまだありません<br />(タイトルを入れて「保存」を押すとここに並びます)
    </p>

    <ul v-else class="saved">
      <li v-for="(item, index) in items" :key="index" class="saved__item">
        <button
          type="button"
          class="saved__title"
          :title="item.title"
          @click="emit('restore', index)"
        >
          <span class="saved__name">{{ item.title }}</span>
          <span v-if="!item.prompt" class="saved__badge">結果なし</span>
        </button>
        <button
          type="button"
          class="btn--icon saved__remove"
          :aria-label="`${item.title} を削除`"
          @click="emit('remove', index)"
        >
          ×
        </button>
      </li>
    </ul>
  </section>
</template>
