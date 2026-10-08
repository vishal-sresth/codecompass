'use client'

import { useEffect, useRef, useState } from 'react'
import { ApiFailure, askQuestion } from '../lib/api'
import type { AskResult } from '../lib/types'
import DebugOnly from './DebugOnly'
import RuleList from './RuleList'
import VerdictBar from './VerdictBar'

const MAX_CHARS = 500
type Phase =
  | { name: 'idle' }
  | { name: 'loading' }
  | { name: 'done'; result: AskResult }
  | { name: 'error'; code: string; message: string; raw?: string }

const INLINE_ERRORS = new Set(['invalid_input', 'unsafe_input']) // shown under the question box
const RETRY_ERRORS = new Set(['agent_error', 'bad_output', 'server_down', 'timeout']) // offer a Try again button

// Wording from docs/specs/ui-states.md, chosen by error code so it does not depend on the server's text.
function friendly(code: string, serverMessage: string, retryAfter?: number): string {
  switch (code) {
    case 'busy':
    case 'rate_limited':
      return `The model is busy. Wait about ${retryAfter ?? 60} s and try again.`
    case 'invalid_input':
      return `Questions can be 1 to ${MAX_CHARS} characters.`
    case 'unsafe_input':
      return 'That question looks like an instruction to the assistant, not a question about the code. Please rephrase.'
    case 'agent_error':
      return 'The agent could not be reached. Try again in a moment.'
    case 'bad_output':
      return 'The agent returned something unexpected.'
    case 'server_down':
      return "Can't reach the CodeCompass server. Is it running on port 8000?"
    default:
      return serverMessage
  }
}

export default function CodeCompassApp() {
  const [question, setQuestion] = useState('')
  const [phase, setPhase] = useState<Phase>({ name: 'idle' })
  const [elapsed, setElapsed] = useState(0)
  const [cooldown, setCooldown] = useState(0) // seconds before Ask is enabled again after busy / rate limited
  const resultRef = useRef<HTMLHeadingElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const retryRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (phase.name !== 'loading') return
    const started = Date.now()
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [phase.name])

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  useEffect(() => {
    if (phase.name === 'done') resultRef.current?.focus()
    if (phase.name === 'error') {
      // keyboard users land where they can act: the Try again button if there is one, else the question box
      if (RETRY_ERRORS.has(phase.code)) retryRef.current?.focus()
      else inputRef.current?.focus()
    }
  }, [phase])

  async function submit(event?: React.FormEvent) {
    event?.preventDefault()
    const text = question.trim()
    if (!text || phase.name === 'loading' || cooldown > 0) return
    setElapsed(0)
    setPhase({ name: 'loading' })
    const controller = new AbortController()
    // the server may wait up to 60 s for its single agent slot and 90 s for the agent: give up only after that
    const giveUp = setTimeout(() => controller.abort(), 155_000)
    try {
      setPhase({ name: 'done', result: await askQuestion(text, controller.signal) })
    } catch (error) {
      if (error instanceof ApiFailure) {
        if (error.code === 'busy' || error.code === 'rate_limited') setCooldown(error.retryAfter ?? 60)
        setPhase({ name: 'error', code: error.code, message: friendly(error.code, error.message, error.retryAfter), raw: error.raw })
      } else {
        setPhase({ name: 'error', code: 'timeout', message: 'This is taking too long. Try again in a moment.' })
      }
    } finally {
      clearTimeout(giveUp)
    }
  }

  const loading = phase.name === 'loading'
  const inlineError = phase.name === 'error' && INLINE_ERRORS.has(phase.code) ? phase.message : null
  const blockError = phase.name === 'error' && !INLINE_ERRORS.has(phase.code) ? phase : null

  return (
    <>
      <form onSubmit={submit} className="card" aria-label="Ask a question">
        <label htmlFor="question" className="label">Ask about the code</label>
        <textarea
          id="question"
          ref={inputRef}
          value={question}
          maxLength={MAX_CHARS}
          rows={3}
          disabled={loading}
          aria-invalid={inlineError ? true : undefined}
          aria-describedby={inlineError ? 'question-error' : undefined}
          onChange={(e) => {
            setQuestion(e.target.value)
            if (inlineError) setPhase({ name: 'idle' })
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
          }}
          placeholder="Type your question about the code"
        />
        {inlineError && (
          <p id="question-error" className="badge badge-err" role="alert">⚠ {inlineError}</p>
        )}
        <div className="row spread">
          <span className="small muted">{question.length}/{MAX_CHARS} · Ctrl or ⌘ + Enter to ask</span>
          <button type="submit" className="btn btn-primary" disabled={loading || cooldown > 0 || question.trim().length === 0}>
            {cooldown > 0 ? `Ask (wait ${cooldown} s)` : 'Ask'}
          </button>
        </div>
        <p className="note small muted" role="note">
          Candidate answers from the code. Verify before using in PRDs, launches or compliance decisions.
        </p>
      </form>

      {/* The seconds counter is aria-hidden so screen readers hear "Asking the agent" once, not every second. */}
      <div role="status">
        {loading && (
          <p className="card loading">
            <span className="spinner" aria-hidden="true" />
            <span>Asking the agent…</span>
            <span aria-hidden="true">{elapsed} s</span>
            {elapsed >= 45 && <span>Still working. Answers can take up to a minute.</span>}
          </p>
        )}
      </div>

      {blockError && (
        <div className="card">
          <p className="badge badge-err" role="alert">⚠ {blockError.message}</p>
          {RETRY_ERRORS.has(blockError.code) && (
            <div className="row">
              <button type="button" ref={retryRef} className="btn" onClick={() => submit()}>Try again</button>
            </div>
          )}
          {blockError.raw && (
            <details>
              <summary className="small">Show raw reply</summary>
              <pre className="evidence"><code>{blockError.raw}</code></pre>
            </details>
          )}
        </div>
      )}

      {phase.name === 'done' && <Result result={phase.result} headingRef={resultRef} />}
    </>
  )
}

