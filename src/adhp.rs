//! Adaptive Dual Hull Pruning (ADHP) Solver for the Constrained Shortest Path Problem.

use crate::dijkstra::{dijkstra_backward, dijkstra_forward};
use crate::{CsppInstance, CsppSolution, CsppSolver, SolutionStatus, SolverStats};
use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::time::Instant;

/// Priority queue search label.
#[derive(Clone, Copy, PartialEq)]
struct SearchLabel {
    vertex: usize,
    cost: f64,
    weight: f64,
    /// Key for min-heap: $c + \mathcal{L}_u(W - w)$
    key: f64,
    /// Index in the label pool for path reconstruction.
    pool_idx: usize,
}

impl Eq for SearchLabel {}

impl Ord for SearchLabel {
    fn cmp(&self, other: &Self) -> Ordering {
        // Min-heap ordering: invert comparison. Break ties by smaller weight.
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

impl PartialOrd for SearchLabel {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// A node in the path reconstruction pool.
#[derive(Clone, Copy)]
struct PoolNode {
    vertex: usize,
    parent_idx: Option<usize>,
}

/// Represents a non-dominated Pareto label stored at a vertex.
#[derive(Clone, Copy, Debug)]
struct ParetoPoint {
    cost: f64,
    weight: f64,
}

/// Local Pareto frontier at a vertex, maintained sorted by weight ascending.
#[derive(Clone, Default)]
struct VertexFrontier {
    points: Vec<ParetoPoint>,
}

impl VertexFrontier {
    /// Checks if a new label `(c, w)` is weakly dominated by an existing point.
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

    /// Prunes any existing points dominated by `(new_c, new_w)` and inserts the new point.
    #[inline(always)]
    fn insert_and_prune(&mut self, new_c: f64, new_w: f64) {
        // Remove existing points with weight >= new_w and cost >= new_c
        self.points
            .retain(|pt| !(pt.weight >= new_w && pt.cost >= new_c));

        // Insert maintaining sorted order by weight ascending
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

/// Adaptive Dual Hull Pruning (ADHP) Solver.
#[derive(Debug, Clone)]
pub struct AdhpSolver {
    /// Maximum number of dual multipliers $K$ to discover on the lower hull.
    pub max_facets: usize,
}

impl Default for AdhpSolver {
    fn default() -> Self {
        Self { max_facets: 5 }
    }
}

impl AdhpSolver {
    /// Creates a new ADHP solver with the specified maximum number of facets $K$.
    pub fn new(max_facets: usize) -> Self {
        Self {
            max_facets: max_facets.max(2),
        }
    }

    /// Evaluates the discrete dual lower-bound envelope $\mathcal{L}_u^\Lambda(\Delta w)$.
    #[inline(always)]
    fn eval_dual_bound(u: usize, remaining_w: f64, lambdas: &[f64], dist_dual: &[Vec<f64>]) -> f64 {
        let mut max_lb = f64::NEG_INFINITY;
        for (k, &lambda) in lambdas.iter().enumerate() {
            let val = dist_dual[k][u] - lambda * remaining_w;
            if val > max_lb {
                max_lb = val;
            }
        }
        max_lb
    }

    /// Reconstructs the vertex path from the label pool.
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

impl CsppSolver for AdhpSolver {
    fn name(&self) -> &'static str {
        "ADHP (Adaptive Dual Hull Pruning)"
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

        // If unconstrained minimum cost path is feasible, it is globally optimal!
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

        // Check minimum weight path
        let tree_w = dijkstra_forward(&instance.graph, s, 0.0, true);
        if tree_w.distances[t] > budget {
            // Even minimum weight path exceeds budget: certified infeasible!
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

        // Initialize best upper bound with feasible weight-minimizing path
        let mut best_cost = cost_w;
        let mut best_weight = weight_w;
        let mut best_path = path_w.clone();

        // Step 2: Adaptive Dual Multiplier Selection
        let mut lambdas = Vec::with_capacity(self.max_facets);
        lambdas.push(0.0); // Pure cost

        // Bisection queue: store (c_left, w_left, c_right, w_right)
        let mut seg_queue: Vec<(f64, f64, f64, f64)> = Vec::new();
        seg_queue.push((cost_c, weight_c, cost_w, weight_w));

        while lambdas.len() < self.max_facets && !seg_queue.is_empty() {
            let (c_l, w_l, c_r, w_r) = seg_queue.remove(0);
            let dw = w_l - w_r;
            if dw <= 1e-9 {
                continue;
            }
            let dc = c_r - c_l;
            if dc <= 1e-9 {
                continue;
            }

            let lambda_mid = dc / dw;
            if lambdas.iter().any(|&l| (l - lambda_mid).abs() < 1e-6) {
                continue;
            }

            lambdas.push(lambda_mid);

            let tree_mid = dijkstra_forward(&instance.graph, s, lambda_mid, false);
            if let Some((p_mid, c_mid, w_mid)) = tree_mid.reconstruct_path_with_metrics(s, t) {
                if w_mid <= budget && c_mid < best_cost {
                    best_cost = c_mid;
                    best_weight = w_mid;
                    best_path = p_mid.clone();
                }

                if w_l - w_mid > 1e-6 && c_mid - c_l > 1e-6 {
                    seg_queue.push((c_l, w_l, c_mid, w_mid));
                }
                if w_mid - w_r > 1e-6 && c_r - c_mid > 1e-6 {
                    seg_queue.push((c_mid, w_mid, c_r, w_r));
                }
            }
        }

        lambdas.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));

        // Step 3: Compute backward shortest path trees from target t
        let mut dist_dual = Vec::with_capacity(lambdas.len());
        for &lambda in &lambdas {
            let d_back = dijkstra_backward(&instance.graph, t, lambda, false);
            dist_dual.push(d_back);
        }

        let dist_weight = dijkstra_backward(&instance.graph, t, 0.0, true);

        stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;

        // Step 4: Priority Search with Adaptive Dual Hull Pruning
        let mut heap = BinaryHeap::new();
        let mut pool: Vec<PoolNode> = Vec::with_capacity(1024);
        let mut frontiers = vec![VertexFrontier::default(); n];

        pool.push(PoolNode {
            vertex: s,
            parent_idx: None,
        });

        frontiers[s].insert_and_prune(0.0, 0.0);

        let root_lb = Self::eval_dual_bound(s, budget, &lambdas, &dist_dual);
        heap.push(SearchLabel {
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

            // Global upper bound pruning
            let lb_u = Self::eval_dual_bound(u, budget - w_u, &lambdas, &dist_dual);
            if c_u + lb_u >= best_cost - 1e-12 {
                stats.labels_pruned_dual_bound += 1;
                continue;
            }

            for edge in instance.graph.outgoing_edges(u) {
                stats.labels_generated += 1;
                let v = edge.target;
                let new_c = c_u + edge.cost;
                let new_w = w_u + edge.weight;

                // Filter 1: Resource feasibility
                if new_w + dist_weight[v] > budget {
                    stats.labels_pruned_resource += 1;
                    continue;
                }

                // Filter 2: Dual Hull Pruning
                let rem_w = budget - new_w;
                let lb_v = Self::eval_dual_bound(v, rem_w, &lambdas, &dist_dual);
                if new_c + lb_v >= best_cost - 1e-12 {
                    stats.labels_pruned_dual_bound += 1;
                    continue;
                }

                // Filter 3: Local Pareto Dominance
                if frontiers[v].is_dominated(new_c, new_w) {
                    stats.labels_pruned_dominance += 1;
                    continue;
                }

                // Passed all filters: Update vertex frontier and insert into priority queue
                frontiers[v].insert_and_prune(new_c, new_w);

                let pool_idx = pool.len();
                pool.push(PoolNode {
                    vertex: v,
                    parent_idx: Some(label.pool_idx),
                });

                heap.push(SearchLabel {
                    vertex: v,
                    cost: new_c,
                    weight: new_w,
                    key: new_c + lb_v,
                    pool_idx,
                });

                if heap.len() > stats.peak_queue_size {
                    stats.peak_queue_size = heap.len();
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
