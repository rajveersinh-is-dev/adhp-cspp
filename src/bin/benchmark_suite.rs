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

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct CanonicalEdge {
    pub from: usize,
    pub to: usize,
    pub cost_bits: String,
    pub weight_bits: String,
    pub cost: f64,
    pub weight: f64,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct InstanceRecord {
    pub schema_version: String,
    pub evaluation_id: String,
    pub benchmark_category: String,
    pub configuration_name: String,
    pub instance_index: usize,
    pub graph_id: String,
    pub nodes: usize,
    pub edges: usize,
    pub source: usize,
    pub target: usize,
    pub budget: f64,
    pub budget_bits: String,
    pub seed: u64,
    pub canonical_edges: Vec<CanonicalEdge>,
}

/// Standard FIPS 180-4 SHA-256 implementation (zero external dependencies).
struct Sha256 {
    state: [u32; 8],
    count: u64,
    buffer: [u8; 64],
}

impl Sha256 {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];

    fn new() -> Self {
        Self {
            state: [
                0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
                0x5be0cd19,
            ],
            count: 0,
            buffer: [0u8; 64],
        }
    }

    fn update(&mut self, data: &[u8]) {
        for &byte in data {
            let idx = (self.count as usize) & 0x3f;
            self.buffer[idx] = byte;
            self.count = self.count.wrapping_add(1);
            if idx == 63 {
                let chunk = self.buffer;
                self.transform(&chunk);
            }
        }
    }

    fn transform(&mut self, chunk: &[u8; 64]) {
        let mut w = [0u32; 64];
        for (i, slot) in w.iter_mut().take(16).enumerate() {
            *slot = u32::from_be_bytes([
                chunk[i * 4],
                chunk[i * 4 + 1],
                chunk[i * 4 + 2],
                chunk[i * 4 + 3],
            ]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }

        let mut a = self.state[0];
        let mut b = self.state[1];
        let mut c = self.state[2];
        let mut d = self.state[3];
        let mut e = self.state[4];
        let mut f = self.state[5];
        let mut g = self.state[6];
        let mut h = self.state[7];

        for (i, &w_i) in w.iter().enumerate() {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(Self::K[i])
                .wrapping_add(w_i);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }

        self.state[0] = self.state[0].wrapping_add(a);
        self.state[1] = self.state[1].wrapping_add(b);
        self.state[2] = self.state[2].wrapping_add(c);
        self.state[3] = self.state[3].wrapping_add(d);
        self.state[4] = self.state[4].wrapping_add(e);
        self.state[5] = self.state[5].wrapping_add(f);
        self.state[6] = self.state[6].wrapping_add(g);
        self.state[7] = self.state[7].wrapping_add(h);
    }

    fn finalize(mut self) -> [u8; 32] {
        let bit_count = self.count.wrapping_mul(8);
        let pad_len = if (self.count & 0x3f) < 56 {
            56 - (self.count & 0x3f) as usize
        } else {
            120 - (self.count & 0x3f) as usize
        };
        let mut pad = vec![0u8; pad_len];
        pad[0] = 0x80;
        self.update(&pad);
        self.update(&bit_count.to_be_bytes());

        let mut out = [0u8; 32];
        for (i, val) in self.state.iter().enumerate() {
            out[i * 4..i * 4 + 4].copy_from_slice(&val.to_be_bytes());
        }
        out
    }
}

pub fn get_canonical_edges(instance: &CsppInstance) -> Vec<CanonicalEdge> {
    let mut edges: Vec<CanonicalEdge> = instance
        .graph
        .edges()
        .iter()
        .map(|e| CanonicalEdge {
            from: e.from,
            to: e.to,
            cost_bits: format!("{:016x}", e.cost.to_bits()),
            weight_bits: format!("{:016x}", e.weight.to_bits()),
            cost: e.cost,
            weight: e.weight,
        })
        .collect();
    edges.sort_by(|a, b| {
        (a.from, a.to, &a.cost_bits, &a.weight_bits).cmp(&(
            b.from,
            b.to,
            &b.cost_bits,
            &b.weight_bits,
        ))
    });
    edges
}

pub fn canonical_serialization_bytes(instance: &CsppInstance, edges: &[CanonicalEdge]) -> Vec<u8> {
    let mut buf = Vec::new();
    buf.extend_from_slice(b"adhp-canonical-v1\n");
    buf.extend_from_slice(format!("nodes: {}\n", instance.graph.num_nodes()).as_bytes());
    buf.extend_from_slice(format!("source: {}\n", instance.source).as_bytes());
    buf.extend_from_slice(format!("target: {}\n", instance.target).as_bytes());
    buf.extend_from_slice(format!("budget: {:016x}\n", instance.budget.to_bits()).as_bytes());
    buf.extend_from_slice(format!("edges: {}\n", edges.len()).as_bytes());
    for e in edges {
        buf.extend_from_slice(
            format!("{} {} {} {}\n", e.from, e.to, e.cost_bits, e.weight_bits).as_bytes(),
        );
    }
    buf
}

pub fn compute_canonical_graph_sha256(instance: &CsppInstance, edges: &[CanonicalEdge]) -> String {
    let payload = canonical_serialization_bytes(instance, edges);
    let mut hasher = Sha256::new();
    hasher.update(&payload);
    let digest = hasher.finalize();
    let mut s = String::with_capacity(64);
    for b in digest {
        s.push_str(&format!("{:02x}", b));
    }
    s
}

pub fn create_instance_record(
    evaluation_id: String,
    benchmark_category: String,
    configuration_name: String,
    instance_index: usize,
    seed: u64,
    inst: &CsppInstance,
) -> InstanceRecord {
    let canonical_edges = get_canonical_edges(inst);
    let graph_sha256 = compute_canonical_graph_sha256(inst, &canonical_edges);
    InstanceRecord {
        schema_version: "adhp-canonical-v1".to_string(),
        evaluation_id,
        benchmark_category,
        configuration_name,
        instance_index,
        graph_id: graph_sha256,
        nodes: inst.graph.num_nodes(),
        edges: inst.graph.num_edges(),
        source: inst.source,
        target: inst.target,
        budget: inst.budget,
        budget_bits: format!("{:016x}", inst.budget.to_bits()),
        seed,
        canonical_edges,
    }
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
    sorted_runtimes.sort_by(|a, b| a.total_cmp(b));
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
    let args: Vec<String> = std::env::args().collect();
    let instances_only = args
        .iter()
        .any(|a| a == "--instances-only" || a == "--dry-run");

    println!("==================================================================");
    println!("  ADHP-CSPP: RIGOROUS MULTI-INSTANCE BENCHMARK SUITE EXECUTION   ");
    if instances_only {
        println!("  MODE: Deterministic Instance Generation & Canonical Identity Registry");
    }
    println!("==================================================================");

    let num_instances_per_config = 10;
    let mut records: Vec<BenchmarkRecord> = Vec::new();
    let mut instance_records: Vec<InstanceRecord> = Vec::new();

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
        let config_name = format!("anticorr_n{}", n);
        let instances: Vec<CsppInstance> = (1..=num_instances_per_config)
            .map(|s| {
                let seed = (n as u64) * 1000 + (s as u64) * 77 + 13;
                let inst = generate_anticorrelated_instance(n, 0.25, 0.40, seed);
                instance_records.push(create_instance_record(
                    format!("{}_inst{:02}", config_name, s),
                    "Anti-Correlated Scaling".to_string(),
                    config_name.clone(),
                    s,
                    seed,
                    &inst,
                ));
                inst
            })
            .collect();

        let avg_edges =
            instances.iter().map(|i| i.graph.num_edges()).sum::<usize>() / instances.len();
        let avg_budget = instances.iter().map(|i| i.budget).sum::<f64>() / (instances.len() as f64);

        println!(
            "  n = {:>3} (avg m = {}, avg budget = {:.1}) across {} instances:",
            n, avg_edges, avg_budget, num_instances_per_config
        );

        if !instances_only {
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
                    instance_name: config_name.clone(),
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
    }

    // =========================================================================
    // SUITE 2: Scaling on 2D Mesh Grid Graphs (4x4 to 10x10)
    // =========================================================================
    println!("\n>>> SUITE 2: 2D Mesh Grid Scaling (4x4 to 10x10, 10 instances/size)...");
    for &(r, c) in &[(4, 4), (6, 6), (8, 8), (10, 10)] {
        let n = r * c;
        let config_name = format!("grid_{}x{}", r, c);
        let instances: Vec<CsppInstance> = (1..=num_instances_per_config)
            .map(|s| {
                let seed = (n as u64) * 2000 + (s as u64) * 88 + 17;
                let inst = generate_grid_instance(r, c, 0.45, seed);
                instance_records.push(create_instance_record(
                    format!("{}_inst{:02}", config_name, s),
                    "Grid Scaling".to_string(),
                    config_name.clone(),
                    s,
                    seed,
                    &inst,
                ));
                inst
            })
            .collect();

        let avg_edges =
            instances.iter().map(|i| i.graph.num_edges()).sum::<usize>() / instances.len();
        let avg_budget = instances.iter().map(|i| i.budget).sum::<f64>() / (instances.len() as f64);

        println!(
            "  Grid {}x{} (n = {:>3}, avg m = {}, avg budget = {:.1}) across {} instances:",
            r, c, n, avg_edges, avg_budget, num_instances_per_config
        );

        if !instances_only {
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
                    instance_name: config_name.clone(),
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
    }

    // =========================================================================
    // SUITE 3: Random Erdős-Rényi Graphs (n = 30 to 120)
    // =========================================================================
    println!("\n>>> SUITE 3: Random Erdős-Rényi Scaling (n = 30 to 120, 10 instances/size)...");
    for &n in &[30, 60, 90, 120] {
        let config_name = format!("random_er_n{}", n);
        let instances: Vec<CsppInstance> = (1..=num_instances_per_config)
            .map(|s| {
                let seed = (n as u64) * 3000 + (s as u64) * 99 + 23;
                let inst = generate_random_instance(n, 0.20, 0.45, seed);
                instance_records.push(create_instance_record(
                    format!("{}_inst{:02}", config_name, s),
                    "Random ER Scaling".to_string(),
                    config_name.clone(),
                    s,
                    seed,
                    &inst,
                ));
                inst
            })
            .collect();

        let avg_edges =
            instances.iter().map(|i| i.graph.num_edges()).sum::<usize>() / instances.len();
        let avg_budget = instances.iter().map(|i| i.budget).sum::<f64>() / (instances.len() as f64);

        println!(
            "  Random ER n = {:>3} (avg m = {}, avg budget = {:.1}) across {} instances:",
            n, avg_edges, avg_budget, num_instances_per_config
        );

        if !instances_only {
            for solver in &competitive_solvers {
                let agg = evaluate_solver_across_instances(*solver, &instances);

                records.push(BenchmarkRecord {
                    benchmark_category: "Random ER Scaling".to_string(),
                    instance_name: config_name.clone(),
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
    }

    // =========================================================================
    // SUITE 4: Budget Tightness Sensitivity (alpha = 0.10 to 0.90)
    // =========================================================================
    println!(
        "\n>>> SUITE 4: Budget Factor Sensitivity (alpha = 0.10 to 0.90, 10 instances/alpha)..."
    );
    for &alpha in &[0.10, 0.25, 0.50, 0.75, 0.90] {
        let config_name = format!("budget_alpha_{:.2}", alpha);
        let instances: Vec<CsppInstance> = (1..=num_instances_per_config)
            .map(|s| {
                let seed = 5000 + (s as u64) * 44 + (alpha * 100.0) as u64;
                let inst = generate_anticorrelated_instance(50, 0.25, alpha, seed);
                instance_records.push(create_instance_record(
                    format!("{}_inst{:02}", config_name, s),
                    "Budget Sensitivity".to_string(),
                    config_name.clone(),
                    s,
                    seed,
                    &inst,
                ));
                inst
            })
            .collect();

        let avg_edges =
            instances.iter().map(|i| i.graph.num_edges()).sum::<usize>() / instances.len();
        let avg_budget = instances.iter().map(|i| i.budget).sum::<f64>() / (instances.len() as f64);

        if !instances_only {
            for solver in &competitive_solvers {
                let agg = evaluate_solver_across_instances(*solver, &instances);

                records.push(BenchmarkRecord {
                    benchmark_category: "Budget Sensitivity".to_string(),
                    instance_name: config_name.clone(),
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
    }

    // =========================================================================
    // SUITE 5: Ablation Analysis: Varying Facet Count K in ADHP (K = 1, 2, 3, 5, 8, 12)
    // =========================================================================
    println!("\n>>> SUITE 5: Ablation Study: Facet Count K (K = 1, 2, 3, 5, 8, 12)...");
    let ablation_instances_with_meta: Vec<(CsppInstance, u64, String, Vec<CanonicalEdge>)> = (1
        ..=num_instances_per_config)
        .map(|s| {
            let seed = 7000 + (s as u64) * 31 + 7;
            let inst = generate_anticorrelated_instance(70, 0.25, 0.40, seed);
            let canonical_edges = get_canonical_edges(&inst);
            let graph_id = compute_canonical_graph_sha256(&inst, &canonical_edges);
            (inst, seed, graph_id, canonical_edges)
        })
        .collect();

    let ablation_instances: Vec<CsppInstance> = ablation_instances_with_meta
        .iter()
        .map(|(inst, _, _, _)| inst.clone())
        .collect();

    for &k in &[1, 2, 3, 5, 8, 12] {
        let config_name = format!("ablation_k{}", k);
        for (s, (inst, seed, graph_id, canonical_edges)) in
            ablation_instances_with_meta.iter().enumerate()
        {
            instance_records.push(InstanceRecord {
                schema_version: "adhp-canonical-v1".to_string(),
                evaluation_id: format!("{}_inst{:02}", config_name, s + 1),
                benchmark_category: "Ablation K Facets".to_string(),
                configuration_name: config_name.clone(),
                instance_index: s + 1,
                graph_id: graph_id.clone(),
                nodes: inst.graph.num_nodes(),
                edges: inst.graph.num_edges(),
                source: inst.source,
                target: inst.target,
                budget: inst.budget,
                budget_bits: format!("{:016x}", inst.budget.to_bits()),
                seed: *seed,
                canonical_edges: canonical_edges.clone(),
            });
        }

        if !instances_only {
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
                instance_name: config_name.clone(),
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
    }

    // =========================================================================
    // OUTPUT PERSISTENCE: Save Raw JSON and CSV Artifacts
    // =========================================================================
    std::fs::create_dir_all("results/raw").ok();
    std::fs::create_dir_all("results/processed").ok();

    // Always persist instance registry with canonical graph IDs
    let instance_json = serde_json::to_string_pretty(&instance_records)
        .expect("Failed to serialize instance records");
    let mut inst_file = File::create("results/raw/benchmark_instances.json")
        .expect("Failed to create benchmark_instances.json");
    inst_file
        .write_all(instance_json.as_bytes())
        .expect("Failed to write benchmark_instances.json");

    let distinct_graph_ids: std::collections::HashSet<_> =
        instance_records.iter().map(|r| &r.graph_id).collect();
    println!(
        "\n>>> Instance Registry: {} evaluations recorded across {} distinct canonical graph IDs.",
        instance_records.len(),
        distinct_graph_ids.len()
    );

    if instances_only {
        println!(
            ">>> Instance registry successfully written to results/raw/benchmark_instances.json."
        );
        return;
    }

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sha256_standard_vectors() {
        let mut h = Sha256::new();
        h.update(b"hello");
        let digest = h.finalize();
        let hex: String = digest.iter().map(|b| format!("{:02x}", b)).collect();
        assert_eq!(
            hex,
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        );
    }
}
