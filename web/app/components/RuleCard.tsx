import type { Rule } from '../lib/types'
import DebugOnly from './DebugOnly'

// Label plus a small icon (docs/specs/ui-states.md). The icon is decorative; the word carries the meaning.
const CATEGORY: Record<Rule['category'], { label: string; icon: string }> = {
  regulatory: { label: 'Regulatory', icon: '§' },
  commercial: { label: 'Commercial', icon: '$' },
  technical: { label: 'Technical', icon: '#' },
  unknown: { label: 'Unknown', icon: '?' },
}

// All agent text is rendered as plain text (React escapes it); never as HTML.
export default function RuleCard({ rule }: { rule: Rule }) {
  return (
    <article className="card rule">
      <p className="rule-text">{rule.rule}</p>
      {/* The category is the model's guess, so it is a builder detail: shown only with ?debug=1 */}
      <DebugOnly>
        <p className="muted small">
          <span className="chip">
            <span aria-hidden="true">{CATEGORY[rule.category].icon} </span>
            {CATEGORY[rule.category].label}
          </span>
        </p>
      </DebugOnly>

      {rule.citations.length === 0 && (
        <p className="badge badge-warn">⚠ {rule.verify_text ?? 'Could not verify: the rule has no citation'}</p>
      )}

      {rule.citations.map((c, i) => {
        // Show what the code really says (read from the pinned file), not the agent's quote of it.
        const real = c.source_lines ?? []
        const first = real.length ? real[0].n : c.line_start
        const last = real.length ? real[real.length - 1].n : c.line_end
        return (
          <div className="citation" key={i}>
            <p className="small">
              <strong>{c.repo}</strong> / <code>{c.file}</code> : {first === last ? first : `${first}-${last}`}
            </p>
            <pre className="evidence">
              <code>
                {real.length > 0
                  ? real.map((line) => (
                      <span className="src-line" key={line.n}>
                        <span className="ln" aria-hidden="true">{line.n}</span>
                        {line.text}
                        {'\n'}
                      </span>
                    ))
                  : c.evidence}
              </code>
            </pre>
            <p className={c.verified ? 'badge badge-ok' : 'badge badge-warn'}>
              {c.verified ? '✓' : '⚠'} {c.verify_text}
            </p>
            <DebugOnly>
              <p className="small muted">checks: {c.verify_notes.join(', ')}</p>
            </DebugOnly>
          </div>
        )
      })}

      {rule.reasoning && (
        <details>
          <summary className="small">Why this is the rule</summary>
          <p className="small">{rule.reasoning}</p>
        </details>
      )}
    </article>
  )
}
