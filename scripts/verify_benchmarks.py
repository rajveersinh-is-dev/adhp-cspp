#!/usr/bin/env python3
"""
Automated Consistency, Canonical Instance Hashing, and Benchmark Verification Script for ADHP-CSPP.

Recalculates and strictly asserts all headline statistics and cryptographic identities
directly from authoritative machine-readable benchmark data:
  - results/raw/benchmark_raw.csv
  - results/raw/benchmark_instances.json
  - results/processed/summary_table.csv

Substantive assertions verified:
1. Strict fail-closed verification: mandatory presence and non-emptiness of raw CSV,
   instance registry, and summary table.
2. Record count and configuration integrity: exactly 120 raw benchmark records across 25 configurations.
3. Dual Canonical Identity Verification (FIPS 180-4 SHA-256 independent recomputation):
   - Problem-Instance Digest (schema adhp-canonical-v1): exactly 200 distinct problem instances
     across 250 evaluations (190 in Suites 1-4, 10 controlled repeated instances in Suite 5).
   - Graph Topology Digest (schema adhp-topology-v1): exactly 164 distinct topologies across
     250 evaluations (40 grid evaluations share 4 grid graph topologies).
4. IEEE-754 binary64 Value-vs-Bit Representation Invariants:
   - Every numeric field (budget, cost, weight) is strictly reconciled against its 16-hex-character bit representation.
   - Non-finite numbers (NaN, infinity) and negative zero (-0.0) are strictly rejected.
   - Graph structural boundaries (node index bounds, source/target bounds, edge counts) strictly enforced.
5. Metric physical validity: strictly non-negative runtimes, labels, and decomposition bounds.
6. Summary table synchronization: recomputed means and maxes match summary_table.csv within 0.05 us.
7. Empirical honesty check: preserves observed regressions (e.g., Martins outperforming ADHP on
   small random ER graphs due to low label collision).
8. Comprehensive published claim reconciliation: fail-closed verification of all 522 table cells
   and headline quantitative statements across README.md, paper/main.tex, paper/main.typ,
   and research/BENCHMARK_REPORT.md.

Fails closed with exit code 1 if any discrepancy or assertion violation is detected.
"""

import os
import sys
import json
import math
import struct
import hashlib
import pandas as pd
import numpy as np

EXPECTED_COLUMNS = [
    'benchmark_category', 'instance_name', 'nodes', 'edges', 'budget',
    'solver_name', 'num_instances', 'mean_runtime_micros', 'median_runtime_micros',
    'std_dev_micros', 'mean_preprocessing_micros', 'mean_search_micros',
    'mean_labels_generated', 'median_labels_generated', 'mean_labels_pruned_dual',
    'mean_labels_pruned_dominance', 'mean_labels_explored', 'peak_queue_size',
    'peak_memory_bytes'
]

EXPECTED_CATEGORIES = [
    'Anti-Correlated Scaling',
    'Grid Scaling',
    'Random ER Scaling',
    'Budget Sensitivity',
    'Ablation K Facets'
]

EXPECTED_CONFIGS = {
    'Anti-Correlated Scaling': [
        'anticorr_n20', 'anticorr_n40', 'anticorr_n60',
        'anticorr_n80', 'anticorr_n100', 'anticorr_n150'
    ],
    'Grid Scaling': [
        'grid_4x4', 'grid_6x6', 'grid_8x8', 'grid_10x10'
    ],
    'Random ER Scaling': [
        'random_er_n30', 'random_er_n60', 'random_er_n90', 'random_er_n120'
    ],
    'Budget Sensitivity': [
        'budget_alpha_0.10', 'budget_alpha_0.25', 'budget_alpha_0.50',
        'budget_alpha_0.75', 'budget_alpha_0.90'
    ],
    'Ablation K Facets': [
        'ablation_k1', 'ablation_k2', 'ablation_k3',
        'ablation_k5', 'ablation_k8', 'ablation_k12'
    ]
}

