from typing import List, Dict, Any
from decimal import Decimal
from datetime import date
from backend.models.schema import NormalizedTransaction, ReconciliationPartySummary

def reconcile_ledgers(
    transactions: List[NormalizedTransaction], 
    discrepancy_threshold: Decimal = Decimal("1.00")
) -> List[ReconciliationPartySummary]:
    """
    Performs independent arithmetic verification of ledger entries grouped by party.
    Recalculates cumulative running balances and flags discrepancies.
    """
    # Group transactions by party
    party_txns: Dict[str, List[NormalizedTransaction]] = {}
    for txn in transactions:
        party_txns.setdefault(txn.party, []).append(txn)
        
    summaries = []
    
    for party, txns in party_txns.items():
        # Sort transactions by date and row index to maintain order
        sorted_txns = sorted(txns, key=lambda x: (x.date, x.row_idx))
        
        # 1. Identify opening balance
        opening_bal = Decimal("0.00")
        stated_closing = Decimal("0.00")
        has_stated_closing = False
        
        # If there are transactions, find the opening balance row
        opening_rows = [t for t in sorted_txns if t.is_opening_bal]
        if opening_rows:
            # Tally can represent opening balance as debit or credit
            # If both are zero but running balance is present, use running balance
            op_row = opening_rows[0]
            if op_row.debit > 0:
                opening_bal = op_row.debit
            elif op_row.credit > 0:
                opening_bal = -op_row.credit  # Credit opening balance represented as negative
            elif op_row.balance is not None:
                opening_bal = op_row.balance
                # Check if it was Cr in narration
                if "cr" in op_row.narration.lower():
                    opening_bal = -opening_bal
                    
        # Find stated closing balance (balance of the last row that has a balance)
        for t in reversed(sorted_txns):
            if t.balance is not None:
                stated_closing = t.balance
                # SAP/Tally signs
                if t.credit > 0 and t.debit == 0 and "cr" in (t.narration or "").lower():
                    stated_closing = -stated_closing
                has_stated_closing = True
                break
                
        # 2. Recalculate running balance
        # Determine ledger direction type: Debtor (debits increase, credits decrease)
        # or Creditor (credits increase, debits decrease)
        # To determine, we look at the net direction of transactions
        total_debits = sum(t.debit for t in sorted_txns if not t.is_opening_bal)
        total_credits = sum(t.credit for t in sorted_txns if not t.is_opening_bal)
        
        # Default direction: positive means Debtor (Asset)
        # If net transactions are credit-heavy, or opening balance is negative (Cr),
        # we treat it as Creditor (Liability) where Credits increase balance.
        is_creditor = False
        if opening_bal < 0 or (opening_bal == 0 and total_credits > total_debits):
            is_creditor = True
            
        # Initialize running balance
        current_recalculated = opening_bal
        negative_periods = []
        active_negative_start = None
        min_neg_bal = Decimal("0.00")
        
        has_discrepancy = False
        max_variance = Decimal("0.00")
        
        # Recalculate transaction by transaction
        for txn in sorted_txns:
            if txn.is_opening_bal:
                continue
                
            # Update balance
            current_recalculated += (txn.debit - txn.credit)
            
            # Check for negative balance (indicating overpayment / cash advances)
            # For Debtors: negative balance means balance < 0 (Credits exceeded Debits)
            # For Creditors: negative balance means balance > 0 (Debits exceeded Credits)
            # In normalized terms, let's look at the absolute sign relative to the normal state:
            is_neg = False
            normal_sign_bal = current_recalculated if not is_creditor else -current_recalculated
            
            if normal_sign_bal < 0:
                is_neg = True
                
            if is_neg:
                if active_negative_start is None:
                    active_negative_start = txn.date
                    min_neg_bal = normal_sign_bal
                else:
                    min_neg_bal = min(min_neg_bal, normal_sign_bal)
            else:
                if active_negative_start is not None:
                    negative_periods.append({
                        "start_date": active_negative_start,
                        "end_date": txn.date,
                        "min_balance": abs(min_neg_bal),
                        "duration_days": (txn.date - active_negative_start).days
                    })
                    active_negative_start = None
                    min_neg_bal = Decimal("0.00")
                    
            # Check discrepancy on rows that have stated balance
            if txn.balance is not None:
                # Compare absolute values because sheets often write balances as positive numbers with Dr/Cr flags
                row_variance = abs(abs(current_recalculated) - abs(txn.balance))
                if row_variance > discrepancy_threshold:
                    has_discrepancy = True
                    max_variance = max(max_variance, row_variance)

        # Close any open negative balance period at the end
        if active_negative_start is not None:
            negative_periods.append({
                "start_date": active_negative_start,
                "end_date": sorted_txns[-1].date,
                "min_balance": abs(min_neg_bal),
                "duration_days": (sorted_txns[-1].date - active_negative_start).days
            })
            
        # Calculate final closing variance
        if has_stated_closing:
            variance = abs(abs(current_recalculated) - abs(stated_closing))
        else:
            variance = Decimal("0.00")
            
        summaries.append(ReconciliationPartySummary(
            party=party,
            stated_opening=abs(opening_bal),
            stated_closing=abs(stated_closing) if has_stated_closing else abs(current_recalculated),
            recalculated_closing=abs(current_recalculated),
            variance=variance,
            total_debits=total_debits,
            total_credits=total_credits,
            has_discrepancy=has_discrepancy or (variance > discrepancy_threshold),
            negative_balance_periods=negative_periods
        ))
        
    return summaries
