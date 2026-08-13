<script setup lang="ts">
// タイトルの入力と保存ボタン。保存の実行と結果の通知は親が受け持つ
const title = defineModel<string>({ required: true })

defineProps<{
  /** 直後に保存が成功したか。ボタンの表示を一時的に切り替える */
  saved: boolean
  /** 保存できなかった理由。空なら表示しない */
  error: string
}>()

const emit = defineEmits<{ save: [] }>()
</script>

<template>
  <section class="card">
    <div class="card__label">タイトル</div>
    <div class="title__row">
      <input
        v-model="title"
        type="text"
        class="input title__input"
        placeholder="例: 商店街を歩く少女"
        @keydown.enter.prevent="emit('save')"
      />
      <button type="button" class="btn title__save" @click="emit('save')">
        {{ saved ? '保存しました' : '保存' }}
      </button>
    </div>
    <p class="note note--plain title__note">
      今の入力と生成結果を、このタイトルで保存します。
    </p>
    <p v-if="error" class="title__error">{{ error }}</p>
  </section>
</template>
