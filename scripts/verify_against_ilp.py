#!/usr/bin/env python3
"""
Rigorous Independent Ground-Truth ILP Verification for ADHP-CSPP.

Formulates the Weight-Constrained Shortest Path Problem as a 0-1 Integer Linear
Program (ILP) and solves it using SciPy's HiGHS-backed MILP solver.

Key Correctness Guarantees:
1. Rigorous Solver Status Classification:
   - Status 0: Proven Optimal.
   - Status 2: Proven Infeasible.
   - Status 1: Time/Iteration Limit Reached -> Inconclusive (NEVER treated as infeasible).
   - Status 3: Unbounded -> Discrepancy for CSPP.
   - Status 4: Numerical Difficulty -> Inconclusive (NEVER treated as infeasible).
   - Inconclusive runs are explicitly tracked and never increment verified agreement counts.
2. Differential Verification for Floating-Point Solver (AdhpSolver).
3. Direct Differential Verification for Exact Integer Solver (IntAdhpSolver).
"""

import sys
import json
import os
from enum import Enum
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds


class IlpStatus(Enum):
    OPTIMAL = "Optimal"
    INFEASIBLE = "Infeasible"
    TIMEOUT = "Timeout"
    UNBOUNDED = "Unbounded"
    NUMERICAL_ERROR = "NumericalError"
    UNKNOWN = "Unknown"


def classify_milp_result(res):
    """
    Classifies a scipy.optimize.milp result based on its documented status code.
    SciPy MILP Status Codes:
      0 : Optimal solution found
      1 : Iteration or time limit reached
      2 : Problem is infeasible
      3 : Problem is unbounded
      4 : Other numerical difficulties
    """
    status_code = getattr(res, "status", None)
    if status_code == 0:
        return IlpStatus.OPTIMAL
    elif status_code == 2:
        return IlpStatus.INFEASIBLE
    elif status_code == 1:
        return IlpStatus.TIMEOUT
    elif status_code == 3:
        return IlpStatus.UNBOUNDED
    elif status_code == 4:
        return IlpStatus.NUMERICAL_ERROR
    else:
        return IlpStatus.UNKNOWN


def solve_cspp_ilp(n_nodes, edges, source, target, budget):
    """
    Solves CSPP as a 0-1 ILP:
        min sum c_e * x_e
        s.t. sum_{e outgoing u} x_e - sum_{e incoming u} x_e = b_u for all u
             sum w_e * x_e <= budget
             x_e in {0, 1}

    Returns:
        (status: IlpStatus, chosen_edge_indices, opt_cost, opt_weight, raw_res)
    """
    m = len(edges)
    if m == 0:
        if source == target:
            return IlpStatus.OPTIMAL, [], 0.0, 0.0, None
        return IlpStatus.INFEASIBLE, None, float('inf'), float('inf'), None

    c = np.array([float(e['cost']) for e in edges], dtype=float)
    w = np.array([float(e['weight']) for e in edges], dtype=float)

    # Incidence matrix A_flow: (n_nodes, m)
    A_flow = np.zeros((n_nodes, m), dtype=float)
    for idx, e in enumerate(edges):
        u, v = int(e['from']), int(e['to'])
        if u < n_nodes:
            A_flow[u, idx] += 1.0  # outgoing
        if v < n_nodes:
            A_flow[v, idx] -= 1.0  # incoming

    b_flow = np.zeros(n_nodes, dtype=float)
    if source < n_nodes:
        b_flow[source] += 1.0
    if target < n_nodes:
        b_flow[target] -= 1.0

    # Resource constraint row: w^T x <= budget
    A_total = np.vstack([A_flow, w.reshape(1, -1)])
    lhs = np.concatenate([b_flow, [-np.inf]])
    rhs = np.concatenate([b_flow, [float(budget)]])

    constraints = LinearConstraint(A_total, lhs, rhs)
    integrality = np.ones(m)  # All binary 0-1
    bounds = Bounds(0.0, 1.0)

    res = milp(c=c, integrality=integrality, constraints=constraints, bounds=bounds)
    status = classify_milp_result(res)

    if status == IlpStatus.OPTIMAL:
        opt_cost = float(res.fun)
        chosen_edges = [int(i) for i in np.where(res.x > 0.5)[0]]
        opt_weight = float(np.sum(w[chosen_edges]))
        return status, chosen_edges, opt_cost, opt_weight, res
    elif status == IlpStatus.INFEASIBLE:
        return status, None, float('inf'), float('inf'), res
    else:
        # Inconclusive or unbounded
        return status, None, float('nan'), float('nan'), res


