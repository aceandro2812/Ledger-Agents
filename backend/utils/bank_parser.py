"""
Bank Statement Parser
Supports auto-detection and parsing of:
  - HDFC Bank (CSV / XLS)
  - SBI (CSV)
  - ICICI Bank (CSV)
  - Axis Bank (CSV)
  - Kotak Mahindra Bank (CSV)
  - Tally Bank Book Export (same structure as GL; treated as generic)
Returns a list of BankTransaction objects.
"""
import csv
import io
import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Tuple
import os

try:
    from openpyxl.worksheet.filters import CustomFilterValueDescriptor
    if not getattr(CustomFilterValueDescriptor, "_patched", False):
        from openpyxl.descriptors.base import Convertible
        _orig_set = CustomFilterValueDescriptor.__set__
        def _patched_set(self, instance, value):
            if isinstance(value, str):
                self.expected_type = str
                Convertible.__set__(self, instance, value)
            else:
                _orig_set(self, instance, value)
        CustomFilterValueDescriptor.__set__ = _patched_set
        CustomFilterValueDescriptor._patched = True
except Exception as e:
    print(f"[Monkeypatch Warning] Failed to patch openpyxl filters descriptor: {e}")

from backend.models.schema import BankTransaction
from backend.utils.date_utils import parse_date


# ---------------------------------------------------------------------------
# Known bank format signatures: map column-header patterns → bank name
# Each entry is (bank_name, required_header_substrings)
# ---------------------------------------------------------------------------
BANK_SIGNATURES: List[Tuple[str, List[str]]] = [
    ("HDFC",   ["narration", "value dt", "debit amount", "credit amount", "chq/ref number", "closing balance"]),
    ("SBI",    ["txn date", "description", "ref no./cheque no.", "debit", "credit", "balance"]),
    ("ICICI",  ["value date", "transaction date", "cheque number", "transaction remarks",
                "withdrawal amount", "deposit amount"]),
    ("AXIS",   ["tran date", "chqno", "particulars", "debit", "credit", "balance"]),
    ("KOTAK",  ["date", "description", "chq/ref no", "debit", "credit", "balance"]),
]


def _clean_amount(val: str) -> Decimal:
    """Strip currency symbols, commas and convert to Decimal. Returns 0 on failure."""
    if not val:
        return Decimal("0.00")
    cleaned = val.strip().replace(",", "").replace("Rs.", "").replace("INR", "").replace(" ", "")
    if cleaned in ("", "-", "N/A", "nil", "Nil"):
        return Decimal("0.00")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0.00")


def _detect_bank(headers: List[str]) -> str:
    """Return best-match bank name from column headers."""
    headers_lower = [h.lower().strip() for h in headers]
    for bank_name, sig in BANK_SIGNATURES:
        if all(any(s in h for h in headers_lower) for s in sig):
            return bank_name
    return "UNKNOWN"


def _parse_hdfc(rows: List[Dict], file_name: str) -> List[BankTransaction]:
    txns = []
    for i, row in enumerate(rows, start=2):
        raw_date = row.get("Date", "").strip()
        if not raw_date:
            continue
        try:
            txn_date = parse_date(raw_date)
        except Exception:
            continue
        txns.append(BankTransaction(
            row_idx=i,
            date=txn_date,
            narration=row.get("Narration", "").strip(),
            debit=_clean_amount(row.get("Debit Amount", "")),
            credit=_clean_amount(row.get("Credit Amount", "")),
            balance=_clean_amount(row.get("Closing Balance", "")) or None,
            ref_no=row.get("Chq/Ref Number", "").strip() or None,
            bank_name="HDFC",
        ))
    return txns


def _parse_sbi(rows: List[Dict], file_name: str) -> List[BankTransaction]:
    txns = []
    for i, row in enumerate(rows, start=2):
        raw_date = row.get("Txn Date", "").strip()
        if not raw_date:
            continue
        try:
            txn_date = parse_date(raw_date)
        except Exception:
            continue
        txns.append(BankTransaction(
            row_idx=i,
            date=txn_date,
            narration=row.get("Description", "").strip(),
            debit=_clean_amount(row.get("Debit", "")),
            credit=_clean_amount(row.get("Credit", "")),
            balance=_clean_amount(row.get("Balance", "")) or None,
            ref_no=row.get("Ref No./Cheque No.", "").strip() or None,
            bank_name="SBI",
        ))
    return txns


