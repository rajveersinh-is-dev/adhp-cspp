# ADHP-CSPP: Adaptive Dual Hull Pruning

[![Continuous Integration](https://github.com/rajveersinh-is-dev/adhp-cspp/actions/workflows/ci.yml/badge.svg)](https://github.com/rajveersinh-is-dev/adhp-cspp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE-APACHE)
[![Rust](https://img.shields.io/badge/rust-1.80%2B-orange.svg)](https://www.rust-lang.org)

**Adaptive Dual Hull Pruning (ADHP)** is an exact, high-performance algorithm for solving the NP-hard **Weight-Constrained Shortest Path Problem (CSPP)** on directed graphs.

---

## 1. What Problem Does This Solve?

Given a directed graph $G = (V, E)$ with non-negative edge traversal costs $c(e) \ge 0$, non-negative resource consumption weights $w(e) \ge 0$, a source vertex $s$, destination target vertex $t$, and a maximum allowable resource budget $W \ge 0$, find an $(s, t)$-path $P^*$ that minimizes total cost subject to the cumulative resource constraint:

$$\min_{P \in \mathcal{P}_{s, t}} \sum_{e \in P} c(e) \quad \text{subject to} \quad \sum_{e \in P} w(e) \le W$$

### Context and Applications
The single-resource non-negative constrained shortest path problem is the foundational combinatorial pricing subproblem in decomposition and routing frameworks:
- **Vehicle Routing with Resource Windows (VRPTW)** (pricing elementary paths under duration or capacity constraints)
- **Quality-of-Service (QoS) Delay-Constrained Routing** in telecommunication networks (minimizing transmission cost subject to latency ceilings)
- **Energy-Constrained Path Planning** in autonomous robotics and electric fleet logistics

---

## 2. Core Mathematical Mechanism

Traditional exact algorithms for CSPP encounter distinct structural bottlenecks:
- **Standard Label-Setting (Martins 1984)**: Explores full Pareto frontiers $(c, w)$ that explode exponentially when costs and resources conflict.
- **1D Distance Bounding (Dumitrescu & Boland 2003, Lozano & Medaglia 2013)**: Projects distances along pure cost ($d_c$) or pure weight ($d_w$) axes, leaving a massive unpruned search wedge for intermediate trade-offs.
- **Single-Multiplier Lagrangian Relaxation (Handler & Zang 1980, Carlyle, Royset & Wood 2008)**: Uses a single root Lagrangian multiplier $\lambda^*_{s,t}$, providing a single linear lower bound that does not capture localized multi-faceted trade-offs across intermediate vertices.

### The Multi-Faceted Adaptive Dual Hull (ADH)
ADHP constructs an adaptive set of $K$ dual shadow prices $\Lambda = \{\lambda_1, \dots, \lambda_K\}$ ($0 = \lambda_1 < \dots < \lambda_K$) on the biobjective lower hull and materializes a **discrete Legendre-Fenchel lower-bound envelope** across all vertices simultaneously:

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
  Combined with Filter 1 ($w + d_w(u, t) \le W$, representing the $\lambda \to \infty$ boundary), the two-stage ADHP filter strictly subsumes classical 1D orthogonal bounding.

- **Theorem 3 (Convexity & Monotonicity)**:
  The discrete envelope $\Delta w \mapsto \mathcal{L}_u^\Lambda(\Delta w)$ is continuous, convex, and monotonically non-increasing on $[0, \infty)$.

- **Theorem 4 (Exact Global Optimality & Finite Termination)**:
  Filtering any candidate label satisfying $c(P) + \mathcal{L}_u^\Lambda(W - w(P)) > C_{\text{UB}} + \epsilon_{\text{prune}}$ with $\epsilon_{\text{prune}} = 10^{-9}$ preserves exact global optimality, protects against floating-point roundoff, and guarantees finite termination even on graphs containing zero-cost and zero-weight cycles.

Full proofs are documented in [`docs/MATHEMATICAL_FOUNDATIONS.md`](docs/MATHEMATICAL_FOUNDATIONS.md).

---

## 3. Empirical Benchmark Summary

Evaluated on an **11th Gen Intel Core i5-11260H @ 2.60GHz** running Windows 11 with 16 GB RAM. Each configuration was evaluated across **10 distinct random instances** with **3 discarded warmups** and **3 timed runs** per instance using in-process hardware counters (`std::time::Instant`).

### A. Anti-Correlated Graph Scaling ($p = 0.25$, $\alpha = 0.40$, 10 Instances/Size)

| Nodes ($n$) | ADHP ($K=5$) Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels (Mean/Med) | Martins Labels (Mean/Med) | Label Suppression vs Martins |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 20 | $9.82 \, \mu\text{s}$ ($8.80$ / $1.02$) | $6.45 \, \mu\text{s}$ | $3.12 \, \mu\text{s}$ | $3.55 \, \mu\text{s}$ | $3.20 \, \mu\text{s}$ | **12** / **10** | 68 / 65 | **82.4%** |
| 40 | $21.63 \, \mu\text{s}$ ($20.23$ / $1.40$) | $14.64 \, \mu\text{s}$ | $8.75 \, \mu\text{s}$ | $7.47 \, \mu\text{s}$ | $6.80 \, \mu\text{s}$ | **29** / **34** | 317 / 333 | **90.9%** |
| 60 | $58.02 \, \mu\text{s}$ ($55.52$ / $2.50$) | $30.39 \, \mu\text{s}$ | $13.68 \, \mu\text{s}$ | $13.69 \, \mu\text{s}$ | $10.50 \, \mu\text{s}$ | **59** / **47** | 959 / 1,067 | **93.8%** |
| 80 | $87.37 \, \mu\text{s}$ ($83.71$ / $3.66$) | $57.00 \, \mu\text{s}$ | $20.83 \, \mu\text{s}$ | $22.70 \, \mu\text{s}$ | $18.73 \, \mu\text{s}$ | **76** / **64** | 1,480 / 1,434 | **94.9%** |
| 100 | $125.89 \, \mu\text{s}$ ($122.35$ / $3.54$) | $69.96 \, \mu\text{s}$ | $31.99 \, \mu\text{s}$ | $31.94 \, \mu\text{s}$ | $29.70 \, \mu\text{s}$ | **64** / **58** | 2,292 / 1,784 | **97.2%** |
| 150 | $239.06 \, \mu\text{s}$ ($234.32$ / **4.74**) | $149.04 \, \mu\text{s}$ | $78.19 \, \mu\text{s}$ | $92.47 \, \mu\text{s}$ | $84.90 \, \mu\text{s}$ | **98** / **110** | 6,445 / 6,185 | **98.5%** |

*Note on Anti-Correlated Graphs*:
ADHP achieves the strongest candidate label suppression of all evaluated solvers (generating only 98 labels at $n=150$ vs 6,445 for Martins and 10,576 for Pulse). Its forward search phase is the fastest (**4.74 µs**, an **17.9x search speedup** over Martins). However, because computing $K=5$ reverse trees requires $O(K(m + n \log n))$ time, total wall-clock time on graphs of this scale is dominated by preprocessing, making lightweight 1D-bounded solvers (Dumitrescu-Boland) faster overall.

---

### B. 2D Mesh Grid Scaling (Planar Bottleneck Topologies, 10 Instances/Dimension)

| Dimensions | Vertices ($n$) | ADHP ($K=5$) Total (Prep / Search) | Carlyle-Wood Total | Dumitrescu-Boland Total | Pulse Total | Martins Total | ADHP Labels (Mean/Med) | Martins Labels (Mean/Med) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $9.72 \, \mu\text{s}$ ($7.43$ / $2.29$) | $6.35 \, \mu\text{s}$ | $4.64 \, \mu\text{s}$ | $4.76 \, \mu\text{s}$ | $4.52 \, \mu\text{s}$ | **16** / **13** | 58 / 61 |
| $6 \times 6$ | 36 | $14.34 \, \mu\text{s}$ ($11.48$ / $2.86$) | $10.50 \, \mu\text{s}$ | $5.42 \, \mu\text{s}$ | $7.10 \, \mu\text{s}$ | $9.23 \, \mu\text{s}$ | **35** / **35** | 315 / 330 |
| $8 \times 8$ | 64 | $26.46 \, \mu\text{s}$ ($22.06$ / $4.40$) | $15.60 \, \mu\text{s}$ | $10.95 \, \mu\text{s}$ | $22.61 \, \mu\text{s}$ | $36.54 \, \mu\text{s}$ | **44** / **40** | 1,111 / 1,139 |
| $10 \times 10$ | 100 | **$46.88 \, \mu\text{s}$** ($37.84$ / $9.04$) | $26.93 \, \mu\text{s}$ | $35.12 \, \mu\text{s}$ | $160.67 \, \mu\text{s}$ | $166.14 \, \mu\text{s}$ | **92** / **92** | 3,111 / 3,063 |

*Grid Performance Findings*:
- On the $10 \times 10$ mesh grid, unconstrained Pareto expansion causes Martins to generate **3,111 labels** ($166.14 \, \mu\text{s}$) and Pulse to generate **4,741 labels** ($160.67 \, \mu\text{s}$).
- ADHP constrains search to **92 labels**, running in **$46.88 \, \mu\text{s}$** (**3.54x faster than Martins**, **3.42x faster than Pulse**).
- Carlyle-Wood ($26.93 \, \mu\text{s}$) and Dumitrescu-Boland ($35.12 \, \mu\text{s}$) remain faster in total time due to computing fewer reverse trees during preprocessing.

---

### C. Ablation Analysis on Dual Facet Count $K$ ($n = 70$, Anti-Correlated Graph)

| Facet Count $K$ | Preprocessing ($\mu\text{s}$) | Search Time ($\mu\text{s}$) | Total Runtime ($\mu\text{s}$) | Labels Generated (Mean / Med) | Dual-Pruned Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **$K = 1$** (1D Cost Bound) | **23.29** | **7.55** | **30.84** | **148** / **175** | 40 |
| **$K = 2$** (First Dual Slope) | 34.98 | 2.02 | 37.00 | **48** / **42** (-67.6%) | 24 |
| **$K = 3$** (Two Active Slopes) | 42.94 | 1.69 | 44.63 | **45** / **42** | 22 |
| **$K = 5$** (Adaptive Dual Hull) | 61.41 | 1.70 | 63.11 | **40** / **39** | 21 |
| **$K = 8$** (Fine Discretization) | 81.25 | 1.68 | 82.93 | **40** / **39** | 21 |
| **$K = 12$** (Over-Discretized) | 85.84 | 2.00 | 87.83 | **40** / **39** | 21 |

*Ablation Insights*:
Adding the first Lagrangian multiplier slope ($K=2$) produces the primary algorithmic leap, **reducing label generation from 148 to 48 (a 67.6% drop)**. Beyond $K=5$, label pruning saturates while preprocessing cost grows linearly.

Full methodology and raw CSV/JSON records: [`research/BENCHMARK_REPORT.md`](research/BENCHMARK_REPORT.md) and [`research/BENCHMARK_METHODOLOGY.md`](research/BENCHMARK_METHODOLOGY.md).

---

## 4. Honest Limitations & Algorithmic Trade-offs

1. **Preprocessing Break-Even Threshold**:
   ADHP requires $K$ backward Dijkstra runs ($O(K(m + n \log n))$). For small graphs ($n \le 100$) where search spaces are small, simpler algorithms (Dumitrescu-Boland or Martins) terminate faster in total wall-clock time. ADHP is engineered for regimes where search-space explosion is the primary bottleneck.
2. **Computational Complexity**:
   Because CSPP is weakly NP-hard, pathological graphs with exponentially many Pareto-optimal paths on a convex arc can still force exponential label generation in the worst case. ADHP tightens the practical search space exponent, but does not alter the NP-hardness barrier.
3. **Single-Resource Scope**:
   ADHP is formulated for single-resource weight constraints ($w(e) \ge 0$). Extending multi-faceted dual envelopes to multi-resource constraints ($d \ge 2$) requires computing multi-dimensional polyhedral convex hulls.

---

## 5. Quick Start and Installation

### Prerequisites
- [Rust toolchain](https://rustup.rs/) (version 1.80 or newer).

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

# Run multi-instance empirical benchmark suite
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
    graph.add_edge(0, 1, 25.0, 2.0);
    graph.add_edge(1, 4, 25.0, 2.0);

    graph.add_edge(0, 2, 10.0, 8.0);
    graph.add_edge(2, 4, 10.0, 8.0);

    graph.add_edge(0, 3, 15.0, 5.0);
    graph.add_edge(3, 4, 15.0, 5.0);

    let budget = 12.0;
    let instance = CsppInstance::new(graph, 0, 4, budget);

    // Initialize ADHP with K = 5 dual facets
    let solver = AdhpSolver::new(5);
    let solution = solver.solve(&instance);

    match solution.status {
        SolutionStatus::Optimal => {
            println!("Optimal Path: {:?}", solution.path);
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
6. **Muhandiramge, R., & Boland, N. (2009)**. *Simultaneous label setting and bound generation for the constrained shortest path problem*. INFORMS Journal on Computing, 21(2), 273–288.

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
