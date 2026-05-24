"""
Temporal Pattern Detection Agent

Detects time-based manipulation patterns common in Indian financial statements:

1. YEAR_END_LOADING — Disproportionate bookings in last 3 days of any calendar month
2. FY_END_SPIKE    — >40% of annual expense/debit volume concentrated in March
                      (last month of Indian fiscal year: April–March)
3. GAP_BURST       — A gap of >30 days with no transactions followed by ≥5 entries
                     in the next 3 days (sudden catch-up booking)
4. WEEKEND_CONC    — Unusually high proportion (>30%) of transactions on weekends
                     (Saturday / Sunday) — harder to verify same-day
"""
import uuid
import datetime as dt
from decimal import Decimal
from typing import List, Dict, Any
from collections import defaultdict, Counter

from backend.models.schema import NormalizedTransaction, TemporalPatternFinding

_WEEKEND_THRESHOLD = 0.30          # >30% on weekends = suspicious
_YEAR_END_DAY_THRESHOLD = 0.25     # >25% in last 3 days of any month = suspicious
_FY_END_MARCH_THRESHOLD = 0.40     # >40% of annual debits in March = suspicious (Indian FY)
_GAP_MIN_DAYS = 30                 # Minimum gap to detect
_BURST_MIN_TXNS = 5                # Minimum transactions in burst to flag


