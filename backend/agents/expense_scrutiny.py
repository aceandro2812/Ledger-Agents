"""
Expense Scrutiny Agent — India-Specific Checks

Runs 9 forensic checks on expense/debit transactions:

1. YEAR_END_LOADING       — >40% of annual expenses in March (Indian FY: April–March)
2. PERSONAL_EXPENSE       — Narration contains personal/lifestyle keywords
3. CASH_ABOVE_10K         — Cash payments >Rs.10,000 (Section 40A(3) Income Tax Act, 1961)
4. ROUND_NUMBER_EXPENSE   — Suspiciously round amounts (possible fabricated bills)
5. VENDOR_CONCENTRATION   — Single vendor receives >50% of total expense outflow
6. SPLIT_PAYMENT          — Multiple payments to same vendor on same day summing above threshold
7. PREPAID_UNSETTLED      — Advance/prepaid entries with no subsequent settlement
8. SUSPENSE_ABUSE         — Large amounts in suspense/miscellaneous accounts
9. EXPENSE_WITHOUT_GST    — B2B expenses >Rs.5,000 with no GST indicator in narration
"""
import uuid
import re
import datetime as dt
from decimal import Decimal
from typing import List, Dict, Any, Optional
from collections import defaultdict

from backend.models.schema import NormalizedTransaction, ExpenseScrutinyFinding

# ---- Keyword lists ----
PERSONAL_KEYWORDS = [
    "personal", "birthday", "gift", "party", "restaurant", "club", "membership",
    "tour", "holiday", "vacation", "family", "entertainment", "hotel stay",
    "cinema", "flight", "ticket", "grooming", "shopping", "marriage", "wedding",
    "donation", "charity", "school fee", "tuition",
]

PREPAID_KEYWORDS = ["advance", "prepaid", "pre-paid", "deposit given", "security deposit",
                    "mobilisation", "mobi advance"]
SUSPENSE_KEYWORDS = ["suspense", "misc", "miscellaneous", "other", "sundry", "to be allocated",
                     "clearing", "temp", "intermediate"]
GST_KEYWORDS = ["gst", "cgst", "sgst", "igst", "tax invoice", "igst@", "cgst@", "sgst@"]

# Thresholds
CASH_LIMIT = Decimal("10000")
GST_B2B_LIMIT = Decimal("5000")
VENDOR_CONC_THRESHOLD = 0.50
YEAR_END_THRESHOLD = 0.40
ROUND_NUMBER_DIVISORS = [1000, 5000, 10000, 50000, 100000]
SPLIT_PAYMENT_THRESHOLD = Decimal("30000")  # 194C TDS threshold


def _is_cash_payment(t: NormalizedTransaction) -> bool:
    narr = (t.narration or "").lower()
    contra = (t.contra_ledger or "").lower()
    return any(k in narr or k in contra for k in ["cash", "petty cash"]) or \
           "cash" in t.party.lower()


def _has_gst_indicator(t: NormalizedTransaction) -> bool:
    narr = (t.narration or "").lower()
    return any(kw in narr for kw in GST_KEYWORDS)


def _is_round_number(amt: Decimal) -> bool:
    for divisor in ROUND_NUMBER_DIVISORS:
        if amt % divisor == 0 and amt >= divisor:
            return True
    return False


