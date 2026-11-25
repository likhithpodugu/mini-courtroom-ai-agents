# ⚖️ Mini Courtroom — AI Agents Debate, Judge Decides

**Hackathon:** AI for Lawyers (HackIndia, Nov 2 – Dec 1, 2026) · **Built by:** Likhith Podugu

Paste **one problem statement**. All three AI agents receive the **same**
statement — no agent gets extra facts. The Offense (Prosecution) lawyer
and the Defense lawyer debate it for 3 rounds, then the Judge scores
both sides and delivers the final verdict.

```
You ── problem statement ──► ┌─────────────────────┐
                              │  Shared case file   │  (same text to all 3)
                              └──────┬──────┬───────┘
                                     ▼      ▼       ▼
                              Prosecution  Defense  Judge (listens)
                                     │      │
                              Round 1: Opening Statements
                              Round 2: Rebuttals
                              Round 3: Closing Arguments
                                     ▼
                              Judge: scores + verdict + order
```

## How it works

- **Case parser** (`courtroom.py:parse_case`) — extracts the issue type
  (tenancy / contract / criminal / employment / consumer / property /
  accident), parties (`X vs Y`), amounts (₹), dates, and documents
  (agreement, receipt, CCTV, witness…) from the statement.
- **Prosecution Lawyer** — argues the claim, cites the documents and the
  amount, answers the defence in rebuttal.
- **Defense Lawyer** — burden of proof, gaps in the evidence, no fair
  chance to cure, proportionate relief at most.
- **Judge** — public rubric, computed from the case: evidence, reasoning,
  consistency (each /10). Verdict follows the score margin: a clear lead
  wins, a close debate is *partly allowed*, a thin criminal case is
  *not proved beyond reasonable doubt*. The order (pay / dismiss / 50%)
  follows the verdict.
- **No API keys needed** — the debate engine is deterministic and
  fact-grounded, so every different case produces a genuinely different
  debate. `llm.py` is the optional seam: set `OPENAI_API_KEY` and speeches
  are enriched by a real LLM; without it, the local engine runs untouched.

## Run it

```bash
pip install -r requirements.txt

# Web UI — open http://127.0.0.1:5000, paste a case, click "Start the hearing"
python app.py --serve

# CLI — sample cases
python app.py --sample rent-deposit
python app.py --sample freelance-payment
python app.py --sample shoplifting

# CLI — your own case
python app.py --case "Priya paid a ₹50,000 deposit ..."

# API
curl -X POST localhost:5000/api/hearing -H 'Content-Type: application/json' \
  -d '{"case": "Priya paid a ₹50,000 deposit ..."}'
```

## Sample cases (one click in the UI)

| Sample | Issue | Why it's a good demo |
|---|---|---|
| Rental deposit dispute | tenancy | Strong documents for the claimant — watch the Judge side with her |
| Freelance contract, unpaid ₹80,000 | contract | Signed contract + acceptance email vs a "delay" excuse |
| Shoplifting allegation | criminal | CCTV claimed but never shared, no witness — burden of proof bites |

## API

`POST /api/hearing` `{"case": "..."}` →

```json
{
  "shared_case_statement": "...",
  "case_summary": {"issue": "tenancy", "plaintiff": "...", "defendant": "...",
                   "amounts": ["₹50,000"], "dates": [...], "documents": [...]},
  "transcript": [{"round_no": 1, "round_name": "Opening Statements",
                  "speaker": "Prosecution", "role": "...", "text": "..."}],
  "verdict": {"verdict": "...", "winner": "prosecution",
              "scores": {"prosecution": {...}, "defense": {...}},
              "confidence_pct": 78, "reasons": [...], "order": "..."}
}
```

## Tests

```bash
python test_courtroom.py        # 5 tests, no dependencies
# or: python -m pytest test_courtroom.py -v
```

## Files

- `courtroom.py` — parser + 3 agents + judge + `run_hearing()`
- `app.py` — CLI + Flask web UI / API
- `samples.py` — 3 sample cases
- `llm.py` — optional OpenAI enrichment (key optional, fails closed)
- `templates/index.html` — light-theme courtroom UI
- `test_courtroom.py` — tests

## Disclaimer

Simulation for legal education and hackathon demo only. Not legal advice,
and not a real court judgment.
