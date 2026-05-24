"""
GST / TDS Compliance Agent — India-Specific

Analyzes expense/debit transactions to detect potential TDS non-compliance
under standard Income Tax Act sections.

Sections covered:
  194C  — Contractor / Sub-contractor Payments
  194J  — Professional / Technical Services
  194H  — Commission / Brokerage
  194I  — Rent (split into 194I(a) Plant/Machinery, 194I(b) Land/Building)
  194A  — Interest (non-banking)
  194Q  — Purchase of Goods (Finance Act 2021)

Logic:
  1. Group all debit payments by party
  2. For each party, check if cumulative payment exceeds applicable threshold
  3. Search for TDS evidence in narrations ("tds", "tax deducted", "194C", etc.)
  4. If threshold exceeded and no TDS evidence found → flag as TDSFinding
"""
import uuid
import re
from decimal import Decimal
from typing import List, Dict, Any, Optional
from collections import defaultdict

from backend.models.schema import NormalizedTransaction, TDSFinding

# TDS Section reference data (rates and thresholds as per Finance Act 2023-24)
TDS_SECTIONS: List[Dict[str, Any]] = [
    {
        "section": "194C",
        "name": "Contractor/Sub-contractor Payments",
        "keywords": ["contractor", "sub-contractor", "sub contractor", "labour", "labor",
                     "works contract", "job work", "printing", "advertising", "transport",
                     "carriage", "freight", "catering", "housekeeping", "security"],
        "rate_individual": 1.0,
        "rate_company": 2.0,
        "threshold_single": Decimal("30000"),
        "threshold_annual": Decimal("100000"),
    },
    {
        "section": "194J",
        "name": "Professional/Technical Services",
        "keywords": ["professional", "consultant", "consultancy", "legal", "chartered accountant",
                     "ca fees", "audit fees", "technical service", "management fee",
                     "royalty", "director fee", "sitting fee", "doctor", "architect",
                     "engineer", "software", "it service", "technology service"],
        "rate_individual": 10.0,
        "rate_company": 10.0,
        "threshold_single": Decimal("30000"),
        "threshold_annual": None,
    },
    {
        "section": "194H",
        "name": "Commission/Brokerage",
        "keywords": ["commission", "brokerage", "agent fee", "dealer margin",
                     "referral fee", "sales commission"],
        "rate_individual": 5.0,
        "rate_company": 5.0,
        "threshold_single": Decimal("15000"),
        "threshold_annual": None,
    },
    {
        "section": "194I(a)",
        "name": "Rent - Plant/Machinery",
        "keywords": ["plant hire", "machinery hire", "equipment hire", "machinery rent",
                     "crane hire", "vehicle hire", "equipment rent"],
        "rate_individual": 2.0,
        "rate_company": 2.0,
        "threshold_single": None,
        "threshold_annual": Decimal("240000"),
    },
    {
        "section": "194I(b)",
        "name": "Rent - Land/Building/Furniture",
        "keywords": ["rent", "office rent", "shop rent", "godown rent", "warehouse rent",
                     "premises rent", "lease rent", "ground rent"],
        "rate_individual": 10.0,
        "rate_company": 10.0,
        "threshold_single": None,
        "threshold_annual": Decimal("240000"),
    },
    {
        "section": "194A",
        "name": "Interest (Non-Banking)",
        "keywords": ["interest", "loan interest", "od interest", "cc interest",
                     "interest on loan", "interest expense"],
        "rate_individual": 10.0,
        "rate_company": 10.0,
        "threshold_single": Decimal("5000"),
        "threshold_annual": None,
    },
    {
        "section": "194Q",
        "name": "Purchase of Goods",
        "keywords": ["purchase", "goods", "raw material", "stock", "inventory",
                     "merchandise", "consumable", "material"],
        "rate_individual": 0.1,
        "rate_company": 0.1,
        "threshold_single": None,
        "threshold_annual": Decimal("5000000"),  # Rs. 50 Lakhs
    },
]

TDS_EVIDENCE_KEYWORDS = [
    "tds", "tax deducted", "tax deduction", "tds deducted",
    "194", "withholding tax", "tds @ ", "tds @",
]


