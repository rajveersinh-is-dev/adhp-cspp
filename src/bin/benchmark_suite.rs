//! Rigorous Multi-Instance Empirical Benchmark Suite for CSPP Solvers.
//!
//! Follows strict computational honesty rules:
//! - Multi-instance evaluation: evaluates across multiple distinct random instances per configuration
//!   to report true sample distributions (mean, median, standard deviation across instances)
//! - Discarded warmup runs per instance to ensure cache stability
//! - In-process timing via high-resolution std::time::Instant
//! - Evaluates and compares all five solvers fairly without omissions:
//!   ADHP, Carlyle-Wood (LARAC), Dumitrescu-Boland, Pulse (Lozano & Medaglia), Martins
//! - Measures total runtime, preprocessing overhead, search-only time, labels generated, and peak memory
//! - Outputs machine-readable raw JSON and CSV data.

use adhp_cspp::instance_generator::{
    generate_anticorrelated_instance, generate_grid_instance, generate_random_instance,
};
use adhp_cspp::{
    AdhpSolver, CarlyleWoodSolver, CsppInstance, CsppSolver, DumitrescuBolandSolver,
    HybridAdhpSolver, MartinsSolver, PulseSolver,
};
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct BenchmarkRecord {
    pub benchmark_category: String,
    pub instance_name: String,
    pub nodes: usize,
    pub edges: usize,
    pub budget: f64,
    pub solver_name: String,
    pub num_instances: usize,
    pub mean_runtime_micros: f64,
    pub median_runtime_micros: f64,
    pub std_dev_micros: f64,
    pub mean_preprocessing_micros: f64,
    pub mean_search_micros: f64,
    pub mean_labels_generated: usize,
    pub median_labels_generated: usize,
    pub mean_labels_pruned_dual: usize,
    pub mean_labels_pruned_dominance: usize,
    pub mean_labels_explored: usize,
    pub peak_queue_size: usize,
    pub peak_memory_bytes: usize,
}

#[derive(Default)]
struct SolverAggregate {
    mean_runtime_micros: f64,
    median_runtime_micros: f64,
    std_dev_micros: f64,
    mean_preprocessing_micros: f64,
    mean_search_micros: f64,
    mean_labels_generated: usize,
    median_labels_generated: usize,
    mean_labels_pruned_dual: usize,
    mean_labels_pruned_dominance: usize,
    mean_labels_explored: usize,
    peak_queue_size: usize,
    peak_memory_bytes: usize,
}

