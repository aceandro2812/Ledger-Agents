import re
from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from datetime import date
from backend.models.schema import SchemaMap, NormalizedTransaction
from backend.utils.excel_parser import RawRow
from backend.utils.date_utils import parse_date

# Define common row-header patterns for party names
PARTY_HEADER_MARKERS = [
    r"(?i)ledger\s*:\s*(.*)",
    r"(?i)ledger\s+account\s*:\s*(.*)",
    r"(?i)account\s+of\s*:\s*(.*)",
    r"(?i)party\s*name\s*:\s*(.*)",
    r"(?i)customer\s*:\s*(.*)",
    r"(?i)vendor\s*:\s*(.*)"
]

def clean_amount(val: Any) -> Decimal:
    """
    Cleans a numeric/string cell value and returns it as a Decimal.
    Handles commas, currency symbols, and brackets.
    """
    if val is None:
        return Decimal("0.00")
        
    if isinstance(val, (int, float)):
        return Decimal(f"{val:.2f}")
        
    if isinstance(val, Decimal):
        return val

    # Clean string representation
    val_str = str(val).strip()
    if not val_str:
        return Decimal("0.00")

    # Remove currency symbols and formatting commas
    cleaned = re.sub(r"[^\d\.\-\(\)]", "", val_str)
    
    # Handle brackets for negative numbers, e.g. (1,200.00) -> -1200.00
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
        
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0.00")

def parse_combined_amount(val: Any) -> tuple[Decimal, bool, bool]:
    """
    Parses a single combined amount cell (e.g. '15000.00 Dr' or '-15000.00')
    Returns: (Amount, is_debit, is_credit)
    """
    if val is None:
        return Decimal("0.00"), False, False
        
    val_str = str(val).strip().lower()
    
    # Check for Dr/Cr suffixes
    is_dr = "dr" in val_str
    is_cr = "cr" in val_str
    
    # Clean and parse number
    amt = clean_amount(val)
    
    if amt < 0:
        # Negative indicates credit in a combined ledger representation
        return abs(amt), False, True
    elif amt > 0:
        if is_cr:
            return amt, False, True
        # Default or Dr suffix
        return amt, True, False
        
    return Decimal("0.00"), False, False

def extract_party_from_row(row_cells: List[Any], only_explicit: bool = False) -> Optional[str]:
    """
    Checks if a row is a party name header row and extracts the party name.
    """
    # Look for explicit string match
    for cell in row_cells:
        if cell and isinstance(cell, str):
            for marker in PARTY_HEADER_MARKERS:
                match = re.search(marker, cell)
                if match:
                    return match.group(1).strip()
                    
    if only_explicit:
        return None

    # Look for standalone bold/text row (where almost all other cells are empty)
    non_empty = [c for c in row_cells if c is not None and str(c).strip() != ""]
    if len(non_empty) == 1 and isinstance(non_empty[0], str):
        val = non_empty[0].strip()
        # Ensure it's not a generic table header or total row
        lower_val = val.lower()
        excluded_keywords = ["date", "particulars", "debit", "credit", "balance", "total", "opening", "closing", "period", "vch"]
        if not any(ek in lower_val for ek in excluded_keywords):
            # Check length to ensure it looks like a name
            if 3 < len(val) < 60:
                return val
                
    return None

