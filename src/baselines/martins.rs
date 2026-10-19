use crate::frontier::VertexFrontier;
use crate::{CsppInstance, CsppSolution, CsppSolver, SolutionStatus, SolverStats};
use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::time::Instant;

#[derive(Clone, Copy, PartialEq)]
struct MartinsLabel {
    vertex: usize,
    cost: f64,
    weight: f64,
    pool_idx: usize,
}

impl Eq for MartinsLabel {}

impl Ord for MartinsLabel {
    fn cmp(&self, other: &Self) -> Ordering {
        // Min-heap ordering on cost using IEEE 754 total ordering, break ties on weight
        other
            .cost
            .total_cmp(&self.cost)
            .then_with(|| other.weight.total_cmp(&self.weight))
    }
}

impl PartialOrd for MartinsLabel {
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

/// Martins Standard Multi-Label Dijkstra Solver.
#[derive(Debug, Clone, Default)]
pub struct MartinsSolver;

impl MartinsSolver {
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

impl CsppSolver for MartinsSolver {
    fn name(&self) -> &'static str {
        "Martins (Standard Multi-Label Dijkstra)"
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

        let mut heap = BinaryHeap::new();
        let mut pool: Vec<PoolNode> = Vec::with_capacity(1024);
        let mut frontiers = vec![VertexFrontier::default(); n];

        pool.push(PoolNode {
            vertex: s,
            edge_id: None,
            parent_idx: None,
        });

        frontiers[s].insert_and_prune(0.0, 0.0);
        heap.push(MartinsLabel {
            vertex: s,
            cost: 0.0,
            weight: 0.0,
            pool_idx: 0,
        });

        stats.labels_generated += 1;

        let mut best_cost = f64::INFINITY;
        let mut best_weight = f64::INFINITY;
        let mut best_path = Vec::new();
        let mut best_edge_path = Vec::new();

        let weight_tol = budget.abs().max(1.0) * 1e-9;

        while let Some(label) = heap.pop() {
            stats.labels_explored += 1;
            let u = label.vertex;
            let c_u = label.cost;
            let w_u = label.weight;

            if u == t && c_u < best_cost && w_u <= budget + weight_tol {
                best_cost = c_u;
                best_weight = w_u;
                let (p, ep) = Self::reconstruct_path(&pool, label.pool_idx);
                best_path = p;
                best_edge_path = ep;
                break;
            }

            for edge in instance.graph.outgoing_edges(u) {
                stats.labels_generated += 1;
                let v = edge.target;
                let new_c = c_u + edge.cost;
                let new_w = w_u + edge.weight;

                if new_w > budget + weight_tol {
                    stats.labels_pruned_resource += 1;
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

                heap.push(MartinsLabel {
                    vertex: v,
                    cost: new_c,
                    weight: new_w,
                    pool_idx,
                });
            }

            if heap.len() > stats.peak_queue_size {
                stats.peak_queue_size = heap.len();
            }
        }

        let frontiers_bytes: usize = frontiers.iter().map(|f| f.capacity_bytes()).sum();
        let pool_bytes = pool.capacity() * std::mem::size_of::<PoolNode>();
        let heap_bytes = heap.capacity() * std::mem::size_of::<MartinsLabel>();
        stats.peak_memory_bytes = frontiers_bytes + pool_bytes + heap_bytes;

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
