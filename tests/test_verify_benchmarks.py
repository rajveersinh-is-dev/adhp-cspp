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
        self.assertTrue(os.path.exists(self.raw_csv), "Raw benchmark CSV missing")
        self.assertTrue(os.path.exists(self.summary_csv), "Summary table CSV missing")

    def test_genuine_data_passes(self):
        """Genuine dataset passes all consistency assertions."""
        self.assertTrue(verify_benchmarks(self.raw_csv, self.summary_csv))

    def test_missing_column_fails(self):
        """Dropping a required column must fail verification."""
        df = pd.read_csv(self.raw_csv)
        df_corrupted = df.drop(columns=['mean_preprocessing_micros'])
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            df_corrupted.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            with self.assertRaises(AssertionError):
                verify_benchmarks(temp_path, self.summary_csv)
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
                verify_benchmarks(temp_path, self.summary_csv)
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
                verify_benchmarks(temp_path, self.summary_csv)
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
                verify_benchmarks(temp_path, self.summary_csv)
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
                verify_benchmarks(self.raw_csv, temp_path)
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
                verify_benchmarks(temp_path, self.summary_csv)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