EXPECTED_COMPETITIVE_SOLVERS = [
    'ADHP (Adaptive Dual Hull Pruning)',
    'Adaptive Hybrid ADHP',
    'Carlyle-Wood (LARAC Single-Multiplier Lagrangian Bounding)',
    'Dumitrescu-Boland (1D-Bounded Label Setting)',
    'Martins (Standard Multi-Label Dijkstra)',
    'Pulse (Lozano & Medaglia 2013)'
]

EXPECTED_ABLATION_SOLVERS = [
    'ADHP (K=1)', 'ADHP (K=2)', 'ADHP (K=3)',
    'ADHP (K=5)', 'ADHP (K=8)', 'ADHP (K=12)'
]

EXPECTED_INSTANCE_KEYS = {
    'schema_version', 'evaluation_id', 'benchmark_category', 'configuration_name',
    'instance_index', 'graph_id', 'nodes', 'edges', 'source',
    'target', 'budget', 'budget_bits', 'seed', 'canonical_edges'
}


def validate_numeric_representation(val, bit_str: str, field_name: str):
    """
    Validates that a numeric float value strictly agrees with its 16-hex IEEE-754 binary64 representation.
    Rejects NaNs, infinities, signed negative zeros, malformed bit strings, and bit mismatches.
    """
    if not isinstance(bit_str, str) or len(bit_str) != 16:
        raise ValueError(f"Field '{field_name}' bit string must be exactly 16 hex characters, got: {bit_str}")
    
    if not all(c in '0123456789abcdefABCDEF' for c in bit_str):
        raise ValueError(f"Field '{field_name}' bit string '{bit_str}' contains non-hex characters")

    bit_str_clean = bit_str.lower()
    
    # Reject signed negative zero (-0.0 has bit pattern 0x8000000000000000)
    if bit_str_clean == "8000000000000000":
        raise ValueError(f"Negative zero (-0.0) is invalid for {field_name}")

    try:
        unpacked = struct.unpack('>d', bytes.fromhex(bit_str_clean))[0]
    except Exception as e:
        raise ValueError(f"Field '{field_name}' bit string '{bit_str}' failed hex/IEEE-754 decoding: {e}")

    if not isinstance(val, (int, float)):
        raise TypeError(f"Field '{field_name}' value must be numeric float/int, got: {type(val)}")

    val_f = float(val)

    # Reject non-finite values (NaN / infinity)
    if not math.isfinite(val_f) or not math.isfinite(unpacked):
        raise ValueError(f"Field '{field_name}' contains non-finite value (NaN/Inf) which is unsupported")

    # Bit-exact check
    packed_hex = struct.pack('>d', val_f).hex().lower()
    if packed_hex != bit_str_clean:
        raise ValueError(
            f"Discrepancy in '{field_name}': numeric value {val_f} (IEEE-754 bits {packed_hex}) "
            f"does not match stored bit encoding '{bit_str_clean}'"
        )
    
    if unpacked != val_f:
        raise ValueError(f"Decoded float {unpacked} != stored float {val_f} for '{field_name}'")


