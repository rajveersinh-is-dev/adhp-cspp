//! High-Resolution Empirical Benchmark Suite for CSPP Solvers.
//!
//! Follows strict computational honesty rules:
//! - Real, unadulterated execution to completion
//! - In-process timing via std::time::Instant
//! - Preceded by at least 5 discarded warmup runs per configuration
//! - Multiple repetitions with mean and standard deviation
//! - Outputs machine-readable raw JSON and CSV data.

use adhp_cspp::instance_generator::{
    generate_anticorrelated_instance, generate_grid_instance, generate_random_instance,
};
use adhp_cspp::{
    AdhpSolver, CarlyleWoodSolver, CsppInstance, CsppSolver, DumitrescuBolandSolver, MartinsSolver,
    PulseSolver,
};
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Serialize, Deserialize, Clone)]
struct BenchmarkRecord {
    benchmark_category: String,
    instance_name: String,
    nodes: usize,
    edges: usize,
    budget: f64,
    solver_name: String,
    mean_runtime_micros: f64,
    std_dev_micros: f64,
    mean_preprocessing_micros: f64,
    mean_labels_generated: usize,
    mean_labels_pruned_dual: usize,
    mean_labels_pruned_dominance: usize,
    mean_labels_explored: usize,
    peak_queue_size: usize,
    cost: f64,
    weight: f64,
}

fn measure_solver(
    solver: &dyn CsppSolver,
    instance: &CsppInstance,
    warmup_runs: usize,
    timed_runs: usize,
) -> (f64, f64, f64, adhp_cspp::CsppSolution) {
    // Discarded warmup runs to warm up CPU instruction and data caches
    for _ in 0..warmup_runs {
        let _ = solver.solve(instance);
    }

    let mut runtimes = Vec::with_capacity(timed_runs);
    let mut prep_times = Vec::with_capacity(timed_runs);
    let mut last_solution = None;

    for _ in 0..timed_runs {
        let t0 = Instant::now();
        let sol = solver.solve(instance);
        let elapsed = t0.elapsed().as_nanos() as f64 / 1_000.0; // microseconds
        runtimes.push(elapsed);
        prep_times.push(sol.stats.preprocessing_nanos as f64 / 1_000.0);
        last_solution = Some(sol);
    }

    let n = runtimes.len() as f64;
    let mean_time = runtimes.iter().sum::<f64>() / n;
    let variance = runtimes
        .iter()
        .map(|&t| (t - mean_time).powi(2))
        .sum::<f64>()
        / n;
    let std_dev = variance.sqrt();
    let mean_prep = prep_times.iter().sum::<f64>() / n;

    let sol = match last_solution {
        Some(s) => s,
        None => solver.solve(instance),
    };

    (mean_time, std_dev, mean_prep, sol)
}