def _parse_icici(rows: List[Dict], file_name: str) -> List[BankTransaction]:
    txns = []
    for i, row in enumerate(rows, start=2):
        raw_date = (row.get("Transaction Date") or row.get("Value Date", "")).strip()
        if not raw_date:
            continue
        try:
            txn_date = parse_date(raw_date)
        except Exception:
            continue
        debit_key = next((k for k in row if "withdrawal" in k.lower()), None)
        credit_key = next((k for k in row if "deposit" in k.lower()), None)
        bal_key = next((k for k in row if "balance" in k.lower()), None)
        txns.append(BankTransaction(
            row_idx=i,
            date=txn_date,
            narration=row.get("Transaction Remarks", "").strip(),
            debit=_clean_amount(row.get(debit_key, "")) if debit_key else Decimal("0.00"),
            credit=_clean_amount(row.get(credit_key, "")) if credit_key else Decimal("0.00"),
            balance=_clean_amount(row.get(bal_key, "")) if bal_key else None,
            ref_no=row.get("Cheque Number", "").strip() or None,
            bank_name="ICICI",
        ))
    return txns


def _parse_axis(rows: List[Dict], file_name: str) -> List[BankTransaction]:
    txns = []
    for i, row in enumerate(rows, start=2):
        raw_date = row.get("Tran Date", "").strip()
        if not raw_date:
            continue
        try:
            txn_date = parse_date(raw_date)
        except Exception:
            continue
        txns.append(BankTransaction(
            row_idx=i,
            date=txn_date,
            narration=row.get("Particulars", "").strip(),
            debit=_clean_amount(row.get("Debit", "")),
            credit=_clean_amount(row.get("Credit", "")),
            balance=_clean_amount(row.get("Balance", "")) or None,
            ref_no=row.get("CHQNO", "").strip() or None,
            bank_name="AXIS",
        ))
    return txns


def _parse_kotak(rows: List[Dict], file_name: str) -> List[BankTransaction]:
    txns = []
    for i, row in enumerate(rows, start=2):
        raw_date = row.get("date", "").strip()
        if not raw_date:
            continue
        try:
            txn_date = parse_date(raw_date)
        except Exception:
            continue
        txns.append(BankTransaction(
            row_idx=i,
            date=txn_date,
            narration=row.get("description", "").strip(),
            debit=_clean_amount(row.get("Debit", "")),
            credit=_clean_amount(row.get("Credit", "")),
            balance=_clean_amount(row.get("Balance", "")) or None,
            ref_no=row.get("Chq/Ref No", "").strip() or None,
            bank_name="KOTAK",
        ))
    return txns


def _parse_generic(rows: List[Dict], file_name: str) -> List[BankTransaction]:
    """Generic fallback: tries to pick reasonable columns by keyword."""
    if not rows:
        return []
    headers = list(rows[0].keys())
    date_col   = next((h for h in headers if "date" in h.lower()), None)
    narr_col   = next((h for h in headers if any(k in h.lower() for k in ["narration", "description", "particulars", "remarks"])), None)
    debit_col  = next((h for h in headers if any(k in h.lower() for k in ["debit", "withdrawal", "dr"])), None)
    credit_col = next((h for h in headers if any(k in h.lower() for k in ["credit", "deposit", "cr"])), None)
    bal_col    = next((h for h in headers if "balance" in h.lower()), None)
    ref_col    = next((h for h in headers if any(k in h.lower() for k in ["ref", "chq", "cheque", "refno"])), None)

    txns = []
    for i, row in enumerate(rows, start=2):
        raw_date = row.get(date_col, "").strip() if date_col else ""
        if not raw_date:
            continue
        try:
            txn_date = parse_date(raw_date)
        except Exception:
            continue
        txns.append(BankTransaction(
            row_idx=i,
            date=txn_date,
            narration=row.get(narr_col, "").strip() if narr_col else "",
            debit=_clean_amount(row.get(debit_col, "")) if debit_col else Decimal("0.00"),
            credit=_clean_amount(row.get(credit_col, "")) if credit_col else Decimal("0.00"),
            balance=_clean_amount(row.get(bal_col, "")) if bal_col else None,
            ref_no=row.get(ref_col, "").strip() if ref_col else None,
            bank_name="UNKNOWN",
        ))
    return txns


