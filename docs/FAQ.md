# CodeCompass FAQ

Questions people ask about how CodeCompass was built, why, how it was tested, and what is not done yet. Numbers come from `LEARNINGS.md` entry 29 and `eval/results/hs_live_20261007_2028.json`. Small sample: treat results as a first signal, not proof.

## Product

**Who is this for, and what problem does it solve?**

A PM who needs to know a business rule (for example which payment method works in which country) that lives in code they cannot read. Today that means booking an engineer. CodeCompass answers in plain English with the exact lines of code behind it.

**Why not just use ChatGPT or another general AI tool?**

Three differences: it only reads this one codebase (no outside knowledge), every claim is checked automatically against the real file, and "not found" is a proper answer that says where it looked. A general tool will not tell you where it did not look.

**Can I rely on it for compliance or launch decisions?**

No, and the app says so: candidate answers, verify before using in PRDs, launches or compliance decisions. It tells you what the configuration says, not what the running system does. Engineering still signs off.

**Why Hyperswitch?**

It is a real, open-source payments product, so the demo shows a real codebase without exposing anyone's private code. The rules I ask about (country and currency per payment method) are clear in its configuration files, so I can check every answer by hand.

**Does it work on other codebases?**

That is the next test. A second codebase is indexed separately but I have not tested it for the demo, so I make no claim about it.

## Design Decisions

**Why a "not found" answer instead of the best guess?**

In payments and compliance a confident wrong answer is worse than no answer. Knowing what you do not know is as valuable as the answer. It held in 9 of 9 runs on questions whose answers are not in the code.

**Why check citations with code instead of trusting the AI?**

Language models can cite a real-looking line that does not say what they claim. The checker compares the quoted text with the cited lines of the real file at a pinned commit. Result: 0 unverified citations in 22 answers.

**Why only configuration files, not all the code?**

That is where these country and currency rules are written, and it keeps the search small and checkable. The cost is that it cannot see runtime logic, merchant-level switches or feature flags. The "where I looked / what I did not find" section says that explicitly and gives a follow-up question for engineering.

**Why a pinned commit?**

Code changes. Every citation is tied to one fixed version so a PM and an engineer are looking at the same lines.

**Why no web search for the agent?**

So the code is the only source of truth. With web search it could mix in public documentation that does not match this version of the code.

**Why Azure AI Foundry?**

It gives a managed agent with file search over an index, plus traces that show exactly what the model received, how long it took, tokens and cost. That visibility is how I found and fixed problems.

**Why GPT-5 mini?**

A small model keeps each answer at about a cent and 10 to 15 seconds. I have not compared it against larger models, so I would not claim it is the best choice, only that it was enough for this test.

**Why a separate server between the web page and the agent?**

Credentials stay on the server and never reach the browser, and the server is where the citation checker and the log run.

**How did you split the code into searchable pieces?**

Each piece carries its file, section and line numbers, so the agent can name the connector and the line. Early on, pieces lost their headers and long lines were cut off; fixing that was the biggest improvement I found.

**Why log every question and add Correct / Partial / Wrong buttons?**

The verdicts become my evaluation set, so accuracy gets measured on real questions over time. The original answer is saved unchanged; only the verdict is added.

## Evidence And Limits

**How accurate is it?**

On 12 questions with answers I had checked against the config, 11 matched exactly (right connector section, exact countries and currencies). The miss gave the right fact but cited the wrong section. 0 unverified citations in 22 answers. Small sample, one run each for answerable questions, one codebase.

**What did testing find?**

Chunks losing headers, long lines being cut, an answer that attached an adjacent rule, and an answer that missed a global setting. Some are fixed; the rest are on the next-steps list.

**Are there questions it gets wrong?**

Yes. A question about a refund window gave an honest answer but missed a global refund setting. Questions that return a long list of rules are harder to read. I kept those off the stage and I say so.

**How do you know it will not make up a rule?**

I asked questions whose answers are not in the code, three questions three times each, and it invented nothing in all nine runs. That is evidence, not a guarantee, with a small sample.

**What does "Citation verified" mean exactly?**

The text the agent quoted was found on the cited lines of the real file. It does not mean the rule is complete or that nothing else overrides it.

**What does one question cost?**

About half a cent to a cent in model usage.

## Deployment, Security And Next Steps (Overview)

**Why is it running on your laptop and not on a website?**

On purpose. The server signs in to Azure with my own login, which a hosted site cannot use. A public site calling a paid AI service also needs a service identity, per-visitor limits so nobody can spend my credit, and a security review. That is the next step, in that order.

**What about security?**

Credentials never reach the browser; the server only answers its own web page; questions trying to instruct the assistant are rejected; agent text is shown as plain text. A formal security plan is not done yet.

**What would you do next?**

