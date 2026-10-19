//! # ADHP-CSPP: Adaptive Dual Hull Pruning for the Constrained Shortest Path Problem
//!
//! An exact, high-performance algorithm for solving the single-source single-target
//! Weight-Constrained Shortest Path Problem on directed graphs, differentially verified
//! against four baseline solvers and independent integer linear programming oracles.

pub mod adhp;
pub mod baselines;
pub mod dijkstra;
pub mod exact;
pub mod frontier;
pub mod graph;
pub mod hybrid;
pub mod instance_generator;

use serde::{Deserialize, Serialize};

/// Status of the CSPP solver output.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SolutionStatus {
    /// A globally optimal path satisfying the resource budget was found.
    Optimal,
    /// Proved that no path from source to target satisfies the resource budget.
    Infeasible,
    /// Arithmetic overflow occurred during path accumulation, distance relaxation, or bounding.
    ArithmeticOverflow,
    /// Input problem violates supported domain invariants (e.g. invalid node indices, non-finite values).
    UnsupportedInput,
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

    /// Evaluates the total cost and resource consumption of an explicit sequence of edge indices.
    /// This provides unambiguous, exact path verification even in multigraphs with parallel edges.
    pub fn evaluate_edge_path(&self, edge_indices: &[usize]) -> Option<(f64, f64)> {
        if edge_indices.is_empty() {
            if self.source == self.target {
                return Some((0.0, 0.0));
            }
            return None;
        }

        let mut total_cost = 0.0;
        let mut total_weight = 0.0;
        let mut curr_node = self.source;

        for &e_id in edge_indices {
            let edge = self.graph.get_edge(e_id)?;
            if edge.from != curr_node {
                return None;
            }
            total_cost += edge.cost;
            total_weight += edge.weight;
            curr_node = edge.to;
        }

        if curr_node != self.target {
            return None;
        }

        Some((total_cost, total_weight))
    }

    /// Evaluates the total cost and resource consumption of a vertex path.
    /// In multigraphs with parallel edges between adjacent vertices, this method disambiguates
    /// by selecting the edge that is budget-feasible and minimizes cost.
    pub fn evaluate_path(&self, path: &[usize]) -> Option<(f64, f64)> {
        if path.is_empty() || path[0] != self.source || *path.last()? != self.target {
            return None;
        }

        if path.len() == 1 {
            return Some((0.0, 0.0));
        }

        let mut total_cost = 0.0;
        let mut total_weight = 0.0;

        for window in path.windows(2) {
            let u = window[0];
            let v = window[1];

            let candidates: Vec<_> = self
                .graph
                .outgoing_edges(u)
                .iter()
                .filter(|e| e.target == v)
                .collect();

            if candidates.is_empty() {
                return None;
            }

            // Prefer candidate edges whose weight does not exceed the remaining budget,
            // then choose the one minimizing traversal cost.
            let rem_budget = self.budget - total_weight + 1e-9;
            let feasible_candidates: Vec<_> = candidates
                .iter()
                .filter(|e| e.weight <= rem_budget)
                .copied()
                .collect();

            let pool = if !feasible_candidates.is_empty() {
                feasible_candidates
            } else {
                candidates
            };

            let best_edge = pool
                .iter()
                .min_by(|a, b| {
                    a.cost
                        .total_cmp(&b.cost)
                        .then_with(|| a.weight.total_cmp(&b.weight))
                })
                .copied()?;

            total_cost += best_edge.cost;
            total_weight += best_edge.weight;
        }

        Some((total_cost, total_weight))
    }

    /// Converts this floating-point CSPP instance into an exact integer CSPP instance
    /// by scaling costs and weights by positive scale factors and rounding.
    pub fn to_integer_scaled(
        &self,
        scale_cost: f64,
        scale_weight: f64,
    ) -> Result<exact::IntCsppInstance, String> {
        exact::IntCsppInstance::from_scaled_float_instance(self, scale_cost, scale_weight)
    }
}

/// The solution returned by a CSPP solver.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CsppSolution {
    /// Solution status: Optimal or Infeasible.
    pub status: SolutionStatus,
    /// The sequence of vertices on the optimal path (empty if Infeasible).
    pub path: Vec<usize>,
    /// The sequence of edge indices on the optimal path (empty if Infeasible or source == target).
    pub edge_path: Vec<usize>,
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

    /// Solves the given CSPP instance to exact optimality.
    fn solve(&self, instance: &CsppInstance) -> CsppSolution;
}

pub use adhp::AdhpSolver;
pub use baselines::carlyle_wood::CarlyleWoodSolver;
pub use baselines::dumitrescu_boland::DumitrescuBolandSolver;
pub use baselines::martins::MartinsSolver;
pub use baselines::pulse::PulseSolver;
pub use exact::{IntAdhpSolver, IntCsppInstance, IntCsppSolution, IntDirectedGraph};
pub use frontier::{ParetoPoint, VertexFrontier};
pub use graph::DirectedGraph;
pub use hybrid::{AdaptiveSelectionStrategy, HybridAdhpSolver};
