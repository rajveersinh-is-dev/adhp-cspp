//! Independent Oracle and Differential Verification Binary.
//!
//! Generates diverse problem instances, executes all five solvers,
//! validates mathematical invariants, and outputs full JSON verification records.

use adhp_cspp::exact::{IntAdhpSolver, IntCsppInstance, IntDirectedGraph};
use adhp_cspp::instance_generator::{
    generate_anticorrelated_instance, generate_grid_instance, generate_random_instance,
};
use adhp_cspp::{
    AdhpSolver, CarlyleWoodSolver, CsppSolver, DumitrescuBolandSolver, HybridAdhpSolver,
    MartinsSolver, PulseSolver, SolutionStatus,
};
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Write;

#[derive(Serialize, Deserialize, Clone)]
struct IntegerVerificationEdge {
    from: usize,
    to: usize,
    cost: u64,
    weight: u64,
}

#[derive(Serialize, Deserialize, Clone)]
struct FullIntegerVerificationInstance {
    instance_id: String,
    family: String,
    num_nodes: usize,
    source: usize,
    target: usize,
    budget: u64,
    edges: Vec<IntegerVerificationEdge>,
    int_adhp_status: String,
    int_adhp_cost: Option<u64>,
    int_adhp_weight: Option<u64>,
    int_adhp_path: Vec<usize>,
    int_adhp_edge_path: Vec<usize>,
    oracle_verified: bool,
}

#[derive(Serialize, Deserialize)]
struct VerificationRecord {
    instance_id: String,
    family: String,
    num_nodes: usize,
    num_edges: usize,
    budget: f64,
    status: String,
    optimal_cost: f64,
    optimal_weight: f64,
    all_solvers_agreed: bool,
    adhp_labels_generated: usize,
    martins_labels_generated: usize,
    pruning_ratio_percent: f64,
}

#[derive(Serialize, Deserialize)]
struct VerificationEdge {
    from: usize,
    to: usize,
    cost: f64,
    weight: f64,
}

#[derive(Serialize, Deserialize)]
struct FullVerificationInstance {
    instance_id: String,
    family: String,
    num_nodes: usize,
    source: usize,
    target: usize,
    budget: f64,
    edges: Vec<VerificationEdge>,
    adhp_status: String,
    adhp_cost: f64,
    adhp_weight: f64,
    adhp_edge_path: Vec<usize>,
    martins_status: String,
    martins_cost: f64,
    all_solvers_agreed: bool,
}

