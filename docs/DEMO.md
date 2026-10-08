# Demo script: one product, one codebase (3 minutes)

**The story:** "I'm a product manager on a payments product. The rules about which payment method works in which country live in the code, and I can't read it. CodeCompass answers in plain English, and every answer points to the exact lines of code."
The codebase is **Hyperswitch**, an open-source payments product, standing in for "your product's code". Only this one codebase is indexed for the demo.
Say only what you can back up. Numbers come from `LEARNINGS.md` entry 29 and `eval/results/hs_live_20261007_2028.json`.

## Before you start (not part of the 3 minutes)
- Tab 1: `http://localhost:3000` (the PM view). Tab 2: Foundry, Agents, Codecompass-agent, **Traces** (range: Last day). Tab 3: the same agent's **Playground** page (to show the tools).
- Terminal 1: project folder, `.venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000`. Terminal 2: `cd web && npm run dev`. `az login` must be valid.
- Warm up with one throwaway question and let it finish. Wait 20 s between questions (token quota). "Model is busy": wait a minute.
- Keep the questions in a notes file to paste. An answer takes 10 to 15 s: start talking when you press Ask.

## Questions to paste (all three passed live on agent v6)
| # | Paste | What the PM sees |
|---|---|---|
| 1 | `In which markets can customers pay with Walley on Adyen?` | One rule: SE, NO, DK, FI; DKK, EUR, NOK, SEK; verified line (`production.toml` 435) |
| 2 | `Why can't we use Giropay on Stripe outside Germany?` | One rule: Germany only, EUR, in both environments (`production.toml` 718, `development.toml` 658); honest "no reason stated in the code" |
| 3 | `What minimum customer age is required to use Klarna on Stripe?` | "No matching rule found" and where it looked (passed in 3 of 3 runs) |

Backups: `Where is MobilePay available on Adyen?` (DK, FI), `Which countries support Flexiti?` (CA), `Which countries does Hyperswitch block for sanctions reasons?` (honest not-found, 3 of 3 runs).
**Do not show:** the Klarna Germany/India question (its second rule reads as a contradiction), broad questions like "what rules apply for US" (long lists), the Giropay refund-window question (the config has a global refund setting the answer missed), any question you have not run on the final index.

## Script (3:00)
**0:00 to 0:35, context.** "Imagine you're a product manager who just inherited a payments product. The rules about which payment method works in which country live in the code, and you can't read them, so every question means booking an engineer. CodeCompass lets you ask in plain English, and every answer points to the exact line of code behind it. My example is Hyperswitch: an open-source payments platform that connects a business to many payment providers, like Stripe or Adyen, through one interface."

**0:35 to 1:05, question 1.** Paste #1, press Ask, keep talking: "A question a PM really asks. While it works, it's searching an index of this one codebase." Point at the answer, the rule card, the **real lines of code** with line numbers, and the green **"Citation verified"**. "Every claim comes with the file, the line, and an automatic check that the code really says that."

**1:05 to 1:25, question 2.** Paste #2. "A restriction." Point at: Germany only, euros, the evidence. "A rule I can act on, with evidence I can show an engineer."

**1:25 to 1:55, the honesty moment.** Paste #3. "Now the one that matters most: something the code does not say." Point at **"No matching rule found in the indexed code"** and **"Where I looked and did not find it"**. "It doesn't invent a minimum age. It tells me where it looked and what to ask engineering. In a regulated business, knowing what you don't know is as valuable as the answer." Click **Correct**, show "Saved": "Every question is logged, and verdicts become my evaluation set."

**1:55 to 2:35, Foundry and why it runs locally.** (1) **Traces** (10 s): "Each question is a trace: time, tokens in and out, and the estimated cost, about a cent each." (2) Click the newest trace (15 s): "This is what the model actually received: the chunks it retrieved, each with its file, section and line numbers. That's how it can name the connector and the line." (3) Agent page, Tools (15 s): "One tool: file search over this one codebase's configuration. No web search, so the code is the only source of truth." (4) Why it runs on my laptop (10 s): "I run this on my laptop on purpose, not on a public site: the agent signs in with Microsoft credentials, and putting a paid AI service on the open internet needs proper credentials, per-visitor limits and a security review first. Those are my next steps."

**2:35 to 3:00, close.** "I tested it with questions whose answers are not in the code: in 9 of 9 runs it invented nothing. On 12 questions with answers I'd checked against the config, 11 matched exactly; the one miss gave the right fact from the wrong section. Testing also found real defects, like chunks losing their headers, which I fixed. It's a small sample, and the next step is more codebases and a bigger test set. It's all public on GitHub, including the build log of what went wrong and how I fixed it. Happy to take questions."

## If asked
- **What is Hyperswitch, in one line?** "A switchboard for payments: a business connects once, and Hyperswitch handles many payment providers (connectors) behind it. Which method is allowed in which country and currency is set as configuration in its code." (Published as open source by Juspay under Apache 2.0. Do not claim who uses it or how big it is.)
- **How accurate is it?** "11 of 12 labelled questions matched exactly on a first run, 0 unverified citations in 22 answers, and 9 of 9 absent-concept runs returned no invented rule. Small sample, one run each for the answerable ones."
- **Does it work on other codebases?** "That's the next test. A second codebase is indexed separately; I haven't put it in front of this demo." (Do not claim results for it.)
- **Why not a general AI tool?** The output is in PM language, every claim is checked against the pinned source, and "not found" is a first-class answer. A general tool won't tell you where it did not look.
- **Why not deploy it (for example on Netlify)?** "Deliberately local for the demo. The server signs in to Azure with my own login, which a hosted site cannot use; a hosted version needs a service identity and secrets kept out of the browser. Without per-visitor rate limits anyone could spend my Azure credit, and the security review (stage 8 of my plan) is not done. Deploying is the next step, in that order."
- **Which version of the code?** A pinned commit; every citation is tied to it.
- **Security?** Credentials never reach the browser (sign-in is `az login` on the server); the server only answers its own web page; questions that try to instruct the assistant are rejected; agent text is shown as plain text.
- **Builder view:** add `?debug=1` to the address to show server status, seconds, tokens and agent version under each answer, and the category label.

## If something goes wrong
Slow answer: keep talking about the Foundry architecture. "Model is busy": wait a minute. Page blank: refresh. Server down: restart terminal 1. A strange answer: "this is exactly why there's a verify note and the evidence box", and move on. Have a recording of a good run ready.
