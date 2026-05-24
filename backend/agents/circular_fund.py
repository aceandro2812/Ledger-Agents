"""
Circular Fund Detection Agent

Builds a directed payment-flow graph from transaction contra_ledger fields
and searches for cycles (round-trips) of length 2 to 5.

A cycle means: Party A paid Party B, Party B paid Party C, Party C paid Party A
— a classic indicator of fund round-tripping, fictitious sales, or money-laundering.

Requires the `contra_ledger` field to be populated in NormalizedTransaction.
Falls back gracefully if contra data is sparse.
"""
import uuid
from decimal import Decimal
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from backend.models.schema import NormalizedTransaction, CircularFundFinding

MAX_CYCLE_LENGTH = 5
MIN_CYCLE_AMOUNT = Decimal("10000")  # Ignore cycles with total flow < Rs. 10,000


def _build_graph(transactions: List[NormalizedTransaction]) -> Dict[str, Dict[str, List[Dict]]]:
    """
    Builds a directed adjacency map: graph[from_party][to_party] = list of edge dicts.
    An edge exists when Party A has a Debit entry with contra_ledger = Party B,
    meaning A paid B (money left A and went to B).
    """
    graph: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))

    for t in transactions:
        if t.is_opening_bal or not t.contra_ledger:
            continue
        contra = t.contra_ledger.strip()
        if not contra or contra.lower() in ("", "none", "-"):
            continue

        if t.debit > 0:
            # A paid B (debit in A's ledger)
            graph[t.party][contra].append({
                "row_idx": t.row_idx,
                "date": str(t.date),
                "voucher_no": t.voucher_no,
                "amount": float(t.debit),
                "direction": f"{t.party} → {contra}",
            })
        # Note: credit in A's ledger means B paid A (graph[B][A]), but since we're
        # processing A's ledger here, skip credits to avoid double-counting.

    return graph


def _dfs_find_cycles(
    graph: Dict[str, Dict[str, List[Dict]]],
    start: str,
    current: str,
    path: List[str],
    visited: Set[str],
    all_cycles: List[List[str]],
    max_len: int,
):
    """DFS cycle finder. Records cycles when we return to `start`."""
    if len(path) > max_len:
        return

    for neighbor in graph.get(current, {}):
        if neighbor == start and len(path) >= 2:
            all_cycles.append(path + [start])
        elif neighbor not in visited:
            visited.add(neighbor)
            _dfs_find_cycles(graph, start, neighbor, path + [neighbor], visited, all_cycles, max_len)
            visited.discard(neighbor)


def _cycle_key(cycle: List[str]) -> frozenset:
    """Canonical key for a cycle (independent of starting point)."""
    return frozenset(cycle[:-1])


def detect_circular_funds(
    transactions: List[NormalizedTransaction],
) -> List[CircularFundFinding]:
    """
    Detects circular fund flows.
    Returns a list of CircularFundFinding — one per unique cycle.
    """
    # Check if contra_ledger data is present at all
    populated = sum(1 for t in transactions if t.contra_ledger and t.contra_ledger.strip())
    if populated < 10:
        # Not enough contra data for meaningful graph analysis
        return []

    graph = _build_graph(transactions)
    if not graph:
        return []

    seen_cycle_keys: Set[frozenset] = set()
    raw_cycles: List[List[str]] = []
    parties = list(graph.keys())

    for party in parties:
        cycles: List[List[str]] = []
        _dfs_find_cycles(graph, party, party, [party], {party}, cycles, MAX_CYCLE_LENGTH)
        for cycle in cycles:
            key = _cycle_key(cycle)
            if key not in seen_cycle_keys:
                seen_cycle_keys.add(key)
                raw_cycles.append(cycle)

    findings: List[CircularFundFinding] = []

    for cycle in raw_cycles:
        # Collect evidence (all edges along the cycle path)
        evidence: List[Dict] = []
        total_amount = Decimal("0.00")

        for i in range(len(cycle) - 1):
            from_p = cycle[i]
            to_p = cycle[i + 1]
            edges = graph.get(from_p, {}).get(to_p, [])
            for edge in edges:
                evidence.append(edge)
                total_amount += Decimal(str(edge["amount"]))

        if total_amount < MIN_CYCLE_AMOUNT:
            continue

        leg_count = len(cycle) - 1
        severity = "CRITICAL" if leg_count == 2 else ("HIGH" if leg_count <= 3 else "MEDIUM")

        cycle_str = " → ".join(cycle)
        findings.append(CircularFundFinding(
            finding_id=str(uuid.uuid4()),
            cycle_parties=cycle[:-1],  # Exclude the repeated start node
            leg_count=leg_count,
            total_amount=total_amount,
            evidence=evidence[:20],  # Cap evidence rows to keep JSON manageable
            severity=severity,
            description=(
                f"Circular fund flow detected: {cycle_str}. "
                f"Total amount in cycle: Rs. {float(total_amount):,.2f} across {leg_count} leg(s). "
                f"This pattern may indicate round-tripping, fictitious transactions, or "
                f"related-party fund rotation."
            ),
            recommendation=(
                f"Obtain supporting documentation (invoices, contracts, delivery records) for all "
                f"{leg_count} legs of this cycle. Verify commercial substance. "
                f"Cross-check with GST returns to confirm invoices exist. "
                f"Consider reporting to statutory auditor if substance is absent."
            ),
        ))

    # Sort by amount descending
    findings.sort(key=lambda f: f.total_amount, reverse=True)
    return findings
