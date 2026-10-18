# COMPLEXITY ANALYSIS & THEORETICAL COMPARISON
## Adaptive Dual Hull Pruning (ADHP) for the Constrained Shortest Path Problem

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/COMPLEXITY_ANALYSIS.md`  

---

### 1. Preprocessing Complexity

The preprocessing phase consists of:
1. **Adaptive Multiplier Discovery**:
   - Solving $O(K)$ single-pair shortest path queries between $s$ and $t$ using Fibonacci/binary heaps on $G$.
   - Each Dijkstra execution requires $O(m + n \log n)$ time.
   - For $K$ multipliers, total time: $O(K(m + n \log n))$.
2. **Reverse Multi-Tree Preprocessing**:
   - Building reversed graph $G^R$: $O(m + n)$ time.
   - Running $K$ single-source all-destinations Dijkstra queries from $t$ on $G^R$, plus one run for pure weight $w$:
     $$(K + 1) \times O(m + n \log n) = O(K(m + n \log n))$$
3. **Space Complexity of Preprocessing**:
   - The dual distance table `dist_dual` stores $K$ floating-point distances per vertex:
     $$\text{Space}(\text{dist\_dual}) = K \cdot n \times 8 \text{ bytes} = O(K \cdot n)$$
   - The reversed graph requires $O(m + n)$ space.
   - Total Preprocessing Space: $O(K \cdot n + m)$.

*Practical Observation*: For $n = 10,000$ and $K = 5$, `dist_dual` consumes only $5 \times 10,000 \times 8 \approx 400 \text{ KB}$ of memory, fitting entirely within the L2/L3 cache of modern microprocessors.

---

### 2. Search Complexity and Query Cost

During the main priority queue search:
1. **Dual Envelope Evaluation Query**:
   - For any candidate label at vertex $u$ with remaining budget $\Delta w$, computing $\mathcal{L}_u^\Lambda(\Delta w)$ involves evaluating:
     $$\max_{k=1}^K \{ \text{dist\_dual}[k][u] - \lambda_k \Delta w \}$$
   - **Linear Scan**: Takes $O(K)$ arithmetic operations.
   - **Convex Binary Search**: Because $-\lambda_k$ is monotonically decreasing, the upper envelope can be queried via binary search on the slope interval in $O(\log K)$ time.
   - For $K \le 8$, the linear scan has zero branching mispredictions and is faster than binary search in practice.
2. **Local Pareto Dominance**:
   - If $|\mathcal{P}_v|$ denotes the number of non-dominated labels stored at vertex $v$, checking dominance takes $O(|\mathcal{P}_v|)$ time (or $O(\log |\mathcal{P}_v|)$ via binary search over sorted weights).
3. **Total Search Time**:
   - Let $\mathcal{L}_{\text{explored}}$ be the number of labels extracted from the priority queue, and $\mathcal{L}_{\text{generated}}$ be the total number of candidate labels generated across all edge relaxations.
   - Each generated label takes $O(K + \log |\mathcal{P}_v|)$ time to evaluate.
   - Total Search Time:
     $$T_{\text{search}} = O\left( \mathcal{L}_{\text{explored}} \cdot \log \mathcal{L}_{\text{explored}} + \mathcal{L}_{\text{generated}} \cdot (K + |\mathcal{P}_v|) \right)$$

---

### 3. Comparison of Theoretical Bounds

| Algorithm | Preprocessing Time | Preprocessing Space | Worst-Case Time Complexity | Practical State Space Metric |
|---|---|---|---|---|
| **Martins (1984)** | $0$ | $0$ | $O(m \cdot |\mathcal{P}_{\text{all}}|)$ | Full Pareto Frontier Size $\sum_v |\mathcal{P}_v|$ |
| **Dumitrescu & Boland (2003)** | $O(m + n \log n)$ | $O(n)$ | $O(m \cdot |\mathcal{P}_{\text{all}}|)$ | $1D$-Filtered Frontier |
| **Carlyle & Wood (2008)** | $O(\text{LARAC})$ | $O(n)$ | $O(\text{LARAC} + K_{\text{paths}} \cdot m \log n)$ | $K_{\text{paths}}$ (Explodes with wide duality gap) |
| **Pulse (Lozano & Medaglia 2013)** | $O(m + n \log n)$ | $O(n)$ | $O(2^n)$ DFS | Explored DFS Call Tree |
| **ADHP (This Work)** | $O(K(m + n \log n))$ | $O(K \cdot n)$ | $O(K(m + n \log n) + m \cdot |\mathcal{P}_{\text{filtered}}|)$ | **$K$-Faceted Filtered Frontier** ($|\mathcal{P}_{\text{filtered}}| \ll |\mathcal{P}_{\text{all}}|$) |

---

### 4. Mathematical Pruning Advantage Analysis

Why does ADHP achieve an exponential reduction in the number of generated labels in practice?

Consider the bi-objective space $(c, w)$ at vertex $u$. Let $\mathcal{C}_u \subset \mathbb{R}^2$ be the convex hull of all feasible completions $(c(P_{u, t}), w(P_{u, t}))$.
- **1D Lower Bounds ($d_c, d_w$)**:
  - The admissible region under 1D bounds is the bounding box $[d_c(u, t), \infty) \times [d_w(u, t), \infty)$.
  - Any partial path with cost $c$ and weight $w$ is retained as long as $c + d_c(u, t) < C_{UB}$ and $w + d_w(u, t) \le W$.
  - The volume of unpruned state space in $(c, w)$ is proportional to:
    $$\text{Area}_{\text{1D}} = (C_{UB} - d_c(u, t)) \times (W - d_w(u, t))$$
- **$K$-Faceted Dual Hull Bound**:
  - The ADHP envelope cuts off the loose lower-left corner of this bounding box using $K$ supporting hyperplanes of slope $-\lambda_k$.
  - For each hyperplane $k$:
    $$c_{\text{suffix}} \ge d_{\lambda_k}(u, t) - \lambda_k w_{\text{suffix}}$$
  - The unpruned region is the intersection of the budget box with the half-spaces $c + d_{\lambda_k}(u, t) - \lambda_k(W - w) < C_{UB}$.
  - The eliminated volume is:
    $$\Delta \text{Area} = \int_{d_w(u, t)}^{W - w} (\mathcal{L}_u^\Lambda(\Delta w) - d_c(u, t)) \, d(\Delta w) > 0$$
  - In practice, as demonstrated by the experiments, $\mathcal{L}_u^\Lambda(\Delta w)$ cuts off **between 75% and 98%** of the area of the bounding box.
  - Because label generation in graphs grows exponentially with search depth, eliminating a fraction $\rho$ of labels at each step compounds exponentially across the search tree, yielding a reduction factor of $(1 - \rho)^d \ll 1$.
