import re
from typing import List, Dict, Any
from decimal import Decimal
import uuid
from backend.models.schema import NormalizedTransaction, DuplicatePaymentFinding

def get_txn_amount(t: NormalizedTransaction) -> Decimal:
    """Returns the non-zero amount of the transaction."""
    return t.debit if t.debit > 0 else t.credit

def calculate_date_delta(t1: NormalizedTransaction, t2: NormalizedTransaction) -> int:
    return abs((t1.date - t2.date).days)

def detect_duplicates(
    transactions: List[NormalizedTransaction], 
    duplicate_window_days: int = 7
) -> List[DuplicatePaymentFinding]:
    """
    Runs 5 duplicate-detection passes.
    """
    findings: List[DuplicatePaymentFinding] = []
    
    # Track flagged transaction pairs to avoid redundant reports
    # (store sorted tuple of row indices)
    flagged_pairs = set()

    # Filter out opening balance rows
    txns = [t for t in transactions if not t.is_opening_bal]
    
    # Group transactions by party
    party_txns: Dict[str, List[NormalizedTransaction]] = {}
    for t in txns:
        party_txns.setdefault(t.party, []).append(t)

    # ----------------------------------------------------
    # PASS 1: EXACT DUPLICATE
    # Same party + same amount + same contra account + date within window
    # ----------------------------------------------------
    for party, p_txns in party_txns.items():
        n = len(p_txns)
        for i in range(n):
            t1 = p_txns[i]
            t1_amt = get_txn_amount(t1)
            if t1_amt == 0:
                continue
                
            for j in range(i + 1, n):
                t2 = p_txns[j]
                t2_amt = get_txn_amount(t2)
                
                if t1_amt == t2_amt and ((t1.debit > 0 and t2.debit > 0) or (t1.credit > 0 and t2.credit > 0)):
                    # Check date window
                    delta = calculate_date_delta(t1, t2)
                    if delta <= duplicate_window_days:
                        # Check contra account if present in both
                        contra_match = True
                        if t1.contra_ledger and t2.contra_ledger:
                            contra_match = (t1.contra_ledger.strip().lower() == t2.contra_ledger.strip().lower())
                            
                        if contra_match:
                            pair = tuple(sorted((t1.row_idx, t2.row_idx)))
                            flagged_pairs.add(pair)
                            
                            findings.append(DuplicatePaymentFinding(
                                finding_id=str(uuid.uuid4()),
                                party=party,
                                pass_number=1,
                                pass_name="EXACT DUPLICATE",
                                transaction_A={
                                    "row_idx": t1.row_idx,
                                    "date": str(t1.date),
                                    "voucher_no": t1.voucher_no,
                                    "amount": float(t1_amt),
                                    "contra_ledger": t1.contra_ledger,
                                    "type": "Debit" if t1.debit > 0 else "Credit"
                                },
                                transaction_B={
                                    "row_idx": t2.row_idx,
                                    "date": str(t2.date),
                                    "voucher_no": t2.voucher_no,
                                    "amount": float(t2_amt),
                                    "contra_ledger": t2.contra_ledger,
                                    "type": "Debit" if t2.debit > 0 else "Credit"
                                },
                                delta_days=delta,
                                delta_amount=Decimal("0.00"),
                                confidence="HIGH",
                                recommendation="Immediate auditor review. Crosscheck with invoice records and bank clearance to verify if this represents a double payment."
                            ))

    # ----------------------------------------------------
    # PASS 2: SAME VOUCHER MULTI-HIT
    # Same voucher/reference number appearing more than once across entire ledger
    # ----------------------------------------------------
    # Group all transactions (even different parties) by voucher number
    vch_txns: Dict[str, List[NormalizedTransaction]] = {}
    for t in txns:
        if t.voucher_no and str(t.voucher_no).strip():
            vch_clean = str(t.voucher_no).strip().lower()
            # Ignore common placeholder/opening voucher numbers
            if vch_clean not in ("none", "ob", "opening", "null", "0", ""):
                vch_txns.setdefault(vch_clean, []).append(t)
                
    for vch, v_txns in vch_txns.items():
        if len(v_txns) > 1:
            m = len(v_txns)
            for i in range(m):
                t1 = v_txns[i]
                for j in range(i + 1, m):
                    t2 = v_txns[j]
                    pair = tuple(sorted((t1.row_idx, t2.row_idx)))
                    if pair not in flagged_pairs:
                        flagged_pairs.add(pair)
                        
                        t1_amt = get_txn_amount(t1)
                        t2_amt = get_txn_amount(t2)
                        
                        findings.append(DuplicatePaymentFinding(
                                finding_id=str(uuid.uuid4()),
                                party=t1.party,
                                pass_number=2,
                                pass_name="SAME VOUCHER MULTI-HIT",
                                transaction_A={
                                    "row_idx": t1.row_idx,
                                    "date": str(t1.date),
                                    "voucher_no": t1.voucher_no,
                                    "amount": float(t1_amt),
                                    "contra_ledger": t1.contra_ledger,
                                    "type": "Debit" if t1.debit > 0 else "Credit"
                                },
                                transaction_B={
                                    "row_idx": t2.row_idx,
                                    "date": str(t2.date),
                                    "voucher_no": t2.voucher_no,
                                    "amount": float(t2_amt),
                                    "contra_ledger": t2.contra_ledger,
                                    "type": "Debit" if t2.debit > 0 else "Credit"
                                },
                                delta_days=calculate_date_delta(t1, t2),
                                delta_amount=abs(t1_amt - t2_amt),
                                confidence="HIGH",
                                recommendation=f"Audit voucher reference '{t1.voucher_no}' used multiple times. This represents potential data entry error or unauthorized split/duplicate invoicing."
                            ))

    # ----------------------------------------------------
    # PASS 3: SAME DAY SAME AMOUNT
    # Same party + identical amount on same date
    # ----------------------------------------------------
    for party, p_txns in party_txns.items():
        n = len(p_txns)
        for i in range(n):
            t1 = p_txns[i]
            t1_amt = get_txn_amount(t1)
            if t1_amt == 0:
                continue
            for j in range(i + 1, n):
                t2 = p_txns[j]
                t2_amt = get_txn_amount(t2)
                
                if t1.date == t2.date and t1_amt == t2_amt and ((t1.debit > 0 and t2.debit > 0) or (t1.credit > 0 and t2.credit > 0)):
                    pair = tuple(sorted((t1.row_idx, t2.row_idx)))
                    if pair not in flagged_pairs:
                        flagged_pairs.add(pair)
                        findings.append(DuplicatePaymentFinding(
                            finding_id=str(uuid.uuid4()),
                            party=party,
                            pass_number=3,
                            pass_name="SAME DAY SAME AMOUNT",
                            transaction_A={
                                "row_idx": t1.row_idx,
                                "date": str(t1.date),
                                "voucher_no": t1.voucher_no,
                                "amount": float(t1_amt),
                                "contra_ledger": t1.contra_ledger,
                                "type": "Debit" if t1.debit > 0 else "Credit"
                            },
                            transaction_B={
                                "row_idx": t2.row_idx,
                                "date": str(t2.date),
                                "voucher_no": t2.voucher_no,
                                "amount": float(t2_amt),
                                "contra_ledger": t2.contra_ledger,
                                "type": "Debit" if t2.debit > 0 else "Credit"
                            },
                            delta_days=0,
                            delta_amount=Decimal("0.00"),
                            confidence="HIGH",
                            recommendation="Review same-day duplicate entries. Verify if a payment was executed twice or if there is a double posting in the ledger."
                        ))

    # ----------------------------------------------------
    # PASS 4: FUZZY AMOUNT (Near-Duplicate)
    # Same party + amount within 1% + within 3-day window
    # ----------------------------------------------------
    for party, p_txns in party_txns.items():
        n = len(p_txns)
        for i in range(n):
            t1 = p_txns[i]
            t1_amt = get_txn_amount(t1)
            if t1_amt == 0:
                continue
            for j in range(i + 1, n):
                t2 = p_txns[j]
                t2_amt = get_txn_amount(t2)
                if t2_amt == 0:
                    continue
                    
                # Must be same side (both debits or both credits)
                same_side = (t1.debit > 0 and t2.debit > 0) or (t1.credit > 0 and t2.credit > 0)
                if not same_side:
                    continue
                    
                delta = calculate_date_delta(t1, t2)
                if delta <= 3:
                    # Check 1% tolerance
                    max_amt = max(t1_amt, t2_amt)
                    diff = abs(t1_amt - t2_amt)
                    if diff <= (Decimal("0.01") * max_amt):
                        pair = tuple(sorted((t1.row_idx, t2.row_idx)))
                        if pair not in flagged_pairs:
                            flagged_pairs.add(pair)
                            findings.append(DuplicatePaymentFinding(
                                finding_id=str(uuid.uuid4()),
                                party=party,
                                pass_number=4,
                                pass_name="FUZZY AMOUNT (Near-Duplicate)",
                                transaction_A={
                                    "row_idx": t1.row_idx,
                                    "date": str(t1.date),
                                    "voucher_no": t1.voucher_no,
                                    "amount": float(t1_amt),
                                    "contra_ledger": t1.contra_ledger,
                                    "type": "Debit" if t1.debit > 0 else "Credit"
                                },
                                transaction_B={
                                    "row_idx": t2.row_idx,
                                    "date": str(t2.date),
                                    "voucher_no": t2.voucher_no,
                                    "amount": float(t2_amt),
                                    "contra_ledger": t2.contra_ledger,
                                    "type": "Debit" if t2.debit > 0 else "Credit"
                                },
                                delta_days=delta,
                                delta_amount=diff,
                                confidence="MEDIUM",
                                recommendation="Review near-duplicate payments. Check if variance is due to exchange rates, rounding, bank fees, or slight invoicing differences."
                            ))

    # ----------------------------------------------------
    # PASS 5: SUSPICIOUS ROUND NUMBERS
    # Credit/debit amount is exact multiple of 1000 with no invoice reference
    # ----------------------------------------------------
    # For Pass 5, we look at individual transactions (often credits representing payments)
    # The requirement: "Credit amount is exact multiple of 1000 with no invoice reference linkable to it"
    # Or debit if it is a payment from our side. To be safe, we look at any receipt/payment entry
    # (credit for debtor accounts, debit for creditor accounts, or simply any entry > Rs. 1000 that is round).
    # Let's check entries where amount % 1000 == 0.
    for t in txns:
        t_amt = get_txn_amount(t)
        if t_amt >= 1000 and t_amt % 1000 == 0:
            # Check references
            has_ref = (t.ref_no is not None and str(t.ref_no).strip() != "")
            has_vch = (t.voucher_no is not None and str(t.voucher_no).strip() != "")
            # Check narration for invoice numbers (e.g. inv, bill, no, # followed by digit)
            narr_lower = (t.narration or "").lower()
            has_ref_in_narr = any(term in narr_lower for term in ["inv", "bill", "invoice", "invoice#", "bill#", "ref"]) or re.search(r'\d+', narr_lower) is not None
            
            if not has_ref and not has_ref_in_narr:
                # Add finding
                findings.append(DuplicatePaymentFinding(
                    finding_id=str(uuid.uuid4()),
                    party=t.party,
                    pass_number=5,
                    pass_name="SUSPICIOUS ROUND NUMBERS",
                    transaction_A={
                        "row_idx": t.row_idx,
                        "date": str(t.date),
                        "voucher_no": t.voucher_no,
                        "amount": float(t_amt),
                        "contra_ledger": t.contra_ledger,
                        "type": "Debit" if t.debit > 0 else "Credit"
                    },
                    transaction_B={}, # Unused for single transaction flag
                    delta_days=0,
                    delta_amount=Decimal("0.00"),
                    confidence="LOW",
                    recommendation="Informational flag. Verify if this round-number transaction has an underlying invoice, work order, or contract backing it."
                ))
                
    return findings
