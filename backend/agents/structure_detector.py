import re
from typing import List, Dict, Any, Optional, Tuple
from backend.models.schema import SchemaMap
from backend.utils.excel_parser import RawRow
from backend.utils.llm import LLMClient
from backend.utils.date_utils import parse_date

# Define keywords for heuristic column mapping
HEADER_KEYWORDS = {
    "date_col_idx": ["date", "dt", "posting date", "txn date", "tran date", "trans date"],
    "voucher_col_idx": ["voucher", "vch", "vno", "vch no", "vnum", "doc no", "document", "vch type", "voucher type", "type", "doc. no"],
    "debit_col_idx": ["debit", "dr", "payment", "withdrawal", "dr amount", "debit amount", "amount", "amt", "val", "value", "local cur"],
    "credit_col_idx": ["credit", "cr", "receipt", "deposit", "cr amount", "credit amount", "amount", "amt", "val", "value", "local cur"],
    "balance_col_idx": ["balance", "bal", "closing", "outstanding", "running balance", "cum balance"],
    "narration_col_idx": ["narration", "particulars", "description", "remarks", "details", "naration", "text", "line text", "comment"],
    "refno_col_idx": ["ref", "ref no", "reference", "cheque", "chq", "instrument", "inst no", "chq no", "cheque no", "assignment"],
    "username_col_idx": ["username", "user", "entered by", "creator", "prepared by", "operator", "user name"],
    "party_col_idx": ["party", "party name", "customer", "vendor", "supplier", "account name", "ledger", "ledger name"]
}

def detect_date_format(sample_values: List[str]) -> str:
    """
    Analyzes sample date strings to detect the most probable date format.
    Defaults to '%d-%m-%Y'.
    """
    formats_patterns = [
        (re.compile(r'^\d{4}-\d{2}-\d{2}$'), "%Y-%m-%d"),
        (re.compile(r'^\d{4}/\d{2}/\d{2}$'), "%Y/%m/%d"),
        (re.compile(r'^\d{2}-\d{2}-\d{4}$'), "%d-%m-%Y"),
        (re.compile(r'^\d{2}/\d{2}/\d{4}$'), "%d/%m/%Y"),
        (re.compile(r'^\d{1,2}-[a-zA-Z]{3}-\d{2,4}$'), "%d-%b-%Y"),
        (re.compile(r'^\d{1,2}\s[a-zA-Z]{3}\s\d{2,4}$'), "%d %b %Y"),
    ]
    
    votes = {}
    for val in sample_values:
        if not val:
            continue
        val_str = str(val).strip()
        for regex, fmt in formats_patterns:
            if regex.match(val_str):
                votes[fmt] = votes.get(fmt, 0) + 1
                break
                
    if votes:
        return max(votes, key=votes.get)
    return "%d-%m-%Y"

