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

## 17. Publishing the repo: what the checks caught (2026-10-05)
- **Scan controls caught a bug in our own scan:** the pre-publish sensitive-content scan had a planted-string control for each pattern; the `employer` pattern failed it
  because it was case-sensitive (a lowercase pattern did not match a capitalised planted sample). Without the control the scan would have missed capitalised mentions. After the fix: 33 files read, 0 hits in 10 categories.
- **Anything with a public effect was checked from the outside:** after pushing we asked GitHub itself (not our own machine) for the file count (32), the commit author
  (the no-reply address, so no personal email in history), the visibility, and whether `.claude/skills` arrived as a symlink. GitHub showed "license: none detected" for a few seconds
  before detecting MIT; a short indexing delay, not a problem with the file.
- **Reversible clean-up:** two out-of-date files were moved to an ignored `_local_archive/` instead of deleted.
- **Git identity** was set for this repo only (not globally), using GitHub's no-reply address.
- **Takeaway:** for public actions, show the exact list first, get a yes, do it, then verify from the receiving side.

## 18. Specs are cheaper to fix than code, so we ran them before approving (2026-10-05)
- **What we did:** Stage 3 specs were executed, not just read. The SQLite schema was run against a real SQLite (it rejects an empty or 501-character question, bad JSON, an invalid verdict, a verdict without its
  timestamp, and any rewrite of the original answer). The citation-checker algorithm was implemented as a throwaway reference and run against 14 fixtures built from real lines in the pinned repos
  (including the BitPay wrong-lines case and the Airwallex prefix case). All JSON examples in the specs were parsed.
- **What it caught:** the spec said "the first note" without defining an order (a citation can carry `prefix_stripped` and `range_loose` together). We added an explicit priority rule and re-ran: 14/14.
- **Takeaway:** a spec you can execute is a spec you can trust; the same fixtures become the unit tests in Stage 5, so the code is held to exactly what was approved.

