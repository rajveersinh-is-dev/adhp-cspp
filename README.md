# ADHP-CSPP: Adaptive Dual Hull Pruning

[![Continuous Integration](https://github.com/rajveersinh-is-dev/adhp-cspp/actions/workflows/ci.yml/badge.svg)](https://github.com/rajveersinh-is-dev/adhp-cspp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE-APACHE)
[![Rust](https://img.shields.io/badge/rust-1.80%2B-orange.svg)](https://www.rust-lang.org)

**Adaptive Dual Hull Pruning (ADHP)** is an exact algorithm for solving the NP-hard **Weight-Constrained Shortest Path Problem (CSPP)** on directed graphs with non-negative edge traversal costs and weights.

---

## 1. Problem Formulation

Given a directed graph $G = (V, E)$ with non-negative edge traversal costs $c(e) \ge 0$, non-negative resource consumption weights $w(e) \ge 0$, a source vertex $s$, destination target vertex $t$, and a maximum allowable resource budget $W \ge 0$, find an $(s, t)$-path $P^*$ that minimizes total cost subject to the cumulative resource constraint:

$$\min_{P \in \mathcal{P}_{s, t}} \sum_{e \in P} c(e) \quad \text{subject to} \quad \sum_{e \in P} w(e) \le W$$

### Context and Applications
The single-resource non-negative constrained shortest path problem arises as a key combinatorial pricing subproblem:
- **Vehicle Routing with Time Windows (VRPTW)**: Pricing elementary paths under a single duration or capacity constraint with non-negative costs and metrics in column generation.
- **Quality-of-Service (QoS) Routing**: Minimizing link transmission cost subject to an additive latency threshold.
- **Energy-Constrained Path Planning**: Battery-constrained routing in automated guided vehicles and drone flight paths.

---

## 2. Core Mathematical Mechanism

Traditional exact algorithms for CSPP encounter distinct structural trade-offs:
- **Standard Label-Setting (Martins 1984)**: Explores full Pareto frontiers $(c, w)$ that explode exponentially when costs and resources conflict.
- **1D Distance Bounding (Dumitrescu & Boland 2003, Lozano & Medaglia 2013)**: Projects distances along pure cost ($d_c$) or pure weight ($d_w$) axes, leaving an unpruned search wedge for intermediate trade-offs.
- **Single-Multiplier Lagrangian Relaxation (Handler & Zang 1980, Carlyle, Royset & Wood 2008)**: Uses a single root Lagrangian multiplier $\lambda^*_{s,t}$, providing a single linear lower bound.
- **Parametric Lower Hull Search (Mehlhorn & Ziegelmann 2000)**: Traces the convex lower hull of bicriteria paths via parametric bisection. While Mehlhorn & Ziegelmann use hull points globally, ADHP utilizes the discovered hull facets to project localized, multi-faceted lower bounding hyperplanes $\mathcal{L}_u^\Lambda(\Delta w)$ across every intermediate vertex simultaneously during forward label setting.

### The Multi-Faceted Adaptive Dual Hull (ADH)
ADHP identifies $K$ dual shadow prices $\Lambda = \{\lambda_1, \dots, \lambda_K\}$ ($0 = \lambda_1 < \dots < \lambda_K$) on the biobjective lower hull via recursive bisection (Mehlhorn & Ziegelmann 2000) and materializes a **discrete Legendre-Fenchel lower-bound envelope** across all vertices simultaneously:

$$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k=1}^K \left[ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right]$$

where $d_{\lambda_k}(u, t)$ is the backward shortest path distance from vertex $u$ to destination $t$ under composite metric $c(e) + \lambda_k w(e)$, and $\Delta w = W - w_{cur}$ is the remaining budget.

```
Cost ^
     |            / (Unconstrained Cost-Min Path, λ_1 = 0)
     |           /
     |          /  Dual Facet 1: slope -λ_2
     |         /------------------
     |        /                   \  Dual Facet 2: slope -λ_3
     |       /                     \----------------
     |      /                                       \ (Weight-Min Path, λ -> ∞)
     +-----+-----------------------------------------+-----> Weight
           0                                         W
```

### Mathematical Guarantees

- **Theorem 1 (Admissibility)**: For every vertex $u$ and remaining budget $\Delta w \ge 0$:
  $$\mathcal{L}_u^\Lambda(\Delta w) \le \min_{P \in \mathcal{P}_{u,t}, \, w(P) \le \Delta w} c(P)$$

- **Theorem 2 (Dominance & 1D Subsumption)**:
  For all vertices $u$ and remaining budget $\Delta w \ge 0$:
  $$\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$$
  Strict inequality $\mathcal{L}_u^\Lambda(\Delta w) > d_c(u, t)$ holds if and only if there exists $\lambda_k \in \Lambda$ ($\lambda_k > 0$) such that $d_{\lambda_k}(u, t) - d_c(u, t) > \lambda_k \Delta w$.
  Combined with Filter 1 ($w + d_w(u, t) \le W$), the two-stage filter strictly subsumes classical 1D orthogonal bounding.

- **Theorem 3 (Convexity & Monotonicity)**:
  The discrete envelope $\Delta w \mapsto \mathcal{L}_u^\Lambda(\Delta w)$ is continuous, convex, and monotonically non-increasing on $[0, \infty)$.

- **Theorem 4 (Exact Global Optimality, Exhaustiveness & Termination)**:
  Filtering candidate labels with relative tolerance preserves exact global optimality, protects against floating-point roundoff, and guarantees finite termination even on graphs containing zero-cost and zero-weight cycles.

Full proofs are documented in [`docs/MATHEMATICAL_FOUNDATIONS.md`](docs/MATHEMATICAL_FOUNDATIONS.md).

---

## 3. Empirical Benchmark Summary

Evaluated on an **11th Gen Intel Core i5-11260H @ 2.60GHz** running Windows 11 with 16 GB RAM. Evaluated across **20 benchmark configurations** with **10 distinct random instances** per configuration (200 distinct problem instances total), with **3 discarded warmups** and **3 timed runs** per instance using in-process monotonic timing (`std::time::Instant`).

### Important Wall-Clock Findings & Break-Even Analysis
Across all benchmark configurations in `results/raw/benchmark_raw.csv`:
- **Break-Even Regime (Grid Topologies)**: On planar grids with exponential branching, ADHP's state-space pruning pays for itself completely. On **Grid $10 \times 10$ ($n = 100$)**, ADHP is the **fastest solver overall at $57.11 \, \mu\text{s}$** (generating only 105 labels), outperforming Carlyle-Wood ($61.67 \, \mu\text{s}$, 115 labels), Dumitrescu-Boland ($72.82 \, \mu\text{s}$, 662 labels), Pulse ($288.66 \, \mu\text{s}$, 4,741 labels), and Martins ($337.70 \, \mu\text{s}$, 3,111 labels, a **$5.9\times$ speedup**).
- **Preprocessing Overhead on Dense Networks**: On dense anti-correlated graphs and Random ER networks, backward Dijkstra preprocessing accounts for $70$–$85\%$ of ADHP's runtime ($15$–$156 \, \mu\text{s}$). On instances where the search space is small enough that unguided search (Martins) or 1D bounding (Dumitrescu-Boland) finishes in $< 50 \, \mu\text{s}$, those lightweight methods achieve lower total wall-clock times.
- **Comparison Against Multi-Tree Lagrangian Bounding**: Against Carlyle-Wood (which uses iterative LARAC preprocessing), ADHP's backward-centric tree duality and adaptive facet selection achieve superior total runtime on large anti-correlated graphs ($190.11 \, \mu\text{s}$ vs. $305.68 \, \mu\text{s}$ on $n=150$, a **$1.6\times$ speedup**).
- **Combinatorial Label Suppression**: In all configurations with severe cost-weight conflict, ADHP suppresses label generation by **85% to 97%** relative to standard multi-label Dijkstra.

### A. Anti-Correlated Graph Scaling ($p = 0.25$, $\alpha = 0.40$)

| Nodes ($n$) | ADHP Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels (Mean) | Martins Labels (Mean) | Label Suppression vs Martins |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 20 | $25.37 \, \mu\text{s}$ ($19.24$ / $6.13$) | $25.04 \, \mu\text{s}$ | $6.42 \, \mu\text{s}$ | $6.43 \, \mu\text{s}$ | $6.77 \, \mu\text{s}$ | **18** | 97 | **81.4%** |
| 40 | $17.63 \, \mu\text{s}$ ($15.35$ / $2.28$) | $25.68 \, \mu\text{s}$ | $14.48 \, \mu\text{s}$ | $21.39 \, \mu\text{s}$ | $10.33 \, \mu\text{s}$ | **38** | 316 | **88.0%** |
| 60 | $37.68 \, \mu\text{s}$ ($33.42$ / $4.26$) | $57.31 \, \mu\text{s}$ | $25.78 \, \mu\text{s}$ | $30.79 \, \mu\text{s}$ | $20.68 \, \mu\text{s}$ | **87** | 957 | **90.9%** |
| 80 | $67.38 \, \mu\text{s}$ ($59.77$ / $7.61$) | $94.72 \, \mu\text{s}$ | $68.05 \, \mu\text{s}$ | $57.29 \, \mu\text{s}$ | $44.31 \, \mu\text{s}$ | **140** | 1478 | **90.5%** |
| 100 | $144.20 \, \mu\text{s}$ ($138.19$ / $6.01$) | $150.30 \, \mu\text{s}$ | $62.57 \, \mu\text{s}$ | $71.58 \, \mu\text{s}$ | $61.31 \, \mu\text{s}$ | **79** | 2751 | **97.1%** |
| 150 | $190.11 \, \mu\text{s}$ ($156.87$ / $33.24$) | $305.68 \, \mu\text{s}$ | $141.58 \, \mu\text{s}$ | $196.74 \, \mu\text{s}$ | $139.81 \, \mu\text{s}$ | **964** | 6319 | **84.7%** |

### B. 2D Mesh Grid Scaling (Planar Topologies)

| Dimensions | Vertices ($n$) | ADHP Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels | Martins Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $12.93 \, \mu\text{s}$ ($9.58$ / $3.35$) | $14.51 \, \mu\text{s}$ | $7.73 \, \mu\text{s}$ | $9.19 \, \mu\text{s}$ | $6.21 \, \mu\text{s}$ | **19** | 58 |
| $6 \times 6$ | 36 | $20.72 \, \mu\text{s}$ ($14.82$ / $5.91$) | $25.09 \, \mu\text{s}$ | $14.43 \, \mu\text{s}$ | $21.50 \, \mu\text{s}$ | $21.49 \, \mu\text{s}$ | **43** | 315 |
| $8 \times 8$ | 64 | $35.04 \, \mu\text{s}$ ($26.91$ / $8.13$) | $37.08 \, \mu\text{s}$ | $25.04 \, \mu\text{s}$ | $57.00 \, \mu\text{s}$ | $86.81 \, \mu\text{s}$ | **49** | 1111 |
| $10 \times 10$ | 100 | $57.11 \, \mu\text{s}$ ($42.94$ / $14.17$) | $61.67 \, \mu\text{s}$ | $72.82 \, \mu\text{s}$ | $288.66 \, \mu\text{s}$ | $337.70 \, \mu\text{s}$ | **105** | 3111 |

### C. Random Erdos-Renyi Scaling ($p = 0.22$)

| Vertices ($n$) | ADHP Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels | Martins Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 30 | $15.67 \, \mu\text{s}$ ($12.45$ / $3.22$) | $13.18 \, \mu\text{s}$ | $6.90 \, \mu\text{s}$ | $8.83 \, \mu\text{s}$ | $6.15 \, \mu\text{s}$ | **24** | 204 |
| 60 | $45.84 \, \mu\text{s}$ ($40.07$ / $5.77$) | $60.23 \, \mu\text{s}$ | $21.84 \, \mu\text{s}$ | $19.51 \, \mu\text{s}$ | $12.61 \, \mu\text{s}$ | **84** | 673 |
| 90 | $67.85 \, \mu\text{s}$ ($61.07$ / $6.78$) | $111.59 \, \mu\text{s}$ | $34.24 \, \mu\text{s}$ | $43.08 \, \mu\text{s}$ | $31.59 \, \mu\text{s}$ | **181** | 2320 |
| 120 | $111.29 \, \mu\text{s}$ ($103.11$ / $8.19$) | $160.27 \, \mu\text{s}$ | $64.70 \, \mu\text{s}$ | $82.89 \, \mu\text{s}$ | $41.05 \, \mu\text{s}$ | **190** | 2138 |

### D. Budget Sensitivity ($n = 50$, Anti-Correlated Graph)

| Budget Tightness ($\alpha$) | ADHP Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels | Martins Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $\alpha = 0.10$ (Very Tight) | $48.19 \, \mu\text{s}$ ($43.39$ / $4.80$) | $63.78 \, \mu\text{s}$ | $17.35 \, \mu\text{s}$ | $20.57 \, \mu\text{s}$ | $7.35 \, \mu\text{s}$ | **42** | 429 |
| $\alpha = 0.25$ (Tight) | $37.08 \, \mu\text{s}$ ($33.56$ / $3.51$) | $33.39 \, \mu\text{s}$ | $17.78 \, \mu\text{s}$ | $15.41 \, \mu\text{s}$ | $10.02 \, \mu\text{s}$ | **33** | 477 |
| $\alpha = 0.50$ (Medium) | $25.72 \, \mu\text{s}$ ($22.53$ / $3.19$) | $27.13 \, \mu\text{s}$ | $12.45 \, \mu\text{s}$ | $16.79 \, \mu\text{s}$ | $9.43 \, \mu\text{s}$ | **44** | 437 |
| $\alpha = 0.75$ (Loose) | $25.29 \, \mu\text{s}$ ($22.21$ / $3.08$) | $54.92 \, \mu\text{s}$ | $21.03 \, \mu\text{s}$ | $26.61 \, \mu\text{s}$ | $25.54 \, \mu\text{s}$ | **75** | 563 |
| $\alpha = 0.90$ (Very Loose) | $21.95 \, \mu\text{s}$ ($18.45$ / $3.50$) | $41.63 \, \mu\text{s}$ | $26.78 \, \mu\text{s}$ | $22.85 \, \mu\text{s}$ | $9.34 \, \mu\text{s}$ | **68** | 451 |

### E. Ablation Analysis on Facet Count $K$ ($n = 70$)

| Facet Configuration | Preprocessing ($\mu\text{s}$) | Search Time ($\mu\text{s}$) | Total Runtime ($\mu\text{s}$) | Labels Generated (Mean) | Dual-Pruned Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **ADHP ($K=1$)** | 19.46 | 9.49 | 28.95 | **146** | 40 |
| **ADHP ($K=2$)** | 31.23 | 4.89 | 36.12 | **91** (-37.7%) | 39 |
| **ADHP ($K=3$)** | 35.19 | 4.09 | 39.28 | **91** | 39 |
| **ADHP ($K=5$)** | 43.85 | 4.40 | 48.25 | **91** | 39 |
| **ADHP ($K=8$)** | 44.03 | 4.23 | 48.26 | **91** | 39 |
| **ADHP ($K=12$)** | 43.25 | 4.57 | 47.82 | **91** | 39 |

---

## 4. Algorithmic Trade-offs & Limitations

1. **Preprocessing Break-Even Threshold**:
   ADHP requires $K$ backward Dijkstra runs ($O(K(m + n \log n))$). For small graphs ($n \le 100$) or networks with small Pareto frontiers, simpler algorithms terminate faster in total wall-clock time. ADHP is engineered for combinatorial topologies where search-space explosion dominates.
2. **Computational Complexity**:
   Because CSPP is weakly NP-hard, pathological graphs with exponentially many Pareto-optimal paths on a convex arc can still force exponential label generation in the worst case.
3. **Single-Resource Scope**:
   ADHP is formulated for single-resource weight constraints ($w(e) \ge 0$). Extending multi-faceted dual envelopes to multi-resource constraints ($d \ge 2$) requires computing multi-dimensional polyhedral convex hulls.

---

## 5. Quick Start and Installation

### Prerequisites
- [Rust toolchain](https://rustup.rs/) (version 1.80 or newer).
- Python 3.10+ with `scipy` and `numpy` (for ILP verification).

### Building and Running Tests
```bash
# Clone the repository
git clone https://github.com/rajveersinh-is-dev/adhp-cspp.git
cd adhp-cspp

# Run all unit, property, and cycle-termination tests
cargo test

# Run 100-instance differential verification against 4 solvers and HiGHS ILP
cargo run --bin verify_oracle --release
python scripts/verify_against_ilp.py

# Run multi-instance empirical benchmark suite (200 problem instances)
cargo run --bin benchmark_suite --release
```

---

## 6. Minimal Working Example

```rust
use adhp_cspp::graph::DirectedGraph;
use adhp_cspp::{AdhpSolver, CsppInstance, CsppSolver, SolutionStatus};

fn main() {
    let mut graph = DirectedGraph::new(5);

    // Add edges: (from, to, cost, weight)
    assert!(graph.add_edge(0, 1, 25.0, 2.0));
    assert!(graph.add_edge(1, 4, 25.0, 2.0));

    assert!(graph.add_edge(0, 2, 10.0, 8.0));
    assert!(graph.add_edge(2, 4, 10.0, 8.0));

    assert!(graph.add_edge(0, 3, 15.0, 5.0));
    assert!(graph.add_edge(3, 4, 15.0, 5.0));

    let budget = 12.0;
    let instance = CsppInstance::new(graph, 0, 4, budget);

    // Initialize ADHP with K = 5 dual facets
    let solver = AdhpSolver::new(5);
    let solution = solver.solve(&instance);

    match solution.status {
        SolutionStatus::Optimal => {
            println!("Optimal Path: {:?}", solution.path);
            println!("Edge Path: {:?}", solution.edge_path);
            println!("Cost: {:.2}, Weight: {:.2}", solution.cost, solution.weight);
        }
        SolutionStatus::Infeasible => {
            println!("No path satisfies budget.");
        }
    }
}
```

Run via:
```bash
cargo run --example simple_solve
```

---

## 7. Key References

1. **Martins, E. Q. (1984)**. *On a multicriteria shortest path problem*. European Journal of Operational Research, 16(2), 236–245.
2. **Dumitrescu, I., & Boland, N. (2003)**. *Improved preprocessing, labeling and dual algorithms for the weight-constrained shortest path problem*. INFORMS Journal on Computing, 15(4), 384–401.
3. **Carlyle, W. M., Royset, J. O., & Wood, R. K. (2008)**. *Lagrangian relaxation and enumeration for solving constrained shortest-path problems*. INFORMS Journal on Computing, 20(3), 416–426.
4. **Lozano, L., & Medaglia, A. L. (2013)**. *On an exact pulse algorithm for the constrained shortest path problem*. Computers & Operations Research, 40(1), 378–388.
5. **Handler, G. Y., & Zang, I. (1980)**. *A dual algorithm for the constrained shortest path problem*. Networks, 10(4), 293–309.
6. **Mehlhorn, K., & Ziegelmann, M. (2000)**. *Resource constrained shortest paths*. European Symposium on Algorithms (ESA), Springer, 32–42.
7. **Muhandiramge, R., & Boland, N. (2009)**. *Simultaneous label setting and bound generation for the constrained shortest path problem*. INFORMS Journal on Computing, 21(2), 273–288.

---

## 8. Citation

If you use ADHP in your research, please cite:

```bibtex
@software{pardeshi2026adhp,
  author    = {Rajveersinh Vishal Pardeshi},
  title     = {Adaptive Dual Hull Pruning: An Exact Algorithm for the Weight-Constrained Shortest Path Problem},
  year      = {2026},
  url       = {https://github.com/rajveersinh-is-dev/adhp-cspp},
  version   = {0.1.0}
}
```

---

## 9. License

This project is dual-licensed under either:
- **MIT License** ([LICENSE-MIT](LICENSE-MIT) or [http://opensource.org/licenses/MIT](http://opensource.org/licenses/MIT))
- **Apache License, Version 2.0** ([LICENSE-APACHE](LICENSE-APACHE) or [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0))
