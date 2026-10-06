## **CodeCompass: A PM's Semantic Layer Over the Codebase**

### **Week 1**

#### **PROBLEM DEFINITION**

**What problem is this solving?**

Non-technical Product Managers who inherit an existing fintech product — as a backfill, through a reorg, or as a new hire onto an established area — cannot independently understand what their product does. The real source of truth for how the product behaves lives in the code: business rules, feature flags, country-availability logic, regulatory guardrails, error handling, API contracts, and retry policies. PRDs decay, Confluence goes stale, and the actual knowledge sits in engineers' heads. Job-to-be-done: *"Help me understand what business rules govern my product — starting with which features are available in which markets and why — without booking an engineering meeting every time."*

**Who are you solving this problem for?**

*Primary persona:* Non-technical fintech PMs (0–2 years in a new area) at large regulated fintechs (Chase, Stripe, Block, Adyen, Wise, Revolut, Nubank) who inherited a product they didn't build and can't read the codebase fluently.

*Secondary persona:* Technical PMs and Product Ops at the same companies who can read code but don't have time to trace rules across microservices, feature flag systems, and config files.

Target market: Product organizations at regulated fintechs, where inherited-product ownership is the norm and every reorg resets institutional knowledge. Estimated 50k+ PMs globally at fintechs above \$100M revenue.

**Why is this problem worth solving?**

PM onboarding to inherited products takes 3–6 months at large fintechs, and "understand a rule I own" happens weekly for the life of the role. The cost is doubled: PMs lose weeks to information gathering, and engineers lose hours per week answering rule questions instead of building. Every reorg, attrition event, or team reshuffle resets this cost.

MOAT vs Claude, Cursor, Greptile, Sourcegraph Cody, Copilot: (1) PM-shaped output — plain-English rule statements structured by PM-native categories, not code snippets; (2) persistent product-mental-model that compounds across sessions rather than resetting; (3) fintech-domain evaluation — extraction is tested against real fintech rule categories (feature availability, KYC gates, transaction limits, disclosure logic) a horizontal tool cannot credibly evaluate against; (4) confidence + gap-aware output — the tool flags "I looked here and didn't find anything" as first-class output, because in regulated domains knowing where to still ask engineering is as valuable as the extracted rules; (5) assistant framing, not authority — output is candidate rules the PM verifies with code citations, not autonomous decisions.

**Why Agentic AI?**

Understanding a fintech codebase isn't a single-prompt problem. It requires multi-step reasoning: exploring files, following imports, tracing feature flag definitions to their consumers, distinguishing regulatory constraints from commercial policy from technical retries, and deciding what to explore next based on what was found. A rule-based system can grep for if country == patterns but cannot distinguish a KYC gate from an A/B test allocation — both look similar in code. LLMs are needed for the semantic judgment; agentic orchestration is needed for the multi-step exploration and for persistent memory of what the PM cares about across sessions. The value compounds: each PM correction sharpens future extractions. Rule-based logic cannot replicate this.

**How will you know that the problem is solved?**

*North Star Metric:* Time from "PM has a rule question" to "PM has a verified answer with code citation" — target: reduce from ~2 hours (via engineering meeting) to \<5 minutes (via CodeCompass + PM verification).

*Primary Metrics:*

- Extraction precision on feature-availability rules: \>80% on hand-labeled ground truth

- Extraction recall on hand-labeled ground truth: \>60%

- Citation accuracy (does cited code line actually contain the rule): \>90%

