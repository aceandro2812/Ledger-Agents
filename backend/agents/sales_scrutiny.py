"""
Sales Scrutiny Agent — India-Specific Checks

Runs 7 forensic checks on sales/credit transactions:

1. CASH_SALE_CLUSTER    — Multiple sales just below Rs. 50,000 (GST mandatory invoice threshold)
                          to same/unknown party on same or consecutive days
2. EXCESSIVE_RETURNS    — Credit notes > 20% of gross sales to any single party
3. RAPID_REVERSAL       — Sale + credit note/reversal within 7 days
4. SALES_CONCENTRATION  — Single party accounts for > 60% of total revenue
5. VOUCHER_GAP          — Missing voucher numbers in sequential series
6. CASH_PARTY_SALES     — Sales to parties named "cash", "walk-in", or unidentified
7. POST_DATED_SALES     — Transaction dates after the audit as_on_date
"""
import uuid
import re
import datetime as dt
from decimal import Decimal
from typing import List, Dict, Any, Optional
from collections import defaultdict

from backend.models.schema import NormalizedTransaction, SalesScrutinyFinding

CASH_INVOICE_THRESHOLD = Decimal("50000")   # GST mandatory invoice threshold
SALES_CONC_THRESHOLD = 0.60                 # 60% from one party
EXCESSIVE_RETURN_PCT = 0.20                 # >20% return rate
REVERSAL_WINDOW_DAYS = 7                    # Reversal within 7 days of sale

CASH_PARTY_KEYWORDS = [
    "cash", "cash sales", "walk-in", "walk in", "counter sales",
    "retail customer", "unknown", "sundry", "misc customer",
]

REVERSAL_KEYWORDS = [
    "return", "reversal", "reverse", "credit note", "cr note", "cancellation",
    "cancelled", "rejected", "returned", "reversed",
]


def _is_cash_party(party: str, narration: Optional[str]) -> bool:
    name = party.lower()
    narr = (narration or "").lower()
    return any(kw in name or kw in narr for kw in CASH_PARTY_KEYWORDS)


def _is_reversal(narration: Optional[str]) -> bool:
    narr = (narration or "").lower()
    return any(kw in narr for kw in REVERSAL_KEYWORDS)