More codebases and a bigger test set with repeats; a second prompt version (cite the connector's own section, avoid adjacent rules, state "I only checked configuration files, engineering should confirm nothing else overrides this"); security review and rate limits; then deploy.

**What would make you stop or change course?**

If it invents rules, cites lines that do not say it, or PMs cannot act on the answers. Those are the failure conditions in my hypothesis.

## Evals In Detail

**How did you test it?**

Three layers. (1) Unit tests on the code: 79 server tests, 17 on the scorer, and 16 citation-checker cases built from real lines in the pinned repos. (2) A labelled question set for Hyperswitch, scored automatically. (3) A live run of 22 questions through the real app, saved to a results file in the repo.

**What was in the live run?**

12 questions with answers I had checked against the config (run once each), 1 near-miss question, and 3 questions whose answers are NOT in the code (run 3 times each, 9 runs). 12 + 1 + 9 = 22 answers.

**How do you decide an answer is "correct"?**

Strict, automatic scoring: it must cite the right connector's section and give the exact countries and currencies. Right fact from the wrong section counts as a miss. That is why the iDEAL on Stripe question failed: right answer (NL, EUR) but it cited the default section, not Stripe's own.

**Who wrote the expected answers?**

I took them from the config files in the pinned code and checked them by hand. I am one person, so the answer key has not been reviewed by an engineer.

**Why run the "absent" questions three times?**

Models vary between runs. A question passes only if all three runs pass, and passing means no invented rule. 3 of 3 questions passed in all runs, so 9 of 9.

**How do you know a "not found" answer is really right, i.e. the code truly does not contain it?**

By checking the code with the codebase's own vocabulary and a positive control: first search for a term known to exist and confirm it is found, and count the files read. A search that finds nothing proves nothing until the control passes.

**What is the difference between a wrong answer and an invented one?**

I score three kinds of failure separately because they need different fixes: a fabricated rule, a real but irrelevant (adjacent) rule, and a bad citation. Fabrication is the worst for trust; an adjacent rule is a prompt problem; a bad citation is caught by the checker.

**What failed or was weak?**

One of 12 answerable questions missed (wrong section). The near-miss question (Giropay refund window) gave an honest answer but attached an adjacent rule and missed a global refund setting. One question (Klarna Germany/India) returned a second rule that reads like a contradiction. I kept those off the stage.

**Is 11 of 12 statistically meaningful?**

No. It is a first signal. 12 questions, one run each, one codebase, one person writing the key. I would need many more questions and repeats before claiming a rate.

**Did you test on the second codebase?**

It is indexed separately, but I have not scored it for this demo, so I make no claim about it.

**Were the demo questions tested on the final version?**

Yes: all three passed live on the final agent version (v6).

**How fast and how expensive?**

Median about 11.5 seconds, around 15,000 input tokens per question (range about 12,000 to 28,000), roughly half a cent to a cent each. The whole 22-answer run cost a few tenths of a dollar at most.

**Does the citation check prove the answer is right?**

No. It proves the quoted text exists on the cited lines. It does not prove the rule is complete or that nothing elsewhere overrides it. The scoring against my answer key is what measures correctness.

**How will you keep measuring after the demo?**

Every question is logged, and the Correct / Partial / Wrong buttons add a verdict without changing the original answer. Those verdicts grow into a larger evaluation set. Re-scoring a saved run works offline, so a prompt change can be compared without new cost for old answers.

**What would you test next?**

More questions per codebase, repeated runs for the answerable ones, questions from real PMs rather than only mine, and the second codebase.

## Deployment In Detail

**Is it deployed?**

No. It runs locally on purpose: a web page on my laptop talking to a local server, which talks to the Azure agent. Public deployment is the next step, after the security work.

**What stops you deploying it today?**

(1) The server signs in with my personal Azure login; a hosted app needs its own service identity. (2) Anyone could spend my Azure credit without per-visitor rate limits. (3) The security review is not done. (4) Secrets must stay on the server and out of the browser.

**What would deployment look like?**

In order: service identity and secrets kept on the server, per-visitor limits and a spending cap, security review and fixes, then host the web page and server. I have not chosen a hosting provider yet, so I would not name one as decided.

**Why not put it on Netlify or a similar host today?**

A static host can serve the web page, but the server and the Azure sign-in are the hard part, and putting a paid AI service on the open internet without limits is the risk. So it is deliberately not done yet.

**How is the data protected now?**

Credentials never reach the browser; the server only answers its own web page; questions that try to instruct the assistant are rejected; agent text is shown as plain text. The logs stay in a local database on my machine. The code being searched is public open-source code, so nothing sensitive is indexed.

**What happens with a real company's private code?**

That needs more than this demo: access control on who can ask, an agreed place where the index is stored, and a review of whether sending code to a cloud model is allowed by company policy. I have not done that work and would say so.

**What if Azure is down or rate limits hit?**

The app shows a "model is busy" message and asks the user to retry; bad or empty model output is handled without crashing. During the demo I keep a recording as a fallback.

**What are the running costs at scale?**

Per question about a cent, so 1,000 questions is roughly $5 to $10. Fixed costs (the index and hosting) I have not measured, so I would not quote a total.