def validate_edge_path(edges, source, target, budget, edge_indices):
    """
    Validates that edge_indices forms a valid, contiguous (source -> target) path
    satisfying the budget constraint, and recalculates its exact cost and weight.
    """
    if not edge_indices:
        if source == target:
            return True, 0.0, 0.0, None
        return False, 0.0, 0.0, f"Empty edge path for distinct vertices ({source} -> {target})"

    total_cost = 0.0
    total_weight = 0.0
    curr_node = source

    for step, e_id in enumerate(edge_indices):
        if e_id < 0 or e_id >= len(edges):
            return False, 0.0, 0.0, f"Edge index {e_id} at step {step} out of bounds (len={len(edges)})"
        edge = edges[e_id]
        if edge["from"] != curr_node:
            return False, 0.0, 0.0, f"Edge {e_id} starts at {edge['from']}, expected {curr_node} at step {step}"
        total_cost += float(edge["cost"])
        total_weight += float(edge["weight"])
        curr_node = edge["to"]

    if curr_node != target:
        return False, 0.0, 0.0, f"Path terminates at {curr_node}, expected target {target}"

    if total_weight > budget + 1e-6:
        return False, total_cost, total_weight, f"Path weight {total_weight:.6f} exceeds budget {budget:.6f}"

    return True, total_cost, total_weight, None


def verify_instances_against_ilp(instances):
    """
    Executes independent ILP verification over floating-point instances.
    """
    verified_optimal = 0
    verified_infeasible = 0
    inconclusive_count = 0
    discrepancies = []

    for inst in instances:
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
        adhp_edge_path = inst.get("adhp_edge_path", [])

        status, chosen_edges, ilp_cost, ilp_weight, _ = solve_cspp_ilp(
            n_nodes, edges, source, target, budget
        )

        if status == IlpStatus.OPTIMAL:
            if adhp_status != "Optimal":
                err = f"Instance {inst_id} ({family}): ILP found feasible optimum (cost={ilp_cost:.4f}, weight={ilp_weight:.4f}), but ADHP reported {adhp_status}"
                discrepancies.append(err)
            else:
                cost_diff = abs(ilp_cost - adhp_cost)
                rel_diff = cost_diff / max(1.0, abs(ilp_cost))
                if cost_diff > 1e-4 and rel_diff > 1e-5:
                    err = f"Instance {inst_id} ({family}): Cost mismatch! ILP cost={ilp_cost:.6f}, ADHP cost={adhp_cost:.6f}, diff={cost_diff:.6e}"
                    discrepancies.append(err)
                elif adhp_weight > budget + 1e-6:
                    err = f"Instance {inst_id} ({family}): ADHP weight {adhp_weight:.6f} exceeds budget {budget:.6f}"
                    discrepancies.append(err)
                else:
                    # Validate path integrity
                    valid_path, recalc_cost, recalc_weight, path_err = validate_edge_path(
                        edges, source, target, budget, adhp_edge_path
                    )
                    if not valid_path:
                        err = f"Instance {inst_id} ({family}): Invalid path returned by ADHP: {path_err}"
                        discrepancies.append(err)
                    elif abs(recalc_cost - adhp_cost) > 1e-4 or abs(recalc_weight - adhp_weight) > 1e-4:
                        err = f"Instance {inst_id} ({family}): Recalculated path metrics (c={recalc_cost}, w={recalc_weight}) disagree with reported (c={adhp_cost}, w={adhp_weight})"
                        discrepancies.append(err)
                    else:
                        verified_optimal += 1

        elif status == IlpStatus.INFEASIBLE:
            if adhp_status != "Infeasible":
                err = f"Instance {inst_id} ({family}): ILP proved Infeasible, but ADHP returned {adhp_status} (cost={adhp_cost})"
                discrepancies.append(err)
            else:
                verified_infeasible += 1

        elif status in (IlpStatus.TIMEOUT, IlpStatus.NUMERICAL_ERROR, IlpStatus.UNKNOWN):
            inconclusive_count += 1
            print(f"  [INCONCLUSIVE] Instance {inst_id} ({family}): ILP status={status.value}. Excluded from verified count.")

        elif status == IlpStatus.UNBOUNDED:
            err = f"Instance {inst_id} ({family}): ILP reported Unbounded, which is invalid for non-negative CSPP."
            discrepancies.append(err)

    return {
        "total_evaluated": len(instances),
        "verified_optimal": verified_optimal,
        "verified_infeasible": verified_infeasible,
        "inconclusive": inconclusive_count,
        "discrepancies": discrepancies,
    }


