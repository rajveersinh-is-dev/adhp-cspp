#!/usr/bin/env python3
"""
Independent Ground-Truth ILP Verification for ADHP-CSPP.

Formulates the Weight-Constrained Shortest Path Problem as a standard
0-1 Integer Linear Program (ILP) and solves it using HiGHS / SciPy MILP.
Validates exact agreement with ADHP solver output across generated instances.
"""

import sys
import json
import subprocess
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

def solve_cspp_ilp(n_nodes, edges, source, target, budget):
    """
    Solves CSPP as a 0-1 ILP:
        min sum c_e * x_e
        s.t. flow conservation at all vertices
             sum w_e * x_e <= budget
             x_e in {0, 1}
    """
    m = len(edges)
    c = np.array([e['cost'] for e in edges], dtype=float)
    w = np.array([e['weight'] for e in edges], dtype=float)

    # Incidence matrix A_flow: (n_nodes, m)
    A_flow = np.zeros((n_nodes, m), dtype=float)
    for idx, e in enumerate(edges):
        u, v = e['from'], e['to']
        A_flow[u, idx] += 1.0   # outgoing
        A_flow[v, idx] -= 1.0   # incoming

    b_flow = np.zeros(n_nodes, dtype=float)
    b_flow[source] = 1.0
    b_flow[target] = -1.0

    # Resource constraint row: w^T x <= budget
    A_total = np.vstack([A_flow, w.reshape(1, -1)])
    lhs = np.concatenate([b_flow, [-np.inf]])
    rhs = np.concatenate([b_flow, [budget]])

    constraints = LinearConstraint(A_total, lhs, rhs)
    integrality = np.ones(m) # All binary 0-1
    bounds = Bounds(0.0, 1.0)

    res = milp(c=c, integrality=integrality, constraints=constraints, bounds=bounds)

    if not res.success:
        return None, float('inf'), float('inf')

    opt_cost = float(res.fun)
    chosen_edges = np.where(res.x > 0.5)[0]
    opt_weight = float(np.sum(w[chosen_edges]))
    return chosen_edges, opt_cost, opt_weight

def main():
    print("=== ADHP-CSPP: Ground-Truth Verification against Independent HiGHS ILP Oracle ===")
    
    # Load serialized instance records
    instance_path = "results/raw/verification_instances.json"
    try:
        with open(instance_path, "r") as f:
            instances = json.load(f)
    except Exception as e:
        print(f"Error reading verification instances from {instance_path}: {e}")
        print("Please run `cargo run --bin verify_oracle --release` first.")
        sys.exit(1)

    print(f"Loaded {len(instances)} full problem instances from Rust solver.")
    print("Executing independent 0-1 ILP solver (SciPy / HiGHS MILP) on each instance...")

    verified_optimal = 0
    verified_infeasible = 0
    total_checked = 0
    discrepancies = []

    for inst in instances:
        total_checked += 1
        inst_id = inst["instance_id"]
        family = inst["family"]
        n_nodes = inst["num_nodes"]
        edges = inst["edges"]
        source = inst["source"]
        target = inst["target"]
        budget = inst["budget"]

        adhp_status = inst.get("adhp_status")
        adhp_cost = float(inst["adhp_cost"]) if inst.get("adhp_cost") is not None else float("inf")
        adhp_weight = float(inst["adhp_weight"]) if inst.get("adhp_weight") is not None else float("inf")

        # Solve independent 0-1 ILP using HiGHS
        chosen_edges, ilp_cost, ilp_weight = solve_cspp_ilp(n_nodes, edges, source, target, budget)

        if ilp_cost == float('inf'):
            # ILP found problem infeasible
            if adhp_status != "Infeasible":
                err = f"Instance {inst_id} ({family}): ILP proved Infeasible, but ADHP returned {adhp_status} (cost={adhp_cost})"
                discrepancies.append(err)
                print(f"  [DISCREPANCY] {err}")
            else:
                verified_infeasible += 1
        else:
            # ILP found optimal solution
            if adhp_status != "Optimal":
                err = f"Instance {inst_id} ({family}): ILP found feasible optimum (cost={ilp_cost:.4f}, weight={ilp_weight:.4f}), but ADHP returned {adhp_status}"
                discrepancies.append(err)
                print(f"  [DISCREPANCY] {err}")
            else:
                cost_diff = abs(ilp_cost - adhp_cost)
                rel_diff = cost_diff / max(1.0, abs(ilp_cost))
                if cost_diff > 1e-4 and rel_diff > 1e-5:
                    err = f"Instance {inst_id} ({family}): Cost mismatch! ILP cost={ilp_cost:.6f}, ADHP cost={adhp_cost:.6f}, diff={cost_diff:.6e}"
                    discrepancies.append(err)
                    print(f"  [DISCREPANCY] {err}")
                elif adhp_weight > budget + 1e-6:
                    err = f"Instance {inst_id} ({family}): ADHP weight {adhp_weight:.6f} exceeds budget {budget:.6f}"
                    discrepancies.append(err)
                    print(f"  [DISCREPANCY] {err}")
                else:
                    verified_optimal += 1

        if total_checked % 25 == 0:
            print(f"  Processed {total_checked}/{len(instances)} instances: {verified_optimal} optimal, {verified_infeasible} infeasible matched.")

    print("\n================ VERIFICATION SUMMARY ================")
    print(f"Total instances evaluated: {total_checked}")
    print(f"Exact optimal matches:      {verified_optimal}")
    print(f"Exact infeasible matches:   {verified_infeasible}")
    print(f"Total discrepancies:        {len(discrepancies)}")
    print("======================================================")

    if discrepancies:
        print(f"FAILED: {len(discrepancies)} discrepancies detected between ADHP and HiGHS ILP.")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {total_checked}/{total_checked} instances mathematically verified against HiGHS ILP oracle with 0 discrepancies.")

if __name__ == "__main__":
    main()
