from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import datetime as dt
from decimal import Decimal

class SchemaMap(BaseModel):
    """
    Schema configuration mapping raw spreadsheet columns to target fields.
    """
    party_source: str = Field(
        ..., 
        description="Source of party names. Either 'column' (if party is a column) or 'row_header' (if party appears on a row header)"
    )
    party_col_idx: Optional[int] = Field(None, description="0-based column index for Party Name (if party_source is 'column')")
    party_row_pattern: Optional[str] = Field(None, description="Sub-string or pattern to match party header rows (if party_source is 'row_header')")
    
    date_col_idx: Optional[int] = Field(None, description="0-based column index for Date")
    voucher_col_idx: Optional[int] = Field(None, description="0-based column index for Voucher Number / Type")
    debit_col_idx: Optional[int] = Field(None, description="0-based column index for Debit amount")
    credit_col_idx: Optional[int] = Field(None, description="0-based column index for Credit amount")
    balance_col_idx: Optional[int] = Field(None, description="0-based column index for Running Balance")
    narration_col_idx: Optional[int] = Field(None, description="0-based column index for Narration/Remarks")
    refno_col_idx: Optional[int] = Field(None, description="0-based column index for Reference Number / Cheque No")
    username_col_idx: Optional[int] = Field(None, description="0-based column index for entering Username")
    
    date_format: str = Field("%d-%m-%Y", description="Date parsing format (e.g. %d-%m-%Y or %Y-%m-%d)")
    header_row_idx: int = Field(..., description="1-based row index containing the column headers")
    data_start_row_idx: int = Field(..., description="1-based row index where transaction rows start")

class NormalizedTransaction(BaseModel):
    """
    Standardized transaction record representing a single debit, credit, or opening balance entry.
    """
    row_idx: int = Field(..., description="Original 1-based row index in the spreadsheet")
    party: str = Field(..., description="Name of the Debtor / Creditor party")
    date: dt.date = Field(..., description="Transaction Date")
    voucher_no: Optional[str] = Field(None, description="Voucher number or reference")
    voucher_type: Optional[str] = Field(None, description="Type of voucher (e.g., Payment, Receipt, Journal)")
    debit: Decimal = Field(default=Decimal('0.00'), description="Debit amount")
    credit: Decimal = Field(default=Decimal('0.00'), description="Credit amount")
    balance: Optional[Decimal] = Field(None, description="Reported running balance")
    narration: Optional[str] = Field("", description="Transaction narration")
    contra_ledger: Optional[str] = Field(None, description="Contra ledger account name")
    ref_no: Optional[str] = Field(None, description="Cheque/Ref number")
    username: Optional[str] = Field(None, description="Username associated with entry")
    is_opening_bal: bool = Field(default=False, description="True if this is an opening balance row")

class DuplicatePaymentFinding(BaseModel):
    """
    Finding from the Duplicate Payment Detective Agent.
    """
    finding_id: str = Field(..., description="Unique ID for the duplicate finding")
    party: str = Field(..., description="Name of the party")
    pass_number: int = Field(..., description="The detection pass number (1 to 5) that caught this")
    pass_name: str = Field(..., description="Name of the pass (e.g. EXACT DUPLICATE)")
    transaction_A: Dict[str, Any] = Field(..., description="Details of transaction A: row_idx, date, voucher, amount, contra")
    transaction_B: Dict[str, Any] = Field(..., description="Details of transaction B: row_idx, date, voucher, amount, contra")
    delta_days: int = Field(..., description="Days difference between A and B")
    delta_amount: Decimal = Field(..., description="Amount difference between A and B")
    confidence: str = Field(..., description="HIGH, MEDIUM, or LOW")
    recommendation: str = Field(..., description="Recommended auditor action")

class AgingBill(BaseModel):
    """
    Details of an individual outstanding bill.
    """
    bill_date: dt.date
    voucher_no: Optional[str]
    original_amount: Decimal
    outstanding_amount: Decimal
    age_days: int