- Hallucination rate (rules extracted that don't exist anywhere): \<5%

*Secondary Metrics:*

- PM verification rate (% of extracted rules PM confirms as correct on first pass)

- Repeat-use rate (% of test PMs who query the tool more than once in a week)

- Engineering-meeting deflection (self-reported: "would you have asked eng this instead?")

#### **SOLUTION DEFINITION**

**User Flows**

*\[Flow diagram to be inserted — sketching here as text for now\]*

PM Input: "Why is Feature X available in India but not Germany?"

↓

Agent Step 1: Explore codebase — locate feature flag definitions,

country routing logic, guard clauses referencing Feature X

↓

Agent Step 2: Trace dependencies — which config files, which

services, which regulatory-guard middleware

↓

Agent Step 3: Extract candidate rules with:

\- Plain-English rule statement

\- File + line citations (multiple where applicable)

\- Confidence score

\- Rule category (regulatory / commercial / technical / unknown)

\- Explicit gaps ("I looked in X and Y but didn't find Z —

worth asking engineering")

↓

PM Verification Layer: PM marks rule as Correct / Wrong / Partial;

adds notes; agent updates persistent model

↓

Persistent Codebase Memory: agent's model of this codebase +

this PM's priorities sharpens over time

*AI drawback mitigation:*

- *Hallucination:* Every rule must come with a code citation; unverifiable rules are flagged with low confidence, not hidden. Hallucination rate is a monitored metric.

- *Explainability:* Every extracted rule shows its reasoning trace — which files were explored, why each was flagged, what the extraction inferred.

- *Overconfidence:* Confidence scores are calibrated against ground-truth evals; the UI treats \<70% confidence as "candidate for PM review," not settled fact.

- *Gaps as first-class output:* "I looked but didn't find" is a required output category, not an afterthought.

**Functional Requirements**

*MVP feature set (Phase 1: Feature-Availability Reasoning):*

1.  **Codebase ingestion** — accept a GitHub repo URL or uploaded codebase; index files with attention to feature flag definitions, config files, country/locale code, and guard clauses.

2.  **Natural-language query interface** — PM asks a question like "why is Feature X on in Country Y?" or "which features are gated to specific countries?"

3.  **Rule extraction with citations** — returns plain-English rule statements, code citations (file + line range), confidence score, and category.

4.  **Gap flagging** — for every query, agent surfaces where it looked and didn't find, so PM knows what still needs an engineering conversation.

5.  **PM verification + correction UI** — PM confirms, corrects, or annotates each extracted rule; corrections update the persistent model.

6.  **Persistent codebase memory** — extracted + verified rules, PM annotations, and query history are retained across sessions so repeated queries compound in accuracy.

7.  **Structured rule inventory view** — browsable list of all extracted-and-verified rules for this codebase, filterable by category and confidence.

*User stories (MVP):*

- As a non-technical fintech PM inheriting a product, I can point CodeCompass at my product's repo and get a browsable rule inventory within 24 hours.

- As a PM, I can ask "why is Feature X available in Country Y and not Z?" in natural language and get a cited, confidence-scored answer without opening the code.

- As a PM, I can see explicitly what CodeCompass looked at and didn't find, so I know what to still ask engineering.

- As a PM, I can mark extractions as correct/wrong so the tool improves for my next question.

- As a PM, I can share a specific rule (with its citation) as a link in a PRD or Slack, so my stakeholders can verify.

*Out of scope for MVP (explicitly deferred to later phases):*

- Regulatory rule extraction (Phase 2)

- KYC/CIP rule extraction (Phase 3)

- Compliance-gap detection / codebase compliance evaluation (Phase 4 — not in class pitch)

- Multi-stakeholder mental models (QA, legal, ops) — PM-only for MVP

- Integration with Jira, Confluence, Slack for cross-source context (V2)


### **Week 2**

**Section 3. PRIORITIZATION**

**Breaking the agentic workflow into components**

CodeCompass decomposes into five components. Components 1 and 5 are mostly conventional software; components 2–4 carry the ML risk and are where the MVP must prove itself.

PM question: "Why is Feature X available in India but not Germany?"

\|

v

\[1\] Repo ingestion & indexing --\> file map, config index, symbol index

\|

v

\[2\] Exploration agent --\> plan \> search \> read \> follow \> repeat

\|

v

\[3\] Rule extraction & category --\> rule + file:line citation + category

\|

v

\[4\] Confidence & gap detection --\> citation check + "looked, found nothing"

\|

v

\[5\] PM verification & memory --\> Correct / Wrong / Partial --\> rule inventory

\|

+---- verified rules feed back into \[2\] and \[3\] on the next query

**Component-level risk assessment**

*Target codebase for MVP and evaluation: Hyperswitch (Juspay’s open-source payments switch, Rust, Apache 2.0). It contains real feature-availability logic — which payment methods are enabled for which countries/currencies per payment processor — making it a realistic stand-in for an inherited fintech product.*

**Component: 1. Repo ingestion & indexing**

| **Check** | **Result** | **Explanation** |
|----|----|----|
| Is ML necessary? | **NOT REQUIRED** | File walking, config parsing and symbol indexing are deterministic. Deliberately no ML here — rule-based is cheaper and exact. |
| Do you have data to train/evaluate? | **PASS** | The public repository (Hyperswitch, Apache 2.0) is the data. No training required. |
| ML feasibility | **PASS** | N/A — standard tooling (grep, tree-sitter, TOML/YAML parsing). |
| Can it meet accuracy requirements? | **PASS** | Deterministic: a file is either indexed or it isn’t. |
| Can it scale? | **PASS (with caveat)** | Hyperswitch is a large multi-crate repo; index everything but prioritize config and routing paths. |
| How fast can you get feedback? | **PASS** | Immediate — index coverage is countable. |
| Applicable laws | **PASS (public) / FAIL (private)** | Public repo license permits use. Proprietary company code requires IP/InfoSec approval — out of MVP scope. |
| Bias | **PASS (with caveat)** | Parsers are language-specific; MVP supports Rust + TOML only. Other stacks disclosed as unsupported. |
| Explainability | **PASS** | The index is inspectable. |
| How easy to judge good vs. bad response? | **PASS** | Coverage report lists files indexed vs. skipped. |

**Component: 2. Exploration agent (query planning + retrieval)**

| **Check** | **Result** | **Explanation** |
|----|----|----|
| Is ML necessary? | **PASS** | Deciding what to open next (follow this flag? this connector config?) needs semantic judgment; grep alone returns hundreds of unranked hits. |
| Do you have data to train/evaluate? | **FAIL → mitigated** | No labeled "where does rule X live" dataset exists. Mitigation: hand-label 25 feature-availability rules with file:line locations in Hyperswitch (Week 3 eval). |
| ML feasibility | **PASS** | Agentic code search (plan → search → read → iterate) is proven by coding agents such as Claude Code. |
| Can it meet accuracy requirements? | **UNKNOWN (key risk)** | Recall is the main risk — rules spread across config, routing code and connector files may be missed. Target recall \>60%, measured in Week 3 eval. |
| Can it scale? | **PASS (with caveat)** | Cost and latency grow with exploration steps; cap tool calls per query. A 60-second answer is acceptable for the PM workflow. |
| How fast can you get feedback? | **PASS** | Every exploration step is logged, so failed searches are visible immediately. |
| Applicable laws | **PASS** | Reads source code only; no personal data. |
| Bias | **PASS (with caveat)** | Rules in standard config files are easier to find than rules buried in custom in-house flag frameworks. Disclosed limitation. |
| Explainability | **PASS** | The full reasoning trace (files opened, and why) is shown to the PM. |
| How easy to judge good vs. bad response? | **MEDIUM** | Checking what was found is easy; knowing what was missed requires ground truth. |

**Component: 3. Rule extraction & categorization**

| **Check** | **Result** | **Explanation** |
|----|----|----|
| Is ML necessary? | **PASS** | A regulatory gate, a commercial restriction and an A/B test all look like "if country in \[...\]" in code. Distinguishing them needs LLM semantic judgment. |
| Do you have data to train/evaluate? | **FAIL → mitigated** | Same 25-rule labeled set, with an expected plain-English statement and category for each rule. |
| ML feasibility | **PASS** | Code-to-English summarization with structured JSON output is well within frontier-model capability. |
| Can it meet accuracy requirements? | **UNKNOWN (core hypothesis)** | This is the bet: precision \>80%, hallucination \<5%, citation accuracy \>90%. Validated in Week 3 eval against pre-set pivot triggers (below). |
| Can it scale? | **PASS** | Each extraction is a bounded LLM call over retrieved snippets. |
| How fast can you get feedback? | **PASS** | Each rule can be checked against its cited lines in seconds. |
| Applicable laws | **PASS (with caveat)** | Output must not be presented as a compliance determination — framed as "candidate rules for PM review". |
| Bias | **PASS (with caveat)** | The model may over-label restrictions as "regulatory" because fintech context primes it to. Category confusion tracked in eval. |
| Explainability | **PASS** | Every rule carries a file:line citation and a reasoning note. |
| How easy to judge good vs. bad response? | **MEDIUM** | "Does this rule exist?" is objective; "is it regulatory or commercial?" is subjective — category labels need a second labeler. |

**Component: 4. Confidence scoring & gap detection**

| **Check** | **Result** | **Explanation** |
|----|----|----|
| Is ML necessary? | **PARTIAL** | Citation verification (does the cited line exist and contain the referenced value?) is deterministic. Gap reasoning ("searched X and Y, found nothing about Z") needs an LLM. |
| Do you have data to train/evaluate? | **FAIL → mitigated** | Calibration needs labeled outcomes. Use the eval set plus deliberate "trick" questions about rules that do not exist, to test honest "not found" behavior. |
| ML feasibility | **CAUTION** | LLM self-reported confidence is poorly calibrated. Mitigation: derive confidence from checkable signals (citation verified, number of corroborating locations, config vs. inferred) rather than the model’s own opinion. |
| Can it meet accuracy requirements? | **HIGH RISK** | Proving absence is hard. A false "no rule exists" is the most dangerous failure mode for a regulated-domain PM. |
| Can it scale? | **PASS** | Cheap post-extraction checks. |
| How fast can you get feedback? | **SLOW** | Calibration requires many labeled answers before confidence scores become meaningful. |
| Applicable laws | **PASS** | N/A. |
| Bias | **PASS** | N/A. |
| Explainability | **PASS** | Gap output lists exactly which paths were searched. |
| How easy to judge good vs. bad response? | **HARD** | Whether a gap is genuine requires full repo knowledge; only measurable against the labeled set. |

**Component: 5. PM verification loop & persistent memory**

| **Check** | **Result** | **Explanation** |
|----|----|----|
| Is ML necessary? | **MOSTLY NOT** | Verification UI and rule storage are standard software; the LLM is used only to retrieve relevant verified rules into later queries. |
| Do you have data to train/evaluate? | **PASS** | Generated by usage — every Correct / Wrong / Partial click is a label. |
| ML feasibility | **PASS** | Storing verified rules and injecting them into context is a simple, established pattern. |
| Can it meet accuracy requirements? | **RISK** | A wrong PM correction can poison memory. Mitigation: store corrections with provenance (who, when, citation) and make them reversible. |
| Can it scale? | **PASS** | Small structured store per repository. |
| How fast can you get feedback? | **SLOW** | Proving memory "compounds" needs repeated use over weeks. For class: simulate by re-asking eval questions after corrections. |
| Applicable laws | **PASS (with caveat)** | Stores PM notes; retention policy required for any internal deployment. |
| Bias | **PASS** | N/A. |
| Explainability | **PASS** | Each answer shows which stored, verified rules it relied on. |
| How easy to judge good vs. bad response? | **MEDIUM** | Measured as accuracy lift on repeated questions before vs. after corrections. |

**Risk summary across components**

| **Component** | **Risk level** | **Mitigation** |
|----|----|----|
| 1\. Repo ingestion & indexing | Low | Deterministic; public repo only; coverage report. |
| 2\. Exploration agent | Medium–High | Recall measured against 25 labeled rules; tool-call cap; full reasoning trace shown. |
| 3\. Rule extraction & categorization | High (core hypothesis) | Mandatory citations; precision/hallucination thresholds; pivot triggers set before the eval runs. |
| 4\. Confidence & gap detection | High | Confidence from checkable signals, not self-report; trick questions test honest "not found" answers. |
| 5\. PM verification & memory | Medium | Corrections stored with provenance and reversible; before/after re-ask test. |

**Pivot triggers (set before the Week 3 eval, so results are not rationalized post-hoc)**

- **Precision \<60%** on the 25-rule set → narrow scope to rules declared in config files only (drop inferred rules from application code).

- **Hallucination rate \>10%** → add a mandatory citation-verification pass that drops any rule whose cited lines do not contain it; re-run.

- **Recall \<40%** → pre-index all country/currency/payment-method config and give the agent that index up front instead of relying on open-ended search.

- **Still below thresholds after two iterations** → pivot the MVP from "answer any question" to "generate a static feature-availability inventory from config", which is lower-risk and still PM-useful.

**Prioritized stories and narrowed scope**

| **Story ID** | **Story** | **Priority** | **Points** | **Rationale** |
|----|----|----|----|----|
| US-001 | Point CodeCompass at a repo and have it indexed | P0 | 3 | Entry point; low risk. |
| US-002 | Ask a feature-availability question in plain English | P0 | 5 | Primary interaction surface. |
| US-003 | Receive plain-English rules with file:line citations, category and reasoning trace | P0 | 8 | Core value; highest-risk component, so must be proven first. |
| US-004 | See where the agent looked and found nothing ("gaps") | P0 | 5 | Moat — no general coding tool does this; this is where regulated-domain trust comes from. |
| US-005 | See a confidence score on each rule | P1 (MVP ships "citation verified" badge only) | 5 | Full calibration requires eval data first. |
| US-006 | Mark a rule Correct / Wrong / Partial and add notes | P1 | 3 | Cheap to build; generates labels. |
| US-007 | Corrections improve future answers (persistent memory) | P1 | 8 | Moat, but cannot be proven until enough corrections exist. |
| US-008 | Browse and filter the rule inventory | P1 | 5 | Retention value; not needed to validate the hypothesis. |
| US-009 | Share a rule with its citation as a link (PRD / Slack) | P2 | 2 | Adoption/virality; backlog. |

**MVP scope rationale:** US-001 to US-004 test the single riskiest assumption — can an agent extract correct, cited feature-availability rules from a real fintech codebase, and be honest about what it did not find? If extraction precision or gap honesty fails, memory, inventory and sharing have nothing trustworthy to build on, so they are deferred. Confidence ships only as a deterministic "citation verified" badge until eval data supports calibration. An MVP that includes everything is not an MVP.

**Section 4. ROADMAP**

| **Release** | **Features** | **Duration** |
|----|----|----|
| MVP (evaluable) | US-001 to US-004 + citation-verified badge. Single repo (Hyperswitch), feature-availability rules only, CLI or simple web UI, run locally. Evaluated on 25 hand-labeled rules. | 2 weeks |
| MVP 1 | US-005 calibrated confidence, US-006 verification, US-007 persistent memory, US-008 rule inventory. Second repo added to test generalization. | +3–4 weeks |
| Launch | US-009 share links; hosted web app; pilot with 5–10 PMs; repeat-use and engineering-deflection metrics tracked. | Months 3–4 |
| Iteration | Phase 2 regulatory rules; Phase 3 KYC/CIP rules; Jira/Confluence context; internal enterprise deployment after IP/InfoSec review. | Ongoing |

**Linkage to priorities and risks:** each release starts only once the previous release’s highest risk is retired. The MVP exists to test components 3 and 4 (High risk). MVP 1 adds component 5 (Medium) once extracted rules are trustworthy enough to be worth correcting. Launch is gated on the Week 3 launch criteria. Regulatory and KYC extraction are deferred because the cost of a wrong answer there is highest.

**Dependencies**

- Target repository confirmed (Hyperswitch).

- 25 ground-truth rules hand-labeled before the MVP eval — ideally with a second labeler for category labels.

- LLM API access and budget (Claude / Gemini).

- Pivot triggers (above) fixed before the first eval run.

### **Week 3**

*\[To be filled after extraction eval numbers are in from Week 1–2 experimentation.\]*

*Evaluation Strategy — planned approach:*

- Ground truth: hand-label 20–30 feature-availability rules in one open-source fintech-shaped repo (candidate: Hyperswitch or Apache Fineract).

- Metrics: precision, recall, citation accuracy, hallucination rate.

- Failure threshold to decide before running: pivot triggers to be set in Week 2 so results aren't rationalized post-hoc.

*Model Requirements — placeholder criteria (to be finalized Week 3):*

|  |  |  |
|:--:|----|----|
| **CRITERIA** | **REQUIREMENT** | **RATIONALE** |
| Open vs Closed Source | Closed Source (Claude / Gemini) | Long-context and reasoning quality matter more than cost for MVP demo. |
| Context Window | 200K+ tokens | Fintech microservice codebases often span thousands of files; need to hold meaningful chunks in context. |
| Modalities | Text only | Code + natural language for MVP. No vision. |
| Fine-Tuning | Not required for MVP | In-context learning + PM feedback loop is sufficient at MVP scale. |
| Latency | Medium priority | PM workflow is not real-time; a 60-second response for a well-cited answer is acceptable. |
| Accuracy | High priority | Regulated domain; hallucinated rules are worse than no output. |
| Time to Market | 6 weeks (class MVP) | Class deliverable. |

*Launch Plan — placeholder (fill after evals run):*

*\[HHH launch criteria table to be filled with real thresholds after Week 3 eval data.\]*

### **Week 4**

*\[To be filled after evaluation strategy is finalized.\]*

*Data Requirements — planned approach:*

- Fine-tuning: none for MVP.

- Data prep: hand-labeled ground truth on 1 open-source repo for eval; PM verification data collected during test sessions.

- Data quantity: 20–30 hand-labeled rules for initial eval; scale to 50+ across 2–3 repos for robustness testing.

- Iterative collection: PM verification loop generates ongoing ground-truth signal.

- Knowledge base: retrieved code chunks from the target repo; no separate RAG corpus for MVP.

*Prompt Strategy — planned approach:*

- Chain-of-Thought prompting for exploration decisions.

- Structured output (JSON) with rule / citation / confidence / category / gaps fields.

- Verification prompts that re-check extraction against the cited code.

*Responsible AI Risks & Mitigation:*

*Accountability:*

- Efficacy limits: MVP handles feature-availability rules only. Explicitly does not extract regulatory, KYC, or compliance rules — those categories are Phase 2+ and will not be inferred by the MVP.

- Sensitive data: MVP runs on public open-source repos only. No customer data. Private-repo use requires separate IP/InfoSec review — not in scope.

- Human oversight: every extracted rule requires PM verification before being trusted. Tool is positioned as assistant, not authority.

*Transparency:*

- Every rule has code citation with file + line reference.

- Reasoning trace shown for each extraction (what was explored, why).

- Confidence scores calibrated against ground-truth evals; UI shows uncertainty explicitly.

- Explicit disclosure: "This is candidate output for PM review. Verify before using in PRDs, launches, or compliance decisions."

*Fairness:*

- Codebase diversity: eval on repos with different languages, sizes, and architectures to avoid overfitting to one codebase style.

- Known gaps: codebases with heavy in-house feature flag frameworks may extract worse than those using LaunchDarkly / Split. This limitation is disclosed.

*Reliability & safety:*

- Acceptable error rates for MVP demo: precision \>80%, hallucination \<5%. Below these, tool is not "launched" (i.e., not recommended for PM use).

- Consequences of wrong output: PM makes wrong scoping call → real product risk in fintech. Mitigation: mandatory verification UX, low-confidence flagging, "ask engineering" gaps as first-class output.

- Recovery: PM correction loop; every wrong extraction becomes training signal for the persistent codebase memory.

- Monitoring: extraction accuracy tracked continuously; degradation triggers alert.

### **Week 5**

*\[To be filled once MVP is built and cost data is real, not speculated.\]*

*Costs & Accuracy Tradeoffs — to be filled with actual choices made during Weeks 1–4.*

*Development Costs — placeholder (real numbers post-build):*

Class MVP scope: single developer (self), no team. Infrastructure cost dominated by LLM API calls (Claude / Gemini) during eval and demo. Estimate: \$200–500 for 6-week build. No hosting, no infra beyond a Python script and local storage for MVP.

*Operational Costs:*

- LLM API per query (estimate to be validated).

- No hosting for class MVP; local execution only.

*Market Size:*

- TAM: ~50k PMs at fintechs \>\$100M revenue globally. At \$50/user/month, ~\$30M ARR ceiling for PM-only positioning.

- SAM: ~10–15k PMs at large US/EU fintechs where inherited-product ownership is most common. ~\$6–9M ARR realistic.

- Expansion: adjacent regulated verticals (healthtech, insurtech) roughly 3x the SAM if extraction generalizes.

*Revenue Potential — to be filled after commercial viability is validated (not in class scope).*

*Pricing Models — placeholder:*

- Per-seat SaaS (\$30–100/PM/month) if commercialized.

- Enterprise site license for large fintechs.

- Class project scope: no pricing; any private deployment (Phase 2) would be under-the-hood, not billed.

> *\*Directional Pricing — not applicable for class MVP.*