fn evaluate_solver_across_instances(
    solver: &dyn CsppSolver,
    instances: &[CsppInstance],
) -> SolverAggregate {
    let mut runtimes = Vec::with_capacity(instances.len());
    let mut prep_times = Vec::with_capacity(instances.len());
    let mut search_times = Vec::with_capacity(instances.len());
    let mut labels_gen = Vec::with_capacity(instances.len());
    let mut labels_pruned_dual = Vec::with_capacity(instances.len());
    let mut labels_pruned_dom = Vec::with_capacity(instances.len());
    let mut labels_explored = Vec::with_capacity(instances.len());
    let mut peak_queues = Vec::with_capacity(instances.len());
    let mut peak_mems = Vec::with_capacity(instances.len());

    for inst in instances {
        // 5 discarded warmup runs per instance per computational integrity rules
        for _ in 0..5 {
            let _ = solver.solve(inst);
        }

        // 3 timed runs per instance to average out transient OS jitter
        let mut t_acc = 0.0;
        let mut prep_acc = 0.0;
        let mut last_sol = None;
        let repeats = 3;

        for _ in 0..repeats {
            let t0 = Instant::now();
            let sol = solver.solve(inst);
            let elapsed = t0.elapsed().as_nanos() as f64 / 1_000.0;
            t_acc += elapsed;
            prep_acc += sol.stats.preprocessing_nanos as f64 / 1_000.0;
            last_sol = Some(sol);
        }

        let sol = match last_sol {
            Some(s) => s,
            None => continue,
        };
        let avg_time = t_acc / (repeats as f64);
        let avg_prep = prep_acc / (repeats as f64);
        let avg_search = (avg_time - avg_prep).max(0.0);

        runtimes.push(avg_time);
        prep_times.push(avg_prep);
        search_times.push(avg_search);
        labels_gen.push(sol.stats.labels_generated);
        labels_pruned_dual.push(sol.stats.labels_pruned_dual_bound);
        labels_pruned_dom.push(sol.stats.labels_pruned_dominance);
        labels_explored.push(sol.stats.labels_explored);
        peak_queues.push(sol.stats.peak_queue_size);
        peak_mems.push(sol.stats.peak_memory_bytes);
    }

    let n = runtimes.len() as f64;
    let mean_time = runtimes.iter().sum::<f64>() / n;
    let variance = runtimes
        .iter()
        .map(|&t| (t - mean_time).powi(2))
        .sum::<f64>()
        / n;
    let std_dev = variance.sqrt();

    let mut sorted_runtimes = runtimes.clone();
    sorted_runtimes.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let median_time = sorted_runtimes[sorted_runtimes.len() / 2];

    let mut sorted_labels = labels_gen.clone();
    sorted_labels.sort();
    let median_labels = sorted_labels[sorted_labels.len() / 2];

    SolverAggregate {
        mean_runtime_micros: mean_time,
        median_runtime_micros: median_time,
        std_dev_micros: std_dev,
        mean_preprocessing_micros: prep_times.iter().sum::<f64>() / n,
        mean_search_micros: search_times.iter().sum::<f64>() / n,
        mean_labels_generated: (labels_gen.iter().sum::<usize>() as f64 / n).round() as usize,
        median_labels_generated: median_labels,
        mean_labels_pruned_dual: (labels_pruned_dual.iter().sum::<usize>() as f64 / n).round()
            as usize,
        mean_labels_pruned_dominance: (labels_pruned_dom.iter().sum::<usize>() as f64 / n).round()
            as usize,
        mean_labels_explored: (labels_explored.iter().sum::<usize>() as f64 / n).round() as usize,
        peak_queue_size: peak_queues.into_iter().max().unwrap_or(0),
        peak_memory_bytes: peak_mems.into_iter().max().unwrap_or(0),
    }
}

