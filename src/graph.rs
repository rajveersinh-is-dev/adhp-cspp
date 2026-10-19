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

    /// Validates internal structural and metric invariants of the graph.
    ///
    /// Guarantees that:
    /// - Adjacency lists match `node_count`.
    /// - All edge endpoints are in bounds.
    /// - All edge costs and weights are non-negative and finite.
    /// - HalfEdge indices and weights match their corresponding Edge records.
    pub fn validate(&self) -> Result<(), &'static str> {
        if self.forward_adj.len() != self.node_count || self.reverse_adj.len() != self.node_count {
            return Err("Adjacency list length does not match node_count");
        }
        for (i, edge) in self.edges.iter().enumerate() {
            if edge.id != i {
                return Err("Edge id mismatch with position");
            }
            if edge.from >= self.node_count || edge.to >= self.node_count {
                return Err("Edge endpoint out of bounds");
            }
            if edge.cost < 0.0
                || !edge.cost.is_finite()
                || edge.weight < 0.0
                || !edge.weight.is_finite()
            {
                return Err("Edge cost or weight is negative or non-finite");
            }
        }
        for (u, adj) in self.forward_adj.iter().enumerate() {
            for he in adj {
                if he.target >= self.node_count {
                    return Err("Forward half-edge target out of bounds");
                }
                let edge = match self.edges.get(he.edge_id) {
                    Some(e) => e,
                    None => return Err("Forward half-edge references invalid edge_id"),
                };
                if edge.from != u || edge.to != he.target {
                    return Err("Forward half-edge does not match underlying edge endpoints");
                }
                if edge.cost != he.cost || edge.weight != he.weight {
                    return Err("Forward half-edge metrics do not match underlying edge");
                }
            }
        }
        for (v, adj) in self.reverse_adj.iter().enumerate() {
            for he in adj {
                if he.target >= self.node_count {
                    return Err("Reverse half-edge target out of bounds");
                }
                let edge = match self.edges.get(he.edge_id) {
                    Some(e) => e,
                    None => return Err("Reverse half-edge references invalid edge_id"),
                };
                if edge.to != v || edge.from != he.target {
                    return Err("Reverse half-edge does not match underlying edge endpoints");
                }
                if edge.cost != he.cost || edge.weight != he.weight {
                    return Err("Reverse half-edge metrics do not match underlying edge");
                }
            }
        }
        Ok(())
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
