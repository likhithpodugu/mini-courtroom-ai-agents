"""Tests: one statement in, evidence matrix + debate + Judge's critique
+ case brief out. No verdict, no confidence percentage.
Run: python test_courtroom.py  (or: python -m pytest test_courtroom.py -v)
No network or API keys needed — the LLM tests use fake clients."""
import json
import os

from courtroom import (build_case_brief, build_evidence_matrix,
                       judge_assessment, judge_check, parse_case,
                       run_hearing)
from legal_sources import SOURCES, retrieve
from samples import SAMPLES


class DeadLLM:
    provider = "openai"

    def chat(self, *a, **k):
        return None  # every call fails -> local engine must speak


class CannedLLM:
    provider = "test-llm"

    def chat(self, system, user, max_tokens=420):
        return "Canned LLM speech for testing."


def _no_confidence(result):
    assert "confidence_pct" not in json.dumps(result), \
        "confidence_pct must not appear anywhere in the result"


def test_all_three_agents_get_same_statement():
    r = run_hearing(SAMPLES[0]["case"])
    assert r["shared_case_statement"] == SAMPLES[0]["case"]
    speakers = [t["speaker"] for t in r["transcript"]]
    assert speakers.count("Prosecution") >= 3  # opening, rebuttal(s), closing
    assert speakers.count("Defense") >= 3
    assert speakers.count("Judge") == 1


def test_debate_runs_until_judge_says_enough():
    r = run_hearing(SAMPLES[1]["case"])
    assert 2 <= r["rounds_held"] <= 6
    assert r["judge_checks"], "Judge must check after each round"
    assert r["judge_checks"][-1]["sufficient"] is True
    assert r["stopped_by"] in ("judge", "max_rounds")
    assert r["transcript"][-1]["speaker"] == "Judge"
    assert r["assessment"]["assessment"]
    assert "verdict" not in r, "verdict key removed — assessment only"
    _no_confidence(r)


def test_clear_case_stops_early_thin_case_runs_longer():
    # Rent-deposit is now a genuinely mixed case: strong documents for
    # the deposit, but the ₹20,000 deduction is unsupported ("no bills"),
    # so the rubric margin is close and the debate runs longer. The
    # freelance case (signed contract + acceptance email, no gap) is
    # the clear one that stops at 2 rounds.
    clear = run_hearing(SAMPLES[1]["case"])   # strong documents, no gap
    thin = run_hearing(SAMPLES[2]["case"])    # CCTV never shared, no witness
    assert clear["rounds_held"] == 2, clear["rounds_held"]
    assert clear["assessment"]["assessment"] == \
        "Potentially supported, subject to verification"
    assert thin["rounds_held"] >= 3, thin["rounds_held"]
    assert thin["assessment"]["assessment"] == \
        "Mixed — partly supported; key points remain unverified"
    assert thin["assessment"]["unsupported_claims"]


def test_judge_check_respects_max_rounds_cap():
    case = parse_case(SAMPLES[2]["case"])
    check = judge_check(case, [], llm=None, min_rounds=2, max_rounds=2)
    # No speeches yet: rounds_held is 0, below min -> not sufficient.
    assert check["sufficient"] is False


def test_different_cases_give_different_debates():
    a = run_hearing(SAMPLES[0]["case"])
    b = run_hearing(SAMPLES[2]["case"])
    assert a["case_summary"]["issue"] != b["case_summary"]["issue"]
    assert a["transcript"][0]["text"] != b["transcript"][0]["text"]
    assert a["evidence_matrix"] != b["evidence_matrix"]
    assert a["legal_sources"] != b["legal_sources"]


def test_parser_finds_amounts_and_documents():
    c = parse_case(SAMPLES[0]["case"])
    assert "₹50,000" in c.amounts
    assert "agreement" in c.documents
    assert c.issue == "tenancy"


def test_empty_case_rejected():
    try:
        run_hearing("   ")
    except ValueError:
        return
    raise AssertionError("empty case should raise ValueError")


def test_dead_llm_falls_back_to_local_engine():
    r = run_hearing(SAMPLES[0]["case"], llm=DeadLLM())
    assert r["llm_provider"] == "openai"
    assert all(t["source"] == "local" for t in r["transcript"])
    assert r["assessment"]["assessment"]


def test_working_llm_speaks_for_the_lawyers():
    r = run_hearing(SAMPLES[0]["case"], llm=CannedLLM())
    assert r["llm_provider"] == "test-llm"
    lawyer_lines = [t for t in r["transcript"]
                    if t["speaker"] in ("Prosecution", "Defense")]
    assert lawyer_lines and all(t["source"] == "llm:test-llm"
                                for t in lawyer_lines)


class SwappingLLM:
    """Weak-model failure seen in live testing: the Defense claims to
    represent the claimant. Those speeches must fall back to local."""
    provider = "test-llm"

    def chat(self, system, user, max_tokens=420):
        if "Respondent" in system:
            return ("Ladies and gentlemen, I represent Priya Sharma, "
                    "a tenant who did everything right.")
        return "Canned LLM speech for testing."


def test_llm_side_swap_falls_back_to_local():
    r = run_hearing(SAMPLES[0]["case"], llm=SwappingLLM())
    defense = [t for t in r["transcript"] if t["speaker"] == "Defense"]
    prosecution = [t for t in r["transcript"]
                   if t["speaker"] == "Prosecution"]
    assert defense and all(t["source"] == "local" for t in defense)
    assert prosecution and all(t["source"] == "llm:test-llm"
                               for t in prosecution)


