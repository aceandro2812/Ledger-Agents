from typing import Annotated, TypedDict, List, Dict, Any, Optional
from operator import add
import datetime as dt
from decimal import Decimal
import os
import traceback

from langgraph.graph import StateGraph, START, END

from backend.models.schema import (
    SchemaMap,
    NormalizedTransaction,
    DuplicatePaymentFinding,
    PartyAgingSummary,
    AnomalyFinding,
    ReconciliationPartySummary,
    AuditMemoModel,
    BenfordsLawFinding,
    StatisticalOutlierFinding,
    CircularFundFinding,
    TemporalPatternFinding,
    BankReconciliationSummary,
    BankTransaction,
    ExpenseScrutinyFinding,
    SalesScrutinyFinding,
    TDSFinding,
)
from backend.utils.excel_parser import parse_file
from backend.agents.structure_detector import detect_structure
from backend.agents.ingestion import ingest_transactions
from backend.agents.duplicate_detector import detect_duplicates
from backend.agents.aging_fifo import calculate_aging_fifo
from backend.agents.anomaly_detector import detect_anomalies
from backend.agents.reconciliation import reconcile_ledgers
from backend.agents.report_generator import generate_excel_report, generate_audit_memo_markdown
from backend.agents.benfords_law import detect_benfords_violations
from backend.agents.zscore_outlier import detect_statistical_outliers
from backend.agents.circular_fund import detect_circular_funds
from backend.agents.temporal_pattern import detect_temporal_patterns
from backend.agents.bank_reconciliation import reconcile_with_bank
from backend.agents.expense_scrutiny import scrutinize_expenses
from backend.agents.sales_scrutiny import scrutinize_sales
from backend.agents.gst_tds import detect_tds_gaps
from backend.utils.llm import LLMClient

# Define LangGraph Audit State
class AuditState(TypedDict):
    file_path: str
    as_on_date: Optional[dt.date]
    currency_symbol: str
    duplicate_window_days: int
    custom_holidays: List[str]

    # Extra files attached after primary upload: [{file_path, ledger_type}]
    extra_files: List[Dict[str, str]]

    # Reducer appends lists of status logs
    status_updates: Annotated[List[Dict[str, Any]], add]

    # Raw parsed rows — populated once by structure_detector, reused by ingestion.
    # Avoids reading and parsing the file a second time.
    raw_rows: Optional[List[Any]]

    # Mapped outputs
    schema_map: Optional[SchemaMap]
    transactions: List[NormalizedTransaction]

    # --- Existing findings ---
    duplicates: List[DuplicatePaymentFinding]
    aging: List[PartyAgingSummary]
    anomalies: List[AnomalyFinding]
    reconciliation: List[ReconciliationPartySummary]

    # --- Tier 1: Statistical / Advanced ---
    benfords_findings: List[BenfordsLawFinding]
    statistical_outliers: List[StatisticalOutlierFinding]
    circular_funds: List[CircularFundFinding]
    temporal_patterns: List[TemporalPatternFinding]

    # --- Tier 2: Multi-Ledger / Compliance ---
    bank_transactions: List[BankTransaction]
    bank_reconciliation: Optional[BankReconciliationSummary]
    expense_scrutiny: List[ExpenseScrutinyFinding]
    sales_scrutiny: List[SalesScrutinyFinding]
    gst_tds: List[TDSFinding]

    # --- Report outputs ---
    memo: Optional[AuditMemoModel]
    excel_report_path: Optional[str]

    error_summary: Optional[str]


# ---------------------------------------------------------------------------
# Helper: skip guard
# ---------------------------------------------------------------------------
def _should_skip(state: AuditState) -> bool:
    return bool(state.get("error_summary") or not state.get("transactions"))

# ----------------------------------------------------
# LangGraph Nodes
# ----------------------------------------------------

