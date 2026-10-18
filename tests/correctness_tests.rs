//! Comprehensive correctness and differential verification tests for ADHP and baselines.

use adhp_cspp::graph::DirectedGraph;
use adhp_cspp::instance_generator::{
    generate_anticorrelated_instance, generate_grid_instance, generate_random_instance,
};
use adhp_cspp::{
    AdhpSolver, CarlyleWoodSolver, CsppInstance, CsppSolver, DumitrescuBolandSolver, MartinsSolver,
    PulseSolver, SolutionStatus,
};

#[test]
fn test_minimal_graph_direct_edge() {
    let mut g = DirectedGraph::new(2);
    assert!(g.add_edge(0, 1, 10.0, 5.0));

    let inst_feasible = CsppInstance::new(g.clone(), 0, 1, 6.0);
    let solver = AdhpSolver::new(3);
    let sol = solver.solve(&inst_feasible);

    assert_eq!(sol.status, SolutionStatus::Optimal);
    assert_eq!(sol.path, vec![0, 1]);
    assert!((sol.cost - 10.0).abs() < 1e-9);
    assert!((sol.weight - 5.0).abs() < 1e-9);

    let inst_infeasible = CsppInstance::new(g, 0, 1, 4.0);
    let sol_inf = solver.solve(&inst_infeasible);
    assert_eq!(sol_inf.status, SolutionStatus::Infeasible);
}

#[test]
fn test_disconnected_target() {
    let mut g = DirectedGraph::new(3);
    assert!(g.add_edge(0, 1, 5.0, 5.0));
    // Node 2 has no incoming edges

    let inst = CsppInstance::new(g, 0, 2, 100.0);
    let solver = AdhpSolver::new(3);
    let sol = solver.solve(&inst);
    assert_eq!(sol.status, SolutionStatus::Infeasible);
}

#[test]
fn test_two_path_tradeoff() {
    // Path 1: 0 -> 1 -> 3: cost = 10 + 10 = 20, weight = 2 + 2 = 4
    // Path 2: 0 -> 2 -> 3: cost = 5 + 5 = 10, weight = 6 + 6 = 12
    let mut g = DirectedGraph::new(4);
    assert!(g.add_edge(0, 1, 10.0, 2.0));
    assert!(g.add_edge(1, 3, 10.0, 2.0));

    assert!(g.add_edge(0, 2, 5.0, 6.0));
    assert!(g.add_edge(2, 3, 5.0, 6.0));

    let solver = AdhpSolver::new(3);

    // If budget = 5: Path 2 exceeds budget (12 > 5). Only Path 1 is feasible (weight 4 <= 5). Cost = 20.
    let inst1 = CsppInstance::new(g.clone(), 0, 3, 5.0);
    let sol1 = solver.solve(&inst1);
    assert_eq!(sol1.status, SolutionStatus::Optimal);
    assert_eq!(sol1.path, vec![0, 1, 3]);
    assert!((sol1.cost - 20.0).abs() < 1e-9);

    // If budget = 15: Both paths feasible. Path 2 has cost 10 < 20. Cost = 10.
    let inst2 = CsppInstance::new(g, 0, 3, 15.0);
    let sol2 = solver.solve(&inst2);
    assert_eq!(sol2.status, SolutionStatus::Optimal);
    assert_eq!(sol2.path, vec![0, 2, 3]);
    assert!((sol2.cost - 10.0).abs() < 1e-9);
}

