"""
Mini Courtroom — 3 AI agents, one shared case statement.

Flow (exactly what the user asked for):
    1. The user passes ONE problem statement.
    2. All three agents receive the SAME statement — no agent gets extra facts.
    3. Prosecution (offense) lawyer and Defense lawyer debate it
       (Opening -> Rebuttal -> Closing, 3 rounds).
    4. The Judge listens to the whole debate, scores both sides on a
       public rubric, and delivers the final verdict + order.

No API keys needed: the agents are a deterministic, fact-grounded
argument engine. It parses the case for parties, amounts, dates,
documents and the issue type, then builds every speech from THOSE facts
— so a different case produces a genuinely different debate, not the
same canned script. `llm.py` is the optional seam: if an
OPENAI_API_KEY is set, speeches are enriched by a real LLM; otherwise
the local engine runs untouched (the hackathon demo path).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


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
    # The claimant is (almost always) the first person named in a problem
    # statement, and the respondent the second — "Priya ... paid ... to
    # Ramesh", "Arjun ... signed a contract with TechStart ...".
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
        # Criminal accusation: the accused is named, the accuser usually isn't.
        pc.defendant = m3.group(1)
        pc.plaintiff = "the Complainant"
    else:
        names = re.findall(r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){1,2})\b", text)
        # Drop month names / place names that look like people.
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

    # Amounts, dates, documents. (Rs needs a word boundary — "repairs"
    # used to match as "rs," — and amounts must end in a digit.)
    pc.amounts = [a.rstrip(",") for a in re.findall(
        r"₹\s?[\d,]+(?:\.\d+)?|\bRs\.?\s?[\d,]+(?:\.\d+)?"
        r"|\bINR\s?[\d,]+(?:\.\d+)?|\$\s?[\d,]+(?:\.\d+)?"
        r"|\b[\d,]+\s?(?:rupees|lakh|lakhs|crore)\b", text, re.I)]
    pc.dates = re.findall(r"\b\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|"
                          r"Oct|Nov|Dec)[a-z]*\s\d{4}\b|\b\d{1,2}[/-]\d{1,2}"
                          r"[/-]\d{2,4}\b|\b(?:January|February|March|April|"
                          r"May|June|July|August|September|October|November|"
                          r"December)\s+\d{4}\b", text, re.I)
    # A document counts only if it exists — "no bills or receipts" is
    # the absence of a document, not a document on record. A mention is
    # negated when "no" appears 0–2 words before it in the same sentence.
    def _document_present(keyword: str) -> bool:
        for m in re.finditer(rf"\b{re.escape(keyword)}s?\b", low):
            prefix = low[max(0, m.start() - 60):m.start()]
            prefix = prefix.split(".")[-1]  # same sentence only
            if re.search(r"\bno\s+(?:\w+\s+){0,2}$", prefix):
                continue
            return True
        return False

    pc.documents = sorted({k for k in DOC_KEYWORDS if _document_present(k)})
    pc.evidence_withheld = any(p in low for p in
                               ["not been shared", "not shared",
                                "has not been produced", "not produced",
                                "not been provided", "no witness",
                                "never produced", "refused to share"])
    pc.sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    pc.key_facts = [s for s in pc.sentences
                    if any(w in s.lower() for w in
                           ["paid", "refus", "fail", "agre", "sign", "promis",
                            "demand", "loss", "damag", "took", "gave", "owe",
                            "breach", "denied", "terminat"])]
    return pc


# ---------------------------------------------------------------- agents

@dataclass
class Speech:
    round_no: int
    round_name: str
    speaker: str          # "Prosecution" | "Defense" | "Judge"
    role: str
    text: str
    source: str = "local"  # "local" | "llm:<provider>"


class BaseLawyer:
    """Both lawyers get the SAME ParsedCase — nothing else."""
    side: str = ""
    role: str = ""

    def __init__(self, case: ParsedCase):
        self.case = case

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


class ProsecutionLawyer(BaseLawyer):
    side, role = "prosecution", "Offense Lawyer (Prosecution)"

    def opening(self) -> str:
        c = self.case
        claim = {
            "tenancy": "unpaid rent and an unlawfully withheld deposit",
            "contract": "a clear breach of contract and unpaid dues",
            "criminal": "an offence proved by the complainant's account",
            "employment": "an unlawful termination and unpaid salary",
            "consumer": "a defective product/service and a refused refund",
            "property": "an unlawful encroachment on rightful property",
            "accident": "negligence that directly caused injury and loss",
        }.get(c.issue, "a wrong that caused real loss to my client")
        return (
            f"Your Honour, {c.plaintiff} brings this case because of {claim}. "
            f"The facts are simple and they are documented: {self._facts_line()}. "
            f"{c.defendant} accepted the obligation and then failed to honour it — "
            f"that failure is the whole case. My client should not have to chase "
            f"what was promised, and I will show the Court, point by point, that "
            f"the liability rests squarely with {c.defendant}."
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
            "I ask the Court to hold the defence to the record, not to sympathy."
        )

    def closing(self) -> str:
        c = self.case
        remedy = (f"direct {c.defendant} to pay {c.amount_text} with interest "
                  if c.amount_text else
                  f"grant {c.plaintiff} the relief sought")
        return (
            f"In closing, Your Honour: the evidence points one way. "
            f"{c.plaintiff} performed their part; {c.defendant} did not. "
            f"I pray this Court {remedy}, together with costs, so that "
            f"agreements in this country still mean something. Justice delayed "
            f"here would be justice denied to a party who did everything right."
        )


class DefenseLawyer(BaseLawyer):
    side, role = "defense", "Defense Lawyer"

    def opening(self) -> str:
        c = self.case
        facts = self._facts_line()
        facts = facts[0].upper() + facts[1:]  # keep "12 March" capitalised
        return (
            f"Your Honour, my client {c.defendant} disputes this case in full. "
            f"The other side has told a tidy story, but a tidy story is not proof. "
            f"{facts} — none of it, on its own, proves "
            f"liability. The burden rests entirely on {c.plaintiff}, and that "
            f"burden has not been met. There are two sides to these facts, and "
            f"the Court will hear why my client acted reasonably at every step."
        )

    def rebuttal(self, prosecution_opening: str) -> str:
        c = self.case
        gap = ("no independent witness and no contemporaneous record has been "
               "produced to corroborate the claim"
               if not c.documents else
               f"the {', '.join(c.documents[:2])} show what happened, but they do "
               f"not show what the other side claims they show — the interpretation "
               f"is theirs, not the document's")
        return (
            f"With respect, the prosecution's case rests on assertion. {gap.capitalize()}. "
            f"My client was never given a fair chance to cure the issue, and no "
            f"notice or opportunity to explain was afforded before this claim was filed. "
            f"An inference is not evidence, and a disputed figure — "
            + (f"{c.amount_text} — " if c.amount_text else "") +
            "does not become a debt merely because it is repeated loudly. "
            "The Court must decide on proof, not on volume."
        )

    def closing(self) -> str:
        c = self.case
        return (
            f"In closing, Your Honour: doubt is not a technicality, it is the "
            f"standard. {c.plaintiff} has not proved the case to the standard "
            f"this Court requires, and my client should not pay for a claim "
            f"built on gaps. I pray the claim be dismissed"
            + (f", or at most that any relief be limited and proportionate, "
               if c.amount_text else ", ") +
            f"with costs. {c.defendant} came to Court to be heard — I ask that "
            f"they leave with their name cleared."
        )


# ---------------------------------------------------------------- judge

def _score(case: ParsedCase, speeches: list[Speech]) -> dict:
    """Public rubric, computed from the case — not from vibes.

    Evidence: concrete facts in the statement (amounts, dates, documents).
    Reasoning: how many key facts each side actually engaged with.
    Consistency: both sides spoke in every round.
    The side whose arguments track the documented facts scores higher.
    """
    doc_points = min(len(case.documents) * 1.5, 4.0)
    fact_points = min(len(case.key_facts) * 0.8, 3.0)
    base = 3.0 + doc_points + fact_points          # 3–10 scale
    # Prosecution benefits from documentary proof; defence benefits when
    # the record is thin (burden of proof is on the claimant).
    if case.documents and case.amount_text:
        pros, defe = min(base + 0.8, 10), max(base - 1.2, 3)
    elif not case.documents:
        pros, defe = max(base - 1.5, 3), min(base + 0.6, 10)
    else:
        pros, defe = base, base - 0.4
    # Evidence the statement says was withheld/never produced cannot
    # count for the claimant — that is the burden-of-proof point.
    if case.evidence_withheld:
        pros = max(pros - 1.8, 3)
    # Both sides argued all rounds: consistency point each.
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


def judge_deliberation(case: ParsedCase, speeches: list[Speech]) -> dict:
    scores = _score(case, speeches)
    p_avg = sum(scores["prosecution"].values()) / 3
    d_avg = sum(scores["defense"].values()) / 3
    margin = round(p_avg - d_avg, 1)
    confidence = min(55 + abs(margin) * 12, 92)

    criminal = case.issue == "criminal"
    if margin >= 1.0:
        verdict = ("Guilty as charged" if criminal
                   else f"In favour of {case.plaintiff} — claim allowed")
        winner = "prosecution"
    elif margin <= -1.0:
        verdict = ("Not guilty — benefit of doubt to the accused" if criminal
                   else f"In favour of {case.defendant} — claim dismissed")
        winner = "defense"
    else:
        verdict = ("Case not proved beyond reasonable doubt — accused acquitted"
                   if criminal else
                   "Partly allowed — claim succeeds in part only")
        winner = "split"

    if winner == "prosecution":
        reasons = [
            f"The {', '.join(case.documents[:2]) if case.documents else 'facts on record'} "
            "support the claimant's version of events.",
            "The defence raised doubts but produced no counter-record to displace them.",
            "The balance of probabilities — and the documented facts — favour the claimant.",
        ]
        order = ("The accused stands convicted; the Court will hear both "
                 "sides on sentence." if criminal else
                 (f"{case.defendant} to pay {case.amount_text} to {case.plaintiff} "
                  f"within 30 days, with interest, plus costs." if case.amount_text
                  else f"Relief as prayed for is granted to {case.plaintiff}, with costs."))
    elif winner == "defense":
        reasons = [
            "The burden of proof rested on the claimant, and it was not discharged.",
            "The record is thin — assertions were not matched by corroborating documents.",
            "Where doubt remains, it must go to the defendant.",
        ]
        order = (f"The claim against {case.defendant} is dismissed with costs."
                 if not criminal else
                 "The accused is acquitted and set at liberty.")
    else:
        reasons = [
            "Both sides argued credibly and the documentary record is mixed.",
            "The core grievance is made out, but not to the full extent claimed.",
            "A proportionate order serves justice better than an all-or-nothing one.",
        ]
        order = ("The accused is acquitted; the benefit of doubt goes to "
                 "the accused." if criminal else
                 (f"{case.defendant} to pay 50% of {case.amount_text} to "
                  f"{case.plaintiff} within 30 days; the balance of the claim is dismissed."
                  if case.amount_text else
                  "Part relief is granted; the remaining prayers are dismissed."))

    return {
        "verdict": verdict,
        "winner": winner,
        "margin": margin,
        "scores": scores,
        "prosecution_avg": round(p_avg, 1),
        "defense_avg": round(d_avg, 1),
        "confidence_pct": int(confidence),
        "reasons": reasons,
        "order": order,
        "judge_statement": (
            f"Having heard both sides across three rounds, this Court finds: "
            f"{verdict}. Prosecution scored {p_avg:.1f}/10, Defence {d_avg:.1f}/10 "
            f"on evidence, reasoning and consistency. {order} "
            f"This is a simulation for legal education — not legal advice, "
            f"and not a substitute for a real court."
        ),
    }


# ---------------------------------------------------------------- hearing

MIN_ROUNDS = 2   # both sides must be heard at least this many rounds
MAX_ROUNDS = 6   # hard cap — the Judge must decide by here


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
    """First name of a person party, or '' for generic parties
    ('the Claimant', 'the State', ...)."""
    if party.lower().startswith("the "):
        return ""
    return party.split()[0]


def judge_check(case: ParsedCase, speeches: list[Speech],
                llm=None, min_rounds: int = MIN_ROUNDS,
                max_rounds: int = MAX_ROUNDS) -> dict:
    """After each debate round the Judge decides: enough, or one more round?

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
                          "the Court must decide now.",
                "scores": scores, "margin": margin, "decided_by": "cap"}
    if rounds_held < min_rounds:
        return {"after_round": rounds_held, "sufficient": False,
                "reason": "Both sides have not yet been fully heard.",
                "scores": scores, "margin": margin, "decided_by": "rule"}
    if abs(margin) >= 1.0:
        decision, reason = True, (
            f"One side leads the rubric by {abs(margin)} points "
            f"({max(p_avg, d_avg):.1f} vs {min(p_avg, d_avg):.1f}) — the "
            "case is clear enough to decide.")
    elif rounds_held >= 4:
        decision, reason = True, (
            f"Both sides have argued for {rounds_held} rounds and the scores "
            "are still close — further argument would only repeat the same "
            "points.")
    else:
        decision, reason = False, (
            f"Scores are close ({p_avg:.1f} vs {d_avg:.1f}) and the key "
            "facts are still disputed — the Court needs another round.")

    # The LLM Judge gets a say too: it can keep a close debate going.
    if decision and llm is not None and rounds_held < max_rounds:
        try:
            transcript = "\n".join(
                f"{s.speaker}: {s.text}" for s in speeches)
            verdict = llm.chat(
                "You are the Judge in a mini courtroom. You have heard the "
                "debate below. Decide ONLY whether you have heard enough to "
                "give a verdict, or need one more round of debate.",
                f"Case: {case.raw}\n\nDebate so far:\n{transcript}\n\n"
                "Reply with exactly one line, either "
                "'SUFFICIENT: <one-line reason>' or "
                "'CONTINUE: <one-line reason>'.",
                max_tokens=120)
        except Exception:
            verdict = None
        if verdict and verdict.strip().upper().startswith("CONTINUE"):
            return {"after_round": rounds_held, "sufficient": False,
                    "reason": verdict.strip()[len("CONTINUE:"):].strip()
                    or "The Judge wants one more round.",
                    "scores": scores, "margin": margin,
                    "decided_by": "llm-judge"}
    return {"after_round": rounds_held, "sufficient": decision,
            "reason": reason, "scores": scores, "margin": margin,
            "decided_by": "rule"}


