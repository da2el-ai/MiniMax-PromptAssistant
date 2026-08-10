// バックエンドとの通信をまとめる

import type { GenerateRequest, GenerateResponse, HealthResponse } from '@/types/api'

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') {
      return body.detail
    }
    // Pydantic のバリデーションエラーは配列で返る
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item: { loc?: unknown[]; msg?: string }) => {
          const location = Array.isArray(item.loc) ? item.loc.join('.') : ''
          return location ? `${location}: ${item.msg ?? ''}` : (item.msg ?? '')
        })
        .join(' / ')
    }
    return JSON.stringify(body)
  } catch {
    return `HTTP ${response.status}`
  }
}

export async function generatePrompt(request: GenerateRequest): Promise<GenerateResponse> {
  const response = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return (await response.json()) as GenerateResponse
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return (await response.json()) as HealthResponse
}
