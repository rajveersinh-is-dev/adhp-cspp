//! Mathematically exact integer CSPP solver and representations.
//!
//! Provides zero-tolerance, exact integer arithmetic optimization for the
//! Weight-Constrained Shortest Path Problem without floating-point representation
//! artifacts, rounding errors, or tolerance-based pruning ambiguities.

use crate::{CsppInstance, SolutionStatus, SolverStats};
use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::time::Instant;

/// Directed edge with integer cost and resource weight.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IntEdge {
    pub id: usize,
    pub from: usize,
    pub to: usize,
    pub cost: u64,
    pub weight: u64,
}

/// Incidence record for fast graph traversal with integer metrics.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct IntHalfEdge {
    pub target: usize,
    pub cost: u64,
    pub weight: u64,
    pub edge_id: usize,
}

/// Directed graph with integer costs and weights.
#[derive(Debug, Clone)]
pub struct IntDirectedGraph {
    node_count: usize,
    forward_adj: Vec<Vec<IntHalfEdge>>,
    reverse_adj: Vec<Vec<IntHalfEdge>>,
    edges: Vec<IntEdge>,
}

impl IntDirectedGraph {
    /// Creates a new integer directed graph with `node_count` vertices.
    pub fn new(node_count: usize) -> Self {
        Self {
            node_count,
            forward_adj: vec![Vec::new(); node_count],
            reverse_adj: vec![Vec::new(); node_count],
            edges: Vec::new(),
        }
    }

    pub fn num_nodes(&self) -> usize {
        self.node_count
    }

    pub fn num_edges(&self) -> usize {
        self.edges.len()
    }

    pub fn edges(&self) -> &[IntEdge] {
        &self.edges
    }

    pub fn get_edge(&self, edge_id: usize) -> Option<&IntEdge> {
        self.edges.get(edge_id)
    }

    pub fn add_edge(&mut self, from: usize, to: usize, cost: u64, weight: u64) -> bool {
        if from >= self.node_count || to >= self.node_count {
            return false;
        }

        let edge_id = self.edges.len();
        self.edges.push(IntEdge {
            id: edge_id,
            from,
            to,
            cost,
            weight,
        });

        self.forward_adj[from].push(IntHalfEdge {
            target: to,
            cost,
            weight,
            edge_id,
        });
        self.reverse_adj[to].push(IntHalfEdge {
            target: from,
            cost,
            weight,
            edge_id,
        });
        true
    }

    pub fn outgoing_edges(&self, u: usize) -> &[IntHalfEdge] {
        if u < self.node_count {
            &self.forward_adj[u]
        } else {
            &[]
        }
    }

    pub fn incoming_edges(&self, u: usize) -> &[IntHalfEdge] {
        if u < self.node_count {
            &self.reverse_adj[u]
        } else {
            &[]
        }
    }
}

/// Exact integer CSPP problem instance.
#[derive(Debug, Clone)]
pub struct IntCsppInstance {
    pub graph: IntDirectedGraph,
    pub source: usize,
    pub target: usize,
    pub budget: u64,
}

impl IntCsppInstance {
    pub fn new(graph: IntDirectedGraph, source: usize, target: usize, budget: u64) -> Self {
        Self {
            graph,
            source,
            target,
            budget,
        }
    }

    /// Converts a floating-point CSPP instance into an exact integer CSPP instance
    /// by scaling costs and weights by positive scale factors and rounding.
    pub fn from_scaled_float_instance(
        instance: &CsppInstance,
        scale_cost: f64,
        scale_weight: f64,
    ) -> Result<Self, String> {
        if scale_cost <= 0.0
            || !scale_cost.is_finite()
            || scale_weight <= 0.0
            || !scale_weight.is_finite()
        {
            return Err("Scale factors must be positive finite real numbers".to_string());
        }

        let scaled_budget = (instance.budget * scale_weight).round();
        if scaled_budget < 0.0 || scaled_budget > u64::MAX as f64 {
            return Err("Scaled budget overflows u64".to_string());
        }
        let budget = scaled_budget as u64;

        let mut int_graph = IntDirectedGraph::new(instance.graph.num_nodes());
        for e in instance.graph.edges() {
            let sc = (e.cost * scale_cost).round();
            let sw = (e.weight * scale_weight).round();
            if sc < 0.0 || sc > u64::MAX as f64 || sw < 0.0 || sw > u64::MAX as f64 {
                return Err(format!("Edge {} overflows u64 after scaling", e.id));
            }
            int_graph.add_edge(e.from, e.to, sc as u64, sw as u64);
        }

        Ok(Self {
            graph: int_graph,
            source: instance.source,
            target: instance.target,
            budget,
        })
    }

