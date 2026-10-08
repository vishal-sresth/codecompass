'use client'

import { useState } from 'react'
import { sendVerdict } from '../lib/api'
import type { Verdict } from '../lib/types'

const OPTIONS: { value: Verdict; label: string }[] = [
  { value: 'correct', label: 'Correct' },
  { value: 'partial', label: 'Partial' },
  { value: 'wrong', label: 'Wrong' },
]

// Judges the whole answer. Saved verdicts never change the original record (docs/specs/storage-schema.sql).
export default function VerdictBar({ id }: { id: number }) {
  const [selected, setSelected] = useState<Verdict | null>(null)
  const [note, setNote] = useState('')
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle')

  async function choose(verdict: Verdict) {
    setSelected(verdict)
    setStatus('saving')
    try {
      await sendVerdict(id, verdict, note.trim())
      setStatus('saved')
    } catch {
      setStatus('failed')
    }
  }

  return (
    <section className="card" aria-labelledby="verdict-heading">
      <h2 id="verdict-heading">Was this answer right?</h2>
      <div className="row" role="group" aria-label="Verdict">
        {OPTIONS.map((o) => (
          <button key={o.value} type="button" className={selected === o.value ? 'btn btn-selected' : 'btn'} aria-pressed={selected === o.value} onClick={() => choose(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
      <label className="small" htmlFor="verdict-note">Optional note</label>
      <textarea id="verdict-note" value={note} maxLength={1000} rows={2} onChange={(e) => setNote(e.target.value)} placeholder="What was right or wrong? Pick a verdict again to save an edited note." />
      <p className="small" role="status" aria-live="polite">
        {status === 'saving' && 'Saving…'}
        {status === 'saved' && '✓ Saved'}
        {status === 'failed' && '⚠ Could not save your verdict. Try again.'}
      </p>
    </section>
  )
}