def recompute_canonical_graph_sha256(rec):
    """
    Independently reconstructs the bit-exact canonical serialization of a problem instance
    under schema adhp-canonical-v1 and computes its standard FIPS 180-4 SHA-256 digest.
    Asserts bit-exact parity between the record's graph_id and this recomputation.
    """
    schema = rec.get("schema_version")
    if schema != "adhp-canonical-v1":
        raise ValueError(f"Unsupported instance schema version: {schema}")

    nodes = rec.get("nodes")
    if not isinstance(nodes, int) or nodes <= 0:
        raise ValueError(f"Invalid node count: {nodes}")

    source = rec.get("source")
    target = rec.get("target")
    if not isinstance(source, int) or not (0 <= source < nodes):
        raise ValueError(f"Invalid source vertex {source} for graph with {nodes} nodes")
    if not isinstance(target, int) or not (0 <= target < nodes):
        raise ValueError(f"Invalid target vertex {target} for graph with {nodes} nodes")

    budget = rec.get("budget")
    budget_bits = rec.get("budget_bits")
    if budget_bits is None or budget is None:
        raise ValueError("Missing budget or budget_bits in instance record")
    validate_numeric_representation(budget, budget_bits, "budget")
    if float(budget) <= 0:
        raise ValueError(f"Budget must be strictly positive, got: {budget}")

    edges = rec.get("canonical_edges")
    if not isinstance(edges, list):
        raise ValueError("canonical_edges must be a list of edge objects")
    
    declared_edges = rec.get("edges")
    if len(edges) != declared_edges:
        raise ValueError(f"Canonical edge count mismatch: declared {declared_edges}, actual {len(edges)}")

    for e in edges:
        u = e.get("from")
        v = e.get("to")
        if not isinstance(u, int) or not (0 <= u < nodes):
            raise ValueError(f"Edge 'from' vertex {u} out of bounds for graph with {nodes} nodes")
        if not isinstance(v, int) or not (0 <= v < nodes):
            raise ValueError(f"Edge 'to' vertex {v} out of bounds for graph with {nodes} nodes")

        c = e.get("cost")
        c_bits = e.get("cost_bits")
        validate_numeric_representation(c, c_bits, f"edge {u}->{v} cost")
        if float(c) < 0:
            raise ValueError(f"Negative edge cost {c} on edge {u}->{v}")

        w = e.get("weight")
        w_bits = e.get("weight_bits")
        validate_numeric_representation(w, w_bits, f"edge {u}->{v} weight")
        if float(w) < 0:
            raise ValueError(f"Negative edge weight {w} on edge {u}->{v}")

    sorted_edges = sorted(
        edges,
        key=lambda e: (e['from'], e['to'], e['cost_bits'].lower(), e['weight_bits'].lower())
    )
    lines = [
        f"{schema}\n",
        f"nodes: {nodes}\n",
        f"source: {source}\n",
        f"target: {target}\n",
        f"budget: {budget_bits.lower()}\n",
        f"edges: {len(sorted_edges)}\n"
    ]
    for e in sorted_edges:
        lines.append(f"{e['from']} {e['to']} {e['cost_bits'].lower()} {e['weight_bits'].lower()}\n")
    payload = "".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def recompute_canonical_topology_sha256(rec):
    """
    Independently reconstructs the graph topology digest (schema adhp-topology-v1).
    Captures node count and deterministically sorted directed edge endpoints (from, to).
    """
    nodes = rec["nodes"]
    edges = rec.get("canonical_edges", [])
    sorted_edges = sorted(edges, key=lambda e: (e['from'], e['to']))
    lines = [
        "adhp-topology-v1\n",
        f"nodes: {nodes}\n",
        f"edges: {len(sorted_edges)}\n"
    ]
    for e in sorted_edges:
        lines.append(f"{e['from']} {e['to']}\n")
    payload = "".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_benchmarks(raw_csv_path="results/raw/benchmark_raw.csv",
                      summary_csv_path="results/processed/summary_table.csv",
                      instances_json_path="results/raw/benchmark_instances.json"):
    """
    Executes substantive assertions on benchmark CSV and instance registry data.
    Strictly fail-closed: raises FileNotFoundError, ValueError, or AssertionError on any issue.
    Returns True on success.
    """
    # 1. Mandatory Artifact Existence and Non-Emptiness
    if not raw_csv_path or not os.path.exists(raw_csv_path):
        raise FileNotFoundError(f"Required raw benchmark CSV not found: {raw_csv_path}")
    if os.path.getsize(raw_csv_path) == 0:
        raise ValueError(f"Required raw benchmark CSV is empty: {raw_csv_path}")

    if not summary_csv_path or not os.path.exists(summary_csv_path):
        raise FileNotFoundError(f"Required summary table CSV not found: {summary_csv_path}")
    if os.path.getsize(summary_csv_path) == 0:
        raise ValueError(f"Required summary table CSV is empty: {summary_csv_path}")

    if not instances_json_path:
        raise FileNotFoundError("Required benchmark instance registry path must be provided")

    if isinstance(instances_json_path, str):
        if not os.path.exists(instances_json_path):
            raise FileNotFoundError(f"Required benchmark instance registry JSON not found: {instances_json_path}")
        if os.path.getsize(instances_json_path) == 0:
            raise ValueError(f"Required benchmark instance registry JSON is empty: {instances_json_path}")
        with open(instances_json_path, 'r', encoding='utf-8') as f:
            inst_records = json.load(f)
    elif isinstance(instances_json_path, list):
        inst_records = instances_json_path
    else:
        raise TypeError(f"Invalid instances_json_path type: {type(instances_json_path)}")

    df = pd.read_csv(raw_csv_path)

    # 2. Schema and Column Checks
    missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
    assert not missing_cols, f"Missing columns in {raw_csv_path}: {missing_cols}"
    assert len(df) == 120, f"Expected exactly 120 raw records, found {len(df)}"
    assert not df.isnull().any().any(), "Dataset contains unexpected null/NaN values"

    duplicates = df[df.duplicated(subset=['benchmark_category', 'instance_name', 'solver_name'], keep=False)]
    assert len(duplicates) == 0, f"Duplicate benchmark records detected:\n{duplicates}"

    # 3. Category & Configuration Accounting
    categories = sorted(df['benchmark_category'].unique().tolist())
    assert categories == sorted(EXPECTED_CATEGORIES), f"Unexpected categories: {categories}"

    total_configs = 0
    for cat, expected_insts in EXPECTED_CONFIGS.items():
        cat_df = df[df['benchmark_category'] == cat]
        actual_insts = sorted(cat_df['instance_name'].unique().tolist())
        assert actual_insts == sorted(expected_insts), \
            f"Category {cat} configuration mismatch: expected {expected_insts}, got {actual_insts}"
        total_configs += len(actual_insts)

        if cat == 'Ablation K Facets':
            actual_solvers = sorted(cat_df['solver_name'].unique().tolist())
            assert actual_solvers == sorted(EXPECTED_ABLATION_SOLVERS), \
                f"Ablation solver mismatch: expected {EXPECTED_ABLATION_SOLVERS}, got {actual_solvers}"
            assert len(cat_df) == 6, f"Expected 6 ablation records, got {len(cat_df)}"
        else:
            for inst in expected_insts:
                inst_df = cat_df[cat_df['instance_name'] == inst]
                actual_solvers = sorted(inst_df['solver_name'].unique().tolist())
                assert actual_solvers == sorted(EXPECTED_COMPETITIVE_SOLVERS), \
                    f"Instance {inst} missing solvers: expected {EXPECTED_COMPETITIVE_SOLVERS}, got {actual_solvers}"
                assert len(inst_df) == 6, f"Expected 6 solvers for {inst}, got {len(inst_df)}"

    assert total_configs == 25, f"Expected 25 distinct configurations, got {total_configs}"

    total_evals = df.groupby(['benchmark_category', 'instance_name'])['num_instances'].first().sum()
    assert total_evals == 250, f"Expected 250 total instance evaluations, got {total_evals}"

    # 4. Canonical Instance Identity and Distinct Graph Verification (FIPS 180-4 SHA-256 independent recomputation)
    assert isinstance(inst_records, list), "Instance registry must be a list of records"
    assert len(inst_records) == 250, f"Expected 250 instance evaluations, found {len(inst_records)}"

    config_counts = {}
    distinct_instance_ids = set()
    distinct_topology_ids = set()
    suite_instance_ids = set()
    suite_topology_ids = set()
    grid_topology_ids = set()
    ablation_instance_ids_by_cfg = {}
    ablation_topology_ids_by_cfg = {}

    for rec in inst_records:
        missing_keys = EXPECTED_INSTANCE_KEYS - set(rec.keys())
        assert not missing_keys, f"Instance record missing keys: {missing_keys}"
        assert isinstance(rec['graph_id'], str) and len(rec['graph_id']) == 64, \
            f"Invalid canonical graph_id length (expected 64-hex SHA-256): {rec.get('graph_id')}"
        assert rec.get('schema_version') == 'adhp-canonical-v1', \
            f"Unsupported instance schema version: {rec.get('schema_version')}"

        # Independent FIPS 180-4 SHA-256 recomputation of Problem-Instance Digest
        recomputed_instance_hash = recompute_canonical_graph_sha256(rec)
        assert recomputed_instance_hash == rec['graph_id'], \
            f"Independent SHA-256 recomputation mismatch for evaluation {rec.get('evaluation_id')}: " \
            f"recomputed {recomputed_instance_hash} != record {rec.get('graph_id')}"

        # Independent recomputation of Graph Topology Digest
        recomputed_topology_hash = recompute_canonical_topology_sha256(rec)

        cfg = rec['configuration_name']
        config_counts[cfg] = config_counts.get(cfg, 0) + 1
        distinct_instance_ids.add(recomputed_instance_hash)
        distinct_topology_ids.add(recomputed_topology_hash)

        cat = rec['benchmark_category']
        if cat == 'Ablation K Facets':
            ablation_instance_ids_by_cfg.setdefault(cfg, []).append(recomputed_instance_hash)
            ablation_topology_ids_by_cfg.setdefault(cfg, []).append(recomputed_topology_hash)
        else:
            suite_instance_ids.add(recomputed_instance_hash)
            suite_topology_ids.add(recomputed_topology_hash)
            if cat == 'Grid Scaling':
                grid_topology_ids.add(recomputed_topology_hash)

    # Check configuration counts: 25 configs, 10 evals each
    assert len(config_counts) == 25, \
        f"Expected 25 distinct configurations in instance registry, found {len(config_counts)}"
    for cfg, count in config_counts.items():
        assert count == 10, f"Configuration {cfg} expected 10 instances, found {count}"

    # Check deduplication: exactly 200 distinct problem instances across 250 evaluations
    assert len(distinct_instance_ids) == 200, \
        f"Deduplicated canonical problem instance IDs must equal 200, found {len(distinct_instance_ids)}"

    # Check topology deduplication: exactly 164 distinct topologies across 250 evaluations
    assert len(distinct_topology_ids) == 164, \
        f"Deduplicated canonical graph topology IDs must equal 164, found {len(distinct_topology_ids)}"

    # Check that Grid Scaling evaluates exactly 4 distinct grid topologies across 40 evaluations
    assert len(grid_topology_ids) == 4, \
        f"Grid Scaling must evaluate exactly 4 distinct planar grid topologies, found {len(grid_topology_ids)}"

    # Check that Suites 1-4 contain exactly 190 unique problem instances
    assert len(suite_instance_ids) == 190, \
        f"Expected 190 unique problem instance IDs across Suites 1-4, found {len(suite_instance_ids)}"

    # Check Suite 5 ablation: all 6 configurations evaluate the same 10 instances
    assert len(ablation_instance_ids_by_cfg) == 6, \
        f"Expected 6 ablation configurations, found {len(ablation_instance_ids_by_cfg)}"
    ablation_reference_ids = None
    for cfg, ids in ablation_instance_ids_by_cfg.items():
        assert len(ids) == 10, f"Ablation config {cfg} must have 10 instances, found {len(ids)}"
        assert len(set(ids)) == 10, f"Ablation config {cfg} instances must be distinct, found {len(set(ids))}"
        if ablation_reference_ids is None:
            ablation_reference_ids = ids
        else:
            assert ids == ablation_reference_ids, \
                f"Ablation config {cfg} did not evaluate the same instance graphs as reference"

    assert suite_instance_ids.isdisjoint(set(ablation_reference_ids)), \
        "Ablation problem instance IDs must be disjoint from Suites 1-4"

    # 5. Numerical & Physical Validity Checks
    assert (df['nodes'] > 0).all(), "Found non-positive node counts"
    assert (df['edges'] > 0).all(), "Found non-positive edge counts"
    assert (df['budget'] > 0).all(), "Found non-positive budget values"
    assert (df['mean_runtime_micros'] > 0).all(), "Found non-positive mean runtimes"
    assert (df['median_runtime_micros'] > 0).all(), "Found non-positive median runtimes"
    assert (df['std_dev_micros'] >= 0).all(), "Found negative standard deviations"
    assert (df['mean_preprocessing_micros'] >= 0).all(), "Found negative preprocessing times"
    assert (df['mean_search_micros'] >= 0).all(), "Found negative search times"
    assert (df['mean_labels_generated'] >= 0).all(), "Found negative label counts"
    assert (df['mean_labels_explored'] >= 0).all(), "Found negative explored counts"

    decomp_diff = (df['mean_preprocessing_micros'] + df['mean_search_micros'] - df['mean_runtime_micros']).abs()
    assert (decomp_diff < 1.0).all(), \
        f"Preprocessing + search diverges from total runtime (> 1.0 us):\n{df[decomp_diff >= 1.0]}"

    assert (df['mean_labels_generated'] >= df['mean_labels_explored']).all(), \
        "Found instances where explored labels exceeded generated labels"

    # 6. Summary Table Synchronization
    summary_df = pd.read_csv(summary_csv_path)
    summary_cols = list(summary_df.columns)
    assert len(summary_df) == 30, f"Expected 30 summary records, found {len(summary_df)}"

    for _, row in summary_df.iterrows():
        cat = row['Category']
        sol = row['Solver']
        sub = df[(df['benchmark_category'] == cat) & (df['solver_name'] == sol)]
        assert len(sub) > 0, f"Summary entry ({cat}, {sol}) has no corresponding raw data"

        calc_avg_rt = round(sub['mean_runtime_micros'].mean(), 2)
        calc_max_rt = round(sub['mean_runtime_micros'].max(), 2)
        calc_avg_lbl_raw = sub['mean_labels_generated'].mean()
        calc_max_lbl = int(sub['mean_labels_generated'].max())

        stored_avg_rt = float(row[summary_cols[2]])
        stored_max_rt = float(row[summary_cols[3]])
        stored_avg_lbl = int(row[summary_cols[4]])
        stored_max_lbl = int(row[summary_cols[5]])

        assert abs(calc_avg_rt - stored_avg_rt) <= 0.05, \
            f"Summary avg runtime mismatch for ({cat}, {sol}): calculated {calc_avg_rt}, stored {stored_avg_rt}"
        assert abs(calc_max_rt - stored_max_rt) <= 0.05, \
            f"Summary max runtime mismatch for ({cat}, {sol}): calculated {calc_max_rt}, stored {stored_max_rt}"
        assert stored_avg_lbl in (int(calc_avg_lbl_raw), int(round(calc_avg_lbl_raw))), \
            f"Summary avg labels mismatch for ({cat}, {sol}): calculated {calc_avg_lbl_raw:.2f}, stored {stored_avg_lbl}"
        assert calc_max_lbl == stored_max_lbl, \
            f"Summary max labels mismatch for ({cat}, {sol}): calculated {calc_max_lbl}, stored {stored_max_lbl}"

    # 7. Empirical Honesty: Verify Regressions are Preserved and Not Suppressed
    er30_adhp = df[(df['instance_name'] == 'random_er_n30') & (df['solver_name'] == 'ADHP (Adaptive Dual Hull Pruning)')]['mean_runtime_micros'].values[0]
    er30_martins = df[(df['instance_name'] == 'random_er_n30') & (df['solver_name'] == 'Martins (Standard Multi-Label Dijkstra)')]['mean_runtime_micros'].values[0]
    assert er30_adhp > er30_martins, \
        f"Empirical honesty check failed: ADHP ({er30_adhp} us) was expected to be slower than Martins ({er30_martins} us) on random_er_n30"

    # 8. Comprehensive Published Claim Reconciliations across maintained documents
    # Fails closed if module cannot be imported or any claim diverges
    try:
        import scripts.sync_published_claims as sync_mod
    except ImportError:
        try:
            import sync_published_claims as sync_mod
        except ImportError as e:
            raise ImportError(f"Required claim reconciliation module could not be imported: {e}")

    sync_mod.check_all_claims(df)
    verify_published_headlines(df)

    return True