def verify_integer_instances_against_ilp(instances):
    """
    Directly validates integer CSPP instances solved by IntAdhpSolver against SciPy HiGHS ILP.
    Performs zero-tolerance integer cost checks and structural path validation.
    """
    verified_optimal = 0
    verified_infeasible = 0
    inconclusive_count = 0
    discrepancies = []

    for inst in instances:
        inst_id = inst["instance_id"]
        family = inst["family"]
        n_nodes = inst["num_nodes"]
        edges = inst["edges"]
        source = inst["source"]
        target = inst["target"]
        budget = int(inst["budget"])

        int_adhp_status = inst.get("int_adhp_status")
        int_adhp_cost = inst.get("int_adhp_cost")
        int_adhp_weight = inst.get("int_adhp_weight")
        int_adhp_edge_path = inst.get("int_adhp_edge_path", [])

        status, chosen_edges, ilp_cost, ilp_weight, _ = solve_cspp_ilp(
            n_nodes, edges, source, target, budget
        )

        if status == IlpStatus.OPTIMAL:
            ilp_opt_cost_int = int(round(ilp_cost))
            if int_adhp_status != "Optimal":
                err = f"Integer Instance {inst_id} ({family}): ILP found feasible optimum (cost={ilp_opt_cost_int}), but IntAdhpSolver reported {int_adhp_status}"
                discrepancies.append(err)
            elif int_adhp_cost is None or int_adhp_cost != ilp_opt_cost_int:
                err = f"Integer Instance {inst_id} ({family}): Exact cost mismatch! ILP cost={ilp_opt_cost_int}, IntAdhpSolver cost={int_adhp_cost}"
                discrepancies.append(err)
            elif int_adhp_weight is None or int_adhp_weight > budget:
                err = f"Integer Instance {inst_id} ({family}): IntAdhpSolver weight {int_adhp_weight} exceeds budget {budget}"
                discrepancies.append(err)
            else:
                # Structural path validation
                valid_path, recalc_cost, recalc_weight, path_err = validate_edge_path(
                    edges, source, target, budget, int_adhp_edge_path
                )
                if not valid_path:
                    err = f"Integer Instance {inst_id} ({family}): Invalid path returned by IntAdhpSolver: {path_err}"
                    discrepancies.append(err)
                elif int(round(recalc_cost)) != int_adhp_cost or int(round(recalc_weight)) != int_adhp_weight:
                    err = f"Integer Instance {inst_id} ({family}): Recalculated path metrics (c={recalc_cost}, w={recalc_weight}) disagree with reported (c={int_adhp_cost}, w={int_adhp_weight})"
                    discrepancies.append(err)
                else:
                    verified_optimal += 1

        elif status == IlpStatus.INFEASIBLE:
            if int_adhp_status != "Infeasible":
                err = f"Integer Instance {inst_id} ({family}): ILP proved Infeasible, but IntAdhpSolver returned {int_adhp_status}"
                discrepancies.append(err)
            else:
                verified_infeasible += 1

        elif status in (IlpStatus.TIMEOUT, IlpStatus.NUMERICAL_ERROR, IlpStatus.UNKNOWN):
            inconclusive_count += 1
            print(f"  [INCONCLUSIVE] Integer Instance {inst_id} ({family}): ILP status={status.value}. Excluded from verified count.")

        elif status == IlpStatus.UNBOUNDED:
            err = f"Integer Instance {inst_id} ({family}): ILP reported Unbounded, which is invalid for non-negative CSPP."
            discrepancies.append(err)

    return {
        "total_evaluated": len(instances),
        "verified_optimal": verified_optimal,
        "verified_infeasible": verified_infeasible,
        "inconclusive": inconclusive_count,
        "discrepancies": discrepancies,
    }


