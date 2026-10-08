'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'

// Builder information (server status, per-answer tokens and versions) is hidden from PMs by default.
// It appears only when the page URL has ?debug=1. useSearchParams is client-only; in a prerendered page it must sit
// inside <Suspense> or the production build fails (node_modules/next/dist/docs/01-app/03-api-reference/04-functions/use-search-params.md).
// Children are mounted only in debug mode, so anything that fetches on mount (the server status line) does not run for PMs.
function Gate({ children }: { children: React.ReactNode }) {
  const searchParams = useSearchParams()
  return searchParams.get('debug') === '1' ? <>{children}</> : null
}

export default function DebugOnly({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={null}>
      <Gate>{children}</Gate>
    </Suspense>
  )
}
