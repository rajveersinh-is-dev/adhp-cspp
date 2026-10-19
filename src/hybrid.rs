//! Instance-Adaptive Hybrid CSPP Solver.
//!
//! Adaptively selects the optimal dual lower-bounding depth based on observable
//! instance characteristics (graph density, duality gap, and resource tightness)
//! measured in constant time before search, preserving exact optimality while
//! eliminating dual preprocessing overhead on dense networks and loose-budget instances.

use crate::dijkstra::dijkstra_backward_tree;
use crate::frontier::VertexFrontier;
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
    key: f64,
    pool_idx: usize,
}

impl Eq for SearchLabel {}

impl Ord for SearchLabel {
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

impl PartialOrd for SearchLabel {
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

/// Adaptive selection mode chosen by the hybrid solver.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdaptiveSelectionStrategy {
    /// 1D Lagrangian bounding ($K=1$): optimal for dense graphs and loose budgets.
    OneDimensionalFast,
    /// Balanced dual bounding ($K=2$): optimal for moderate density and intermediate gap.
    BalancedDual,
    /// Deep multi-faceted ADHP ($K=5$): optimal for sparse/planar grids with tight budgets.
    DeepMultiFaceted,
}

/// Instance-Adaptive Hybrid CSPP Solver.
#[derive(Debug, Clone, Default)]
pub struct HybridAdhpSolver {
    pub max_facets: usize,
}

impl HybridAdhpSolver {
    pub fn new() -> Self {
        Self { max_facets: 5 }
    }

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

    /// Evaluates observable instance characteristics to select the optimal dual depth.
    pub fn select_strategy(
        num_nodes: usize,
        _num_edges: usize,
        density: f64,
        duality_gap_ratio: f64,
        resource_tightness_alpha: f64,
    ) -> AdaptiveSelectionStrategy {
        if duality_gap_ratio < 0.04
            || resource_tightness_alpha >= 0.85
            || (density >= 3.5 && num_nodes <= 200)
        {
            AdaptiveSelectionStrategy::OneDimensionalFast
        } else if density <= 2.5 && duality_gap_ratio >= 0.15 && resource_tightness_alpha <= 0.70 {
            AdaptiveSelectionStrategy::DeepMultiFaceted
        } else {
            AdaptiveSelectionStrategy::BalancedDual
        }
    }
}

impl CsppSolver for HybridAdhpSolver {
    fn name(&self) -> &'static str {
        "Adaptive Hybrid ADHP"
    }

