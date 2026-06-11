# Ledger Agents Handoff

Generated from the 2026-06-07 session.

## Summary

This session completed the creditors split work on top of the forensic audit app, fixed the stale SQLite schema problem that was causing `extra_files_json` insert failures, and uncovered one remaining compatibility bug in the report generator.

The important outcome is that creditors are now treated as a separate upload path and a separate results page, instead of being mixed into the generic attachment flow.

## What Was Built

### 1. Dedicated creditors page

A new frontend page was added at `frontend/src/pages/CreditorsLedger.jsx`.

What it does:
- Reads creditor-related aging data from `results.aging`
- Filters to records marked as creditors using the new `is_creditor` flag
- Falls back to a heuristic if older results do not contain `is_creditor`
- Shows AP-focused KPIs:
  - total AP outstanding
  - overdue AP over 30 days
  - critical overdue AP over 180 days
  - largest vendor
- Shows warning pills for:
  - zero-payment vendors
  - unsettled opening balances
- Renders a sortable AP aging table with bucket columns:
  - `0-30`
  - `31-60`
  - `61-90`
  - `91-180`
  - `181-365`
  - `>365`
- Includes a clear empty state that tells the user to upload a creditors ledger through the dedicated upload path

Why this matters:
- Creditors/AP analysis is now a first-class workflow, not just another ledger type hidden inside generic attachment logic
- The page is ready for future AP drill-downs, vendor-level investigation, or dedicated export features

### 2. Upload flow split into creditors + generic attachments

`frontend/src/pages/Upload.jsx` was updated so creditors are handled separately from the rest of the additional files.

What changed:
- `CREDITORS_LEDGER` was removed from the generic dropdown list
- A dedicated purple creditors section was added with a strong visual distinction
- The creditors section uses a fixed `ledger_type=CREDITORS_LEDGER`
- Generic attachments remain available for:
  - bank statement
  - debtors ledger
  - sales ledger
  - expense ledger
- The upload experience now looks like this:
  - primary audit file upload
  - dedicated creditors ledger upload
  - optional additional attachments
  - start audit

Why this matters:
- It makes creditors obvious to the user
- It reduces confusion over whether AP data belongs in the generic file picker
- It gives the next agent a clean place to add more AP-specific behavior later

### 3. Results navigation updated

`frontend/src/App.jsx` was updated to include a dedicated `Creditors (AP)` tab in the results sidebar.

Navigation now includes:
- Overview Dashboard
- Duplicate Payments
- Forensic Anomalies
- Aging Schedule
- Creditors (AP)
- Benford's Law
- Statistical Outliers
- Circular Funds
- Temporal Patterns
- Bank Reconciliation
- Expense Scrutiny
- Sales Scrutiny
- GST/TDS Compliance
- CA Observations Memo

Why this matters:
- Creditors/AP results are now discoverable from the main audit results view
- Users do not have to infer that AP content lives inside the generic Aging page

### 4. Aging model now exposes creditor/debtor type

`backend/models/schema.py` and `backend/agents/aging_fifo.py` were updated.

Backend changes:
- `PartyAgingSummary` now has an `is_creditor: bool` field
- `aging_fifo.py` already knew whether a party was creditor or debtor; that state is now included in the output summary

Why this matters:
- Frontend pages can now distinguish AP from AR cleanly
- Future backend logic can branch on the same flag without re-inferring the direction from balances

### 5. SQLite schema issue was fixed operationally

There was a runtime error earlier in the session:
- `sqlite3.OperationalError: table audits has no column named extra_files_json`

Root cause:
- The backend process was stale and using the old model state
- The db file had been deleted, but the running server had not been fully restarted from a clean state
- The database path is relative, so startup directory matters

What fixed it:
- Stale `uvicorn` / Python backend processes were killed
- `backend/**/__pycache__` was cleared
- The backend was restarted from the repository root
- The db schema was rechecked and the `audits` table now includes `extra_files_json`

Important operational note:
- `DATABASE_URL = "sqlite:///forensic_audit.db"` is relative to the current working directory
- The backend should be started from the repo root, not from inside `backend/`, unless the team intentionally wants the db file somewhere else

