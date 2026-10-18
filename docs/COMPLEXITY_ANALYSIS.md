# COMPLEXITY ANALYSIS & THEORETICAL COMPARISON
## Adaptive Dual Hull Pruning (ADHP) for the Constrained Shortest Path Problem

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/COMPLEXITY_ANALYSIS.md`  

---

### 1. Preprocessing Complexity

In the backward-centric architecture:
1. **Backward-Centric Tree Preprocessing**:
   - The graph reversal $G^R$ is precomputed once in $O(m + n)$ time and space.
   - Run 1 (Pure weight): Computes $d_w(\cdot, t)$ and reconstructs $P_w(s, t)$ in $O(m + n \log n)$ time.
     *If $d_w(s, t) > W$, the instance is certified infeasible and terminates immediately in a single Dijkstra pass ($1 \times O(m + n \log n)$).*
   - Run 2 (Pure cost, $\lambda_1 = 0$): Computes $d_c(\cdot, t)$ and reconstructs $P_c(s, t)$ in $O(m + n \log n)$ time.
     *If $w(P_c) \le W$, the unconstrained cost-minimal path is feasible and globally optimal, terminating in 2 Dijkstra passes ($2 \times O(m + n \log n)$).*
   - Runs 3 to $K+1$ (Adaptive Dual Facets):
     Each bisection step runs backward Dijkstra on $G^R$ from $t$ with multiplier $\lambda_{mid}$.
     By Theorem 0 (Backward-Centric Tree Duality), a single backward pass simultaneously produces:
     1. The path $P_{mid}(s, t)$ used to tighten the global upper bound $C_{UB}$.
     2. The complete reverse distance vector $d_{\lambda_{mid}}(\cdot, t)$ saved directly to `dist_dual`.
     Zero duplicate forward Dijkstra passes are executed.
   - For at most $K$ dual multipliers, total preprocessing runs are bounded by $K + 1$ Dijkstra passes:
     $$T_{\text{prep}} \le (K + 1) \cdot O(m + n \log n)$$
   - With adaptive termination (halting when marginal root lower bound improvement $\delta \le 0.02$), the effective number of facets is typically $2 \le K \le 3$, cutting preprocessing to $3$ to $4$ passes.

2. **Space Complexity of Preprocessing**:
   - The dual distance array `dist_dual` stores $K$ floats per vertex:
     $$\text{Space}(\text{dist\_dual}) = K \cdot n \times 8 \text{ bytes} = O(K \cdot n)$$
   - The reverse graph requires $O(m + n)$ storage.
   - Total Space: $O(K \cdot n + m)$. For $n = 10,000$ and $K = 5$, `dist_dual` occupies only $400 \text{ KB}$, fitting within the CPU L2/L3 cache.

---

### 2. Search Complexity and Query Cost

During priority queue label setting:
1. **Dual Envelope Evaluation**:
   - For a candidate label at vertex $u$ with remaining budget $\Delta w$, computing $\mathcal{L}_u^\Lambda(\Delta w) = \max_{k=1}^K [ d_{\lambda_k}(u, t) - \lambda_k \Delta w ]$ takes $O(K)$ time via a linear loop.
   - For practical $K \in \{1, \dots, 5\}$, this linear scan runs in under 10 nanoseconds without cache misses.
2. **Strict Local Pareto Dominance**:
   - At vertex $v$, `VertexFrontier` maintains non-dominated labels sorted by weight ascending.
   - Using `partition_point`, `is_dominated` locates the maximal-weight label $\le new\_w$ in $O(\log |\mathcal{P}_v|)$ time.
   - Pruning dominated labels takes $O(|\mathcal{P}_v|)$ time in the worst case (or $O(1)$ amortized when few labels are dominated).
3. **Total Search Time**:
   - Let $\mathcal{L}_{\text{explored}}$ be labels extracted from the priority queue, and $\mathcal{L}_{\text{generated}}$ be candidate labels generated.
   - Search complexity:
     $$T_{\text{search}} = O\left( \mathcal{L}_{\text{explored}} \log \mathcal{L}_{\text{explored}} + \mathcal{L}_{\text{generated}} \cdot (K + \log |\mathcal{P}_v|) \right)$$

---

### 3. NP-Hardness Honesty & Worst-Case Behavior

The Constrained Shortest Path Problem is weakly NP-hard (Garey & Johnson 1979). 
- In the worst case, the number of non-dominated Pareto paths $|\mathcal{P}_{\text{all}}|$ can grow exponentially with graph size: $|\mathcal{P}_{\text{all}}| = \Omega(2^{n/2})$ on specially constructed adversarial topologies.
- ADHP does **not** alter the worst-case complexity of CSPP: $T_{\text{worst}} = O(2^n)$.
- What ADHP accomplishes is an empirical and mathematical suppression of the explored label space by cutting off up to 98% of candidate labels before they are enqueued.

---

### 4. Theoretical Comparison of Solvers

| Algorithm | Preprocessing Dijkstra Runs | Preprocessing Space | Worst-Case Time | Search Pruning Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **Martins (1984)** | $0$ | $0$ | $O(m \cdot |\mathcal{P}|)$ | Local Pareto dominance only |
| **Dumitrescu & Boland (2003)** | $2$ (1 cost, 1 weight) | $O(n)$ | $O(m \cdot |\mathcal{P}|)$ | 1D cost ($d_c$) + 1D weight ($d_w$) |
| **Carlyle & Wood (2008)** | $\text{LARAC}$ ($\approx 3\text{--}6$ runs) | $O(n)$ | $O(K_{\text{paths}} \cdot m \log n)$ | Single Lagrangian multiplier bound |
| **Pulse (2013)** | $2$ (1 cost, 1 weight) | $O(n)$ | $O(2^n)$ DFS | Recursive DFS with 1D bounds & memory |
| **ADHP (This Work)** | $K + 1$ (Adaptive $2\text{--}4$ runs) | $O(K \cdot n)$ | $O(m \cdot |\mathcal{P}_{\text{filtered}}|)$ | **Convex $K$-Faceted Dual Envelope** $\mathcal{L}_u^\Lambda(\Delta w)$ |

---

### 5. Practical Trade-off and Break-Even Regime

The total wall-clock execution time is:
$$T_{\text{total}} = T_{\text{prep}} + T_{\text{search}}$$

1. **Favorable Regime (ADHP Dominates)**:
   - Planar grids, mesh networks, transport topologies, and large sparse multigraphs where shortest paths branch heavily and many alternative paths exist.
   - On Grid 10x10 ($n = 100$): ADHP takes $57.11 \ \mu\text{s}$ (generating 105 labels), outperforming Dumitrescu-Boland ($72.82 \ \mu\text{s}$, 662 labels), Pulse ($288.66 \ \mu\text{s}$, 4,741 labels), and Martins ($337.70 \ \mu\text{s}$, 3,111 labels).
   - In this regime, the 6x to 45x reduction in label exploration easily offsets the $K+1$ backward Dijkstra preprocessing passes.

2. **Unfavorable Regime (Simpler Solvers Win)**:
   - Small graphs ($n \le 30$) or dense graphs where label exploration is already fast.
   - On dense anti-correlated graphs or small random ER graphs, Martins (0 preprocessing) and Dumitrescu-Boland (2 Dijkstra passes) achieve faster total wall-clock times because the preprocessing overhead of computing additional dual facets exceeds the modest search time savings.
