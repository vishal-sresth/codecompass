// Shapes from docs/specs/api-contract.md

export type Category = 'regulatory' | 'commercial' | 'technical' | 'unknown'

export type Citation = {
  repo: string
  file: string
  line_start: number
  line_end: number
  evidence: string
  verified: boolean
  verify_notes: string[]
  verify_text: string
  found_lines: [number, number] | null
  // The real lines from the pinned file (what the code actually says), for display. Empty if the file could not be read.
  source_lines: { n: number; text: string }[]
}

export type Rule = {
  rule: string
  category: Category
  citations: Citation[]
  reasoning: string
  all_verified: boolean
  verify_text?: string
}

export type Gap = { looked_in: string[]; not_found: string; suggested_follow_up: string }

export type Meta = {
  seconds: number | null
  input_tokens: number | null
  output_tokens: number | null
  agent_version: number | null
  prompt_version: string | null
}

export type AskResult = { id: number; answer: string; rules: Rule[]; gaps: Gap[]; meta: Meta }

export type Verdict = 'correct' | 'partial' | 'wrong'
