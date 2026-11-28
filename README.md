# ⚖️ Mini Courtroom — Litigation-Prep Simulator

**Hackathon:** AI for Lawyers (HackIndia, Nov 2 – Dec 1, 2026) · **Built by:** Likhith Podugu

**▶ Try it live:** https://mini-courtroom-ai-agents.onrender.com — paste a case, click "Analyse the case". (Free tier: first load after idle can take ~50s.)

Paste **one problem statement** and get a litigation-preparation
work product: an **evidence matrix**, **verified Indian legal
sources**, both sides argued, a **Judge's critique** (not a verdict),
and a **downloadable case brief** a lawyer can review.

> **What this is NOT:** it does not decide cases, give verdicts,
> predict court outcomes, or give legal advice. It stress-tests
> arguments, exposes weaknesses and missing evidence, and produces
> a cited brief. A qualified lawyer must review and verify
> everything.

```
You ── problem statement ──► ┌─────────────────────┐
                              │  Shared case file   │  (same text to all)
                              └──────┬──────┬───────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Evidence Analyst    │  fact → evidence →
                          │  Reported /          │  supports → status
                          │  Unverified /        │
                          │  Unsupported         │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Legal Research      │  ONLY verified Indian
                          │  (curated sources)   │  statutes & judgments
                          └──────────┬───────────┘
                                     ▼      ▼
                          Claimant's Counsel  Respondent's Counsel
                                     │      │
                          Round 1: Opening Statements
                          Rounds 2-6: Rebuttals ──► Judge checks after
                              │    each round: ENOUGH to assess, or CONTINUE?
                              ▼    (clear lead, or 4+ rounds, or cap)
                          Closing Arguments
                                     ▼
                          Judge: critique — unsupported claims,
                                 contradictions, evidence gaps,
                                 preliminary assessment
                                     ▼
                          Case Brief (.md) — facts, evidence, law,
                          weaknesses, missing evidence, next steps
```

A clear case stops after round 2; a close one (thin evidence, scores
tied) runs to 4+ rounds. The debate never runs past 6 rounds.

## How it works

- **Evidence Analyst** (`courtroom.py:build_evidence_matrix`) — runs
  BEFORE the debate. Each fact/claim is tied to the evidence the
  statement mentions for it and labelled **Reported** (supporting
  material exists), **Unverified** (asserted, nothing stated) or
  **Unsupported** (the statement itself says the material was never
  produced — "no bills", "footage not shared", "no witness"). A
  document merely being mentioned does not mean it supports a claim.
  Example: in the rent-deposit sample the ₹20,000 repair deduction
  is flagged **Unsupported — no bills or receipts supplied**.
- **Optional evidence notes** — paste excerpts (one per line) in the
  "Evidence / documents (optional)" field, e.g. "Clause 4, Rental
  Agreement: deposit refundable on vacating in good condition". Each
  line becomes a **Reported** matrix row with evidence
  "User-supplied evidence note", is fed to both counsel and the
  Judge, and is cited in the brief as user-supplied — reported as
  stated, never treated as a verified document. Empty evidence
  changes nothing. API: `POST /api/hearing {"case": "...",
  "evidence": "..."}`; CLI: `--evidence "..."` or
  `--evidence-file notes.txt`.
- **Legal Research** (`legal_sources.py`) — keyword retrieval over a
  small curated set of **verified** Indian sources: Indian Contract
  Act 1872 ss. 73–74, Transfer of Property Act 1882 ss. 105, 108(m)
  and (q), and the Supreme Court decisions in *Fateh Chand*
  (AIR 1963 SC 1405), *Kailash Nath Associates* ((2015) 4 SCC 136)
  and *M.S. Nagabhushan* ((2025) INSC 316). Every entry was verified
  by search before inclusion, with its source link. If no source
  supports a claim, it is labelled **unsupported — no verified
  source retrieved** instead of inventing a citation.
- **Claimant's Counsel / Respondent's Counsel** — argue from the
  evidence matrix and the retrieved sources only. Prompts forbid
  inventing facts, amounts, statutes or case names, and forbid
  citing anything but the retrieved sources.
