<script setup lang="ts">
// ショット一覧。Shot 1 は常に存在し削除できない
import ShotCard from '@/components/ShotCard.vue'
import type { Mode, Shot } from '@/types/api'
import { createEmptyShot } from '@/utils/form'

const props = defineProps<{
  shots: Shot[]
  mode: Mode
}>()

function addShot(): void {
  props.shots.push(createEmptyShot())
}

function removeShot(index: number): void {
  props.shots.splice(index, 1)
}
</script>

<template>
  <section class="card">
    <div class="card__label">ショット</div>

    <p v-if="mode === 'fl2va' && shots.length > 1" class="note--warn">
      FL2VA は最初と最後を滑らかにつなぐため、単一ショットを推奨します。複数ショットにすると意図した補間にならないことがあります
    </p>

    <div class="stack stack--cards">
      <ShotCard
        v-for="(shot, index) in shots"
        :key="index"
        :shot="shot"
        :index="index"
        @remove="removeShot(index)"
      />
      <button type="button" class="btn--add btn--add-shot" @click="addShot">
        + ショットを追加
      </button>
    </div>
  </section>
</template>