## Validation Already Done

The following checks were completed successfully:
- `get_errors` on the changed frontend files returned no errors
- A fresh schema inspection of `forensic_audit.db` showed the `audits` table columns:
  - `id`
  - `filename`
  - `file_path`
  - `status`
  - `created_at`
  - `results_json`
  - `extra_files_json`
- Backend startup logs showed:
  - `[Server] SQLite Database Initialized.`

## Current State Of The Codebase

### Working frontend pieces

The new or updated frontend files are:
- `frontend/src/pages/CreditorsLedger.jsx`
- `frontend/src/pages/Upload.jsx`
- `frontend/src/App.jsx`

The earlier pages from the same workstream are still relevant and already present:
- `frontend/src/pages/SalesScrutiny.jsx`
- `frontend/src/pages/GSTCompliance.jsx`
- `frontend/src/pages/BenfordsLaw.jsx`
- `frontend/src/pages/StatisticalOutliers.jsx`
- `frontend/src/pages/CircularFunds.jsx`
- `frontend/src/pages/TemporalPatterns.jsx`
- `frontend/src/pages/BankReconciliation.jsx`
- `frontend/src/pages/ExpenseScrutiny.jsx`

### Working backend pieces

The backend files updated in this creditors split are:
- `backend/models/schema.py`
- `backend/agents/aging_fifo.py`

Other relevant backend files from the same session are still part of the contract:
- `backend/main.py`
- `backend/orchestrator.py`
- `backend/utils/db.py`

## Data Contract For The New Pages

The frontend pages now expect these result fields:
- `results.aging` for the AP/AR aging page and the new creditors page
- `results.gst_tds` for GST/TDS compliance
- `results.sales_scrutiny` for sales scrutiny
- `results.expense_scrutiny` for expense scrutiny
- `results.circular_funds` for circular fund detection
- `results.temporal_patterns` for temporal anomaly detection
- `results.bank_reconciliation` for GL vs bank matching
- `results.benfords_findings` for Benford analysis
- `results.statistical_outliers` for Z-score / outlier detection

Creditors page-specific behavior:
- If `results.aging[i].is_creditor` exists, the page uses it directly
- If older result payloads do not contain the flag, the page falls back to a heuristic based on totals and outstanding balance

## Remaining Blocker

There is still one active runtime compatibility bug to fix next.

Observed failure:
- `backend/agents/report_generator.py` crashes in the template memo fallback because it tries to read aging fields that no longer exist on `PartyAgingSummary`

Old field names still referenced in the fallback:
- `bucket_91_180`
- `bucket_181_365`
- `bucket_over_365`

Why it fails:
- `PartyAgingSummary` now stores aging data in `aging_buckets`
- The report generator still expects legacy attributes from an older model shape

Where to look:
- `backend/agents/report_generator.py`
- `backend/models/schema.py`

Best fix options:
- Add compatibility properties to `PartyAgingSummary` so the old field names still resolve
- Or refactor the report generator to read from `aging_buckets` directly

Recommended next step:
1. Search for every `bucket_` reference in the backend
2. Update the report generator to use the current model shape
3. Re-run a full upload and audit cycle
4. Confirm memo generation no longer fails on the fallback path

## Suggested Follow-Up Work

If the next agent continues immediately, the best order is:
1. Fix report generator compatibility
2. Re-run an audit with a creditors attachment
3. Verify the results view opens the new `Creditors (AP)` tab correctly
4. Confirm the AP aging table only shows creditors
5. Add a drill-down or export if the creditors page needs more depth

## Useful Run Commands

Backend from repo root:
- `backend/venv/Scripts/uvicorn.exe backend.main:app --reload --port 8000`

Frontend dev server:
- `cd frontend && npm run dev`

If schema problems come back:
- delete `forensic_audit.db` at the repo root
- clear `backend/**/__pycache__`
- restart the backend from the repo root

## Session Takeaway

The creditors split is now real in the product:
- separate upload path
- separate results page
- backend model support for creditor/debtor classification

The next engineering task is not UI work, it is compatibility cleanup in the report generator so the new aging model shape does not crash the memo fallback.
