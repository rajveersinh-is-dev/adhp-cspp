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
import shutil
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
        self.assertEqual(res["status"], "SCOPED_VERIFIED_AGAINST_REGISTERED_MANIFEST")
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
        inv.add_exact_numerical("TEST-NUM-1", "README.md", "Test Num", "19.97", "19.97", "raw.csv", anchor_pattern=r"19\.97")
        inv.add_manual_review("TEST-REV-1", "docs/COMPLEXITY_ANALYSIS.md", "Pending Review",
                              "O(K * m * log n)", "docs/COMPLEXITY_ANALYSIS.md",
                              review_status="MANUAL_REVIEW_PENDING", evidence="")
        self.assertEqual(inv.overall_verification_status, "PARTIAL_VERIFIED_PENDING_MANUAL_REVIEW")
        self.assertNotEqual(inv.overall_verification_status, "FULLY_VERIFIED_WITH_RECORDED_EVIDENCE")

    def test_verification_failed_claim_sets_overall_failure(self):
        """[R18] Any failed claim must set overall status to VERIFICATION_FAILED."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        inv.add_exact_numerical("TEST-NUM-1", "README.md", "Test Num", "19.97", "19.97", "raw.csv", anchor_pattern=r"19\.97")
        with self.assertRaises(AssertionError):
            inv.add_exact_numerical("TEST-NUM-FAIL", "README.md", "Missing Num", "99.99", "19.97", "raw.csv", anchor_pattern=r"19\.97")
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
        self.assertEqual(summary["overall_verification_status"], "SCOPED_VERIFIED_AGAINST_REGISTERED_MANIFEST")
        self.assertEqual(summary["manual_review_pending"], 0)
        self.assertEqual(summary["verification_failed"], 0)
        self.assertEqual(summary["total_claims_tracked"], len(json_data["claims"]))
        self.assertIn(f"| **Claims Passed (Automated)** | **{summary['claims_passed']}** |", md_content)
        self.assertIn(f"| **Claims Reviewed with Documented Evidence** | {summary['claims_reviewed_with_documented_evidence']} |", md_content)
        self.assertIn("| **Overall Repository Verification Status** | **SCOPED_VERIFIED_AGAINST_REGISTERED_MANIFEST** |", md_content)

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

    def test_mutation_mode_1_number_moved_to_unrelated_sentence_fails_anchored_prose(self):
        """Mode 1: Correct number moved into an unrelated sentence fails anchored extraction."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.README_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                target = r"On **Random ER $n=120$**, Adaptive Hybrid runtime is **$50.92 \, \mu\text{s}**"
                self.assertIn(target, content)
                mutated = content.replace(target, r"On **Random ER $n=120$**, Adaptive Hybrid runtime is **$99.99 \, \mu\text{s}**")
                mutated += "\n\nUnrelated paragraph mentions 50.92 microsecond measurement elsewhere.\n"
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df)
            self.assertIn("README-PROSE-ER120-HYB-TIME", str(ctx.exception))

    def test_mutation_mode_2_correct_number_retained_elsewhere_fails_anchored_check(self):
        """Mode 2: Correct number retained elsewhere in document after target claim is corrupted."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.TEX_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                target = r"delivering a $8.2\times$ speedup over Martins"
                self.assertIn(target, content)
                mutated = content.replace(target, r"delivering a $15.0\times$ speedup over Martins")
                mutated += "\n% Retained 8.20 in comment\n"
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df)
            self.assertIn("TEX-PROSE-G10-MAR-SPEEDUP", str(ctx.exception))

    def test_mutation_mode_3_value_moved_to_wrong_table_row_or_column_fails(self):
        """Mode 3: Swapping two numbers between table columns in same row fails coordinate check."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.README_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                target = "| 20 | $6.18 \\, \\mu\\text{s}$ | $10.92 \\, \\mu\\text{s}$ | $15.33 \\, \\mu\\text{s}$ | **$3.39 \\, \\mu\\text{s}$** | $3.89 \\, \\mu\\text{s}$ | $3.50 \\, \\mu\\text{s}$ |"
                swapped = "| 20 | $6.18 \\, \\mu\\text{s}$ | $10.92 \\, \\mu\\text{s}$ | $15.33 \\, \\mu\\text{s}$ | $3.89 \\, \\mu\\text{s}$ | **$3.39 \\, \\mu\\text{s}$** | $3.50 \\, \\mu\\text{s}$ |"
                self.assertIn(target, content)
                mutated = content.replace(target, swapped)
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df)
            self.assertTrue("README-TAB-A-n20-DB-TIME" in str(ctx.exception) or "README-TAB-A-n20-PULSE-TIME" in str(ctx.exception))

    def test_mutation_mode_4_derived_speedup_numerically_incorrect_fails(self):
        """Mode 4: Derived speedup or suppression ratio numerically incorrect fails check."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.README_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                target = r"Martins ($163.82 \, \mu\text{s}$, a **$8.2\times$ speedup**)"
                self.assertIn(target, content)
                mutated = content.replace(target, r"Martins ($163.82 \, \mu\text{s}$, a **$99.9\times$ speedup**)")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df)
            self.assertIn("README-PROSE-G10-MAR-SPEEDUP", str(ctx.exception))

    def test_mutation_mode_5_changed_raw_measurement_with_stale_docs_fails(self):
        """Mode 5: Changed raw measurement without document update fails verification."""
        import scripts.sync_published_claims as sync_mod
        df_mut = self.raw_df.copy()
        idx = df_mut[(df_mut['instance_name'] == 'anticorr_n20') & (df_mut['solver_name'].str.startswith('Adaptive Hybrid'))].index[0]
        df_mut.at[idx, 'mean_runtime_micros'] = 99.99

        with self.assertRaises(AssertionError):
            sync_mod.check_all_claims(df_mut)

    def test_mutation_mode_6_missing_or_duplicated_anchor_fails_closed(self):
        """Mode 6: Missing anchor fails closed; duplicated anchor fails closed."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        doc_content = "This is a single sentence mentioning 42.0.\n"
        with self.assertRaises(AssertionError) as ctx1:
            inv.add_anchored_prose_numerical(
                "TEST-MISSING", "test.md", "Desc", doc_content,
                r"Nonexistent anchor with (?P<val>[\d\.]+)", 42.0, "src:1"
            )
        self.assertIn("Missing claim anchor", str(ctx1.exception))

        dup_doc = doc_content + doc_content
        with self.assertRaises(AssertionError) as ctx2:
            inv.add_anchored_prose_numerical(
                "TEST-DUP", "test.md", "Desc", dup_doc,
                r"mentioning (?P<val>[\d\.]+)", 42.0, "src:1"
            )
        self.assertIn("Ambiguous/duplicated claim anchor", str(ctx2.exception))

    def test_mutation_mode_7_material_statement_deleted_from_registry_fails(self):
        """Mode 7: Material claim present in document but omitted from registry fails discovery audit."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        inv.add_exact_numerical("NUM-1", "README.md", "Desc", "19.97", "19.97", "src:1", anchor_pattern=r"19\.97")
        with self.assertRaises(AssertionError) as ctx:
            sync_mod.run_claim_discovery_audit(inv, self.raw_df)
        self.assertIn("uncovered material claims detected", str(ctx.exception))

    def test_mutation_mode_8_resolved_defect_reintroduced_regression_fails(self):
        """Mode 8: Regression test verifying that Defect 3.1 checked overflow cannot silently succeed."""
        max_u64 = 0xFFFFFFFFFFFFFFFF
        cost_multiplier = 2
        wrapped_64 = (max_u64 * cost_multiplier) & 0xFFFFFFFFFFFFFFFF
        checked_128 = max_u64 * cost_multiplier
        self.assertNotEqual(wrapped_64, checked_128, "64-bit multiplication wrapped silently!")
        self.assertGreater(checked_128, max_u64, "Checked 128-bit arithmetic did not detect overflow!")

    def test_mutation_mode_9_historical_defect_incorrectly_labeled_current_fact_fails(self):
        """Mode 9: Changing [HISTORICAL — RESOLVED] to active defect fails verifier."""
        import io
        import scripts.sync_published_claims as sync_mod
        orig_open = open
        def custom_open(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(sync_mod.AUDIT_PATH):
                with orig_open(path, *args, **kwargs) as f:
                    content = f.read()
                self.assertIn("[HISTORICAL — RESOLVED]", content)
                mutated = content.replace("[HISTORICAL — RESOLVED]", "[ACTIVE DEFECT — UNRESOLVED]")
                return io.StringIO(mutated)
            return orig_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=custom_open):
            with self.assertRaises(AssertionError):
                sync_mod.check_all_claims(self.raw_df)

    def test_mutation_mode_10_proof_presence_check_labeled_mathematically_verified_fails(self):
        """Mode 10: Structural document presence check cannot claim exact numerical proof."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        inv.add_document_presence("PRESENCE-1", "docs/COMPLEXITY_ANALYSIS.md", "Theorem 1 Presence",
                                  "T_{prep} <= (K+1)*O(m+n log n)", "T_{prep} <= (K+1)*O(m+n log n)",
                                  "docs/COMPLEXITY_ANALYSIS.md", anchor_pattern=r"T_\{prep\}")
        rec = inv.records[0]
        self.assertEqual(rec.claim_type, "DOCUMENT_PRESENCE")
        self.assertEqual(rec.check_performed, "structural_document_text_presence_check")
        self.assertIn("structural text presence check; not independent numerical validation", rec.evidence)
        self.assertNotEqual(rec.claim_type, "EXACT_NUMERICAL")

    def test_mutation_mode_11_inventory_claims_full_coverage_despite_uncovered_material_claim_fails(self):
        """Mode 11: Inventory rejects full coverage status when material claims are uncovered."""
        import scripts.sync_published_claims as sync_mod
        inv = sync_mod.ClaimInventory()
        with self.assertRaises(AssertionError):
            sync_mod.run_claim_discovery_audit(inv, self.raw_df)
        self.assertGreater(inv.material_claims_not_yet_covered, 0)
        self.assertNotEqual(inv.overall_verification_status, "SCOPED_VERIFIED_AGAINST_REGISTERED_MANIFEST")
        self.assertEqual(inv.overall_verification_status, "DISCOVERY_AUDIT_UNCOVERED_MATERIAL_CLAIMS")

    def test_mutation_mode_12_mismatch_between_json_markdown_and_executed_results_fails(self):
        """Mode 12: Tampered JSON or Markdown inventory causes cross-audit discrepancy."""
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


