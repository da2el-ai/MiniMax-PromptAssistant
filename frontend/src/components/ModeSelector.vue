<script setup lang="ts">
// 方式の選択。ドロップダウンで 1 つ選ぶ
import { computed } from 'vue'

import { MODES, SUPPORTED_MODES, type Mode } from '@/types/api'

const mode = defineModel<Mode>({ required: true })

const description = computed(
  () => MODES.find((option) => option.value === mode.value)?.description ?? '',
)

const supported = computed(() => SUPPORTED_MODES.includes(mode.value))
</script>

<template>
  <section class="card">
    <div class="card__label">方式</div>
    <select v-model="mode" class="input select select--mode">
      <option v-for="option in MODES" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <div class="mode__desc">{{ description }}</div>
    <p v-if="!supported" class="mode__unsupported">
      この方式はまだバックエンドが対応していません。入力はできますが、生成するとエラーになります
      (現在生成できるのは I2VA のみです)。
    </p>
  </section>
</template>
