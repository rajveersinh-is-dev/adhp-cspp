//! # ADHP-CSPP: Adaptive Dual Hull Pruning for the Constrained Shortest Path Problem
//!
//! An exact, mathematically certified, high-performance algorithm for solving the
//! single-source single-target Weight-Constrained Shortest Path Problem on directed graphs.

pub mod adhp;
pub mod baselines;
pub mod dijkstra;
pub mod graph;
pub mod instance_generator;

use serde::{Deserialize, Serialize};

/// Status of the CSPP solver output.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SolutionStatus {
    /// A globally optimal path satisfying the resource budget was found.
    Optimal,
    /// Certified that no path from source to target satisfies the resource budget.
    Infeasible,
}

/// Statistics gathered during the execution of a CSPP solver.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SolverStats {
    /// Total wall-clock execution time in nanoseconds.
    pub elapsed_nanos: u64,
    /// Preprocessing time in nanoseconds.
    pub preprocessing_nanos: u64,
    /// Total number of candidate labels generated during edge relaxations.
    pub labels_generated: usize,
    /// Labels pruned immediately because remaining resource is insufficient.
    pub labels_pruned_resource: usize,
    /// Labels pruned because dual lower-bound envelope exceeds upper bound.
    pub labels_pruned_dual_bound: usize,
    /// Labels pruned because they are Pareto-dominated by an existing label at the vertex.
    pub labels_pruned_dominance: usize,
    /// Maximum number of active labels in the priority queue at any point.
    pub peak_queue_size: usize,
    /// Estimated peak memory allocated by label queues and frontiers in bytes.
    pub peak_memory_bytes: usize,
    /// Total number of labels popped and explored from the priority queue.
    pub labels_explored: usize,
}

/// A CSPP problem instance.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CsppInstance {
    /// The underlying directed graph.
    pub graph: graph::DirectedGraph,
    /// Source vertex index.
    pub source: usize,
    /// Destination vertex index.
    pub target: usize,
    /// Maximum allowable cumulative resource weight ($W \ge 0$).
    pub budget: f64,
}

impl CsppInstance {
    /// Creates a new CSPP instance.
    pub fn new(graph: graph::DirectedGraph, source: usize, target: usize, budget: f64) -> Self {
        Self {
            graph,
            source,
            target,
            budget,
        }
    }

    /// Evaluates the total cost and resource consumption of a given path.
    pub fn evaluate_path(&self, path: &[usize]) -> Option<(f64, f64)> {
        if path.is_empty() || path[0] != self.source || *path.last()? != self.target {
            return None;
        }

        let mut total_cost = 0.0;
        let mut total_weight = 0.0;

        for window in path.windows(2) {
            let u = window[0];
            let v = window[1];

            // Find matching edge from u to v
            let edge = self
                .graph
                .outgoing_edges(u)
                .iter()
                .find(|e| e.target == v)?;

            total_cost += edge.cost;
            total_weight += edge.weight;
        }

        Some((total_cost, total_weight))
    }
}

/// The solution returned by a CSPP solver.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CsppSolution {
    /// Solution status: Optimal or Infeasible.
    pub status: SolutionStatus,
    /// The sequence of vertices on the optimal path (empty if Infeasible).
    pub path: Vec<usize>,
    /// Total cost of the optimal path (or +inf if Infeasible).
    pub cost: f64,
    /// Total resource weight of the optimal path (or +inf if Infeasible).
    pub weight: f64,
    /// Detailed solver execution metrics.
    pub stats: SolverStats,
}

/// Common trait implemented by all CSPP solvers (proposed and baselines).
pub trait CsppSolver {
    /// Returns the human-readable algorithm name.
    fn name(&self) -> &'static str;

    /// Solves the given CSPP instance to certified exact optimality.
    fn solve(&self, instance: &CsppInstance) -> CsppSolution;
}

pub use adhp::AdhpSolver;
pub use baselines::carlyle_wood::CarlyleWoodSolver;
pub use baselines::dumitrescu_boland::DumitrescuBolandSolver;
pub use baselines::martins::MartinsSolver;
pub use baselines::pulse::PulseSolver;