def main():
    print("=== ADHP-CSPP: Ground-Truth Verification against Independent HiGHS ILP Oracle ===")

    float_instance_path = "results/raw/verification_instances.json"
    int_instance_path = "results/raw/integer_verification_instances.json"

    if not os.path.exists(float_instance_path) or not os.path.exists(int_instance_path):
        print("Verification artifacts missing. Executing `cargo run --bin verify_oracle --release`...")
        import subprocess
        subprocess.run(["cargo", "run", "--bin", "verify_oracle", "--release"], check=True)

    with open(float_instance_path, "r") as f:
        float_instances = json.load(f)
    with open(int_instance_path, "r") as f:
        int_instances = json.load(f)

    print(f"Loaded {len(float_instances)} floating-point instances and {len(int_instances)} exact integer instances.")

    print("\n--- Verifying Floating-Point Instances (AdhpSolver vs HiGHS ILP) ---")
    results_float = verify_instances_against_ilp(float_instances)

    print("\n--- Verifying Exact Integer Instances (IntAdhpSolver vs HiGHS ILP) ---")
    results_int = verify_integer_instances_against_ilp(int_instances)

    total_evaluated = results_float["total_evaluated"] + results_int["total_evaluated"]
    total_optimal = results_float["verified_optimal"] + results_int["verified_optimal"]
    total_infeasible = results_float["verified_infeasible"] + results_int["verified_infeasible"]
    total_verified = total_optimal + total_infeasible
    total_inconclusive = results_float["inconclusive"] + results_int["inconclusive"]
    all_discrepancies = results_float["discrepancies"] + results_int["discrepancies"]

    print("\n================ VERIFICATION SUMMARY ================")
    print(f"Total instances evaluated: {total_evaluated}")
    print(f"  - Floating-point instances: {results_float['total_evaluated']} ({results_float['verified_optimal']} opt, {results_float['verified_infeasible']} inf)")
    print(f"  - Exact integer instances:  {results_int['total_evaluated']} ({results_int['verified_optimal']} opt, {results_int['verified_infeasible']} inf)")
    print(f"Total verified matches:     {total_verified} / {total_evaluated}")
    print(f"Inconclusive checks:        {total_inconclusive}")
    print(f"Total discrepancies:        {len(all_discrepancies)}")
    print("======================================================")

    if all_discrepancies:
        print(f"\nFAILED: {len(all_discrepancies)} discrepancies detected between ADHP and HiGHS ILP:")
        for d in all_discrepancies:
            print(f"  - {d}")
        sys.exit(1)

    if total_inconclusive > 0:
        print(f"\nFAILED: Verification incomplete due to {total_inconclusive} inconclusive ILP status(es).")
        sys.exit(1)

    if total_verified < total_evaluated:
        print(f"\nFAILED: Unresolved evaluations ({total_verified}/{total_evaluated} verified).")
        sys.exit(1)

    print(f"\nSUCCESS: All {total_verified}/{total_evaluated} instances (100 float + 50 integer) verified against HiGHS ILP oracle with 0 discrepancies and 0 inconclusive checks.")
    sys.exit(0)


if __name__ == "__main__":
    main()

