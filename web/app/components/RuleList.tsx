'use client'

import { useState } from 'react'
import type { Rule } from '../lib/types'
import RuleCard from './RuleCard'

// Broad questions can return many rules; show the first few so the gaps and the verdict buttons stay within reach.
const INITIAL = 5

export default function RuleList({ rules }: { rules: Rule[] }) {
  const [showAll, setShowAll] = useState(false)
  const visible = showAll ? rules : rules.slice(0, INITIAL)
  const hidden = rules.length - visible.length

  return (
    <>
      {visible.map((rule, i) => (
        <RuleCard key={i} rule={rule} />
      ))}
      {hidden > 0 && (
        <button type="button" className="btn" onClick={() => setShowAll(true)}>
          Show {hidden} more {hidden === 1 ? 'rule' : 'rules'}
        </button>
      )}
    </>
  )
}