_PARSERS = {
    "HDFC":  _parse_hdfc,
    "SBI":   _parse_sbi,
    "ICICI": _parse_icici,
    "AXIS":  _parse_axis,
    "KOTAK": _parse_kotak,
}


def categorize_narration(narration: str, is_debit: bool) -> str:
    if not narration:
        return "Vendor Payments" if is_debit else "Customer Receipts"
    n_lower = str(narration).lower()
    
    # 1. Salary / Payroll
    if any(kw in n_lower for kw in ["salary", "payroll", "wage", "slip", "sal.", "incentive", "bonus"]):
        return "Salary / Payroll"
    
    # 2. Rent & Infrastructure
    if any(kw in n_lower for kw in ["rent", "lease", "estate", "infra", "maintenance", "brokerage"]):
        return "Rent & Infrastructure"
        
    # 3. Utilities
    if any(kw in n_lower for kw in ["electricity", "water", "power", "internet", "broadband", "telecom", "telephone", "mobile", "utility"]):
        return "Utilities"
        
    # 4. Taxes & Compliance
    if any(kw in n_lower for kw in ["gst", "tds", "tax", "excise", "vat", "customs", "income tax", "pf", "provident", "esi", "professional tax"]):
        return "Taxes & Compliance"
        
    # 5. Bank Charges & Interest
    if any(kw in n_lower for kw in ["bank charges", "chg", "commission", "processing", "interest", "int.", "fee", "bounced", "penalty", "card charges"]):
        return "Bank Charges & Interest"
        
    # 6. Cash Deposit / Withdrawal
    if any(kw in n_lower for kw in ["cash deposit", "cash dep", "cash self", "atm wdl", "cash withdrawal", "cash wdl", "atm"]):
        return "Cash Deposit / Withdrawal"
        
    # 7. Loan Repayments / Receipts
    if any(kw in n_lower for kw in ["emi", "loan", "repayment", "disbursement", "mortgage"]):
        return "Loan Repayments / Receipts"
        
    # 8. Travel & Office Expense
    if any(kw in n_lower for kw in ["travel", "fuel", "petrol", "cab", "uber", "ola", "stay", "hotel", "stationary", "pantry", "courier", "postage"]):
        return "Travel & Office Expense"

    # Default
    return "Vendor Payments" if is_debit else "Customer Receipts"


def parse_bank_statement(file_path: str) -> Tuple[str, List[BankTransaction]]:
    """
    Parse a bank statement file (CSV or XLSX).
    Returns (bank_name, list_of_BankTransaction).
    """
    ext = os.path.splitext(file_path)[1].lower()
    rows: List[Dict] = []
    headers: List[str] = []

    if ext == ".csv":
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            content = f.read()
        # Skip preamble lines (some bank CSVs have title rows before headers)
        lines = content.splitlines()
        header_line_idx = 0
        for idx, line in enumerate(lines):
            if "," in line and len(line.split(",")) >= 4:
                header_line_idx = idx
                break
        reader = csv.DictReader(io.StringIO("\n".join(lines[header_line_idx:])))
        rows = list(reader)
        headers = reader.fieldnames or []

    elif ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=False)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        # Find header row (first row with enough non-None cells)
        header_row_idx = 0
        for idx, row in enumerate(all_rows):
            non_empty = sum(1 for c in row if c is not None)
            if non_empty >= 4:
                header_row_idx = idx
                break
        headers = [str(c).strip() if c is not None else "" for c in all_rows[header_row_idx]]
        for row_vals in all_rows[header_row_idx + 1:]:
            if all(v is None for v in row_vals):
                continue
            rows.append({headers[i]: str(row_vals[i]).strip() if row_vals[i] is not None else ""
                         for i in range(len(headers))})
    else:
        raise ValueError(f"Unsupported file type for bank statement: {ext}")

    bank_name = _detect_bank(headers)
    parser_fn = _PARSERS.get(bank_name, _parse_generic)
    transactions = parser_fn(rows, os.path.basename(file_path))

    # If bank_name was UNKNOWN, still tag transactions
    for t in transactions:
        t.bank_name = bank_name
        t.category = categorize_narration(t.narration, t.debit > 0)

    return bank_name, transactions