def scrutinize_expenses(
    transactions: List[NormalizedTransaction],
) -> List[ExpenseScrutinyFinding]:
    findings: List[ExpenseScrutinyFinding] = []

    debit_txns = [t for t in transactions if not t.is_opening_bal and t.debit > 0]
    if not debit_txns:
        return []

    # ----------------------------------------------------------------
    # Check 1: Year-End Loading (March in Indian FY)
    # ----------------------------------------------------------------
    march_debits = sum(t.debit for t in debit_txns if t.date.month == 3)
    total_debits = sum(t.debit for t in debit_txns)
    if total_debits > 0 and float(march_debits / total_debits) > YEAR_END_THRESHOLD:
        march_pct = float(march_debits / total_debits) * 100
        findings.append(ExpenseScrutinyFinding(
            finding_id=str(uuid.uuid4()),
            check_type="YEAR_END_LOADING",
            severity="HIGH",
            party=None,
            amount=march_debits,
            description=(
                f"March expense loading: Rs. {float(march_debits):,.2f} out of annual "
                f"Rs. {float(total_debits):,.2f} ({march_pct:.1f}%) booked in March (Indian FY end). "
                f"Threshold is {YEAR_END_THRESHOLD*100:.0f}%."
            ),
            evidence={
                "march_debits": float(march_debits),
                "total_debits": float(total_debits),
                "march_pct": round(march_pct, 1),
            },
            recommendation=(
                "Review March expense entries for validity, proper cut-off, and supporting invoices. "
                "Identify provisions, write-offs, and one-time charges booked before March 31."
            ),
        ))

    # ----------------------------------------------------------------
    # Check 2: Personal Expense Keywords
    # ----------------------------------------------------------------
    personal_txns = [
        t for t in debit_txns
        if any(kw in (t.narration or "").lower() for kw in PERSONAL_KEYWORDS)
    ]
    if personal_txns:
        total_personal = sum(t.debit for t in personal_txns)
        severity = "CRITICAL" if total_personal > Decimal("100000") else "HIGH"
        findings.append(ExpenseScrutinyFinding(
            finding_id=str(uuid.uuid4()),
            check_type="PERSONAL_EXPENSE",
            severity=severity,
            party=None,
            amount=total_personal,
            description=(
                f"{len(personal_txns)} expense entries (Rs. {float(total_personal):,.2f} total) "
                f"contain personal/lifestyle keywords in narration. "
                f"These may be personal expenses routed through the business."
            ),
            evidence={
                "count": len(personal_txns),
                "total_amount": float(total_personal),
                "samples": [
                    {"row_idx": t.row_idx, "narration": t.narration, "amount": float(t.debit), "date": str(t.date)}
                    for t in personal_txns[:10]
                ],
            },
            recommendation=(
                "Verify each personal-keyword expense has genuine business purpose. "
                "Section 37(1) of Income Tax Act requires expenses to be wholly and exclusively "
                "for business. Disallow personal expenses before filing."
            ),
        ))

    # ----------------------------------------------------------------
    # Check 3: Cash Payments Above Rs. 10,000 (Section 40A(3))
    # ----------------------------------------------------------------
    cash_violations = [
        t for t in debit_txns
        if _is_cash_payment(t) and t.debit > CASH_LIMIT
    ]
    if cash_violations:
        total_cash = sum(t.debit for t in cash_violations)
        findings.append(ExpenseScrutinyFinding(
            finding_id=str(uuid.uuid4()),
            check_type="CASH_ABOVE_10K",
            severity="HIGH",
            party=None,
            amount=total_cash,
            description=(
                f"{len(cash_violations)} cash payment(s) exceed Rs. 10,000 each "
                f"(total Rs. {float(total_cash):,.2f}). Under Section 40A(3) of the Income Tax Act, "
                f"cash expenses above Rs. 10,000 in a single day to one person are disallowable."
            ),
            evidence={
                "count": len(cash_violations),
                "total": float(total_cash),
                "transactions": [
                    {"row_idx": t.row_idx, "date": str(t.date), "amount": float(t.debit), "narration": t.narration}
                    for t in cash_violations[:10]
                ],
            },
            recommendation=(
                "Disallow these cash expenses under Section 40A(3). "
                "Confirm whether payments were genuinely made in cash or narration is incorrect. "
                "Consider switching to banking channels to maintain deductibility."
            ),
        ))

    # ----------------------------------------------------------------
    # Check 4: Round Number Expenses
    # ----------------------------------------------------------------
    round_txns = [t for t in debit_txns if _is_round_number(t.debit)]
    if len(round_txns) >= 5:
        round_total = sum(t.debit for t in round_txns)
        round_pct = len(round_txns) / len(debit_txns) * 100
        if round_pct > 30:  # Only flag if >30% of expenses are round numbers
            findings.append(ExpenseScrutinyFinding(
                finding_id=str(uuid.uuid4()),
                check_type="ROUND_NUMBER_EXPENSE",
                severity="MEDIUM",
                party=None,
                amount=round_total,
                description=(
                    f"{len(round_txns)} ({round_pct:.1f}%) of expense entries are perfectly round "
                    f"numbers (multiples of 1,000/5,000/10,000/etc.). "
                    f"Genuine bills rarely round to exact figures. May indicate estimated/fabricated entries."
                ),
                evidence={
                    "count": len(round_txns),
                    "pct_of_total": round(round_pct, 1),
                    "total_amount": float(round_total),
                    "samples": [float(t.debit) for t in round_txns[:10]],
                },
                recommendation=(
                    "Request supporting invoices for round-number expenses above Rs. 1,000. "
                    "Verify GST invoice numbers and vendor GST registration for all B2B expenses."
                ),
            ))

    # ----------------------------------------------------------------
    # Check 5: Vendor Concentration
    # ----------------------------------------------------------------
    vendor_totals: Dict[str, Decimal] = defaultdict(Decimal)
    for t in debit_txns:
        vendor_totals[t.party] += t.debit

    if total_debits > 0:
        for vendor, vendor_total in vendor_totals.items():
            conc = float(vendor_total / total_debits)
            if conc > VENDOR_CONC_THRESHOLD:
                findings.append(ExpenseScrutinyFinding(
                    finding_id=str(uuid.uuid4()),
                    check_type="VENDOR_CONCENTRATION",
                    severity="HIGH",
                    party=vendor,
                    amount=vendor_total,
                    description=(
                        f"Vendor '{vendor}' accounts for {conc*100:.1f}% of total expense outflow "
                        f"(Rs. {float(vendor_total):,.2f} of Rs. {float(total_debits):,.2f}). "
                        f"Extreme vendor concentration is a red flag for related-party abuse or fictitious vendors."
                    ),
                    evidence={"vendor": vendor, "amount": float(vendor_total), "pct": round(conc * 100, 1)},
                    recommendation=(
                        "Verify vendor's GST registration, PAN, and arm's-length pricing. "
                        "Obtain competitive quotes to confirm fair market value. "
                        "Check if vendor is a related party under Companies Act/Income Tax definitions."
                    ),
                ))

    # ----------------------------------------------------------------
    # Check 6: Split Payments (same vendor, same day, sum > threshold)
    # ----------------------------------------------------------------
    vendor_day: Dict[str, Dict[str, List[NormalizedTransaction]]] = defaultdict(lambda: defaultdict(list))
    for t in debit_txns:
        vendor_day[t.party][str(t.date)].append(t)

    for vendor, day_map in vendor_day.items():
        for day, day_txns in day_map.items():
            if len(day_txns) >= 2:
                day_total = sum(t.debit for t in day_txns)
                if day_total > SPLIT_PAYMENT_THRESHOLD:
                    findings.append(ExpenseScrutinyFinding(
                        finding_id=str(uuid.uuid4()),
                        check_type="SPLIT_PAYMENT",
                        severity="HIGH",
                        party=vendor,
                        amount=day_total,
                        description=(
                            f"{len(day_txns)} payments to '{vendor}' on {day} totalling "
                            f"Rs. {float(day_total):,.2f}. May be split to avoid TDS threshold "
                            f"of Rs. {float(SPLIT_PAYMENT_THRESHOLD):,.0f} (Section 194C)."
                        ),
                        evidence={
                            "vendor": vendor,
                            "date": day,
                            "payment_count": len(day_txns),
                            "total": float(day_total),
                            "amounts": [float(t.debit) for t in day_txns],
                        },
                        recommendation=(
                            "Verify if these represent separate services/invoices or a single service "
                            "deliberately split. If single service, deduct TDS at applicable rate "
                            "on the aggregate amount."
                        ),
                    ))

    # ----------------------------------------------------------------
    # Check 7: Prepaid/Advance without Settlement
    # ----------------------------------------------------------------
    advance_parties = defaultdict(list)
    for t in debit_txns:
        narr_lower = (t.narration or "").lower()
        if any(kw in narr_lower for kw in PREPAID_KEYWORDS):
            advance_parties[t.party].append(t)

    # Check if any advance party also has a credit (settlement)
    credit_parties = {t.party for t in transactions if t.credit > 0 and not t.is_opening_bal}
    for party, adv_txns in advance_parties.items():
        if party not in credit_parties:
            total_adv = sum(t.debit for t in adv_txns)
            if total_adv > Decimal("10000"):
                findings.append(ExpenseScrutinyFinding(
                    finding_id=str(uuid.uuid4()),
                    check_type="PREPAID_UNSETTLED",
                    severity="MEDIUM",
                    party=party,
                    amount=total_adv,
                    description=(
                        f"Advance/prepaid payments to '{party}' totalling Rs. {float(total_adv):,.2f} "
                        f"with no corresponding credit/settlement entry in the ledger period."
                    ),
                    evidence={
                        "party": party,
                        "total_advance": float(total_adv),
                        "transactions": [
                            {"row_idx": t.row_idx, "date": str(t.date), "amount": float(t.debit)}
                            for t in adv_txns[:5]
                        ],
                    },
                    recommendation=(
                        "Follow up on the status of this advance. Obtain delivery/completion certificate. "
                        "If goods/services not received, consider reversing the expense."
                    ),
                ))

    # ----------------------------------------------------------------
    # Check 8: Suspense / Miscellaneous Account Abuse
    # ----------------------------------------------------------------
    suspense_txns = [
        t for t in debit_txns
        if any(kw in t.party.lower() for kw in SUSPENSE_KEYWORDS) or
           any(kw in (t.narration or "").lower() for kw in SUSPENSE_KEYWORDS)
    ]
    if suspense_txns:
        total_susp = sum(t.debit for t in suspense_txns)
        if total_susp > Decimal("50000"):
            findings.append(ExpenseScrutinyFinding(
                finding_id=str(uuid.uuid4()),
                check_type="SUSPENSE_ABUSE",
                severity="MEDIUM",
                party=None,
                amount=total_susp,
                description=(
                    f"{len(suspense_txns)} transactions (Rs. {float(total_susp):,.2f}) routed through "
                    f"suspense/miscellaneous accounts. These may be unclassified expenses or "
                    f"temporary parking of funds."
                ),
                evidence={
                    "count": len(suspense_txns),
                    "total": float(total_susp),
                    "samples": [
                        {"row_idx": t.row_idx, "party": t.party, "amount": float(t.debit), "date": str(t.date)}
                        for t in suspense_txns[:10]
                    ],
                },
                recommendation=(
                    "All suspense entries should be resolved before year-end. "
                    "Classify into appropriate expense heads. "
                    "Unresolved suspense balances indicate incomplete accounting."
                ),
            ))

    # ----------------------------------------------------------------
    # Check 9: Expense Without GST Indicator (B2B > Rs. 5,000)
    # ----------------------------------------------------------------
    no_gst_txns = [
        t for t in debit_txns
        if t.debit > GST_B2B_LIMIT and not _is_cash_payment(t) and not _has_gst_indicator(t)
    ]
    if len(no_gst_txns) >= 5:
        total_no_gst = sum(t.debit for t in no_gst_txns)
        findings.append(ExpenseScrutinyFinding(
            finding_id=str(uuid.uuid4()),
            check_type="EXPENSE_WITHOUT_GST",
            severity="MEDIUM",
            party=None,
            amount=total_no_gst,
            description=(
                f"{len(no_gst_txns)} B2B expense entries above Rs. {float(GST_B2B_LIMIT):,.0f} "
                f"have no GST reference in narration (total Rs. {float(total_no_gst):,.2f}). "
                f"Registered businesses must issue GST invoices; missing GST may indicate unregistered vendors."
            ),
            evidence={
                "count": len(no_gst_txns),
                "total": float(total_no_gst),
                "samples": [
                    {"row_idx": t.row_idx, "party": t.party, "amount": float(t.debit), "narration": t.narration}
                    for t in no_gst_txns[:10]
                ],
            },
            recommendation=(
                "Verify GSTIN of vendors for all non-cash B2B expenses above Rs. 5,000. "
                "If vendors are unregistered, ITC cannot be claimed. "
                "Ensure tax invoices are obtained and linked in accounting records."
            ),
        ))

    return findings
