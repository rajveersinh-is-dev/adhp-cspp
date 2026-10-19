# ALGORITHM DESIGN & ARCHITECTURE SPECIFICATION
## Adaptive Dual Hull Pruning (ADHP) and Adaptive Hybrid Solver Architecture

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/ALGORITHM_DESIGN.md`  
**Repository**: [https://github.com/rajveersinh-is-dev/adhp-cspp](https://github.com/rajveersinh-is-dev/adhp-cspp)

---

### 1. High-Level Architecture Overview

ADHP-CSPP decomposes the NP-hard Constrained Shortest Path Problem into three synergistically coupled algorithmic stages:

```
+------------------------------------------------------------------------+
| 1. Backward Preprocessing & Extreme Incumbent Harvesting               |
|    - Backward Tree T_w (use_weight_only = true):                       |
|      * d_w(u, t) for all u (Filter 1 resource bounds)                  |
|      * Immediate feasibility check: d_w(s, t) <= W                     |
|      * Path P_w(s, t) provides initial upper bound C_UB                |
|    - Backward Tree T_c (lambda = 0, num = 0, den = 1):                 |
|      * d_c(u, t) for all u (1D unconstrained cost bounds)              |
|      * Immediate optimality check: if w(P_c) <= W, return OPT (0 search)|
+------------------------------------------------------------------------+
                                   |
                                   v
+------------------------------------------------------------------------+
| 2. Instance-Adaptive Multiplier Discovery (Lower Hull Bisection)       |
|    - Evaluates observable instance metrics: density rho, gap gamma,    |
|      and tightness alpha in O(1) time                                  |
|    - Selects target facet count K in {1, 2, 5}                         |
|    - Computes reverse trees for mid-multipliers lambda = dc / dw:      |
|      * Harvests feasible paths to tighten C_UB before search           |
|      * Records 128-bit exact distance vectors d_lambda(u, t)           |
+------------------------------------------------------------------------+
                                   |
                                   v
