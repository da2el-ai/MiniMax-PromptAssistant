<script setup lang="ts">
// 確認ダイアログ。入力のクリア・保存の上書き・保存プロンプトの削除で使い回す
withDefaults(
  defineProps<{
    title: string
    body: string
    confirmLabel: string
    /** 取り消せない操作は確認ボタンを強調する */
    danger?: boolean
  }>(),
  { danger: false },
)

const emit = defineEmits<{ cancel: []; confirm: [] }>()
</script>

<template>
  <div class="overlay" @click.self="emit('cancel')">
    <div class="dialog" role="dialog" aria-modal="true">
      <div class="dialog__title">{{ title }}</div>
      <p class="dialog__body">{{ body }}</p>
      <div class="dialog__actions">
        <button type="button" class="dialog__btn" @click="emit('cancel')">キャンセル</button>
        <button
          type="button"
          class="dialog__btn"
          :class="{ 'dialog__btn--danger': danger }"
          @click="emit('confirm')"
        >
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>
