import re
from typing import List, Dict, Any, Optional
from decimal import Decimal
import uuid
import datetime as dt
from backend.models.schema import NormalizedTransaction, AnomalyFinding
from backend.utils.holidays import HolidayChecker

def is_cash_bank_account(name: Optional[str]) -> bool:
    """Helper to check if a ledger name looks like a Cash or Bank account."""
    if not name:
        return False
    name_lower = name.lower()
    return any(kw in name_lower for kw in ["bank", "hdfc", "sbi", "icici", "cash", "petty", "chq", "cheque"])

def detect_anomalies(
    transactions: List[NormalizedTransaction],
    custom_holidays: List[str] = None
) -> List[AnomalyFinding]:
    """
    Scans normalized transactions for 10 forensic anomaly patterns.
    """
    findings: List[AnomalyFinding] = []
    holiday_checker = HolidayChecker(custom_holidays)

    # Group transactions by party
    party_txns: Dict[str, List[NormalizedTransaction]] = {}
    for txn in transactions:
        party_txns.setdefault(txn.party, []).append(txn)

    # Overall user transaction counts (for User Anomaly check)
    user_counts_per_party: Dict[str, Dict[str, int]] = {}
    
    # ----------------------------------------------------
    # Scans per party
    # ----------------------------------------------------
    for party, txns in party_txns.items():
        sorted_txns = sorted(txns, key=lambda x: (x.date, x.row_idx))
        n = len(sorted_txns)
        
        # Calculate totals for creditor vs debtor check
        total_debits = sum(t.debit for t in sorted_txns if not t.is_opening_bal)
        total_credits = sum(t.credit for t in sorted_txns if not t.is_opening_bal)
        
        is_creditor = total_credits > total_debits
        
        # Track running balance for Excess Payment checks
        running_bal = Decimal("0.00")
        
        for idx, t in enumerate(sorted_txns):
            # Accumulate running balance
            if t.is_opening_bal:
                if t.debit > 0:
                    running_bal = t.debit
                elif t.credit > 0:
                    running_bal = -t.credit
                continue
                
            prev_bal = running_bal
            running_bal += (t.debit - t.credit)

            # ------------------------------------------------
            # ANOMALY 1: GHOST PAYMENT
            # Credit entry with no corresponding debit/invoice in same party ledger
            # ------------------------------------------------
            if not is_creditor and t.credit > 0 and total_debits == 0:
                findings.append(AnomalyFinding(
                    finding_id=str(uuid.uuid4()),
                    party=party,
                    anomaly_type="GHOST PAYMENT",
                    severity="CRITICAL",
                    description=f"Credit/Payment entry of Rs. {t.credit} found, but there are no Debit (Invoice) entries in this party's ledger.",
                    evidence={"row_idx": t.row_idx, "date": str(t.date), "amount": float(t.credit), "voucher": t.voucher_no},
                    recommendation="Investigate if this ledger represents a fictitious vendor or if sales invoices were recorded off-books."
                ))
            elif is_creditor and t.debit > 0 and total_credits == 0:
                findings.append(AnomalyFinding(
                    finding_id=str(uuid.uuid4()),
                    party=party,
                    anomaly_type="GHOST PAYMENT",
                    severity="CRITICAL",
                    description=f"Debit/Payment entry of Rs. {t.debit} found, but there are no Credit (Invoice) entries in this vendor's ledger.",
                    evidence={"row_idx": t.row_idx, "date": str(t.date), "amount": float(t.debit), "voucher": t.voucher_no},
                    recommendation="Investigate if this represents an unauthorized cash withdrawal or advance payment without receipt of goods."
                ))

            # ------------------------------------------------
            # ANOMALY 2: HOLIDAY PAYMENT
            # Payment made on a Sunday or Indian public holiday
            # ------------------------------------------------
            # Payments are Credits for Debtors, Debits for Creditors
            is_payment = (t.credit > 0 and not is_creditor) or (t.debit > 0 and is_creditor)
            if is_payment and holiday_checker.is_holiday_or_sunday(t.date):
                reason = holiday_checker.get_holiday_reason(t.date)
                findings.append(AnomalyFinding(
                    finding_id=str(uuid.uuid4()),
                    party=party,
                    anomaly_type="HOLIDAY PAYMENT",
                    severity="MEDIUM",
                    description=f"Transaction occurred on a holiday: {reason} ({t.date}).",
                    evidence={"row_idx": t.row_idx, "date": str(t.date), "amount": float(t.credit if t.credit > 0 else t.debit), "holiday_reason": reason},
                    recommendation="Verify bank statement clearance dates to check if this payment was backdated or posted during non-operational hours."
                ))

            # ------------------------------------------------
            # ANOMALY 3: LATE NIGHT ENTRY
            # Entry with timestamp outside 9am-7pm (if timestamp exists)
            # ------------------------------------------------
            # Check if there is an hour timestamp in narration or comments
            time_match = re.search(r'\b(2[0-3]|[01]?[0-9]):([0-5][0-9])\b', t.narration or "")
            if time_match:
                hour = int(time_match.group(1))
                if hour < 9 or hour > 19:
                    findings.append(AnomalyFinding(
                        finding_id=str(uuid.uuid4()),
                        party=party,
                        anomaly_type="LATE NIGHT ENTRY",
                        severity="MEDIUM",
                        description=f"Transaction posted at late night: {time_match.group(0)}.",
                        evidence={"row_idx": t.row_idx, "date": str(t.date), "time": time_match.group(0), "user": t.username},
                        recommendation="Review system audit trails to ensure the posting user had valid overtime clearance or if an automated batch job was run."
                    ))

            # ------------------------------------------------
            # ANOMALY 7: EXCESS PAYMENT
            # Payment exceeds outstanding balance (results in negative balance)
            # ------------------------------------------------
            # If debtor has negative balance (Cr) or creditor has negative payable (Dr)
            if not is_creditor and t.credit > 0 and prev_bal > 0 and running_bal < 0:
                findings.append(AnomalyFinding(
                    finding_id=str(uuid.uuid4()),
                    party=party,
                    anomaly_type="EXCESS PAYMENT",
                    severity="HIGH",
                    description=f"Payment of Rs. {t.credit} exceeded the outstanding balance of Rs. {prev_bal}, creating an overpayment of Rs. {abs(running_bal)}.",
                    evidence={"row_idx": t.row_idx, "date": str(t.date), "payment_amount": float(t.credit), "outstanding_before": float(prev_bal), "excess": float(abs(running_bal))},
                    recommendation="Verify whether this excess payment was adjusted against a future invoice or represents a refund fraud opportunity."
                ))
            elif is_creditor and t.debit > 0 and prev_bal < 0 and running_bal > 0:
                # Creditor: negative means payable (Credit). If it goes positive (Debit), we overpaid the supplier.
                findings.append(AnomalyFinding(
                    finding_id=str(uuid.uuid4()),
                    party=party,
                    anomaly_type="EXCESS PAYMENT",
                    severity="HIGH",
                    description=f"Payment of Rs. {t.debit} exceeded the payable balance of Rs. {abs(prev_bal)}, creating an advance of Rs. {running_bal}.",
                    evidence={"row_idx": t.row_idx, "date": str(t.date), "payment_amount": float(t.debit), "outstanding_before": float(abs(prev_bal)), "excess": float(running_bal)},
                    recommendation="Check if a credit note is outstanding from the supplier or if the cash payment was mistakenly inflated."
                ))

            # ------------------------------------------------
            # ANOMALY 8: JV WITHOUT BACKING
            # Journal voucher with no cash/bank and no reference
            # ------------------------------------------------
            is_jv = t.voucher_type and any(kw in t.voucher_type.lower() for kw in ["journal", "jv"])
            if is_jv:
                # JV is through contra accounts
                # If contra_ledger is not cash/bank and no reference is linkable
                if t.contra_ledger and not is_cash_bank_account(t.contra_ledger) and not t.ref_no:
                    # check narration for bill reference
                    if not re.search(r'(?i)(inv|bill|ref|invno|billno)\b', t.narration or ""):
                        findings.append(AnomalyFinding(
                            finding_id=str(uuid.uuid4()),
                            party=party,
                            anomaly_type="JV WITHOUT BACKING",
                            severity="HIGH",
                            description=f"Journal voucher entry (Row {t.row_idx}) through contra account '{t.contra_ledger}' has no linkable invoice reference.",
                            evidence={"row_idx": t.row_idx, "date": str(t.date), "amount": float(t.debit if t.debit > 0 else t.credit), "contra_ledger": t.contra_ledger},
                            recommendation="Check physical JV supporting documentation. JVs adjusting ledger balances without invoice links are common vectors for masking shortages."
                        ))

            # Record username counts for seg of duties checks
            if t.username:
                user_counts_per_party.setdefault(party, {}).setdefault(t.username, 0)
                user_counts_per_party[party][t.username] += 1

        # ----------------------------------------------------
        # Reversal and Round Trip Checks (Pairwise scans)
        # ----------------------------------------------------
        for i in range(n):
            t1 = sorted_txns[i]
            t1_amt = t1.debit if t1.debit > 0 else t1.credit
            if t1_amt == 0 or t1.is_opening_bal:
                continue
                
            for j in range(i + 1, n):
                t2 = sorted_txns[j]
                t2_amt = t2.debit if t2.debit > 0 else t2.credit
                if t2_amt == 0 or t2.is_opening_bal:
                    continue
                    
                # Reversal check: debit followed by credit of SAME amount
                is_reversal = (t1.debit > 0 and t2.credit > 0 and t1_amt == t2_amt) or \
                              (t1.credit > 0 and t2.debit > 0 and t1_amt == t2_amt)
                              
                if is_reversal:
                    delta_days = (t2.date - t1.date).days
                    
                    # Same Day Reversal
                    if delta_days == 0:
                        findings.append(AnomalyFinding(
                            finding_id=str(uuid.uuid4()),
                            party=party,
                            anomaly_type="SAME DAY REVERSAL",
                            severity="HIGH",
                            description=f"Same-day reversal of Rs. {t1_amt} (Row {t1.row_idx} reversed by Row {t2.row_idx}).",
                            evidence={"row_idx_A": t1.row_idx, "row_idx_B": t2.row_idx, "date": str(t1.date), "amount": float(t1_amt)},
                            recommendation="Verify authorization for the cancellation. Same day credit/debit matches are frequently used to correct errors but can hide cash suppression."
                        ))
                    # Next Day Reversal (within 1 calendar day)
                    elif delta_days == 1:
                        findings.append(AnomalyFinding(
                            finding_id=str(uuid.uuid4()),
                            party=party,
                            anomaly_type="NEXT DAY REVERSAL",
                            severity="MEDIUM",
                            description=f"Next-day reversal of Rs. {t1_amt} (Row {t1.row_idx} reversed by Row {t2.row_idx} next day).",
                            evidence={"row_idx_A": t1.row_idx, "row_idx_B": t2.row_idx, "date_A": str(t1.date), "date_B": str(t2.date), "amount": float(t1_amt)},
                            recommendation="Review the approval log for this correction entry to check if it was authorized by a manager."
                        ))
                    # Round Trip (within 30 days)
                    elif delta_days <= 30:
                        # Round trip: payment made and refunded/reversed within 30 days
                        findings.append(AnomalyFinding(
                            finding_id=str(uuid.uuid4()),
                            party=party,
                            anomaly_type="ROUND TRIP",
                            severity="MEDIUM",
                            description=f"Round-trip transaction of Rs. {t1_amt} matching entry on {t1.date} with reversal on {t2.date} ({delta_days} days).",
                            evidence={"row_idx_A": t1.row_idx, "row_idx_B": t2.row_idx, "date_A": str(t1.date), "date_B": str(t2.date), "amount": float(t1_amt), "delta_days": delta_days},
                            recommendation="Investigate if this represents temporary funds diversion, accommodation billings, or window dressing."
                        ))

        # ----------------------------------------------------
        # SPLIT PAYMENT PATTERN
        # Multiple small credits adding up to a round number within 7 days
        # ----------------------------------------------------
        # Look at credits (receipts/payments)
        credits_only = [t for t in sorted_txns if t.credit > 0 and not t.is_opening_bal]
        nc = len(credits_only)
        for i in range(nc):
            window_txns = [credits_only[i]]
            t1 = credits_only[i]
            total_sum = t1.credit
            
            for j in range(i + 1, nc):
                t2 = credits_only[j]
                if (t2.date - t1.date).days <= 7:
                    window_txns.append(t2)
                    total_sum += t2.credit
                    
                    # Check if total sum is a round number (e.g. 50k, 1L, etc.) and individual txns are not
                    # Ignore if total_sum is small (let's check >= 10000)
                    if total_sum >= 10000 and total_sum % 10000 == 0:
                        # Ensure individual transactions are not round numbers themselves to avoid false flags
                        if all(w.credit % 10000 != 0 for w in window_txns):
                            rows_list = [w.row_idx for w in window_txns]
                            findings.append(AnomalyFinding(
                                finding_id=str(uuid.uuid4()),
                                party=party,
                                anomaly_type="SPLIT PAYMENT PATTERN",
                                severity="HIGH",
                                description=f"Potential split payment pattern: {len(window_txns)} transactions within 7 days sum up to a round Rs. {total_sum}.",
                                evidence={"row_indices": rows_list, "dates": [str(w.date) for w in window_txns], "amounts": [float(w.credit) for w in window_txns], "total_sum": float(total_sum)},
                                recommendation="Review if payments were split into smaller tranches to bypass corporate authorization / approval limits."
                            ))
                            break

    # ----------------------------------------------------
    # USER ANOMALY
    # Single username responsible for >40% of entries for a party
    # ----------------------------------------------------
    for party, u_counts in user_counts_per_party.items():
        total_party_txns = len(party_txns[party])
        # Only check if party has a reasonable amount of data (>= 5 rows)
        if total_party_txns >= 5 and len(u_counts) > 1:
            for user, count in u_counts.items():
                pct = (count / total_party_txns) * 100
                if pct > 40:
                    findings.append(AnomalyFinding(
                        finding_id=str(uuid.uuid4()),
                        party=party,
                        anomaly_type="USER ANOMALY",
                        severity="LOW",
                        description=f"Segregation of Duties Risk: User '{user}' processed {count} transactions ({pct:.1f}%) for this party.",
                        evidence={"username": user, "user_count": count, "total_count": total_party_txns, "percentage": pct},
                        recommendation="Informational flag. Verify if a single employee has excessive control over this supplier/customer account, which increases transaction risk."
                    ))

    return findings