class PartyAgingSummary(BaseModel):
    """
    Aging breakdown for a single party.
    """
    party: str
    opening_balance: Decimal
    total_debits: Decimal
    total_credits: Decimal
    outstanding_balance: Decimal
    aging_buckets: Dict[str, Decimal] = Field(
        default_factory=lambda: {
            "0-30": Decimal('0.00'),
            "31-60": Decimal('0.00'),
            "61-90": Decimal('0.00'),
            "91-180": Decimal('0.00'),
            "181-365": Decimal('0.00'),
            ">365": Decimal('0.00')
        }
    )
    outstanding_bills: List[AgingBill] = Field(default_factory=list)
    flag_unsettled_opening: bool = Field(default=False, description="Flagged if opening balance is still outstanding")
    flag_zero_payments: bool = Field(default=False, description="Flagged if no receipts/payments occurred in the period")
    is_creditor: bool = Field(default=False, description="True if this party is a creditor (AP/payable party), False if debtor")

class AnomalyFinding(BaseModel):
    """
    Single anomaly flag found during audit.
    """
    finding_id: str
    party: str
    anomaly_type: str = Field(..., description="e.g. GHOST PAYMENT, HOLIDAY PAYMENT, SAME DAY REVERSAL")
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    description: str
    evidence: Dict[str, Any] = Field(..., description="Detailed parameters of the anomaly (dates, amounts, rows)")
    recommendation: str

class ReconciliationPartySummary(BaseModel):
    """
    Reconciliation statement for a single party.
    """
    party: str
    stated_opening: Decimal
    stated_closing: Decimal
    recalculated_closing: Decimal
    variance: Decimal
    total_debits: Decimal
    total_credits: Decimal
    has_discrepancy: bool
    negative_balance_periods: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="List of intervals where running balance went negative (indicating overpayments/undocumented credits)"
    )

class AuditMemoModel(BaseModel):
    """
    Final CA-style audit memo and observations.
    """
    scope: str
    methodology: str
    key_findings: List[str]
    risk_ratings: Dict[str, str]
    recommendations: List[str]
    raw_markdown: str

class AuditSessionState(BaseModel):
    """
    Orchestration state representing the entire audit run.
    """
    file_path: str
    as_on_date: Optional[dt.date] = None
    currency_symbol: str = "Rs."
    duplicate_window_days: int = 7
    custom_holidays: List[str] = Field(default_factory=list)
    
    # Progress status streaming
    agent_statuses: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Outputs of intermediate stages
    schema_map: Optional[SchemaMap] = None
    transactions: List[NormalizedTransaction] = Field(default_factory=list)
    
    # Final findings
    duplicates: List[DuplicatePaymentFinding] = Field(default_factory=list)
    aging: List[PartyAgingSummary] = Field(default_factory=list)
    anomalies: List[AnomalyFinding] = Field(default_factory=list)
    reconciliation: List[ReconciliationPartySummary] = Field(default_factory=list)
    memo: Optional[AuditMemoModel] = None
    
    error_summary: Optional[str] = None


# ---------------------------------------------------------------------------
# Tier 1 — Advanced Forensic Finding Models
# ---------------------------------------------------------------------------

class BenfordsDigitResult(BaseModel):
    digit: int
    observed_count: int
    observed_pct: float
    expected_pct: float
    deviation: float
    z_score: float
    is_flagged: bool

class BenfordsLawFinding(BaseModel):
    """Benford's Law first-digit frequency analysis result."""
    finding_id: str
    scope: str                          # "ALL_TRANSACTIONS" or a party name
    total_transactions: int
    digit_results: List[BenfordsDigitResult]
    mad_score: float                    # Mean Absolute Deviation
    chi_square: float
    conformity: str                     # CLOSE / ACCEPTABLE / MARGINAL / NON_CONFORMING
    severity: str                       # LOW / MEDIUM / HIGH / CRITICAL
    description: str
    recommendation: str

