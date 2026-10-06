# CodeCompass build log: issues, learnings and how we solved them

Purpose: a running record of what went wrong or surprised us while building the Claude Code + Azure AI Foundry POC,
why it happened, and what we did. Newest entries at the bottom. Format: Problem, Why it happened, What we did, Takeaway.

---

## 1. The model we planned for wasn't available (2026-10-04)
- **Problem:** The plan assumed claude-sonnet-5-5 in Foundry. On the free/tiered subscription it could not be deployed.
- **Why:** Model availability in Foundry depends on subscription tier and quota, not just on the model catalog listing it.
- **What we did:** Picked GPT-5 mini. Reasoning: File Search sends several chunks per question, so a cheap model with quota headroom is
  best; retrieval means the model never needs a huge context window; start cheap and move up only if evals fail.
- **Takeaway:** Check access and quota before designing around a specific model. Pick the cheapest model that might work and let the eval
  decide whether to pay for more. (Mahesh Week 5: "start with the cheapest model, measure with evals".)

## 2. A repo that looked right but had no rules in it (2026-10-04)
- **Problem:** We chose `mollie/mollie-api-php` as a third repo because it was small and about payment methods.
- **Why it was wrong:** It is a client SDK. Mollie's servers decide which payment method is available where, so the rules are not in this code.
  The "country/currency" matches were mostly mock test responses.
- **What we did:** Looked inside before indexing, dropped it, and started with 2 repos. Made the ingest driven by a repo list so a third
  (candidate: Adyen/adyen-web components) is a one-line addition later.
- **Takeaway:** Judge a repo by where the *decision logic* lives, not by its topic. Grep for the kind of rule you want before committing to a repo.
  Also: fewer repos first, get the pipeline working end to end, then widen.

## 3. File Search does not return line numbers (2026-10-04)
- **Problem:** The PRD promises `file:line` citations, but the File Search tool only returns chunk text (at best with a file name).
- **Why:** The service splits files itself and has no notion of original line numbers. If a line number is not inside the text the agent sees,
  the agent can only guess it, and a guessed number is a hallucination.
- **What we did:** Our ingest writes `REPO / COMMIT / PATH / LINES` and numbered lines into every chunk, so the agent copies a citation
  instead of inventing it, and a checker can verify it against the real file.
- **Takeaway:** Anything you want the agent to cite must be inside the text it can see.

## 4. The service re-splits big files, so our header can get lost (2026-10-04)
- **Problem:** If we upload one large file with the header at the top, the service's own splitter (roughly 800-token windows) cuts it again,
  and the later pieces have no header.
- **What we did:** Each chunk is its own small file (under about 2,400 characters), so it is not split again. Consequence: thousands of
  tiny files, uploaded through code instead of the portal.
- **Takeaway:** Know what the platform does to your data after you hand it over; design chunks to survive that.

## 5. A chunk lost which connector a rule belonged to (2026-10-04)
- **Problem:** In Hyperswitch `development.toml`, a chunk held `google_pay = { country = ... }` lines, but the `[pm_filters.<connector>]` line that says
  *whose* rule it is sat in an earlier chunk. The agent could have guessed the connector and been wrong.
- **Why:** Chunk boundaries ignore structure. This is the classic "chunk loses its context" problem in RAG.
- **Options considered:** (A) add a SECTION line to each chunk header from the nearest `[section]` or `class`; (B) overlap chunks by N lines;
  (C) bigger chunks.
- **We measured instead of arguing** (96 chunks of development.toml): no overlap, section visible in 70%; overlap 10 lines, 94%; overlap 20 or 40,
  95-96% (plateau); SECTION header, 100%.
- **What we did:** A + small overlap (10 lines, capped at a third of the chunk). A closes the last ~5% that overlap cannot reach;
  overlap protects rules cut mid-block.
- **Takeaway:** Overlap is the general answer; structure-aware headers are the specific answer; measure before choosing.
- **Behaviour rule for the agent (user decision):** if the agent cannot tell which connector a rule belongs to, it must say so honestly,
  may retry with another search, and must never make up a connector or a rule. This goes into the system prompt and into the eval
  (gap-honesty trick questions).

## 6. Overlap blew up the chunk count (2026-10-04)
- **Problem:** After adding a 10-line overlap, chunks went from 1,927 to 3,077 (Hyperswitch 339 to 1,135), far more than the ~15% expected.
- **Why:** Hyperswitch config lines are very long (country lists), so a chunk holds only about 4 lines. An overlap of 10 lines is larger than the chunk,
  so the window advanced one line at a time.
- **What we did:** Cap the overlap at a third of the chunk. Result: 2,397 chunks (Hyperswitch +42%, active_merchant +20%).
- **Takeaway:** Parameters that look reasonable in isolation interact. Always look at the counts after a change.

