"""Evaluation — 10 hand-built cases, local engine only.

Run: python3 eval_cases.py
No network or API keys needed. Each case states the EXPECTED evidence
gap, runs run_hearing() with the offline local engine, and records the
ACTUAL result honestly: Correct / Partial / Missed. A Missed result is
reported as a Missed result — it is a known limitation, not a failure
to run. The table printed here is the table in README.md.
"""
from courtroom import run_hearing
from samples import SAMPLES


def _blob(r):
    a = r["assessment"]
    parts = [r["assessment"]["assessment"]]
    parts += [f"{x['fact']} | {x['evidence']} | {x['status']}"
              for x in r["evidence_matrix"]]
    parts += a["weaknesses"] + a["missing_evidence"] + a["unsupported_claims"]
    return "\n".join(parts).lower()


def _matrix_row(r, word):
    return [x for x in r["evidence_matrix"] if word.lower() in x["fact"].lower()]


def check_rent_deposit(r):
    rows = _matrix_row(r, "repair")
    if rows and rows[0]["status"] == "Unsupported":
        return "Correct", "Repairs row Unsupported — 'No bills or receipts supplied'."
    return "Missed", "Repairs row not flagged Unsupported."


def check_freelance(r):
    rows = _matrix_row(r, "delay")
    if rows and rows[0]["status"] == "Unverified":
        return "Correct", "Delay row Unverified — delay is not a defence unless the contract makes it one."
    return "Missed", "Delay excuse not flagged."


def check_shoplifting(r):
    rows = _matrix_row(r, "cctv")
    wit = _matrix_row(r, "eyewitness")
    if rows and rows[0]["status"] == "Unsupported" and wit:
        return "Correct", "CCTV Unsupported (footage not shared); no-witness row present."
    return "Missed", "CCTV / witness gap not flagged."


def check_inspection(r):
    b = _blob(r)
    if "inspection" in b and ("missing" in b or "unsupported" in b):
        return "Correct", "Missing inspection report flagged."
    return ("Missed",
            "No row mentions the inspection report — the matrix only "
            "covers the patterns it knows (deposit, agreement, repairs, "
            "refund). The assessment still comes back Mixed, but the "
            "specific gap is not named.")


def check_delivery_proof(r):
    b = _blob(r)
    if "deliver" in "\n".join(r["assessment"]["missing_evidence"]).lower():
        return "Correct", "Missing delivery proof listed under missing evidence."
    if _matrix_row(r, "deliver"):
        return "Partial", "Delivery mentioned in the matrix, but not listed as missing evidence."
    return ("Missed",
            "No row flags the missing delivery receipt — the matrix has "
            "no 'delivery proof' pattern, so the gap is invisible even "
            "though the statement says no receipt exists.")


def check_timestamp(r):
    b = _blob(r)
    if "timestamp" in b or "contradict" in b:
        return "Correct", "Timestamp inconsistency flagged."
    return ("Missed",
            "CCTV is flagged Unsupported (footage not shared), but the "
            "3:00 AM vs 10 PM closing contradiction is never detected — "
            "the system does not compare times or look for contradictions "
            "between facts.")


def check_contradictory_amounts(r):
    b = _blob(r)
    if "contradict" in b:
        return "Correct", "Contradictory deposit figures flagged."
    return ("Missed",
            "Both amounts (₹50,000 and ₹30,000) are parsed, but the "
            "matrix uses only the first amount and never flags that the "
            "parties disagree on the deposit figure.")


def check_vague(r):
    if r["assessment"]["assessment"] == "Not established on current evidence":
        return ("Correct",
                "Assessment is 'Not established on current evidence'; "
                "the matrix is all Unverified — the system honestly says "
                "nothing is proved.")
    return "Missed", f"Assessment was: {r['assessment']['assessment']}"


def check_withheld_witness(r):
    b = _blob(r)
    if "withheld" in b:
        return ("Correct",
                "Weaknesses name the withheld evidence ('Evidence the "
                "statement itself says was withheld...'). No dedicated "
                "witness row, but the gap is surfaced.")
    if "witness" in b:
        return "Partial", "Witness mentioned, but not flagged as withheld."
    return "Missed", "Withheld witness not flagged."


def check_invoices_supplied(r):
    rows = _matrix_row(r, "repair")
    if not rows:
        return "Missed", "No repairs row at all."
    if rows[0]["status"] == "Unsupported":
        return "Missed", "Repairs flagged Unsupported even though bills were supplied."
    if "no cost evidence" in rows[0]["evidence"].lower():
        return ("Partial",
                "Status is right (not Unsupported — bills exist), but the "
                "row's evidence text wrongly says 'No cost evidence "
                "stated in the statement'.")
    return "Correct", "Repairs row reflects the supplied bills."