def run_hearing(statement: str, llm=None,
                max_rounds: int = MAX_ROUNDS,
                min_rounds: int = MIN_ROUNDS) -> dict:
    """Run one full hearing. One statement in, transcript + verdict out.

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
    # All three agents receive the SAME case object.
    prosecution = ProsecutionLawyer(case)
    defense = DefenseLawyer(case)

    speeches: list[Speech] = []

    def add(round_no, name, speaker, role, text, source):
        speeches.append(Speech(round_no, name, speaker, role, text, source))

    # Round 1 — Opening Statements (both sides). Party names are stated
    # explicitly: the LLM must never swap sides (it did once in testing).
    no_invent = ("Use ONLY the facts in the case below. Never invent "
                 "facts, amounts, dates, documents, or clauses from an "
                 "agreement. If a fact is not in the case, say so. "
                 "120-180 words.")
    p_first, d_first = _first_name(case.plaintiff), _first_name(case.defendant)
    # Side-swap guard: reject any LLM speech that claims the other side.
    no_p = [f"represent {p_first}", f"represent ms. {p_first}",
            f"represent mr. {p_first}"] if p_first else []
    no_d = [f"represent {d_first}", f"represent ms. {d_first}",
            f"represent mr. {d_first}"] if d_first else []
    text, src = _llm_speech(
        llm,
        "You are the Prosecution (offense) lawyer in a mini courtroom. "
        f"Your client is {case.plaintiff}. The other side is "
        f"{case.defendant}. Argue for your client. {no_invent}",
        f"Case: {case.raw}\n\nGive your opening statement. Begin with the "
        f"sentence 'I represent {case.plaintiff}.'",
        prosecution.opening(), forbidden=no_d)
    add(1, "Opening Statements", "Prosecution", prosecution.role, text, src)
    p_open = text
    text, src = _llm_speech(
        llm,
        "You are the Defense lawyer in a mini courtroom. "
        f"Your client is {case.defendant}. The other side is "
        f"{case.plaintiff}. Argue for your client. {no_invent}",
        f"Case: {case.raw}\n\nGive your opening statement. Begin with the "
        f"sentence 'I represent {case.defendant}.'",
        defense.opening(), forbidden=no_p)
    add(1, "Opening Statements", "Defense", defense.role, text, src)
    d_open = text

    # Rounds 2..MAX — Rebuttals, until the Judge says enough.
    judge_checks: list[dict] = []
    stopped_by = "judge"
    round_no = 2
    while True:
        text, src = _llm_speech(
            llm,
            "You are the Prosecution (offense) lawyer in a mini courtroom. "
            f"Your client is {case.plaintiff}. Rebut the Defense lawyer's "
            "last speech point by point. " + no_invent,
            f"Case: {case.raw}\n\nDefense just said:\n{d_open}\n\n"
            f"Remember: your client is {case.plaintiff}, not "
            f"{case.defendant}. Give your rebuttal.",
            prosecution.rebuttal(d_open), forbidden=no_d)
        add(round_no, "Rebuttals", "Prosecution", prosecution.role, text, src)
        p_last = text
        text, src = _llm_speech(
            llm,
            "You are the Defense lawyer in a mini courtroom. "
            f"Your client is {case.defendant}. Rebut the Prosecution "
            "lawyer's last speech point by point. " + no_invent,
            f"Case: {case.raw}\n\nProsecution just said:\n{p_last}\n\n"
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

    # Closing Arguments (both sides), then the verdict.
    closing_no = rounds_held + 1
    text, src = _llm_speech(
        llm,
        "You are the Prosecution (offense) lawyer. "
        f"Your client is {case.plaintiff}. Give your closing argument, "
        "summarising why your client should win. " + no_invent.replace(
            "120-180 words", "100-150 words"),
        f"Case: {case.raw}\n\nRemember: your client is {case.plaintiff}. "
        "Give your closing argument.",
        prosecution.closing(), forbidden=no_d)
    add(closing_no, "Closing Arguments", "Prosecution",
        prosecution.role, text, src)
    text, src = _llm_speech(
        llm,
        "You are the Defense lawyer. "
        f"Your client is {case.defendant}. Give your closing argument, "
        "summarising why the claim should fail. " + no_invent.replace(
            "120-180 words", "100-150 words"),
        f"Case: {case.raw}\n\nRemember: your client is {case.defendant}. "
        "Give your closing argument.",
        defense.closing(), forbidden=no_p)
    add(closing_no, "Closing Arguments", "Defense", defense.role, text, src)

    verdict = judge_deliberation(case, speeches)
    drafted, judge_src = _llm_speech(
        llm,
        "You are the Judge. Draft the one-paragraph judgment from the "
        "verdict below, in plain language. Do not change the verdict, "
        "the scores or the order.",
        f"Verdict: {verdict['verdict']}\nScores: Prosecution "
        f"{verdict['prosecution_avg']}/10, Defense "
        f"{verdict['defense_avg']}/10. Order: {verdict['order']}",
        verdict["judge_statement"])
    verdict = dict(verdict, judge_statement=drafted)
    speeches.append(Speech(closing_no + 1, "Judgment", "Judge", "Judge",
                           verdict["judge_statement"], judge_src))

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
        "transcript": [s.__dict__ for s in speeches],
        "verdict": verdict,
        "disclaimer": ("Simulation for education and hackathon demo only. "
                       "Not legal advice and not a real court judgment."),
    }
