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
    g.add_edge(0, 1, 10.0, 5.0);

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
    g.add_edge(0, 1, 5.0, 5.0);
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
    g.add_edge(0, 1, 10.0, 2.0);
    g.add_edge(1, 3, 10.0, 2.0);

    g.add_edge(0, 2, 5.0, 6.0);
    g.add_edge(2, 3, 5.0, 6.0);

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
    g.add_edge(0, 1, 5.0, 2.0);
    g.add_edge(1, 2, 0.0, 0.0);
    g.add_edge(2, 1, 0.0, 0.0);
    g.add_edge(2, 3, 5.0, 2.0);

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
    g.add_edge(0, 1, 10.0, 2.0);
    g.add_edge(1, 3, 10.0, 2.0);
    g.add_edge(0, 2, 5.0, 6.0);
    g.add_edge(2, 3, 5.0, 6.0);

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
    g.add_edge(0, 1, 5.0, 2.5);
    g.add_edge(1, 2, 5.000000001, 2.5);
    g.add_edge(0, 2, 10.000000002, 4.0);

    let inst = CsppInstance::new(g, 0, 2, 6.0);
    let solver = AdhpSolver::new(2);
    let sol = solver.solve(&inst);

    assert_eq!(sol.status, SolutionStatus::Optimal);
    assert!(sol.cost <= 10.000000001 + 1e-8);
}
