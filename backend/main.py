import os
import uuid
import json
import shutil
import asyncio
import datetime as dt
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List

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

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from decimal import Decimal
from backend.utils.db import init_db, get_db, AuditRecord, SessionLocal
from backend.orchestrator import audit_graph
from backend.models.schema import AuditSessionState
from backend.utils.date_utils import parse_date
from backend.utils.config import read_config, write_config, is_llm_configured, get_llm_settings

app = FastAPI(title="GL Ledger Forensic Audit API")

# Enable CORS for desktop/local operation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
def startup_event():
    # Initialize the local SQLite database
    init_db()
    print("[Server] SQLite Database Initialized.")

@app.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts ledger Excel/CSV file upload and initializes a queued audit record.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".xlsx", ".xlsm", ".csv"):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file extension. Please upload an Excel (.xlsx, .xlsm) or CSV (.csv) file."
        )
        
    audit_id = str(uuid.uuid4())
    local_path = os.path.join(UPLOAD_DIR, f"{audit_id}{ext}")
    
    # Save uploaded file locally
    try:
        with open(local_path, "wb") as f:
            f.write(file.file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # Create DB entry
    record = AuditRecord(
        id=audit_id,
        filename=filename,
        file_path=local_path,
        status="queued"
    )
    db.add(record)
    db.commit()
    
    return {"audit_id": audit_id, "filename": filename}


@app.post("/audit/{audit_id}/attach")
async def attach_file(
    audit_id: str,
    file: UploadFile = File(...),
    ledger_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Attach an additional file (bank statement, secondary ledger) to an existing audit session.
    Must be called after /upload and before /audit/{id}/stream.
    ledger_type: BANK_STATEMENT | DEBTORS_LEDGER | CREDITORS_LEDGER | SALES_LEDGER | EXPENSE_LEDGER
    """
    record = db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Audit session not found.")

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".xlsx", ".xlsm", ".csv"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file extension. Please upload an Excel (.xlsx, .xlsm) or CSV (.csv) file."
        )

    dest = os.path.join(UPLOAD_DIR, f"{audit_id}_{ledger_type}_{filename}")
    try:
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save attached file: {str(e)}")

    existing = json.loads(record.extra_files_json or "[]")
    # Replace any existing entry with the same ledger_type to avoid duplicates
    existing = [e for e in existing if e.get("ledger_type") != ledger_type]
    existing.append({"file_path": dest, "ledger_type": ledger_type})
    record.extra_files_json = json.dumps(existing)
    db.commit()

    return {"status": "attached", "ledger_type": ledger_type, "file_path": dest}


@app.get("/audit/{audit_id}/stream")
async def stream_audit(
    audit_id: str,
    as_on_date: Optional[str] = None,
    currency_symbol: str = "Rs.",
    duplicate_window_days: int = 7,
    custom_holidays: Optional[str] = None, # JSON-serialized list of dates
    db: Session = Depends(get_db)
):
    """
    SSE Endpoint that executes the LangGraph audit workflow and streams status updates.
    """
    record = db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Audit session not found.")
        
    record.status = "running"
    db.commit()
    
    # Eagerly capture values from the model before Session is detached/closed
    file_path = record.file_path
    extra_files = json.loads(record.extra_files_json or "[]")
    holidays_list = []
    if custom_holidays:
        try:
            holidays_list = json.loads(custom_holidays)
        except Exception:
            pass
            
    # Parse as_on_date
    as_on_dt = None
    if as_on_date:
        as_on_dt = parse_date(as_on_date)

    async def sse_generator():
        # Setup starting state for LangGraph
        initial_state = {
            "file_path": file_path,
            "as_on_date": as_on_dt,
            "currency_symbol": currency_symbol,
            "duplicate_window_days": duplicate_window_days,
            "custom_holidays": holidays_list,
            "extra_files": extra_files,
            "status_updates": [],
            "raw_rows": None,
            "schema_map": None,
            "transactions": [],
            "duplicates": [],
            "aging": [],
            "anomalies": [],
            "reconciliation": [],
            "benfords_findings": [],
            "statistical_outliers": [],
            "circular_funds": [],
            "temporal_patterns": [],
            "bank_transactions": [],
            "bank_reconciliation": None,
            "expense_scrutiny": [],
            "sales_scrutiny": [],
            "gst_tds": [],
            "memo": None,
            "excel_report_path": None,
            "error_summary": None
        }

        loop = asyncio.get_running_loop()
        # Queue carries tuples: ("update", dict) | ("done", final_state_dict) | ("error", str)
        queue: asyncio.Queue = asyncio.Queue()

        def run_graph_in_thread():
            """
            Runs the synchronous LangGraph stream in a background thread so the
            asyncio event loop stays free to flush SSE bytes to the client.
            """
            accumulated = dict(initial_state)
            try:
                for chunk in audit_graph.stream(initial_state):
                    for node_name, node_state in chunk.items():
                        accumulated.update(node_state)
                        for update in node_state.get("status_updates", []):
                            loop.call_soon_threadsafe(queue.put_nowait, ("update", update))
                loop.call_soon_threadsafe(queue.put_nowait, ("done", accumulated))
            except Exception as exc:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    ("error", str(exc), traceback.format_exc())
                )

        # Launch graph in thread pool — does NOT block the event loop
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="audit_graph")
        graph_future = loop.run_in_executor(executor, run_graph_in_thread)

        final_state = None
        error_msg = None

        # Drain the queue, yielding SSE events as each node finishes
        while True:
            item = await queue.get()
            kind = item[0]

            if kind == "update":
                update = item[1]
                yield f"data: {json.dumps(update)}\n\n"

            elif kind == "done":
                final_state = item[1]
                break

            elif kind == "error":
                error_msg = item[1]
                tb = item[2] if len(item) > 2 else ""
                print(f"[SSE] Graph thread error:\n{tb}")
                break

        # Ensure the thread has fully exited before DB writes
        try:
            await graph_future
        except Exception as exc:
            if error_msg is None:
                error_msg = str(exc)

        class CustomEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (dt.date, dt.datetime)):
                    return obj.isoformat()
                if isinstance(obj, Decimal):
                    return float(obj)
                return super().default(obj)

        if error_msg:
            with SessionLocal() as bg_db:
                bg_record = bg_db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
                if bg_record:
                    bg_record.status = "failed"
                    bg_db.commit()
            yield f"data: {json.dumps({'agent': 'Orchestrator', 'status': 'failed', 'progress_pct': 100, 'finding_count': 0, 'error': error_msg})}\n\n"
            return

        if final_state and not final_state.get("error_summary"):
            results = {
                "schema_map": final_state["schema_map"].model_dump() if final_state["schema_map"] else None,
                "duplicates": [d.model_dump() for d in final_state.get("duplicates", [])],
                "aging": [a.model_dump() for a in final_state.get("aging", [])],
                "anomalies": [a.model_dump() for a in final_state.get("anomalies", [])],
                "reconciliation": [r.model_dump() for r in final_state.get("reconciliation", [])],
                "benfords_findings": [f.model_dump() for f in final_state.get("benfords_findings", [])],
                "statistical_outliers": [f.model_dump() for f in final_state.get("statistical_outliers", [])],
                "circular_funds": [f.model_dump() for f in final_state.get("circular_funds", [])],
                "temporal_patterns": [f.model_dump() for f in final_state.get("temporal_patterns", [])],
                "bank_reconciliation": final_state["bank_reconciliation"].model_dump() if final_state.get("bank_reconciliation") else None,
                "expense_scrutiny": [f.model_dump() for f in final_state.get("expense_scrutiny", [])],
                "sales_scrutiny": [f.model_dump() for f in final_state.get("sales_scrutiny", [])],
                "gst_tds": [f.model_dump() for f in final_state.get("gst_tds", [])],
                "memo": final_state["memo"].model_dump() if final_state.get("memo") else None,
                "excel_report_path": final_state.get("excel_report_path")
            }
            with SessionLocal() as bg_db:
                bg_record = bg_db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
                if bg_record:
                    bg_record.status = "completed"
                    bg_record.results_json = json.dumps(results, cls=CustomEncoder)
                    bg_db.commit()
            yield f"data: {json.dumps({'agent': 'Orchestrator', 'status': 'completed', 'progress_pct': 100, 'finding_count': 0})}\n\n"
        else:
            err = (final_state or {}).get("error_summary", "Unknown error") if final_state else "Graph returned no state"
            with SessionLocal() as bg_db:
                bg_record = bg_db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
                if bg_record:
                    bg_record.status = "failed"
                    bg_db.commit()
            yield f"data: {json.dumps({'agent': 'Orchestrator', 'status': 'failed', 'progress_pct': 100, 'finding_count': 0, 'error': err})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@app.get("/audits")
def list_audits(db: Session = Depends(get_db)):
    """
    Returns lists of all past audits.
    """
    records = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        }
        for r in records
    ]

@app.get("/audit/{audit_id}")
def get_audit_details(audit_id: str, db: Session = Depends(get_db)):
    """
    Returns parsed transaction audit details.
    """
    record = db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Audit record not found.")
        
    if record.status != "completed":
        return {"status": record.status, "filename": record.filename}
        
    try:
        results = json.loads(record.results_json)
        return {
            "id": record.id,
            "filename": record.filename,
            "status": record.status,
            "created_at": record.created_at.isoformat(),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load audit findings: {str(e)}")

@app.get("/audit/{audit_id}/excel")
def download_excel_report(audit_id: str, db: Session = Depends(get_db)):
    """
    Downloads the styled openpyxl Excel spreadsheet generated during audit.
    """
    record = db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
    if not record or record.status != "completed":
        raise HTTPException(status_code=404, detail="Audit not completed or record not found.")
        
    try:
        results = json.loads(record.results_json)
        excel_path = results.get("excel_report_path")
        if not excel_path or not os.path.exists(excel_path):
            raise HTTPException(status_code=404, detail="Excel report file not found on disk.")
            
        return FileResponse(
            path=excel_path, 
            filename=f"Forensic_Audit_Report_{record.filename.split('.')[0]}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving Excel report: {str(e)}")

# ---------------------------------------------------------------------------
# Settings Endpoints
# ---------------------------------------------------------------------------

@app.get("/settings/status")
def settings_status():
    """
    Returns whether the LLM API key has been configured.
    Used by the frontend to decide whether to show the Settings page on startup.
    """
    configured = is_llm_configured()
    if configured:
        cfg = get_llm_settings()
        return {
            "configured": True,
            "model": cfg["model"],
            "has_base_url": bool(cfg["base_url"])
        }
    return {"configured": False, "model": "", "has_base_url": False}

@app.get("/settings")
def get_settings():
    """
    Returns current LLM configuration (API key is masked for security).
    """
    cfg = get_llm_settings()
    api_key = cfg["api_key"]
    # Mask key: show only first 8 chars + asterisks
    masked = ""
    if api_key:
        masked = api_key[:8] + "*" * max(0, len(api_key) - 8)
    return {
        "api_key_masked": masked,
        "api_key_configured": bool(api_key),
        "model": cfg["model"],
        "base_url": cfg["base_url"]
    }

from pydantic import BaseModel as pydantic_BaseModel

class SettingsPayload(pydantic_BaseModel):
    api_key: str
    model: str
    base_url: str = ""

@app.post("/settings")
def save_settings(payload: SettingsPayload):
    """
    Saves LLM configuration to the local config.json file.
    Handles masked keys by preserving the original saved key.
    """
    if not payload.api_key or not payload.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    if not payload.model or not payload.model.strip():
        raise HTTPException(status_code=400, detail="Model name cannot be empty.")
        
    api_key = payload.api_key.strip()
    if "*" in api_key:
        saved_cfg = get_llm_settings()
        if saved_cfg["api_key"]:
            api_key = saved_cfg["api_key"]
        else:
            raise HTTPException(status_code=400, detail="Invalid API key format.")
            
    try:
        write_config({
            "llm_api_key": api_key,
            "llm_model": payload.model.strip(),
            "llm_base_url": payload.base_url.strip()
        })
        return {"success": True, "message": "Settings saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.post("/settings/test")
def test_llm_connection(payload: SettingsPayload):
    """
    Sends a minimal test ping to the specified LLM using the provided settings.
    Allows testing before saving. Handles masked API keys by restoring the saved key.
    """
    api_key = payload.api_key.strip()
    
    # Debug logging to trace key resolution issues
    print(f"[DEBUG Settings Test] Received api_key from frontend (len={len(api_key)}): '{api_key[:10]}...{api_key[-4:] if len(api_key) > 4 else ''}'")
    
    # If the user didn't modify the key, it will be the masked one from the frontend.
    if "*" in api_key:
        saved_cfg = get_llm_settings()
        print(f"[DEBUG Settings Test] Resolving masked key against saved config key (len={len(saved_cfg.get('api_key', ''))}): '{saved_cfg.get('api_key', '')[:10]}...'")
        if saved_cfg["api_key"]:
            api_key = saved_cfg["api_key"]
        else:
            raise HTTPException(status_code=400, detail="Invalid API key format.")
            
    print(f"[DEBUG Settings Test] Final API key used (len={len(api_key)}): '{api_key[:10]}...{api_key[-4:] if len(api_key) > 4 else ''}'")
    print(f"[DEBUG Settings Test] Model: '{payload.model.strip()}'")
    print(f"[DEBUG Settings Test] Base URL: '{payload.base_url.strip()}'")

    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    if not payload.model.strip():
        raise HTTPException(status_code=400, detail="Model name cannot be empty.")

    try:
        import litellm
        litellm.set_verbose = True  # Enable debugging logs in the terminal
        
        response = litellm.completion(
            model=payload.model.strip(),
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
            api_key=api_key,
            **(({"base_url": payload.base_url.strip()}) if payload.base_url.strip() else {})
        )
        reply = response.choices[0].message.content or ""
        return {"success": True, "reply": reply.strip(), "model": payload.model.strip()}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"LLM connection test failed: {str(e)}")

@app.post("/analyze/bank-statement")
def analyze_bank_statement_endpoint(
    file: UploadFile = File(...)
):
    """
    Directly parse and categorize a bank statement without requiring a primary GL ledger.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".xlsx", ".xlsm", ".csv"):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file extension. Please upload an Excel (.xlsx, .xlsm) or CSV (.csv) file."
        )
    
    # Save file
    audit_id = str(uuid.uuid4())
    local_path = os.path.join(UPLOAD_DIR, f"{audit_id}_BS{ext}")
    try:
        with open(local_path, "wb") as f:
            f.write(file.file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save bank statement: {str(e)}")
        
    try:
        from backend.utils.bank_parser import parse_bank_statement
        bank_name, transactions = parse_bank_statement(local_path)
        
        # Calculate summary metrics
        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")
        category_summary = {}
        txns_list = []
        
        for t in transactions:
            total_debits += t.debit
            total_credits += t.credit
            cat = t.category or "Uncategorized"
            category_summary[cat] = category_summary.get(cat, Decimal("0.00")) + (t.debit if t.debit > 0 else t.credit)
            
            txns_list.append({
                "row_idx": t.row_idx,
                "date": t.date.isoformat(),
                "narration": t.narration,
                "debit": float(t.debit),
                "credit": float(t.credit),
                "balance": float(t.balance) if t.balance is not None else None,
                "ref_no": t.ref_no,
                "bank_name": t.bank_name,
                "category": cat
            })
            
        # Format categories summary
        cat_summary_float = {k: float(v) for k, v in category_summary.items()}
        
        results = {
            "bank_name": bank_name,
            "filename": filename,
            "total_transactions": len(transactions),
            "total_debits": float(total_debits),
            "total_credits": float(total_credits),
            "category_summary": cat_summary_float,
            "transactions": txns_list
        }
        
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Bank statement analysis failed: {str(e)}")

@app.post("/analyze/creditors")
def analyze_creditors_endpoint(
    file: UploadFile = File(...),
    as_on_date: Optional[str] = None
):
    """
    Directly parse and calculate aging for a creditors ledger.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".xlsx", ".xlsm", ".csv"):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file extension. Please upload an Excel (.xlsx, .xlsm) or CSV (.csv) file."
        )
    
    # Save file
    audit_id = str(uuid.uuid4())
    local_path = os.path.join(UPLOAD_DIR, f"{audit_id}_CR{ext}")
    try:
        with open(local_path, "wb") as f:
            f.write(file.file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save creditors ledger: {str(e)}")
        
    try:
        from backend.utils.excel_parser import parse_file
        from backend.agents.structure_detector import detect_structure
        from backend.agents.ingestion import ingest_transactions
        from backend.agents.aging_fifo import calculate_aging_fifo
        from backend.utils.llm import LLMClient
        from backend.models.schema import PartyAgingSummary
        
        # 1. Parse spreadsheet rows
        sheets = parse_file(local_path)
        if not sheets:
            raise HTTPException(status_code=400, detail="The uploaded spreadsheet contains no worksheets.")
        sheet_name = list(sheets.keys())[0]
        rows = sheets[sheet_name]
        
        # 2. Detect schema
        llm = LLMClient()
        schema_map = detect_structure(rows, llm_client=llm)
        
        # 3. Ingest transactions
        txns = ingest_transactions(rows, schema_map)
        
        # 4. Calculate aging
        as_on_dt = None
        if as_on_date:
            from backend.utils.date_utils import parse_date
            as_on_dt = parse_date(as_on_date)
            
        aging_res = calculate_aging_fifo(txns, as_on_dt)
        
        # Force is_creditor = True for the results since this is a creditors ledger
        aging_dict_list = []
        for a in aging_res:
            a.is_creditor = True
            aging_dict_list.append(a.model_dump())
            
        return {
            "aging": aging_dict_list
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Creditors analysis failed: {str(e)}")

# Serve frontend static assets from the React dist folder if it exists
import sys
from fastapi.staticfiles import StaticFiles
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if not os.path.exists(frontend_dist):
    if getattr(sys, 'frozen', False):
        frontend_dist = os.path.join(sys._MEIPASS, "dist")
    else:
        frontend_dist = "dist"

if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")