## 7. Verifying the index before trusting it (2026-10-04)
- **Check:** Parsed every numbered line in all 2,397 chunks and compared it with the source file at the pinned commit.
  Result: 103,731 rows checked, 0 mismatches.
- **Takeaway:** Test the property everything downstream depends on (here: line numbers are true) before building on it.
  This is a preview of the deterministic citation checker used in the eval.

## 8. Homebrew refused to run: "current working directory must be readable" (2026-10-05)
- **Problem:** `brew install azure-cli` failed immediately with that message.
- **Why:** the shell's working directory was a temporary folder that had been removed, so the tool had nowhere valid to start from.
- **What we did:** ran the command from the home folder (`cd ~`). It then installed Azure CLI 2.90.0.
- **Takeaway:** when a command fails before doing any work, check the environment (working directory, PATH) before suspecting the command.

## 9. The agent had a web_search tool that would break our honesty promise (2026-10-05)
- **Problem:** Inspecting the agent showed two tools: file_search and web_search (plus version 2, model gpt-5-mini, a placeholder prompt).
- **Why it matters:** with web search on, the agent can answer from the internet instead of the repo. The answer may be right but has no file:line
  citation and is not "what the code does", which is the product's whole promise.
- **What we do:** remove web_search when we publish the new agent version. Agents are versioned (new version, not an in-place edit), so we can roll back.
- **Takeaway:** check the default tools of anything you create. Every tool is a second source of truth the agent can quietly use.

## 10. First retrieval test on a 20-chunk store (2026-10-05)
- **Setup:** new vector store with 20 hand-picked chunks (10 Hyperswitch pm_filters, 10 active_merchant stripe.rb); called the Responses API with
  file_search directly, so the agent itself was untouched.
