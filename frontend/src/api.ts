export interface Location {
  name: string
  lat: number
  lon: number
  elevation: number
}

export interface KeyFactors {
  humidity: number
  wind_speed: number
  temp_inversion: boolean
  low_cloud: number
}

export interface PredictionResult {
  location: string
  prediction_time: string
  probability: '高' | '中' | '低'
  best_window: string
  confidence: number
  summary: string
  key_factors: KeyFactors
  advice: string
  safety_tips?: string
  clothing_tips?: string
  error?: string
  message?: string
}

function apiUrl(path: string): string {
  if (window.location.port === '8000') return path
  return `http://127.0.0.1:8000${path}`
}

export async function fetchLocations(): Promise<Location[]> {
  const res = await fetch(apiUrl('/api/locations'))
  if (!res.ok) throw new Error(`获取景区列表失败: ${res.status}`)
  return res.json()
}

export async function predict(location: string): Promise<PredictionResult> {
  const res = await fetch(apiUrl('/api/predict'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ location }),
  })
  if (!res.ok) throw new Error(`预测请求失败: ${res.status}`)
  return res.json()
}
