<script setup lang="ts">
// RF2VA の参照アセット。画像・動画・音声を複数登録する
import { computed } from 'vue'

import { ASSET_KINDS, ASSET_ROLES, type AssetKind, type RefAsset } from '@/types/api'
import { createEmptyAsset } from '@/utils/form'

const props = defineProps<{ assets: RefAsset[] }>()

const KIND_LABELS: Record<AssetKind, string> = {
  image: '画像',
  video: '動画',
  audio: '音声',
}

// 種類ごとの通し番号を振ったラベル(例: 画像 1、音声 1)
const labels = computed(() =>
  props.assets.map((asset, index) => {
    const number =
      props.assets.slice(0, index).filter((item) => item.kind === asset.kind).length + 1
    return `${KIND_LABELS[asset.kind]} ${number}`
  }),
)

function addAsset(): void {
  props.assets.push(createEmptyAsset())
}

function removeAsset(index: number): void {
  props.assets.splice(index, 1)
}
</script>

<template>
  <section class="card">
    <div class="card__label">参照情報 — 参照アセット</div>
    <p class="note note--plain">画像・動画・音声を複数登録できます。内容は日本語で説明してください。</p>
    <div class="stack stack--cards">
      <div v-for="(asset, index) in assets" :key="index" class="subcard subcard--asset">
        <div class="subcard__header">
          <div class="subcard__title subcard__title--accent">{{ labels[index] }}</div>
          <button type="button" class="btn btn--sm" @click="removeAsset(index)">削除</button>
        </div>
        <div class="asset__row">
          <select v-model="asset.kind" class="input input--plain input--sm select asset__kind">
            <option v-for="kind in ASSET_KINDS" :key="kind.value" :value="kind.value">
              {{ kind.label }}
            </option>
          </select>
          <input
            v-model="asset.role"
            type="text"
            class="input input--plain input--sm asset__role"
            :list="`roles-${asset.kind}`"
            placeholder="役割(選択または自由記述)"
          />
        </div>
        <textarea
          v-model="asset.description"
          class="input input--plain input--sm textarea"
          rows="3"
          placeholder="内容の説明(何が写っている / 入っているか)"
        ></textarea>
      </div>
      <button type="button" class="btn--add btn--add-asset" @click="addAsset">
        + 参照アセットを追加
      </button>
    </div>

    <datalist v-for="(roles, kind) in ASSET_ROLES" :id="`roles-${kind}`" :key="kind">
      <option v-for="role in roles" :key="role" :value="role"></option>
    </datalist>
  </section>
</template>