- **Good:** Stripe countries answer matched stripe.rb:30 exactly. Klarna answer named three connectors (aci, multisafepay, mollie) with the
  right line numbers; the SECTION header (learning #5) is what made the attribution possible. All cited lines were checked by hand against the real file.
- **Problems found:**
  1. Citation ranges are sometimes loose (e.g. 1066-1068 spans the end of one section and the header of the next). Fix: prompt asks for the
     tightest line range; checker will test that the cited lines contain the value.
  2. The model says "the uploaded files" and offers things it cannot do ("I can search the repo for other config files"). Fix: prompt.
  3. A trick question on a partial index proves nothing: "no evidence" is expected when most of the repo is missing. Run trick questions on the full index.
  4. Cost and speed: 15-23 s and ~17-18K input tokens per question (4-5 searches each). With the 50K tokens/minute quota that is about 2 questions per minute,
     so the eval runner must pace itself.
- **Takeaway:** a correct-looking answer is not a verified answer; check each citation. And measure tokens per question early, because quota,
  not money, is our real limit.

## 11. The full upload took 2h15m, not the estimated 10-40 min (2026-10-05)
- **Problem:** I estimated from the 20-file test (24 s, ~1.2 s per file). The real run of 2,397 files took 8,098 s (~3.4 s per file).
- **Why:** the SDK uploads files one at a time before attaching each batch, and each batch then has to be embedded; a small test hides per-batch overhead and
  slower processing under load. Results: 2,397 completed, 0 failed, 8.4 MB.
- **Takeaway:** extrapolating from a tiny test is optimistic; say "at least" and re-measure after the first few batches. If we re-index, upload in parallel
  (several threads) or only re-upload changed files.

## 12. "0 matches" from a search that could not read anything (2026-10-05)
- **Problem:** to pick trick questions we searched all chunks for concepts that should be absent (sanction, ofac, kyc, ...). Every search returned 0.
- **Why it was misleading:** the search was failing, not finding nothing ("cannot open directory: Operation not permitted"). A failed search and a true
  "absent" print the same number.
- **How we caught it:** a positive control. A keyword known to be present (supported_countries, klarna) must return more than 0, and the script printed
  "chunks read: 0".
- **Takeaway:** same lesson as 10.3, one level up. Never trust a "not found" unless the same method has been shown to find things that do exist.
  Every absence check (including the eval's ground-truth script) needs positive controls and a count of files actually read.

## 13. Claude Code lost access to folders because it had become an orphan process (2026-10-05)
- **Problem:** after ~12 hours, Claude Code could no longer read ingest/, hyperswitch/ or repos/ ("Operation not permitted"), though VS Code had Documents
  access in System Settings and nothing was deleted. Restarting VS Code did not help.
- **Diagnosis:** the process tree showed claude.exe running since the day before with PID 1 (launchd) as its parent, so it was no longer attached to VS Code.
  Folders created by that process (carrying a com.apple.macl attribute) stayed readable; older ones did not. Cause is a hypothesis, but ending the
  orphan and starting Claude from VS Code's own terminal fixed it.
- **Fix:** end the old process, run `claude --continue` from VS Code's integrated terminal.
- **Takeaway:** check the process tree (`ps` with parent PIDs) when permissions fail for no visible reason. And keep project state in files and notes,
  so a restart loses nothing; ours did not.

## 14. Substring matches gave false "present" signals; a near-miss makes the best trap (2026-10-05)
- **Problem:** once the search worked, "ofac" showed 4 hits and "blacklist" 4. Looking at the lines: "ofac" was inside `PagoFacil` and `nameOfAccount`;
  "blacklist" was gateways' own error messages (`50001 => 'Country blacklisted'` in paymill.rb:277), not rules.
- **Fix:** whole-word patterns (`\bofac\b`), and read the actual matching lines before deciding a concept is present or absent.
- **Result:** 5 verified-absent trick questions (sanctions, KYC, GDPR, crypto, refund window), all with 0 matches and passing positive controls
  (supported_countries 232, klarna 54, pm_filters 274 chunks), saved in eval/trick_questions.json. Plus one hard "near-miss" question (Paymill country
  blocking), where a hint of the concept exists (an error message) but no rule does; the right answer is nuanced, which a plain "not found" test cannot probe.
- **Takeaway:** keyword search is crude. Whole words, read the hits, and keep the evidence next to the label so the ground truth can be audited.

## 15. First honesty run on agent v4: 2/5 "passed", but the scoreboard hid three different things (2026-10-05)
- **Run:** 5 verified-absent trick questions + 1 near-miss, on the live agent (v4, full index). Raw results: eval/results/trick_20261005_2011.json.
  T1 (sanctions) and T5 (refund window) passed cleanly: no rule, a gaps explanation. T2, T3, T4 returned rules, so the strict scorer said FAIL.
- **What was really going on:**
  1. **T4 was MY mistake, not the agent's.** I called "Bitcoin / cryptocurrency" absent after searching for "bitcoin|cryptocurrenc" (0 hits). The codebase calls it
     `crypto_currency` (21 chunks) with connectors `coinbase` (17) and `bitpay` (7). The agent found them and was substantively right.
     Lesson: an absence check must use the codebase's own vocabulary, not the PM's. T4 is withdrawn and must be replaced.
  2. **T2 and T3: honest answer text, but "relevance creep".** The `answer` said "I did not find a KYC flow / GDPR restriction", yet `rules` still held real but tangential
     facts (ACH accounts must be verified; EU countries are supported). Nothing was invented, but a PM could read them as a partial answer to the wrong question.
  3. **Citation defects, even where content was real:** (a) Airwallex evidence was copied WITH the "7 |" line-number prefix, so the checker failed it;
     after stripping the prefix it passes (checker and prompt problem); (b) evidence was truncated or reformatted on two rules (T2 verify(), T3 development.toml);
     (c) T4 bitpay: the quoted text is real but the agent cited config.example.toml:644-645 when it is at 1003-1004. Right content, wrong line numbers.
- **Why (c) matters:** wrong line numbers on real text is exactly the failure the design (line-numbered chunks plus a checker) was built to catch, and the checker caught it.
  Without the checker, a PM would have been sent to the wrong lines.
- **Takeaways:** (1) split "fabricated rule" from "irrelevant but real rule" from "bad citation" when scoring, because they need different fixes (prompt vs checker vs index);
  (2) a single pass/fail number can hide who is at fault; read the answers; (3) the deterministic checker earns its place.
- **Fixes queued:** prompt v2 (copy evidence without line-number prefix, quote exact text, "if nothing matches the question, return rules: [] and put adjacent findings only in gaps/answer");
  checker normalises the prefix; replace T4 with a question verified absent using the codebase's vocabulary.

## 16. The token-per-minute quota bit us in the Playground (2026-10-05)
- **Problem:** while trying a second question in the Foundry Playground the user got "Your requests to gpt-5-mini ... have exceeded token rate limit."
- **Why:** the deployment's quota is 50K tokens per minute, shared by everything using it. One agent question sends the retrieved chunks to the model, measured at 17K-35K
  input tokens per question on the full index (about twice the small-store test), so two questions within a minute can exceed the limit. We predicted this in learning 10.4.
- **What we do:** one question at a time and wait ~60 s after an error; the eval runner already pauses 30 s between questions, which is tight at 35K tokens, so it needs a longer pause
  or retry-with-backoff. Look at the quota ceiling in Models + endpoints; if it cannot be raised, consider retrieving fewer chunks (measure recall first) or pacing.
- **Takeaway:** for LLM apps, the quota (tokens per minute) is often the real constraint, before money. Measure tokens per request early and design the eval around it.
- **Fix applied (by the user, in the portal Quota page):** the Quota page showed the subscription had 500K TPM for gpt-5-mini (Global) with only 50K allocated to the deployment (rate limiting 4.76%).
  Raised the deployment to 201K TPM. Earlier I wrongly assumed a free/tiered subscription would cap this; it did not. Takeaway: look at the actual quota page before guessing.