def run_heuristics(rows: List[RawRow]) -> Tuple[Optional[SchemaMap], int]:
    """
    Executes a score-based mapping scan on the first 100 rows.
    Returns (SchemaMap, confidence_score) where confidence_score is 0-100.
    """
    best_row_idx = -1
    best_total_score = -1
    best_mapping = {}

    limit = min(len(rows), 100)
    for r_idx in range(limit):
        row = rows[r_idx]
        cells = row.cells
        
        # We need a minimum number of cells to consider this a header row candidate
        non_empty_str_cells = [c for c in cells if c is not None and isinstance(c, str) and c.strip() != ""]
        if len(non_empty_str_cells) < 3:
            continue
            
        # Score each cell for each target field
        scores = {target: [-1] * len(cells) for target in HEADER_KEYWORDS.keys()}
        
        for c_idx, cell in enumerate(cells):
            if not cell or not isinstance(cell, str):
                continue
            cell_lower = cell.lower().strip()
            
            # 1. Date
            if any(kw in cell_lower for kw in ["date", "dt", "posting", "txn", "tran"]):
                scores["date_col_idx"][c_idx] = 10
                
            # 2. Voucher
            if any(kw in cell_lower for kw in ["vno", "vch no", "vch_no", "voucher no", "voucher_no", "voucher number", "doc no", "doc_no", "document no", "document number", "vch. no", "doc. no"]):
                scores["voucher_col_idx"][c_idx] = 12
            elif any(kw in cell_lower for kw in ["voucher", "vch", "doc", "document"]):
                scores["voucher_col_idx"][c_idx] = 10
            elif "type" in cell_lower:
                scores["voucher_col_idx"][c_idx] = 5
                
            # 3. Debit
            if any(kw in cell_lower for kw in ["debit", "dr"]):
                scores["debit_col_idx"][c_idx] = 10
            elif any(kw in cell_lower for kw in ["payment", "withdrawal"]):
                scores["debit_col_idx"][c_idx] = 8
            elif any(kw in cell_lower for kw in ["amount", "amt", "value", "local cur"]):
                scores["debit_col_idx"][c_idx] = 5
                
            # 4. Credit
            if any(kw in cell_lower for kw in ["credit", "cr"]):
                scores["credit_col_idx"][c_idx] = 10
            elif any(kw in cell_lower for kw in ["receipt", "deposit"]):
                scores["credit_col_idx"][c_idx] = 8
            elif any(kw in cell_lower for kw in ["amount", "amt", "value", "local cur"]):
                scores["credit_col_idx"][c_idx] = 5
                
            # 5. Balance
            if any(kw in cell_lower for kw in ["balance", "bal", "closing", "outstanding"]):
                scores["balance_col_idx"][c_idx] = 10
                
            # 6. Narration
            if any(kw in cell_lower for kw in ["narration", "particulars", "description", "remarks", "text", "comment"]):
                scores["narration_col_idx"][c_idx] = 10
                
            # 7. Ref No
            if any(kw in cell_lower for kw in ["ref", "reference", "cheque", "chq", "instrument", "assignment"]):
                scores["refno_col_idx"][c_idx] = 10
                
            # 8. Username
            if any(kw in cell_lower for kw in ["username", "user", "creator", "prepared by", "operator"]):
                scores["username_col_idx"][c_idx] = 10
                
            # 9. Party
            if any(kw in cell_lower for kw in ["party", "customer", "vendor", "supplier", "ledger", "account name"]):
                scores["party_col_idx"][c_idx] = 10

        # Build mapping based on highest score per field
        mapping = {}
        row_score = 0
        for target, col_scores in scores.items():
            max_val = max(col_scores)
            if max_val > 0:
                mapping[target] = col_scores.index(max_val)
                # Date and financials are more important
                weight = 2 if target in ["date_col_idx", "debit_col_idx", "credit_col_idx"] else 1
                row_score += max_val * weight

        # Check if this row is a valid header candidate
        has_date = "date_col_idx" in mapping
        has_financial = "debit_col_idx" in mapping or "credit_col_idx" in mapping or "balance_col_idx" in mapping
        
        if has_date and has_financial and row_score > best_total_score:
            best_total_score = row_score
            best_row_idx = row.row_idx
            best_mapping = mapping

    if best_row_idx == -1:
        return None, 0

    party_source = "column" if "party_col_idx" in best_mapping else "row_header"
    
    # Try to identify date format from samples (look down the Date column)
    sample_dates = []
    date_col = best_mapping.get("date_col_idx")
    if date_col is not None:
        start_row = best_row_idx
        for r_idx in range(start_row, min(len(rows), start_row + 20)):
            if r_idx < len(rows) and date_col < len(rows[r_idx].cells):
                cell_val = rows[r_idx].cells[date_col]
                if cell_val:
                    sample_dates.append(str(cell_val))
                    
    detected_fmt = detect_date_format(sample_dates)

    schema_map = SchemaMap(
        party_source=party_source,
        party_col_idx=best_mapping.get("party_col_idx"),
        party_row_pattern="Ledger:|Account of:|Party:",
        date_col_idx=best_mapping.get("date_col_idx"),
        voucher_col_idx=best_mapping.get("voucher_col_idx"),
        debit_col_idx=best_mapping.get("debit_col_idx"),
        credit_col_idx=best_mapping.get("credit_col_idx"),
        balance_col_idx=best_mapping.get("balance_col_idx"),
        narration_col_idx=best_mapping.get("narration_col_idx"),
        refno_col_idx=best_mapping.get("refno_col_idx"),
        username_col_idx=best_mapping.get("username_col_idx"),
        date_format=detected_fmt,
        header_row_idx=best_row_idx,
        data_start_row_idx=best_row_idx + 1
    )
    
    # Confidence calculation:
    critical_count = sum(1 for f in ["date_col_idx", "debit_col_idx", "credit_col_idx", "narration_col_idx"] if f in best_mapping)
    confidence = int((critical_count / 4.0) * 100)
    
    return schema_map, confidence