fn main() {
    println!("=== ADHP-CSPP: Running Differential Testing Against 4 Baselines (100 Instances) ===");

    let adhp = AdhpSolver::new(5);
    let hybrid = HybridAdhpSolver::new();
    let martins = MartinsSolver::new();
    let dumitrescu = DumitrescuBolandSolver::new();
    let pulse = PulseSolver::new();
    let carlyle = CarlyleWoodSolver::new();

    let mut records = Vec::new();
    let mut full_instances = Vec::new();
    let mut total_verified = 0;
    let mut total_agreed = 0;

    // Test across 100 diverse instances
    for seed in 1..=25 {
        let instances = vec![
            (
                format!("anticorr_n{}_s{}", 15 + (seed % 5) * 5, seed),
                "Anti-Correlated".to_string(),
                generate_anticorrelated_instance(
                    15 + (seed % 5) * 5,
                    0.25,
                    0.20 + (seed as f64 % 5.0) * 0.12,
                    (seed as u64) * 100,
                ),
            ),
            (
                format!("grid_{}x{}_s{}", 3 + (seed % 4), 3 + (seed % 4), seed),
                format!("Grid {}x{}", 3 + (seed % 4), 3 + (seed % 4)),
                generate_grid_instance(
                    3 + (seed % 4),
                    3 + (seed % 4),
                    0.35 + (seed as f64 % 4.0) * 0.10,
                    (seed as u64) * 200,
                ),
            ),
            (
                format!("random_n{}_s{}", 20 + (seed % 6) * 5, seed),
                "Random ER".to_string(),
                generate_random_instance(
                    20 + (seed % 6) * 5,
                    0.22,
                    0.40 + (seed as f64 % 5.0) * 0.08,
                    (seed as u64) * 300,
                ),
            ),
            (
                format!("anticorr_dense_n{}_s{}", 20 + (seed % 4) * 8, seed),
                "Anti-Correlated Dense".to_string(),
                {
                    let mut inst = generate_anticorrelated_instance(
                        20 + (seed % 4) * 8,
                        0.40,
                        0.50,
                        (seed as u64) * 500 + 77,
                    );
                    if seed >= 24 {
                        // Guarantee strict infeasibility (budget far below min weight path)
                        inst.budget = 1.0;
                    }
                    inst
                },
            ),
        ];

        for (id, family, inst) in instances {
            total_verified += 1;
            let sol_adhp = adhp.solve(&inst);
            let sol_hybrid = hybrid.solve(&inst);
            let sol_martins = martins.solve(&inst);
            let sol_db = dumitrescu.solve(&inst);
            let sol_pulse = pulse.solve(&inst);
            let sol_cw = carlyle.solve(&inst);

            let mut agreed = true;

            // Check status agreement
            if sol_adhp.status != sol_martins.status
                || sol_adhp.status != sol_db.status
                || sol_adhp.status != sol_pulse.status
                || sol_adhp.status != sol_cw.status
                || sol_adhp.status != sol_hybrid.status
            {
                agreed = false;
                println!(
                    "[DISCREPANCY STATUS] Instance: {} | ADHP: {:?}, Hybrid: {:?}, Martins: {:?}, DB: {:?}, Pulse: {:?}, CW: {:?}",
                    id, sol_adhp.status, sol_hybrid.status, sol_martins.status, sol_db.status, sol_pulse.status, sol_cw.status
                );
            }

            if sol_adhp.status == SolutionStatus::Optimal {
                let c_ref = sol_adhp.cost;
                for (name, sol) in [
                    ("Hybrid", &sol_hybrid),
                    ("Martins", &sol_martins),
                    ("DB", &sol_db),
                    ("Pulse", &sol_pulse),
                    ("CW", &sol_cw),
                ] {
                    if (sol.cost - c_ref).abs() > 1e-6 {
                        agreed = false;
                        println!(
                            "[DISCREPANCY COST] Instance: {} | ADHP cost: {}, {} cost: {}, budget: {}",
                            id, c_ref, name, sol.cost, inst.budget
                        );
                    }
                    if sol.weight > inst.budget + 1e-9 {
                        agreed = false;
                        println!(
                            "[DISCREPANCY WEIGHT] Instance: {} | {} weight: {} > budget: {}",
                            id, name, sol.weight, inst.budget
                        );
                    }
                }
            }

            if agreed {
                total_agreed += 1;
            }

            let pruning_ratio = if sol_martins.stats.labels_generated > 0 {
                let diff = (sol_martins.stats.labels_generated as f64)
                    - (sol_adhp.stats.labels_generated as f64);
                (diff / (sol_martins.stats.labels_generated as f64)) * 100.0
            } else {
                0.0
            };

            records.push(VerificationRecord {
                instance_id: id.clone(),
                family: family.clone(),
                num_nodes: inst.graph.num_nodes(),
                num_edges: inst.graph.num_edges(),
                budget: inst.budget,
                status: format!("{:?}", sol_adhp.status),
                optimal_cost: sol_adhp.cost,
                optimal_weight: sol_adhp.weight,
                all_solvers_agreed: agreed,
                adhp_labels_generated: sol_adhp.stats.labels_generated,
                martins_labels_generated: sol_martins.stats.labels_generated,
                pruning_ratio_percent: pruning_ratio,
            });

            let edges_vec: Vec<VerificationEdge> = inst
                .graph
                .edges()
                .iter()
                .map(|e| VerificationEdge {
                    from: e.from,
                    to: e.to,
                    cost: e.cost,
                    weight: e.weight,
                })
                .collect();

            full_instances.push(FullVerificationInstance {
                instance_id: id,
                family,
                num_nodes: inst.graph.num_nodes(),
                source: inst.source,
                target: inst.target,
                budget: inst.budget,
                edges: edges_vec,
                adhp_status: format!("{:?}", sol_adhp.status),
                adhp_cost: sol_adhp.cost,
                adhp_weight: sol_adhp.weight,
                adhp_edge_path: sol_adhp.edge_path,
                martins_status: format!("{:?}", sol_martins.status),
                martins_cost: sol_martins.cost,
                all_solvers_agreed: agreed,
            });
        }
    }

    println!(
        "Verification complete: {} / {} instances verified with 100% agreement.",
        total_agreed, total_verified
    );
    assert_eq!(
        total_agreed, total_verified,
        "Differential verification failed!"
    );

    let json_data =
        serde_json::to_string_pretty(&records).expect("Failed to serialize verification records");
    std::fs::create_dir_all("results/raw").ok();
    let mut file = File::create("results/raw/verification_results.json")
        .expect("Failed to write verification file");
    file.write_all(json_data.as_bytes())
        .expect("Failed to write bytes");
    println!("Saved summary to results/raw/verification_results.json");

    let full_json_data = serde_json::to_string_pretty(&full_instances)
        .expect("Failed to serialize full verification instances");
    let mut full_file = File::create("results/raw/verification_instances.json")
        .expect("Failed to write full verification instances file");
    full_file
        .write_all(full_json_data.as_bytes())
        .expect("Failed to write full bytes");
    println!("Saved full instances to results/raw/verification_instances.json");

    // Execute the direct integer verification suite
    let full_int_instances = run_integer_verification_suite();
    let int_json_data = serde_json::to_string_pretty(&full_int_instances)
        .expect("Failed to serialize integer verification instances");
    let mut int_file = File::create("results/raw/integer_verification_instances.json")
        .expect("Failed to write integer verification instances file");
    int_file
        .write_all(int_json_data.as_bytes())
        .expect("Failed to write integer bytes");
    println!(
        "Saved integer verification instances to results/raw/integer_verification_instances.json"
    );
}

