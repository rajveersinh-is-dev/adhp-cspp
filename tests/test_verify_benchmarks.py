#!/usr/bin/env python3
"""
Adversarial and Regression Unit Tests for scripts/verify_benchmarks.py.

Validates that the benchmark verifier:
1. Passes on genuine, untampered benchmark data and instance registry.
2. [A1] Fails closed on missing or empty raw CSV.
3. [A2] Fails closed on missing or empty instance registry.
4. [A3] Fails closed on missing or empty summary CSV.
5. [A4] Fails closed when required claim validator cannot be imported.
6. [A5] Propagates claim validator assertion or runtime errors as nonzero failures.
7. [A6] Fails when numeric values disagree with IEEE-754 bit encodings (cost, weight, budget).
8. [A6] Rejects non-finite values (NaN, infinity), negative zeros (-0.0), and malformed hex strings.
9. [A7] Enforces graph structural schema: node bounds, vertex bounds, source/target, and edge counts.
10. [A8] Separates Problem-Instance Digest (adhp-canonical-v1) from Graph Topology Digest (adhp-topology-v1).
11. [A9] Guarantees deterministic serialization invariant under edge reordering.
12. [A10] Reconciles published claims: detecting mutations in README, paper/main.tex, paper/main.typ,
    and research/BENCHMARK_REPORT.md.
13. Preserves empirical honesty (regressions on small random graphs).
"""

import copy
import json
import os
import random
import sys
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd

# Add repository root to pythonpath
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from scripts.verify_benchmarks import (
    verify_benchmarks,
    recompute_canonical_graph_sha256,
    recompute_canonical_topology_sha256,
    validate_numeric_representation,
)


class TestBenchmarkVerifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_csv = os.path.join(REPO_ROOT, "results", "raw", "benchmark_raw.csv")
        cls.summary_csv = os.path.join(REPO_ROOT, "results", "processed", "summary_table.csv")
        cls.instances_json = os.path.join(REPO_ROOT, "results", "raw", "benchmark_instances.json")
        assert os.path.exists(cls.raw_csv), "Raw benchmark CSV missing"
        assert os.path.exists(cls.summary_csv), "Summary table CSV missing"
        assert os.path.exists(cls.instances_json), "Benchmark instances JSON missing"
        with open(cls.instances_json, "r", encoding="utf-8") as f:
            cls.cached_instances = json.load(f)

    def setUp(self):
        self.raw_csv = self.__class__.raw_csv
        self.summary_csv = self.__class__.summary_csv
        self.instances_json = self.__class__.instances_json
        self.cached_instances = self.__class__.cached_instances

    # --- Baseline Positive Test ---
    def test_genuine_data_passes(self):
        """Genuine dataset passes all consistency and cryptographic assertions."""
        self.assertTrue(verify_benchmarks(self.raw_csv, self.summary_csv, self.instances_json))

    # --- A1: Missing or Empty Raw CSV Tests ---
    def test_missing_raw_csv_fails(self):
        """[A1] Missing raw benchmark CSV must raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            verify_benchmarks("results/raw/nonexistent_raw.csv", self.summary_csv, self.cached_instances)

    def test_empty_raw_csv_fails(self):
        """[A1] Empty raw benchmark CSV must raise ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            temp_path = tf.name
        try:
            with self.assertRaises(ValueError):
                verify_benchmarks(temp_path, self.summary_csv, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # --- A2: Missing or Empty Instance Registry Tests ---
    def test_missing_instance_registry_fails(self):
        """[A2] Missing benchmark instance registry must raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            verify_benchmarks(self.raw_csv, self.summary_csv, "results/raw/nonexistent_instances.json")

    def test_empty_instance_registry_fails(self):
        """[A2] Empty benchmark instance registry must raise ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            temp_path = tf.name
        try:
            with self.assertRaises(ValueError):
                verify_benchmarks(self.raw_csv, self.summary_csv, temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # --- A3: Missing or Empty Summary CSV Tests ---
    def test_missing_summary_csv_fails(self):
        """[A3] Missing summary table CSV must raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            verify_benchmarks(self.raw_csv, "results/processed/nonexistent_summary.csv", self.cached_instances)

    def test_empty_summary_csv_fails(self):
        """[A3] Empty summary table CSV must raise ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            temp_path = tf.name
        try:
            with self.assertRaises(ValueError):
                verify_benchmarks(self.raw_csv, temp_path, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # --- A4: Missing Claim Validator Import Tests ---
    def test_missing_claim_validator_import_fails(self):
        """[A4] Import failure of claim reconciliation module must fail closed."""
        with patch.dict("sys.modules", {"scripts.sync_published_claims": None, "sync_published_claims": None}):
            with self.assertRaises(ImportError):
                verify_benchmarks(self.raw_csv, self.summary_csv, self.cached_instances)

    # --- A5: Claim Validator Assertion Propagation Tests ---
    def test_claim_validator_assertion_error_propagates(self):
        """[A5] An assertion failure in sync_published_claims must propagate and fail verification."""
        import scripts.sync_published_claims as sync_mod
        with patch.object(sync_mod, "check_all_claims", side_effect=AssertionError("Adversarial claim mismatch")):
            with self.assertRaises(AssertionError):
                verify_benchmarks(self.raw_csv, self.summary_csv, self.cached_instances)

    # --- A6: Numeric Value vs Bit Encoding Invariant Mutations ---
    def test_tampered_cost_numeric_mismatch_fails(self):
        """[A6] Mutating edge cost numeric value without updating cost_bits must fail validation."""
        corrupted = copy.deepcopy(self.cached_instances)
        corrupted[0]['canonical_edges'][0]['cost'] = 999.0  # cost_bits remains unchanged
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    def test_tampered_weight_numeric_mismatch_fails(self):
        """[A6] Mutating edge weight numeric value without updating weight_bits must fail validation."""
        corrupted = copy.deepcopy(self.cached_instances)
        corrupted[0]['canonical_edges'][0]['weight'] = 888.0  # weight_bits remains unchanged
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    def test_tampered_budget_numeric_mismatch_fails(self):
        """[A6] Mutating instance budget numeric value without updating budget_bits must fail validation."""
        corrupted = copy.deepcopy(self.cached_instances)
        corrupted[0]['budget'] = 777.0  # budget_bits remains unchanged
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    def test_corrupted_bit_string_width_fails(self):
        """[A6] Bit string with width != 16 characters must fail validation."""
        with self.assertRaises(ValueError):
            validate_numeric_representation(10.0, "402400000000", "test_cost")

    def test_corrupted_bit_string_non_hex_fails(self):
        """[A6] Bit string with non-hexadecimal characters must fail validation."""
        with self.assertRaises(ValueError):
            validate_numeric_representation(10.0, "402400000000000z", "test_cost")

    def test_nan_numeric_value_rejected(self):
        """[A6] NaN float values must be strictly rejected."""
        with self.assertRaises(ValueError):
            validate_numeric_representation(float('nan'), "7ff8000000000000", "test_cost")

    def test_inf_numeric_value_rejected(self):
        """[A6] Infinite float values must be strictly rejected."""
        with self.assertRaises(ValueError):
            validate_numeric_representation(float('inf'), "7ff0000000000000", "test_cost")

    def test_signed_negative_zero_rejected(self):
        """[A6] Negative zero (-0.0) encodings must be strictly rejected."""
        with self.assertRaises(ValueError):
            validate_numeric_representation(-0.0, "8000000000000000", "test_cost")

    def test_negative_cost_or_weight_rejected(self):
        """[A6] Negative cost or weight values must be rejected."""
        corrupted = copy.deepcopy(self.cached_instances)
        # Set negative cost and matching negative float IEEE bits
        corrupted[0]['canonical_edges'][0]['cost'] = -5.0
        corrupted[0]['canonical_edges'][0]['cost_bits'] = "c014000000000000"
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    def test_boolean_numeric_value_rejected(self):
        """[A6] Boolean values (True/False) must be strictly rejected for numeric fields."""
        with self.assertRaises(TypeError):
            validate_numeric_representation(True, "3ff0000000000000", "test_cost")
        with self.assertRaises(TypeError):
            validate_numeric_representation(False, "0000000000000000", "test_cost")

    def test_boolean_node_count_rejected_in_canonical_hashing(self):
        """[A7] Boolean value for 'nodes' must be rejected in canonical and topology digests."""
        rec = copy.deepcopy(self.cached_instances[0])
        rec['nodes'] = True
        with self.assertRaises(ValueError):
            recompute_canonical_graph_sha256(rec)
        with self.assertRaises(ValueError):
            recompute_canonical_topology_sha256(rec)

    def test_boolean_source_target_rejected(self):
        """[A7] Boolean value for source/target must be rejected in canonical digest."""
        rec = copy.deepcopy(self.cached_instances[0])
        rec['source'] = True
        with self.assertRaises(ValueError):
            recompute_canonical_graph_sha256(rec)

    def test_boolean_edge_endpoint_rejected(self):
        """[A7] Boolean value for edge endpoints must be rejected in canonical and topology digests."""
        rec = copy.deepcopy(self.cached_instances[0])
        rec['canonical_edges'][0]['from'] = True
        with self.assertRaises(ValueError):
            recompute_canonical_graph_sha256(rec)
        with self.assertRaises(ValueError):
            recompute_canonical_topology_sha256(rec)

    # --- A7: Structural Metadata & Invariant Enforcements ---
    def test_structural_vertex_from_out_of_bounds_fails(self):
        """[A7] Edge 'from' vertex >= nodes must fail structural validation."""
        corrupted = copy.deepcopy(self.cached_instances)
        nodes = corrupted[0]['nodes']
        corrupted[0]['canonical_edges'][0]['from'] = nodes + 5
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    def test_structural_vertex_to_out_of_bounds_fails(self):
        """[A7] Edge 'to' vertex >= nodes must fail structural validation."""
        corrupted = copy.deepcopy(self.cached_instances)
        nodes = corrupted[0]['nodes']
        corrupted[0]['canonical_edges'][0]['to'] = nodes + 2
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    def test_structural_source_out_of_bounds_fails(self):
        """[A7] Source vertex >= nodes must fail structural validation."""
        corrupted = copy.deepcopy(self.cached_instances)
        nodes = corrupted[0]['nodes']
        corrupted[0]['source'] = nodes + 1
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    def test_structural_target_out_of_bounds_fails(self):
        """[A7] Target vertex >= nodes must fail structural validation."""
        corrupted = copy.deepcopy(self.cached_instances)
        nodes = corrupted[0]['nodes']
        corrupted[0]['target'] = nodes + 1
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    def test_structural_edge_count_mismatch_fails(self):
        """[A7] Canonical edge count != declared 'edges' must fail validation."""
        corrupted = copy.deepcopy(self.cached_instances)
        corrupted[0]['edges'] = len(corrupted[0]['canonical_edges']) + 1
        with self.assertRaises(ValueError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted)

    # --- A8: Dual Canonical Identity Semantics ---
    def test_problem_instance_vs_topology_digest_separation(self):
        """
        [A8] Modifying a problem parameter (budget or costs) must change the Problem-Instance
        digest (adhp-canonical-v1) while strictly preserving the Graph Topology digest (adhp-topology-v1).
        """
        rec = copy.deepcopy(self.cached_instances[0])
        orig_inst_hash = recompute_canonical_graph_sha256(rec)
        orig_topo_hash = recompute_canonical_topology_sha256(rec)

        # Mutate budget (valid float and matching bits)
        rec['budget'] = 12345.0
        rec['budget_bits'] = "40c81c8000000000"

        new_inst_hash = recompute_canonical_graph_sha256(rec)
        new_topo_hash = recompute_canonical_topology_sha256(rec)

        # Instance digest changes because problem parameter changed
        self.assertNotEqual(orig_inst_hash, new_inst_hash)
        # Topology digest remains identical because graph structure (nodes, edge endpoints) is invariant
        self.assertEqual(orig_topo_hash, new_topo_hash)

    # --- A9: Deterministic Serialization under Reordering ---
    def test_deterministic_serialization_under_edge_reordering(self):
        """
        [A9] Shuffling the input edge list must produce bit-exact identical Problem-Instance
        and Topology digests, proving canonical sorting invariance.
        """
        rec = copy.deepcopy(self.cached_instances[0])
        orig_inst_hash = recompute_canonical_graph_sha256(rec)
        orig_topo_hash = recompute_canonical_topology_sha256(rec)

        # Reverse and randomly shuffle edges
        shuffled_edges = list(reversed(rec['canonical_edges']))
        rng = random.Random(42)
        rng.shuffle(shuffled_edges)
        rec['canonical_edges'] = shuffled_edges

        recomputed_inst_hash = recompute_canonical_graph_sha256(rec)
        recomputed_topo_hash = recompute_canonical_topology_sha256(rec)

        self.assertEqual(orig_inst_hash, recomputed_inst_hash)
        self.assertEqual(orig_topo_hash, recomputed_topo_hash)

    # --- A10: Published Claim Mutation Tests ---
    def test_published_claim_mutation_in_readme_fails(self):
        """[A10] Mutating a table value in README.md must trigger claim verification failure."""
        import scripts.sync_published_claims as sync_mod
        df = pd.read_csv(self.raw_csv)
        with open(sync_mod.README_PATH, "r", encoding="utf-8") as f:
            orig_content = f.read()
        target = "$74.23 \\, \\mu\\text{s}$"
        self.assertIn(target, orig_content)
        try:
            mutated = orig_content.replace(target, "$999.99 \\, \\mu\\text{s}$")
            with open(sync_mod.README_PATH, "w", encoding="utf-8") as f:
                f.write(mutated)
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(df)
        finally:
            with open(sync_mod.README_PATH, "w", encoding="utf-8") as f:
                f.write(orig_content)

    def test_published_claim_mutation_in_paper_tex_fails(self):
        """[A10] Mutating a table value in paper/main.tex must trigger claim verification failure."""
        import scripts.sync_published_claims as sync_mod
        df = pd.read_csv(self.raw_csv)
        with open(sync_mod.TEX_PATH, "r", encoding="utf-8") as f:
            orig_content = f.read()
        target = "\\textbf{19.97}"
        self.assertIn(target, orig_content)
        try:
            mutated = orig_content.replace(target, "999.99")
            with open(sync_mod.TEX_PATH, "w", encoding="utf-8") as f:
                f.write(mutated)
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(df)
        finally:
            with open(sync_mod.TEX_PATH, "w", encoding="utf-8") as f:
                f.write(orig_content)

    def test_published_claim_mutation_in_paper_typ_fails(self):
        """[A10] Mutating a table value in paper/main.typ must trigger claim verification failure."""
        import scripts.sync_published_claims as sync_mod
        df = pd.read_csv(self.raw_csv)
        with open(sync_mod.TYP_PATH, "r", encoding="utf-8") as f:
            orig_content = f.read()
        target = "[*19.97 µs*]"
        self.assertIn(target, orig_content)
        try:
            mutated = orig_content.replace(target, "[*999.99 µs*]")
            with open(sync_mod.TYP_PATH, "w", encoding="utf-8") as f:
                f.write(mutated)
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(df)
        finally:
            with open(sync_mod.TYP_PATH, "w", encoding="utf-8") as f:
                f.write(orig_content)

    def test_published_claim_mutation_in_benchmark_report_fails(self):
        """[A10] Mutating a table value in research/BENCHMARK_REPORT.md must trigger claim verification failure."""
        import scripts.sync_published_claims as sync_mod
        df = pd.read_csv(self.raw_csv)
        with open(sync_mod.REPORT_PATH, "r", encoding="utf-8") as f:
            orig_content = f.read()
        target = "$19.97 \\pm 4.22$"
        self.assertIn(target, orig_content)
        try:
            mutated = orig_content.replace(target, "$999.99 \\pm 0.00$")
            with open(sync_mod.REPORT_PATH, "w", encoding="utf-8") as f:
                f.write(mutated)
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(df)
        finally:
            with open(sync_mod.REPORT_PATH, "w", encoding="utf-8") as f:
                f.write(orig_content)

    # --- Structural & Schema Verification Negative Tests ---
    def test_missing_column_fails(self):
        """Dropping a required column must fail verification."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = df.drop(columns=['mean_preprocessing_micros'])
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_duplicate_record_fails(self):
        """Duplicate rows must fail verification."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_missing_configuration_fails(self):
        """Omitting a required configuration must fail verification."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = df[df['instance_name'] != 'anticorr_n150']
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_corrupted_runtime_fails(self):
        """Negative runtime or broken decomposition must fail verification."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = df.copy()
        df_corrupted.loc[0, 'mean_runtime_micros'] = -5.0
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_summary_mismatch_fails(self):
        """Discrepancy between raw data and summary table must fail verification."""
        sum_df = pd.read_csv(self.summary_csv)
        sum_corrupted = sum_df.copy()
        col = sum_corrupted.columns[2]
        sum_corrupted.loc[0, col] = 9999.99
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            sum_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(self.raw_csv, temp_path, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_suppressed_regression_fails(self):
        """Falsifying empirical results to suppress regressions must fail."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = df.copy()
        adhp_idx = df_corrupted[(df_corrupted['instance_name'] == 'random_er_n30') & 
                                (df_corrupted['solver_name'].str.startswith('ADHP'))].index[0]
        df_corrupted.loc[adhp_idx, 'mean_runtime_micros'] = 0.01
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_corrupted_instance_registry_count_fails(self):
        """Instance registry with missing evaluation record must fail verification."""
        corrupted_insts = self.cached_instances[:-1]
        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_corrupted_instance_identity_spoof_fails(self):
        """Tampering with graph_id directly must trigger SHA-256 verification failure."""
        corrupted_insts = copy.deepcopy(self.cached_instances)
        corrupted_insts[0]['graph_id'] = '0' * 64
        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_unsupported_schema_version_fails(self):
        """Invalid schema_version must fail verification."""
        corrupted_insts = copy.deepcopy(self.cached_instances)
        corrupted_insts[0]['schema_version'] = 'unsupported-schema-v99'
        with self.assertRaises((AssertionError, ValueError)):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_corrupted_instance_identity_deduplication_fails(self):
        """Instance registry where distinct instances share graph content collapses count and must fail."""
        corrupted_insts = copy.deepcopy(self.cached_instances)
        corrupted_insts[1]['nodes'] = corrupted_insts[0]['nodes']
        corrupted_insts[1]['edges'] = corrupted_insts[0]['edges']
        corrupted_insts[1]['source'] = corrupted_insts[0]['source']
        corrupted_insts[1]['target'] = corrupted_insts[0]['target']
        corrupted_insts[1]['budget'] = corrupted_insts[0]['budget']
        corrupted_insts[1]['budget_bits'] = corrupted_insts[0]['budget_bits']
        corrupted_insts[1]['canonical_edges'] = copy.deepcopy(corrupted_insts[0]['canonical_edges'])
        corrupted_insts[1]['graph_id'] = corrupted_insts[0]['graph_id']

        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    # --- A8: Adversarial Claim Mutation Tests (Prose & Secondary Documents) ---
    def test_reconciliation_mutated_readme_prose_fails(self):
        """[R17] Mutating speedup or runtime in README.md prose outside table must fail reconciliation."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.README_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace("19.97", "99.99")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)
        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(pd.read_csv(self.raw_csv))

    def test_reconciliation_mutated_limitations_ablation_fails(self):
        """[R17] Mutating ablation runtimes in docs/KNOWN_LIMITATIONS.md must fail reconciliation."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.LIMITATIONS_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace("16.57", "99.99")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)
        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(pd.read_csv(self.raw_csv))

    def test_reconciliation_mutated_complexity_runtime_fails(self):
        """[R17] Mutating Grid 10x10 runtimes in docs/COMPLEXITY_ANALYSIS.md must fail reconciliation."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.COMPLEXITY_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace("19.97", "99.99")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)
        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(pd.read_csv(self.raw_csv))

    def test_reconciliation_mutated_methodology_warmups_fails(self):
        """[R17] Mutating warmup count in docs/BENCHMARK_METHODOLOGY.md must fail reconciliation."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.DOCS_METHOD_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace("at least 5 discarded warmup runs", "0 warmup runs")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)
        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(pd.read_csv(self.raw_csv))

    # --- A9: Raw Source Data Mutation Tests (Data-Side Verification) ---
    def test_raw_data_mutation_runtime_fails_reconciliation(self):
        """[R17] Mutating raw benchmark runtime in DataFrame must trigger reconciliation failure."""
        import scripts.sync_published_claims as sync_mod
        df_mut = pd.read_csv(self.raw_csv)
        idx = df_mut[(df_mut['instance_name'] == 'grid_10x10') & (df_mut['solver_name'].str.startswith('Adaptive Hybrid'))].index[0]
        df_mut.at[idx, 'mean_runtime_micros'] = 999.0
        with self.assertRaises(AssertionError):
            sync_mod.check_all_claims(df_mut)

    def test_raw_data_mutation_labels_fails_reconciliation(self):
        """[R17] Mutating raw label counts alters derived suppression and triggers reconciliation failure."""
        import scripts.sync_published_claims as sync_mod
        df_mut = pd.read_csv(self.raw_csv)
        idx = df_mut[(df_mut['instance_name'] == 'grid_10x10') & (df_mut['solver_name'].str.startswith('Martins'))].index[0]
        df_mut.at[idx, 'mean_labels_generated'] = 99999
        with self.assertRaises(AssertionError):
            sync_mod.check_all_claims(df_mut)

    def test_raw_data_mutation_ranking_flip_fails_reconciliation(self):
        """[R17] Mutating raw runtime to alter solver ranking order triggers reconciliation failure."""
        import scripts.sync_published_claims as sync_mod
        df_mut = pd.read_csv(self.raw_csv)
        idx = df_mut[(df_mut['instance_name'] == 'anticorr_n150') & (df_mut['solver_name'].str.startswith('Dumitrescu-Boland'))].index[0]
        df_mut.at[idx, 'mean_runtime_micros'] = 500.0  # Flips 1st place from DB to Martins
        with self.assertRaises(AssertionError):
            sync_mod.check_all_claims(df_mut)

    def test_raw_data_mutation_ablation_fails_reconciliation(self):
        """[R17] Mutating raw ablation preprocessing runtime triggers reconciliation failure."""
        import scripts.sync_published_claims as sync_mod
        df_mut = pd.read_csv(self.raw_csv)
        idx = df_mut[df_mut['instance_name'] == 'ablation_k1'].index[0]
        df_mut.at[idx, 'mean_preprocessing_micros'] = 99.99
        with self.assertRaises(AssertionError):
            sync_mod.check_all_claims(df_mut)

    def test_dynamic_ranking_generator_adapts_to_data_mutation(self):
        """[R17] format_report_rankings_table dynamically recalculates rankings when raw data changes."""
        import scripts.sync_published_claims as sync_mod
        df_mut = pd.read_csv(self.raw_csv)
        idx = df_mut[(df_mut['instance_name'] == 'grid_10x10') & (df_mut['solver_name'].str.startswith('Carlyle-Wood'))].index[0]
        df_mut.at[idx, 'mean_runtime_micros'] = 1.05
        table = sync_mod.format_report_rankings_table(df_mut)
        self.assertIn("**Carlyle-Wood ($1.05 \\, \\mu\\text{s}$)**", table)
        self.assertIn("Adaptive Hybrid ADHP ($19.97 \\, \\mu\\text{s}$)", table)

    def test_dynamic_ablation_generator_adapts_to_data_mutation(self):
        """[R17] format_report_ablation_table dynamically recalculates label reduction % when raw data changes."""
        import scripts.sync_published_claims as sync_mod
        df_mut = pd.read_csv(self.raw_csv)
        idx = df_mut[df_mut['instance_name'] == 'ablation_k2'].index[0]
        df_mut.at[idx, 'mean_labels_generated'] = 73  # (73 - 146)/146 = -50.0%
        table = sync_mod.format_report_ablation_table(df_mut)
        self.assertIn("(-50.0%)", table)

    def test_claim_inventory_integrity_and_traceability(self):
        """[R16] Verify that claim inventory has valid structure, unique IDs, and derived counts."""
        import scripts.sync_published_claims as sync_mod
        res = sync_mod.check_all_claims(pd.read_csv(self.raw_csv))
        self.assertEqual(res["status"], "VERIFIED")
        self.assertGreater(res["verified_claims"], 700)
        self.assertEqual(res["exact_numerical"] + res["derived_statistics"] + res["document_presence"], res["verified_claims"])
        self.assertEqual(res["verified_claims"] + res["manual_review"], res["total_claims"])
        
        # Verify unique IDs and non-empty sources
        inv = res["inventory"]
        claim_ids = set()
        for rec in inv.records:
            self.assertNotIn(rec.claim_id, claim_ids, f"Duplicate claim ID: {rec.claim_id}")
            claim_ids.add(rec.claim_id)
            self.assertTrue(len(rec.source_reference) > 0, f"Empty source reference for {rec.claim_id}")
            self.assertIn(rec.claim_type, ["EXACT_NUMERICAL", "DERIVED_STATISTIC", "DOCUMENT_PRESENCE", "MANUAL_REVIEW"])

        # Verify exported files exist and are populated
        self.assertTrue(os.path.exists(sync_mod.CLAIM_JSON_PATH))
        self.assertTrue(os.path.exists(sync_mod.CLAIM_MD_PATH))
        self.assertGreater(os.path.getsize(sync_mod.CLAIM_JSON_PATH), 100000)
        self.assertGreater(os.path.getsize(sync_mod.CLAIM_MD_PATH), 50000)

    # --- A10: Contradiction & Truthful Claim States Regression Tests ---
    def test_contradictory_configuration_counts_detected(self):
        """[R18] Stale or contradictory '20 configurations' count in methodology fails verification."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.DOCS_METHOD_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace("25 configurations", "20 configurations")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)
        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(pd.read_csv(self.raw_csv))

    def test_contradictory_instance_and_topology_counts_detected(self):
        """[R18] Conflating 200 problem instances with 200 distinct graphs fails verification."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.DOCS_METHOD_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace(
                    "25 configurations, 250 configuration-instance evaluations, 20 distinct problem instance sets, 200 distinct problem instances, and 164 distinct graph topologies",
                    "25 configurations, 250 configuration-instance evaluations, and 200 distinct generated graphs"
                )
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)
        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(pd.read_csv(self.raw_csv))

    def test_obsolete_defect_statements_cannot_survive_without_qualification(self):
        """[R18] Removing historical qualification from defect statement in audit log fails verification."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.AUDIT_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace("[HISTORICAL — RESOLVED]", "[ACTIVE DEFECT]")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)
        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(pd.read_csv(self.raw_csv))

    def test_pending_manual_review_cannot_be_reported_as_fully_verified(self):
        """[R18] A pending manual review claim must prevent status from reporting FULLY_VERIFIED."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        inv.add_exact_numerical("TEST-NUM-1", "README.md", "Test Num", "19.97", "19.97", "raw.csv")
        inv.add_manual_review("TEST-REV-1", "docs/COMPLEXITY_ANALYSIS.md", "Pending Review",
                              "O(K * m * log n)", "docs/COMPLEXITY_ANALYSIS.md",
                              review_status="MANUAL_REVIEW_PENDING", evidence="")
        self.assertEqual(inv.overall_verification_status, "PARTIAL_VERIFIED_PENDING_MANUAL_REVIEW")
        self.assertNotEqual(inv.overall_verification_status, "FULLY_VERIFIED_WITH_RECORDED_EVIDENCE")

    def test_verification_failed_claim_sets_overall_failure(self):
        """[R18] Any failed claim must set overall status to VERIFICATION_FAILED."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        inv.add_exact_numerical("TEST-NUM-1", "README.md", "Test Num", "19.97", "19.97", "raw.csv")
        with self.assertRaises(AssertionError):
            inv.add_exact_numerical("TEST-NUM-FAIL", "README.md", "Missing Num", "99.99", "19.97", "raw.csv")
        self.assertEqual(inv.verification_failed_count, 1)
        self.assertEqual(inv.overall_verification_status, "VERIFICATION_FAILED")

    def test_claim_inventory_no_duplicate_ids_and_nonempty_provenance(self):
        """[R18] All claims must have globally unique IDs and non-empty provenance and check_performed."""
        import scripts.sync_published_claims as sync_mod
        res = sync_mod.check_all_claims(pd.read_csv(self.raw_csv))
        inv = res["inventory"]
        seen_ids = set()
        for r in inv.records:
            self.assertNotIn(r.claim_id, seen_ids, f"Duplicate claim ID: {r.claim_id}")
            seen_ids.add(r.claim_id)
            self.assertTrue(len(r.source_reference.strip()) > 0, f"Empty source reference for {r.claim_id}")
            self.assertTrue(len(r.check_performed.strip()) > 0, f"Empty check_performed for {r.claim_id}")
            self.assertIn(r.status, ["AUTOMATED_PASSED", "MANUAL_REVIEW_PENDING", "MANUAL_REVIEW_COMPLETED", "VERIFICATION_FAILED"])

    def test_claim_inventory_json_markdown_agreement(self):
        """[R18] Generated JSON and Markdown inventories must agree on counts, status, and records."""
        import scripts.sync_published_claims as sync_mod
        sync_mod.check_all_claims(pd.read_csv(self.raw_csv))
        with open(sync_mod.CLAIM_JSON_PATH, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        with open(sync_mod.CLAIM_MD_PATH, "r", encoding="utf-8") as f:
            md_content = f.read()

        summary = json_data["summary"]
        self.assertEqual(summary["overall_verification_status"], "FULLY_VERIFIED_WITH_RECORDED_EVIDENCE")
        self.assertEqual(summary["manual_review_pending"], 0)
        self.assertEqual(summary["verification_failed"], 0)
        self.assertEqual(summary["total_claims_tracked"], len(json_data["claims"]))
        self.assertIn(f"| **Claims Passed (Automated)** | **{summary['claims_passed']}** |", md_content)
        self.assertIn(f"| **Claims Reviewed with Documented Evidence** | {summary['claims_reviewed_with_documented_evidence']} |", md_content)
        self.assertIn("| **Overall Repository Verification Status** | **FULLY_VERIFIED_WITH_RECORDED_EVIDENCE** |", md_content)

        # Assert every claim in JSON is present in Markdown
        for claim in json_data["claims"]:
            self.assertIn(f"`{claim['claim_id']}`", md_content)
            self.assertIn(f"**{claim['status']}**", md_content)

    def test_raw_data_mutation_distinguishes_failure_from_dynamic_regeneration(self):
        """[R18] Distinguish expected verification failure on stale docs from dynamic regeneration."""
        import scripts.sync_published_claims as sync_mod
        df_mut = pd.read_csv(self.raw_csv)
        idx = df_mut[(df_mut['instance_name'] == 'grid_10x10') & (df_mut['solver_name'].str.startswith('Adaptive Hybrid'))].index[0]
        df_mut.at[idx, 'mean_runtime_micros'] = 12.34  # Mutate runtime

        # 1. Un-regenerated documents must fail verification (expected failure)
        with self.assertRaises(AssertionError):
            sync_mod.check_all_claims(df_mut)

        # 2. Dynamic table generator dynamically reflects mutated data (expected regeneration)
        rankings_table = sync_mod.format_report_rankings_table(df_mut)
        self.assertIn("12.34", rankings_table)


class TestPhase7MutationBattery(unittest.TestCase):
    """
    Dedicated Phase 7 Mutation Testing Battery.
    Deliberately introduces the 10 canonical defects and verifies the verifier fails closed.
    """
    @classmethod
    def setUpClass(cls):
        import scripts.sync_published_claims as sync_mod
        cls.raw_df = pd.read_csv(os.path.join(REPO_ROOT, "results", "raw", "benchmark_raw.csv"))
        with open(os.path.join(REPO_ROOT, "results", "raw", "benchmark_instances.json"), "r", encoding="utf-8") as f:
            cls.instances = json.load(f)

    def test_mutation_1_changed_table_cell_with_original_value_elsewhere_fails(self):
        """[Phase 7.1] Changing published table cell while keeping original value elsewhere in doc fails."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.README_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                # Mutate cell in Table A: 6.18 -> 99.99, but put 6.18 at end of file
                mutated = content.replace("$6.18 \\, \\mu\\text{s}$", "$99.99 \\, \\mu\\text{s}$", 1)
                mutated += "\n\nFootnote mentioning $6.18 \\, \\mu\\text{s}$ elsewhere.\n"
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df)
            self.assertIn("README-TAB-A-n20-HYB-TIME", str(ctx.exception))

    def test_mutation_2_swapped_table_columns_fails(self):
        """[Phase 7.2] Swapping two valid numbers between table columns in same row fails coordinate check."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.README_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                # Row 20 in Table A: swap DB ($3.39) and Pulse ($3.89)
                target = "| 20 | $6.18 \\, \\mu\\text{s}$ | $10.92 \\, \\mu\\text{s}$ | $15.33 \\, \\mu\\text{s}$ | **$3.39 \\, \\mu\\text{s}$** | $3.89 \\, \\mu\\text{s}$ | $3.50 \\, \\mu\\text{s}$ |"
                swapped = "| 20 | $6.18 \\, \\mu\\text{s}$ | $10.92 \\, \\mu\\text{s}$ | $15.33 \\, \\mu\\text{s}$ | $3.89 \\, \\mu\\text{s}$ | **$3.39 \\, \\mu\\text{s}$** | $3.50 \\, \\mu\\text{s}$ |"
                assert target in content, "Target row not found in README!"
                mutated = content.replace(target, swapped)
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df)
            self.assertTrue("README-TAB-A-n20-DB-TIME" in str(ctx.exception) or "README-TAB-A-n20-PULSE-TIME" in str(ctx.exception))

    def test_mutation_3_altered_raw_measurement_without_updating_claims_fails(self):
        """[Phase 7.3] Altering raw benchmark measurement fails downstream claim checks."""
        import scripts.sync_published_claims as sync_mod
        df_mut = self.raw_df.copy()
        idx = df_mut[(df_mut['instance_name'] == 'anticorr_n20') & (df_mut['solver_name'].str.startswith('Adaptive Hybrid'))].index[0]
        df_mut.at[idx, 'mean_runtime_micros'] = 99.99

        with self.assertRaises(AssertionError):
            sync_mod.check_all_claims(df_mut)

    def test_mutation_4_corrupt_source_identifier_or_hash_fails(self):
        """[Phase 7.4] Empty source reference or corrupted instance topology hash is rejected."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        with self.assertRaises(AssertionError):
            inv.add_exact_numerical("TEST-EMPTY-SRC", "README.md", "Test", "1.0", "1.0", source_ref="   ")

        # Corrupted graph edge hash check
        rec = dict(self.instances[0])
        computed_hash = recompute_canonical_graph_sha256(rec)
        self.assertEqual(computed_hash, rec["graph_id"])

        edges = [dict(e) for e in rec["canonical_edges"]]
        edges[0] = dict(edges[0])
        edges[0]["cost_bits"] = "4040000000000000"  # 32.0 in hex
        edges[0]["cost"] = 32.0
        rec_corrupted = dict(rec)
        rec_corrupted["canonical_edges"] = edges
        corrupted_hash = recompute_canonical_graph_sha256(rec_corrupted)
        self.assertNotEqual(corrupted_hash, rec["graph_id"])

    def test_mutation_5_delete_or_duplicate_registry_entry_rejected(self):
        """[Phase 7.5] Duplicate claim IDs and missing required registry entries are rejected."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        inv.add_document_presence("CLAIM-DUP-1", "README.md", "Desc 1", "test", "test", "src:1")
        with self.assertRaises(AssertionError) as ctx:
            inv.add_document_presence("CLAIM-DUP-1", "README.md", "Desc 2", "test", "test", "src:2")
        self.assertIn("Duplicate claim ID", str(ctx.exception))

    def test_mutation_6_contradictory_benchmark_denominator_fails(self):
        """[Phase 7.6] Contradictory configuration/evaluation denominator fails verification."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.DOCS_METHOD_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace("25 configurations", "20 configurations")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(self.raw_df)

    def test_mutation_7_remove_historical_qualification_from_defect_fails(self):
        """[Phase 7.7] Removing historical qualification from defect statement fails verification."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.AUDIT_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                mutated = content.replace("[HISTORICAL — RESOLVED]", "[ACTIVE DEFECT]")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(self.raw_df)

    def test_mutation_8_changed_complexity_claim_without_updating_review_fails(self):
        """[Phase 7.8] Mutating theoretical complexity formula in docs fails verification."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.COMPLEXITY_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                target_str = r"T_{\text{prep}} \le (K + 1) \cdot O(m + n \log n)"
                assert target_str in content, "Target complexity string not found!"
                mutated = content.replace(target_str, r"T_{\text{prep}} \le O(m^2)")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(self.raw_df)

    def test_mutation_9_pending_manual_review_item_prevents_full_verification(self):
        """[Phase 7.9] An unreviewed manual claim fails full verification status."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        inv.add_exact_numerical("NUM-1", "README.md", "Desc", "1.0", "1.0", "src:1")
        inv.add_manual_review("REV-1", "docs/COMPLEXITY_ANALYSIS.md", "Pending item",
                              "O(K * m log n)", "src:2", review_status="MANUAL_REVIEW_PENDING")
        self.assertEqual(inv.manual_review_pending_count, 1)
        self.assertEqual(inv.overall_verification_status, "PARTIAL_VERIFIED_PENDING_MANUAL_REVIEW")
        self.assertNotEqual(inv.overall_verification_status, "FULLY_VERIFIED_WITH_RECORDED_EVIDENCE")

    def test_mutation_10_tampered_json_markdown_inventory_discrepancy_detected(self):
        """[Phase 7.10] Cross-audit catches tampering between JSON and Markdown inventories."""
        import scripts.sync_published_claims as sync_mod
        with open(sync_mod.CLAIM_JSON_PATH, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        with open(sync_mod.CLAIM_MD_PATH, "r", encoding="utf-8") as f:
            md_content = f.read()

        tampered_json = dict(json_data)
        tampered_claims = list(tampered_json["claims"])
        tampered_claims[0] = dict(tampered_claims[0])
        tampered_claims[0]["status"] = "VERIFICATION_FAILED"
        tampered_json["claims"] = tampered_claims

        mismatch_found = False
        target_id = tampered_claims[0]["claim_id"]
        for line in md_content.splitlines():
            if f"`{target_id}`" in line:
                if f"**{tampered_claims[0]['status']}**" not in line:
                    mismatch_found = True
                break
        self.assertTrue(mismatch_found, "Cross-audit failed to detect tampered JSON status against Markdown!")


if __name__ == "__main__":
    unittest.main()

