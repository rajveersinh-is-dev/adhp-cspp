#!/usr/bin/env python3
"""
Unit tests for scripts/verify_benchmarks.py.

Validates that the benchmark verifier:
1. Passes on genuine, untampered benchmark data.
2. Fails (raises AssertionError) when columns are missing.
3. Fails when duplicate evaluations exist.
4. Fails when a required configuration or solver is missing.
5. Fails when negative runtimes or invalid decompositions are injected.
6. Fails when summary table statistics diverge from raw data.
7. Fails when empirical regressions are suppressed (honesty check).
"""

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
    def setUp(self):
        self.raw_csv = os.path.join(REPO_ROOT, "results", "raw", "benchmark_raw.csv")
        self.summary_csv = os.path.join(REPO_ROOT, "results", "processed", "summary_table.csv")
        self.instances_json = os.path.join(REPO_ROOT, "results", "raw", "benchmark_instances.json")
        self.assertTrue(os.path.exists(self.raw_csv), "Raw benchmark CSV missing")
        self.assertTrue(os.path.exists(self.summary_csv), "Summary table CSV missing")
        self.assertTrue(os.path.exists(self.instances_json), "Benchmark instances JSON missing")

    def test_genuine_data_passes(self):
        """Genuine dataset passes all consistency assertions."""
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
                verify_benchmarks(temp_path, self.summary_csv, self.instances_json)
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
                verify_benchmarks(temp_path, self.summary_csv, self.instances_json)
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
                verify_benchmarks(temp_path, self.summary_csv, self.instances_json)
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
                verify_benchmarks(temp_path, self.summary_csv, self.instances_json)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_summary_mismatch_fails(self):
        """Discrepancy between raw data and summary table must fail verification."""
        sum_df = pd.read_csv(self.summary_csv)
        sum_corrupted = sum_df.copy()
        # Alter average runtime for first entry
        col = sum_corrupted.columns[2]
        sum_corrupted.loc[0, col] = 9999.99
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            sum_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(self.raw_csv, temp_path, self.instances_json)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_suppressed_regression_fails(self):
        """Falsifying empirical results to suppress regressions must fail."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = df.copy()
        # Invert random_er_n30 so ADHP artificially beats Martins
        adhp_idx = df_corrupted[(df_corrupted['instance_name'] == 'random_er_n30') & 
                                (df_corrupted['solver_name'].str.startswith('ADHP'))].index[0]
        df_corrupted.loc[adhp_idx, 'mean_runtime_micros'] = 0.01
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv, self.instances_json)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_corrupted_instance_registry_count_fails(self):
        """Instance registry with missing evaluation record must fail verification."""
        import json
        with open(self.instances_json, 'r', encoding='utf-8') as f:
            insts = json.load(f)
        corrupted_insts = insts[:-1]  # Drop one record
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump(corrupted_insts, tf)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(self.raw_csv, self.summary_csv, temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_corrupted_instance_identity_deduplication_fails(self):
        """Instance registry where canonical graph_id is duplicated across distinct instances must fail."""
        import json
        with open(self.instances_json, 'r', encoding='utf-8') as f:
            insts = json.load(f)
        corrupted_insts = list(insts)
        # Force instance 1 and instance 2 to have identical hash in Suite 1, reducing distinct count to 199
        corrupted_insts[1]['graph_id'] = corrupted_insts[0]['graph_id']
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump(corrupted_insts, tf)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(self.raw_csv, self.summary_csv, temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_corrupted_published_headline_fails(self):
        """Mutating a published headline value in raw benchmark data must fail verification."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = df.copy()
        # Mutate Grid 10x10 Hybrid runtime from 33.74 to 999.0
        g10_idx = df_corrupted[(df_corrupted['instance_name'] == 'grid_10x10') & 
                               (df_corrupted['solver_name'] == 'Adaptive Hybrid ADHP')].index[0]
        df_corrupted.loc[g10_idx, 'mean_runtime_micros'] = 999.0
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv, self.instances_json)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