## 19. The pre-push scan caught a leak that I had just written myself (2026-10-06)
- **Problem:** while describing a scan bug in entry 17, I used the real example word (the employer's name) in the build log. The scan run before the second push flagged it;
  the first scan had passed only because the entry did not exist yet.
- **Fix:** reworded the entry, re-ran the scan with controls (12 files read, 0 unexpected hits), and checked the already-published commit with a positive control (0 files contain the word).
- **Takeaway:** sensitive words enter through documentation of the problem as easily as through code. Scan every push, not just the first, and describe incidents without repeating the sensitive value.

## 20. Foundry Traces made cost and the rate-limit failure visible (2026-10-06)
- **What we did:** connected Application Insights to the agent (the user did it in the portal). The Traces tab then listed each call with status, duration, tokens in/out, estimated cost and agent version.
- **What it showed:** (1) cost is tiny, about $0.006 to $0.010 per question (17K to 44K input tokens), so money is not the constraint, the tokens-per-minute quota is; (2) one question used 44,075 tokens,
  nearly all of the old 50K per minute limit, which explains the earlier rate-limit error; that failure appears as a trace with status Failed, 2.5 s and 0 tokens; (3) token use varies 2.5x between questions
  because the agent runs a different number of search rounds; (4) our results file and the trace agree on input tokens exactly, but output tokens differ a little (guess: the trace leaves out reasoning tokens; unverified).
- **Takeaway:** instrument first, then reason about cost. Before connecting Traces we only had guesses ("price not verified"); one table replaced them with measurements.
- Foundry also has an Annotate column and a Create dataset button (its own labelling and eval-data path); our app keeps its own SQLite verdicts for the demo, and Foundry's feature is a candidate for the Beta stage.

## 21. Reading one trace exposed two defects in our index (2026-10-06)
- **What we looked at:** the Foundry trace of "Which countries does the Stripe gateway in active_merchant support?" (about 44K input tokens): 4 agent-written search queries, 20 retrieved chunks.
  The answer chunk (stripe.rb 1-43, line 30) was among them; the other 19 were same-file neighbours, other gateways that also define `supported_countries`, and one Hyperswitch chunk.
- **Defect 1, header lost after re-splitting:** one retrieved Hyperswitch chunk showed no REPO/PATH/SECTION header and began mid-line, although our file on disk starts with the header.
  Cause: the chunk is about 1,200 tokens (rough estimate), above the service's roughly 800-token window, so the service split it again. Country lists are token-dense (about 2 characters per token vs about 4 for code),
  so the 2,400-character cap from learning 4 was not safe. Estimated 324 of 483 Hyperswitch chunks and 12 Ruby chunks are over the window. Estimate used word/number/punctuation counting, not a real tokenizer.
- **Defect 2, wrong SECTION for nested Ruby classes:** the section finder took the nearest `class` line above a chunk and never noticed that a nested class had ended. 27 of 1,914 Ruby chunks (14 in stripe.rb)
  carry the wrong class (for example Stripe's own methods labelled `StripePaymentToken`).
- **Lesson:** a limit measured in characters is not a limit measured in tokens; size chunks in the unit the downstream system uses. And read what the model actually received: the trace is the only place defect 1 was visible.
- **Plan:** chunk by estimated tokens (verified with a real tokenizer), make SECTION nesting-aware, build a new vector store, switch the agent to it as a new version (v4 stays as rollback), compare v4 and v5 on the same questions.

## 22. Fixing the index locally, and proving the fix before touching Azure (2026-10-06)
- **What changed:** `ingest.py` now sizes chunks in tokens (600 per chunk file, counted with the larger of two tokenizers), splits any source line over 400 tokens into `[part n/m]` rows with a continuation hint,
  and finds the enclosing Ruby class with a push/pop on `class` / `end`. The repo list comes from `repos.json`. Output goes to `ingest/out_v2/`; the uploaded set in `ingest/out/` is untouched.
- **Real numbers (real tokenizers, not my rough estimate):** 259 of 483 Hyperswitch chunks (53%) had exceeded 800 tokens (median 879, longest 1,513); individual lines reached 883 tokens, so no line-boundary choice could fit them.
  The rough estimate had said 67%, a reminder to measure with the real thing before sizing a fix.
- **After:** 2,954 chunks, longest 632 tokens; 105,465 numbered rows match the real source lines; every source line appears in at least one chunk; the Stripe nested-class label is fixed (0 of 13 wrong).
  `ingest/verify_chunks.py` runs these checks and refuses to pass if it read zero files.
- **Specs kept in step:** the citation checker now also strips `[part n/m]` markers and continuation hint rows; two new fixtures (C15, C16) built from a real long line; 16 of 16 pass in the reference run.
- **Takeaway:** when a fix changes what the model sees, update everything that consumes that format (checker, specs, docs) in the same step, and verify the new artefact locally before spending anything in the cloud.

## 23. Stage 5 start: let the generator pick versions, read the audit, test the security rule from outside (2026-10-06)
- **Versions:** current stable Next.js is 16.4.0 (two major versions ahead of the reference lab's 14.2.5) and TypeScript 7.0.2 is brand new. Instead of hand-pinning, we used the official generator
  (`create-next-app`, TypeScript, App Router, no Tailwind, no nested git, telemetry off); it chose Next 16.4.0, React 19.3.0 and TypeScript 5, avoiding the unproven new TypeScript major.
  The Python packages are pinned in `requirements.txt` (fastapi 0.142.2, uvicorn 0.54.0, pytest 9.1.1, httpx 0.28.1, plus the Azure packages and tiktoken).
- **The generator ships an AGENTS.md** telling coding agents to read the docs bundled in `node_modules/next/dist/docs/` before writing code, because this Next.js differs from older training data. We treat it as information
  from a package (not an instruction to obey blindly) and follow it because it matches our goal.
- **npm reported 5 high-severity vulnerabilities; we did not run its suggested `npm audit fix --force`.** All five sit in one chain (braces -> micromatch -> fast-glob -> the lint plugin -> eslint-config-next): code-linting
  tooling that is never shipped. `npm audit --omit=dev` (production dependencies) reports 0, and the "fix" would have downgraded eslint-config-next to version 14. Accepted risk, to be recorded in the security plan.
- **The server's browser-access rule was tested from outside, both ways:** our page's address gets an allow header; a wrong address gets none and its preflight is rejected (400); the server listens on 127.0.0.1 only.
  Unit tests alone would not have shown the listening address.
- **Takeaway:** a warning is a question, not an order: find what it is about, where it sits, and whether the suggested fix is worse than the problem. And test a restriction by trying to break it.

## 24. Uploading the rebuilt index: faster, and more robust against re-splitting (2026-10-06)
- **Run:** a new vector store (`codecompass-full-v2`) from the 2,954 verified chunks, started with the user's explicit approval; the agent (v4) and the old store were not touched.
- **Two settings we had not used before:** (1) `max_concurrency` for parallel file uploads (default 5; we used 12): the first 100 files completed in about 80 s instead of about 5.6 min, so roughly 40 minutes in total instead of 2 h 15 min;
  (2) `chunking_strategy`: we asked the service to keep each chunk file whole (static, 1,200 tokens, no overlap) instead of its default 800/400 splitting, which is what broke our headers.
  The script tries the setting when the store is created, before any upload, and falls back to the default if rejected; the service accepted it.
- **A monitoring mistake of mine:** I reported "upload still running" from `pgrep -f upload_chunks`, but that pattern also matches the shell running the check (its own command text contains the words), so it can never say "not running".
  The reliable evidence was the Foundry-side counts (completed / in progress / failed) and a process check that cannot match itself (`ps ... | grep "[u]pload_chunks.py --name"`).
- **Also:** a background launcher's "completed" notification only means the launcher exited, not the work it started (this happened twice).
- **Takeaway:** verify a long job from the system that does the work (here, Foundry), and check your own checks for self-matching. Ask which knobs the service has before accepting its defaults.

## 25. First live run through the real app on agent v5 (2026-10-07)
- **Setup:** agent v5 = same prompt (system_v1) and tool (file_search only), new store built from token-sized chunks (2,954 files, static chunking). Four example questions through the running API (web app -> server -> agent -> parser -> citation checker -> SQLite log).
- **Result:** all four returned valid, parsed answers; every citation the agent gave verified (two with benign notes: range slightly wide, lines off by 1); the refund-window question again gave an honest "not found" with 0 rules; all four were logged with agent version 5 and prompt version system_v1 (the server recognised the instructions as prompts/system_v1.md).
- **Cost and speed vs v4:** input tokens per question 14.8K to 16.7K (v4: 17K to 44K), latency 8 to 14 s (v4: 8 to 25 s). Smaller, whole chunks mean fewer tokens retrieved.
- **The check that matters beyond "citation verified":** the checker only proves the text is on the cited line, not that the line belongs to the connector the agent names. We checked the connector claims against the files by section: Klarna in [pm_filters.klarna] and [pm_filters.stripe] (DE present in both), UPI in [pm_filters.iatapay] at all three cited places. All correct.
- **Caveats, unmeasured:** four questions prove the chain works, not that v5 is better than v4 on accuracy; recall (did it list every payment method for India?) is not measured; the Klarna answer opens with a flat "Yes" before explaining its limits.
- **Takeaway:** verifying the evidence is half the job; verify the attribution of the evidence too.

## 26. We built toward a different demo than the one the product is for (2026-10-07)
- **Problem:** the first message in this project asked for answers across "three GitHub repos"; that became two repos, and the demo script mixed questions about a payment-gateway library with questions about a payments product.
  The product's intent (and the PRD) is one company, one codebase: a PM asks rules questions about their own product and gets accurate, checkable answers. Asking about two unrelated codebases in one demo makes it look like a general code-search tool.
- **Why it happened:** a plan from the first message was carried forward after the scope shrank, and the demo story was never re-checked against the intent. The product worked; the framing was off. It surfaced only when the demo script was being written.
- **What we did:** the demo is now one codebase (Hyperswitch). A Hyperswitch-only index was built from the same verified chunks (byte-identical to that subset of the two-codebase index) and uploaded as its own vector store; the two-codebase store stays as a later generalisation test.
  The 12 PM-style questions that were already labelled became the demo question set; the demo script, README and stage tables follow the one-codebase story.
- **Takeaway:** when scope changes, re-ask "what is the demo meant to prove?" Write the claim you want to make on stage first, then choose the data and questions that support it. Check the story against the user's intent before polishing it.

## 27. Verified-absent has classes: pure absent, near-miss, and "my vocabulary was wrong" (2026-10-07)
- **Found while verifying the Hyperswitch question set against the pinned files (with positive controls):** the trick question "refund window in days for Giropay on Stripe" is not a pure absent concept:
  the configuration has a global `[refund] max_age = 365` ("Max age of a refund in days") in the development and example files (not in the production file). Nothing is specific to Giropay or Stripe.
  It is a near-miss: a good answer says there is no Giropay- or Stripe-specific window and may mention the global setting with its scope. It is kept out of the live demo and scored for human review.
  This is the same lesson as the crypto question (the code's own words differ from the PM's), arriving again from a different direction.
- **What we did:** every question now carries a class: answerable (12, each checked: the line holds the payment method, its section is the named connector, countries and currencies equal the expected sets, and the same values hold in the production file),
  pure absent (3, terms with zero hits and controls above zero) and near-miss (1, manual review).
- **The scorer was tested like the checker:** 17 tests on synthetic replies, plus two deliberate breakages (connector check removed; values ignored) that the tests caught. A scorer that cannot fail would give false comfort on the live run.
- **Takeaway:** classify a question by what the code contains before calling it a trick; read every hit of a term you expected to be absent.

## 28. The first real user test showed our internal formatting leaking into the PM's screen (2026-10-08)
- **What the user saw** after asking "Tell me what business rules are applicable for US": evidence boxes full of `514 | [pm_filters.dwolla]` and `700 [part 3/3] | SOS,SRD,...`, a long scrolling country list with a bright white scrollbar in the dark theme,
  and a badge reading "Verified (a line-number prefix was ignored)". All of it was correct and verified, and all of it was builder jargon.
- **Cause:** we displayed the agent's quote of the code, which carries the index's own formatting, and printed every internal checker note as the badge text.
- **Fix:** the server now returns the real lines of the pinned file for each citation (`source_lines`, at most 12 lines, long lines shortened) and the UI shows those with a line-number gutter; every verified citation reads plainly
  "Citation verified" (the detail stays available at `?debug=1`); the page asks the browser for dark-theme scrollbars. Tests added for each (79 server tests). Replaying the stored US answer through the new checker confirmed all 10 rules still verify.
- **Side effect worth keeping:** the box now shows what the code actually says, not what the model claims it says, which makes the evidence more trustworthy as well as cleaner.
- **Takeaway:** the real user test found in minutes what weeks of my own checks did not, because I had been testing correctness and never what the PM would read. Test with the person who will use it, early. Also: broad questions ("what rules apply for US") produce long lists; they are honest ("I did not find a consolidated policy") but not a good demo.

## 29. First scored live run on the final index (agent v6, Hyperswitch only), and a bug in my own scoring (2026-10-08)
- **Run:** 22 live calls through the real app (12 labelled answerable questions once, the near-miss once, 3 absent-concept questions 3 times each), 25 s apart; all 22 returned HTTP 200 on agent v6 with prompt system_v1.
- **Results (offline scoring against the pinned config):** 11 of 12 answerable questions pass the strict check (right connector section, exact countries and currencies); 3 of 3 absent-concept questions pass in all 3 runs (9 of 9, no rule invented);
  0 unverified citations in 22 answers; median 11.5 s and 15K input tokens (12K to 28K).
- **The one miss (iDEAL on Stripe):** the right fact (NL, EUR) with a verified line, but taken from the default filter section instead of Stripe's own entry: a "right answer, wrong section" miss. The checker cannot catch it because the text is genuinely on that line; only a connector-aware scorer can.
- **The near-miss (Giropay refund window):** honest answer text, but one adjacent rule attached and the real global refund setting not mentioned.
- **A demo lesson:** the Klarna India question passed the scorer's idea of correct, but its second rule (Stripe absent from the Klarna pay-later connector list) reads as a contradiction of the first. Pass/fail does not measure whether a PM would be confused; read the answers you plan to show.
- **My bug:** the first summary said 0 answerable questions were run. For each trick-question run I scored just that run's answers; the scorer adds "NOT RUN" entries for every question missing from a batch, and I relabelled all of those as trick questions, overwriting the real answerable results.
  The 22 saved answers were intact; fixing the step (only touch trick questions) and re-scoring offline (`--rescore`, no Azure calls) produced the numbers above. The summary had visibly impossible numbers, which is why I did not report it.
- **Takeaway:** sanity-check a summary against what you know must be true (12 questions were asked, so "0 run" is impossible) before believing it; keep raw answers separate from scoring so scoring can be redone for free; do not reuse a function built for one purpose in a loop without reading what else it returns.