#[test]
fn test_differential_agreement_across_all_solvers() {
    let adhp = AdhpSolver::new(5);
    let martins = MartinsSolver::new();
    let dumitrescu = DumitrescuBolandSolver::new();
    let pulse = PulseSolver::new();
    let carlyle = CarlyleWoodSolver::new();

    let solvers: Vec<&dyn CsppSolver> = vec![&adhp, &martins, &dumitrescu, &pulse, &carlyle];

    // Run differential tests over 15 distinct generated instances (random, anticorrelated, grid)
    for seed in 1..=5 {
        let inst_rand = generate_random_instance(20, 0.25, 0.4, seed * 101);
        let inst_anti = generate_anticorrelated_instance(15, 0.30, 0.35, seed * 202);
        let inst_grid = generate_grid_instance(4, 4, 0.45, seed * 303);

        let test_cases = [inst_rand, inst_anti, inst_grid];

        for (case_idx, inst) in test_cases.iter().enumerate() {
            let mut solutions = Vec::new();

            for solver in &solvers {
                let sol = solver.solve(inst);
                solutions.push((solver.name(), sol));
            }

            let (first_name, first_sol) = &solutions[0];

            for (solver_name, sol) in &solutions[1..] {
                assert_eq!(
                    first_sol.status, sol.status,
                    "Status mismatch between {} and {} on seed {}, case {}",
                    first_name, solver_name, seed, case_idx
                );

                if first_sol.status == SolutionStatus::Optimal {
                    let cost_diff = (first_sol.cost - sol.cost).abs();
                    assert!(
                        cost_diff < 1e-6,
                        "Cost mismatch between {} ({}) and {} ({}) on seed {}, case {}. Diff = {}",
                        first_name,
                        first_sol.cost,
                        solver_name,
                        sol.cost,
                        seed,
                        case_idx,
                        cost_diff
                    );

                    // Verify feasibility of both paths
                    assert!(
                        sol.weight <= inst.budget + 1e-9,
                        "Solver {} returned path violating budget: {} > {}",
                        solver_name,
                        sol.weight,
                        inst.budget
                    );

                    // Verify path actually exists and connects source to target
                    let eval_res = inst.evaluate_path(&sol.path);
                    assert!(
                        eval_res.is_some(),
                        "Solver {} returned invalid path: {:?}",
                        solver_name,
                        sol.path
                    );
                }
            }
        }
    }
}

#[test]
fn test_zero_cost_zero_weight_cycle_termination() {
    // Graph with zero-cost zero-weight cycle between nodes 1 and 2:
    // 0 -> 1 (cost 5, weight 2)
    // 1 -> 2 (cost 0, weight 0)
    // 2 -> 1 (cost 0, weight 0)
    // 2 -> 3 (cost 5, weight 2)
    let mut g = DirectedGraph::new(4);
    assert!(g.add_edge(0, 1, 5.0, 2.0));
    assert!(g.add_edge(1, 2, 0.0, 0.0));
    assert!(g.add_edge(2, 1, 0.0, 0.0));
    assert!(g.add_edge(2, 3, 5.0, 2.0));

    let inst = CsppInstance::new(g, 0, 3, 10.0);
    let solver = AdhpSolver::new(3);
    let sol = solver.solve(&inst);

    assert_eq!(sol.status, SolutionStatus::Optimal);
    assert!((sol.cost - 10.0).abs() < 1e-9);
    assert!((sol.weight - 4.0).abs() < 1e-9);
    assert!(
        sol.path.len() <= 4,
        "Path should not endlessly loop in cycle"
    );
}

#[test]
fn test_k1_pure_cost_bounding() {
    let mut g = DirectedGraph::new(4);
    assert!(g.add_edge(0, 1, 10.0, 2.0));
    assert!(g.add_edge(1, 3, 10.0, 2.0));
    assert!(g.add_edge(0, 2, 5.0, 6.0));
    assert!(g.add_edge(2, 3, 5.0, 6.0));

    let inst = CsppInstance::new(g, 0, 3, 5.0);
    // K = 1: ADHP must work as 1D-bounded solver without panic
    let solver_k1 = AdhpSolver::new(1);
    let sol = solver_k1.solve(&inst);

    assert_eq!(sol.status, SolutionStatus::Optimal);
    assert_eq!(sol.path, vec![0, 1, 3]);
    assert!((sol.cost - 20.0).abs() < 1e-9);
}

#[test]
fn test_floating_point_epsilon_near_tie() {
    let mut g = DirectedGraph::new(3);
    // Path 1: 0 -> 1 -> 2: cost = 10.000000001, weight = 5.0
    // Path 2: 0 -> 2 direct: cost = 10.000000002, weight = 4.0
    assert!(g.add_edge(0, 1, 5.0, 2.5));
    assert!(g.add_edge(1, 2, 5.000000001, 2.5));
    assert!(g.add_edge(0, 2, 10.000000002, 4.0));

    let inst = CsppInstance::new(g, 0, 2, 6.0);
    let solver = AdhpSolver::new(2);
    let sol = solver.solve(&inst);

    assert_eq!(sol.status, SolutionStatus::Optimal);
    assert!(sol.cost <= 10.000000001 + 1e-8);
}