CASES = [
    {"id": "rent-deposit", "title": "Rental deposit dispute (sample)",
     "case": SAMPLES[0]["case"],
     "expected": "₹20,000 repair deduction flagged Unsupported — no bills",
     "check": check_rent_deposit},
    {"id": "freelance-payment", "title": "Freelance contract, unpaid ₹80,000 (sample)",
     "case": SAMPLES[1]["case"],
     "expected": "'Delay' excuse flagged Unverified — not a defence unless the contract makes it one",
     "check": check_freelance},
    {"id": "shoplifting", "title": "Shoplifting allegation (sample)",
     "case": SAMPLES[2]["case"],
     "expected": "CCTV footage + no witness flagged Unsupported",
     "check": check_shoplifting},
    {"id": "missing-inspection", "title": "Tenancy — no move-out inspection report",
     "case": ("Priya Sharma paid a deposit of ₹50,000 to her landlord Ramesh Kumar "
              "under a rental agreement signed on 12 March 2025. She vacated the flat "
              "on 1 October 2025 in good condition. Ramesh Kumar refused to refund "
              "the deposit, claiming ₹15,000 for damage to the walls, but no move-out "
              "inspection report was ever prepared and no photographs of damage were "
              "provided. Priya has the rental agreement and bank statement showing "
              "the deposit payment."),
     "expected": "Missing move-out inspection report flagged as an evidence gap",
     "check": check_inspection},
    {"id": "no-delivery-proof", "title": "Freelance — no proof of delivery",
     "case": ("Arjun Mehta signed a contract with TechStart Solutions to build a "
              "website for ₹80,000. Arjun says he delivered the website on 5 May "
              "2025, but TechStart says they never received it and have not paid. "
              "No delivery receipt or email confirmation of delivery exists."),
     "expected": "Missing delivery receipt / confirmation flagged as missing evidence",
     "check": check_delivery_proof},
    {"id": "cctv-timestamp", "title": "Shoplifting — CCTV timestamp mismatch",
     "case": ("A shop owner in Secunderabad accuses a customer, Vikram Rao, of "
              "stealing a watch worth ₹12,000 from the store. The owner says CCTV "
              "footage shows Vikram taking the watch at 3:00 AM, but the shop closes "
              "at 10:00 PM every night. The footage has not been shared with the "
              "police and no witness saw the theft."),
     "expected": "3:00 AM timestamp vs 10 PM closing flagged as a contradiction",
     "check": check_timestamp},
    {"id": "contradictory-amounts", "title": "Tenancy — parties disagree on the deposit figure",
     "case": ("Priya Sharma paid a deposit of ₹50,000 to her landlord Ramesh Kumar "
              "under a rental agreement signed on 12 March 2025. She vacated the flat "
              "on 1 October 2025 in good condition. Ramesh Kumar says the deposit was "
              "only ₹30,000 and refuses to refund even that ₹30,000. Priya has the "
              "rental agreement and bank statement showing the deposit payment."),
     "expected": "Two different deposit figures (₹50,000 vs ₹30,000) flagged as a contradiction",
     "check": check_contradictory_amounts},
    {"id": "vague-case", "title": "Vague one-line case",
     "case": "Ramesh owes Priya money and will not pay it back.",
     "expected": "System says nothing is established — every fact Unverified",
     "check": check_vague},
    {"id": "withheld-witness", "title": "Shoplifting — witness never produced",
     "case": ("A shop owner accuses Vikram Rao of stealing a watch worth ₹12,000. "
              "The only witness, Kiran, saw the incident but has not been produced "
              "and refused to share a statement. No CCTV footage exists."),
     "expected": "Witness never produced flagged as an evidence gap",
     "check": check_withheld_witness},
    {"id": "invoices-supplied", "title": "Tenancy — landlord HAS repair bills",
     "case": ("Priya Sharma paid a deposit of ₹50,000 to her landlord Ramesh Kumar "
              "under a rental agreement signed on 12 March 2025. She vacated the flat "
              "on 1 October 2025. Ramesh Kumar refused to refund the deposit, claiming "
              "₹20,000 for repainting and repairs, and he has provided the repair "
              "bills and invoices. Priya has the rental agreement and bank statement "
              "showing the deposit payment."),
     "expected": "₹20,000 repair deduction NOT flagged Unsupported — bills were supplied",
     "check": check_invoices_supplied},
]


def main():
    print("| Case | Expected evidence gap | System result | Actual result |")
    print("|---|---|---|---|")
    counts = {"Correct": 0, "Partial": 0, "Missed": 0}
    for c in CASES:
        r = run_hearing(c["case"])
        verdict, actual = c["check"](r)
        counts[verdict] += 1
        print(f"| {c['title']} | {c['expected']} | **{verdict}** | {actual} |")
    print()
    print(f"Total: {counts['Correct']} Correct, {counts['Partial']} Partial, "
          f"{counts['Missed']} Missed out of {len(CASES)} cases "
          "(local engine, no LLM).")


if __name__ == "__main__":
    main()
