"""
Bank Reconciliation Agent

Matches GL transactions against bank statement transactions:
- Attempts exact amount + date ± window match
- Returns three categories:
  • MATCHED    — amount matches within date window
  • GL_ONLY    — in books but not in bank (possible fictitious entry)
  • BANK_ONLY  — in bank but not in books (unrecorded receipt/payment)
"""
from decimal import Decimal
from typing import List, Optional, Tuple
from collections import defaultdict
import os

from backend.models.schema import (
    NormalizedTransaction,
    BankTransaction,
    BankReconciliationItem,
    BankReconciliationSummary,
)
from backend.utils.bank_parser import parse_bank_statement

DATE_WINDOW_DAYS = 3   # Match if dates are within 3 calendar days
AMOUNT_TOLERANCE = Decimal("1.00")  # Match if amounts differ by at most Rs. 1


def _amounts_match(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= AMOUNT_TOLERANCE


def _dates_match(d1, d2, window: int = DATE_WINDOW_DAYS) -> bool:
    return abs((d1 - d2).days) <= window


def reconcile_with_bank(
    gl_transactions: List[NormalizedTransaction],
    bank_file_path: str,
) -> Optional[BankReconciliationSummary]:
    """
    Parse the bank statement and reconcile against GL transactions.
    Returns None if the bank file cannot be parsed or has no entries.
    """
    try:
        bank_name, bank_txns = parse_bank_statement(bank_file_path)
    except Exception as e:
        print(f"[BankReconciliation] Failed to parse bank file: {e}")
        return None

    if not bank_txns:
        return None

    # Filter GL to only debit/credit cash/bank movements (exclude opening balances)
    gl_entries = [t for t in gl_transactions if not t.is_opening_bal and (t.debit > 0 or t.credit > 0)]

    # Build matching sets
    matched_gl_idxs = set()
    matched_bank_idxs = set()
    items: List[BankReconciliationItem] = []

    # For each GL entry, try to find a matching bank entry
    for gi, gl in enumerate(gl_entries):
        gl_amt = gl.debit if gl.debit > 0 else gl.credit

        for bi, bk in enumerate(bank_txns):
            if bi in matched_bank_idxs:
                continue
            bk_amt = bk.debit if bk.debit > 0 else bk.credit

            if _amounts_match(gl_amt, bk_amt) and _dates_match(gl.date, bk.date):
                # Verify GL Debit (receipt) matches Bank Credit (deposit)
                # and GL Credit (payment) matches Bank Debit (withdrawal)
                is_gl_dr = gl.debit > 0
                is_bk_cr = bk.credit > 0
                if is_gl_dr != is_bk_cr:
                    continue

                matched_gl_idxs.add(gi)
                matched_bank_idxs.add(bi)

                items.append(BankReconciliationItem(
                    item_type="MATCHED",
                    gl_row_idx=gl.row_idx,
                    bank_row_idx=bk.row_idx,
                    amount=gl_amt,
                    date=gl.date,
                    gl_narration=gl.narration,
                    bank_narration=bk.narration,
                    day_diff=abs((gl.date - bk.date).days),
                    category=bk.category or "Uncategorized",
                    is_debit=bk.debit > 0,
                ))
                break

    # GL_ONLY entries (in books but not in bank)
    from backend.utils.bank_parser import categorize_narration
    gl_only_amount = Decimal("0.00")
    for gi, gl in enumerate(gl_entries):
        if gi not in matched_gl_idxs:
            amt = gl.debit if gl.debit > 0 else gl.credit
            gl_only_amount += amt
            items.append(BankReconciliationItem(
                item_type="GL_ONLY",
                gl_row_idx=gl.row_idx,
                bank_row_idx=None,
                amount=amt,
                date=gl.date,
                gl_narration=gl.narration,
                bank_narration=None,
                day_diff=0,
                category=categorize_narration(gl.narration, gl.debit > 0),
                is_debit=gl.debit > 0,
            ))

    # BANK_ONLY entries (in bank but not in books)
    bank_only_amount = Decimal("0.00")
    for bi, bk in enumerate(bank_txns):
        if bi not in matched_bank_idxs:
            amt = bk.debit if bk.debit > 0 else bk.credit
            bank_only_amount += amt
            items.append(BankReconciliationItem(
                item_type="BANK_ONLY",
                gl_row_idx=None,
                bank_row_idx=bk.row_idx,
                amount=amt,
                date=bk.date,
                gl_narration=None,
                bank_narration=bk.narration,
                day_diff=0,
                category=bk.category or "Uncategorized",
                is_debit=bk.debit > 0,
            ))

    gl_only_count   = sum(1 for it in items if it.item_type == "GL_ONLY")
    bank_only_count = sum(1 for it in items if it.item_type == "BANK_ONLY")
    matched_count   = sum(1 for it in items if it.item_type == "MATCHED")
    total = len(gl_entries) + len(bank_txns)
    match_rate = (matched_count * 2 / total * 100) if total > 0 else 0.0

    return BankReconciliationSummary(
        bank_file=os.path.basename(bank_file_path),
        bank_name=bank_name,
        total_gl_entries=len(gl_entries),
        total_bank_entries=len(bank_txns),
        matched_count=matched_count,
        gl_only_count=gl_only_count,
        bank_only_count=bank_only_count,
        gl_only_amount=gl_only_amount,
        bank_only_amount=bank_only_amount,
        match_rate_pct=round(match_rate, 1),
        items=items,
    )
