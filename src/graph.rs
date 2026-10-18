//! Directed graph representation with forward and reverse edge lists.

use serde::{Deserialize, Serialize};

/// Directed edge with non-negative cost and resource weight.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Edge {
    /// Source vertex index.
    pub from: usize,
    /// Destination vertex index.
    pub to: usize,
    /// Primary objective traversal cost ($c \ge 0$).
    pub cost: f64,
    /// Secondary resource weight/consumption ($w \ge 0$).
    pub weight: f64,
}

/// An incidence record for fast graph traversal.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct HalfEdge {
    /// Neighbor vertex index.
    pub target: usize,
    /// Edge cost ($c \ge 0$).
    pub cost: f64,
    /// Edge resource consumption ($w \ge 0$).
    pub weight: f64,
}

/// Directed graph supporting forward and reverse adjacency lookups.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectedGraph {
    node_count: usize,
    forward_adj: Vec<Vec<HalfEdge>>,
    reverse_adj: Vec<Vec<HalfEdge>>,
    edge_count: usize,
}

impl DirectedGraph {
    /// Creates a new directed graph with the specified number of vertices.
    pub fn new(node_count: usize) -> Self {
        Self {
            node_count,
            forward_adj: vec![Vec::new(); node_count],
            reverse_adj: vec![Vec::new(); node_count],
            edge_count: 0,
        }
    }

    /// Returns the number of vertices in the graph.
    pub fn num_nodes(&self) -> usize {
        self.node_count
    }

    /// Returns the number of directed edges in the graph.
    pub fn num_edges(&self) -> usize {
        self.edge_count
    }

    /// Adds a directed edge from `from` to `to` with non-negative cost and weight.
    ///
    /// Returns `true` if the edge was added, or `false` if vertex indices are out of bounds
    /// or if cost/weight is negative/non-finite.
    pub fn add_edge(&mut self, from: usize, to: usize, cost: f64, weight: f64) -> bool {
        if from >= self.node_count || to >= self.node_count {
            return false;
        }
        if cost < 0.0 || !cost.is_finite() || weight < 0.0 || !weight.is_finite() {
            return false;
        }

        self.forward_adj[from].push(HalfEdge {
            target: to,
            cost,
            weight,
        });
        self.reverse_adj[to].push(HalfEdge {
            target: from,
            cost,
            weight,
        });
        self.edge_count += 1;
        true
    }

    /// Outgoing edges from vertex `u`.
    pub fn outgoing_edges(&self, u: usize) -> &[HalfEdge] {
        if u < self.node_count {
            &self.forward_adj[u]
        } else {
            &[]
        }
    }

    /// Incoming edges to vertex `u` (outgoing edges in the reversed graph $G^R$).
    pub fn incoming_edges(&self, u: usize) -> &[HalfEdge] {
        if u < self.node_count {
            &self.reverse_adj[u]
        } else {
            &[]
        }
    }
}