function Result({ result, headingRef }: { result: AskResult; headingRef: React.RefObject<HTMLHeadingElement | null> }) {
  const m = result.meta
  return (
    <>
      <section className="card" aria-labelledby="answer-heading">
        <h2 id="answer-heading" ref={headingRef} tabIndex={-1}>Answer</h2>
        <p>{result.answer}</p>
      </section>

      <section aria-labelledby="rules-heading">
        <h2 id="rules-heading">Rules from the code</h2>
        {result.rules.length === 0 ? (
          <p className="card"><strong>No matching rule found in the indexed code.</strong> See below for where the agent looked.</p>
        ) : (
          <RuleList key={result.id} rules={result.rules} />
        )}
      </section>

      <section className="card" aria-labelledby="gaps-heading">
        <h2 id="gaps-heading">Where I looked and did not find it</h2>
        {result.gaps.length === 0 ? (
          <p className="muted">No gaps reported.</p>
        ) : (
          result.gaps.map((g, i) => (
            <div key={i} className="gap">
              <p className="small"><strong>Where I looked</strong></p>
              {g.looked_in.length > 0 && <ul className="small">{g.looked_in.map((l, j) => <li key={j}>{l}</li>)}</ul>}
              <p className="small"><strong>What I did not find:</strong> {g.not_found}</p>
              <p className="small"><strong>Suggested follow-up for engineering:</strong> {g.suggested_follow_up}</p>
            </div>
          ))
        )}
      </section>

      <VerdictBar key={result.id} id={result.id} />

      {/* Builder information: visible only with ?debug=1 */}
      <DebugOnly>
        <p className="status-bar small muted">
          {m.seconds ?? 'n/a'} s · {m.input_tokens ?? 'n/a'} in / {m.output_tokens ?? 'n/a'} out tokens · agent v{m.agent_version ?? 'n/a'} · prompt {m.prompt_version ?? 'n/a'}
        </p>
      </DebugOnly>
    </>
  )
}
