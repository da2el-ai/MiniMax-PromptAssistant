<script setup lang="ts">
// 参照画像の内容説明。ビジョンモデルは使わずユーザーが日本語で記述する
import { computed, watch } from 'vue'

import type { ImageDesc, ImageRole, Mode } from '@/types/api'
import { ensureImageDesc, requiredImageRoles } from '@/utils/form'

const props = defineProps<{
  images: ImageDesc[]
  mode: Mode
}>()

const ROLE_LABELS: Record<ImageRole, string> = {
  first: '最初のフレーム(Picture 1)',
  last: '最後のフレーム',
}

const ROLE_PLACEHOLDERS: Record<ImageRole, string> = {
  first: '例: 雨に濡れた車窓際に座る若い女性。紺のコート、手元に折りたたんだ手紙。実写・映画調',
  last: '例: 開いた傘の下に立つ女性。自転車は左手に停まっている',
}

// 方式が変わったら、必要な役割の入力欄を用意する
watch(
  () => props.mode,
  (mode) => {
    for (const role of requiredImageRoles(mode)) {
      ensureImageDesc(props.images, role)
    }
  },
  { immediate: true },
)

// 方式に必要な役割の入力欄だけを表示する。バッジ番号は表示順に振る
const fields = computed(() =>
  requiredImageRoles(props.mode)
    .map((role, index) => {
      const image = props.images.find((item) => item.role === role)
      return image
        ? {
            role,
            badge: String(index + 1),
            label: ROLE_LABELS[role],
            placeholder: ROLE_PLACEHOLDERS[role],
            image,
          }
        : null
    })
    .filter((field) => field !== null),
)
</script>

<template>
  <section v-if="fields.length > 0" class="card">
    <div class="card__label">参照情報 — 画像の内容説明</div>
    <p class="note">
      画像そのものはアップロードしません。画像に写っている内容を日本語で書いてください。スタイルが「自動」の場合は、この説明から映像スタイルを判断します。
    </p>
    <div class="stack">
      <div v-for="field in fields" :key="field.role">
        <label class="frame-label">
          <span class="badge">{{ field.badge }}</span>{{ field.label
          }}<span class="required">*</span>
        </label>
        <textarea
          v-model="field.image.description"
          class="input textarea"
          rows="5"
          :placeholder="field.placeholder"
        ></textarea>
      </div>
    </div>
  </section>
</template>
