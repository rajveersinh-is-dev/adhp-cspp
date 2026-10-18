//! Carlyle & Wood (2008) Lagrangian Relaxation & Bounding Solver for CSPP.

use crate::dijkstra::{dijkstra_backward, dijkstra_forward};
use crate::{CsppInstance, CsppSolution, CsppSolver, SolutionStatus, SolverStats};
use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::time::Instant;

#[derive(Clone, Copy, PartialEq)]
struct CwLabel {
    vertex: usize,
    cost: f64,
    weight: f64,
    key: f64,
    pool_idx: usize,
}

impl Eq for CwLabel {}

impl Ord for CwLabel {
    fn cmp(&self, other: &Self) -> Ordering {
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

impl PartialOrd for CwLabel {
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

/// Carlyle & Wood (2008) Solver using single-multiplier LARAC Lagrangian Bounding.
#[derive(Debug, Clone, Default)]
pub struct CarlyleWoodSolver;

impl CarlyleWoodSolver {
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

impl CsppSolver for CarlyleWoodSolver {
    fn name(&self) -> &'static str {
        "Carlyle-Wood (LARAC Single-Multiplier Lagrangian Bounding)"
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

        let prep_start = Instant::now();

        // Step 1: Solve extreme points on (s, t)
        let tree_c = dijkstra_forward(&instance.graph, s, 0.0, false);
        let (path_c, cost_c, weight_c) = match tree_c.reconstruct_path_with_metrics(s, t) {
            Some(res) => res,
            None => {
                stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
                return CsppSolution {
                    status: SolutionStatus::Infeasible,
                    path: Vec::new(),
                    cost: f64::INFINITY,
                    weight: f64::INFINITY,
                    stats,
                };
            }
        };

        if weight_c <= budget {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::Optimal,
                path: path_c,
                cost: cost_c,
                weight: weight_c,
                stats,
            };
        }

        let tree_w = dijkstra_forward(&instance.graph, s, 0.0, true);
        if tree_w.distances[t] > budget {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                cost: f64::INFINITY,
                weight: f64::INFINITY,
                stats,
            };
        }

        let (path_w, cost_w, weight_w) = match tree_w.reconstruct_path_with_metrics(s, t) {
            Some(res) => res,
            None => {
                stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
                return CsppSolution {
                    status: SolutionStatus::Infeasible,
                    path: Vec::new(),
                    cost: f64::INFINITY,
                    weight: f64::INFINITY,
                    stats,
                };
            }
        };

        let mut best_cost = cost_w;
        let mut best_weight = weight_w;
        let mut best_path = path_w.clone();

        // Bisection for LARAC lambda*
        let mut p_c = (cost_c, weight_c, path_c);
        let mut p_w = (cost_w, weight_w, path_w);
        let mut opt_lambda = 0.0;

        for _ in 0..20 {
            let dw = p_c.1 - p_w.1;
            if dw <= 1e-9 {
                break;
            }
            let lambda = (p_w.0 - p_c.0) / dw;
            opt_lambda = lambda;

            let tree_r = dijkstra_forward(&instance.graph, s, lambda, false);
            let (path_r, cost_r, weight_r) = match tree_r.reconstruct_path_with_metrics(s, t) {
                Some(res) => res,
                None => break,
            };

            if weight_r <= budget && cost_r < best_cost {
                best_cost = cost_r;
                best_weight = weight_r;
                best_path = path_r.clone();
            }

            if (cost_r + lambda * weight_r - (p_c.0 + lambda * p_c.1)).abs() < 1e-9 {
                break;
            }

            if weight_r <= budget {
                p_w = (cost_r, weight_r, path_r);
            } else {
                p_c = (cost_r, weight_r, path_r);
            }
        }

        // Backward trees: d_{opt_lambda} and d_w
        let dist_lagrange = dijkstra_backward(&instance.graph, t, opt_lambda, false);
        let dist_weight = dijkstra_backward(&instance.graph, t, 0.0, true);

        stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;

        let mut heap = BinaryHeap::new();
        let mut pool: Vec<PoolNode> = Vec::with_capacity(1024);
        let mut frontiers = vec![VertexFrontier::default(); n];

        pool.push(PoolNode {
            vertex: s,
            parent_idx: None,
        });

        frontiers[s].insert_and_prune(0.0, 0.0);

        let root_lb = dist_lagrange[s] - opt_lambda * budget;
        heap.push(CwLabel {
            vertex: s,
            cost: 0.0,
            weight: 0.0,
            key: root_lb,
            pool_idx: 0,
        });

        stats.labels_generated += 1;

        while let Some(label) = heap.pop() {
            stats.labels_explored += 1;
            let u = label.vertex;
            let c_u = label.cost;
            let w_u = label.weight;

            if u == t {
                if c_u < best_cost {
                    best_cost = c_u;
                    best_weight = w_u;
                    best_path = Self::reconstruct_path(&pool, label.pool_idx);
                }
                continue;
            }

            let lb_u = dist_lagrange[u] - opt_lambda * (budget - w_u);
            if c_u + lb_u >= best_cost - 1e-12 {
                stats.labels_pruned_dual_bound += 1;
                continue;
            }

            for edge in instance.graph.outgoing_edges(u) {
                stats.labels_generated += 1;
                let v = edge.target;
                let new_c = c_u + edge.cost;
                let new_w = w_u + edge.weight;

                if new_w + dist_weight[v] > budget {
                    stats.labels_pruned_resource += 1;
                    continue;
                }

                let lb_v = dist_lagrange[v] - opt_lambda * (budget - new_w);
                if new_c + lb_v > best_cost + 1e-9 {
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
                    parent_idx: Some(label.pool_idx),
                });

                heap.push(CwLabel {
                    vertex: v,
                    cost: new_c,
                    weight: new_w,
                    key: new_c + lb_v,
                    pool_idx,
                });

                if heap.len() > stats.peak_queue_size {
                    stats.peak_queue_size = heap.len();
                    let est_mem = heap.capacity() * std::mem::size_of::<CwLabel>()
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
