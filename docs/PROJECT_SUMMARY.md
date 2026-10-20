# PROJECT SUMMARY & TECHNICAL OVERVIEW
## Adaptive Dual Hull Pruning (ADHP) for the Constrained Shortest Path Problem

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/PROJECT_SUMMARY.md`  

---

### 1. Problem Formulation
The Weight-Constrained Shortest Path Problem (CSPP) is formulated on a directed graph $G = (V, E)$ with non-negative edge costs $c_e \ge 0$, non-negative resource weights $w_e \ge 0$, a designated source $s$, destination $t$, and budget $W \ge 0$:
$$\min_{P \in \mathcal{P}_{s, t}} \sum_{e \in P} c_e \quad \text{subject to} \quad \sum_{e \in P} w_e \le W$$
CSPP is NP-hard in the weak sense and serves as the core subproblem in column generation for Vehicle Routing with Time Windows (VRPTW), airline crew scheduling, and QoS routing.

---

### 2. The Core Mathematical Innovation
Existing exact algorithms either suffer from exponential label explosion (Martins 1984), use loose 1D orthogonal bounds $d_c(u, t), d_w(u, t)$ (Dumitrescu & Boland 2003, Lozano & Medaglia 2013), or rely on a single static Lagrangian multiplier $\lambda^*_{s,t}$ computed at the search root (Carlyle & Wood 2008).

**ADHP** discovers a set of $K$ dual slopes $\Lambda = \{\lambda_1, \dots, \lambda_K\}$ on the biobjective lower hull and constructs a discrete Legendre-Fenchel lower-bound envelope across all vertices simultaneously:
$$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k=1}^K \left[ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right]$$
where $d_{\lambda_k}(u, t)$ is the shortest path distance from $u$ to $t$ under edge weights $c(e) + \lambda_k w(e)$.

We prove:
1. **Admissibility**: For every vertex $u$ and remaining budget $\Delta w \ge 0$:
   $$\mathcal{L}_u^\Lambda(\Delta w) \le \min_{P \in \mathcal{P}_{u, t}, \, w(P) \le \Delta w} c(P)$$
2. **Strict Dominance**: $\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$ universally, with strict inequality whenever an active dual facet separates the budget constraint.
3. **Exact Global Optimality**: Filtering any candidate label with $c(P) + \mathcal{L}_u^\Lambda(W - w(P)) \ge C_{\text{UB}}$ preserves exact optimality.

---

### 3. Empirical Results
Across 25 benchmark configurations and 250 timed executions (200 distinct problem instances, 164 unique topologies):
- **Label Suppression**: On anti-correlated networks ($n=100$), ADHP reduces candidate labels from 2,751 (Martins) down to **79 labels** (a **97.1% reduction**).
- **Wall-Clock Speedup**: On 2D mesh grid networks ($10 \times 10, n=100$), Adaptive Hybrid ADHP achieves an **8.2x speedup** over Martins ($19.97 \, \mu\text{s}$ vs $163.82 \, \mu\text{s}$) and **6.3x** over Pulse ($124.91 \, \mu\text{s}$).
- **Break-Even Boundary**: On small random graphs ($n \le 60$), the fixed cost of multi-faceted Dijkstra passes makes standard Martins faster ($3.89 \, \mu\text{s}$ at $n=30$). ADHP is engineered for combinatorial bottleneck regimes with severe conflict or long paths.

---

### 4. Verification and Software Deliverables
- **Codebase**: Idiomatic Rust library (`adhp-cspp`), zero clippy warnings with `-D warnings`, zero `.unwrap()` in production paths.
- **Verification**: 100% agreement on 150 differential instances (100 float + 50 exact integer) against SciPy HiGHS MILP oracle; 32 Rust tests, 48 Python tests.
- **Paper**: Complete LaTeX manuscript (`paper/main.tex`) and synchronized Typst preprint (`paper/main.typ`).
- **Repository**: Published on GitHub at [https://github.com/rajveersinh-is-dev/adhp-cspp](https://github.com/rajveersinh-is-dev/adhp-cspp).