def run_llm_detector(rows: List[RawRow], llm_client: LLMClient) -> SchemaMap:
    """
    Sends a preview of the sheet (first 30 rows) to the LLM to analyze the structure and return SchemaMap JSON.
    """
    # Create a nice text grid representing the first 20 rows (enough to detect structure)
    grid = []
    for r in rows[:20]:
        grid.append(f"Row {r.row_idx}: {r.cells}")
    grid_txt = "\n".join(grid)

    system_prompt = (
        "You are an expert financial forensic auditor specializing in General Ledger analysis.\n"
        "Your task is to analyze the structure of a spreadsheet export and map its columns to standard transaction fields.\n"
        "You must return a JSON object matching the provided SchemaMap schema."
    )
    
    user_prompt = (
        f"Here is a preview of the first 40 rows of an uploaded ledger dump:\n\n"
        f"{grid_txt}\n\n"
        f"Instructions:\n"
        f"1. Identify the 1-based header row index (where column names are defined).\n"
        f"2. Identify the column mappings (0-based column indices). Note: if Debit and Credit are combined in one column, set both debit_col_idx and credit_col_idx to that column index.\n"
        f"3. Detect if the ledger contains transactions for multiple parties, and if so, how they are represented:\n"
        f"   - If there is a party name column, set party_source = 'column' and map party_col_idx.\n"
        f"   - If party names appear in standalone row headers before their transaction blocks (e.g. containing 'Ledger:' or company names on standalone lines), set party_source = 'row_header' and set a party_row_pattern (e.g. 'Ledger:' or similar text substring that appears in those rows).\n"
        f"4. Detect the date format from the date column sample strings (e.g. %d-%m-%Y, %Y-%m-%d, %d-%b-%Y, etc.).\n"
        f"5. Return the mapped SchemaMap JSON object."
    )

    return llm_client.call_structured(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_model=SchemaMap
    )

def detect_structure(rows: List[RawRow], llm_client: Optional[LLMClient] = None) -> SchemaMap:
    """
    Analyzes raw spreadsheet rows and returns the SchemaMap.
    Uses rules first; if confidence is low (< 75%) and LLM client is configured, falls back to LLM.
    """
    schema_map, confidence = run_heuristics(rows)
    
    # If heuristics succeeded with reasonable confidence, use them directly.
    # Threshold is 50 (not 75) — most standard Tally/SAP/Busy exports score well
    # above this without needing an expensive LLM round-trip.
    if schema_map and confidence >= 50:
        return schema_map

    # Otherwise fallback to LLM if configured
    if llm_client and llm_client.is_configured():
        try:
            return run_llm_detector(rows, llm_client)
        except Exception as e:
            print(f"[Warning] LLM structure detector failed or timed out: {str(e)}. Falling back to heuristics mapping.")
            # If LLM fails, fallback to heuristic schema even if low confidence
            if schema_map:
                return schema_map
            raise
            
    # Default fallback if no LLM and heuristics failed/low-confidence
    if schema_map:
        return schema_map
        
    raise ValueError(
        "Could not detect structure of the ledger dump. "
        "No clear header row or columns found (Date/Particulars/Debit/Credit)."
    )
