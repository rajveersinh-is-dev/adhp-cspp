//! Dumitrescu & Boland (2003) 1D-bounded label setting algorithm.

use crate::dijkstra::dijkstra_backward;
use crate::frontier::VertexFrontier;
use crate::{CsppInstance, CsppSolution, CsppSolver, SolutionStatus, SolverStats};
use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::time::Instant;

#[derive(Clone, Copy, PartialEq)]
struct DbLabel {
    vertex: usize,
    cost: f64,
    weight: f64,
    key: f64,
    pool_idx: usize,
}

impl Eq for DbLabel {}

impl Ord for DbLabel {
    fn cmp(&self, other: &Self) -> Ordering {
        // Min-heap ordering on cost lower bound
        other
            .key
            .partial_cmp(&self.key)
            .unwrap_or(Ordering::Equal)
            .then_with(|| {
                other
                    .weight
                    .partial_cmp(&self.weight)
                    .unwrap_or(Ordering::Equal)
            })
    }
}

impl PartialOrd for DbLabel {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

#[derive(Clone, Copy)]
struct PoolNode {
    vertex: usize,
    edge_id: Option<usize>,
    parent_idx: Option<usize>,
}

/// Dumitrescu & Boland (2003) 1D-Bounded Label Setting Solver.
#[derive(Debug, Clone, Default)]
pub struct DumitrescuBolandSolver;

impl DumitrescuBolandSolver {
    pub fn new() -> Self {
        Self
    }

    fn reconstruct_path(pool: &[PoolNode], mut curr_idx: usize) -> (Vec<usize>, Vec<usize>) {
        let mut path = Vec::new();
        let mut edge_path = Vec::new();
        while let Some(node) = pool.get(curr_idx) {
            path.push(node.vertex);
            if let Some(e_id) = node.edge_id {
                edge_path.push(e_id);
            }
            match node.parent_idx {
                Some(p_idx) => curr_idx = p_idx,
                None => break,
            }
        }
        path.reverse();
        edge_path.reverse();
        (path, edge_path)
    }
}

impl CsppSolver for DumitrescuBolandSolver {
    fn name(&self) -> &'static str {
        "Dumitrescu-Boland (1D-Bounded Label Setting)"
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
        // Compute 1D reverse shortest path trees: d_c and d_w
        let dist_cost = dijkstra_backward(&instance.graph, t, 0.0, false);
        let dist_weight = dijkstra_backward(&instance.graph, t, 0.0, true);
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

        let mut heap = BinaryHeap::new();
        let mut pool: Vec<PoolNode> = Vec::with_capacity(1024);
        let mut frontiers = vec![VertexFrontier::default(); n];

        pool.push(PoolNode {
            vertex: s,
            edge_id: None,
            parent_idx: None,
        });

        frontiers[s].insert_and_prune(0.0, 0.0);
        heap.push(DbLabel {
            vertex: s,
            cost: 0.0,
            weight: 0.0,
            key: dist_cost[s],
            pool_idx: 0,
        });

        stats.labels_generated += 1;

        let mut best_cost = f64::INFINITY;
        let mut best_weight = f64::INFINITY;
        let mut best_path = Vec::new();
        let mut best_edge_path = Vec::new();

        while let Some(label) = heap.pop() {
            stats.labels_explored += 1;
            let u = label.vertex;
            let c_u = label.cost;
            let w_u = label.weight;

            if u == t {
                if c_u < best_cost && w_u <= budget + weight_tol {
                    best_cost = c_u;
                    best_weight = w_u;
                    let (p, ep) = Self::reconstruct_path(&pool, label.pool_idx);
                    best_path = p;
                    best_edge_path = ep;
                }
                continue;
            }

            if c_u + dist_cost[u] > best_cost + 1e-9 {
                stats.labels_pruned_dual_bound += 1;
                continue;
            }

            for edge in instance.graph.outgoing_edges(u) {
                stats.labels_generated += 1;
                let v = edge.target;
                let new_c = c_u + edge.cost;
                let new_w = w_u + edge.weight;

                // 1D Resource bound
                if new_w + dist_weight[v] > budget + weight_tol {
                    stats.labels_pruned_resource += 1;
                    continue;
                }

                // 1D Cost bound (with conservative epsilon policy)
                if new_c + dist_cost[v] > best_cost + 1e-9 {
                    stats.labels_pruned_dual_bound += 1;
                    continue;
                }

                if frontiers[v].is_dominated(new_c, new_w) {
                    stats.labels_pruned_dominance += 1;
                    continue;
                }

                frontiers[v].insert_and_prune(new_c, new_w);

                let pool_idx = pool.len();
                pool.push(PoolNode {
                    vertex: v,
                    edge_id: Some(edge.edge_id),
                    parent_idx: Some(label.pool_idx),
                });

                heap.push(DbLabel {
                    vertex: v,
                    cost: new_c,
                    weight: new_w,
                    key: new_c + dist_cost[v],
                    pool_idx,
                });
            }

            if heap.len() > stats.peak_queue_size {
                stats.peak_queue_size = heap.len();
            }
        }

        stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;

        if !best_path.is_empty() {
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
