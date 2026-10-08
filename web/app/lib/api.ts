import type { AskResult, Verdict } from './types'

// Browser-visible: an address only, never credentials.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export class ApiFailure extends Error {
  constructor(
    public code: string,
    message: string,
    public retryAfter?: number,
    // The server does not send this yet (docs/specs/api-contract.md); shown under "Show raw reply" if it ever does.
    public raw?: string,
  ) {
    super(message)
  }
}

async function failure(response: Response): Promise<ApiFailure> {
  let body: { error?: string; message?: string; retry_after?: number; raw?: string } = {}
  try {
    body = await response.json()
  } catch {
    // not JSON: fall through to the generic message
  }
  return new ApiFailure(
    body.error ?? 'agent_error',
    body.message ?? 'Something went wrong. Try again.',
    body.retry_after,
    typeof body.raw === 'string' ? body.raw : undefined,
  )
}

async function post(path: string, payload: unknown, signal?: AbortSignal): Promise<Response> {
  try {
    return await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    throw new ApiFailure('server_down', "Can't reach the CodeCompass server. Is it running on port 8000?")
  }
}

export async function askQuestion(question: string, signal?: AbortSignal): Promise<AskResult> {
  const response = await post('/api/ask', { question }, signal)
  if (!response.ok) throw await failure(response)
  return response.json()
}

export async function sendVerdict(id: number, verdict: Verdict, note?: string): Promise<void> {
  const response = await post('/api/verdict', { id, verdict, note: note || null })
  if (!response.ok) throw await failure(response)
}
