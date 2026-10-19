use crate::dijkstra::{dijkstra_backward, dijkstra_backward_tree};
use crate::frontier::VertexFrontier;
use crate::{CsppInstance, CsppSolution, CsppSolver, SolutionStatus, SolverStats};
use std::time::Instant;

/// Pulse Algorithm Solver (Lozano & Medaglia 2013).
#[derive(Debug, Clone, Default)]
pub struct PulseSolver;

impl PulseSolver {
    pub fn new() -> Self {
        Self
    }

    #[allow(clippy::too_many_arguments)]
    fn pulse_dfs(
        u: usize,
        c_u: f64,
        w_u: f64,
        target: usize,
        budget: f64,
        instance: &CsppInstance,
        dist_cost: &[f64],
        dist_weight: &[f64],
        memory: &mut [VertexFrontier],
        visited: &mut [bool],
        current_path: &mut Vec<usize>,
        current_edges: &mut Vec<usize>,
        best_cost: &mut f64,
        best_weight: &mut f64,
        best_path: &mut Vec<usize>,
        best_edge_path: &mut Vec<usize>,
        stats: &mut SolverStats,
    ) {
        let weight_tol = budget.abs().max(1.0) * 1e-9;

        if u == target {
            if c_u < *best_cost && w_u <= budget + weight_tol {
                *best_cost = c_u;
                *best_weight = w_u;
                *best_path = current_path.clone();
                *best_edge_path = current_edges.clone();
            }
            return;
        }

        if current_path.len() > stats.peak_queue_size {
            stats.peak_queue_size = current_path.len();
        }

        // Bound Pruning 1: 1D Cost bound
        if c_u + dist_cost[u] > *best_cost + 1e-9 {
            stats.labels_pruned_dual_bound += 1;
            return;
        }

        // Local Dominance Pruning
        if memory[u].is_dominated(c_u, w_u) {
            stats.labels_pruned_dominance += 1;
            return;
        }
        memory[u].insert_and_prune(c_u, w_u);

        visited[u] = true;

        for edge in instance.graph.outgoing_edges(u) {
            let v = edge.target;
            if visited[v] {
                continue; // Avoid cycles
            }

            stats.labels_generated += 1;
            let new_c = c_u + edge.cost;
            let new_w = w_u + edge.weight;

            // Feasibility Pruning
            if new_w + dist_weight[v] > budget + weight_tol {
                stats.labels_pruned_resource += 1;
                continue;
            }

            // Cost Pruning
            if new_c + dist_cost[v] > *best_cost + 1e-9 {
                stats.labels_pruned_dual_bound += 1;
                continue;
            }

            current_path.push(v);
            current_edges.push(edge.edge_id);
            Self::pulse_dfs(
                v,
                new_c,
                new_w,
                target,
                budget,
                instance,
                dist_cost,
                dist_weight,
                memory,
                visited,
                current_path,
                current_edges,
                best_cost,
                best_weight,
                best_path,
                best_edge_path,
                stats,
            );
            current_edges.pop();
            current_path.pop();
        }

        visited[u] = false;
    }
}

impl CsppSolver for PulseSolver {
    fn name(&self) -> &'static str {
        "Pulse (Lozano & Medaglia 2013)"
    }

    fn solve(&self, instance: &CsppInstance) -> CsppSolution {
        let start_time = Instant::now();
        let mut stats = SolverStats::default();

        let s = instance.source;
        let t = instance.target;
        let budget = instance.budget;
        let n = instance.graph.num_nodes();

        if s >= n || t >= n || budget.is_nan() {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::UnsupportedInput,
                path: Vec::new(),
                edge_path: Vec::new(),
                cost: f64::INFINITY,
                weight: f64::INFINITY,
                stats,
            };
        }

        if budget < 0.0 {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                edge_path: Vec::new(),
                cost: f64::INFINITY,
                weight: f64::INFINITY,
                stats,
            };
        }

        if s == t {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::Optimal,
                path: vec![s],
                edge_path: Vec::new(),
                cost: 0.0,
                weight: 0.0,
                stats,
            };
        }

        let weight_tol = budget.abs().max(1.0) * 1e-9;
        let prep_start = Instant::now();
        let dist_cost = dijkstra_backward(&instance.graph, t, 0.0, false);
        let tree_w = dijkstra_backward_tree(&instance.graph, t, 0.0, true);
        let dist_weight = tree_w.distances.clone();
        stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;

        if dist_weight[s] > budget + weight_tol || dist_cost[s].is_infinite() {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                edge_path: Vec::new(),
                cost: f64::INFINITY,
                weight: f64::INFINITY,
                stats,
            };
        }

        let (mut best_cost, mut best_weight, mut best_path, mut best_edge_path) =
            if let Some((p, ep, c, w)) = tree_w.reconstruct_path_with_metrics(s, t) {
                if w <= budget + weight_tol {
                    (c, w, p, ep)
                } else {
                    (f64::INFINITY, f64::INFINITY, Vec::new(), Vec::new())
                }
            } else {
                (f64::INFINITY, f64::INFINITY, Vec::new(), Vec::new())
            };

        let mut memory = vec![VertexFrontier::default(); n];
        let mut visited = vec![false; n];
        let mut current_path = vec![s];
        let mut current_edges = Vec::new();

        Self::pulse_dfs(
            s,
            0.0,
            0.0,
            t,
            budget,
            instance,
            &dist_cost,
            &dist_weight,
            &mut memory,
            &mut visited,
            &mut current_path,
            &mut current_edges,
            &mut best_cost,
            &mut best_weight,
            &mut best_path,
            &mut best_edge_path,
            &mut stats,
        );

        let frontiers_bytes: usize = memory.iter().map(|f| f.capacity_bytes()).sum();
        let prep_bytes = 2 * n * std::mem::size_of::<f64>();
        let path_bytes = current_path.capacity() * std::mem::size_of::<usize>()
            + current_edges.capacity() * std::mem::size_of::<usize>();
        let visited_bytes = visited.len() * std::mem::size_of::<bool>();
        stats.peak_memory_bytes = frontiers_bytes + prep_bytes + path_bytes + visited_bytes;

        stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;

        if best_cost.is_finite() && !best_path.is_empty() {
            CsppSolution {
                status: SolutionStatus::Optimal,
                path: best_path,
                edge_path: best_edge_path,
                cost: best_cost,
                weight: best_weight,
                stats,
            }
        } else {
            CsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                edge_path: Vec::new(),
                cost: f64::INFINITY,
                weight: f64::INFINITY,
                stats,
            }
        }
    }
}