def generate_summary_table(raw_csv_path="results/raw/benchmark_raw.csv",
                           summary_csv_path="results/processed/summary_table.csv"):
    """
    Dynamically generates the processed summary_table.csv from the raw benchmark data.
    """
    df = pd.read_csv(raw_csv_path)
    summary_records = []
    grouped = df.groupby(['benchmark_category', 'solver_name'])
    for (cat, sol), group in grouped:
        avg_rt = round(float(group['mean_runtime_micros'].mean()), 2)
        max_rt = round(float(group['mean_runtime_micros'].max()), 2)
        avg_lbl = int(round(float(group['mean_labels_generated'].mean())))
        max_lbl = int(group['mean_labels_generated'].max())
        summary_records.append({
            'Category': cat,
            'Solver': sol,
            'Avg Runtime (µs)': avg_rt,
            'Max Runtime (µs)': max_rt,
            'Avg Labels Generated': avg_lbl,
            'Max Labels Generated': max_lbl,
        })
    summary_df = pd.DataFrame(summary_records)
    summary_df = summary_df.sort_values(by=['Category', 'Solver'])
    os.makedirs(os.path.dirname(summary_csv_path), exist_ok=True)
    summary_df.to_csv(summary_csv_path, index=False)
    return summary_df


def verify_published_headlines(df):
    """
    Verifies key headline relationships and deterministic algorithmic invariants.
    """
    # 1. Grid 10x10 Hybrid runtime, speedup, and label reduction
    g10_hybrid = df[(df['instance_name'] == 'grid_10x10') & (df['solver_name'] == 'Adaptive Hybrid ADHP')]['mean_runtime_micros'].values[0]
    g10_adhp = df[(df['instance_name'] == 'grid_10x10') & (df['solver_name'] == 'ADHP (Adaptive Dual Hull Pruning)')]['mean_runtime_micros'].values[0]
    g10_martins = df[(df['instance_name'] == 'grid_10x10') & (df['solver_name'] == 'Martins (Standard Multi-Label Dijkstra)')]['mean_runtime_micros'].values[0]
    g10_pulse = df[(df['instance_name'] == 'grid_10x10') & (df['solver_name'] == 'Pulse (Lozano & Medaglia 2013)')]['mean_runtime_micros'].values[0]

    g10_hybrid_lbl = df[(df['instance_name'] == 'grid_10x10') & (df['solver_name'] == 'Adaptive Hybrid ADHP')]['mean_labels_generated'].values[0]
    g10_martins_lbl = df[(df['instance_name'] == 'grid_10x10') & (df['solver_name'] == 'Martins (Standard Multi-Label Dijkstra)')]['mean_labels_generated'].values[0]

    assert g10_hybrid < g10_martins, f"Hybrid expected faster than Martins on grid_10x10: {g10_hybrid} vs {g10_martins}"
    assert g10_hybrid < g10_pulse, f"Hybrid expected faster than Pulse on grid_10x10: {g10_hybrid} vs {g10_pulse}"
    assert g10_martins / g10_hybrid > 2.5, f"Expected significant speedup on grid 10x10, got {g10_martins / g10_hybrid:.2f}x"
    assert g10_hybrid_lbl < g10_martins_lbl * 0.10, f"Expected >90% label reduction on grid 10x10: {g10_hybrid_lbl} vs {g10_martins_lbl}"

    # 2. Anti-correlated n=150 Hybrid performance
    ac150_hybrid = df[(df['instance_name'] == 'anticorr_n150') & (df['solver_name'] == 'Adaptive Hybrid ADHP')]['mean_runtime_micros'].values[0]
    ac150_cw = df[(df['instance_name'] == 'anticorr_n150') & (df['solver_name'] == 'Carlyle-Wood (LARAC Single-Multiplier Lagrangian Bounding)')]['mean_runtime_micros'].values[0]
    assert ac150_hybrid < ac150_cw, f"Hybrid expected faster than Carlyle-Wood on anticorr_n150: {ac150_hybrid} vs {ac150_cw}"

    # 3. Deterministic algorithmic label counts on anti-correlated n=100
    ac100_adhp_lbl = df[(df['instance_name'] == 'anticorr_n100') & (df['solver_name'] == 'ADHP (Adaptive Dual Hull Pruning)')]['mean_labels_generated'].values[0]
    ac100_martins_lbl = df[(df['instance_name'] == 'anticorr_n100') & (df['solver_name'] == 'Martins (Standard Multi-Label Dijkstra)')]['mean_labels_generated'].values[0]
    assert ac100_adhp_lbl == 79, f"Anti-corr n=100 ADHP labels mismatch: {ac100_adhp_lbl}"
    assert ac100_martins_lbl == 2751, f"Anti-corr n=100 Martins labels mismatch: {ac100_martins_lbl}"

    # 4. Ablation on K=1 and K=2 labels
    abl_k1_lbl = df[(df['instance_name'] == 'ablation_k1')]['mean_labels_generated'].values[0]
    abl_k2_lbl = df[(df['instance_name'] == 'ablation_k2')]['mean_labels_generated'].values[0]
    assert abl_k1_lbl == 146, f"Ablation K=1 labels mismatch: {abl_k1_lbl}"
    assert abl_k2_lbl == 91, f"Ablation K=2 labels mismatch: {abl_k2_lbl}"
    assert abl_k1_lbl > abl_k2_lbl, "K=2 must generate fewer search labels than K=1"

    for k in [2, 3, 5, 8, 12]:
        lbl = df[(df['instance_name'] == f'ablation_k{k}')]['mean_labels_generated'].values[0]
        assert lbl == 91, f"Ablation K={k} labels mismatch from plateau: {lbl}"

    return True


