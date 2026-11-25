"""Tests: one statement in, 3 agents debate, Judge decides. Run: python -m pytest test_courtroom.py -v  (or python test_courtroom.py)"""
from courtroom import parse_case, run_hearing
from samples import SAMPLES


def test_all_three_agents_get_same_statement():
    r = run_hearing(SAMPLES[0]["case"])
    assert r["shared_case_statement"] == SAMPLES[0]["case"]
    speakers = [t["speaker"] for t in r["transcript"]]
    assert speakers.count("Prosecution") == 3  # opening, rebuttal, closing
    assert speakers.count("Defense") == 3
    assert speakers.count("Judge") == 1


def test_debate_has_three_rounds_then_verdict():
    r = run_hearing(SAMPLES[1]["case"])
    rounds = [t["round_no"] for t in r["transcript"]]
    assert rounds == [1, 1, 2, 2, 3, 3, 4]
    assert r["verdict"]["verdict"]
    assert r["verdict"]["order"]
    assert 0 < r["verdict"]["confidence_pct"] <= 100


def test_different_cases_give_different_debates():
    a = run_hearing(SAMPLES[0]["case"])
    b = run_hearing(SAMPLES[2]["case"])
    assert a["case_summary"]["issue"] != b["case_summary"]["issue"]
    assert a["transcript"][0]["text"] != b["transcript"][0]["text"]
    assert a["verdict"]["verdict"] != b["verdict"]["verdict"] or \
        a["case_summary"]["plaintiff"] != b["case_summary"]["plaintiff"]


def test_parser_finds_amounts_and_documents():
    c = parse_case(SAMPLES[0]["case"])
    assert "₹50,000" in c.amounts
    assert "rental agreement" in c.documents or "agreement" in c.documents
    assert c.issue == "tenancy"


def test_empty_case_rejected():
    try:
        run_hearing("   ")
    except ValueError:
        return
    raise AssertionError("empty case should raise ValueError")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")
