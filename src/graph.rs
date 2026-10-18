//! Directed graph representation with forward and reverse edge lists.

use serde::{Deserialize, Serialize};

/// Directed edge with unique identifier, non-negative cost and resource weight.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Edge {
    /// Unique sequential edge identifier.
    pub id: usize,
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
    /// Primary objective traversal cost ($c \ge 0$).
    pub cost: f64,
    /// Edge resource consumption ($w \ge 0$).
    pub weight: f64,
    /// Unique identifier of the underlying directed edge.
    pub edge_id: usize,
}

/// Directed graph supporting forward and reverse adjacency lookups and edge indexing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectedGraph {
    node_count: usize,
    forward_adj: Vec<Vec<HalfEdge>>,
    reverse_adj: Vec<Vec<HalfEdge>>,
    edges: Vec<Edge>,
}

impl DirectedGraph {
    /// Creates a new directed graph with the specified number of vertices.
    pub fn new(node_count: usize) -> Self {
        Self {
            node_count,
            forward_adj: vec![Vec::new(); node_count],
            reverse_adj: vec![Vec::new(); node_count],
            edges: Vec::new(),
        }
    }

    /// Returns the number of vertices in the graph.
    pub fn num_nodes(&self) -> usize {
        self.node_count
    }

    /// Returns the number of directed edges in the graph.
    pub fn num_edges(&self) -> usize {
        self.edges.len()
    }

    /// Returns all registered edges in the graph.
    pub fn edges(&self) -> &[Edge] {
        &self.edges
    }

    /// Retrieves an edge by its unique index.
    pub fn get_edge(&self, edge_id: usize) -> Option<&Edge> {
        self.edges.get(edge_id)
    }

    /// Adds a directed edge from `from` to `to` with non-negative cost and weight.
    ///
    /// Returns `true` if the edge was added, or `false` if vertex indices are out of bounds
    /// or if cost/weight is negative or non-finite.
    #[must_use = "returns false if edge is invalid (negative, non-finite, or out of bounds)"]
    pub fn add_edge(&mut self, from: usize, to: usize, cost: f64, weight: f64) -> bool {
        if from >= self.node_count || to >= self.node_count {
            return false;
        }
        if cost < 0.0 || !cost.is_finite() || weight < 0.0 || !weight.is_finite() {
            return false;
        }

        let edge_id = self.edges.len();
        self.edges.push(Edge {
            id: edge_id,
            from,
            to,
            cost,
            weight,
        });

        self.forward_adj[from].push(HalfEdge {
            target: to,
            cost,
            weight,
            edge_id,
        });
        self.reverse_adj[to].push(HalfEdge {
            target: from,
            cost,
            weight,
            edge_id,
        });
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