def detect_temporal_patterns(
    transactions: List[NormalizedTransaction],
) -> List[TemporalPatternFinding]:
    findings: List[TemporalPatternFinding] = []

    non_bal = [t for t in transactions if not t.is_opening_bal]
    if not non_bal:
        return []

    sorted_txns = sorted(non_bal, key=lambda t: t.date)
    dates = [t.date for t in sorted_txns]

    # ----------------------------------------------------------------
    # Check 1: Weekend Concentration
    # ----------------------------------------------------------------
    total = len(non_bal)
    weekend_txns = [t for t in non_bal if t.date.weekday() >= 5]
    weekend_count = len(weekend_txns)
    weekend_pct = weekend_count / total if total else 0

    if weekend_pct > _WEEKEND_THRESHOLD:
        severity = "HIGH" if weekend_pct > 0.45 else "MEDIUM"
        findings.append(TemporalPatternFinding(
            finding_id=str(uuid.uuid4()),
            pattern_type="WEEKEND_CONCENTRATION",
            severity=severity,
            description=(
                f"{weekend_count} of {total} transactions ({weekend_pct*100:.1f}%) "
                f"are booked on weekends (Saturday/Sunday). "
                f"Expected baseline is typically 2/7 ≈ 28.6%. "
                f"Elevated weekend bookings may indicate backdating or fictitious entries."
            ),
            evidence={
                "total_transactions": total,
                "weekend_count": weekend_count,
                "weekend_pct": round(weekend_pct * 100, 1),
                "sample_weekend_dates": sorted(list({str(t.date) for t in weekend_txns}))[:10],
            },
            recommendation=(
                "Review weekend-dated transactions for proper approval and supporting documents. "
                "Verify these weren't backdated from weekday entries to manipulate period-end balances."
            ),
        ))

    # ----------------------------------------------------------------
    # Check 2: Year-End Loading (last 3 days of any month)
    # ----------------------------------------------------------------
    month_total: Dict[str, int] = defaultdict(int)
    month_last3: Dict[str, int] = defaultdict(int)

    for t in non_bal:
        # Last day of this month
        if t.date.month == 12:
            last_day = dt.date(t.date.year, 12, 31)
        else:
            last_day = dt.date(t.date.year, t.date.month + 1, 1) - dt.timedelta(days=1)

        key = t.date.strftime("%Y-%m")
        month_total[key] += 1
        days_from_end = (last_day - t.date).days
        if days_from_end < 3:
            month_last3[key] += 1

    flagged_months = []
    for month_key, cnt in month_total.items():
        last3_cnt = month_last3.get(month_key, 0)
        if cnt >= 10 and (last3_cnt / cnt) > _YEAR_END_DAY_THRESHOLD:
            flagged_months.append({
                "month": month_key,
                "total": cnt,
                "last_3_days": last3_cnt,
                "pct": round((last3_cnt / cnt) * 100, 1),
            })

    if flagged_months:
        severity = "HIGH" if len(flagged_months) >= 3 else "MEDIUM"
        findings.append(TemporalPatternFinding(
            finding_id=str(uuid.uuid4()),
            pattern_type="YEAR_END_LOADING",
            severity=severity,
            description=(
                f"Unusually high transaction concentration in the last 3 days of "
                f"{len(flagged_months)} month(s): "
                + ", ".join(f"{m['month']} ({m['pct']}%)" for m in flagged_months[:5])
                + ". This is a common indicator of period-end earnings manipulation."
            ),
            evidence={"flagged_months": flagged_months[:10]},
            recommendation=(
                "Examine year-end entries for proper cut-off compliance. "
                "Verify expense invoices are dated before month-end, not backdated. "
                "Compare with prior period patterns to identify new year-end loading behavior."
            ),
        ))

    # ----------------------------------------------------------------
    # Check 3: Indian FY-End Spike (March = month 3 of Q4 / last month)
    # ----------------------------------------------------------------
    debit_by_month: Dict[int, Decimal] = defaultdict(Decimal)
    for t in non_bal:
        if t.debit > 0:
            debit_by_month[t.date.month] += t.debit

    total_debits = sum(debit_by_month.values())
    march_debits = debit_by_month.get(3, Decimal("0"))

    if total_debits > 0:
        march_pct = float(march_debits / total_debits)
        if march_pct > _FY_END_MARCH_THRESHOLD:
            findings.append(TemporalPatternFinding(
                finding_id=str(uuid.uuid4()),
                pattern_type="FY_END_SPIKE",
                severity="HIGH",
                description=(
                    f"March (Indian FY end) accounts for {march_pct*100:.1f}% of total debits "
                    f"(Rs. {float(march_debits):,.2f} of Rs. {float(total_debits):,.2f}). "
                    f"Threshold is {_FY_END_MARCH_THRESHOLD*100:.0f}%. "
                    f"Heavy March loading is a classic profit-reduction technique before year-end."
                ),
                evidence={
                    "march_debits": float(march_debits),
                    "total_debits": float(total_debits),
                    "march_pct": round(march_pct * 100, 1),
                    "monthly_breakdown": {str(m): float(v) for m, v in sorted(debit_by_month.items())},
                },
                recommendation=(
                    "Scrutinize March expenses for adequacy of supporting documentation. "
                    "Identify large provisions, write-offs, or one-time expenses booked in March. "
                    "Verify whether services/goods were actually received before 31st March."
                ),
            ))

    # ----------------------------------------------------------------
    # Check 4: Gap + Burst (dormancy followed by sudden bulk booking)
    # ----------------------------------------------------------------
    if len(sorted_txns) >= 10:
        gap_bursts = []
        i = 0
        while i < len(sorted_txns) - 1:
            gap_days = (sorted_txns[i + 1].date - sorted_txns[i].date).days
            if gap_days >= _GAP_MIN_DAYS:
                # Count how many transactions happen in the next 3 days after gap
                burst_end = sorted_txns[i + 1].date + dt.timedelta(days=3)
                burst_txns = [t for t in sorted_txns[i + 1:] if t.date <= burst_end]
                if len(burst_txns) >= _BURST_MIN_TXNS:
                    burst_amount = sum(
                        float(t.debit if t.debit > 0 else t.credit) for t in burst_txns
                    )
                    gap_bursts.append({
                        "gap_start": str(sorted_txns[i].date),
                        "gap_end": str(sorted_txns[i + 1].date),
                        "gap_days": gap_days,
                        "burst_txn_count": len(burst_txns),
                        "burst_amount": round(burst_amount, 2),
                    })
            i += 1

        if gap_bursts:
            findings.append(TemporalPatternFinding(
                finding_id=str(uuid.uuid4()),
                pattern_type="GAP_BURST",
                severity="MEDIUM",
                description=(
                    f"{len(gap_bursts)} instance(s) of prolonged inactivity (≥{_GAP_MIN_DAYS} days) "
                    f"followed by a burst of ≥{_BURST_MIN_TXNS} transactions within 3 days. "
                    f"This may indicate batch backdating or catch-up posting of old transactions."
                ),
                evidence={"gap_bursts": gap_bursts[:5]},
                recommendation=(
                    "Review the burst transactions for correct dates and supporting documents. "
                    "Confirm these were not backdated to fill gaps in sequential voucher numbers. "
                    "Check if the gap period coincides with staff absence or system downtime."
                ),
            ))

    return findings
