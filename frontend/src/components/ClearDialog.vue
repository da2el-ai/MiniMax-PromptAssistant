<script setup lang="ts">
// 「入力をクリア」の確認ダイアログ
const emit = defineEmits<{ cancel: []; confirm: [] }>()
</script>

<template>
  <div class="overlay" @click.self="emit('cancel')">
    <div class="dialog" role="dialog" aria-modal="true">
      <div class="dialog__title">入力をクリアしますか?</div>
      <p class="dialog__body">
        入力内容と生成結果がすべて初期状態に戻ります。この操作は取り消せません。
      </p>
      <div class="dialog__actions">
        <button type="button" class="dialog__btn" @click="emit('cancel')">キャンセル</button>
        <button type="button" class="dialog__btn dialog__btn--danger" @click="emit('confirm')">
          クリアする
        </button>
      </div>
    </div>
  </div>
</template>
