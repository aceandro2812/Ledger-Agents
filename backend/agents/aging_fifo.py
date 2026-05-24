from typing import List, Dict, Any, Optional
from decimal import Decimal
import datetime as dt
from backend.models.schema import NormalizedTransaction, PartyAgingSummary, AgingBill

def calculate_aging_fifo(
    transactions: List[NormalizedTransaction],
    as_on_date: Optional[dt.date] = None
) -> List[PartyAgingSummary]:
    """
    Computes FIFO bill-to-bill matching and reports aging schedules per party.
    """
    # If no as-on date is provided, use the date of the latest transaction in the file
    if not as_on_date and transactions:
        as_on_date = max(t.date for t in transactions)
    if not as_on_date:
        as_on_date = dt.date.today()

    # Group transactions by party
    party_txns: Dict[str, List[NormalizedTransaction]] = {}
    for txn in transactions:
        party_txns.setdefault(txn.party, []).append(txn)

    summaries = []

    for party, txns in party_txns.items():
        sorted_txns = sorted(txns, key=lambda x: (x.date, x.row_idx))
        
        # Calculate opening balance and overall financials
        opening_bal = Decimal("0.00")
        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")
        
        opening_rows = [t for t in sorted_txns if t.is_opening_bal]
        if opening_rows:
            op_row = opening_rows[0]
            if op_row.debit > 0:
                opening_bal = op_row.debit
            elif op_row.credit > 0:
                opening_bal = -op_row.credit
            elif op_row.balance is not None:
                opening_bal = op_row.balance
                if "cr" in op_row.narration.lower():
                    opening_bal = -opening_bal
                    
        for t in sorted_txns:
            if not t.is_opening_bal:
                total_debits += t.debit
                total_credits += t.credit

        # Determine direction: Creditor vs Debtor
        is_creditor = False
        if opening_bal < 0 or (opening_bal == 0 and total_credits > total_debits):
            is_creditor = True
            
        # Structure Bills and Settlements lists
        # A bill increases the outstanding amount, a settlement decreases it.
        # For Debtors: Bill = Debit, Settlement = Credit
        # For Creditors: Bill = Credit, Settlement = Debit
        bills = []
        settlements = []
        
        # Add opening balance as oldest bill (if positive) or settlement (if negative/credit advance)
        start_date = sorted_txns[0].date if sorted_txns else as_on_date
        
        if is_creditor:
            # Liability: Credit is normal bill, Debit is payment
            if opening_bal != 0:
                val = abs(opening_bal)
                if opening_bal < 0: # Payable opening
                    bills.append({
                        "date": start_date,
                        "voucher_no": "OPENING",
                        "original_amount": val,
                        "outstanding_amount": val,
                        "is_opening": True
                    })
                else: # Debit opening (advance paid to supplier)
                    settlements.append(val)
        else:
            # Asset: Debit is normal bill, Credit is payment
            if opening_bal != 0:
                val = abs(opening_bal)
                if opening_bal > 0: # Receivable opening
                    bills.append({
                        "date": start_date,
                        "voucher_no": "OPENING",
                        "original_amount": val,
                        "outstanding_amount": val,
                        "is_opening": True
                    })
                else: # Credit opening (advance received from customer)
                    settlements.append(val)
                    
        # Parse transaction entries
        for t in sorted_txns:
            if t.is_opening_bal:
                continue
                
            if is_creditor:
                # Bills are Credits, Settlements are Debits
                if t.credit > 0:
                    bills.append({
                        "date": t.date,
                        "voucher_no": t.voucher_no or f"ROW-{t.row_idx}",
                        "original_amount": t.credit,
                        "outstanding_amount": t.credit,
                        "is_opening": False
                    })
                if t.debit > 0:
                    settlements.append(t.debit)
            else:
                # Bills are Debits, Settlements are Credits
                if t.debit > 0:
                    bills.append({
                        "date": t.date,
                        "voucher_no": t.voucher_no or f"ROW-{t.row_idx}",
                        "original_amount": t.debit,
                        "outstanding_amount": t.debit,
                        "is_opening": False
                    })
                if t.credit > 0:
                    settlements.append(t.credit)

        # FIFO matching
        for settlement_amt in settlements:
            curr_settlement = settlement_amt
            for bill in bills:
                if bill["outstanding_amount"] > 0:
                    match_amt = min(curr_settlement, bill["outstanding_amount"])
                    bill["outstanding_amount"] -= match_amt
                    curr_settlement -= match_amt
                    if curr_settlement <= 0:
                        break

        # Post-process outstanding bills into aging buckets
        aging_buckets = {
            "0-30": Decimal("0.00"),
            "31-60": Decimal("0.00"),
            "61-90": Decimal("0.00"),
            "91-180": Decimal("0.00"),
            "181-365": Decimal("0.00"),
            ">365": Decimal("0.00")
        }
        
        outstanding_bills = []
        flag_unsettled_opening = False
        
        for bill in bills:
            out_amt = bill["outstanding_amount"]
            if out_amt > 0:
                age_days = (as_on_date - bill["date"]).days
                if age_days < 0:
                    age_days = 0  # transaction date is after as_on_date
                    
                if bill["is_opening"]:
                    flag_unsettled_opening = True
                    
                # Put in bucket
                if age_days <= 30:
                    aging_buckets["0-30"] += out_amt
                elif age_days <= 60:
                    aging_buckets["31-60"] += out_amt
                elif age_days <= 90:
                    aging_buckets["61-90"] += out_amt
                elif age_days <= 180:
                    aging_buckets["91-180"] += out_amt
                elif age_days <= 365:
                    aging_buckets["181-365"] += out_amt
                else:
                    aging_buckets[">365"] += out_amt
                    
                outstanding_bills.append(AgingBill(
                    bill_date=bill["date"],
                    voucher_no=bill["voucher_no"],
                    original_amount=bill["original_amount"],
                    outstanding_amount=out_amt,
                    age_days=age_days
                ))

        # Check flag: zero payments in period
        flag_zero_payments = (len(settlements) == 0)

        # Net outstanding position
        # For debtors, receivable = opening + debits - credits
        # For creditors, payable = opening_payable + credits - debits
        net_outstanding = sum(b.outstanding_amount for b in outstanding_bills)
        if is_creditor:
            # If the outstanding payments exceeded bills, net position is negative
            net_outstanding = -net_outstanding if (total_debits > total_credits + abs(opening_bal)) else net_outstanding
        else:
            net_outstanding = -net_outstanding if (total_credits > total_debits + abs(opening_bal)) else net_outstanding

        summaries.append(PartyAgingSummary(
            party=party,
            opening_balance=opening_bal,
            total_debits=total_debits,
            total_credits=total_credits,
            outstanding_balance=net_outstanding,
            aging_buckets=aging_buckets,
            outstanding_bills=outstanding_bills,
            flag_unsettled_opening=flag_unsettled_opening,
            flag_zero_payments=flag_zero_payments,
            is_creditor=is_creditor
        ))

    return summaries
