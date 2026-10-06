# CodeCompass demo runbook

Everything lives in this folder:
`<repo>/demo`

| File | What it is |
|---|---|
| `codecompass.py` | The whole demo: ask, citation checker, PM verdicts, eval, scoreboard |
| `ground_truth.json` | 12 labeled rules + 3 trick questions |
| `build_ground_truth.py` | Rebuilds the ground truth from the config (only if you change the rules) |
| `results/eval.json` | The saved eval results behind the scoreboard |
| `results/answers/` | Saved answers, used by `--replay` |
| `RUNBOOK.md` | This file |

The agent is headless Claude Code (`claude -p`) reading a shallow clone of Hyperswitch at
`../hyperswitch` (commit d03f854). No API key needed; it uses your normal Claude Code login.
Do not move this folder away from `hyperswitch/`; the script finds the repo as its sibling.

---

## 1. Before you present (do this once, 10 minutes before)

1. Open Terminal. Make the font big (Cmd + plus a few times) and use a dark or light theme that is readable on a projector.
2. Go to the folder:
   `cd "<repo>/demo"`
3. Check Claude Code works: `claude -p "say ok"` should print "ok". If it asks you to log in, run `claude` once and log in.
4. Reset PM verdicts so the "verified" moment is fresh: `rm -f results/verdicts.json`
5. Warm up the demo question once so a saved answer exists as a fallback (takes ~20 s):
   `python3 codecompass.py ask "Why is Klarna on Stripe available in Germany but not in India?"`
6. Do the same for the trick question:
   `python3 codecompass.py ask "What is the refund window in days for Giropay payments on Stripe?"`
7. Check the scoreboard prints: `python3 codecompass.py scoreboard`
8. `clear` the screen. Have the PRD (or a slide with the problem and roadmap) open in another window.

Python 3.9 (the Mac default) is enough. No packages to install.

---

## 2. The demo, step by step (about 8 minutes)

Copy each command exactly. Say the "Say" lines in your own words.

**Step 1 (1 min): the problem.** No command. 
Say: "A PM inherits a payments product. The real source of truth for 'where is feature X on and why' is the code, and the PM can't read it. Today they book an engineering meeting, about 2 hours. CodeCompass answers in minutes with citations."

**Step 2 (2 min): live question.**
`python3 codecompass.py ask "Why is Klarna on Stripe available in Germany but not in India?"`
Takes ~20 seconds. While it runs, say: "The agent is searching the Hyperswitch repo, opening files, following the config."
Point at, in order:
- the plain-English rule with the full country and currency lists
- the green "citation verified" badge (a plain Python check opened the file and confirmed the cited line contains the quote and every country/currency)
- the category: `unknown`. Say: "It did not invent a reason. The code never says why India is excluded."
- the yellow section "Where I looked and did NOT find an answer", with the "ask engineering" question. Say: "This is the part a generic coding assistant doesn't give a PM."

**Step 3 (1 min): trick question, a rule that does not exist.**
`python3 codecompass.py ask "What is the refund window in days for Giropay payments on Stripe?"`
Expected: "No supporting rule found in the repo", plus a gap explaining the only refund setting is a generic global default. Say: "In a regulated domain a confident wrong answer is the worst outcome. It says 'not found' instead."

**Step 4 (1 min): what happens without the repo.**
`python3 codecompass.py ask "Why is Klarna on Stripe available in Germany but not in India?" --plain`
Expected: red "citation FAILED" badges. Say: "Same model, no repo access. It guesses, can't give real line numbers, and the checker rejects every citation. This is why retrieval and the checker matter."
(Be fair: the model labels its own answer 'unverified'. The point is it cannot cite.)

**Step 5 (1 min): PM verification.**
`python3 codecompass.py ask "Why is Klarna on Stripe available in Germany but not in India?" --replay --verify`
When asked, type `c` (Correct), Enter, then a note such as `matches config line 651`, Enter.
Then show the badge appears on the next ask:
`python3 codecompass.py ask "Why is Klarna on Stripe available in Germany but not in India?" --replay`
Say: "This is the verification loop. In the full product these verdicts feed back into later answers. In this demo they are only stored and shown."

**Step 6 (2 min): the scoreboard.**
`python3 codecompass.py scoreboard`
Say: "12 labeled rules and 3 trick questions from Hyperswitch. Targets from the PRD: precision over 80%, recall over 60%, citation accuracy over 90%, hallucination under 5%."
Current saved results:
- Plain LLM: precision 6%, recall 8%, hallucination 100%
- Agent: precision 100%, recall 100%, citations 100%, hallucination 0%, trick questions 2 of 3
- About 140K tokens and ~16 s per question for the agent (cost data for Week 5)

Then close with the roadmap: MVP is this; next are calibrated confidence, persistent memory, a second repo; later regulatory and KYC rules.

---

## 3. If something goes wrong

| Problem | Fix |
|---|---|
| Live call is slow or hangs (>60 s) | Ctrl+C, rerun the same command with `--replay` added. It shows the saved answer. Say "here is the run from earlier" |
| `claude: command not found` or login prompt | Run `claude` once interactively and log in, then retry |
| Output looks garbled (odd `[1m` characters) | You are not in a normal terminal; use Terminal.app or iTerm |
| `--replay` says nothing saved / re-runs live | Run the command once without `--replay` to create the saved answer |
| Whole demo fails | Play the screen recording (see below) |

## 4. Make a fallback recording (recommended, 5 minutes)

Press Cmd + Shift + 5, choose "Record Selected Portion" over the Terminal, and click Record. Run steps 2 to 6 once, then stop recording from the menu bar. Save it next to this runbook.

## 5. Questions you may get (honest answers)

- **"Is 100% real?"** It is real but the test is easy: all 12 rules are single lines in one config file. It shows config lookups work. It does not show that rules buried in Rust code, or regulatory reasons, work. Say that plainly.
- **"Why did one trick question fail?"** On the minimum-age question the agent said no age rule exists but still returned the Klarna country rule. A known weakness: it pads with related rules. The fix is to tighten the prompt to return only rules that answer the question. I did not tune on the test set.
- **"Who labeled the ground truth?"** The 12 rules were picked and read from the config by script (Claude), so spot check a few lines yourself in `config/development.toml` (line numbers are in `ground_truth.json`) before saying "hand-labeled".
- **"Why is the plain-LLM number so low?"** It had no repo access and was asked for best-guess citations. It admitted it was guessing and gave no real line numbers, so it scores near zero by design. It shows why grounding is needed, not that models are bad at this.
- **"What is cut from the PRD?"** The RAG iteration, persistent memory that improves answers, a UI, a second repo, calibrated confidence (only the citation-verified badge exists), and share links.

## 6. Re-running things

- Re-run the whole eval (~4 minutes, 30 headless runs): `python3 codecompass.py eval`
  Results are overwritten in `results/eval.json`. Numbers can shift slightly between runs, so re-run the scoreboard before presenting if you re-run the eval.
- Ask your own question: `python3 codecompass.py ask "your question here"`. Best on payment-method availability by connector, country and currency.
- Change the rules: edit the list in `build_ground_truth.py`, run it, then re-run the eval.

## 7. Where this fits in the PRD

PRD file: `CodeCompass PRD (backup before Week 2).docx` (and the `.md` copy) in the parent folder. Weeks 3 and 4 describe this eval. The PRD plans 25 rules and 5 trick questions and three iterations (plain LLM, RAG, agentic). This demo does 12 + 3 and two setups (plain LLM, agent), as agreed. Mention this if asked.