def scrutinize_sales(
    transactions: List[NormalizedTransaction],
    as_on_date: Optional[dt.date] = None,
) -> List[SalesScrutinyFinding]:
    findings: List[SalesScrutinyFinding] = []

    credit_txns = [t for t in transactions if not t.is_opening_bal and t.credit > 0]
    if not credit_txns:
        return []

    total_credits = sum(t.credit for t in credit_txns)

    # ----------------------------------------------------------------
    # Check 1: Cash Sale Clustering (just below Rs. 50,000)
    # ----------------------------------------------------------------
    # Detect multiple sales to same/cash party on same day all below threshold
    lower_bound = CASH_INVOICE_THRESHOLD * Decimal("0.90")
    near_threshold = [
        t for t in credit_txns
        if lower_bound <= t.credit < CASH_INVOICE_THRESHOLD
    ]

    party_day: Dict[str, Dict[str, List[NormalizedTransaction]]] = defaultdict(lambda: defaultdict(list))
    for t in near_threshold:
        party_day[t.party][str(t.date)].append(t)

    for party, day_map in party_day.items():
        for day, grp in day_map.items():
            if len(grp) >= 2:
                day_total = sum(t.credit for t in grp)
                findings.append(SalesScrutinyFinding(
                    finding_id=str(uuid.uuid4()),
                    check_type="CASH_SALE_CLUSTER",
                    severity="HIGH",
                    party=party,
                    amount=day_total,
                    description=(
                        f"{len(grp)} sales to '{party}' on {day} each just below "
                        f"Rs. {float(CASH_INVOICE_THRESHOLD):,.0f} (total Rs. {float(day_total):,.2f}). "
                        f"May be deliberately split to avoid mandatory GST tax invoice requirement."
                    ),
                    evidence={
                        "party": party, "date": day, "count": len(grp),
                        "amounts": [float(t.credit) for t in grp],
                        "total": float(day_total),
                    },
                    recommendation=(
                        "Confirm whether these are separate transactions or one sale split into parts. "
                        "If aggregate exceeds Rs. 50,000, a GST tax invoice must be issued under CGST Act. "
                        "Review GSTR-1 filing to verify these were reported."
                    ),
                ))

    # ----------------------------------------------------------------
    # Check 2: Excessive Credit Notes / Returns
    # ----------------------------------------------------------------
    party_sales: Dict[str, Decimal] = defaultdict(Decimal)
    party_returns: Dict[str, Decimal] = defaultdict(Decimal)

    for t in credit_txns:
        if _is_reversal(t.narration):
            party_returns[t.party] += t.credit
        else:
            party_sales[t.party] += t.credit

    for party, sales in party_sales.items():
        returns = party_returns.get(party, Decimal("0"))
        if sales > 0 and float(returns / sales) > EXCESSIVE_RETURN_PCT:
            return_pct = float(returns / sales) * 100
            findings.append(SalesScrutinyFinding(
                finding_id=str(uuid.uuid4()),
                check_type="EXCESSIVE_RETURNS",
                severity="HIGH",
                party=party,
                amount=returns,
                description=(
                    f"Credit notes/returns to '{party}' are Rs. {float(returns):,.2f} — "
                    f"{return_pct:.1f}% of gross sales of Rs. {float(sales):,.2f}. "
                    f"Threshold is {EXCESSIVE_RETURN_PCT*100:.0f}%. "
                    f"Inflated returns may indicate fictitious sales being reversed, or genuine quality issues."
                ),
                evidence={"party": party, "gross_sales": float(sales), "returns": float(returns), "return_pct": round(return_pct, 1)},
                recommendation=(
                    "Obtain debit notes from the party confirming the return. "
                    "Verify goods were actually returned (GRN / rejection note). "
                    "Check if these returns are reported in GSTR-1 and GST returns."
                ),
            ))

    # ----------------------------------------------------------------
    # Check 3: Rapid Reversal (sale + credit note within 7 days)
    # ----------------------------------------------------------------
    sale_txns = [t for t in credit_txns if not _is_reversal(t.narration)]
    rev_txns  = [t for t in credit_txns if _is_reversal(t.narration)]

    for rev in rev_txns:
        for sale in sale_txns:
            if sale.party == rev.party and abs((rev.date - sale.date).days) <= REVERSAL_WINDOW_DAYS:
                diff_pct = abs(float(rev.credit) - float(sale.credit)) / float(sale.credit) if sale.credit > 0 else 1
                if diff_pct < 0.10:  # Amounts are within 10% of each other
                    findings.append(SalesScrutinyFinding(
                        finding_id=str(uuid.uuid4()),
                        check_type="RAPID_REVERSAL",
                        severity="MEDIUM",
                        party=sale.party,
                        amount=sale.credit,
                        description=(
                            f"Sale of Rs. {float(sale.credit):,.2f} to '{sale.party}' on {sale.date} "
                            f"reversed by a credit note of Rs. {float(rev.credit):,.2f} on {rev.date} "
                            f"({abs((rev.date - sale.date).days)} day(s) later). "
                            f"Rapid reversals may indicate window dressing or circular sales."
                        ),
                        evidence={
                            "sale_row": sale.row_idx, "sale_date": str(sale.date),
                            "sale_amount": float(sale.credit),
                            "reversal_row": rev.row_idx, "reversal_date": str(rev.date),
                            "reversal_amount": float(rev.credit),
                            "days_diff": abs((rev.date - sale.date).days),
                        },
                        recommendation=(
                            "Verify the business reason for the reversal. "
                            "Check that the original sale entry and the reversal are both reported in GST returns. "
                            "If both are reversed in the same return period, it may indicate fictitious recording."
                        ),
                    ))
                    break  # Only flag once per reversal

    # ----------------------------------------------------------------
    # Check 4: Sales Concentration
    # ----------------------------------------------------------------
    party_gross: Dict[str, Decimal] = defaultdict(Decimal)
    for t in credit_txns:
        party_gross[t.party] += t.credit

    if total_credits > 0:
        for party, party_total in party_gross.items():
            conc = float(party_total / total_credits)
            if conc > SALES_CONC_THRESHOLD:
                findings.append(SalesScrutinyFinding(
                    finding_id=str(uuid.uuid4()),
                    check_type="SALES_CONCENTRATION",
                    severity="HIGH",
                    party=party,
                    amount=party_total,
                    description=(
                        f"Party '{party}' accounts for {conc*100:.1f}% of total sales "
                        f"(Rs. {float(party_total):,.2f} of Rs. {float(total_credits):,.2f}). "
                        f"Extreme concentration may indicate related-party circular transactions or limited business."
                    ),
                    evidence={"party": party, "amount": float(party_total), "pct": round(conc * 100, 1)},
                    recommendation=(
                        "Verify the party's identity, GST registration, and independent legal existence. "
                        "Review sales terms, pricing, and commercial substance of the transactions."
                    ),
                ))

    # ----------------------------------------------------------------
    # Check 5: Voucher Number Gaps
    # ----------------------------------------------------------------
    # Extract numeric voucher numbers and detect gaps in sequence
    vouchers = []
    for t in credit_txns:
        if t.voucher_no:
            nums = re.findall(r"\d+", t.voucher_no)
            if nums:
                vouchers.append(int(nums[-1]))

    if len(vouchers) >= 10:
        vouchers_sorted = sorted(set(vouchers))
        gaps = []
        for i in range(1, len(vouchers_sorted)):
            diff = vouchers_sorted[i] - vouchers_sorted[i - 1]
            if diff > 1:
                gaps.append({
                    "from": vouchers_sorted[i - 1],
                    "to": vouchers_sorted[i],
                    "missing_count": diff - 1,
                })
        if gaps:
            total_missing = sum(g["missing_count"] for g in gaps)
            findings.append(SalesScrutinyFinding(
                finding_id=str(uuid.uuid4()),
                check_type="VOUCHER_GAP",
                severity="HIGH",
                party=None,
                amount=None,
                description=(
                    f"{len(gaps)} gap(s) in voucher number sequence with {total_missing} missing voucher(s). "
                    f"Missing vouchers may indicate suppressed or deleted sales entries."
                ),
                evidence={"gaps": gaps[:10], "total_missing": total_missing},
                recommendation=(
                    "Obtain the complete voucher register and reconcile missing numbers. "
                    "Each voucher gap represents potentially suppressed sales — "
                    "a tax evasion risk under GST and Income Tax."
                ),
            ))

    # ----------------------------------------------------------------
    # Check 6: Cash Party Sales
    # ----------------------------------------------------------------
    cash_sales = [t for t in credit_txns if _is_cash_party(t.party, t.narration)]
    if cash_sales:
        total_cash_sales = sum(t.credit for t in cash_sales)
        findings.append(SalesScrutinyFinding(
            finding_id=str(uuid.uuid4()),
            check_type="CASH_PARTY_SALES",
            severity="MEDIUM",
            party=None,
            amount=total_cash_sales,
            description=(
                f"{len(cash_sales)} sales to unidentified cash parties "
                f"(Rs. {float(total_cash_sales):,.2f} total). "
                f"Under GST rules, sales to unregistered persons above Rs. 50,000 "
                f"require the party's name and address on the invoice."
            ),
            evidence={
                "count": len(cash_sales),
                "total": float(total_cash_sales),
                "parties": list({t.party for t in cash_sales}),
                "samples": [
                    {"row_idx": t.row_idx, "party": t.party, "amount": float(t.credit), "date": str(t.date)}
                    for t in cash_sales[:10]
                ],
            },
            recommendation=(
                "For all cash sales above Rs. 50,000, ensure buyer's name, address, and state are "
                "recorded on the invoice (Rule 46 of CGST Rules). "
                "High cash sale concentration increases risk of income suppression."
            ),
        ))

    # ----------------------------------------------------------------
    # Check 7: Post-Dated Sales
    # ----------------------------------------------------------------
    if as_on_date:
        post_dated = [t for t in credit_txns if t.date > as_on_date]
        if post_dated:
            total_post = sum(t.credit for t in post_dated)
            findings.append(SalesScrutinyFinding(
                finding_id=str(uuid.uuid4()),
                check_type="POST_DATED_SALES",
                severity="CRITICAL",
                party=None,
                amount=total_post,
                description=(
                    f"{len(post_dated)} sales entries are dated after the audit date "
                    f"({as_on_date}), totalling Rs. {float(total_post):,.2f}. "
                    f"These may be future-dated entries included to inflate current period revenue."
                ),
                evidence={
                    "audit_date": str(as_on_date),
                    "count": len(post_dated),
                    "total": float(total_post),
                    "samples": [
                        {"row_idx": t.row_idx, "date": str(t.date), "amount": float(t.credit)}
                        for t in post_dated[:10]
                    ],
                },
                recommendation=(
                    "Remove all post-dated entries from the current period accounts. "
                    "These entries must be recognised in the period they actually arise. "
                    "Revenue recognition before the transaction date violates Ind AS 115."
                ),
            ))

    return findings