def ingest_transactions(rows: List[RawRow], schema: SchemaMap) -> List[NormalizedTransaction]:
    """
    Parses raw rows into a list of normalized transaction records.
    """
    transactions = []
    current_party = "Default Party"
    
    # If the sheet is a single party with party name in top rows
    # we pre-scan the rows before the header row to see if we can find a party name
    if schema.party_source == "row_header":
        for r in rows:
            if r.row_idx < schema.header_row_idx:
                party_name = extract_party_from_row(r.cells, only_explicit=False)
                if party_name:
                    current_party = party_name
                    break

    for row in rows:
        r_idx = row.row_idx
        cells = row.cells
        
        # If it's the header row or before, skip it for transaction parsing
        if r_idx <= schema.header_row_idx:
            # But keep scanning for party name changes if party_source is row_header
            if schema.party_source == "row_header":
                party_name = extract_party_from_row(cells, only_explicit=False)
                if party_name:
                    current_party = party_name
            continue
            
        # Check if the row contains subtotal or summary keywords. Skip them.
        row_txt = " ".join([str(c) for c in cells if c is not None]).lower()
        if any(kw in row_txt for kw in ["total", "subtotal", "carried forward", "c/f", "brought forward", "b/f", "closing balance"]):
            # Note: "opening balance" or "brought forward" inside a transaction row is parsed as opening balance,
            # but standard summary footer rows are skipped.
            # If the row is simply a balance summary line, we skip it to prevent double counting.
            if "opening balance" not in row_txt and "op. bal" not in row_txt:
                continue
                
        # If party name is defined as a column, retrieve it
        if schema.party_source == "column" and schema.party_col_idx is not None:
            if schema.party_col_idx < len(cells):
                p_val = cells[schema.party_col_idx]
                if p_val:
                    current_party = str(p_val).strip()
                else:
                    # Skip rows with empty party column in column-source files (often blank filler rows)
                    continue
        elif schema.party_source == "row_header":
            # Check if this row is a new party header row (must be explicit inside data section)
            party_name = extract_party_from_row(cells, only_explicit=True)
            if party_name:
                current_party = party_name
                continue
                
        # Parse Date
        if schema.date_col_idx is None or schema.date_col_idx >= len(cells):
            continue
        raw_date = cells[schema.date_col_idx]
        if raw_date is None:
            continue
            
        txn_date = parse_date(raw_date)
        if txn_date is None:
            # If date is unparseable and financial columns are empty, skip row
            continue

        # Check if this is an opening balance row
        is_opening = False
        narration_text = ""
        if schema.narration_col_idx is not None and schema.narration_col_idx < len(cells):
            narr_val = cells[schema.narration_col_idx]
            if narr_val:
                narration_text = str(narr_val).strip()
                if any(kw in narration_text.lower() for kw in ["opening balance", "op. bal", "opening b/f", "brought forward"]):
                    is_opening = True

        # Parse debit/credit/balance
        debit_amt = Decimal("0.00")
        credit_amt = Decimal("0.00")
        
        # Scenario A: Combined Amount column
        if schema.debit_col_idx == schema.credit_col_idx and schema.debit_col_idx is not None:
            col_idx = schema.debit_col_idx
            if col_idx < len(cells):
                val = cells[col_idx]
                amt, is_dr, is_cr = parse_combined_amount(val)
                if is_dr:
                    debit_amt = amt
                else:
                    credit_amt = amt
        else:
            # Scenario B: Separate columns
            if schema.debit_col_idx is not None and schema.debit_col_idx < len(cells):
                debit_amt = clean_amount(cells[schema.debit_col_idx])
            if schema.credit_col_idx is not None and schema.credit_col_idx < len(cells):
                credit_amt = clean_amount(cells[schema.credit_col_idx])
                
        # Parse running balance (optional check)
        balance_amt = None
        if schema.balance_col_idx is not None and schema.balance_col_idx < len(cells):
            bal_val = cells[schema.balance_col_idx]
            if bal_val is not None:
                # Running balance can also have Dr/Cr suffix
                balance_amt, _, _ = parse_combined_amount(bal_val)
                
        # If both debit and credit are zero, and it's not an opening balance row, skip
        if debit_amt == 0 and credit_amt == 0 and not is_opening:
            # Try to see if this is an opening balance row represented in some other column
            particulars_val = ""
            if schema.narration_col_idx is not None and schema.narration_col_idx < len(cells):
                particulars_val = str(cells[schema.narration_col_idx] or "").lower()
            if "opening" in particulars_val or "op. bal" in particulars_val:
                is_opening = True
            else:
                continue

        # Parse voucher and references
        voucher_val = None
        if schema.voucher_col_idx is not None and schema.voucher_col_idx < len(cells):
            v_val = cells[schema.voucher_col_idx]
            if v_val is not None:
                voucher_val = str(v_val).strip()
                
        ref_val = None
        if schema.refno_col_idx is not None and schema.refno_col_idx < len(cells):
            r_val = cells[schema.refno_col_idx]
            if r_val is not None:
                ref_val = str(r_val).strip()

        username_val = None
        if schema.username_col_idx is not None and schema.username_col_idx < len(cells):
            u_val = cells[schema.username_col_idx]
            if u_val is not None:
                username_val = str(u_val).strip()

        # Build transaction record
        txn = NormalizedTransaction(
            row_idx=r_idx,
            party=current_party,
            date=txn_date,
            voucher_no=voucher_val,
            debit=debit_amt,
            credit=credit_amt,
            balance=balance_amt,
            narration=narration_text,
            ref_no=ref_val,
            username=username_val,
            is_opening_bal=is_opening
        )
        transactions.append(txn)
        
    return transactions
