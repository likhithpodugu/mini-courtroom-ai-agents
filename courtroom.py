"""
Mini Courtroom — litigation-prep simulator, not a court.

Flow:
    1. The user passes ONE problem statement.
    2. An Evidence Analyst parses it into an evidence matrix BEFORE
       anyone argues: each fact/claim is tied to the evidence mentioned
       for it and labelled Reported / Unverified / Unsupported. A
       document merely being mentioned does NOT mean it supports a
       claim; evidence the statement says was withheld or never
       produced cannot count for the claimant.
    3. Legal Research retrieves ONLY verified Indian legal sources
       (legal_sources.py — statutes and judgments verified by search).
       If no source supports a claim, it is labelled unsupported.
    4. Claimant's Counsel and Respondent's Counsel debate the same
       statement, grounded on the evidence matrix and the retrieved
       sources (Opening -> Rebuttals -> Closing, 2-6 rounds, Judge
       checks after each rebuttal round).
    5. The Judge CRITIQUES both sides — it does not decide the case.
       It identifies unsupported claims, contradictions, missing
       elements and evidence gaps, and gives a preliminary assessment
       (e.g. "Potentially supported, subject to verification") with
       supporting factors, weaknesses, missing evidence and legal
       uncertainty. There is no verdict, no order and no confidence
       percentage: a rubric score is not a probability of winning.
    6. A structured case brief is generated for a lawyer to review.

No API keys needed: the agents are a deterministic, fact-grounded
argument engine. It parses the case for parties, amounts, dates,
documents and the issue type, then builds every speech from THOSE
facts — so a different case produces a genuinely different debate,
not the same canned script. `llm.py` is the optional seam: if a
GROQ_API_KEY / OPENAI_API_KEY is set, speeches are enriched by a
real LLM; otherwise the free Pollinations API is used, and the
local engine runs untouched (the hackathon demo path).

This is a simulation for legal education and litigation preparation.
Not legal advice, not a real court judgment, and not a prediction
of how a real court would rule.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from legal_sources import format_for_prompt, retrieve


# ---------------------------------------------------------------- case parsing

ISSUE_TYPES = [
    ("tenancy", ["rent", "landlord", "tenant", "deposit", "evict", "lease",
                 "flat", "house", "apartment", "pg ", "room"]),
    ("contract", ["contract", "agreement", "freelance", "payment", "invoice",
                  "deliver", "project", "client", "vendor", "breach",
                  "deadline", "milestone"]),
    ("criminal", ["theft", "steal", "stole", "shoplift", "robber", "assault",
                  "fraud", "cheat", "forgery", "police", "arrest", "fir",
                  "criminal", "guilty"]),
    ("employment", ["employ", "salary", "terminat", "fired", "resign",
                    "notice period", "workplace", "manager", "hr "]),
    ("consumer", ["defect", "refund", "warranty", "product", "service",
                  "customer", "bought", "purchase", "seller"]),
    ("property", ["property", "land", "boundary", "plot", "ownership",
                  "encroach"]),
    ("accident", ["accident", "injur", "negligence", "damage", "collision",
                  "hospital"]),
]

DOC_KEYWORDS = ["agreement", "contract", "receipt", "invoice", "email",
                "message", "whatsapp", "chat", "cctv", "photo", "video",
                "witness", "bill", "bank statement", "document", "letter",
                "recording", "certificate"]

EVIDENCE_WORDS = ["proof", "evidence", "showed", "shows", "recorded",
                  "signed", "paid", "received"]

WITHHELD_PHRASES = ["not been shared", "not shared",
                    "has not been produced", "not produced",
                    "not been provided", "no witness",
                    "never produced", "refused to share",
                    "no bills", "no receipts", "no receipt",
                    "no stock record"]


@dataclass
class ParsedCase:
    raw: str
    issue: str = "civil dispute"
    plaintiff: str = "the Claimant"
    defendant: str = "the Defendant"
    amounts: list = field(default_factory=list)
    dates: list = field(default_factory=list)
    documents: list = field(default_factory=list)
    sentences: list = field(default_factory=list)
    key_facts: list = field(default_factory=list)
    # Evidence the statement itself says was NOT produced (e.g. CCTV
    # "not shared", "no witness") — it cannot count for the claimant.
    evidence_withheld: bool = False

    @property
    def amount_text(self) -> str:
        return self.amounts[0] if self.amounts else ""

    @property
    def has_amount(self) -> bool:
        return bool(self.amounts)

    @property
    def has_documents(self) -> bool:
        return bool(self.documents)


def parse_case(statement: str) -> ParsedCase:
    text = " ".join(statement.split())
    low = text.lower()
    pc = ParsedCase(raw=text)

    # Issue type: first keyword family that matches.
    for issue, kws in ISSUE_TYPES:
        if any(k in low for k in kws):
            pc.issue = issue
            break

    # Parties: "X vs Y" / "X filed against Y" / role cues / first two names.
    m = re.search(r"(.{2,40}?)\s+(?:vs\.?|v\.?|versus)\s+(.{2,40})",
                  text, re.I)
    m2 = re.search(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})\s+"
                   r"(?:filed|sued|complained) against\s+"
                   r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})", text)
    m3 = re.search(r"accuses?\s+(?:a\s+\w+,\s+)?"
                   r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,1}),?\s+of", text)
    if m:
        pc.plaintiff = m.group(1).strip(" ,.")
        pc.defendant = m.group(2).strip(" ,.").split(",")[0].split(" filed")[0]
    elif m2:
        pc.plaintiff, pc.defendant = m2.group(1), m2.group(2)
    elif m3:
        pc.defendant = m3.group(1)
        pc.plaintiff = "the Complainant"
    else:
        names = re.findall(r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){1,2})\b", text)
        names = [n for n in names
                 if not any(w in n for w in
                            ("March", "April", "June", "July", "August",
                             "October", "November", "December", "January",
                             "February", "September", "Hyderabad",
                             "Secunderabad", "Kondapur"))]
        seen, uniq = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        if len(uniq) >= 2:
            pc.plaintiff, pc.defendant = uniq[0], uniq[1]
        elif pc.issue == "criminal":
            pc.plaintiff, pc.defendant = "the State", "the Accused"

    pc.amounts = [a.rstrip(",") for a in re.findall(
        r"₹\s?[\d,]+(?:\.\d+)?|\bRs\.?\s?[\d,]+(?:\.\d+)?"
        r"|\bINR\s?[\d,]+(?:\.\d+)?|\$\s?[\d,]+(?:\.\d+)?"
        r"|\b[\d,]+\s?(?:rupees|lakh|lakhs|crore)\b", text, re.I)]
    pc.dates = re.findall(r"\b\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|"
                          r"Oct|Nov|Dec)[a-z]*\s\d{4}\b|\b\d{1,2}[/-]\d{1,2}"
                          r"[/-]\d{2,4}\b|\b(?:January|February|March|April|"
                          r"May|June|July|August|September|October|November|"
                          r"December)\s+\d{4}\b", text, re.I)

    def _document_present(keyword: str) -> bool:
        for m in re.finditer(rf"\b{re.escape(keyword)}s?\b", low):
            prefix = low[max(0, m.start() - 60):m.start()]
            prefix = prefix.split(".")[-1]  # same sentence only
            if re.search(r"\bno\s+(?:\w+\s+){0,2}$", prefix):
                continue
            return True
        return False

    pc.documents = sorted({k for k in DOC_KEYWORDS if _document_present(k)})
    pc.evidence_withheld = any(p in low for p in WITHHELD_PHRASES)
    pc.sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    pc.key_facts = [s for s in pc.sentences
                    if any(w in s.lower() for w in
                           ["paid", "refus", "fail", "agre", "sign", "promis",
                            "demand", "loss", "damag", "took", "gave", "owe",
                            "breach", "denied", "terminat"])]
    return pc


# ---------------------------------------------------------------- evidence analyst

def build_evidence_matrix(case: ParsedCase) -> list[dict]:
    """Evidence Analyst step — runs BEFORE the debate.

    One row per fact/claim: what is asserted, what evidence is
    mentioned for it, which side it supports, and its status:
      Reported    — the statement says supporting material exists
                    (a named document, receipt, photo, email…)
      Unverified  — asserted in the statement, no supporting material
                    stated
      Unsupported — the statement itself says the supporting material
                    was not produced / does not exist ("no bills",
                    "footage not shared", "no witness"). This cannot
                    count for the party asserting it.
    A document merely being mentioned never upgrades a row beyond
    what that document actually shows.
    """
    low = case.raw.lower()
    rows: list[dict] = []

    def add(fact, evidence, supports, status, note=""):
        fact = fact.strip()
        if not fact or any(r["fact"] == fact for r in rows):
            return
        rows.append({"fact": fact, "evidence": evidence,
                     "supports": supports, "status": status,
                     "note": note})

    def _amount_in(sentence: str) -> str:
        m = re.findall(r"₹\s?[\d,]+(?:\.\d+)?|\bRs\.?\s?[\d,]+", sentence)
        return m[0] if m else (case.amount_text or "")

    # Deposit / payment actually made (tenancy-style cases).
    if "deposit" in low and case.amount_text:
        docs = [d for d in ("bank statement", "receipt", "agreement")
                if d in case.documents]
        add(f"Deposit of {case.amount_text} was paid",
            ", ".join(docs) if docs else "Asserted in the statement only",
            "claimant", "Reported" if docs else "Unverified",
            "Payment is documented, not just asserted." if docs else
            "No payment record is mentioned in the statement.")

    # Signed agreement / contract on record.
    if "agreement" in case.documents or "contract" in case.documents:
        doc = "agreement" if "agreement" in case.documents else "contract"
        add(f"Signed {doc} on record", doc, "both", "Reported",
            "The agreement's actual terms are not in the statement — "
            "they must be read before relying on any clause.")

    # Property returned in good condition.
    if "good condition" in low:
        add("Property returned in good condition",
            "Photos of the property on the day of leaving"
            if "photo" in case.documents else "Tenant's assertion only",
            "claimant", "Reported" if "photo" in case.documents
            else "Unverified")

    # Repair / repainting deduction claimed.
    if "repair" in low or "repaint" in low:
        sent = next((s for s in case.sentences
                     if "repair" in s.lower() or "repaint" in s.lower()), "")
        amt = _amount_in(sent)
        no_proof = any(p in low for p in ("no bills", "no receipts",
                                          "no receipt", "no invoice"))
        add(f"Repairs/repainting cost {amt} claimed by the respondent"
            if amt else "Repairs/repainting cost claimed by the respondent",
            "No bills or receipts supplied" if no_proof
            else "No cost evidence stated in the statement",
            "respondent", "Unsupported" if no_proof else "Unverified",
            "An unproved deduction cannot stand on the named figure "
            "alone — loss must be proved (see Kailash Nath, 2015).")

    # Work delivered and accepted (contract cases).
    if "deliver" in low and ("accept" in low or "confirmed" in low):
        add("Work delivered and accepted by the client",
            "Delivery email / acceptance email"
            if "email" in case.documents else "Acceptance asserted",
            "claimant", "Reported" if "email" in case.documents
            else "Unverified")

    # Payment / refund withheld — the disputed claim itself.
    if "not paid" in low or "has not paid" in low or \
            "refused to refund" in low:
        fact = ("Deposit refund refused" if "refund" in low
                else "Payment withheld / not paid")
        add(fact, "Asserted in the statement — this is the disputed "
                  "claim, not a proved fact",
            "claimant", "Reported",
            "The refusal is the grievance; it does not prove the "
            "underlying entitlement.")

    # CCTV said to show the act (criminal cases).
    if "cctv" in low:
        withheld = any(p in low for p in WITHHELD_PHRASES)
        add("CCTV footage said to show the alleged act",
            "Footage not shared / not produced" if withheld
            else "CCTV footage (asserted, not in evidence)",
            "claimant", "Unsupported" if withheld else "Unverified",
            "Evidence that is claimed but never produced cannot "
            "support the allegation.")

    # No eyewitness.
    if "no witness" in low:
        add("Eyewitness to the alleged act", "No witness",
            "respondent", "Unsupported",
            "The absence of a witness is itself a gap in the case.")

    # Item said to be missing, with no stock record.
    if "stock record" in low and "no " in low:
        add("Item missing from stock",
            "No receipt or stock record proving it is missing",
            "respondent", "Unsupported")

    # Theft allegation itself.
    if case.issue == "criminal" and any(w in low for w in
                                        ("steal", "theft", "stealing")):
        add(f"Theft of an item worth {case.amount_text} alleged"
            if case.amount_text else "Theft alleged",
            "Complainant's assertion only", "claimant", "Unverified",
            "An allegation is not evidence of the act.")

    # Delay offered as the explanation (contract cases).
    if "delay" in low:
        add("Project was delayed (respondent's explanation)",
            "No penalty clause in the contract; no delay evidence stated",
            "respondent", "Unverified",
            "Delay, even if true, is not a defence unless the contract "
            "makes it one.")

    # Fallback: key-fact sentences not yet covered, so the matrix is
    # never empty for an arbitrary case. Only used when the targeted
    # patterns above found little — otherwise it just duplicates rows.
    if len(rows) < 3:
        for s in case.key_facts:
            if len(rows) >= 6:
                break
            if any(r["fact"][:40].lower() in s.lower() or
                   s[:40].lower() in r["fact"].lower() for r in rows):
                continue
            doc = next((d for d in case.documents if d in s.lower()), "")
            add(s[:140], doc or "No supporting material stated",
                "both", "Reported" if doc else "Unverified")
    if not rows:  # last resort — one row per sentence, capped
        for s in case.sentences[:4]:
            add(s[:140], "No supporting material stated",
                "both", "Unverified")
    return rows


def missing_evidence(matrix: list[dict]) -> list[str]:
    """What a lawyer should obtain next, from the Unsupported rows."""
    out = []
    for r in matrix:
        if r["status"] == "Unsupported":
            out.append(f"{r['fact']} — produce the supporting material "
                       f"(currently: {r['evidence'].lower()}).")
    return out


# ---------------------------------------------------------------- agents

@dataclass
class Speech:
    round_no: int
    round_name: str
    speaker: str          # "Prosecution" | "Defense" | "Judge"
    role: str
    text: str
    source: str = "local"  # "local" | "llm:<provider>"


def _evidence_summary(matrix: list[dict]) -> str:
    rep = sum(1 for r in matrix if r["status"] == "Reported")
    uns = sum(1 for r in matrix if r["status"] == "Unsupported")
    unv = sum(1 for r in matrix if r["status"] == "Unverified")
    return (f"Evidence matrix: {rep} reported, {unv} unverified, "
            f"{uns} unsupported.")


class BaseLawyer:
    """Both lawyers get the SAME case, evidence matrix and sources."""
    side: str = ""
    role: str = ""

    def __init__(self, case: ParsedCase, matrix=None, sources=None):
        self.case = case
        self.matrix = matrix or []
        self.sources = sources or []

    def _facts_line(self) -> str:
        c = self.case
        bits = []
        if c.amount_text:
            bits.append(f"the disputed sum of {c.amount_text}")
        if c.dates:
            bits.append(f"the events of {c.dates[0]}")
        if c.documents:
            bits.append(f"the {', '.join(c.documents[:3])} on record")
        return "; ".join(bits) if bits else "the facts as stated"

    def _unsupported_line(self) -> str:
        bad = [r["fact"] for r in self.matrix
               if r["status"] == "Unsupported"]
        return "; ".join(bad) if bad else ""


class ProsecutionLawyer(BaseLawyer):
    side, role = "prosecution", "Claimant's Counsel"

    def opening(self) -> str:
        c = self.case
        claim = {
            "tenancy": "an unlawfully withheld deposit",
            "contract": "a clear breach of contract and unpaid dues",
            "criminal": "an offence the complainant's account describes",
            "employment": "an unlawful termination and unpaid salary",
            "consumer": "a defective product/service and a refused refund",
            "property": "an unlawful encroachment on rightful property",
            "accident": "negligence that directly caused injury and loss",
        }.get(c.issue, "a wrong that caused real loss to my client")
        ev = _evidence_summary(self.matrix)
        return (
            f"Your Honour, {c.plaintiff} brings this case because of {claim}. "
            f"The facts are simple and they are documented: {self._facts_line()}. "
            f"{ev} The reported evidence supports my client's account, and "
            f"I will argue from the record — not from assertion. "
            f"{c.defendant} accepted the obligation and then failed to honour it. "
            f"My client should not have to chase what was promised."
        )

    def rebuttal(self, defense_opening: str) -> str:
        c = self.case
        doc = (f"The {c.documents[0]} alone answers the defence — it records "
               f"exactly what was agreed, and {c.defendant} cannot rewrite it now."
               if c.documents else
               "The defence offers explanations, not evidence — no document, "
               "no record, nothing that contradicts my client's account.")
        return (
            f"My learned friend asks the Court to doubt what is plain. {doc} "
            f"The defence has not denied the core facts — only their consequences. "
            f"Where a party takes a benefit and refuses the corresponding duty, "
            f"the law does not reward the refusal. "
            + (f"On {c.amount_text}, the figure is not disputed, only the will to pay it. "
               if c.amount_text else "") +
            "I ask that the record be judged on the evidence matrix, not on sympathy."
        )

    def closing(self) -> str:
        c = self.case
        return (
            f"In closing: the reported evidence points one way. "
            f"{c.plaintiff} performed their part; {c.defendant} did not. "
            f"The strongest supported points for my client are the documented "
            f"facts in the evidence matrix. What my client seeks is a fair "
            f"assessment of those facts — and the chance to put the missing "
            f"evidence before a real lawyer and a real court."
        )


class DefenseLawyer(BaseLawyer):
    side, role = "defense", "Respondent's Counsel"

    def opening(self) -> str:
        c = self.case
        facts = self._facts_line()
        facts = facts[0].upper() + facts[1:]
        bad = self._unsupported_line()
        return (
            f"Your Honour, my client {c.defendant} disputes this case in full. "
            f"The other side has told a tidy story, but a tidy story is not proof. "
            f"{facts} — none of it, on its own, proves "
            f"liability. {_evidence_summary(self.matrix)} "
            + (f"The other side's own statement flags these as unsupported: {bad}. "
               if bad else "") +
            f"The burden rests entirely on {c.plaintiff}, and that "
            f"burden has not been met on the evidence as it stands."
        )

    def rebuttal(self, prosecution_opening: str) -> str:
        c = self.case
        gap = ("no independent witness and no contemporaneous record has been "
               "produced to corroborate the claim"
               if not c.documents else
               f"the {', '.join(c.documents[:2])} show what happened, but they do "
               f"not show what the other side claims they show — the interpretation "
               f"is theirs, not the document's")
        bad = self._unsupported_line()
        return (
            f"With respect, the claimant's case rests on assertion. {gap.capitalize()}. "
            + (f"The evidence matrix itself marks as unsupported: {bad}. "
               if bad else "") +
            f"My client was never given a fair chance to cure the issue, and no "
            f"notice or opportunity to explain was afforded before this claim was filed. "
            f"An inference is not evidence, and a disputed figure — "
            + (f"{c.amount_text} — " if c.amount_text else "") +
            "does not become a debt merely because it is repeated loudly. "
            "Any assessment must say what is missing, not paper over it."
        )

    def closing(self) -> str:
        c = self.case
        return (
            f"In closing: doubt is not a technicality, it is the "
            f"standard. {c.plaintiff} has not proved the case on the "
            f"evidence as it stands, and my client should not pay for a claim "
            f"built on gaps. The honest assessment here is to name the gaps — "
            f"the unsupported claims and the missing evidence — so a lawyer "
            f"knows exactly what to obtain next."
        )


# ---------------------------------------------------------------- judge (critique, not a verdict)

def _score(case: ParsedCase, speeches: list[Speech]) -> dict:
    """Public rubric, computed from the case — an argument-quality
    score, NOT a probability of winning and NOT a verdict. It only
    decides how long the debate runs and which way the assessment
    leans; the assessment itself is qualitative."""
    doc_points = min(len(case.documents) * 1.5, 4.0)
    fact_points = min(len(case.key_facts) * 0.8, 3.0)
    base = 3.0 + doc_points + fact_points          # 3–10 scale
    if case.documents and case.amount_text:
        pros, defe = min(base + 0.8, 10), max(base - 1.2, 3)
    elif not case.documents:
        pros, defe = max(base - 1.5, 3), min(base + 0.6, 10)
    else:
        pros, defe = base, base - 0.4
    if case.evidence_withheld:
        pros = max(pros - 1.8, 3)
    rounds = {s.round_no for s in speeches}
    if len(rounds) >= 3:
        pros, defe = min(pros + 0.3, 10), min(defe + 0.3, 10)
    return {
        "prosecution": {
            "evidence": round(min(pros, 10), 1),
            "reasoning": round(min(pros - 0.4, 10), 1),
            "consistency": 9.0 if len(rounds) >= 3 else 7.0,
        },
        "defense": {
            "evidence": round(min(defe, 10), 1),
            "reasoning": round(min(defe - 0.2, 10), 1),
            "consistency": 9.0 if len(rounds) >= 3 else 7.0,
        },
    }


def judge_assessment(case: ParsedCase, speeches: list[Speech],
                     matrix: list[dict], sources: list[dict]) -> dict:
    """The Judge critiques — it does not decide the case.

    Returns a preliminary assessment: a qualitative label, the
    supporting factors, the weaknesses, the missing evidence, the
    legal uncertainty, and what would change the assessment. No
    confidence percentage, no order, no verdict."""
    scores = _score(case, speeches)
    p_avg = sum(scores["prosecution"].values()) / 3
    d_avg = sum(scores["defense"].values()) / 3
    margin = round(p_avg - d_avg, 1)

    reported = [r for r in matrix if r["status"] == "Reported"]
    unsupported = [r for r in matrix if r["status"] == "Unsupported"]
    unverified = [r for r in matrix if r["status"] == "Unverified"]

    if margin >= 1.0:
        label = "Potentially supported, subject to verification"
        lean = "claimant"
    elif margin <= -1.0:
        label = "Not established on current evidence"
        lean = "respondent"
    else:
        label = "Mixed — partly supported; key points remain unverified"
        lean = "neither"

    supporting = [
        f"{r['fact']} — {r['evidence']}" for r in reported
        if r["supports"] in ("claimant", "both")]
    if not supporting:
        supporting = ["No fact in the statement is backed by supporting "
                      "material that was actually produced."]
    weaknesses = [
        f"{r['fact']} — {r['evidence']}" for r in unsupported]
    weaknesses += [
        f"{r['fact']} — asserted without supporting material"
        for r in unverified]
    if case.evidence_withheld:
        weaknesses.append(
            "Evidence the statement itself says was withheld or never "
            "produced cannot count for the party asserting it.")
    missing = missing_evidence(matrix)
    if not missing:
        missing = ["Any documents the statement mentions but does not "
                   "quote — obtain the originals before advising."]

    uncertainty = [
        "Jurisdiction and the exact contract/agreement terms were not "
        "stated in the case and must be verified.",
        "The legal sources used here are a curated starter set, not "
        "full legal research — a lawyer must check current law.",
    ]
    if not sources:
        uncertainty.append(
            "No verified legal source was retrieved for this issue type — "
            "every legal proposition in the debate is therefore labelled "
            "unsupported, not cited.")
    what_would_change = []
    for r in unsupported:
        what_would_change.append(
            f"Producing the supporting material for '{r['fact']}' "
            f"({r['evidence'].lower()}) would change the assessment.")
    if not what_would_change:
        what_would_change = [
            "Producing the original agreement and any missing receipts "
            "or records would let a lawyer assess the claim properly."]

    reasons = [
        f"{len(reported)} fact(s) are reported with supporting material; "
        f"{len(unsupported)} are unsupported and {len(unverified)} "
        "unverified on the statement as given.",
        "The assessment leans on the evidence matrix, not on how "
        "persuasively either side argued.",
    ]
    if unsupported:
        reasons.append(
            "Unsupported claims — above all the ones listed under "
            "weaknesses — hold the assessment back more than any "
            "argument in the debate.")

    return {
        "assessment": label,
        "lean": lean,
        "margin": margin,
        "scores": scores,
        "prosecution_avg": round(p_avg, 1),
        "defense_avg": round(d_avg, 1),
        "supporting_factors": supporting,
        "weaknesses": weaknesses,
        "missing_evidence": missing,
        "legal_uncertainty": uncertainty,
        "what_would_change": what_would_change,
        "unsupported_claims": [r["fact"] for r in unsupported],
        "citations": [s["citation"] for s in sources],
        "reasons": reasons,
        "judge_statement": (
            f"Preliminary assessment: {label}. Having heard both sides, "
            f"the argument rubric stands at Claimant {p_avg:.1f}/10 and "
            f"Respondent {d_avg:.1f}/10 — that is a measure of how the "
            f"arguments tracked the evidence, not a probability of "
            f"winning. {len(unsupported)} claim(s) are unsupported and "
            f"{len(unverified)} unverified on the evidence as given. "
            f"This is a preparation aid for a lawyer to review — not "
            f"legal advice, not a court judgment, and not a prediction "
            f"of any real outcome."
        ),
    }


# ---------------------------------------------------------------- case brief

LEGAL_ISSUES = {
    "tenancy": [
        "Was the deposit refundable on vacating, and on what terms?",
        "Were the claimed deductions (if any) proved, and were they "
        "reasonable compensation for actual loss?",
        "Was the property returned in the condition the lease required?",
    ],
    "contract": [
        "Was there a binding contract, and what did it require?",
        "Was there a breach, and by whom?",
        "What loss, if any, flowed from the breach — and is it proved?",
    ],
    "criminal": [
        "Is there admissible evidence of the alleged act?",
        "Does the available evidence meet the burden of proof?",
        "Are there contradictions or gaps in the account?",
    ],
}

DEFAULT_ISSUES = [
    "What exactly is each party asserting, and what must they prove?",
    "What evidence supports each assertion — and what is missing?",
    "Which verified legal sources actually apply to these facts?",
]


def build_case_brief(case: ParsedCase, matrix: list[dict],
                     sources: list[dict], assessment: dict,
                     transcript: list[dict]) -> str:
    """A lawyer-ready structured brief, built ONLY from the case
    statement, the evidence matrix, the verified sources and the
    assessment. No invented facts, amounts or citations."""
    lines = []
    lines.append("# Case Brief — Preliminary Assessment")
    lines.append("")
    lines.append("> Litigation-preparation aid, generated by Mini "
                 "Courtroom. Simulation only — **not legal advice, not a "
                 "real court judgment, and not a prediction of any real "
                 "outcome**. A qualified lawyer must review and verify "
                 "everything before acting on it.")
    lines.append("")
    lines.append("## 1. Case overview")
    lines.append("")
    lines.append(f"- **Issue type:** {case.issue}")
    lines.append(f"- **Parties:** {case.plaintiff} (claimant) vs "
                 f"{case.defendant} (respondent)")
    if case.amounts:
        lines.append(f"- **Amounts mentioned:** {', '.join(case.amounts)}")
    if case.dates:
        lines.append(f"- **Dates mentioned:** {', '.join(case.dates)}")
    lines.append(f"- **Documents mentioned:** "
                 f"{', '.join(case.documents) if case.documents else 'none'}")
    lines.append("")
    lines.append("**Case statement (as given):**")
    lines.append("")
    lines.append(f"> {case.raw}")
    lines.append("")
    lines.append("## 2. Facts")
    lines.append("")
    reported = [r for r in matrix if r["status"] == "Reported"]
    alleged = [r for r in matrix if r["status"] == "Unverified"]
    disputed = [r for r in matrix if r["status"] == "Unsupported"]
    lines.append("### Reported — supporting material mentioned in the statement")
    lines.append("")
    for r in reported or [{"fact": "None.", "evidence": "", "supports": ""}]:
        lines.append(f"- {r['fact']} ({r['evidence']})")
    lines.append("")
    lines.append("### Alleged — asserted, no supporting material stated")
    lines.append("")
    for r in alleged or [{"fact": "None.", "evidence": ""}]:
        lines.append(f"- {r['fact']}")
    lines.append("")
    lines.append("### Disputed / unsupported — supporting material said to "
                 "be missing or never produced")
    lines.append("")
    for r in disputed or [{"fact": "None.", "evidence": ""}]:
        lines.append(f"- {r['fact']} — {r['evidence']}")
    lines.append("")
    lines.append("## 3. Evidence matrix")
    lines.append("")
    lines.append("| Fact / claim | Evidence | Supports | Status |")
    lines.append("|---|---|---|---|")
    for r in matrix:
        lines.append(f"| {r['fact']} | {r['evidence']} | {r['supports']} "
                     f"| {r['status']} |")
    lines.append("")
    lines.append("## 4. Legal issues")
    lines.append("")
    for issue in LEGAL_ISSUES.get(case.issue, DEFAULT_ISSUES):
        lines.append(f"- {issue}")
    lines.append("")
    lines.append("## 5. Applicable law — verified sources only")
    lines.append("")
    if sources:
        for s in sources:
            lines.append(f"- **{s['citation']}** — {s['excerpt']}")
            lines.append(f"  Source: {s['url']}")
            lines.append(f"  Relevance: {s['applies_to']}")
    else:
        lines.append("- No verified legal source was retrieved for this "
                     "issue type. Every legal proposition in this brief "
                     "is therefore **unsupported — no verified source "
                     "retrieved**. Do not cite any statute or case from "
                     "this brief.")
    lines.append("")
    lines.append("## 6. Claimant's strongest supported arguments")
    lines.append("")
    for r in reported:
        if r["supports"] in ("claimant", "both"):
            lines.append(f"- {r['fact']} — {r['evidence']}")
    if not any(r["supports"] in ("claimant", "both")
               for r in reported):
        lines.append("- None on the current evidence.")
    lines.append("")
    lines.append("## 7. Respondent's strongest arguments")
    lines.append("")
    for r in matrix:
        if r["supports"] == "respondent":
            lines.append(f"- {r['fact']} — {r['evidence']} "
                         f"({r['status']})")
    lines.append("- The burden of proof rests on the claimant; gaps in "
                 "the claimant's evidence are themselves the "
                 "respondent's strongest point.")
    lines.append("")
    lines.append("## 8. Weaknesses and risks")
    lines.append("")
    for w in assessment["weaknesses"]:
        lines.append(f"- {w}")
    lines.append("")
    lines.append("## 9. Missing evidence")
    lines.append("")
    for m in assessment["missing_evidence"]:
        lines.append(f"- {m}")
    lines.append("")
    lines.append("## 10. Questions for the client")
    lines.append("")
    for m in assessment["missing_evidence"]:
        lines.append(f"- Can you produce the material behind this: {m}")
    lines.append("- Which state / jurisdiction governs the agreement, "
                 "and what do its exact terms say about deductions, "
                 "notice and refunds?")
    lines.append("- Is there any written communication (email, message, "
                 "letter) not mentioned in the statement?")
    lines.append("")
    lines.append("## 11. Preliminary assessment (not a verdict)")
    lines.append("")
    lines.append(f"**{assessment['assessment']}**")
    lines.append("")
    lines.append(assessment["judge_statement"])
    lines.append("")
    lines.append("**What would change this assessment:**")
    lines.append("")
    for w in assessment["what_would_change"]:
        lines.append(f"- {w}")
    lines.append("")
    lines.append("**Legal uncertainty:**")
    lines.append("")
    for u in assessment["legal_uncertainty"]:
        lines.append(f"- {u}")
    lines.append("")
    lines.append("## 12. Debate transcript (summary)")
    lines.append("")
    lines.append("Full speeches are in the hearing transcript. Opening "
                 "positions:")
    lines.append("")
    for t in transcript[:2]:
        lines.append(f"- **{t['speaker']}** ({t['role']}): "
                     f"{t['text'][:300]}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Generated by Mini Courtroom — litigation-prep "
                 "simulator. Not legal advice.")
    return "\n".join(lines)


# ---------------------------------------------------------------- hearing

MIN_ROUNDS = 2   # both sides must be heard at least this many rounds
MAX_ROUNDS = 6   # hard cap — the Judge must assess by here


def _llm_speech(llm, system: str, user: str, fallback: str,
                forbidden: list | None = None) -> tuple[str, str]:
    """One speech from the LLM when available, else the local engine.
    Returns (text, source). Never raises — a failed LLM call just means
    the local engine speaks instead. `forbidden` guards against the
    classic weak-model failure: the LLM siding with the wrong party
    (e.g. the Defense claiming to represent the claimant). A speech
    containing a forbidden phrase is discarded for the local one."""
    if llm is None:
        return fallback, "local"
    try:
        out = llm.chat(system, user)
    except Exception:
        out = None
    if out:
        low = out.lower()
        if forbidden and any(f.lower() in low for f in forbidden):
            return fallback, "local"
        return out, f"llm:{llm.provider}"
    return fallback, "local"


def _first_name(party: str) -> str:
    if party.lower().startswith("the "):
        return ""
    return party.split()[0]


def judge_check(case: ParsedCase, speeches: list[Speech],
                llm=None, min_rounds: int = MIN_ROUNDS,
                max_rounds: int = MAX_ROUNDS) -> dict:
    """After each debate round the Judge decides: enough to assess,
    or one more round?

    Deterministic rule (always applies): not enough before MIN_ROUNDS;
    enough when one side leads the rubric by >= 1.0; enough at 4+ rounds
    when both sides have been fully heard and are only repeating
    themselves; never past MAX_ROUNDS. When an LLM is available the
    Judge also asks it — the LLM can keep a close debate going, but it
    can never override the caps.
    """
    rounds_held = max((s.round_no for s in speeches), default=0)
    scores = _score(case, speeches)
    p_avg = sum(scores["prosecution"].values()) / 3
    d_avg = sum(scores["defense"].values()) / 3
    margin = round(p_avg - d_avg, 1)

    if rounds_held >= max_rounds:
        return {"after_round": rounds_held, "sufficient": True,
                "reason": f"Maximum of {max_rounds} debate rounds reached — "
                          "the assessment must be prepared now.",
                "scores": scores, "margin": margin, "decided_by": "cap"}
    if rounds_held < min_rounds:
        return {"after_round": rounds_held, "sufficient": False,
                "reason": "Both sides have not yet been fully heard.",
                "scores": scores, "margin": margin, "decided_by": "rule"}
    if abs(margin) >= 1.0:
        decision, reason = True, (
            f"One side leads the rubric by {abs(margin)} points "
            f"({max(p_avg, d_avg):.1f} vs {min(p_avg, d_avg):.1f}) — the "
            "case is clear enough to assess.")
    elif rounds_held >= 4:
        decision, reason = True, (
            f"Both sides have argued for {rounds_held} rounds and the scores "
            "are still close — further argument would only repeat the same "
            "points.")
    else:
        decision, reason = False, (
            f"Scores are close ({p_avg:.1f} vs {d_avg:.1f}) and the key "
            "facts are still disputed — another round is needed.")

    if decision and llm is not None and rounds_held < max_rounds:
        try:
            transcript = "\n".join(
                f"{s.speaker}: {s.text}" for s in speeches)
            llm_reply = llm.chat(
                "You are the Judge in a litigation-prep simulation. You "
                "have heard the debate below. Decide ONLY whether you "
                "have heard enough to prepare a preliminary assessment, "
                "or need one more round of debate. You do not decide the "
                "case.",
                f"Case: {case.raw}\n\nDebate so far:\n{transcript}\n\n"
                "Reply with exactly one line, either "
                "'SUFFICIENT: <one-line reason>' or "
                "'CONTINUE: <one-line reason>'.",
                max_tokens=120)
        except Exception:
            llm_reply = None
        if llm_reply and llm_reply.strip().upper().startswith("CONTINUE"):
            return {"after_round": rounds_held, "sufficient": False,
                    "reason": llm_reply.strip()[len("CONTINUE:"):].strip()
                    or "The Judge wants one more round.",
                    "scores": scores, "margin": margin,
                    "decided_by": "llm-judge"}
    return {"after_round": rounds_held, "sufficient": decision,
            "reason": reason, "scores": scores, "margin": margin,
            "decided_by": "rule"}


def run_hearing(statement: str, llm=None,
                max_rounds: int = MAX_ROUNDS,
                min_rounds: int = MIN_ROUNDS) -> dict:
    """Run one full hearing. One statement in, evidence matrix +
    debate transcript + Judge's critique + case brief out.

    The debate is NOT fixed-length: after every rebuttal round the Judge
    checks whether it has heard enough (see judge_check). It stops early
    on a clear case and runs longer on a close one, up to max_rounds.
    Pass an LLM client (llm.get_client()) for LLM-generated speeches,
    or None for the offline local engine.
    """
    return _run_hearing(statement, llm, min_rounds, max_rounds)


def _run_hearing(statement: str, llm=None,
                 min_rounds: int = MIN_ROUNDS,
                 max_rounds: int = MAX_ROUNDS) -> dict:
    if not statement or not statement.strip():
        raise ValueError("Please provide a problem statement / case facts.")
    case = parse_case(statement)
    # Evidence Analyst first, then Legal Research — before any lawyer
    # speaks. All three agents receive the SAME case, matrix and sources.
    matrix = build_evidence_matrix(case)
    sources = retrieve(case.issue, case.raw)
    sources_text = format_for_prompt(sources)
    matrix_text = "\n".join(
        f"- {r['fact']} | evidence: {r['evidence']} | supports: "
        f"{r['supports']} | status: {r['status']}"
        for r in matrix)
    prosecution = ProsecutionLawyer(case, matrix, sources)
    defense = DefenseLawyer(case, matrix, sources)

    speeches: list[Speech] = []

    def add(round_no, name, speaker, role, text, source):
        speeches.append(Speech(round_no, name, speaker, role, text, source))

    no_invent = ("Use ONLY the facts in the case below, the evidence "
                 "matrix, and the verified legal sources. Never invent "
                 "facts, amounts, dates, documents, clauses, statutes or "
                 "case names. Cite ONLY the verified sources given. If a "
                 "claim has no verified source, say it is unsupported. "
                 "120-180 words.")
    evidence_block = (f"\n\nEvidence matrix:\n{matrix_text}\n\n"
                      f"{sources_text}")
    p_first, d_first = _first_name(case.plaintiff), _first_name(case.defendant)
    no_p = [f"represent {p_first}", f"represent ms. {p_first}",
            f"represent mr. {p_first}"] if p_first else []
    no_d = [f"represent {d_first}", f"represent ms. {d_first}",
            f"represent mr. {d_first}"] if d_first else []
    text, src = _llm_speech(
        llm,
        "You are the Claimant's Counsel in a litigation-prep simulation. "
        f"Your client is {case.plaintiff}. The other side is "
        f"{case.defendant}. Argue for your client, from the evidence "
        f"matrix and verified sources only. {no_invent}",
        f"Case: {case.raw}{evidence_block}\n\nGive your opening statement. Begin with the "
        f"sentence 'I represent {case.plaintiff}.'",
        prosecution.opening(), forbidden=no_d)
    add(1, "Opening Statements", "Prosecution", prosecution.role, text, src)
    p_open = text
    text, src = _llm_speech(
        llm,
        "You are the Respondent's Counsel in a litigation-prep simulation. "
        f"Your client is {case.defendant}. The other side is "
        f"{case.plaintiff}. Argue for your client, from the evidence "
        f"matrix and verified sources only. {no_invent}",
        f"Case: {case.raw}{evidence_block}\n\nGive your opening statement. Begin with the "
        f"sentence 'I represent {case.defendant}.'",
        defense.opening(), forbidden=no_p)
    add(1, "Opening Statements", "Defense", defense.role, text, src)
    d_open = text

    judge_checks: list[dict] = []
    stopped_by = "judge"
    round_no = 2
    while True:
        text, src = _llm_speech(
            llm,
            "You are the Claimant's Counsel in a litigation-prep simulation. "
            f"Your client is {case.plaintiff}. Rebut the Respondent's "
            "last speech point by point, using the evidence matrix and "
            "verified sources only. " + no_invent,
            f"Case: {case.raw}{evidence_block}\n\nRespondent just said:\n{d_open}\n\n"
            f"Remember: your client is {case.plaintiff}, not "
            f"{case.defendant}. Give your rebuttal.",
            prosecution.rebuttal(d_open), forbidden=no_d)
        add(round_no, "Rebuttals", "Prosecution", prosecution.role, text, src)
        p_last = text
        text, src = _llm_speech(
            llm,
            "You are the Respondent's Counsel in a litigation-prep simulation. "
            f"Your client is {case.defendant}. Rebut the Claimant's "
            "last speech point by point, using the evidence matrix and "
            "verified sources only. " + no_invent,
            f"Case: {case.raw}{evidence_block}\n\nClaimant just said:\n{p_last}\n\n"
            f"Remember: your client is {case.defendant}, not "
            f"{case.plaintiff}. Give your rebuttal.",
            defense.rebuttal(p_last), forbidden=no_p)
        add(round_no, "Rebuttals", "Defense", defense.role, text, src)
        d_open = text

        check = judge_check(case, speeches, llm, min_rounds, max_rounds)
        judge_checks.append(check)
        if check["sufficient"]:
            stopped_by = ("max_rounds" if check["decided_by"] == "cap"
                          else "judge")
            break
        round_no += 1

    rounds_held = round_no

    closing_no = rounds_held + 1
    text, src = _llm_speech(
        llm,
        "You are the Claimant's Counsel. "
        f"Your client is {case.plaintiff}. Give your closing argument, "
        "summarising the strongest evidence-backed points for your client. "
        + no_invent.replace("120-180 words", "100-150 words"),
        f"Case: {case.raw}{evidence_block}\n\nRemember: your client is {case.plaintiff}. "
        "Give your closing argument.",
        prosecution.closing(), forbidden=no_d)
    add(closing_no, "Closing Arguments", "Prosecution",
        prosecution.role, text, src)
    text, src = _llm_speech(
        llm,
        "You are the Respondent's Counsel. "
        f"Your client is {case.defendant}. Give your closing argument, "
        "summarising the gaps and unsupported claims. "
        + no_invent.replace("120-180 words", "100-150 words"),
        f"Case: {case.raw}{evidence_block}\n\nRemember: your client is {case.defendant}. "
        "Give your closing argument.",
        defense.closing(), forbidden=no_p)
    add(closing_no, "Closing Arguments", "Defense", defense.role, text, src)

    assessment = judge_assessment(case, speeches, matrix, sources)
    drafted, judge_src = _llm_speech(
        llm,
        "You are the Judge in a litigation-prep simulation. Draft the "
        "one-paragraph critique from the assessment below, in plain "
        "language. Do not change the assessment label, the scores or "
        "the missing-evidence list. Do not give a verdict or an order, "
        "and do not state a confidence percentage.",
        f"Assessment: {assessment['assessment']}\nRubric scores: Claimant "
        f"{assessment['prosecution_avg']}/10, Respondent "
        f"{assessment['defense_avg']}/10. Missing evidence: "
        f"{'; '.join(assessment['missing_evidence'])}",
        assessment["judge_statement"])
    assessment = dict(assessment, judge_statement=drafted)
    speeches.append(Speech(closing_no + 1, "Judge's Critique", "Judge", "Judge",
                           assessment["judge_statement"], judge_src))

    transcript = [s.__dict__ for s in speeches]
    brief = build_case_brief(case, matrix, sources, assessment, transcript)

    return {
        "shared_case_statement": case.raw,
        "llm_provider": llm.provider if llm is not None else "local",
        "rounds_held": rounds_held,
        "stopped_by": stopped_by,
        "judge_checks": judge_checks,
        "case_summary": {
            "issue": case.issue,
            "plaintiff": case.plaintiff,
            "defendant": case.defendant,
            "amounts": case.amounts,
            "dates": case.dates,
            "documents": case.documents,
            "key_facts": case.key_facts,
            "evidence_withheld": case.evidence_withheld,
        },
        "evidence_matrix": matrix,
        "legal_sources": sources,
        "sources_verified": True,
        "transcript": transcript,
        "assessment": assessment,
        "brief_markdown": brief,
        "disclaimer": ("Litigation-preparation simulation for education "
                       "and hackathon demo only. Not legal advice, not a "
                       "real court judgment, and not a prediction of how "
                       "a real court would rule. A qualified lawyer must "
                       "review and verify everything."),
        "limitations": ("Legal sources are a curated starter set of "
                        "verified Indian statutes and judgments, not full "
                        "legal research. The evidence matrix is derived "
                        "only from the statement as given. No outcome is "
                        "predicted."),
    }
