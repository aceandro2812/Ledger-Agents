# User Navigation & Feature Guide

Welcome to the **Ledger Forensic Audit Engine** desktop suite! This guide outlines how to easily navigate the interface and utilize the forensic capabilities.

---

## 🧭 Application Structure & Navigation

The interface features a left-side navigation panel divided into three distinct operational sections. The sidebar is structured to let you choose your starting path immediately, depending on the files you have available.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Top Navbar (System Status)                      │
├──────────────────────┬─────────────────────────────────────────────────┤
│ Ingestion & Setup    │                                                 │
│  • Ingestion Page    │                                                 │
│                      │                                                 │
│ Ind. Workspaces      │                                                 │
│  • Creditors Audit   │                 Main Workspace                  │
│  • Bank Statement    │             (Tables, Graphs, KPIs)              │
│                      │                                                 │
│ General Ledger Suite │                                                 │
│  • Overview / KPI    │                                                 │
│  • Duplicates        │                                                 │
│  • Forensic Tools    │                                                 │
└──────────────────────┴─────────────────────────────────────────────────┘
```

---

## ⚡ Operational Flows

### 🚀 Flow A: Independent Workspaces (No General Ledger Required)
You can start using these tools immediately by uploading statements directly to their respective pages. They run fully independently.

#### 1. Bank Statement Analysis (`Bank Statement Analysis` tab)
*   **What it does:** Categorizes corporate bank statement deposits and withdrawals, detects bank types, and maps patterns.
*   **How to use:**
    1. Click the tab in the sidebar.
    2. Drag and drop your `.xlsx`, `.xlsm`, or `.csv` bank statement.
    3. The workspace will load interactive KPI cards (Total Deposits, Total Withdrawals, Net Cash Flow, and Transactions Count) along with a categorized ledger.
    4. **Filtering & Searching:** Use the search bar to locate specific narrations, filter by specific category dropdowns, or isolate Debits/Credits.
    5. **On-Screen Running Totals:** The KPI cards and the bottom **TOTALS** row update in real time to reflect the sums of the *currently filtered items* on screen.
    6. **Filtered Download:** Click **Download Categorized CSV**. It generates a customized sheet containing only your filtered items, appending a summary spacer and a final totals row matching the on-screen totals.

#### 2. Creditors (AP) Audit (`Creditors (AP) Audit` tab)
*   **What it does:** Runs pattern scans, invoice timing validations, and payment flow checks on your accounts payable ledger.
*   **How to use:** Drop your Creditors file directly to perform validation checks without having to process a general ledger first.

---

### 🔍 Flow B: General Ledger Suite (Requires General Ledger/Debtors Upload)
This is the complete forensic audit pipeline. It checks compliance, fraud, mathematical reconciliation, and generates a formal observation memo.

#### 1. Ingestion & Setup (`Upload & Ingestion` tab)
*   Go to **Upload & Ingestion**, choose your General Ledger workbook, specify target columns, and start the local ingestion runner.
*   Once processing completes, all pages in the **General Ledger Suite** will automatically unlock.

#### 2. General Ledger Suite Modules
*   **Overview Dashboard:** High-level summary of findings, transaction counts, and compliance statuses.
*   **Duplicate Payments:** Flags identical transactions, fuzzy matches within 1%, same-day/same-amount transactions, and round number references.
*   **Forensic Anomalies:** Runs checks against 10 risk vectors, including holiday transactions, round-trip transactions, split payments bypassing approval limits, and user concentrations.
*   **Aging (AR) Schedule:** Groups receivables chronologically in standard FIFO buckets (0-30, 31-60, 61-90 days, etc.).
*   **Benford's Law & Statistical Outliers:** Mathematical frequency analysis of leading digits and statistical outliers to identify anomalous journal entries.
*   **Circular Funds:** Scans for round-trip transactions and transfer loops.
*   **CA Observations Memo:** Automatically generates a formatted draft of standard observations, counts, and findings for review.

---

## ⚙️ Configuration & Key Setup

To enable CA Observation Memo generation and AI-assisted categorization, configure your LLM Provider settings:
1. Click the **Gear Icon** (Settings) in the top-right corner.
2. Enter your API keys and select your model provider (e.g. OpenAI, Anthropic, Gemini, etc.).
3. Click **Save Settings**.