fn main() {
    println!("==================================================================");
    println!("     ADHP-CSPP: AUTONOMOUS RIGOROUS BENCHMARK SUITE EXECUTION     ");
    println!("==================================================================");

    let warmup_runs = 5;
    let timed_runs = 10;
    let mut records: Vec<BenchmarkRecord> = Vec::new();

    let adhp5 = AdhpSolver::new(5);
    let martins = MartinsSolver::new();
    let dumitrescu = DumitrescuBolandSolver::new();
    let carlyle = CarlyleWoodSolver::new();
    let pulse = PulseSolver::new();

    let competitive_solvers: Vec<&dyn CsppSolver> =
        vec![&adhp5, &carlyle, &dumitrescu, &pulse, &martins];

    // =========================================================================
    // SUITE 1: Scaling on Anti-Correlated Graphs (The Hardest Classical Domain)
    // =========================================================================
    println!("\n>>> SUITE 1: Scaling on Anti-Correlated Graphs (n = 20 to 100)...");
    for &n in &[20, 40, 60, 80, 100] {
        let inst = generate_anticorrelated_instance(n, 0.25, 0.40, (n as u64) * 777);
        println!(
            "  Evaluating Anti-Correlated Instance: n = {}, m = {}, budget = {:.2}",
            inst.graph.num_nodes(),
            inst.graph.num_edges(),
            inst.budget
        );

        for solver in &competitive_solvers {
            let (mean_t, std_t, mean_prep, sol) =
                measure_solver(*solver, &inst, warmup_runs, timed_runs);

            println!(
                "    {:<30} | Time: {:>9.2} ± {:>6.2} µs | Gen: {:>7} | DualPruned: {:>7}",
                solver.name(),
                mean_t,
                std_t,
                sol.stats.labels_generated,
                sol.stats.labels_pruned_dual_bound
            );

            records.push(BenchmarkRecord {
                benchmark_category: "Anti-Correlated Scaling".to_string(),
                instance_name: format!("anticorr_n{}", n),
                nodes: inst.graph.num_nodes(),
                edges: inst.graph.num_edges(),
                budget: inst.budget,
                solver_name: solver.name().to_string(),
                mean_runtime_micros: mean_t,
                std_dev_micros: std_t,
                mean_preprocessing_micros: mean_prep,
                mean_labels_generated: sol.stats.labels_generated,
                mean_labels_pruned_dual: sol.stats.labels_pruned_dual_bound,
                mean_labels_pruned_dominance: sol.stats.labels_pruned_dominance,
                mean_labels_explored: sol.stats.labels_explored,
                peak_queue_size: sol.stats.peak_queue_size,
                cost: sol.cost,
                weight: sol.weight,
            });
        }
    }

    // =========================================================================
    // SUITE 2: Scaling on 2D Mesh Grid Graphs (Planar Bottleneck Routing)
    // =========================================================================
    println!("\n>>> SUITE 2: Scaling on 2D Mesh Grid Graphs (4x4 to 9x9)...");
    for &(r, c) in &[(4, 4), (6, 6), (8, 8), (9, 9)] {
        let inst = generate_grid_instance(r, c, 0.45, (r * c) as u64 * 888);
        println!(
            "  Evaluating Grid Instance: {}x{} (n = {}, m = {}, budget = {:.2})",
            r,
            c,
            inst.graph.num_nodes(),
            inst.graph.num_edges(),
            inst.budget
        );

        for solver in &competitive_solvers {
            let (mean_t, std_t, mean_prep, sol) =
                measure_solver(*solver, &inst, warmup_runs, timed_runs);

            println!(
                "    {:<30} | Time: {:>9.2} ± {:>6.2} µs | Gen: {:>7} | DualPruned: {:>7}",
                solver.name(),
                mean_t,
                std_t,
                sol.stats.labels_generated,
                sol.stats.labels_pruned_dual_bound
            );

            records.push(BenchmarkRecord {
                benchmark_category: "Grid Scaling".to_string(),
                instance_name: format!("grid_{}x{}", r, c),
                nodes: inst.graph.num_nodes(),
                edges: inst.graph.num_edges(),
                budget: inst.budget,
                solver_name: solver.name().to_string(),
                mean_runtime_micros: mean_t,
                std_dev_micros: std_t,
                mean_preprocessing_micros: mean_prep,
                mean_labels_generated: sol.stats.labels_generated,
                mean_labels_pruned_dual: sol.stats.labels_pruned_dual_bound,
                mean_labels_pruned_dominance: sol.stats.labels_pruned_dominance,
                mean_labels_explored: sol.stats.labels_explored,
                peak_queue_size: sol.stats.peak_queue_size,
                cost: sol.cost,
                weight: sol.weight,
            });
        }
    }

    // =========================================================================
    // SUITE 3: Scaling on Random Erdős-Rényi Graphs (n = 30 to 120)
    // =========================================================================
    println!("\n>>> SUITE 3: Scaling on Random Erdős-Rényi Graphs (n = 30 to 120)...");
    for &n in &[30, 60, 90, 120] {
        let inst = generate_random_instance(n, 0.20, 0.45, (n as u64) * 666);
        println!(
            "  Evaluating Random ER Instance: n = {}, m = {}, budget = {:.2}",
            inst.graph.num_nodes(),
            inst.graph.num_edges(),
            inst.budget
        );

        for solver in &competitive_solvers {
            let (mean_t, std_t, mean_prep, sol) =
                measure_solver(*solver, &inst, warmup_runs, timed_runs);

            println!(
                "    {:<30} | Time: {:>9.2} ± {:>6.2} µs | Gen: {:>7} | DualPruned: {:>7}",
                solver.name(),
                mean_t,
                std_t,
                sol.stats.labels_generated,
                sol.stats.labels_pruned_dual_bound
            );

            records.push(BenchmarkRecord {
                benchmark_category: "Random ER Scaling".to_string(),
                instance_name: format!("random_er_n{}", n),
                nodes: inst.graph.num_nodes(),
                edges: inst.graph.num_edges(),
                budget: inst.budget,
                solver_name: solver.name().to_string(),
                mean_runtime_micros: mean_t,
                std_dev_micros: std_t,
                mean_preprocessing_micros: mean_prep,
                mean_labels_generated: sol.stats.labels_generated,
                mean_labels_pruned_dual: sol.stats.labels_pruned_dual_bound,
                mean_labels_pruned_dominance: sol.stats.labels_pruned_dominance,
                mean_labels_explored: sol.stats.labels_explored,
                peak_queue_size: sol.stats.peak_queue_size,
                cost: sol.cost,
                weight: sol.weight,
            });
        }
    }

    // =========================================================================
    // SUITE 4: Sensitivity to Budget Tightness Factor alpha
    // =========================================================================
    println!("\n>>> SUITE 4: Budget Tightness Sensitivity (alpha = 0.10 to 0.90)...");
    for &alpha in &[0.10, 0.25, 0.50, 0.75, 0.90] {
        let inst = generate_anticorrelated_instance(50, 0.25, alpha, 9999);
        println!(
            "  Evaluating Budget Factor alpha = {:.2} (budget = {:.2})",
            alpha, inst.budget
        );

        for solver in &competitive_solvers {
            let (mean_t, std_t, mean_prep, sol) =
                measure_solver(*solver, &inst, warmup_runs, timed_runs);

            println!(
                "    {:<30} | Time: {:>9.2} ± {:>6.2} µs | Gen: {:>7} | PeakQueue: {:>5}",
                solver.name(),
                mean_t,
                std_t,
                sol.stats.labels_generated,
                sol.stats.peak_queue_size
            );

            records.push(BenchmarkRecord {
                benchmark_category: "Budget Sensitivity".to_string(),
                instance_name: format!("budget_alpha_{:.2}", alpha),
                nodes: inst.graph.num_nodes(),
                edges: inst.graph.num_edges(),
                budget: inst.budget,
                solver_name: solver.name().to_string(),
                mean_runtime_micros: mean_t,
                std_dev_micros: std_t,
                mean_preprocessing_micros: mean_prep,
                mean_labels_generated: sol.stats.labels_generated,
                mean_labels_pruned_dual: sol.stats.labels_pruned_dual_bound,
                mean_labels_pruned_dominance: sol.stats.labels_pruned_dominance,
                mean_labels_explored: sol.stats.labels_explored,
                peak_queue_size: sol.stats.peak_queue_size,
                cost: sol.cost,
                weight: sol.weight,
            });
        }
    }

    // =========================================================================
    // SUITE 5: Ablation Analysis: Varying Facet Count K in ADHP
    // =========================================================================
    println!("\n>>> SUITE 5: Ablation Study: Facet Count K (K = 2, 3, 5, 8, 12)...");
    let ablation_inst = generate_anticorrelated_instance(70, 0.25, 0.40, 12345);
    for &k in &[2, 3, 5, 8, 12] {
        let adhp_k = AdhpSolver::new(k);
        let (mean_t, std_t, mean_prep, sol) =
            measure_solver(&adhp_k, &ablation_inst, warmup_runs, timed_runs);

        println!(
            "    ADHP (K = {:>2}) | Prep: {:>7.2} µs | Total: {:>8.2} µs | LabelsGen: {:>6} | DualPruned: {:>6}",
            k,
            mean_prep,
            mean_t,
            sol.stats.labels_generated,
            sol.stats.labels_pruned_dual_bound
        );

        records.push(BenchmarkRecord {
            benchmark_category: "Ablation K Facets".to_string(),
            instance_name: format!("ablation_k{}", k),
            nodes: ablation_inst.graph.num_nodes(),
            edges: ablation_inst.graph.num_edges(),
            budget: ablation_inst.budget,
            solver_name: format!("ADHP (K={})", k),
            mean_runtime_micros: mean_t,
            std_dev_micros: std_t,
            mean_preprocessing_micros: mean_prep,
            mean_labels_generated: sol.stats.labels_generated,
            mean_labels_pruned_dual: sol.stats.labels_pruned_dual_bound,
            mean_labels_pruned_dominance: sol.stats.labels_pruned_dominance,
            mean_labels_explored: sol.stats.labels_explored,
            peak_queue_size: sol.stats.peak_queue_size,
            cost: sol.cost,
            weight: sol.weight,
        });
    }

    // =========================================================================
    // OUTPUT PERSISTENCE: Save Raw JSON and CSV Artifacts
    // =========================================================================
    std::fs::create_dir_all("results/raw").ok();
    std::fs::create_dir_all("results/processed").ok();

    let json_content =
        serde_json::to_string_pretty(&records).expect("Failed to serialize benchmarks");
    let mut json_file =
        File::create("results/raw/benchmark_raw.json").expect("Failed to create JSON");
    json_file
        .write_all(json_content.as_bytes())
        .expect("Failed to write JSON");

    let mut csv_file = File::create("results/raw/benchmark_raw.csv").expect("Failed to create CSV");
    writeln!(
        csv_file,
        "benchmark_category,instance_name,nodes,edges,budget,solver_name,mean_runtime_micros,std_dev_micros,mean_preprocessing_micros,mean_labels_generated,mean_labels_pruned_dual,mean_labels_pruned_dominance,mean_labels_explored,peak_queue_size,cost,weight"
    )
    .expect("Failed to write CSV header");

    for r in &records {
        writeln!(
            csv_file,
            "{},{},{},{},{:.4},{},{:.2},{:.2},{:.2},{},{},{},{},{},{:.4},{:.4}",
            r.benchmark_category,
            r.instance_name,
            r.nodes,
            r.edges,
            r.budget,
            r.solver_name,
            r.mean_runtime_micros,
            r.std_dev_micros,
            r.mean_preprocessing_micros,
            r.mean_labels_generated,
            r.mean_labels_pruned_dual,
            r.mean_labels_pruned_dominance,
            r.mean_labels_explored,
            r.peak_queue_size,
            r.cost,
            r.weight
        )
        .expect("Failed to write CSV row");
    }

    println!("\n>>> Benchmarks finished successfully!");
    println!(">>> Raw results stored in results/raw/benchmark_raw.json and results/raw/benchmark_raw.csv");
}