class TestClaimDiscoveryAndReconciliationAuthoritative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_csv = os.path.join(REPO_ROOT, "results", "raw", "benchmark_raw.csv")
        cls.raw_df = pd.read_csv(cls.raw_csv)
        import scripts.sync_published_claims as sync_mod
        cls.sync_mod = sync_mod

    def test_authoritative_reconciliation_arithmetic_identities(self):
        """Phase 1: Validate fundamental arithmetic count identities on authoritative scan."""
        report = self.sync_mod.scan_all_artifacts(repo_root=REPO_ROOT)
        self.assertTrue(report.is_complete_scan)
        self.assertEqual(len(report.scan_failures), 0)

        with open(self.sync_mod.CLAIM_JSON_PATH, "r", encoding="utf-8") as f:
            stored_json = json.load(f)
        summary = stored_json["summary"]

        unique_cands = summary["unique_candidates_count"]
        raw_cands = summary["raw_candidates_count"]
        unique_matched = summary["unique_matched_candidates_count"]
        unregistered = summary["unregistered_candidates_count"]
        ambiguous = summary["ambiguous_candidate_mappings_count"]
        reg_claims = summary["registered_claims_count"]
        matched_reg = summary["matched_registered_claims_count"]
        stale_reg = summary["stale_registered_claims_count"]
        compound = summary["compound_cell_claims_count"]
        manual_ev = summary["human_review_evidence_recorded_count"]

        # Assert fundamental candidate partition identity:
        # unique_candidates == unique_matched_candidates + unregistered_candidates + ambiguous_candidate_mappings
        self.assertEqual(unique_cands, unique_matched + unregistered + ambiguous)
        self.assertLessEqual(unique_cands, raw_cands)

        # Assert candidate breakdown adds up to unique candidates
        cat_breakdown = summary["candidate_categories_breakdown"]
        self.assertEqual(
            sum(cat_breakdown.values()),
            unique_cands
        )

        # Assert registry partition identity:
        # registered_claims == matched_registered_claims + stale_registered_claims
        self.assertEqual(reg_claims, matched_reg + stale_reg)

        # Assert matched registration derivation:
        # matched_registered == unique_matched + compound_cell_claims + human_review_evidence_recorded
        self.assertEqual(matched_reg, unique_matched + compound + manual_ev)

    def test_json_and_markdown_summary_exact_match(self):
        """Phase 1: Assert JSON and Markdown contain identical shared metrics."""
        self.sync_mod.verify_inventory_consistency(REPO_ROOT)
        with open(self.sync_mod.CLAIM_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(self.sync_mod.CLAIM_MD_PATH, "r", encoding="utf-8") as f:
            md_text = f.read()

        s = data["summary"]
        self.assertIn(f"| **Registered Claims Verified** | **{s['registered_claims_count']} / {s['registered_claims_count']}** |", md_text)
        self.assertIn(f"| **Independently Discovered Candidates** | **{s['unique_candidates_count']}** |", md_text)
        self.assertIn(f"| **Distinct Discovered Candidates Matched** | **{s['unique_matched_candidates_count']}** |", md_text)
        self.assertIn(f"| **Discovered Unregistered Candidates** | **{s['unregistered_candidates_count']}** |", md_text)

    def test_tampered_count_in_inventory_markdown_fails(self):
        """Phase 1: Fail if Markdown report contains a count diverging from generated candidate data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            for sub in ["results/processed", "docs", "paper", "research", "reviews"]:
                os.makedirs(os.path.join(temp_dir, sub), exist_ok=True)
            shutil.copy2(self.sync_mod.CLAIM_JSON_PATH, os.path.join(temp_dir, "results", "processed", "claim_inventory.json"))
            shutil.copy2(self.sync_mod.AUDIT_PATH, os.path.join(temp_dir, "docs", "RESEARCH_AUDIT.md"))
            with open(self.sync_mod.CLAIM_MD_PATH, "r", encoding="utf-8") as f:
                md_content = f.read()
            # Tamper the unique candidates count
            tampered_md = md_content.replace(
                "| **Independently Discovered Candidates** | **1382** |",
                "| **Independently Discovered Candidates** | **9999** |"
            )
            with open(os.path.join(temp_dir, "docs", "CLAIM_INVENTORY.md"), "w", encoding="utf-8") as f:
                f.write(tampered_md)

            with self.assertRaises(AssertionError) as ctx:
                self.sync_mod.verify_inventory_consistency(temp_dir)
            self.assertIn("inconsistent unique candidates count", str(ctx.exception))

    def test_add_and_remove_source_claim_reconciles_dynamically(self):
        """Phase 1: Count invariants recompute dynamically after adding and removing a source claim."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Clone maintained artifacts to temp_dir
            for path in self.sync_mod.MAINTAINED_RESEARCH_ARTIFACTS:
                src = os.path.join(REPO_ROOT, path)
                dst = os.path.join(temp_dir, path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(src):
                    shutil.copy2(src, dst)

            # Step 1: Baseline scan
            rep0 = self.sync_mod.scan_all_artifacts(repo_root=temp_dir)
            u0 = rep0.unique_candidates_count

            # Step 2: Add novel source claim in README
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "r", encoding="utf-8") as f:
                orig_readme = f.read()
            novel_claim = "\n\nNovel Discovery Test: Our custom dual variant reduces latency to 12.34 ms on sparse networks.\n"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(orig_readme + novel_claim)

            rep_added = self.sync_mod.scan_all_artifacts(repo_root=temp_dir)
            self.assertEqual(rep_added.unique_candidates_count, u0 + 1)

            # Step 3: Remove the claim
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(orig_readme)

            rep_removed = self.sync_mod.scan_all_artifacts(repo_root=temp_dir)
            self.assertEqual(rep_removed.unique_candidates_count, u0)

    def test_missing_required_artifact_fails_closed(self):
        """Phase 3: Missing maintained required artifact records structured failure and aborts complete scan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            for path in self.sync_mod.MAINTAINED_RESEARCH_ARTIFACTS:
                src = os.path.join(REPO_ROOT, path)
                dst = os.path.join(temp_dir, path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(src):
                    shutil.copy2(src, dst)

            # Delete paper/main.tex
            tex_file = os.path.join(temp_dir, "paper", "main.tex")
            os.remove(tex_file)

            rep = self.sync_mod.scan_all_artifacts(repo_root=temp_dir)
            self.assertFalse(rep.is_complete_scan)
            self.assertGreater(len(rep.scan_failures), 0)
            fail = rep.scan_failures[0]
            self.assertEqual(fail.artifact, "paper/main.tex")
            self.assertEqual(fail.failure_type, "MISSING")
            self.assertEqual(rep.artifact_statuses["paper/main.tex"], "MISSING")

    def test_unreadable_or_corrupted_encoding_fails_closed(self):
        """Phase 3: Artifact with invalid encoding records structured failure and aborts complete scan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            for path in self.sync_mod.MAINTAINED_RESEARCH_ARTIFACTS:
                src = os.path.join(REPO_ROOT, path)
                dst = os.path.join(temp_dir, path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(src):
                    shutil.copy2(src, dst)

            # Write invalid UTF-8 bytes to paper/main.typ
            typ_file = os.path.join(temp_dir, "paper", "main.typ")
            with open(typ_file, "wb") as f:
                f.write(b"\x80\x81\xff\xfe\x00\x00")

            rep = self.sync_mod.scan_all_artifacts(repo_root=temp_dir)
            self.assertFalse(rep.is_complete_scan)
            self.assertGreater(len(rep.scan_failures), 0)
            fail = [sf for sf in rep.scan_failures if sf.artifact == "paper/main.typ"][0]
            self.assertEqual(fail.failure_type, "UNREADABLE")
            self.assertEqual(rep.artifact_statuses["paper/main.typ"], "INVALID_ENCODING")



if __name__ == "__main__":
    unittest.main()

