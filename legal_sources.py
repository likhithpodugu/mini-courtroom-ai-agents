"""
Curated, VERIFIED Indian legal sources for Mini Courtroom.

Every entry below was verified by web search on 28 Nov 2026 before
being included. No citation, section number, case name or link in
this file was invented:

- Indian Contract Act 1872, s.73 — text verified at
  https://indiankanoon.org/doc/339747/
- Indian Contract Act 1872, s.74 — text verified at
  https://indiankanoon.org/doc/1941714/ (which also quotes
  Fateh Chand v. Balkishan Dass, AIR 1963 SC 1405)
- Transfer of Property Act 1882, ss.105 / 108 — s.105 definition and
  s.108(q) (lessee must put lessor into possession on determination
  of the lease) verified at
  https://www.legalrepublic.in/everyday-law/security-deposit-recovery/
  and s.108 text at http://theindianlaw.in/laws/IND_central_2338/108
- Kailash Nath Associates v. Delhi Development Authority,
  (2015) 4 SCC 136 — verified via the Supreme Court discussion at
  https://indiankanoon.org/doc/1941714/ and
  https://www.legalrepublic.in/everyday-law/security-deposit-recovery/
- M.S. Nagabhushan v. D.S. Nagaraja, (2025) INSC 316 — security-deposit
  refund held conditional on the tenant vacating; verified at
  https://www.legalrecovery.in/blog/landlord-not-returning-security-deposit-india

This is a curated starter set, NOT full legal research. If a case
raises an issue no entry covers, retrieval returns nothing for it
and the system must say so ("unsupported — no verified source
retrieved") instead of inventing a citation. A lawyer must verify
applicability, jurisdiction and current law before relying on any
of this.
"""
from __future__ import annotations

