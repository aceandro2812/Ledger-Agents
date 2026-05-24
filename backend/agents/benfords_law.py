"""
Benford's Law Analysis Agent
Applies the first-digit law to detect statistically anomalous distributions
in transaction amounts — a classic forensic accounting technique.

Expected first-digit distribution (Benford, 1938):
  d=1: 30.1%   d=2: 17.6%   d=3: 12.5%   d=4: 9.7%
  d=5: 7.9%    d=6: 6.7%    d=7: 5.8%    d=8: 5.1%   d=9: 4.6%

MAD thresholds (Nigrini 2012):
  < 0.006  → Close conformity
  0.006-0.012 → Acceptable conformity
  0.012-0.015 → Marginal acceptability
  > 0.015  → Non-conformity (investigate)
"""
import math
import uuid
from decimal import Decimal
from typing import List, Dict, Optional

from backend.models.schema import (
    NormalizedTransaction,
    BenfordsLawFinding,
    BenfordsDigitResult,
)

# Expected Benford's first-digit probabilities
BENFORD_EXPECTED: Dict[int, float] = {
    1: 30.103, 2: 17.609, 3: 12.494, 4: 9.691,
    5: 7.918,  6: 6.695,  7: 5.799,  8: 5.115,  9: 4.576,
}

_MAD_CONFORMITY = [
    (0.006, "CLOSE"),
    (0.012, "ACCEPTABLE"),
    (0.015, "MARGINAL"),
    (float("inf"), "NON_CONFORMING"),
]

_MAD_SEVERITY = {
    "CLOSE": "LOW",
    "ACCEPTABLE": "LOW",
    "MARGINAL": "MEDIUM",
    "NON_CONFORMING": "HIGH",
}


def _first_digit(amount: Decimal) -> Optional[int]:
    """Extract the first significant digit of an amount."""
    s = str(abs(amount)).replace(".", "").lstrip("0")
    return int(s[0]) if s else None


def _conformity_label(mad: float) -> str:
    for threshold, label in _MAD_CONFORMITY:
        if mad < threshold:
            return label
    return "NON_CONFORMING"


def _analyze_amounts(amounts: List[Decimal], scope: str) -> Optional[BenfordsLawFinding]:
    """Core Benford's analysis on a list of amounts."""
    # Extract valid non-zero first digits
    digits = [_first_digit(a) for a in amounts if a > Decimal("0")]
    digits = [d for d in digits if d is not None]
    n = len(digits)

    if n < 100:  # Too few data points for meaningful analysis
        return None

    # Count observed frequency
    obs_count: Dict[int, int] = {d: 0 for d in range(1, 10)}
    for d in digits:
        obs_count[d] += 1

    # Build digit results and compute MAD + chi-square
    digit_results: List[BenfordsDigitResult] = []
    mad_sum = 0.0
    chi_sq = 0.0

    for d in range(1, 10):
        expected_pct = BENFORD_EXPECTED[d]
        observed_pct = (obs_count[d] / n) * 100
        deviation = abs(observed_pct - expected_pct)
        mad_sum += deviation

        expected_count = (expected_pct / 100) * n
        chi_sq += ((obs_count[d] - expected_count) ** 2) / max(expected_count, 0.0001)

        # Z-score for individual digit significance
        p = expected_pct / 100
        z_score = (abs(observed_pct / 100 - p) - (1 / (2 * n))) / math.sqrt(p * (1 - p) / n)
        is_flagged = z_score > 1.96  # 5% significance

        digit_results.append(BenfordsDigitResult(
            digit=d,
            observed_count=obs_count[d],
            observed_pct=round(observed_pct, 2),
            expected_pct=round(expected_pct, 3),
            deviation=round(deviation, 3),
            z_score=round(max(z_score, 0), 3),
            is_flagged=is_flagged,
        ))

    mad = mad_sum / 9
    conformity = _conformity_label(mad)
    severity = _MAD_SEVERITY[conformity]

    flagged_digits = [r.digit for r in digit_results if r.is_flagged]
    description = (
        f"Benford's Law analysis on {n:,} transactions (scope: {scope}). "
        f"MAD = {mad:.4f} → {conformity}. "
        + (f"Digits {flagged_digits} show statistically significant deviation (Z > 1.96)."
           if flagged_digits else "No individual digit shows significant deviation.")
    )

    recommendation = (
        "Non-conforming distribution detected. Investigate transactions starting with "
        f"digits {flagged_digits}. Common causes: fictitious invoices with preferred amounts, "
        "rounding of fabricated figures, or systematic suppression of certain value ranges."
        if conformity in ("MARGINAL", "NON_CONFORMING")
        else "Distribution is within acceptable Benford's Law conformity range."
    )

    return BenfordsLawFinding(
        finding_id=str(uuid.uuid4()),
        scope=scope,
        total_transactions=n,
        digit_results=digit_results,
        mad_score=round(mad, 6),
        chi_square=round(chi_sq, 3),
        conformity=conformity,
        severity=severity,
        description=description,
        recommendation=recommendation,
    )


def detect_benfords_violations(
    transactions: List[NormalizedTransaction],
) -> List[BenfordsLawFinding]:
    """
    Runs Benford's Law analysis:
    1. Overall corpus (all transaction amounts)
    2. Per-party (for parties with >= 100 transactions)
    Returns a list of BenfordsLawFinding — only non-trivial findings are returned.
    """
    findings: List[BenfordsLawFinding] = []

    non_bal = [t for t in transactions if not t.is_opening_bal]

    # -- Global analysis --
    all_amounts = [t.debit for t in non_bal if t.debit > 0] + \
                  [t.credit for t in non_bal if t.credit > 0]
    global_finding = _analyze_amounts(all_amounts, "ALL_TRANSACTIONS")
    if global_finding:
        findings.append(global_finding)

    # -- Per-party analysis (only parties with >= 100 entries) --
    party_amounts: Dict[str, List[Decimal]] = {}
    for t in non_bal:
        party_amounts.setdefault(t.party, [])
        if t.debit > 0:
            party_amounts[t.party].append(t.debit)
        if t.credit > 0:
            party_amounts[t.party].append(t.credit)

    for party, amounts in party_amounts.items():
        if len(amounts) < 100:
            continue
        pf = _analyze_amounts(amounts, party)
        if pf and pf.conformity in ("MARGINAL", "NON_CONFORMING"):
            findings.append(pf)

    return findings
