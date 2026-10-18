//! Independent Oracle and Differential Verification Binary.
//!
//! Generates diverse problem instances, executes all five solvers,
//! validates mathematical invariants, and outputs full JSON verification records.

use adhp_cspp::instance_generator::{
    generate_anticorrelated_instance, generate_grid_instance, generate_random_instance,
};
use adhp_cspp::{
    AdhpSolver, CarlyleWoodSolver, CsppSolver, DumitrescuBolandSolver, MartinsSolver, PulseSolver,
    SolutionStatus,
};
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Write;

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

fn main() {
    println!("=== ADHP-CSPP: Running Differential Testing Against 4 Baselines (100 Instances) ===");

    let adhp = AdhpSolver::new(5);
    let martins = MartinsSolver::new();
    let dumitrescu = DumitrescuBolandSolver::new();
    let pulse = PulseSolver::new();
    let carlyle = CarlyleWoodSolver::new();

    let mut records = Vec::new();
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
                generate_anticorrelated_instance(
                    20 + (seed % 4) * 8,
                    0.40,
                    0.50,
                    (seed as u64) * 500 + 77,
                ),
            ),
        ];

        for (id, family, inst) in instances {
            total_verified += 1;
            let sol_adhp = adhp.solve(&inst);
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
            {
                agreed = false;
                println!(
                    "[DISCREPANCY STATUS] Instance: {} | ADHP: {:?}, Martins: {:?}, DB: {:?}, Pulse: {:?}, CW: {:?}",
                    id, sol_adhp.status, sol_martins.status, sol_db.status, sol_pulse.status, sol_cw.status
                );
            }

            if sol_adhp.status == SolutionStatus::Optimal {
                let c_ref = sol_adhp.cost;
                for (name, sol) in [
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
                instance_id: id,
                family,
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
    println!("Saved results to results/raw/verification_results.json");
}