def _has_tds_evidence(transactions: List[NormalizedTransaction]) -> bool:
    """Check if any transaction in the group has TDS evidence in narration."""
    for t in transactions:
        narr = (t.narration or "").lower()
        if any(kw in narr for kw in TDS_EVIDENCE_KEYWORDS):
            return True
    return False


def _classify_party(party: str, narrations: List[Optional[str]]) -> Optional[Dict]:
    """
    Match party name and narrations against TDS section keywords.
    Returns the best matching section dict, or None.
    """
    combined_text = party.lower() + " " + " ".join(
        (n or "").lower() for n in narrations
    )
    # Score each section by keyword hits
    best_section = None
    best_score = 0
    for sec in TDS_SECTIONS:
        score = sum(1 for kw in sec["keywords"] if kw in combined_text)
        if score > best_score:
            best_score = score
            best_section = sec
    return best_section if best_score > 0 else None


def detect_tds_gaps(
    transactions: List[NormalizedTransaction],
) -> List[TDSFinding]:
    """
    Detect TDS non-compliance for debit transactions.
    Returns list of TDSFinding for parties where TDS should have been deducted
    but no TDS evidence is found.
    """
    findings: List[TDSFinding] = []

    debit_txns = [t for t in transactions if not t.is_opening_bal and t.debit > 0]
    if not debit_txns:
        return []

    # Group by party
    party_txns: Dict[str, List[NormalizedTransaction]] = defaultdict(list)
    for t in debit_txns:
        party_txns[t.party].append(t)

    for party, txns in party_txns.items():
        total_payment = sum(t.debit for t in txns)
        narrations = [t.narration for t in txns]

        # Classify the party into a TDS section
        matched_section = _classify_party(party, narrations)
        if not matched_section:
            continue

        sec = matched_section
        threshold_single = sec.get("threshold_single")
        threshold_annual = sec.get("threshold_annual")

        # Check threshold breach
        threshold_breached = False
        applicable_threshold = Decimal("0")

        # Single transaction threshold
        if threshold_single:
            for t in txns:
                if t.debit >= threshold_single:
                    threshold_breached = True
                    applicable_threshold = threshold_single
                    break

        # Annual aggregate threshold
        if not threshold_breached and threshold_annual:
            if total_payment >= threshold_annual:
                threshold_breached = True
                applicable_threshold = threshold_annual

        if not threshold_breached:
            continue

        # Check if TDS was deducted (look for TDS credit entries or TDS narration)
        tds_deducted = _has_tds_evidence(txns)
        if tds_deducted:
            continue  # TDS appears to have been handled

        # Calculate expected TDS
        # Use the higher rate (company rate) conservatively; actual rate depends on PAN availability
        rate = float(sec.get("rate_company", sec.get("rate_individual", 10.0)))
        expected_tds = total_payment * Decimal(str(rate)) / Decimal("100")

        severity = "CRITICAL" if rate >= 5.0 else "HIGH"

        findings.append(TDSFinding(
            finding_id=str(uuid.uuid4()),
            party=party,
            total_payment=total_payment,
            applicable_section=sec["section"],
            section_name=sec["name"],
            threshold=applicable_threshold,
            expected_tds_rate=rate,
            expected_tds_amount=expected_tds,
            tds_deducted=False,
            severity=severity,
            description=(
                f"No TDS evidence found for payments to '{party}' (Section {sec['section']} — "
                f"{sec['name']}). Total payments: Rs. {float(total_payment):,.2f}. "
                f"Threshold exceeded: Rs. {float(applicable_threshold):,.2f}. "
                f"Estimated TDS liability @ {rate:.1f}%: Rs. {float(expected_tds):,.2f}."
            ),
            recommendation=(
                f"Verify if TDS @{rate:.1f}% under Section {sec['section']} has been deducted "
                f"and deposited with the government. If not, late payment interest @ 1.5% p.m. "
                f"and penalty may apply. File TDS return in Form 26Q and issue Form 16A to the deductee."
            ),
        ))

    # Sort by expected TDS amount (highest first)
    findings.sort(key=lambda f: f.expected_tds_amount, reverse=True)
    return findings
