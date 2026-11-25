"""Tests: one statement in, 3 agents debate until the Judge says enough.
Run: python test_courtroom.py  (or: python -m pytest test_courtroom.py -v)
No network or API keys needed — the LLM tests use fake clients."""
from courtroom import judge_check, parse_case, run_hearing
from samples import SAMPLES


class DeadLLM:
    provider = "openai"

    def chat(self, *a, **k):
        return None  # every call fails -> local engine must speak


class CannedLLM:
    provider = "test-llm"

    def chat(self, system, user, max_tokens=420):
        return "Canned LLM speech for testing."


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
    assert r["verdict"]["verdict"] and r["verdict"]["order"]
    assert 0 < r["verdict"]["confidence_pct"] <= 100


def test_clear_case_stops_early_thin_case_runs_longer():
    clear = run_hearing(SAMPLES[0]["case"])   # strong documents
    thin = run_hearing(SAMPLES[2]["case"])    # CCTV never shared, no witness
    assert clear["rounds_held"] == 2, clear["rounds_held"]
    assert thin["rounds_held"] >= 3, thin["rounds_held"]
    assert thin["verdict"]["verdict"].startswith("Case not proved")


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
    assert a["rounds_held"] != b["rounds_held"]


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
    assert r["verdict"]["verdict"]


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
        if "Defense lawyer" in system:
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")
