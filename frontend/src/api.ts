// Typed client for the FastAPI backend.

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type DocumentStatus = 'uploaded' | 'processing' | 'ready' | 'failed'

export interface DocumentInfo {
  id: number
  original_name: string
  content_type: string
  size_bytes: number
  page_count: number | null
  status: DocumentStatus
  error: string | null
  created_at: string
}

export interface Source {
  chunk_id: number
  document_id: number
  document_name: string
  page_number: number
  score: number
  text: string
}

export interface AskResponse {
  answer: string
  sources: Source[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, init)
  } catch {
    throw new Error(`Cannot reach the server at ${API_URL}. Is the backend running?`)
  }
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return response.json() as Promise<T>
}

// FastAPI returns {"detail": "..."} for HTTPException and {"detail": [{msg}]} for validation errors
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join('; ')
  } catch {
    // response wasn't JSON
  }
  return `Request failed (${response.status})`
}

export function listDocuments(): Promise<DocumentInfo[]> {
  return request('/documents')
}

export function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData()
  form.append('file', file)
  return request('/documents/upload', { method: 'POST', body: form })
}

export function askQuestion(question: string): Promise<AskResponse> {
  return request('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
}