    /// Evaluates path with exact integer metrics.
    pub fn evaluate_edge_path(&self, edge_indices: &[usize]) -> Option<(u64, u64)> {
        if edge_indices.is_empty() {
            if self.source == self.target {
                return Some((0, 0));
            }
            return None;
        }

        let mut total_cost: u64 = 0;
        let mut total_weight: u64 = 0;
        let mut curr_node = self.source;

        for &e_id in edge_indices {
            let edge = self.graph.get_edge(e_id)?;
            if edge.from != curr_node {
                return None;
            }
            total_cost = total_cost.checked_add(edge.cost)?;
            total_weight = total_weight.checked_add(edge.weight)?;
            curr_node = edge.to;
        }

        if curr_node != self.target {
            return None;
        }

        Some((total_cost, total_weight))
    }
}

/// The exact integer solution returned by an integer CSPP solver.
#[derive(Debug, Clone)]
pub struct IntCsppSolution {
    pub status: SolutionStatus,
    pub path: Vec<usize>,
    pub edge_path: Vec<usize>,
    pub cost: u64,
    pub weight: u64,
    pub stats: SolverStats,
}

/// Exact integer Pareto point.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct IntParetoPoint {
    pub cost: u64,
    pub weight: u64,
}

/// Exact integer vertex frontier.
#[derive(Clone, Default, Debug, PartialEq, Eq)]
pub struct IntVertexFrontier {
    points: Vec<IntParetoPoint>,
}

impl IntVertexFrontier {
    pub fn new() -> Self {
        Self { points: Vec::new() }
    }

    #[inline(always)]
    pub fn len(&self) -> usize {
        self.points.len()
    }

    #[inline(always)]
    pub fn is_empty(&self) -> bool {
        self.points.is_empty()
    }

    #[inline(always)]
    pub fn points(&self) -> &[IntParetoPoint] {
        &self.points
    }

    #[inline(always)]
    pub fn is_dominated(&self, new_c: u64, new_w: u64) -> bool {
        if self.points.is_empty() {
            return false;
        }
        let pos = self.points.partition_point(|pt| pt.weight <= new_w);
        if pos > 0 {
            return self.points[pos - 1].cost <= new_c;
        }
        false
    }