class StatisticalOutlierFinding(BaseModel):
    """Z-Score outlier or structuring (just-under-threshold) finding."""
    finding_id: str
    party: str
    anomaly_type: str                   # "STATISTICAL_OUTLIER" | "STRUCTURING"
    transaction: Dict[str, Any]
    party_mean: float
    party_std: float
    z_score: float
    threshold_suspected: Optional[float]  # For structuring only
    severity: str
    description: str
    recommendation: str

class CircularFundFinding(BaseModel):
    """Round-trip / circular fund flow detected via graph cycle analysis."""
    finding_id: str
    cycle_parties: List[str]
    leg_count: int
    total_amount: Decimal
    evidence: List[Dict[str, Any]]      # individual transactions in the cycle
    severity: str
    description: str
    recommendation: str

class TemporalPatternFinding(BaseModel):
    """Time-based anomaly: year-end loading, FY spike, gap+burst, weekend concentration."""
    finding_id: str
    pattern_type: str                   # YEAR_END_LOADING | FY_END_SPIKE | GAP_BURST | WEEKEND_CONCENTRATION
    severity: str
    description: str
    evidence: Dict[str, Any]
    recommendation: str


# ---------------------------------------------------------------------------
# Tier 2 — Multi-Ledger & Bank Reconciliation Models
# ---------------------------------------------------------------------------

class BankTransaction(BaseModel):
    """Single row from a bank statement (any supported bank format)."""
    row_idx: int
    date: dt.date
    narration: str
    debit: Decimal = Field(default=Decimal("0.00"))
    credit: Decimal = Field(default=Decimal("0.00"))
    balance: Optional[Decimal] = None
    ref_no: Optional[str] = None
    bank_name: str = ""

class BankReconciliationItem(BaseModel):
    item_type: str                      # MATCHED | GL_ONLY | BANK_ONLY
    gl_row_idx: Optional[int] = None
    bank_row_idx: Optional[int] = None
    amount: Decimal
    date: Optional[dt.date] = None
    gl_narration: Optional[str] = None
    bank_narration: Optional[str] = None
    day_diff: int = 0

class BankReconciliationSummary(BaseModel):
    bank_file: str
    bank_name: str
    total_gl_entries: int
    total_bank_entries: int
    matched_count: int
    gl_only_count: int
    bank_only_count: int
    gl_only_amount: Decimal
    bank_only_amount: Decimal
    match_rate_pct: float
    items: List[BankReconciliationItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Expense, Sales, and GST/TDS Finding Models
# ---------------------------------------------------------------------------

class ExpenseScrutinyFinding(BaseModel):
    """Finding from the Expense Scrutiny Agent."""
    finding_id: str
    check_type: str                     # YEAR_END_LOADING | PERSONAL_EXPENSE | CASH_ABOVE_10K | etc.
    severity: str
    party: Optional[str] = None
    amount: Optional[Decimal] = None
    description: str
    evidence: Dict[str, Any]
    recommendation: str

class SalesScrutinyFinding(BaseModel):
    """Finding from the Sales Scrutiny Agent."""
    finding_id: str
    check_type: str                     # CASH_SALE_CLUSTER | EXCESSIVE_RETURNS | RAPID_REVERSAL | etc.
    severity: str
    party: Optional[str] = None
    amount: Optional[Decimal] = None
    description: str
    evidence: Dict[str, Any]
    recommendation: str

class TDSFinding(BaseModel):
    """Potential TDS non-compliance finding."""
    finding_id: str
    party: str
    total_payment: Decimal
    applicable_section: str             # e.g. "194C", "194J"
    section_name: str                   # e.g. "Contractor Payments"
    threshold: Decimal
    expected_tds_rate: float
    expected_tds_amount: Decimal
    tds_deducted: bool                  # True if evidence of TDS found in narrations
    severity: str
    description: str
    recommendation: str