- **Judge — critique, not a verdict** (`courtroom.py:judge_assessment`)
  — identifies unsupported claims, contradictions and evidence gaps
  and gives a **preliminary assessment** ("Potentially supported,
  subject to verification" / "Mixed — partly supported" / "Not
  established on current evidence") with supporting factors,
  weaknesses, missing evidence, legal uncertainty and what would
  change the assessment. The rubric scores (evidence / reasoning /
  consistency, each /10) measure how the arguments tracked the
  evidence — they are **not** a probability of winning. There is no
  confidence percentage, no order and no verdict.
- **Case Brief** (`courtroom.py:build_case_brief`) — structured
  Markdown: case overview, facts (reported / alleged / disputed),
  evidence matrix, legal issues, applicable law (verified citations
  only), both sides' strongest supported arguments, weaknesses,
  missing evidence, questions for the client, preliminary
  assessment. Built only from the statement, matrix, sources and
  assessment — no invented facts.
- **LLM** (`llm.py`) — every speech is generated by a real LLM when one
  is available: **Groq** when `GROQ_API_KEY` is set (recommended — very
  fast; default model `openai/gpt-oss-120b`, override with `GROQ_MODEL`),
  else **OpenAI** when `OPENAI_API_KEY` is set (any OpenAI-compatible
  endpoint works via `OPENAI_BASE_URL` + `OPENAI_MODEL`), otherwise the
  **free Pollinations API — no key needed**, so the demo works out of
  the box. Prompts ground each agent on the case facts, evidence matrix
  and verified sources only, and each speech is tagged with its source
  (`llm:groq`, `llm:openai`, `llm:pollinations`, or `local`). If the LLM
  is unreachable, that speech falls back to the local engine — a hearing
  never fails because of the network. Keys live in env vars only, never
  in the repo.

```bash
# Use Groq (recommended — fastest for the live demo)
export GROQ_API_KEY="gsk-..."        # fresh key via Secure Vault, never in the repo
python app.py --serve

# Use OpenAI
export OPENAI_API_KEY="sk-..."        # fresh key via Secure Vault, never in the repo
python app.py --serve

# Or just run it — the free no-key provider is the default.
python app.py --serve

# Offline, deterministic local engine (also what the tests use)
python app.py --sample rent-deposit --no-llm
```

## Run it

```bash
pip install -r requirements.txt

# Web UI — open http://127.0.0.1:5000, paste a case, click "Analyse the case"
python app.py --serve

# CLI — sample cases
python app.py --sample rent-deposit
python app.py --sample freelance-payment
python app.py --sample shoplifting

# CLI — your own case (LLM on by default; --no-llm for offline)
python app.py --case "Priya paid a ₹50,000 deposit ..."
python app.py --sample shoplifting --max-rounds 4

# API
curl -X POST localhost:5000/api/hearing -H 'Content-Type: application/json' \
  -d '{"case": "Priya paid a ₹50,000 deposit ..."}'
```

## Sample cases (one click in the UI)

| Sample | Issue | Why it's a good demo |
|---|---|---|
| Rental deposit dispute | tenancy | Deposit documented, but the ₹20,000 repair deduction has no bills — watch the matrix flag it Unsupported and the assessment come back Mixed |
| Freelance contract, unpaid ₹80,000 | contract | Signed contract + acceptance email vs a "delay" excuse |
| Shoplifting allegation | criminal | CCTV claimed but never shared, no witness — burden of proof bites; no verified criminal source is retrieved, so legal claims are labelled unsupported |

## API

`POST /api/hearing` `{"case": "..."}` →

```json
{
  "shared_case_statement": "...",
  "llm_provider": "pollinations",
  "rounds_held": 4,
  "stopped_by": "judge",
  "judge_checks": [{"after_round": 2, "sufficient": false,
                    "reason": "Scores are close ..."}],
  "case_summary": {"issue": "tenancy", "plaintiff": "...", "defendant": "...",
                   "amounts": ["₹50,000"], "dates": [...], "documents": [...]},
  "evidence_matrix": [{"fact": "Repairs/repainting cost ₹20,000 claimed ...",
                       "evidence": "No bills or receipts supplied",
                       "supports": "respondent", "status": "Unsupported",
                       "note": "..."}],
  "legal_sources": [{"citation": "Indian Contract Act, 1872, s. 73",
                     "url": "https://indiankanoon.org/doc/339747/", "...": "..."}],
  "sources_verified": true,
  "transcript": [{"round_no": 1, "round_name": "Opening Statements",
                  "speaker": "Prosecution", "role": "...", "text": "...",
                  "source": "llm:pollinations"}],
  "assessment": {"assessment": "Mixed — partly supported; key points remain unverified",
                 "lean": "neither",
                 "scores": {"prosecution": {...}, "defense": {...}},
                 "supporting_factors": [...], "weaknesses": [...],
                 "missing_evidence": [...], "legal_uncertainty": [...],
                 "what_would_change": [...],
                 "judge_statement": "..."},
  "brief_markdown": "# Case Brief — Preliminary Assessment\n...",
  "disclaimer": "Litigation-preparation simulation ... Not legal advice ...",
  "limitations": "Legal sources are a curated starter set ..."
}
```

`GET /api/legal-sources` → the full verified source set.

`POST /api/hearing` also accepts an optional `"evidence"` string
(pasted excerpts, one per line); each becomes a Reported matrix row
attributed as a user-supplied note, and the response echoes them as
`"evidence_notes"`.

## Evaluation — 10 cases

Hand-built cases, run against the offline local engine
(`python3 eval_cases.py` — reproducible, no network, no keys).
Each case states the expected evidence gap; the result is recorded
honestly. Misses are known limitations of the pattern-based matrix,
not hidden: the matrix only covers the fact patterns it knows, and
it does not compare times, amounts or facts for contradictions.

| Case | Expected evidence gap | System result | Actual result |
|---|---|---|---|
| Rental deposit dispute (sample) | ₹20,000 repair deduction flagged Unsupported — no bills | **Correct** | Repairs row Unsupported — 'No bills or receipts supplied'. |
| Freelance contract, unpaid ₹80,000 (sample) | 'Delay' excuse flagged Unverified — not a defence unless the contract makes it one | **Correct** | Delay row Unverified — delay is not a defence unless the contract makes it one. |
| Shoplifting allegation (sample) | CCTV footage + no witness flagged Unsupported | **Correct** | CCTV Unsupported (footage not shared); no-witness row present. |
| Tenancy — no move-out inspection report | Missing move-out inspection report flagged as an evidence gap | **Missed** | No row mentions the inspection report — the matrix only covers the patterns it knows (deposit, agreement, repairs, refund). The assessment still comes back Mixed, but the specific gap is not named. |
| Freelance — no proof of delivery | Missing delivery receipt / confirmation flagged as missing evidence | **Partial** | Delivery mentioned in the matrix, but not listed as missing evidence. |
| Shoplifting — CCTV timestamp mismatch | 3:00 AM timestamp vs 10 PM closing flagged as a contradiction | **Missed** | CCTV is flagged Unsupported (footage not shared), but the 3:00 AM vs 10 PM closing contradiction is never detected — the system does not compare times or look for contradictions between facts. |
| Tenancy — parties disagree on the deposit figure | Two different deposit figures (₹50,000 vs ₹30,000) flagged as a contradiction | **Missed** | Both amounts (₹50,000 and ₹30,000) are parsed, but the matrix uses only the first amount and never flags that the parties disagree on the deposit figure. |
| Vague one-line case | System says nothing is established — every fact Unverified | **Correct** | Assessment is 'Not established on current evidence'; the matrix is all Unverified — the system honestly says nothing is proved. |
| Shoplifting — witness never produced | Witness never produced flagged as an evidence gap | **Correct** | Weaknesses name the withheld evidence ('Evidence the statement itself says was withheld...'). No dedicated witness row, but the gap is surfaced. |
| Tenancy — landlord HAS repair bills | ₹20,000 repair deduction NOT flagged Unsupported — bills were supplied | **Partial** | Status is right (not Unsupported — bills exist), but the row's evidence text wrongly says 'No cost evidence stated in the statement'. |

Total: **5 Correct, 2 Partial, 3 Missed** out of 10 cases
(local engine, no LLM).

## Tests

```bash
python test_courtroom.py        # 21 tests, no dependencies, no network
# or: python -m pytest test_courtroom.py -v
```

Tests cover: same statement to all agents, dynamic rounds, evidence
matrix structure and statuses (rent-deposit repairs Unsupported,
shoplifting CCTV/witness Unsupported), legal-source retrieval
returns only verified entries with links, assessment has no
confidence percentage and no verdict key, the brief contains all
required sections and no invented amounts, the frontend contains
no `innerHTML` (all rendering via `textContent`), a malicious
case input (`<script>`, `<img onerror>`) is handled as data, and
the optional evidence notes (appear in matrix/brief with correct
attribution, empty evidence is a no-op, a malicious note is data
not markup).

## Files

- `courtroom.py` — parser + Evidence Analyst + 2 counsel agents +
  Judge critique + case brief + `run_hearing()` (dynamic rounds)
- `legal_sources.py` — curated verified Indian legal sources + retrieval
- `app.py` — CLI + Flask web UI / API
- `samples.py` — 3 sample cases
- `llm.py` — real LLM client (Groq → OpenAI → free Pollinations → local fallback)
- `templates/index.html` — light-theme workspace UI, XSS-safe rendering
  (`textContent` only, no `innerHTML`)
- `test_courtroom.py` — tests
- `eval_cases.py` — the 10-case evaluation above (reproducible)
- `demo-script.md` — 90-second demo script for the rent-deposit case

## Limitations

- Legal sources are a **curated starter set** (tenancy + contract
  focus), not full legal research. Criminal and other issue types
  may retrieve no source — the system says so rather than inventing
  one. A lawyer must verify applicability, jurisdiction and current
  law.
- The evidence matrix is derived **only from the statement as
  given**. It cannot see the actual documents — it can only note
  what the statement says exists, and flag what it says is missing.
- The rubric scores measure argument quality against the evidence
  matrix. They are not calibrated against real cases and are not a
  probability of winning.
- Known gaps (measured in Evaluation — 10 cases: 5 Correct, 2 Partial,
  3 Missed): the matrix does not detect contradictions between facts
  (a 3:00 AM CCTV timestamp vs a 10 PM closing, or two different
  deposit figures), it does not name gaps outside the patterns it
  knows (e.g. a missing move-out inspection report), and a repairs
  row can say "No cost evidence stated" even when bills were supplied.
- LLM speeches can still be imperfect; the local engine, the matrix
  and the "unsupported" labelling are the guardrails, not a guarantee.

## Disclaimer

Litigation-preparation simulation for education and hackathon demo
only. Not legal advice, not a real court judgment, and not a
prediction of how a real court would rule. A qualified lawyer must
review and verify everything before acting on it.
