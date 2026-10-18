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

Evaluated on an **11th Gen Intel Core i5-11260H @ 2.60GHz** running Windows 11 with 16 GB RAM. Evaluated across **20 benchmark configurations** with **10 distinct random instances** per configuration (200 distinct problem instances total), with **3 discarded warmups** and **3 timed runs** per instance using in-process hardware counters (`std::time::Instant`).

### Important Wall-Clock Findings Across All 19 Benchmark Configurations
Across all 19 benchmark configurations in `results/raw/benchmark_raw.csv`:
- **ADHP is the fastest solver in 0 configurations, is last in 17 configurations, and is 3rd and 4th on the two largest grids ($10\times 10$ and $8\times 8$).**
- **Why**: ADHP computes $K=5$ reverse Dijkstra shortest path trees during preprocessing ($O(K(m + n \log n))$), taking $11$–$234 \, \mu\text{s}$, which accounts for **95–99% of its total execution time**.
- On instances with modest Pareto conflict (Random ER, loose budgets, or small graphs $n \le 100$), simpler solvers (Martins, Dumitrescu-Boland) finish their forward search in $3$–$48 \, \mu\text{s}$ without requiring extensive multi-tree preprocessing.
- ADHP's true strength is **combinatorial label suppression** during forward search (generating up to 98.5% fewer labels than Martins and up to 99.1% fewer than Pulse on $n=150$ anti-correlated graphs).

### A. Anti-Correlated Graph Scaling ($p = 0.25$, $\alpha = 0.40$)

| Nodes ($n$) | ADHP ($K=5$) Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels (Mean) | Martins Labels (Mean) | Label Suppression vs Martins |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 20 | $15.58 \, \mu\text{s}$ ($12.61$ / $2.96$) | $11.13 \, \mu\text{s}$ | $2.59 \, \mu\text{s}$ | $2.63 \, \mu\text{s}$ | $3.56 \, \mu\text{s}$ | **17** | 102 | **83.3%** |
| 40 | $21.63 \, \mu\text{s}$ ($20.23$ / $1.40$) | $14.64 \, \mu\text{s}$ | $8.75 \, \mu\text{s}$ | $7.47 \, \mu\text{s}$ | $6.80 \, \mu\text{s}$ | **29** | 317 | **90.9%** |
| 60 | $58.02 \, \mu\text{s}$ ($55.52$ / $2.50$) | $30.39 \, \mu\text{s}$ | $13.68 \, \mu\text{s}$ | $13.69 \, \mu\text{s}$ | $10.50 \, \mu\text{s}$ | **59** | 959 | **93.8%** |
| 80 | $87.37 \, \mu\text{s}$ ($83.71$ / $3.65$) | $57.00 \, \mu\text{s}$ | $20.83 \, \mu\text{s}$ | $22.70 \, \mu\text{s}$ | $18.73 \, \mu\text{s}$ | **76** | 1,480 | **94.9%** |
| 100 | $125.89 \, \mu\text{s}$ ($122.35$ / $3.54$) | $69.96 \, \mu\text{s}$ | $31.99 \, \mu\text{s}$ | $31.94 \, \mu\text{s}$ | $29.70 \, \mu\text{s}$ | **64** | 2,292 | **97.2%** |
| 150 | $239.06 \, \mu\text{s}$ ($234.32$ / **4.74**) | $149.04 \, \mu\text{s}$ | $78.19 \, \mu\text{s}$ | $92.47 \, \mu\text{s}$ | $84.90 \, \mu\text{s}$ | **98** | 6,445 | **98.5%** |

### B. 2D Mesh Grid Scaling (Planar Topologies)

| Dimensions | Vertices ($n$) | ADHP ($K=5$) Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels | Martins Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $9.72 \, \mu\text{s}$ ($7.43$ / $2.28$) | $6.35 \, \mu\text{s}$ | $4.64 \, \mu\text{s}$ | $4.76 \, \mu\text{s}$ | $4.52 \, \mu\text{s}$ | **16** | 58 |
| $6 \times 6$ | 36 | $14.34 \, \mu\text{s}$ ($11.48$ / $2.86$) | $10.50 \, \mu\text{s}$ | $5.42 \, \mu\text{s}$ | $7.10 \, \mu\text{s}$ | $9.23 \, \mu\text{s}$ | **35** | 315 |
| $8 \times 8$ | 64 | $26.46 \, \mu\text{s}$ ($22.06$ / $4.40$) | $15.60 \, \mu\text{s}$ | $10.95 \, \mu\text{s}$ | $22.61 \, \mu\text{s}$ | $36.54 \, \mu\text{s}$ | **44** | 1,111 |
| $10 \times 10$ | 100 | $46.88 \, \mu\text{s}$ ($37.84$ / $9.04$) | $26.93 \, \mu\text{s}$ | $35.12 \, \mu\text{s}$ | $160.67 \, \mu\text{s}$ | $166.14 \, \mu\text{s}$ | **92** | 3,111 |

