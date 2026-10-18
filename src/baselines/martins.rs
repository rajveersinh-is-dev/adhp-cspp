//! Martins (1984) standard multi-label Dijkstra algorithm with Pareto dominance.

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
        // Min-heap ordering on cost, break ties on weight
        other
            .cost
            .partial_cmp(&self.cost)
            .unwrap_or(Ordering::Equal)
            .then_with(|| {
                other
                    .weight
                    .partial_cmp(&self.weight)
                    .unwrap_or(Ordering::Equal)
            })
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
    parent_idx: Option<usize>,
}

#[derive(Clone, Copy, Debug)]
struct ParetoPoint {
    cost: f64,
    weight: f64,
}

#[derive(Clone, Default)]
struct VertexFrontier {
    points: Vec<ParetoPoint>,
}

impl VertexFrontier {
    #[inline(always)]
    fn is_dominated(&self, new_c: f64, new_w: f64) -> bool {
        for pt in &self.points {
            if pt.weight <= new_w && pt.cost <= new_c {
                return true;
            }
            if pt.weight > new_w {
                break;
            }
        }
        false
    }

    #[inline(always)]
    fn insert_and_prune(&mut self, new_c: f64, new_w: f64) {
        self.points
            .retain(|pt| !(pt.weight >= new_w && pt.cost >= new_c));
        let pos = self
            .points
            .binary_search_by(|pt| pt.weight.partial_cmp(&new_w).unwrap_or(Ordering::Equal))
            .unwrap_or_else(|e| e);
        self.points.insert(
            pos,
            ParetoPoint {
                cost: new_c,
                weight: new_w,
            },
        );
    }
}

/// Martins Standard Multi-Label Dijkstra Solver.
#[derive(Debug, Clone, Default)]
pub struct MartinsSolver;

impl MartinsSolver {
    pub fn new() -> Self {
        Self
    }

    fn reconstruct_path(pool: &[PoolNode], mut curr_idx: usize) -> Vec<usize> {
        let mut path = Vec::new();
        while let Some(node) = pool.get(curr_idx) {
            path.push(node.vertex);
            match node.parent_idx {
                Some(p_idx) => curr_idx = p_idx,
                None => break,
            }
        }
        path.reverse();
        path
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

        if s >= n || t >= n {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
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

        while let Some(label) = heap.pop() {
            stats.labels_explored += 1;
            let u = label.vertex;
            let c_u = label.cost;
            let w_u = label.weight;

            if u == t {
                // Since Martins extracts in order of increasing cost,
                // the very first feasible label to reach t is guaranteed optimal!
                if c_u < best_cost {
                    best_cost = c_u;
                    best_weight = w_u;
                    best_path = Self::reconstruct_path(&pool, label.pool_idx);
                    break;
                }
            }

            for edge in instance.graph.outgoing_edges(u) {
                stats.labels_generated += 1;
                let v = edge.target;
                let new_c = c_u + edge.cost;
                let new_w = w_u + edge.weight;

                if new_w > budget {
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
                    parent_idx: Some(label.pool_idx),
                });

                heap.push(MartinsLabel {
                    vertex: v,
                    cost: new_c,
                    weight: new_w,
                    pool_idx,
                });

                if heap.len() > stats.peak_queue_size {
                    stats.peak_queue_size = heap.len();
                    let est_mem = heap.capacity() * std::mem::size_of::<MartinsLabel>()
                        + pool.capacity() * std::mem::size_of::<PoolNode>()
                        + frontiers
                            .iter()
                            .map(|f| f.points.capacity() * std::mem::size_of::<ParetoPoint>())
                            .sum::<usize>();
                    if est_mem > stats.peak_memory_bytes {
                        stats.peak_memory_bytes = est_mem;
                    }
                }
            }
        }

        stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;

        if best_cost.is_finite() && !best_path.is_empty() {
            CsppSolution {
                status: SolutionStatus::Optimal,
                path: best_path,
                cost: best_cost,
                weight: best_weight,
                stats,
            }
        } else {
            CsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                cost: f64::INFINITY,
                weight: f64::INFINITY,
                stats,
            }
        }
    }
}