def structure_detector_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Structure Detector Node...")
    update = {"agent": "Structure Detector", "status": "running", "progress_pct": 10, "finding_count": 0}

    try:
        sheets = parse_file(state["file_path"])
        # For multi-sheet support, we run on the first sheet
        sheet_name = list(sheets.keys())[0]
        rows = sheets[sheet_name]

        # Load LLM Client
        llm = LLMClient()
        schema_map = detect_structure(rows, llm_client=llm)

        return {
            "schema_map": schema_map,
            # Store parsed rows so ingestion_node doesn't need to re-parse the file
            "raw_rows": rows,
            "status_updates": [
                update,
                {"agent": "Structure Detector", "status": "done", "progress_pct": 20, "finding_count": 0}
            ]
        }
    except Exception as e:
        err_msg = f"Structure Detector failed: {str(e)}"
        print(f"[Orchestrator] {err_msg}")
        return {
            "error_summary": err_msg,
            "status_updates": [
                update,
                {"agent": "Structure Detector", "status": "failed", "progress_pct": 20, "finding_count": 0, "error": str(e)}
            ]
        }

def ingestion_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Ingestion Node...")
    update = {"agent": "Ingestion Agent", "status": "running", "progress_pct": 25, "finding_count": 0}

    if state.get("error_summary"):
        return {
            "status_updates": [
                {"agent": "Ingestion Agent", "status": "skipped", "progress_pct": 30, "finding_count": 0}
            ]
        }

    try:
        # Reuse rows already parsed by structure_detector_node to avoid re-reading the file
        rows = state.get("raw_rows")
        if not rows:
            sheets = parse_file(state["file_path"])
            rows = sheets[list(sheets.keys())[0]]

        txns = ingest_transactions(rows, state["schema_map"])
        
        return {
            "transactions": txns,
            "status_updates": [
                update,
                {"agent": "Ingestion Agent", "status": "done", "progress_pct": 35, "finding_count": len(txns)}
            ]
        }
    except Exception as e:
        err_msg = f"Ingestion Agent failed: {str(e)}"
        print(f"[Orchestrator] {err_msg}")
        return {
            "error_summary": err_msg,
            "status_updates": [
                update,
                {"agent": "Ingestion Agent", "status": "failed", "progress_pct": 35, "finding_count": 0, "error": str(e)}
            ]
        }

