"""
Z-Score Statistical Outlier & Structuring Detection Agent

1. Per-party Z-Score: flags transactions > 2.5 std-dev from party mean
2. Structuring detector: flags clusters of amounts deliberately kept just below
   common approval/reporting thresholds (₹10k, ₹50k, ₹1L, ₹5L, ₹10L, ₹50L, ₹1Cr)
   — a common technique to avoid TDS, GST, or internal approval limits.
"""
import math
import uuid
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from backend.models.schema import NormalizedTransaction, StatisticalOutlierFinding

# Z-score thresholds
Z_CRITICAL  = 3.5   # CRITICAL
Z_HIGH      = 2.5   # HIGH
Z_MEDIUM    = 2.0   # MEDIUM (only flagged if party has < 10 txns and value is very high)

# Indian financial approval / TDS / GST thresholds (in Rs.)
STRUCTURING_THRESHOLDS = [
    10_000,       # Section 40A(3): cash payment limit
    30_000,       # TDS 194C/194J individual transaction threshold
    50_000,       # GST unregistered customer limit
    1_00_000,     # TDS 194C aggregate threshold
    2_40_000,     # TDS 194I (Rent) annual threshold marker
    10_00_000,    # Rs. 10 Lakhs — common internal approval limit
    50_00_000,    # Rs. 50 Lakhs — 194Q purchase threshold
    1_00_00_000,  # Rs. 1 Crore — 194N cash withdrawal threshold
]
STRUCTURING_WINDOW_BELOW = 0.05  # Within 5% below threshold = suspect


def _compute_stats(amounts: List[float]) -> Tuple[float, float]:
    """Return (mean, std_dev) for a list of floats."""
    n = len(amounts)
    if n < 2:
        return amounts[0] if n == 1 else 0.0, 0.0
    mean = sum(amounts) / n
    variance = sum((x - mean) ** 2 for x in amounts) / (n - 1)
    return mean, math.sqrt(variance)


def detect_statistical_outliers(
    transactions: List[NormalizedTransaction],
) -> List[StatisticalOutlierFinding]:
    findings: List[StatisticalOutlierFinding] = []

    non_bal = [t for t in transactions if not t.is_opening_bal]

    # ----------------------------------------------------------------
    # Pass 1: Per-party Z-Score outliers
    # Only run for parties with >= 5 transactions (std requires variance)
    # ----------------------------------------------------------------
    party_txns: Dict[str, List[NormalizedTransaction]] = defaultdict(list)
    for t in non_bal:
        party_txns[t.party].append(t)

    for party, txns in party_txns.items():
        amounts = [float(t.debit if t.debit > 0 else t.credit) for t in txns if (t.debit > 0 or t.credit > 0)]
        if len(amounts) < 5:
            continue

        mean, std = _compute_stats(amounts)
        if std < 1:   # All amounts nearly identical
            continue

        for t in txns:
            amt = float(t.debit if t.debit > 0 else t.credit)
            if amt == 0:
                continue
            z = abs(amt - mean) / std

            if z >= Z_CRITICAL:
                severity = "CRITICAL"
            elif z >= Z_HIGH:
                severity = "HIGH"
            else:
                continue  # Below threshold — not interesting enough

            findings.append(StatisticalOutlierFinding(
                finding_id=str(uuid.uuid4()),
                party=party,
                anomaly_type="STATISTICAL_OUTLIER",
                transaction={
                    "row_idx": t.row_idx,
                    "date": str(t.date),
                    "voucher_no": t.voucher_no,
                    "amount": float(amt),
                    "type": "Debit" if t.debit > 0 else "Credit",
                    "narration": t.narration or "",
                },
                party_mean=round(mean, 2),
                party_std=round(std, 2),
                z_score=round(z, 3),
                threshold_suspected=None,
                severity=severity,
                description=(
                    f"Transaction of Rs. {amt:,.2f} for party '{party}' is {z:.1f} "
                    f"standard deviations from the party mean of Rs. {mean:,.2f} "
                    f"(SD = Rs. {std:,.2f}). Statistically extreme."
                ),
                recommendation=(
                    "Verify supporting documentation (invoice, contract, approval) for this "
                    "unusually large transaction. Compare against market rates and prior periods."
                ),
            ))

    # ----------------------------------------------------------------
    # Pass 2: Structuring — amounts just below known thresholds
    # ----------------------------------------------------------------
    for threshold in STRUCTURING_THRESHOLDS:
        lower_bound = threshold * (1 - STRUCTURING_WINDOW_BELOW)

        # Collect all transactions just below this threshold
        suspect = [
            t for t in non_bal
            if lower_bound <= float(t.debit if t.debit > 0 else t.credit) < threshold
        ]

        if len(suspect) < 3:  # Need at least 3 to flag a pattern
            continue

        # Group by party to see if a single party is doing this repeatedly
        party_groups: Dict[str, List] = defaultdict(list)
        for t in suspect:
            party_groups[t.party].append(t)

        for party, grp in party_groups.items():
            if len(grp) < 3:
                continue

            total = sum(float(t.debit if t.debit > 0 else t.credit) for t in grp)
            severity = "CRITICAL" if len(grp) >= 5 else "HIGH"

            findings.append(StatisticalOutlierFinding(
                finding_id=str(uuid.uuid4()),
                party=party,
                anomaly_type="STRUCTURING",
                transaction={
                    "row_idx": grp[0].row_idx,
                    "date": str(grp[0].date),
                    "voucher_no": grp[0].voucher_no,
                    "amount": float(grp[0].debit if grp[0].debit > 0 else grp[0].credit),
                    "count": len(grp),
                    "total": total,
                },
                party_mean=0.0,
                party_std=0.0,
                z_score=0.0,
                threshold_suspected=float(threshold),
                severity=severity,
                description=(
                    f"{len(grp)} transactions for '{party}' are clustered just below "
                    f"Rs. {threshold:,.0f} (within {STRUCTURING_WINDOW_BELOW*100:.0f}%). "
                    f"Total amount: Rs. {total:,.2f}. "
                    f"Possible deliberate structuring to avoid the threshold limit."
                ),
                recommendation=(
                    f"Investigate whether these payments were intentionally kept below Rs. {threshold:,.0f} "
                    f"to avoid TDS deduction / GST requirement / internal approval. "
                    f"Aggregate total = Rs. {total:,.2f}."
                ),
            ))

    return findings