    fn solve(&self, instance: &CsppInstance) -> CsppSolution {
        let start_time = Instant::now();
        let mut stats = SolverStats::default();

        let s = instance.source;
        let t = instance.target;
        let budget = instance.budget;
        let n = instance.graph.num_nodes();
        let m = instance.graph.num_edges();

        if !budget.is_finite() || budget < 0.0 || s >= n || t >= n {
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

        let prep_start = Instant::now();

        // Step 1: Backward Weight Preprocessing
        let tree_w = dijkstra_backward_tree(&instance.graph, t, 0.0, true);
        if tree_w.distances[s] > budget + 1e-9 || tree_w.distances[s].is_infinite() {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                edge_path: Vec::new(),
                cost: f64::INFINITY,
                weight: f64::INFINITY,
                stats,
            };
        }

        let (path_w, edge_path_w, cost_w, weight_w) =
            match tree_w.reconstruct_path_with_metrics(s, t) {
                Some(res) => res,
                None => {
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
            };

        // Step 2: Backward Cost Preprocessing (lambda = 0)
        let tree_c = dijkstra_backward_tree(&instance.graph, t, 0.0, false);
        let (path_c, edge_path_c, cost_c, weight_c) =
            match tree_c.reconstruct_path_with_metrics(s, t) {
                Some(res) => res,
                None => {
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
            };

        // If unconstrained minimum cost path is feasible, it is globally optimal
        if weight_c <= budget + 1e-9 {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;
            return CsppSolution {
                status: SolutionStatus::Optimal,
                path: path_c,
                edge_path: edge_path_c,
                cost: cost_c,
                weight: weight_c,
                stats,
            };
        }

        // Step 3: Observable Instance Metrics Evaluation
        let density = if n > 0 { m as f64 / n as f64 } else { 0.0 };
        let cost_gap = (cost_w - cost_c).max(0.0);
        let weight_gap = (weight_c - weight_w).max(0.0);
        let duality_gap_ratio = cost_gap / cost_w.max(1.0);
        let tightness_alpha = if weight_gap > 1e-9 {
            ((budget - weight_w) / weight_gap).clamp(0.0, 1.0)
        } else {
            1.0
        };

        let strategy = Self::select_strategy(n, m, density, duality_gap_ratio, tightness_alpha);
        let target_facets = match strategy {
            AdaptiveSelectionStrategy::OneDimensionalFast => 1,
            AdaptiveSelectionStrategy::BalancedDual => 2,
            AdaptiveSelectionStrategy::DeepMultiFaceted => self.max_facets.max(3),
        };

        let mut best_cost = cost_w;
        let mut best_weight = weight_w;
        let mut best_path = path_w;
        let mut best_edge_path = edge_path_w;

        let mut lambdas = Vec::with_capacity(target_facets);
        let mut dist_dual = Vec::with_capacity(target_facets);

        lambdas.push(0.0);
        dist_dual.push(tree_c.distances);

        // Step 4: Facet discovery up to target_facets
        if target_facets > 1 {
            let mut seg_queue: Vec<(f64, f64, f64, f64)> = Vec::new();
            seg_queue.push((cost_c, weight_c, cost_w, weight_w));

            while lambdas.len() < target_facets && !seg_queue.is_empty() {
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

                let tree_mid = dijkstra_backward_tree(&instance.graph, t, lambda_mid, false);
                if let Some((p_mid, ep_mid, c_mid, w_mid)) =
                    tree_mid.reconstruct_path_with_metrics(s, t)
                {
                    if w_mid <= budget + 1e-9 && c_mid < best_cost {
                        best_cost = c_mid;
                        best_weight = w_mid;
                        best_path = p_mid;
                        best_edge_path = ep_mid;
                    }

                    lambdas.push(lambda_mid);
                    dist_dual.push(tree_mid.distances);

                    if w_l - w_mid > 1e-6 && c_mid - c_l > 1e-6 {
                        seg_queue.push((c_l, w_l, c_mid, w_mid));
                    }
                    if w_mid - w_r > 1e-6 && c_r - c_mid > 1e-6 {
                        seg_queue.push((c_mid, w_mid, c_r, w_r));
                    }
                }
            }
        }

        let dist_weight = tree_w.distances;
        stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;

        // Step 5: Priority Search with Adaptive Envelope
        let mut heap: BinaryHeap<SearchLabel> = BinaryHeap::new();
        let mut frontiers: Vec<VertexFrontier> = vec![VertexFrontier::default(); n];
        let mut pool: Vec<PoolNode> = Vec::with_capacity(1024);

        pool.push(PoolNode {
            vertex: s,
            edge_id: None,
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
                if w_u <= budget + 1e-9 && c_u < best_cost {
                    best_cost = c_u;
                    best_weight = w_u;
                    let (p, ep) = Self::reconstruct_path(&pool, label.pool_idx);
                    best_path = p;
                    best_edge_path = ep;
                }
                continue;
            }

            let rem_w_u = (budget - w_u).max(0.0);
            let lb_u = Self::eval_dual_bound(u, rem_w_u, &lambdas, &dist_dual);
            if c_u + lb_u > best_cost + 1e-9 {
                stats.labels_pruned_dual_bound += 1;
                continue;
            }

            for edge in instance.graph.outgoing_edges(u) {
                stats.labels_generated += 1;
                let v = edge.target;
                let new_c = c_u + edge.cost;
                let new_w = w_u + edge.weight;

                // Filter 1: Resource feasibility
                if dist_weight[v].is_infinite() || new_w + dist_weight[v] > budget + 1e-9 {
                    stats.labels_pruned_resource += 1;
                    continue;
                }

                // Filter 2: Dual envelope bounding
                let rem_w_v = (budget - new_w).max(0.0);
                let lb_v = Self::eval_dual_bound(v, rem_w_v, &lambdas, &dist_dual);
                if new_c + lb_v > best_cost + 1e-9 {
                    stats.labels_pruned_dual_bound += 1;
                    continue;
                }

                // Filter 3: Pareto Dominance
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

                heap.push(SearchLabel {
                    vertex: v,
                    cost: new_c,
                    weight: new_w,
                    key: new_c + lb_v,
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