def duplicates_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Duplicate Payment Detective Node...")
    update = {"agent": "Duplicate Payment Detective", "status": "running", "progress_pct": 40, "finding_count": 0}
    
    if _should_skip(state):
        return {"status_updates": [{"agent": "Duplicate Payment Detective", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
        
    try:
        dups = detect_duplicates(state["transactions"], state["duplicate_window_days"])
        return {
            "duplicates": dups,
            "status_updates": [
                update,
                {"agent": "Duplicate Payment Detective", "status": "done", "progress_pct": 60, "finding_count": len(dups)}
            ]
        }
    except Exception as e:
        err_msg = f"Duplicate Payment Detective failed: {str(e)}"
        print(f"[Orchestrator] {err_msg}")
        return {
            "duplicates": [],
            "status_updates": [
                update,
                {"agent": "Duplicate Payment Detective", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}
            ]
        }

def aging_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Aging & FIFO Settlement Node...")
    update = {"agent": "Aging & FIFO Settlement", "status": "running", "progress_pct": 40, "finding_count": 0}
    
    if _should_skip(state):
        return {"status_updates": [{"agent": "Aging & FIFO Settlement", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
        
    try:
        aging_res = calculate_aging_fifo(state["transactions"], state["as_on_date"])
        
        # Outstanding bills counts as findings
        out_bills_count = sum(len(a.outstanding_bills) for a in aging_res)
        
        return {
            "aging": aging_res,
            "status_updates": [
                update,
                {"agent": "Aging & FIFO Settlement", "status": "done", "progress_pct": 60, "finding_count": out_bills_count}
            ]
        }
    except Exception as e:
        err_msg = f"Aging & FIFO Settlement failed: {str(e)}"
        print(f"[Orchestrator] {err_msg}")
        return {
            "aging": [],
            "status_updates": [
                update,
                {"agent": "Aging & FIFO Settlement", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}
            ]
        }

def anomalies_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Anomaly Detection Node...")
    update = {"agent": "Anomaly Detection Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    
    if _should_skip(state):
        return {"status_updates": [{"agent": "Anomaly Detection Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
        
    try:
        anoms = detect_anomalies(state["transactions"], state["custom_holidays"])
        return {
            "anomalies": anoms,
            "status_updates": [
                update,
                {"agent": "Anomaly Detection Agent", "status": "done", "progress_pct": 60, "finding_count": len(anoms)}
            ]
        }
    except Exception as e:
        err_msg = f"Anomaly Detection Agent failed: {str(e)}"
        print(f"[Orchestrator] {err_msg}")
        return {
            "anomalies": [],
            "status_updates": [
                update,
                {"agent": "Anomaly Detection Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}
            ]
        }

def reconciliation_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Reconciliation Node...")
    update = {"agent": "Reconciliation Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    
    if _should_skip(state):
        return {"status_updates": [{"agent": "Reconciliation Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
        
    try:
        recs = reconcile_ledgers(state["transactions"])
        disc_count = sum(1 for r in recs if r.has_discrepancy)
        return {
            "reconciliation": recs,
            "status_updates": [
                update,
                {"agent": "Reconciliation Agent", "status": "done", "progress_pct": 60, "finding_count": disc_count}
            ]
        }
    except Exception as e:
        err_msg = f"Reconciliation Agent failed: {str(e)}"
        print(f"[Orchestrator] {err_msg}")
        return {
            "reconciliation": [],
            "status_updates": [
                update,
                {"agent": "Reconciliation Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}
            ]
        }

# ---------------------------------------------------------------------------
# Node 7: Benford's Law
# ---------------------------------------------------------------------------
def benfords_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Benford's Law Node...")
    update = {"agent": "Benford's Law Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    if _should_skip(state):
        return {"status_updates": [{"agent": "Benford's Law Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
    try:
        findings = detect_benfords_violations(state["transactions"])
        return {"benfords_findings": findings, "status_updates": [update, {"agent": "Benford's Law Agent", "status": "done", "progress_pct": 60, "finding_count": len(findings)}]}
    except Exception as e:
        print(f"[Orchestrator] Benford's Law Agent failed: {e}")
        return {"benfords_findings": [], "status_updates": [update, {"agent": "Benford's Law Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}]}


# ---------------------------------------------------------------------------
# Node 8: Statistical Outliers / Structuring
# ---------------------------------------------------------------------------
def zscore_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Z-Score Outlier Node...")
    update = {"agent": "Statistical Outlier Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    if _should_skip(state):
        return {"status_updates": [{"agent": "Statistical Outlier Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
    try:
        findings = detect_statistical_outliers(state["transactions"])
        return {"statistical_outliers": findings, "status_updates": [update, {"agent": "Statistical Outlier Agent", "status": "done", "progress_pct": 60, "finding_count": len(findings)}]}
    except Exception as e:
        print(f"[Orchestrator] Statistical Outlier Agent failed: {e}")
        return {"statistical_outliers": [], "status_updates": [update, {"agent": "Statistical Outlier Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}]}


# ---------------------------------------------------------------------------
# Node 9: Circular Fund Detection
# ---------------------------------------------------------------------------
def circular_fund_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Circular Fund Detection Node...")
    update = {"agent": "Circular Fund Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    if _should_skip(state):
        return {"status_updates": [{"agent": "Circular Fund Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
    try:
        findings = detect_circular_funds(state["transactions"])
        return {"circular_funds": findings, "status_updates": [update, {"agent": "Circular Fund Agent", "status": "done", "progress_pct": 60, "finding_count": len(findings)}]}
    except Exception as e:
        print(f"[Orchestrator] Circular Fund Agent failed: {e}")
        return {"circular_funds": [], "status_updates": [update, {"agent": "Circular Fund Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}]}


# ---------------------------------------------------------------------------
# Node 10: Temporal Pattern Detection
# ---------------------------------------------------------------------------
def temporal_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Temporal Pattern Node...")
    update = {"agent": "Temporal Pattern Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    if _should_skip(state):
        return {"status_updates": [{"agent": "Temporal Pattern Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
    try:
        findings = detect_temporal_patterns(state["transactions"])
        return {"temporal_patterns": findings, "status_updates": [update, {"agent": "Temporal Pattern Agent", "status": "done", "progress_pct": 60, "finding_count": len(findings)}]}
    except Exception as e:
        print(f"[Orchestrator] Temporal Pattern Agent failed: {e}")
        return {"temporal_patterns": [], "status_updates": [update, {"agent": "Temporal Pattern Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}]}


# ---------------------------------------------------------------------------
# Node 11: Bank Reconciliation
# ---------------------------------------------------------------------------
def bank_recon_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Bank Reconciliation Node...")
    update = {"agent": "Bank Reconciliation Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    if _should_skip(state):
        return {"status_updates": [{"agent": "Bank Reconciliation Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
    try:
        extra_files = state.get("extra_files") or []
        bank_file = next(
            (f["file_path"] for f in extra_files if f.get("ledger_type") == "BANK_STATEMENT"),
            None
        )
        if not bank_file:
            return {"bank_reconciliation": None, "bank_transactions": [], "status_updates": [update, {"agent": "Bank Reconciliation Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0, "message": "No bank statement uploaded"}]}
        summary = reconcile_with_bank(state["transactions"], bank_file)
        unmatched = (summary.gl_only_count + summary.bank_only_count) if summary else 0
        return {"bank_reconciliation": summary, "bank_transactions": [], "status_updates": [update, {"agent": "Bank Reconciliation Agent", "status": "done", "progress_pct": 60, "finding_count": unmatched}]}
    except Exception as e:
        print(f"[Orchestrator] Bank Reconciliation Agent failed: {e}")
        return {"bank_reconciliation": None, "bank_transactions": [], "status_updates": [update, {"agent": "Bank Reconciliation Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}]}


# ---------------------------------------------------------------------------
# Node 12: Expense Scrutiny
# ---------------------------------------------------------------------------
def expense_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Expense Scrutiny Node...")
    update = {"agent": "Expense Scrutiny Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    if _should_skip(state):
        return {"status_updates": [{"agent": "Expense Scrutiny Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
    try:
        findings = scrutinize_expenses(state["transactions"])
        return {"expense_scrutiny": findings, "status_updates": [update, {"agent": "Expense Scrutiny Agent", "status": "done", "progress_pct": 60, "finding_count": len(findings)}]}
    except Exception as e:
        print(f"[Orchestrator] Expense Scrutiny Agent failed: {e}")
        return {"expense_scrutiny": [], "status_updates": [update, {"agent": "Expense Scrutiny Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}]}


# ---------------------------------------------------------------------------
# Node 13: Sales Scrutiny
# ---------------------------------------------------------------------------
def sales_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Sales Scrutiny Node...")
    update = {"agent": "Sales Scrutiny Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    if _should_skip(state):
        return {"status_updates": [{"agent": "Sales Scrutiny Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
    try:
        findings = scrutinize_sales(state["transactions"], state.get("as_on_date"))
        return {"sales_scrutiny": findings, "status_updates": [update, {"agent": "Sales Scrutiny Agent", "status": "done", "progress_pct": 60, "finding_count": len(findings)}]}
    except Exception as e:
        print(f"[Orchestrator] Sales Scrutiny Agent failed: {e}")
        return {"sales_scrutiny": [], "status_updates": [update, {"agent": "Sales Scrutiny Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}]}


# ---------------------------------------------------------------------------
# Node 14: GST / TDS Compliance
# ---------------------------------------------------------------------------
def gst_tds_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running GST/TDS Compliance Node...")
    update = {"agent": "GST/TDS Compliance Agent", "status": "running", "progress_pct": 40, "finding_count": 0}
    if _should_skip(state):
        return {"status_updates": [{"agent": "GST/TDS Compliance Agent", "status": "skipped", "progress_pct": 60, "finding_count": 0}]}
    try:
        findings = detect_tds_gaps(state["transactions"])
        return {"gst_tds": findings, "status_updates": [update, {"agent": "GST/TDS Compliance Agent", "status": "done", "progress_pct": 60, "finding_count": len(findings)}]}
    except Exception as e:
        print(f"[Orchestrator] GST/TDS Compliance Agent failed: {e}")
        return {"gst_tds": [], "status_updates": [update, {"agent": "GST/TDS Compliance Agent", "status": "failed", "progress_pct": 60, "finding_count": 0, "error": str(e)}]}


# ---------------------------------------------------------------------------
# Node 15: Report Generator
# ---------------------------------------------------------------------------
def report_generator_node(state: AuditState) -> Dict[str, Any]:
    print("[Orchestrator] Running Report Generator Node...")
    update = {"agent": "Report Generator", "status": "running", "progress_pct": 85, "finding_count": 0}

    if state.get("error_summary"):
        return {"status_updates": [{"agent": "Report Generator", "status": "skipped", "progress_pct": 100, "finding_count": 0}]}

    try:
        out_dir = os.path.join(os.path.dirname(state["file_path"]), "outputs")
        os.makedirs(out_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(state["file_path"]))[0]
        excel_path = os.path.join(out_dir, f"{base_name}_forensic_report.xlsx")

        generate_excel_report(
            file_path=excel_path,
            duplicates=state.get("duplicates", []),
            aging=state.get("aging", []),
            anomalies=state.get("anomalies", []),
            reconciliation=state.get("reconciliation", []),
        )

        llm = LLMClient()
        if llm.is_configured():
            memo = generate_audit_memo_markdown(
                duplicates=state.get("duplicates", []),
                aging=state.get("aging", []),
                anomalies=state.get("anomalies", []),
                reconciliation=state.get("reconciliation", []),
                llm_client=llm,
            )
        else:
            memo = AuditMemoModel(
                scope="Audit scope covered transactions in ledger dump.",
                methodology="Recalculated running balances, checked holiday entries, ran duplicate payment patterns, and aged invoices.",
                key_findings=["LLM Client is not configured. Audit memo could not be generated dynamically."],
                risk_ratings={},
                recommendations=["Configure LLM_API_KEY in the environment to generate dynamic analysis memos."],
                raw_markdown="# Forensic Audit Memo\n*LLM API Key not provided. Dynamic memo generation skipped.*"
            )

        return {
            "excel_report_path": excel_path,
            "memo": memo,
            "status_updates": [update, {"agent": "Report Generator", "status": "done", "progress_pct": 100, "finding_count": 3}]
        }
    except Exception as e:
        err_msg = f"Report Generator failed: {str(e)}"
        print(f"[Orchestrator] {err_msg}")
        traceback.print_exc()
        return {
            "error_summary": err_msg,
            "status_updates": [update, {"agent": "Report Generator", "status": "failed", "progress_pct": 100, "finding_count": 0, "error": str(e)}]
        }


# ---------------------------------------------------------------------------
# LangGraph StateGraph Compilation
# ---------------------------------------------------------------------------
workflow = StateGraph(AuditState)

# Add Nodes
workflow.add_node("structure_detector", structure_detector_node)
workflow.add_node("ingestion", ingestion_node)
workflow.add_node("duplicates", duplicates_node)
workflow.add_node("aging", aging_node)
workflow.add_node("anomalies", anomalies_node)
workflow.add_node("reconciliation", reconciliation_node)
workflow.add_node("benfords", benfords_node)
workflow.add_node("zscore", zscore_node)
workflow.add_node("circular_fund", circular_fund_node)
workflow.add_node("temporal", temporal_node)
workflow.add_node("bank_recon", bank_recon_node)
workflow.add_node("expense", expense_node)
workflow.add_node("sales", sales_node)
workflow.add_node("gst_tds", gst_tds_node)
workflow.add_node("report_generator", report_generator_node)

# Sequential start
workflow.add_edge(START, "structure_detector")
workflow.add_edge("structure_detector", "ingestion")

# Fan-out from ingestion → 12 parallel analysis nodes
_ANALYSIS_NODES = [
    "duplicates", "aging", "anomalies", "reconciliation",
    "benfords", "zscore", "circular_fund", "temporal",
    "bank_recon", "expense", "sales", "gst_tds",
]
for _node in _ANALYSIS_NODES:
    workflow.add_edge("ingestion", _node)
    workflow.add_edge(_node, "report_generator")

workflow.add_edge("report_generator", END)

# Compile
audit_graph = workflow.compile()
