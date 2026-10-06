---
name: verify-absence
description: How to prove a concept is genuinely absent from the indexed code before using it as a trick question or telling the user "it is not there". Requires positive controls, whole-word matching, reading the hits, and the codebase's own vocabulary. Use whenever you are about to claim "0 matches" or choose a trick question.
---

# Verify absence

A "0 matches" result is only evidence if the search provably works. In this project a failed search (permission error) and a true absence printed the same number.

## Procedure
1. **Read through Python, not shell grep.** Shell search can silently skip hidden folders or fail with permission errors. Search `ingest/out/chunks/*.txt` (what the agent sees) and, for citations, the pinned source files.
2. **Print how many files were read** and assert it equals the expected count (2,397 chunks). Stop if it is 0 or wrong.
3. **Run positive controls first:** terms known to be present (`supported_countries`, `klarna`, `pm_filters`) must return more than 0. If any control fails, the search is broken; stop.
4. **Use whole-word patterns** (`\bofac\b`). Substrings fool you (`ofac` inside `PagoFacil`, `nameOfAccount`).
5. **Use the codebase's vocabulary, not the PM's.** List synonyms and the repo's own naming before declaring absence (the crypto question: "bitcoin" had 0 hits, but the code says `crypto_currency`, `coinbase`, `bitpay`).
6. **Read the hits** of any term that matches. A match may be an error message or a helper, not a rule (`'Country blacklisted'` in paymill.rb:277 is a message from the gateway, not a country list).
7. **Record the evidence** next to the question: each term and its count, the controls and the chunk count, in `eval/trick_questions.json`.

## A good trick question is
Verified absent by the steps above, plausible for a payments product (so a weak agent might invent an answer), and phrased the way a PM would ask it.

## Gate
Show the user the table of terms, counts and controls before saving a question as ground truth.
