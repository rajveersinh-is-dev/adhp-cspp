#!/usr/bin/env python3
"""
Unit tests for scripts/verify_benchmarks.py.

Validates that the benchmark verifier:
1. Passes on genuine, untampered benchmark data and instance registry.
2. Fails (raises AssertionError) when columns are missing.
3. Fails when duplicate evaluations exist.
4. Fails when a required configuration or solver is missing.
5. Fails when negative runtimes or invalid decompositions are injected.
6. Fails when summary table statistics diverge from raw data.
7. Fails when empirical regressions are suppressed (honesty check).
8. Fails when instance evaluation count is corrupted.
9. Fails when instance graph_id is spoofed or tampered with.
10. Fails when edge weights, costs, or budget bits are modified (SHA-256 integrity).
11. Fails when instance schema version is unsupported.
12. Fails when instance deduplication reveals graph collision across distinct instances.
13. Fails when published headline assertions are violated.
"""

import copy
import json
import os
import sys
import tempfile
import unittest
import pandas as pd

# Add repository root to pythonpath
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from scripts.verify_benchmarks import verify_benchmarks


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

    def test_genuine_data_passes(self):
        """Genuine dataset passes all consistency assertions from file paths."""
        self.assertTrue(verify_benchmarks(self.raw_csv, self.summary_csv, self.instances_json))

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
        corrupted_insts = self.cached_instances[:-1]  # Drop one record
        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_corrupted_instance_identity_spoof_fails(self):
        """Tampering with graph_id directly must trigger SHA-256 verification failure."""
        corrupted_insts = copy.deepcopy(self.cached_instances)
        corrupted_insts[0]['graph_id'] = '0' * 64
        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_tampered_edge_weight_fails_sha256(self):
        """Tampering with an edge weight in canonical_edges must cause SHA-256 mismatch."""
        corrupted_insts = copy.deepcopy(self.cached_instances)
        corrupted_insts[0]['canonical_edges'][0]['weight_bits'] = '4050000000000000'
        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_tampered_budget_bits_fails_sha256(self):
        """Tampering with budget_bits must cause SHA-256 mismatch."""
        corrupted_insts = copy.deepcopy(self.cached_instances)
        corrupted_insts[0]['budget_bits'] = 'ffffffffffffffff'
        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_unsupported_schema_version_fails(self):
        """Invalid schema_version must fail verification."""
        corrupted_insts = copy.deepcopy(self.cached_instances)
        corrupted_insts[0]['schema_version'] = 'unsupported-schema-v99'
        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_corrupted_instance_identity_deduplication_fails(self):
        """Instance registry where distinct instances share graph content collapses count and must fail."""
        corrupted_insts = copy.deepcopy(self.cached_instances)
        # Duplicate record 0 content into record 1 in Suite 1, reducing distinct count to 199
        corrupted_insts[1]['nodes'] = corrupted_insts[0]['nodes']
        corrupted_insts[1]['source'] = corrupted_insts[0]['source']
        corrupted_insts[1]['target'] = corrupted_insts[0]['target']
        corrupted_insts[1]['budget_bits'] = corrupted_insts[0]['budget_bits']
        corrupted_insts[1]['canonical_edges'] = copy.deepcopy(corrupted_insts[0]['canonical_edges'])
        corrupted_insts[1]['graph_id'] = corrupted_insts[0]['graph_id']

        with self.assertRaises(AssertionError):
            verify_benchmarks(self.raw_csv, self.summary_csv, corrupted_insts)

    def test_corrupted_published_headline_fails(self):
        """Mutating a published headline value in raw benchmark data must fail verification."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = df.copy()
        g10_idx = df_corrupted[(df_corrupted['instance_name'] == 'grid_10x10') & 
                               (df_corrupted['solver_name'] == 'Adaptive Hybrid ADHP')].index[0]
        df_corrupted.loc[g10_idx, 'mean_runtime_micros'] = 999.0
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv, self.cached_instances)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
