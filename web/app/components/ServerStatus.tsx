'use client'

import { useEffect, useState } from 'react'

// Browser-visible: an address only, never credentials (docs/engineering/engineering-doc.md section 4).
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type Status =
  | { state: 'checking' }
  | { state: 'ok'; db: boolean; agentVersion: number | null }
  | { state: 'down'; reason: string }

export default function ServerStatus() {
  const [status, setStatus] = useState<Status>({ state: 'checking' })

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${API_URL}/api/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json()
      })
      .then((body) => setStatus({ state: 'ok', db: body.db, agentVersion: body.agent_version }))
      .catch((error: Error) => {
        if (error.name !== 'AbortError') setStatus({ state: 'down', reason: error.message })
      })
    return () => controller.abort()
  }, [])

  return (
    <p role="status" aria-live="polite">
      {status.state === 'checking' && <>… server: checking</>}
      {status.state === 'ok' && (
        <>
          ✓ server: ok (database {status.db ? 'ready' : 'not set up yet'}, agent version{' '}
          {status.agentVersion ?? 'unknown'})
        </>
      )}
      {status.state === 'down' && (
        <>
          ⚠ server: can&apos;t reach {API_URL} ({status.reason}). Is it running on port 8000?
        </>
      )}
    </p>
  )
}