#[test]
fn test_decimal_floating_point_precision_case() {
    // Decimal precision edge case: 0.1 + 0.2 = 0.30000000000000004 in IEEE 754 f64.
    // 0 -> 1: cost 1.0, weight 0.1
    // 1 -> 2: cost 1.0, weight 0.2
    // 0 -> 2: cost 100.0, weight 0.3
    // Budget: 0.3.
    // True optimal cost is 2.0 (via 0 -> 1 -> 2), NOT 100.0!
    let mut g = DirectedGraph::new(3);
    assert!(g.add_edge(0, 1, 1.0, 0.1));
    assert!(g.add_edge(1, 2, 1.0, 0.2));
    assert!(g.add_edge(0, 2, 100.0, 0.3));

    let inst = CsppInstance::new(g, 0, 2, 0.3);

    let adhp = AdhpSolver::new(3);
    let martins = MartinsSolver::new();
    let db = DumitrescuBolandSolver::new();
    let cw = CarlyleWoodSolver::new();
    let pulse = PulseSolver::new();

    let sol_adhp = adhp.solve(&inst);
    let sol_martins = martins.solve(&inst);
    let sol_db = db.solve(&inst);
    let sol_cw = cw.solve(&inst);
    let sol_pulse = pulse.solve(&inst);

    assert_eq!(sol_adhp.status, SolutionStatus::Optimal);
    assert_eq!(sol_martins.status, SolutionStatus::Optimal);
    assert_eq!(sol_db.status, SolutionStatus::Optimal);
    assert_eq!(sol_cw.status, SolutionStatus::Optimal);
    assert_eq!(sol_pulse.status, SolutionStatus::Optimal);

    assert!(
        (sol_adhp.cost - 2.0).abs() < 1e-6,
        "ADHP failed decimal test: got {}",
        sol_adhp.cost
    );
    assert!(
        (sol_martins.cost - 2.0).abs() < 1e-6,
        "Martins failed decimal test: got {}",
        sol_martins.cost
    );
    assert!(
        (sol_db.cost - 2.0).abs() < 1e-6,
        "DB failed decimal test: got {}",
        sol_db.cost
    );
    assert!(
        (sol_cw.cost - 2.0).abs() < 1e-6,
        "CW failed decimal test: got {}",
        sol_cw.cost
    );
    assert!(
        (sol_pulse.cost - 2.0).abs() < 1e-6,
        "Pulse failed decimal test: got {}",
        sol_pulse.cost
    );
}

#[test]
fn test_invalid_inputs_and_edge_cases() {
    let mut g = DirectedGraph::new(3);
    assert!(g.add_edge(0, 1, 5.0, 2.0));
    assert!(g.add_edge(1, 2, 5.0, 2.0));

    let solver = AdhpSolver::new(3);

    // Negative budget
    let inst_neg = CsppInstance::new(g.clone(), 0, 2, -1.0);
    assert_eq!(solver.solve(&inst_neg).status, SolutionStatus::Infeasible);

    // NaN budget
    let inst_nan = CsppInstance::new(g.clone(), 0, 2, f64::NAN);
    assert_eq!(solver.solve(&inst_nan).status, SolutionStatus::Infeasible);

    // Out of bounds source / target
    let inst_oob = CsppInstance::new(g.clone(), 99, 2, 10.0);
    assert_eq!(solver.solve(&inst_oob).status, SolutionStatus::Infeasible);

    // add_edge rejection of negative/infinite values
    let mut bad_g = DirectedGraph::new(2);
    assert!(!bad_g.add_edge(0, 1, -1.0, 5.0));
    assert!(!bad_g.add_edge(0, 1, 5.0, -1.0));
    assert!(!bad_g.add_edge(0, 1, f64::NAN, 5.0));
    assert!(!bad_g.add_edge(0, 1, 5.0, f64::INFINITY));
}