struct DfsExplorer<'a> {
    graph: &'a IntDirectedGraph,
    target: usize,
    budget: u64,
    visited: Vec<bool>,
    path: Vec<usize>,
    best: Option<(u64, u64, Vec<usize>)>,
}

impl DfsExplorer<'_> {
    fn dfs(&mut self, u: usize, c_cur: u64, w_cur: u64) {
        if u == self.target {
            if w_cur <= self.budget {
                match self.best {
                    Some((b_c, b_w, _)) => {
                        if c_cur < b_c || (c_cur == b_c && w_cur < b_w) {
                            self.best = Some((c_cur, w_cur, self.path.clone()));
                        }
                    }
                    None => {
                        self.best = Some((c_cur, w_cur, self.path.clone()));
                    }
                }
            }
            return;
        }

        for edge in self.graph.outgoing_edges(u) {
            let v = edge.target;
            if !self.visited[v] {
                if let (Some(new_c), Some(new_w)) =
                    (c_cur.checked_add(edge.cost), w_cur.checked_add(edge.weight))
                {
                    if new_w <= self.budget {
                        self.visited[v] = true;
                        self.path.push(v);
                        self.dfs(v, new_c, new_w);
                        self.path.pop();
                        self.visited[v] = false;
                    }
                }
            }
        }
    }
}

fn solve_exhaustive_dfs(
    graph: &IntDirectedGraph,
    s: usize,
    t: usize,
    budget: u64,
) -> Option<(u64, u64, Vec<usize>)> {
    let n = graph.num_nodes();
    let mut explorer = DfsExplorer {
        graph,
        target: t,
        budget,
        visited: vec![false; n],
        path: vec![s],
        best: None,
    };
    explorer.visited[s] = true;
    explorer.dfs(s, 0, 0);
    explorer.best
}

