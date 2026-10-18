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
$$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k=1}^K \left\{ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right\}$$
where $d_{\lambda_k}(u, t)$ is the shortest path distance from $u$ to $t$ under edge weights $c_e + \lambda_k w_e$.

We prove:
1. **Admissibility**: For every vertex $u$ and remaining budget $\Delta w \ge 0$, $\mathcal{L}_u^\Lambda(\Delta w) \le \min \{ c(P) : P \in \mathcal{P}_{u, t}, w(P) \le \Delta w \}$.
2. **Strict Dominance**: $\mathcal{L}_u^\Lambda(\Delta w) > d_c(u, t)$ whenever an active dual facet separates the budget constraint.
3. **Exact Global Optimality**: Filtering any label with $c + \mathcal{L}_u^\Lambda(W - w) \ge C_{UB}$ preserves exact optimality.

---

### 3. Empirical Results
Across 25 benchmark configurations and 250 timed executions:
- **Label Suppression**: On anti-correlated networks, ADHP reduces candidate labels from 1,449 (Martins) and 2,671 (Pulse) down to **48 labels** (a **96.7% reduction**).
- **Wall-Clock Speedup**: On 2D mesh grid networks, ADHP achieves a **2.64x speedup** over Martins at $n=81$ ($26.29 \, \mu\text{s}$ vs $69.34 \, \mu\text{s}$).
- **Break-Even Boundary**: On small dense graphs ($n \le 50$), the fixed cost of computing $K=5$ reverse Dijkstra passes makes lightweight 1D-bounding (Dumitrescu-Boland) faster. ADHP is engineered for non-trivial, combinatorial bottleneck regimes.

---

### 4. Verification and Software Deliverables
- **Codebase**: Idiomatic Rust library (`adhp-cspp`), zero clippy warnings with `-D warnings`, zero `.unwrap()` in lowering pipelines.
- **Verification**: 100% agreement on 30 differential instances across all 5 solvers; mathematical property test suite.
- **Paper**: Complete LaTeX manuscript (`paper/main.tex`) and compiled PDF (`paper/paper.pdf`).
- **Repository**: Published on GitHub at [https://github.com/rajveersinh-is-dev/adhp-cspp](https://github.com/rajveersinh-is-dev/adhp-cspp).