#[test]
fn test_parallel_edge_disambiguation() {
    // Parallel edges between node 0 and node 1:
    // Edge 0: cost 10.0, weight 10.0 (infeasible under budget 5.0)
    // Edge 1: cost 20.0, weight 1.0 (feasible under budget 5.0)
    let mut g = DirectedGraph::new(2);
    assert!(g.add_edge(0, 1, 10.0, 10.0));
    assert!(g.add_edge(0, 1, 20.0, 1.0));

    let inst = CsppInstance::new(g, 0, 1, 5.0);
    let solver = AdhpSolver::new(3);
    let sol = solver.solve(&inst);

    assert_eq!(sol.status, SolutionStatus::Optimal);
    assert!((sol.cost - 20.0).abs() < 1e-9);
    assert!((sol.weight - 1.0).abs() < 1e-9);
    assert_eq!(sol.edge_path, vec![1]);

    // Unambiguous evaluation via edge indices
    let eval_edge = inst.evaluate_edge_path(&sol.edge_path);
    assert_eq!(eval_edge, Some((20.0, 1.0)));

    // Ambiguity-resolving evaluation via vertex sequence
    let eval_vert = inst.evaluate_path(&sol.path);
    assert_eq!(eval_vert, Some((20.0, 1.0)));
}

/// Independent 2D Dynamic Programming algorithm for exact integer-weighted CSPP.
/// Shares ZERO code with label setting, heuristics, or Lagrangian bounds.
fn solve_cspp_integer_dp(inst: &CsppInstance) -> Option<f64> {
    let n = inst.graph.num_nodes();
    let max_w = inst.budget.floor() as usize;
    let mut dp = vec![vec![f64::INFINITY; max_w + 1]; n];
    dp[inst.source][0] = 0.0;

    for _ in 0..n {
        let mut changed = false;
        for u in 0..n {
            for edge in inst.graph.outgoing_edges(u) {
                let v = edge.target;
                let c = edge.cost;
                let ew = edge.weight.round() as usize;
                for w in 0..=(max_w.saturating_sub(ew)) {
                    if dp[u][w].is_finite() && dp[u][w] + c < dp[v][w + ew] {
                        dp[v][w + ew] = dp[u][w] + c;
                        changed = true;
                    }
                }
            }
        }
        if !changed {
            break;
        }
    }

    let min_target = dp[inst.target][..=max_w]
        .iter()
        .copied()
        .fold(f64::INFINITY, f64::min);

    if min_target.is_finite() {
        Some(min_target)
    } else {
        None
    }
}

#[test]
fn test_integer_dp_oracle_fuzz() {
    let adhp = AdhpSolver::new(4);
    let martins = MartinsSolver::new();

    // Test across 15 randomized graphs with exact integer weights
    for seed in 1..=15 {
        let n = 15;
        let mut g = DirectedGraph::new(n);
        let mut rng_state = seed as u64 * 777 + 13;

        let mut next_rand = || {
            rng_state = rng_state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            rng_state
        };

        // Hamiltonian path
        for i in 0..n - 1 {
            let c = (next_rand() % 40 + 1) as f64;
            let w = (next_rand() % 10 + 1) as f64;
            assert!(g.add_edge(i, i + 1, c, w));
        }

        // Random forward edges
        for u in 0..n {
            for v in (u + 1)..n {
                if next_rand() % 100 < 30 {
                    let c = (next_rand() % 50 + 1) as f64;
                    let w = (next_rand() % 15 + 1) as f64;
                    assert!(g.add_edge(u, v, c, w));
                }
            }
        }

        let budget = (next_rand() % 35 + 15) as f64;
        let inst = CsppInstance::new(g, 0, n - 1, budget);

        let dp_cost = solve_cspp_integer_dp(&inst);
        let sol_adhp = adhp.solve(&inst);
        let sol_martins = martins.solve(&inst);

        match dp_cost {
            Some(expected_cost) => {
                assert_eq!(
                    sol_adhp.status,
                    SolutionStatus::Optimal,
                    "Seed {}: ADHP reported Infeasible but DP found cost {}",
                    seed,
                    expected_cost
                );
                assert_eq!(sol_martins.status, SolutionStatus::Optimal);
                assert!(
                    (sol_adhp.cost - expected_cost).abs() < 1e-9,
                    "Seed {}: ADHP cost {} != DP cost {}",
                    seed,
                    sol_adhp.cost,
                    expected_cost
                );
                assert!(
                    (sol_martins.cost - expected_cost).abs() < 1e-9,
                    "Seed {}: Martins cost {} != DP cost {}",
                    seed,
                    sol_martins.cost,
                    expected_cost
                );
            }
            None => {
                assert_eq!(
                    sol_adhp.status,
                    SolutionStatus::Infeasible,
                    "Seed {}: DP found Infeasible but ADHP found cost {}",
                    seed,
                    sol_adhp.cost
                );
                assert_eq!(sol_martins.status, SolutionStatus::Infeasible);
            }
        }
    }
}
