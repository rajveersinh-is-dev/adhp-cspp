//! Minimal working example demonstrating ADHP on a small constrained routing network.

use adhp_cspp::graph::DirectedGraph;
use adhp_cspp::{AdhpSolver, CsppInstance, CsppSolver, SolutionStatus};

fn main() {
    println!("=== ADHP-CSPP: Minimal Working Example ===");

    // Construct a directed graph with 5 vertices
    // Node 0: Source, Node 4: Target
    let mut graph = DirectedGraph::new(5);

    // Path 1 (Fast but expensive): 0 -> 1 -> 4
    // Cost: 25 + 25 = 50, Weight: 2 + 2 = 4
    graph.add_edge(0, 1, 25.0, 2.0);
    graph.add_edge(1, 4, 25.0, 2.0);

    // Path 2 (Cheap but slow): 0 -> 2 -> 4
    // Cost: 10 + 10 = 20, Weight: 8 + 8 = 16
    graph.add_edge(0, 2, 10.0, 8.0);
    graph.add_edge(2, 4, 10.0, 8.0);

    // Path 3 (Balanced trade-off): 0 -> 3 -> 4
    // Cost: 15 + 15 = 30, Weight: 5 + 5 = 10
    graph.add_edge(0, 3, 15.0, 5.0);
    graph.add_edge(3, 4, 15.0, 5.0);

    let budget = 12.0;
    println!(
        "Graph has {} vertices, {} edges. Budget W = {:.1}",
        graph.num_nodes(),
        graph.num_edges(),
        budget
    );

    let instance = CsppInstance::new(graph, 0, 4, budget);

    // Initialize ADHP with K = 5 dual facets
    let solver = AdhpSolver::new(5);
    let solution = solver.solve(&instance);

    match solution.status {
        SolutionStatus::Optimal => {
            println!("\nOptimal constrained path discovered!");
            println!("  Path: {:?}", solution.path);
            println!("  Total Cost:   {:.2}", solution.cost);
            println!(
                "  Total Weight: {:.2} (Budget: {:.2})",
                solution.weight, budget
            );
            println!("  Labels generated: {}", solution.stats.labels_generated);
            println!(
                "  Labels pruned by dual hull: {}",
                solution.stats.labels_pruned_dual_bound
            );
        }
        SolutionStatus::Infeasible => {
            println!("\nCertified: No path satisfies the resource budget.");
        }
    }
}
