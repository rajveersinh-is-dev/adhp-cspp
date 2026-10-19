#!/usr/bin/env python3
"""
Unit tests for ILP oracle status classification in scripts/verify_against_ilp.py.

Verifies:
1. SciPy status 0 maps to IlpStatus.OPTIMAL.
2. SciPy status 2 maps to IlpStatus.INFEASIBLE.
3. SciPy status 1 (timeout / iteration limit) maps to IlpStatus.TIMEOUT (inconclusive).
4. SciPy status 4 (numerical difficulty) maps to IlpStatus.NUMERICAL_ERROR (inconclusive).
5. SciPy status 3 maps to IlpStatus.UNBOUNDED.
6. Unknown status codes map to IlpStatus.UNKNOWN (inconclusive).
7. Inconclusive outcomes (status 1, 4, unknown) NEVER increment verified agreement counts.
"""

import os
import sys
import unittest
from types import SimpleNamespace

# Add repository root to pythonpath
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from scripts.verify_against_ilp import (
    IlpStatus,
    classify_milp_result,
    verify_instances_against_ilp,
)


class TestIlpStatusClassification(unittest.TestCase):
    def test_status_0_is_optimal(self):
        mock_res = SimpleNamespace(status=0, success=True)
        self.assertEqual(classify_milp_result(mock_res), IlpStatus.OPTIMAL)

    def test_status_2_is_infeasible(self):
        mock_res = SimpleNamespace(status=2, success=False)
        self.assertEqual(classify_milp_result(mock_res), IlpStatus.INFEASIBLE)

    def test_status_1_is_timeout_not_infeasible(self):
        mock_res = SimpleNamespace(status=1, success=False)
        status = classify_milp_result(mock_res)
        self.assertEqual(status, IlpStatus.TIMEOUT)
        self.assertNotEqual(status, IlpStatus.INFEASIBLE)

    def test_status_4_is_numerical_error_not_infeasible(self):
        mock_res = SimpleNamespace(status=4, success=False)
        status = classify_milp_result(mock_res)
        self.assertEqual(status, IlpStatus.NUMERICAL_ERROR)
        self.assertNotEqual(status, IlpStatus.INFEASIBLE)

    def test_status_3_is_unbounded(self):
        mock_res = SimpleNamespace(status=3, success=False)
        self.assertEqual(classify_milp_result(mock_res), IlpStatus.UNBOUNDED)

    def test_unknown_status_is_unknown(self):
        mock_res = SimpleNamespace(status=99, success=False)
        self.assertEqual(classify_milp_result(mock_res), IlpStatus.UNKNOWN)

    def test_inconclusive_never_increments_verified_counts(self):
        """
        Tests that an instance resulting in timeout/error is recorded as
        inconclusive and does NOT increase verified_optimal or verified_infeasible.
        """
        instances = [
            {
                "instance_id": "test_inconclusive",
                "family": "synthetic",
                "num_nodes": 2,
                "edges": [{"from": 0, "to": 1, "cost": 1.0, "weight": 1.0}],
                "source": 0,
                "target": 1,
                "budget": 5.0,
                "adhp_status": "Optimal",
                "adhp_cost": 1.0,
                "adhp_weight": 1.0,
                "adhp_edge_path": [0],
            }
        ]

        import scripts.verify_against_ilp as ilp_mod
        orig_solve = ilp_mod.solve_cspp_ilp

        try:
            ilp_mod.solve_cspp_ilp = lambda *args: (IlpStatus.TIMEOUT, None, float('nan'), float('nan'), None)
            res = verify_instances_against_ilp(instances)
            self.assertEqual(res["verified_optimal"], 0)
            self.assertEqual(res["verified_infeasible"], 0)
            self.assertEqual(res["inconclusive"], 1)
            self.assertEqual(len(res["discrepancies"]), 0)
        finally:
            ilp_mod.solve_cspp_ilp = orig_solve

    def test_validate_edge_path_correctness(self):
        """Validates path topology, edge continuity, cost/weight recalculation."""
        from scripts.verify_against_ilp import validate_edge_path

        edges = [
            {"from": 0, "to": 1, "cost": 10, "weight": 5},
            {"from": 1, "to": 2, "cost": 15, "weight": 8},
            {"from": 0, "to": 2, "cost": 100, "weight": 2},
        ]

        # Valid 2-edge path (0 -> 1 -> 2)
        valid, cost, weight, err = validate_edge_path(edges, 0, 2, 20, [0, 1])
        self.assertTrue(valid)
        self.assertEqual(cost, 25)
        self.assertEqual(weight, 13)
        self.assertIsNone(err)

        # Budget exceeded (weight 13 > budget 10)
        valid, cost, weight, err = validate_edge_path(edges, 0, 2, 10, [0, 1])
        self.assertFalse(valid)
        self.assertIn("exceeds budget", err)

        # Disconnected edges (step 0 ends at 1, step 1 starts at 0)
        valid, _, _, err = validate_edge_path(edges, 0, 2, 20, [0, 2])
        self.assertFalse(valid)
        self.assertIn("starts at 0, expected 1", err)

        # Wrong target (path ends at 1, expected 2)
        valid, _, _, err = validate_edge_path(edges, 0, 2, 20, [0])
        self.assertFalse(valid)
        self.assertIn("expected target 2", err)

    def test_integer_ilp_differential_mutations(self):
        """Tests that verify_integer_instances_against_ilp detects discrepancies when mutated."""
        from scripts.verify_against_ilp import verify_integer_instances_against_ilp

        base_inst = {
            "instance_id": "test_int_1",
            "family": "synthetic",
            "num_nodes": 3,
            "source": 0,
            "target": 2,
            "budget": 20,
            "edges": [
                {"from": 0, "to": 1, "cost": 5, "weight": 5},
                {"from": 1, "to": 2, "cost": 5, "weight": 5},
            ],
            "int_adhp_status": "Optimal",
            "int_adhp_cost": 10,
            "int_adhp_weight": 10,
            "int_adhp_edge_path": [0, 1],
        }

        # 1. Genuine instance passes
        res = verify_integer_instances_against_ilp([base_inst])
        self.assertEqual(res["verified_optimal"], 1)
        self.assertEqual(len(res["discrepancies"]), 0)

        # 2. Mutated cost triggers discrepancy
        mutated_cost = dict(base_inst, int_adhp_cost=999)
        res = verify_integer_instances_against_ilp([mutated_cost])
        self.assertEqual(len(res["discrepancies"]), 1)
        self.assertIn("cost mismatch", res["discrepancies"][0].lower())

        # 3. Mutated status triggers discrepancy
        mutated_status = dict(base_inst, int_adhp_status="Infeasible")
        res = verify_integer_instances_against_ilp([mutated_status])
        self.assertEqual(len(res["discrepancies"]), 1)
        self.assertIn("reported Infeasible", res["discrepancies"][0])

        # 4. Mutated path (corrupted edge index) triggers discrepancy
        mutated_path = dict(base_inst, int_adhp_edge_path=[0])
        res = verify_integer_instances_against_ilp([mutated_path])
        self.assertEqual(len(res["discrepancies"]), 1)
        self.assertIn("Invalid path", res["discrepancies"][0])


if __name__ == "__main__":
    unittest.main()