### C. Random Erdős–Rényi Scaling ($p = 0.22$)

| Vertices ($n$) | ADHP ($K=5$) Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels | Martins Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 30 | $13.74 \, \mu\text{s}$ ($11.24$ / $2.50$) | $10.83 \, \mu\text{s}$ | $4.78 \, \mu\text{s}$ | $4.53 \, \mu\text{s}$ | $3.80 \, \mu\text{s}$ | **23** | 204 |
| 60 | $52.55 \, \mu\text{s}$ ($49.59$ / $2.97$) | $27.46 \, \mu\text{s}$ | $11.65 \, \mu\text{s}$ | $11.53 \, \mu\text{s}$ | $9.62 \, \mu\text{s}$ | **61** | 673 |
| 90 | $116.04 \, \mu\text{s}$ ($111.52$ / $4.53$) | $61.84 \, \mu\text{s}$ | $23.60 \, \mu\text{s}$ | $26.08 \, \mu\text{s}$ | $26.80 \, \mu\text{s}$ | **91** | 2,320 |
| 120 | $161.69 \, \mu\text{s}$ ($157.86$ / $3.83$) | $102.55 \, \mu\text{s}$ | $48.95 \, \mu\text{s}$ | $56.00 \, \mu\text{s}$ | $37.83 \, \mu\text{s}$ | **99** | 2,138 |

### D. Budget Sensitivity ($n = 50$, Anti-Correlated Graph)

| Budget Tightness ($\alpha$) | ADHP ($K=5$) Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels | Martins Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $\alpha = 0.10$ (Very Tight) | $47.07 \, \mu\text{s}$ ($43.96$ / $3.11$) | $27.12 \, \mu\text{s}$ | $6.53 \, \mu\text{s}$ | $6.17 \, \mu\text{s}$ | $3.57 \, \mu\text{s}$ | **47** | 436 |
| $\alpha = 0.25$ (Tight) | $26.95 \, \mu\text{s}$ ($25.86$ / $1.09$) | $17.49 \, \mu\text{s}$ | $6.26 \, \mu\text{s}$ | $7.69 \, \mu\text{s}$ | $4.46 \, \mu\text{s}$ | **33** | 482 |
| $\alpha = 0.50$ (Medium) | $26.92 \, \mu\text{s}$ ($25.74$ / $1.18$) | $16.48 \, \mu\text{s}$ | $6.71 \, \mu\text{s}$ | $8.14 \, \mu\text{s}$ | $6.85 \, \mu\text{s}$ | **39** | 431 |
| $\alpha = 0.75$ (Loose) | $29.63 \, \mu\text{s}$ ($28.41$ / $1.21$) | $17.82 \, \mu\text{s}$ | $10.75 \, \mu\text{s}$ | $11.78 \, \mu\text{s}$ | $7.69 \, \mu\text{s}$ | **43** | 561 |
| $\alpha = 0.90$ (Very Loose) | $27.29 \, \mu\text{s}$ ($25.95$ / $1.33$) | $15.82 \, \mu\text{s}$ | $7.45 \, \mu\text{s}$ | $13.55 \, \mu\text{s}$ | $6.53 \, \mu\text{s}$ | **48** | 450 |

### E. Ablation Analysis on Facet Count $K$ ($n = 70$)

| Facet Count $K$ | Preprocessing ($\mu\text{s}$) | Search Time ($\mu\text{s}$) | Total Runtime ($\mu\text{s}$) | Labels Generated (Mean) | Dual-Pruned Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **$K = 1$** (1D Cost Bound) | **23.29** | **7.55** | **30.84** | **148** | 40 |
| **$K = 2$** (First Dual Slope) | 34.98 | 2.02 | 37.00 | **48** (-67.6%) | 24 |
| **$K = 3$** (Two Active Slopes) | 42.94 | 1.69 | 44.63 | **45** | 22 |
| **$K = 5$** (Adaptive Dual Hull) | 61.41 | 1.70 | 63.11 | **40** | 21 |
| **$K = 8$** (Fine Discretization) | 81.25 | 1.68 | 82.93 | **40** | 21 |
| **$K = 12$** (Over-Discretized) | 85.84 | 2.00 | 87.83 | **40** | 21 |

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