fn main() {
    println!("==================================================================");
    println!("  ADHP-CSPP: RIGOROUS MULTI-INSTANCE BENCHMARK SUITE EXECUTION   ");
    println!("==================================================================");

    let num_instances_per_config = 10;
    let mut records: Vec<BenchmarkRecord> = Vec::new();

    let adhp5 = AdhpSolver::new(5);
    let hybrid = HybridAdhpSolver::new();
    let martins = MartinsSolver::new();
    let dumitrescu = DumitrescuBolandSolver::new();
    let carlyle = CarlyleWoodSolver::new();
    let pulse = PulseSolver::new();

    let competitive_solvers: Vec<&dyn CsppSolver> =
        vec![&adhp5, &hybrid, &carlyle, &dumitrescu, &pulse, &martins];

    // =========================================================================
    // SUITE 1: Scaling on Anti-Correlated Graphs (n = 20, 40, 60, 80, 100, 150)
    // =========================================================================
    println!("\n>>> SUITE 1: Anti-Correlated Graph Scaling (n = 20 to 150, 10 instances/size)...");
    for &n in &[20, 40, 60, 80, 100, 150] {
        let instances: Vec<CsppInstance> = (1..=num_instances_per_config)
            .map(|s| {
                generate_anticorrelated_instance(
                    n,
                    0.25,
                    0.40,
                    (n as u64) * 1000 + (s as u64) * 77 + 13,
                )
            })
            .collect();

        let avg_edges =
            instances.iter().map(|i| i.graph.num_edges()).sum::<usize>() / instances.len();
        let avg_budget = instances.iter().map(|i| i.budget).sum::<f64>() / (instances.len() as f64);

        println!(
            "  n = {:>3} (avg m = {}, avg budget = {:.1}) across {} instances:",
            n, avg_edges, avg_budget, num_instances_per_config
        );

        for solver in &competitive_solvers {
            let agg = evaluate_solver_across_instances(*solver, &instances);

            println!(
                "    {:<18} | Time: {:>8.2} ± {:>6.2} µs (med: {:>7.2}) | Prep: {:>7.2} µs | Gen: {:>6} (med: {:>6}) | Mem: {:>6} B",
                solver.name().split_whitespace().next().unwrap_or(solver.name()),
                agg.mean_runtime_micros,
                agg.std_dev_micros,
                agg.median_runtime_micros,
                agg.mean_preprocessing_micros,
                agg.mean_labels_generated,
                agg.median_labels_generated,
                agg.peak_memory_bytes
            );

            records.push(BenchmarkRecord {
                benchmark_category: "Anti-Correlated Scaling".to_string(),
                instance_name: format!("anticorr_n{}", n),
                nodes: n,
                edges: avg_edges,
                budget: avg_budget,
                solver_name: solver.name().to_string(),
                num_instances: num_instances_per_config,
                mean_runtime_micros: agg.mean_runtime_micros,
                median_runtime_micros: agg.median_runtime_micros,
                std_dev_micros: agg.std_dev_micros,
                mean_preprocessing_micros: agg.mean_preprocessing_micros,
                mean_search_micros: agg.mean_search_micros,
                mean_labels_generated: agg.mean_labels_generated,
                median_labels_generated: agg.median_labels_generated,
                mean_labels_pruned_dual: agg.mean_labels_pruned_dual,
                mean_labels_pruned_dominance: agg.mean_labels_pruned_dominance,
                mean_labels_explored: agg.mean_labels_explored,
                peak_queue_size: agg.peak_queue_size,
                peak_memory_bytes: agg.peak_memory_bytes,
            });
        }
    }

    // =========================================================================
    // SUITE 2: Scaling on 2D Mesh Grid Graphs (4x4 to 10x10)
    // =========================================================================
    println!("\n>>> SUITE 2: 2D Mesh Grid Scaling (4x4 to 10x10, 10 instances/size)...");
    for &(r, c) in &[(4, 4), (6, 6), (8, 8), (10, 10)] {
        let n = r * c;
        let instances: Vec<CsppInstance> = (1..=num_instances_per_config)
            .map(|s| generate_grid_instance(r, c, 0.45, (n as u64) * 2000 + (s as u64) * 88 + 17))
            .collect();

        let avg_edges =
            instances.iter().map(|i| i.graph.num_edges()).sum::<usize>() / instances.len();
        let avg_budget = instances.iter().map(|i| i.budget).sum::<f64>() / (instances.len() as f64);

        println!(
            "  Grid {}x{} (n = {:>3}, avg m = {}, avg budget = {:.1}) across {} instances:",
            r, c, n, avg_edges, avg_budget, num_instances_per_config
        );

        for solver in &competitive_solvers {
            let agg = evaluate_solver_across_instances(*solver, &instances);

            println!(
                "    {:<18} | Time: {:>8.2} ± {:>6.2} µs (med: {:>7.2}) | Prep: {:>7.2} µs | Gen: {:>6} (med: {:>6}) | Mem: {:>6} B",
                solver.name().split_whitespace().next().unwrap_or(solver.name()),
                agg.mean_runtime_micros,
                agg.std_dev_micros,
                agg.median_runtime_micros,
                agg.mean_preprocessing_micros,
                agg.mean_labels_generated,
                agg.median_labels_generated,
                agg.peak_memory_bytes
            );

            records.push(BenchmarkRecord {
                benchmark_category: "Grid Scaling".to_string(),
                instance_name: format!("grid_{}x{}", r, c),
                nodes: n,
                edges: avg_edges,
                budget: avg_budget,
                solver_name: solver.name().to_string(),
                num_instances: num_instances_per_config,
                mean_runtime_micros: agg.mean_runtime_micros,
                median_runtime_micros: agg.median_runtime_micros,
                std_dev_micros: agg.std_dev_micros,
                mean_preprocessing_micros: agg.mean_preprocessing_micros,
                mean_search_micros: agg.mean_search_micros,
                mean_labels_generated: agg.mean_labels_generated,
                median_labels_generated: agg.median_labels_generated,
                mean_labels_pruned_dual: agg.mean_labels_pruned_dual,
                mean_labels_pruned_dominance: agg.mean_labels_pruned_dominance,
                mean_labels_explored: agg.mean_labels_explored,
                peak_queue_size: agg.peak_queue_size,
                peak_memory_bytes: agg.peak_memory_bytes,
            });
        }
    }

    // =========================================================================
    // SUITE 3: Random Erdős-Rényi Graphs (n = 30 to 120)
    // =========================================================================
    println!("\n>>> SUITE 3: Random Erdős-Rényi Scaling (n = 30 to 120, 10 instances/size)...");
    for &n in &[30, 60, 90, 120] {
        let instances: Vec<CsppInstance> = (1..=num_instances_per_config)
            .map(|s| {
                generate_random_instance(n, 0.20, 0.45, (n as u64) * 3000 + (s as u64) * 99 + 23)
            })
            .collect();

        let avg_edges =
            instances.iter().map(|i| i.graph.num_edges()).sum::<usize>() / instances.len();
        let avg_budget = instances.iter().map(|i| i.budget).sum::<f64>() / (instances.len() as f64);

        println!(
            "  Random ER n = {:>3} (avg m = {}, avg budget = {:.1}) across {} instances:",
            n, avg_edges, avg_budget, num_instances_per_config
        );

        for solver in &competitive_solvers {
            let agg = evaluate_solver_across_instances(*solver, &instances);

            records.push(BenchmarkRecord {
                benchmark_category: "Random ER Scaling".to_string(),
                instance_name: format!("random_er_n{}", n),
                nodes: n,
                edges: avg_edges,
                budget: avg_budget,
                solver_name: solver.name().to_string(),
                num_instances: num_instances_per_config,
                mean_runtime_micros: agg.mean_runtime_micros,
                median_runtime_micros: agg.median_runtime_micros,
                std_dev_micros: agg.std_dev_micros,
                mean_preprocessing_micros: agg.mean_preprocessing_micros,
                mean_search_micros: agg.mean_search_micros,
                mean_labels_generated: agg.mean_labels_generated,
                median_labels_generated: agg.median_labels_generated,
                mean_labels_pruned_dual: agg.mean_labels_pruned_dual,
                mean_labels_pruned_dominance: agg.mean_labels_pruned_dominance,
                mean_labels_explored: agg.mean_labels_explored,
                peak_queue_size: agg.peak_queue_size,
                peak_memory_bytes: agg.peak_memory_bytes,
            });
        }
    }

    // =========================================================================
    // SUITE 4: Budget Tightness Sensitivity (alpha = 0.10 to 0.90)
    // =========================================================================
    println!(
        "\n>>> SUITE 4: Budget Factor Sensitivity (alpha = 0.10 to 0.90, 10 instances/alpha)..."
    );
    for &alpha in &[0.10, 0.25, 0.50, 0.75, 0.90] {
        let instances: Vec<CsppInstance> = (1..=num_instances_per_config)
            .map(|s| {
                generate_anticorrelated_instance(
                    50,
                    0.25,
                    alpha,
                    5000 + (s as u64) * 44 + (alpha * 100.0) as u64,
                )
            })
            .collect();

        let avg_edges =
            instances.iter().map(|i| i.graph.num_edges()).sum::<usize>() / instances.len();
        let avg_budget = instances.iter().map(|i| i.budget).sum::<f64>() / (instances.len() as f64);

        for solver in &competitive_solvers {
            let agg = evaluate_solver_across_instances(*solver, &instances);

            records.push(BenchmarkRecord {
                benchmark_category: "Budget Sensitivity".to_string(),
                instance_name: format!("budget_alpha_{:.2}", alpha),
                nodes: 50,
                edges: avg_edges,
                budget: avg_budget,
                solver_name: solver.name().to_string(),
                num_instances: num_instances_per_config,
                mean_runtime_micros: agg.mean_runtime_micros,
                median_runtime_micros: agg.median_runtime_micros,
                std_dev_micros: agg.std_dev_micros,
                mean_preprocessing_micros: agg.mean_preprocessing_micros,
                mean_search_micros: agg.mean_search_micros,
                mean_labels_generated: agg.mean_labels_generated,
                median_labels_generated: agg.median_labels_generated,
                mean_labels_pruned_dual: agg.mean_labels_pruned_dual,
                mean_labels_pruned_dominance: agg.mean_labels_pruned_dominance,
                mean_labels_explored: agg.mean_labels_explored,
                peak_queue_size: agg.peak_queue_size,
                peak_memory_bytes: agg.peak_memory_bytes,
            });
        }
    }

    // =========================================================================
    // SUITE 5: Ablation Analysis: Varying Facet Count K in ADHP (K = 1, 2, 3, 5, 8, 12)
    // =========================================================================
    println!("\n>>> SUITE 5: Ablation Study: Facet Count K (K = 1, 2, 3, 5, 8, 12)...");
    let ablation_instances: Vec<CsppInstance> = (1..=num_instances_per_config)
        .map(|s| generate_anticorrelated_instance(70, 0.25, 0.40, 7000 + (s as u64) * 31 + 7))
        .collect();

    for &k in &[1, 2, 3, 5, 8, 12] {
        let adhp_k = AdhpSolver::new(k);
        let agg = evaluate_solver_across_instances(&adhp_k, &ablation_instances);

        println!(
            "    ADHP (K = {:>2}) | Total: {:>7.2} µs | Prep: {:>7.2} µs | Search: {:>7.2} µs | Gen: {:>5} (med: {:>5}) | DualPruned: {:>4}",
            k,
            agg.mean_runtime_micros,
            agg.mean_preprocessing_micros,
            agg.mean_search_micros,
            agg.mean_labels_generated,
            agg.median_labels_generated,
            agg.mean_labels_pruned_dual
        );

        records.push(BenchmarkRecord {
            benchmark_category: "Ablation K Facets".to_string(),
            instance_name: format!("ablation_k{}", k),
            nodes: 70,
            edges: ablation_instances[0].graph.num_edges(),
            budget: ablation_instances[0].budget,
            solver_name: format!("ADHP (K={})", k),
            num_instances: num_instances_per_config,
            mean_runtime_micros: agg.mean_runtime_micros,
            median_runtime_micros: agg.median_runtime_micros,
            std_dev_micros: agg.std_dev_micros,
            mean_preprocessing_micros: agg.mean_preprocessing_micros,
            mean_search_micros: agg.mean_search_micros,
            mean_labels_generated: agg.mean_labels_generated,
            median_labels_generated: agg.median_labels_generated,
            mean_labels_pruned_dual: agg.mean_labels_pruned_dual,
            mean_labels_pruned_dominance: agg.mean_labels_pruned_dominance,
            mean_labels_explored: agg.mean_labels_explored,
            peak_queue_size: agg.peak_queue_size,
            peak_memory_bytes: agg.peak_memory_bytes,
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
        "benchmark_category,instance_name,nodes,edges,budget,solver_name,num_instances,mean_runtime_micros,median_runtime_micros,std_dev_micros,mean_preprocessing_micros,mean_search_micros,mean_labels_generated,median_labels_generated,mean_labels_pruned_dual,mean_labels_pruned_dominance,mean_labels_explored,peak_queue_size,peak_memory_bytes"
    )
    .expect("Failed to write CSV header");

    for r in &records {
        writeln!(
            csv_file,
            "{},{},{},{},{:.4},{},{},{:.2},{:.2},{:.2},{:.2},{:.2},{},{},{},{},{},{},{}",
            r.benchmark_category,
            r.instance_name,
            r.nodes,
            r.edges,
            r.budget,
            r.solver_name,
            r.num_instances,
            r.mean_runtime_micros,
            r.median_runtime_micros,
            r.std_dev_micros,
            r.mean_preprocessing_micros,
            r.mean_search_micros,
            r.mean_labels_generated,
            r.median_labels_generated,
            r.mean_labels_pruned_dual,
            r.mean_labels_pruned_dominance,
            r.mean_labels_explored,
            r.peak_queue_size,
            r.peak_memory_bytes
        )
        .expect("Failed to write CSV row");
    }

    println!("\n>>> Benchmarks finished successfully!");
    println!(">>> Raw results stored in results/raw/benchmark_raw.json and results/raw/benchmark_raw.csv");
}
