//! Deterministic, reproducible instance generators for CSPP benchmarking.

use crate::graph::DirectedGraph;
use crate::CsppInstance;

/// Pseudo-random number generator (LCG) for completely deterministic, zero-dependency generation.
#[derive(Clone)]
pub struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    /// Initializes RNG with a fixed seed.
    pub fn new(seed: u64) -> Self {
        Self {
            state: seed.wrapping_add(0x9E3779B97F4A7C15),
        }
    }

    /// Generates next 64-bit integer.
    pub fn next_u64(&mut self) -> u64 {
        self.state = self
            .state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.state
    }

    /// Generates next float in [0, 1).
    pub fn next_f64(&mut self) -> f64 {
        let val = self.next_u64() >> 11;
        (val as f64) / ((1u64 << 53) as f64)
    }

    /// Generates float in [min, max].
    pub fn gen_range(&mut self, min: f64, max: f64) -> f64 {
        min + self.next_f64() * (max - min)
    }

    /// Generates usize in [min, max).
    pub fn gen_range_usize(&mut self, min: usize, max: usize) -> usize {
        if min >= max {
            min
        } else {
            min + (self.next_u64() as usize % (max - min))
        }
    }
}

/// Generates a directed Erdős-Rényi random graph with uncorrelated costs and weights.
pub fn generate_random_instance(
    n: usize,
    edge_prob: f64,
    budget_factor: f64,
    seed: u64,
) -> CsppInstance {
    let mut rng = DeterministicRng::new(seed);
    let mut graph = DirectedGraph::new(n);

    // Ensure connectivity: generate a Hamiltonian path first
    for i in 0..n - 1 {
        let c = rng.gen_range(1.0, 50.0);
        let w = rng.gen_range(1.0, 50.0);
        graph.add_edge(i, i + 1, c, w);
    }

    // Add random directed edges
    for u in 0..n {
        for v in 0..n {
            if u != v && u + 1 != v && rng.next_f64() < edge_prob {
                let c = rng.gen_range(1.0, 100.0);
                let w = rng.gen_range(1.0, 100.0);
                graph.add_edge(u, v, c, w);
            }
        }
    }

    let source = 0;
    let target = n - 1;

    // Estimate budget using weight distance
    let tree_w = crate::dijkstra::dijkstra_forward(&graph, source, 0.0, true);
    let tree_c = crate::dijkstra::dijkstra_forward(&graph, source, 0.0, false);

    let min_w = tree_w.distances[target];
    let path_c = tree_c.reconstruct_path(source, target).unwrap_or_default();
    let max_w = if let Some((_, w)) =
        CsppInstance::new(graph.clone(), source, target, 0.0).evaluate_path(&path_c)
    {
        w
    } else {
        min_w * 2.0
    };

    let budget = min_w + budget_factor * (max_w - min_w).max(10.0);
    CsppInstance::new(graph, source, target, budget)
}

/// Generates an Anti-Correlated graph: classic hard CSPP benchmark where $w_e = M - c_e + \text{noise}$.
/// This creates an extensive Pareto frontier with numerous non-dominated paths.
pub fn generate_anticorrelated_instance(
    n: usize,
    edge_density: f64,
    budget_factor: f64,
    seed: u64,
) -> CsppInstance {
    let mut rng = DeterministicRng::new(seed);
    let mut graph = DirectedGraph::new(n);

    // Backbone path for guaranteed connectivity
    for i in 0..n - 1 {
        let c = rng.gen_range(10.0, 90.0);
        let w = 100.0 - c + rng.gen_range(-5.0, 5.0).max(1.0);
        graph.add_edge(i, i + 1, c, w);
    }

    for u in 0..n {
        for v in 0..n {
            if u != v && u + 1 != v && rng.next_f64() < edge_density {
                let c = rng.gen_range(5.0, 95.0);
                let w = (100.0 - c + rng.gen_range(-5.0, 5.0)).max(1.0);
                graph.add_edge(u, v, c, w);
            }
        }
    }

    let source = 0;
    let target = n - 1;

    let tree_w = crate::dijkstra::dijkstra_forward(&graph, source, 0.0, true);
    let tree_c = crate::dijkstra::dijkstra_forward(&graph, source, 0.0, false);

    let min_w = tree_w.distances[target];
    let path_c = tree_c.reconstruct_path(source, target).unwrap_or_default();
    let max_w = if let Some((_, w)) =
        CsppInstance::new(graph.clone(), source, target, 0.0).evaluate_path(&path_c)
    {
        w
    } else {
        min_w * 2.0
    };

    let budget = min_w + budget_factor * (max_w - min_w).max(10.0);
    CsppInstance::new(graph, source, target, budget)
}

/// Generates a 2D directed Grid/Mesh graph with right, down, and diagonal transitions.
pub fn generate_grid_instance(
    rows: usize,
    cols: usize,
    budget_factor: f64,
    seed: u64,
) -> CsppInstance {
    let mut rng = DeterministicRng::new(seed);
    let n = rows * cols;
    let mut graph = DirectedGraph::new(n);

    let node_idx = |r: usize, c: usize| r * cols + c;

    for r in 0..rows {
        for c in 0..cols {
            let u = node_idx(r, c);

            // Right edge
            if c + 1 < cols {
                let cost = rng.gen_range(5.0, 50.0);
                let weight = (60.0 - cost + rng.gen_range(-5.0, 5.0)).max(1.0);
                graph.add_edge(u, node_idx(r, c + 1), cost, weight);
            }

            // Down edge
            if r + 1 < rows {
                let cost = rng.gen_range(5.0, 50.0);
                let weight = (60.0 - cost + rng.gen_range(-5.0, 5.0)).max(1.0);
                graph.add_edge(u, node_idx(r + 1, c), cost, weight);
            }

            // Diagonal edge
            if r + 1 < rows && c + 1 < cols {
                let cost = rng.gen_range(8.0, 70.0);
                let weight = (80.0 - cost + rng.gen_range(-5.0, 5.0)).max(1.0);
                graph.add_edge(u, node_idx(r + 1, c + 1), cost, weight);
            }
        }
    }

    let source = 0;
    let target = n - 1;

    let tree_w = crate::dijkstra::dijkstra_forward(&graph, source, 0.0, true);
    let tree_c = crate::dijkstra::dijkstra_forward(&graph, source, 0.0, false);

    let min_w = tree_w.distances[target];
    let path_c = tree_c.reconstruct_path(source, target).unwrap_or_default();
    let max_w = if let Some((_, w)) =
        CsppInstance::new(graph.clone(), source, target, 0.0).evaluate_path(&path_c)
    {
        w
    } else {
        min_w * 2.0
    };

    let budget = min_w + budget_factor * (max_w - min_w).max(10.0);
    CsppInstance::new(graph, source, target, budget)
}