SOURCES = [
    {
        "id": "ica-1872-s73",
        "kind": "statute",
        "title": "Indian Contract Act, 1872 — Section 73",
        "citation": "Indian Contract Act, 1872, s. 73",
        "excerpt": ("Compensation for loss or damage caused by breach of "
                    "contract: the party who suffers is entitled to "
                    "compensation for loss that naturally arose in the usual "
                    "course of things from the breach, or which the parties "
                    "knew was likely to result from it. No compensation for "
                    "remote and indirect loss."),
        "url": "https://indiankanoon.org/doc/339747/",
        "issues": ["tenancy", "contract", "consumer", "employment",
                   "property"],
        "keywords": ["breach", "damages", "compensation", "contract",
                     "payment", "refund", "deposit", "loss"],
        "applies_to": ("Use when a party claims money for a broken "
                       "promise: the claimant must connect the claimed "
                       "loss to the breach and show it was foreseeable, "
                       "not remote."),
    },
    {
        "id": "ica-1872-s74",
        "kind": "statute",
        "title": "Indian Contract Act, 1872 — Section 74",
        "citation": "Indian Contract Act, 1872, s. 74",
        "excerpt": ("Compensation for breach where a penalty is stipulated: "
                    "where a sum is named in the contract as payable on "
                    "breach, or the contract contains a stipulation by way "
                    "of penalty, the complaining party is entitled to "
                    "reasonable compensation not exceeding the amount so "
                    "named or the penalty stipulated."),
        "url": "https://indiankanoon.org/doc/1941714/",
        "issues": ["tenancy", "contract"],
        "keywords": ["penalty", "liquidated", "forfeit", "deposit",
                     "deduction", "stipulated", "breach"],
        "applies_to": ("Use when a contract names a sum payable on breach "
                       "or a deposit/deduction is forfeited: only "
                       "reasonable compensation up to the named sum is "
                       "recoverable — the named figure is a ceiling, not "
                       "an entitlement."),
    },
    {
        "id": "tpa-1882-s105",
        "kind": "statute",
        "title": "Transfer of Property Act, 1882 — Section 105",
        "citation": "Transfer of Property Act, 1882, s. 105",
        "excerpt": ("'Lease' defined: a lease of immovable property is a "
                    "transfer of a right to enjoy such property, made for "
                    "a certain time, express or implied, or in perpetuity, "
                    "in consideration of a price paid or promised, or of "
                    "money to be rendered periodically to the transferor "
                    "by the transferee."),
        "url": "https://www.legalrepublic.in/everyday-law/security-deposit-recovery/",
        "issues": ["tenancy", "property"],
        "keywords": ["lease", "landlord", "tenant", "rent", "flat",
                     "house", "apartment", "deposit", "lessor",
                     "lessee"],
        "applies_to": ("Use to frame the landlord–tenant relationship: a "
                       "lease is a transfer of the right to enjoy the "
                       "property for a term, on the agreed terms."),
    },
    {
        "id": "tpa-1882-s108",
        "kind": "statute",
        "title": "Transfer of Property Act, 1882 — Section 108",
        "citation": "Transfer of Property Act, 1882, s. 108(m) and (q)",
        "excerpt": ("Rights and liabilities of lessor and lessee. Clause "
                    "(m): the lessee must keep, and on termination restore, "
                    "the property in as good condition as when put in "
                    "possession, subject only to reasonable wear and tear. "
                    "Clause (q): on determination of the lease the lessee "
                    "is bound to put the lessor into possession. The Act "
                    "contains no express provision on return of a security "
                    "deposit; the refund obligation is read with the "
                    "contract, and deductions are governed by ss. 73–74 "
                    "of the Indian Contract Act."),
        "url": "http://theindianlaw.in/laws/IND_central_2338/108",
        "issues": ["tenancy", "property"],
        "keywords": ["lease", "landlord", "tenant", "vacat", "possession",
                     "condition", "repair", "deposit", "refund",
                     "wear and tear"],
        "applies_to": ("Use for tenancy disputes: the tenant's duty is to "
                       "restore the property in good condition (fair wear "
                       "and tear excepted) and hand back possession; the "
                       "landlord's side of the bargain is the refund of "
                       "the deposit net of legitimate, proved deductions."),
    },
    {
        "id": "fateh-chand-1963",
        "kind": "judgment",
        "title": "Fateh Chand v. Balkishan Dass",
        "citation": "Fateh Chand v. Balkishan Dass, AIR 1963 SC 1405",
        "excerpt": ("Supreme Court on s. 74, Indian Contract Act: the "
                    "section eliminates the English distinction between "
                    "liquidated damages and penalty; in either case the "
                    "court awards only reasonable compensation, not "
                    "exceeding the sum named. A party cannot simply "
                    "forfeit a deposit — it must show the forfeiture is "
                    "reasonable compensation for loss."),
        "url": "https://indiankanoon.org/doc/1941714/",
        "issues": ["tenancy", "contract"],
        "keywords": ["forfeit", "penalty", "deposit", "liquidated",
                     "reasonable compensation"],
        "applies_to": ("Use when a deposit or sum is withheld as a "
                       "forfeiture: the withholding party must justify it "
                       "as reasonable compensation, not as a penalty."),
    },
    {
        "id": "kailash-nath-2015",
        "kind": "judgment",
        "title": "Kailash Nath Associates v. Delhi Development Authority",
        "citation": "Kailash Nath Associates v. DDA, (2015) 4 SCC 136",
        "excerpt": ("Supreme Court on s. 74: damage or loss is the sine qua "
                    "non for compensation even under s. 74 — proof of loss "
                    "is not dispensed with where loss can be proved; only "
                    "where loss is difficult or impossible to prove may "
                    "the court award the liquidated amount if it is a "
                    "genuine pre-estimate. If no loss was suffered, the "
                    "law does not provide a windfall."),
        "url": "https://www.legalrepublic.in/everyday-law/security-deposit-recovery/",
        "issues": ["tenancy", "contract"],
        "keywords": ["loss", "proof", "liquidated", "forfeit", "deposit",
                     "damages", "windfall"],
        "applies_to": ("Use when a deduction/forfeiture is claimed without "
                       "proof of loss: if the loss can be proved, it must "
                       "be proved — an unproved deduction cannot stand "
                       "on the named figure alone."),
    },
    {
        "id": "nagabhushan-2025",
        "kind": "judgment",
        "title": "M.S. Nagabhushan v. D.S. Nagaraja",
        "citation": "M.S. Nagabhushan v. D.S. Nagaraja, (2025) INSC 316",
        "excerpt": ("Supreme Court (4 March 2025): post-dated cheques issued "
                    "as a security-deposit refund were conditional on the "
                    "tenant vacating the premises. Because the tenant "
                    "continued occupying beyond the lease without paying "
                    "rent, the cheques did not constitute a legally "
                    "enforceable debt; the landlord could adjust unpaid "
                    "rent before refunding the deposit."),
        "url": "https://www.legalrecovery.in/blog/landlord-not-returning-security-deposit-india",
        "issues": ["tenancy"],
        "keywords": ["deposit", "refund", "rent", "vacat", "landlord",
                     "tenant", "arrears"],
        "applies_to": ("Use with care: a deposit refund can be conditional "
                       "on handing back possession and can be adjusted "
                       "against proved unpaid rent — but only proved "
                       "amounts, and only on the facts of the case."),
    },
]


def retrieve(issue: str, case_text: str = "", limit: int = 4) -> list[dict]:
    """Return verified sources relevant to this case.

    Match first on issue type, then on keyword overlap with the case
    text. Returns copies (callers must not mutate the module list).
    An issue with no verified source in the set returns [] — callers
    must label that "no verified source retrieved", never invent one.
    """
    low = (case_text or "").lower()
    scored = []
    for src in SOURCES:
        if issue not in src["issues"]:
            continue
        hits = sum(1 for kw in src["keywords"] if kw in low)
        scored.append((hits, src))
    scored.sort(key=lambda t: -t[0])
    return [dict(s) for _, s in scored[:limit]]


def format_for_prompt(sources: list[dict]) -> str:
    """Short source block to paste into an LLM prompt."""
    if not sources:
        return ("No verified legal source was retrieved for this case. "
                "Do NOT cite any statute or case. Say the claim is "
                "unsupported — no verified source retrieved.")
    lines = ["Verified legal sources (cite ONLY these, by citation):"]
    for s in sources:
        lines.append(f"- {s['citation']}: {s['excerpt']} "
                     f"[{s['applies_to']}]")
    lines.append("If a claim is not supported by one of these sources, "
                 "label it 'unsupported — no verified source retrieved'. "
                 "Never invent a case name, citation or section number.")
    return "\n".join(lines)
