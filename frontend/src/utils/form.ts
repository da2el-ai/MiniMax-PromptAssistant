// フォームの初期値を作るヘルパー

import type {
  AssetKind,
  GenerateRequest,
  ImageDesc,
  ImageRole,
  Mode,
  RefAsset,
  Shot,
} from '@/types/api'

export function createEmptyShot(): Shot {
  return { cutTimeSec: null, description: '', camera: '', dialogues: [] }
}

export function createEmptyAsset(): RefAsset {
  return { kind: 'image', role: '', description: '' }
}

export function createInitialRequest(mode: Mode = 'i2va'): GenerateRequest {
  return {
    mode,
    durationSec: 8,
    style: 'auto',
    shots: [createEmptyShot()],
    onScreenTexts: [],
    ambience: { none: false, note: '' },
    bgm: { none: false, note: '' },
    images: [],
    refAssets: [],
  }
}

/** 方式ごとに必要な参照画像の役割を返す。 */
export function requiredImageRoles(mode: Mode): ImageRole[] {
  switch (mode) {
    case 'i2va':
      return ['first']
    case 'fl2va':
      return ['first', 'last']
    case 'l2va':
      return ['last']
    default:
      return []
  }
}

/** 指定した役割の画像説明を取り出す。無ければ作って追加する。 */
export function ensureImageDesc(images: ImageDesc[], role: ImageRole): ImageDesc {
  const found = images.find((image) => image.role === role)
  if (found) {
    return found
  }
  const created: ImageDesc = { role, description: '' }
  images.push(created)
  return created
}

/** 種類ごとの通し番号を付けたラベルを返す(例: 画像 1)。 */
export function assetLabel(assets: RefAsset[], index: number, kindLabels: Record<AssetKind, string>): string {
  const kind = assets[index].kind
  const number = assets.slice(0, index).filter((asset) => asset.kind === kind).length + 1
  return `${kindLabels[kind]} ${number}`
}