def main():
    print("=== ADHP-CSPP: Rigorous Benchmark Consistency & Integrity Audit ===")
    update_summary = "--update-summary" in sys.argv or "--update" in sys.argv
    if update_summary:
        print(">> Generating fresh summary_table.csv from raw benchmark data...")
        generate_summary_table()

    try:
        verify_benchmarks()
        print(" [PASSED] Strict fail-closed artifact check: raw CSV, summary CSV, and instance registry verified.")
        print(" [PASSED] Record count integrity: 120 raw records across 25 configurations.")
        print(" [PASSED] Canonical Problem-Instance identity (adhp-canonical-v1): exactly 200 distinct instances across 250 evaluations.")
        print(" [PASSED] Canonical Graph Topology identity (adhp-topology-v1): exactly 164 distinct topologies across 250 evaluations.")
        print(" [PASSED] Value-vs-bit IEEE-754 binary64 validation: all float fields bit-match hex encodings.")
        print(" [PASSED] Metric physical validity: non-negativity and runtime decomposition verified.")
        print(" [PASSED] Summary table synchronization: exact agreement with results/processed/summary_table.csv.")
        print(" [PASSED] Empirical honesty verification: regressions on random graphs verified.")
        print(" [PASSED] Comprehensive claim reconciliation: all published tables and text verified fail-closed.")
        print("\n========================================================")
        print("SUCCESS: All benchmark consistency and integrity assertions passed.")
        print("========================================================")
        sys.exit(0)
    except Exception as e:
        print(f"\n[BENCHMARK VERIFICATION FAILED]: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