# ---- new behaviour: evidence matrix -------------------------------

def test_evidence_matrix_rent_deposit_flags_repairs_unsupported():
    case = parse_case(SAMPLES[0]["case"])
    matrix = build_evidence_matrix(case)
    assert matrix, "matrix must not be empty"
    for row in matrix:
        assert set(row) == {"fact", "evidence", "supports", "status",
                            "note"}
        assert row["status"] in ("Reported", "Unverified", "Unsupported")
        assert row["supports"] in ("claimant", "respondent", "both")
    repairs = [r for r in matrix if "Repair" in r["fact"]]
    assert repairs, matrix
    assert repairs[0]["status"] == "Unsupported", repairs
    assert "No bills" in repairs[0]["evidence"]
    deposit = [r for r in matrix if "Deposit of" in r["fact"]]
    assert deposit and deposit[0]["status"] == "Reported"


def test_evidence_matrix_shoplifting_cctv_and_witness_unsupported():
    case = parse_case(SAMPLES[2]["case"])
    matrix = build_evidence_matrix(case)
    by_fact = {r["fact"]: r for r in matrix}
    cctv = [r for r in matrix if "CCTV" in r["fact"]]
    assert cctv and cctv[0]["status"] == "Unsupported"
    assert any("Eyewitness" in f for f in by_fact), matrix
    assert any(r["status"] == "Unsupported" for r in matrix)


def test_hearing_exposes_evidence_matrix_and_assessment():
    r = run_hearing(SAMPLES[0]["case"])
    assert r["evidence_matrix"]
    assert r["assessment"]["assessment"] in (
        "Potentially supported, subject to verification",
        "Mixed — partly supported; key points remain unverified",
        "Not established on current evidence")
    assert r["assessment"]["missing_evidence"]
    assert r["assessment"]["weaknesses"]
    assert r["assessment"]["supporting_factors"]
    assert r["assessment"]["legal_uncertainty"]
    assert r["assessment"]["what_would_change"]
    assert "order" not in r["assessment"]
    _no_confidence(r)


# ---- new behaviour: verified legal sources -------------------------

def test_legal_sources_only_verified_entries_with_links():
    for src in SOURCES:
        assert src["citation"] and src["url"].startswith("http")
        assert src["excerpt"] and src["kind"] in ("statute", "judgment")
        assert src["issues"]
    tenancy = retrieve("tenancy", SAMPLES[0]["case"])
    assert tenancy, "tenancy must retrieve verified sources"
    assert all(s["id"] in {x["id"] for x in SOURCES} for s in tenancy)
    assert any("73" in s["citation"] for s in tenancy)
    assert any("108" in s["citation"] for s in tenancy)
    contract = retrieve("contract", SAMPLES[1]["case"])
    assert contract and any("74" in s["citation"] for s in contract)


def test_hearing_exposes_legal_sources():
    r = run_hearing(SAMPLES[0]["case"])
    assert r["sources_verified"] is True
    assert r["legal_sources"]
    assert all(s["url"].startswith("http") for s in r["legal_sources"])


# ---- new behaviour: case brief -------------------------------------

def test_brief_contains_required_sections_and_no_invented_amounts():
    r = run_hearing(SAMPLES[0]["case"])
    brief = r["brief_markdown"]
    for section in ("Case overview", "Facts", "Evidence matrix",
                    "Legal issues", "Applicable law",
                    "Claimant's strongest supported arguments",
                    "Respondent's strongest arguments",
                    "Weaknesses and risks", "Missing evidence",
                    "Questions for the client",
                    "Preliminary assessment"):
        assert section in brief, section
    assert "₹50,000" in brief  # stated in the case
    assert "₹20,000" in brief  # stated in the case (unsupported deduction)
    assert "₹99,999" not in brief
    assert "not legal advice" in brief.lower()
    # Brief built directly must not invent amounts either.
    case = parse_case(SAMPLES[1]["case"])
    matrix = build_evidence_matrix(case)
    sources = retrieve(case.issue, case.raw)
    assessment = judge_assessment(case, [], matrix, sources)
    b2 = build_case_brief(case, matrix, sources, assessment, [])
    assert "₹80,000" in b2 and "₹1,00,000" not in b2


# ---- frontend: no innerHTML (XSS) ----------------------------------

def test_frontend_has_no_innerhtml():
    path = os.path.join(os.path.dirname(__file__),
                        "templates", "index.html")
    html = open(path, encoding="utf-8").read()
    assert "innerHTML" not in html, "rendering must use textContent, not innerHTML"
    assert "textContent" in html
    assert "Not legal advice" in html


def test_malicious_case_input_is_data_not_markup():
    evil = ("<script>alert('xss')</script> <img src=x onerror=alert(1)> "
            "Priya Sharma paid a deposit of ₹50,000 to Ramesh Kumar under "
            "a rental agreement signed on 12 March 2025 and he refused "
            "to refund it.")
    r = run_hearing(evil)
    # Backend returns the input as data; it must not crash, and the
    # assessment/brief must be produced. Rendering safety is enforced
    # by the frontend test above (textContent only).
    assert r["assessment"]["assessment"]
    assert r["evidence_matrix"]
    assert "<script>" in r["shared_case_statement"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")
