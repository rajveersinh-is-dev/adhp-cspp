//! Single-source shortest path algorithms using Dijkstra's method.

use crate::graph::DirectedGraph;
use std::cmp::Ordering;
use std::collections::BinaryHeap;

/// State item for the min-heap in Dijkstra's algorithm.
#[derive(Copy, Clone, PartialEq)]
struct HeapItem {
    vertex: usize,
    dist: f64,
}

impl Eq for HeapItem {}

impl Ord for HeapItem {
    fn cmp(&self, other: &Self) -> Ordering {
        // Min-heap ordering: invert comparison. Handle NaNs safely.
        other
            .dist
            .partial_cmp(&self.dist)
            .unwrap_or(Ordering::Equal)
    }
}

impl PartialOrd for HeapItem {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Result of a single-source shortest path query.
#[derive(Debug, Clone)]
pub struct ShortestPathTree {
    /// Distances from the source vertex to every vertex in the graph.
    pub distances: Vec<f64>,
    /// Predecessor array for path reconstruction (`None` if unreachable or root).
    pub predecessors: Vec<Option<usize>>,
    /// Predecessor edge (cost, weight) metrics.
    pub predecessor_edges: Vec<Option<(f64, f64)>>,
    /// Predecessor edge IDs.
    pub predecessor_edge_ids: Vec<Option<usize>>,
}

impl ShortestPathTree {
    /// Reconstructs the shortest path from the source to target vertex `t`.
    pub fn reconstruct_path(&self, source: usize, target: usize) -> Option<Vec<usize>> {
        self.reconstruct_path_with_metrics(source, target)
            .map(|(p, _, _, _)| p)
    }

    /// Reconstructs the shortest path along with exact cost and resource weight.
    pub fn reconstruct_path_with_metrics(
        &self,
        source: usize,
        target: usize,
    ) -> Option<(Vec<usize>, Vec<usize>, f64, f64)> {
        if target >= self.distances.len() || self.distances[target].is_infinite() {
            return None;
        }
        if source == target {
            return Some((vec![source], Vec::new(), 0.0, 0.0));
        }

        let mut path = Vec::new();
        let mut edge_path = Vec::new();
        let mut curr = target;
        path.push(curr);
        let mut total_cost = 0.0;
        let mut total_weight = 0.0;

        while curr != source {
            let pred = self.predecessors[curr]?;
            let (c, w) = self.predecessor_edges[curr]?;
            if let Some(e_id) = self.predecessor_edge_ids[curr] {
                edge_path.push(e_id);
            }
            total_cost += c;
            total_weight += w;
            curr = pred;
            path.push(curr);
        }

        path.reverse();
        edge_path.reverse();
        Some((path, edge_path, total_cost, total_weight))
    }
}

/// Computes the single-source shortest path tree from `source` on graph `graph`
/// using custom edge metric $c_e + \lambda w_e$.
pub fn dijkstra_forward(
    graph: &DirectedGraph,
    source: usize,
    lambda: f64,
    use_weight_only: bool,
) -> ShortestPathTree {
    dijkstra_forward_internal(graph, source, None, lambda, use_weight_only)
}

/// Computes the shortest path from `source` to `target` with early exit as soon as
/// the target vertex is popped from the priority queue.
pub fn dijkstra_forward_target(
    graph: &DirectedGraph,
    source: usize,
    target: usize,
    lambda: f64,
    use_weight_only: bool,
) -> ShortestPathTree {
    dijkstra_forward_internal(graph, source, Some(target), lambda, use_weight_only)
}

fn dijkstra_forward_internal(
    graph: &DirectedGraph,
    source: usize,
    target_to_stop: Option<usize>,
    lambda: f64,
    use_weight_only: bool,
) -> ShortestPathTree {
    let n = graph.num_nodes();
    let mut distances = vec![f64::INFINITY; n];
    let mut predecessors = vec![None; n];
    let mut predecessor_edges = vec![None; n];
    let mut predecessor_edge_ids = vec![None; n];
    let mut visited = vec![false; n];

    if source >= n {
        return ShortestPathTree {
            distances,
            predecessors,
            predecessor_edges,
            predecessor_edge_ids,
        };
    }

    let mut heap = BinaryHeap::new();
    distances[source] = 0.0;
    heap.push(HeapItem {
        vertex: source,
        dist: 0.0,
    });

    while let Some(HeapItem { vertex: u, dist: d }) = heap.pop() {
        if visited[u] {
            continue;
        }
        visited[u] = true;

        if let Some(target) = target_to_stop {
            if u == target {
                break;
            }
        }

        if d > distances[u] {
            continue;
        }

        for edge in graph.outgoing_edges(u) {
            let v = edge.target;
            let edge_len = if use_weight_only {
                edge.weight
            } else {
                edge.cost + lambda * edge.weight
            };

            let new_dist = d + edge_len;
            if new_dist < distances[v] {
                distances[v] = new_dist;
                predecessors[v] = Some(u);
                predecessor_edges[v] = Some((edge.cost, edge.weight));
                predecessor_edge_ids[v] = Some(edge.edge_id);
                heap.push(HeapItem {
                    vertex: v,
                    dist: new_dist,
                });
            }
        }
    }

    ShortestPathTree {
        distances,
        predecessors,
        predecessor_edges,
        predecessor_edge_ids,
    }
}

/// Computes the reverse shortest path tree from `target` on the reversed graph $G^R$
/// using custom edge metric $c_e + \lambda w_e$.
///
/// For each vertex $u$, `distances[u]` gives the shortest path distance from $u$ to $target$.
pub fn dijkstra_backward(
    graph: &DirectedGraph,
    target: usize,
    lambda: f64,
    use_weight_only: bool,
) -> Vec<f64> {
    let n = graph.num_nodes();
    let mut distances = vec![f64::INFINITY; n];
    let mut visited = vec![false; n];

    if target >= n {
        return distances;
    }

    let mut heap = BinaryHeap::new();
    distances[target] = 0.0;
    heap.push(HeapItem {
        vertex: target,
        dist: 0.0,
    });

    while let Some(HeapItem { vertex: u, dist: d }) = heap.pop() {
        if visited[u] {
            continue;
        }
        visited[u] = true;

        if d > distances[u] {
            continue;
        }

        // Traverse incoming edges in G (which are outgoing edges from u in G^R)
        for edge in graph.incoming_edges(u) {
            let v = edge.target;
            let edge_len = if use_weight_only {
                edge.weight
            } else {
                edge.cost + lambda * edge.weight
            };

            let new_dist = d + edge_len;
            if new_dist < distances[v] {
                distances[v] = new_dist;
                heap.push(HeapItem {
                    vertex: v,
                    dist: new_dist,
                });
            }
        }
    }

    distances
}