+------------------------------------------------------------------------+
| 3. Multi-Faceted Priority Search & Dominance Engine                    |
|    - Min-Heap ordered by lower-bound key: c_u + L_u^Lambda(W - w_u)    |
|    - Three-stage hierarchical pruning pipeline:                        |
|        Filter 1: Resource feasibility (d_w)                            |
|        Filter 2: Discrete Dual Envelope Pruning (L_u^Lambda)           |
|        Filter 3: Local Strict Pareto Dominance (O(log |F|) search)     |
|    - Compact array pool for O(1) memory and exact path reconstruction   |
+------------------------------------------------------------------------+
```

---

### 2. Algorithmic Modules

#### 2.1 Backward-Centric Tree Preprocessing
In classical CSPP solvers (e.g., Carlyle-Wood), finding dual multipliers requires running forward Dijkstras, followed by reverse Dijkstras to obtain distance fields for A* heuristics.

ADHP introduces **Backward-Centric Tree Duality** (Theorem 0):
- Reverse Dijkstra is executed from destination $t$ on the incoming adjacency list.
- Because edge metrics $c_e + \lambda w_e$ are symmetric between forward and reverse orientations, the reverse shortest path tree rooted at $t$ simultaneously contains:
  1. The exact distance $d_\lambda(u, t)$ from every vertex $u$ to $t$.
  2. The exact forward shortest path $P_\lambda(s, t)$ by starting at $s$ and iteratively following `successor` pointers to $t$.
- **Zero Forward Runs Required**: Every candidate path evaluated during dual bisection is extracted directly from the backward tree, cutting preprocessing Dijkstra passes in half.

#### 2.2 Hierarchical Three-Tier Pruning Pipeline
When relaxing an outgoing edge $e = (u, v)$ with cost $c_e$ and weight $w_e$, candidate label $(c_{new}, w_{new}) = (c_u + c_e, w_u + w_e)$ undergoes three sequential filters:

1. **Filter 1 (Resource Infeasibility)**:
   $$w_{new} + d_w(v, t) > W$$
   Evaluated in $O(1)$ time using the precomputed weight distance $d_w(v, t)$. If true, no extension of this path can reach $t$ within budget $W$.

2. **Filter 2 (Dual Hull Pruning)**:
   $$c_{new} + \mathcal{L}_v^\Lambda(W - w_{new}) > C_{UB}$$
   Where $\mathcal{L}_v^\Lambda(\Delta w) = \max_{k=1}^K [d_{\lambda_k}(v, t) - \lambda_k \Delta w]$.  
   By Theorem 1, $\mathcal{L}_v^\Lambda$ is a strictly admissible lower bound. If the path's minimum possible completion cost exceeds the incumbent upper bound $C_{UB}$, it is safely pruned.

3. **Filter 3 (Strict Local Pareto Dominance)**:
   Candidate $(c_{new}, w_{new})$ is compared against existing non-dominated points at vertex $v$.
   A point $p$ weakly dominates candidate $q$ if $w_p \le w_q \land c_p \le c_q$.
   Using binary search over weight-sorted points in `VertexFrontier`, this check executes in $O(\log |\mathcal{F}_v|)$ time.

---

### 3. Exact 128-Bit Integer Arithmetic Architecture (`IntAdhpSolver`)

To guarantee 100% mathematical exactness without floating-point rounding errors or integer overflow:
1. **Rational Multipliers**: Dual multipliers are stored as irreducible fractions $\lambda = \text{num} / \text{den}$ ($\text{num}, \text{den} \in \mathbb{N}_0$).
2. **128-Bit Composite Metric**:
   $$c_e^\lambda \cdot \text{den} = c_e \cdot \text{den} + w_e \cdot \text{num}$$
   In 64-bit integer arithmetic, graphs with edge metrics $\approx 10^{10}$ overflow $u64::MAX \approx 1.84 \times 10^{19}$. `IntAdhpSolver` evaluates all composite metrics in `u128` (maximum value $3.4 \times 10^{38}$).
3. **Exact Ceiling Evaluation**:
   $$\mathcal{L}_u^{\lambda}(\Delta w) = \left\lceil \frac{d_\lambda(u, t) - \Delta w \cdot \text{num}}{\text{den}} \right\rceil = (d - \Delta w \cdot \text{num} + \text{den} - 1) / \text{den}$$
4. **Zero Tolerance**: All feasibility and dominance tests use exact non-strict and strict inequalities without positive tolerances, preventing false dominance.

---

### 4. Instance-Adaptive Hybrid Meta-Solver (`HybridAdhpSolver`)

To eliminate the preprocessing overhead on dense networks and loose-budget instances, `HybridAdhpSolver` introduces a constant-time decision rule based on three observable instance parameters:
1. **Network Density**: $\rho = |E| / |V|$.
2. **Duality Gap Ratio**: $\gamma = (c(P_w) - c(P_c)) / \max(c(P_w), 1.0)$.
3. **Resource Tightness**: $\alpha = (W - w(P_w)) / \max(w(P_c) - w(P_w), 1.0) \in [0, 1]$.

#### Decision Policy:
- **Strategy A: 1D Fast Bounding ($K=1$)**
  Triggered when:
  $$\gamma < 0.04 \quad \lor \quad \alpha \ge 0.85 \quad \lor \quad (\rho \ge 3.5 \land |V| \le 200)$$
  *Rationale*: If the duality gap is $<4\%$ or budget is generous ($\alpha \ge 0.85$), the unconstrained cost bound $d_c(u, t)$ alone prunes nearly all sub-optimal paths. On dense graphs ($\rho \ge 3.5$), search is naturally fast ($<25 \, \mu\text{s}$), so avoiding extra reverse Dijkstra passes saves $\sim 50 \, \mu\text{s}$ of preprocessing.
- **Strategy B: Deep Multi-Faceted ADHP ($K=5$)**
  Triggered when:
  $$\rho \le 2.5 \quad \land \quad \gamma \ge 0.15 \quad \land \quad \alpha \le 0.70$$
  *Rationale*: On sparse planar grids with conflicting objectives and tight budgets, multi-faceted dual envelope prunes $85-95\%$ of labels, yielding the fastest wall-clock execution (winning on Grid 10x10 and Anti-Correlated $n=150$).
- **Strategy C: Balanced Dual Bounding ($K=2$)**
  Triggered in all intermediate configurations, discovering 1 optimal intermediate bisector facet.

Every branch preserves 100% mathematical exactness because each choice $K \ge 1$ maintains certified admissible lower bounds.