    #[inline(always)]
    pub fn insert_and_prune(&mut self, new_c: u64, new_w: u64) {
        self.points
            .retain(|pt| !(new_c <= pt.cost && new_w <= pt.weight));
        let pos = self.points.partition_point(|pt| pt.weight < new_w);
        self.points.insert(
            pos,
            IntParetoPoint {
                cost: new_c,
                weight: new_w,
            },
        );
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
struct IntHeapItem {
    vertex: usize,
    dist: u128,
}

impl Ord for IntHeapItem {
    fn cmp(&self, other: &Self) -> Ordering {
        other.dist.cmp(&self.dist)
    }
}

impl PartialOrd for IntHeapItem {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Backward tree with exact 128-bit integer metrics to eliminate overflow.
#[derive(Debug, Clone)]
pub struct IntBackwardTree {
    pub distances: Vec<u128>,
    pub successors: Vec<Option<usize>>,
    pub successor_edges: Vec<Option<(u64, u64)>>,
    pub successor_edge_ids: Vec<Option<usize>>,
}

impl IntBackwardTree {
    pub fn reconstruct_path_with_metrics(
        &self,
        source: usize,
        target: usize,
    ) -> Option<(Vec<usize>, Vec<usize>, u64, u64)> {
        if source >= self.distances.len() || self.distances[source] == u128::MAX {
            return None;
        }
        if source == target {
            return Some((vec![source], Vec::new(), 0, 0));
        }

        let mut path = Vec::new();
        let mut edge_path = Vec::new();
        let mut curr = source;
        path.push(curr);
        let mut total_cost: u64 = 0;
        let mut total_weight: u64 = 0;

        let max_steps = self.distances.len();
        let mut steps = 0;

        while curr != target {
            steps += 1;
            if steps > max_steps {
                return None;
            }
            let next = self.successors[curr]?;
            let (c, w) = self.successor_edges[curr]?;
            if let Some(e_id) = self.successor_edge_ids[curr] {
                edge_path.push(e_id);
            }
            total_cost = total_cost.checked_add(c)?;
            total_weight = total_weight.checked_add(w)?;
            curr = next;
            path.push(curr);
        }

        Some((path, edge_path, total_cost, total_weight))
    }
}

/// Runs reverse Dijkstra from `target` with exact 128-bit integer metric:
/// if `use_weight_only`: $w_e$
/// else: $c_e \cdot \text{den} + w_e \cdot \text{num}$
///
/// Returns `None` if composite metric calculation exceeds `u128::MAX` (preventing silent edge drops).
pub fn dijkstra_backward_tree_int(
    graph: &IntDirectedGraph,
    target: usize,
    num: u64,
    den: u64,
    use_weight_only: bool,
) -> Option<IntBackwardTree> {
    let n = graph.num_nodes();
    let mut distances = vec![u128::MAX; n];
    let mut successors = vec![None; n];
    let mut successor_edges = vec![None; n];
    let mut successor_edge_ids = vec![None; n];
    let mut visited = vec![false; n];

    if target >= n {
        return Some(IntBackwardTree {
            distances,
            successors,
            successor_edges,
            successor_edge_ids,
        });
    }

    let mut heap = BinaryHeap::new();
    distances[target] = 0;
    heap.push(IntHeapItem {
        vertex: target,
        dist: 0,
    });

    while let Some(IntHeapItem { vertex: u, dist: d }) = heap.pop() {
        if visited[u] {
            continue;
        }
        visited[u] = true;

        if d > distances[u] {
            continue;
        }

        for edge in graph.incoming_edges(u) {
            let v = edge.target;
            let edge_len: u128 = if use_weight_only {
                edge.weight as u128
            } else {
                let c_term = (edge.cost as u128).checked_mul(den as u128)?;
                let w_term = (edge.weight as u128).checked_mul(num as u128)?;
                c_term.checked_add(w_term)?
            };

            if let Some(new_dist) = d.checked_add(edge_len) {
                if new_dist < distances[v] {
                    distances[v] = new_dist;
                    successors[v] = Some(u);
                    successor_edges[v] = Some((edge.cost, edge.weight));
                    successor_edge_ids[v] = Some(edge.edge_id);
                    heap.push(IntHeapItem {
                        vertex: v,
                        dist: new_dist,
                    });
                }
            }
        }
    }

    Some(IntBackwardTree {
        distances,
        successors,
        successor_edges,
        successor_edge_ids,
    })
}

/// Dual facet for exact integer lower bounding.
#[derive(Clone, Debug)]
pub struct IntDualFacet {
    pub num: u64,
    pub den: u64,
    pub distances: Vec<u128>,
}

impl IntDualFacet {
    /// Computes $\lceil \max(0, d_\lambda(u, t) - \lambda \cdot \Delta w) \rceil$ with exact 128-bit integer arithmetic.
    #[inline(always)]
    pub fn eval_lb(&self, u: usize, rem_w: u64) -> u64 {
        let d = self.distances[u];
        if d == u128::MAX {
            return u64::MAX;
        }
        let subtrahend = match (rem_w as u128).checked_mul(self.num as u128) {
            Some(s) => s,
            None => return 0,
        };
        if d <= subtrahend {
            return 0;
        }
        let numerator = d - subtrahend;
        let lb = numerator.div_ceil(self.den as u128);
        if lb > u64::MAX as u128 {
            u64::MAX
        } else {
            lb as u64
        }
    }
}

/// Exact integer priority search label.
#[derive(Clone, Copy, PartialEq, Eq)]
struct IntSearchLabel {
    vertex: usize,
    cost: u64,
    weight: u64,
    key: u64,
    pool_idx: usize,
}

impl Ord for IntSearchLabel {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .key
            .cmp(&self.key)
            .then_with(|| other.weight.cmp(&self.weight))
    }
}

impl PartialOrd for IntSearchLabel {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

#[derive(Clone, Copy)]
struct IntPoolNode {
    vertex: usize,
    edge_id: Option<usize>,
    parent_idx: Option<usize>,
}

/// Mathematically exact integer ADHP solver.
#[derive(Debug, Clone, Default)]
pub struct IntAdhpSolver {
    pub max_facets: usize,
}

impl IntAdhpSolver {
    pub fn new(max_facets: usize) -> Self {
        Self {
            max_facets: max_facets.max(1),
        }
    }

    fn eval_envelope(u: usize, rem_w: u64, facets: &[IntDualFacet]) -> u64 {
        let mut max_lb = 0;
        for facet in facets {
            let val = facet.eval_lb(u, rem_w);
            if val > max_lb {
                max_lb = val;
            }
        }
        max_lb
    }

    fn reconstruct_path(pool: &[IntPoolNode], mut curr_idx: usize) -> (Vec<usize>, Vec<usize>) {
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

    /// Solves the integer CSPP instance with 100% mathematical exactness.
    pub fn solve(&self, instance: &IntCsppInstance) -> IntCsppSolution {
        let start_time = Instant::now();
        let mut stats = SolverStats::default();

        let s = instance.source;
        let t = instance.target;
        let budget = instance.budget;
        let n = instance.graph.num_nodes();

        if s >= n || t >= n {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            return IntCsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                edge_path: Vec::new(),
                cost: u64::MAX,
                weight: u64::MAX,
                stats,
            };
        }

        if s == t {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            return IntCsppSolution {
                status: SolutionStatus::Optimal,
                path: vec![s],
                edge_path: Vec::new(),
                cost: 0,
                weight: 0,
                stats,
            };
        }

        let prep_start = Instant::now();

        // 1. Backward tree with pure weight
        let tree_w = match dijkstra_backward_tree_int(&instance.graph, t, 1, 0, true) {
            Some(tree) => tree,
            None => {
                stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
                return IntCsppSolution {
                    status: SolutionStatus::Infeasible,
                    path: Vec::new(),
                    edge_path: Vec::new(),
                    cost: u64::MAX,
                    weight: u64::MAX,
                    stats,
                };
            }
        };

        if tree_w.distances[s] > budget as u128 || tree_w.distances[s] == u128::MAX {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;
            return IntCsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                edge_path: Vec::new(),
                cost: u64::MAX,
                weight: u64::MAX,
                stats,
            };
        }

        let (path_w, edge_path_w, cost_w, weight_w) =
            match tree_w.reconstruct_path_with_metrics(s, t) {
                Some(res) => res,
                None => {
                    stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
                    return IntCsppSolution {
                        status: SolutionStatus::Infeasible,
                        path: Vec::new(),
                        edge_path: Vec::new(),
                        cost: u64::MAX,
                        weight: u64::MAX,
                        stats,
                    };
                }
            };

        // 2. Backward tree with pure cost (lambda = 0, num = 0, den = 1)
        let tree_c = match dijkstra_backward_tree_int(&instance.graph, t, 0, 1, false) {
            Some(tree) => tree,
            None => {
                stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
                return IntCsppSolution {
                    status: SolutionStatus::Infeasible,
                    path: Vec::new(),
                    edge_path: Vec::new(),
                    cost: u64::MAX,
                    weight: u64::MAX,
                    stats,
                };
            }
        };

        let (path_c, edge_path_c, cost_c, weight_c) =
            match tree_c.reconstruct_path_with_metrics(s, t) {
                Some(res) => res,
                None => {
                    stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
                    return IntCsppSolution {
                        status: SolutionStatus::Infeasible,
                        path: Vec::new(),
                        edge_path: Vec::new(),
                        cost: u64::MAX,
                        weight: u64::MAX,
                        stats,
                    };
                }
            };

        // If unconstrained minimum cost path is feasible, it is globally optimal!
        if weight_c <= budget {
            stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;
            stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;
            return IntCsppSolution {
                status: SolutionStatus::Optimal,
                path: path_c,
                edge_path: edge_path_c,
                cost: cost_c,
                weight: weight_c,
                stats,
            };
        }

        let mut best_cost = cost_w;
        let mut best_weight = weight_w;
        let mut best_path = path_w;
        let mut best_edge_path = edge_path_w;

        // Step 2: Facet discovery
        let mut facets = Vec::with_capacity(self.max_facets);
        facets.push(IntDualFacet {
            num: 0,
            den: 1,
            distances: tree_c.distances,
        });

        let mut seg_queue = vec![(cost_c, weight_c, cost_w, weight_w)];

        while facets.len() < self.max_facets && !seg_queue.is_empty() {
            let (c_l, w_l, c_r, w_r) = seg_queue.remove(0);
            if w_l <= w_r || c_r <= c_l {
                continue;
            }
            let dw = w_l - w_r;
            let dc = c_r - c_l;

            // Rational multiplier lambda = dc / dw
            let maybe_tree_mid = dijkstra_backward_tree_int(&instance.graph, t, dc, dw, false);
            if let Some(tree_mid) = maybe_tree_mid {
                if let Some((p_mid, ep_mid, c_mid, w_mid)) =
                    tree_mid.reconstruct_path_with_metrics(s, t)
                {
                    if w_mid <= budget && c_mid < best_cost {
                        best_cost = c_mid;
                        best_weight = w_mid;
                        best_path = p_mid;
                        best_edge_path = ep_mid;
                    }

                    facets.push(IntDualFacet {
                        num: dc,
                        den: dw,
                        distances: tree_mid.distances,
                    });

                    if w_l > w_mid && c_mid > c_l {
                        seg_queue.push((c_l, w_l, c_mid, w_mid));
                    }
                    if w_mid > w_r && c_r > c_mid {
                        seg_queue.push((c_mid, w_mid, c_r, w_r));
                    }
                }
            }
        }

        let dist_weight = tree_w.distances;
        stats.preprocessing_nanos = prep_start.elapsed().as_nanos() as u64;

        // Step 3: Priority Search with exact integer operations
        let mut heap: BinaryHeap<IntSearchLabel> = BinaryHeap::new();
        let mut frontiers: Vec<IntVertexFrontier> = vec![IntVertexFrontier::default(); n];
        let mut pool: Vec<IntPoolNode> = Vec::with_capacity(1024);

        pool.push(IntPoolNode {
            vertex: s,
            edge_id: None,
            parent_idx: None,
        });

        frontiers[s].insert_and_prune(0, 0);

        let root_lb = Self::eval_envelope(s, budget, &facets);
        heap.push(IntSearchLabel {
            vertex: s,
            cost: 0,
            weight: 0,
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
                if w_u <= budget && c_u < best_cost {
                    best_cost = c_u;
                    best_weight = w_u;
                    let (p, ep) = Self::reconstruct_path(&pool, label.pool_idx);
                    best_path = p;
                    best_edge_path = ep;
                }
                continue;
            }

            let lb_u = Self::eval_envelope(u, budget.saturating_sub(w_u), &facets);
            if c_u.saturating_add(lb_u) > best_cost {
                stats.labels_pruned_dual_bound += 1;
                continue;
            }

            for edge in instance.graph.outgoing_edges(u) {
                stats.labels_generated += 1;
                let v = edge.target;
                let new_c = match c_u.checked_add(edge.cost) {
                    Some(c) => c,
                    None => continue,
                };
                let new_w = match w_u.checked_add(edge.weight) {
                    Some(w) => w,
                    None => continue,
                };

                // Filter 1: Resource feasibility
                if dist_weight[v] == u128::MAX
                    || (new_w as u128).saturating_add(dist_weight[v]) > budget as u128
                {
                    stats.labels_pruned_resource += 1;
                    continue;
                }

                // Filter 2: Dual Hull Pruning (Strict integer bound)
                let rem_w = budget.saturating_sub(new_w);
                let lb_v = Self::eval_envelope(v, rem_w, &facets);
                if new_c.saturating_add(lb_v) > best_cost {
                    stats.labels_pruned_dual_bound += 1;
                    continue;
                }

                // Filter 3: Local Pareto Dominance
                if frontiers[v].is_dominated(new_c, new_w) {
                    stats.labels_pruned_dominance += 1;
                    continue;
                }

                frontiers[v].insert_and_prune(new_c, new_w);

                let pool_idx = pool.len();
                pool.push(IntPoolNode {
                    vertex: v,
                    edge_id: Some(edge.edge_id),
                    parent_idx: Some(label.pool_idx),
                });

                heap.push(IntSearchLabel {
                    vertex: v,
                    cost: new_c,
                    weight: new_w,
                    key: new_c.saturating_add(lb_v),
                    pool_idx,
                });
            }

            if heap.len() > stats.peak_queue_size {
                stats.peak_queue_size = heap.len();
            }
        }

        stats.elapsed_nanos = start_time.elapsed().as_nanos() as u64;

        if !best_path.is_empty() {
            IntCsppSolution {
                status: SolutionStatus::Optimal,
                path: best_path,
                edge_path: best_edge_path,
                cost: best_cost,
                weight: best_weight,
                stats,
            }
        } else {
            IntCsppSolution {
                status: SolutionStatus::Infeasible,
                path: Vec::new(),
                edge_path: Vec::new(),
                cost: u64::MAX,
                weight: u64::MAX,
                stats,
            }
        }
    }
}