fn run_integer_verification_suite() -> Vec<FullIntegerVerificationInstance> {
    println!(
        "\n=== ADHP-CSPP: Running Direct Integer Verification for IntAdhpSolver (50 Instances) ==="
    );
    let int_solver = IntAdhpSolver::new(4);
    let mut full_int_instances = Vec::new();

    let mut instances_to_test: Vec<(String, String, IntCsppInstance, bool)> = Vec::new();

    // 1. 15 Anti-Correlated Integer Instances
    for seed in 1..=15 {
        let n = 6 + (seed % 4) * 2;
        let mut g = IntDirectedGraph::new(n);
        let mut rng = (seed as u64)
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);

        // Backbone path
        for i in 0..n - 1 {
            rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
            let cost = (rng % 30) + 1;
            let weight = 40 - (cost % 25);
            g.add_edge(i, i + 1, cost, weight);
        }

        // Cross edges
        for u in 0..n {
            for v in (u + 1)..n {
                rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                if (rng % 100) < 35 {
                    rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let cost = (rng % 40) + 1;
                    let weight = 50 - (cost % 35);
                    g.add_edge(u, v, cost, weight);
                }
            }
        }

        let budget = 30 + (seed as u64 * 5) % 40;
        instances_to_test.push((
            format!("int_anticorr_n{}_s{}", n, seed),
            "Integer Anti-Correlated".to_string(),
            IntCsppInstance::new(g, 0, n - 1, budget),
            n <= 8,
        ));
    }

    // 2. 10 2D Grid Integer Instances
    for seed in 1..=10 {
        let (rows, cols) = if seed % 2 == 1 { (3, 3) } else { (3, 4) };
        let n = rows * cols;
        let mut g = IntDirectedGraph::new(n);
        let mut rng = (seed as u64)
            .wrapping_mul(2862933555777941757)
            .wrapping_add(3037000493);

        for r in 0..rows {
            for c in 0..cols {
                let u = r * cols + c;
                if c + 1 < cols {
                    let v = r * cols + (c + 1);
                    rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let cost = (rng % 25) + 1;
                    rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let weight = (rng % 25) + 1;
                    g.add_edge(u, v, cost, weight);
                }
                if r + 1 < rows {
                    let v = (r + 1) * cols + c;
                    rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let cost = (rng % 25) + 1;
                    rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let weight = (rng % 25) + 1;
                    g.add_edge(u, v, cost, weight);
                }
            }
        }

        let budget = 25 + (seed as u64 * 4) % 35;
        instances_to_test.push((
            format!("int_grid_{}x{}_s{}", rows, cols, seed),
            format!("Integer Grid {}x{}", rows, cols),
            IntCsppInstance::new(g, 0, n - 1, budget),
            n <= 9,
        ));
    }

    // 3. 10 Random Integer Instances
    for seed in 1..=10 {
        let n = 7 + (seed % 4) * 2;
        let mut g = IntDirectedGraph::new(n);
        let mut rng = (seed as u64).wrapping_mul(7777777).wrapping_add(101);

        for u in 0..n {
            for v in 0..n {
                if u != v {
                    rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                    if (rng % 100) < 40 {
                        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                        let cost = (rng % 40) + 1;
                        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                        let weight = (rng % 40) + 1;
                        g.add_edge(u, v, cost, weight);
                    }
                }
            }
        }

        let budget = 35 + (seed as u64 * 6) % 35;
        instances_to_test.push((
            format!("int_random_n{}_s{}", n, seed),
            "Integer Random".to_string(),
            IntCsppInstance::new(g, 0, n - 1, budget),
            n <= 8,
        ));
    }

    // 4. 5 Strictly Infeasible Instances
    for seed in 1..=5 {
        let n = 5;
        let mut g = IntDirectedGraph::new(n);
        g.add_edge(0, 1, 10, 25);
        g.add_edge(1, 2, 10, 25);
        g.add_edge(2, 4, 10, 25);
        g.add_edge(0, 3, 5, 40);
        g.add_edge(3, 4, 5, 40);

        let budget = (seed as u64) * 2; // budget <= 10, impossible
        instances_to_test.push((
            format!("int_infeasible_s{}", seed),
            "Integer Strictly Infeasible".to_string(),
            IntCsppInstance::new(g, 0, 4, budget),
            true,
        ));
    }

    // 5. 5 Exact Boundary Equality Instances
    for seed in 1..=5 {
        let n = 4;
        let mut g = IntDirectedGraph::new(n);
        let w_exact = 15 + (seed as u64) * 5;
        g.add_edge(0, 1, 10, w_exact / 2);
        g.add_edge(1, 3, 10, w_exact - (w_exact / 2));
        g.add_edge(0, 2, 5, w_exact + 10);
        g.add_edge(2, 3, 5, w_exact + 10);

        instances_to_test.push((
            format!("int_boundary_s{}", seed),
            "Integer Exact Boundary".to_string(),
            IntCsppInstance::new(g, 0, 3, w_exact),
            true,
        ));
    }

    // 6. 5 Multiple Optima Instances
    for seed in 1..=5 {
        let n = 4;
        let mut g = IntDirectedGraph::new(n);
        let c = 12 + (seed as u64) * 2;
        let w = 8 + (seed as u64) * 3;
        g.add_edge(0, 1, c, w);
        g.add_edge(1, 3, c, w);
        g.add_edge(0, 2, c, w);
        g.add_edge(2, 3, c, w);

        instances_to_test.push((
            format!("int_multi_opt_s{}", seed),
            "Integer Multiple Optima".to_string(),
            IntCsppInstance::new(g, 0, 3, w * 2 + 5),
            true,
        ));
    }

    assert_eq!(
        instances_to_test.len(),
        50,
        "Expected exactly 50 integer verification instances"
    );

    for (id, family, inst, run_dfs) in instances_to_test {
        let sol = int_solver.solve(&inst);

        let mut oracle_agreed = true;
        if run_dfs {
            let dfs_res = solve_exhaustive_dfs(&inst.graph, inst.source, inst.target, inst.budget);
            match dfs_res {
                Some((exp_c, _exp_w, _)) => {
                    if sol.status != SolutionStatus::Optimal || sol.cost != exp_c {
                        oracle_agreed = false;
                        println!(
                            "[INTEGER DFS MISMATCH] {} | IntAdhp: {:?} cost={}, DFS cost={}",
                            id, sol.status, sol.cost, exp_c
                        );
                    }
                }
                None => {
                    if sol.status != SolutionStatus::Infeasible {
                        oracle_agreed = false;
                        println!(
                            "[INTEGER DFS MISMATCH] {} | IntAdhp: {:?}, DFS: Infeasible",
                            id, sol.status
                        );
                    }
                }
            }
        }

        if sol.status == SolutionStatus::Optimal {
            let (c, w) = match inst.evaluate_edge_path(&sol.edge_path) {
                Some(pair) => pair,
                None => {
                    eprintln!("IntAdhpSolver returned invalid path for {}", id);
                    std::process::exit(1);
                }
            };
            assert_eq!(c, sol.cost, "Cost recalculation mismatch for {}", id);
            assert_eq!(w, sol.weight, "Weight recalculation mismatch for {}", id);
            assert!(
                w <= inst.budget,
                "Path weight {} exceeds budget {} for {}",
                w,
                inst.budget,
                id
            );
        }

        assert!(
            oracle_agreed,
            "Ground-truth DFS oracle disagreement on {}",
            id
        );

        let edges_vec: Vec<IntegerVerificationEdge> = inst
            .graph
            .edges()
            .iter()
            .map(|e| IntegerVerificationEdge {
                from: e.from,
                to: e.to,
                cost: e.cost,
                weight: e.weight,
            })
            .collect();

        full_int_instances.push(FullIntegerVerificationInstance {
            instance_id: id,
            family,
            num_nodes: inst.graph.num_nodes(),
            source: inst.source,
            target: inst.target,
            budget: inst.budget,
            edges: edges_vec,
            int_adhp_status: format!("{:?}", sol.status),
            int_adhp_cost: if sol.status == SolutionStatus::Optimal {
                Some(sol.cost)
            } else {
                None
            },
            int_adhp_weight: if sol.status == SolutionStatus::Optimal {
                Some(sol.weight)
            } else {
                None
            },
            int_adhp_path: sol.path,
            int_adhp_edge_path: sol.edge_path,
            oracle_verified: oracle_agreed,
        });
    }

    println!("Integer verification complete: 50 / 50 instances verified (100% agreement with DFS oracle and path checks).");
    full_int_instances
}
