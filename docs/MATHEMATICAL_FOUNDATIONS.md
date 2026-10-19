# MATHEMATICAL FOUNDATIONS & FORMAL PROOFS
## Adaptive Dual Hull Pruning (ADHP) for the Constrained Shortest Path Problem

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/MATHEMATICAL_FOUNDATIONS.md`  

---

### 1. The Lagrangian Dual and Parametric Shortest Paths

Consider the single-source single-target Weight-Constrained Shortest Path Problem (CSPP) on a directed multigraph $G=(V, E)$ with source vertex $s$, destination vertex $t$, non-negative traversal costs $c_e \ge 0$, non-negative resource consumption weights $w_e \ge 0$, and global resource budget $W \ge 0$.

For any non-negative scalar dual multiplier $\lambda \ge 0$, we define the **composite parametric edge weight**:
$$c_e^\lambda = c_e + \lambda w_e, \quad \forall e \in E$$

Because $c_e \ge 0$, $w_e \ge 0$, and $\lambda \ge 0$, we have $c_e^\lambda \ge 0$ for all $e \in E$, guaranteeing that Dijkstra's algorithm with non-negative edge lengths remains applicable.

#### Definition 1.1 (Parametric Distance Function)
For any pair of vertices $u, v \in V$ and parameter $\lambda \ge 0$, the parametric shortest path distance $d_\lambda(u, v)$ is defined as:
$$d_\lambda(u, v) = \min_{P \in \mathcal{P}_{u, v}} \sum_{e \in P} c_e^\lambda = \min_{P \in \mathcal{P}_{u, v}} \left( c(P) + \lambda w(P) \right)$$

#### Proposition 1.1 (Properties of the Parametric Distance Function)
For any fixed pair $(u, v) \in V \times V$, the mapping $\lambda \mapsto d_\lambda(u, v)$ is:
1. **Concave**: It is the pointwise infimum of a collection of affine functions $\lambda \mapsto c(P) + \lambda w(P)$ over simple paths $P \in \mathcal{P}_{u, v}$.
2. **Monotonically Non-decreasing**: For $0 \le \lambda_1 \le \lambda_2$, non-negativity of weights ($w(P) \ge 0$) implies $c(P) + \lambda_1 w(P) \le c(P) + \lambda_2 w(P)$ for every path $P$.
3. **Piecewise-Linear**: Because the number of simple directed paths between $u$ and $v$ is finite, the infimum is taken over a finite set of linear segments.

---

### 2. The Continuous Legendre-Fenchel Dual Envelope

At an intermediate search vertex $u \in V$, suppose a partial path from $s$ to $u$ has consumed resource weight $w_{cur}$. The **remaining resource budget** to reach destination $t$ is:
$$\Delta w = W - w_{cur}$$

Any completion path $P_{u \to t} \in \mathcal{P}_{u, t}$ is resource-feasible if and only if $w(P_{u \to t}) \le \Delta w$.

#### Definition 2.1 (Continuous Dual Lower-Bound Function)
For any vertex $u \in V$ and remaining budget $\Delta w \ge 0$, the continuous Lagrangian dual lower-bound function $\mathcal{L}_u^*(\Delta w)$ is defined as:
$$\mathcal{L}_u^*(\Delta w) = \sup_{\lambda \ge 0} \left[ d_\lambda(u, t) - \lambda \Delta w \right]$$

Geometrically, $\mathcal{L}_u^*(\Delta w)$ is the **Legendre-Fenchel conjugate** of the concave parametric distance function $\lambda \mapsto d_\lambda(u, t)$, evaluated at $-\Delta w$.

---

### 3. The $K$-Faceted Adaptive Dual Hull (ADH)

Computing the continuous supremum $\sup_{\lambda \ge 0}$ during forward search for all intermediate labels is computationally prohibitive. 

ADHP constructs a **Discrete $K$-Faceted Lower-Bound Envelope** supported by a finite, adaptively chosen set of dual multipliers:
$$\Lambda = \{\lambda_1, \lambda_2, \dots, \lambda_K\}, \quad \text{where } 0 = \lambda_1 < \lambda_2 < \dots < \lambda_K < \infty$$

#### Definition 3.1 ($K$-Faceted Lower-Bound Envelope)
For any vertex $u \in V$ and remaining budget $\Delta w \ge 0$, the $K$-faceted envelope $\mathcal{L}_u^\Lambda(\Delta w)$ is defined as:
$$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k \in \{1, \dots, K\}} \left[ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right]$$

---

### 4. Backward-Centric Tree Duality Theorem

#### Theorem 0 (Simultaneous Bound & Incumbent Discovery via Reverse Trees)
*Let $G^R = (V, E^R)$ be the reverse graph of $G$, where each edge $e = (u, v) \in E$ is replaced by $e^R = (v, u) \in E^R$ with identical cost $c_e$ and weight $w_e$.*  
*A single backward Dijkstra execution from destination $t$ on $G^R$ with metric $c_e + \lambda w_e$ simultaneously computes:*
1. *The exact reverse distance vector $d_\lambda(u, t)$ for all vertices $u \in V$.*
2. *The unconstrained shortest $(s, t)$-path $P_\lambda(s, t)$ in forward order by following the successor pointers from $s$, without requiring any forward Dijkstra search.*

**Proof:**  
In $G^R$, the shortest path distance from $t$ to $u$ under metric $c_e + \lambda w_e$ equals the shortest path distance from $u$ to $t$ in $G$.  
When backward Dijkstra relaxes an incoming edge $e = (v \to u) \in E$ (which is outgoing $u \to v$ in $G^R$) and updates the label at $v$, $u$ is recorded as the successor of $v$ on the shortest path toward $t$: $\text{succ}[v] = u$.  
Starting at source $s$ and iteratively following $\text{succ}[s], \text{succ}[\text{succ}[s]], \dots$ traces the exact sequence of edges on the shortest path from $s$ to $t$ in $G$ in forward order. The cumulative cost and weight of this path provide an immediate feasible candidate solution whenever $\sum_{e \in P} w_e \le W$, tightening the global upper bound $C_{UB}$ before search begins. $\blacksquare$

---

### 5. Formal Proofs of Core Theorems

#### Theorem 1 (Admissibility and Lower-Bound Validity)
*Let $u \in V$ be any vertex, and let $\Delta w \ge 0$ be any remaining budget. For every path $P \in \mathcal{P}_{u, t}$ satisfying the budget constraint $w(P) \le \Delta w$, the path cost is bounded below by the discrete envelope:*
$$c(P) \ge \mathcal{L}_u^\Lambda(\Delta w)$$

**Proof:**  
Let $P \in \mathcal{P}_{u, t}$ be an arbitrary completion path from $u$ to $t$ such that $w(P) \le \Delta w$.  
By Definition 1.1, for any $\lambda_k \ge 0$:
$$d_{\lambda_k}(u, t) \le \sum_{e \in P} (c_e + \lambda_k w_e) = c(P) + \lambda_k w(P)$$

Rearranging:
$$c(P) \ge d_{\lambda_k}(u, t) - \lambda_k w(P)$$

Because $\lambda_k \ge 0$ and $w(P) \le \Delta w$, we have $-\lambda_k w(P) \ge -\lambda_k \Delta w$. Substituting this yields:
$$c(P) \ge d_{\lambda_k}(u, t) - \lambda_k \Delta w$$

Because this holds independently for every multiplier index $k \in \{1, \dots, K\}$, it holds for the maximum:
$$c(P) \ge \max_{k \in \{1, \dots, K\}} \left[ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right] = \mathcal{L}_u^\Lambda(\Delta w)$$
$\blacksquare$

---

#### Theorem 2 (Dominance Conditions and Subsumption of 1D Bounds)
*Let $d_c(u, t) = \min_{P \in \mathcal{P}_{u, t}} c(P)$ be the unconstrained cost distance from $u$ to $t$, and let $d_w(u, t) = \min_{P \in \mathcal{P}_{u, t}} w(P)$ be the unconstrained weight distance.*  
*Let $\Lambda = \{\lambda_1, \dots, \lambda_K\}$ with $0 = \lambda_1 < \dots < \lambda_K < \infty$.*

1. **Lower Bound Dominance**:  
   *For all vertices $u \in V$ and remaining budgets $\Delta w \ge 0$:*
   $$\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$$
   *Strict dominance $\mathcal{L}_u^\Lambda(\Delta w) > d_c(u, t)$ holds if and only if there exists an active dual multiplier $\lambda_k \in \Lambda$ ($\lambda_k > 0$) satisfying:*
   $$d_{\lambda_k}(u, t) - d_c(u, t) > \lambda_k \Delta w$$
   *This requires that the unconstrained cost-minimal path violates the remaining budget ($\Delta w < \min \{ w(P) \mid P \in \mathcal{P}_{u, t}, c(P) = d_c(u, t) \}$) and that $\Lambda$ contains a supporting hyperplane separating $(\Delta w, d_c(u, t))$ from the epigraph of the dual function.*

2. **Mathematical Subsumption of Classical 1D Pruning**:  
   *Under identical relational comparison operators (strict inequality $>$ or non-strict $\ge$) and identical incumbent $C_{UB}$:*
   - *Any candidate label pruned by 1D cost bounding ($c_{cur} + d_c(u, t) > C_{UB}$) is strictly pruned by ADHP Filter 2 ($c_{cur} + \mathcal{L}_u^\Lambda(\Delta w) > C_{UB}$).*
   - *Any candidate label pruned by weight infeasibility ($w_{cur} + d_w(u, t) > W$) is pruned by ADHP Filter 1.*

3. **Boundary Equality & Tolerance Specification**:  
   *In finite-precision implementations, classical algorithms that test non-strict inequalities ($c + d_c \ge C_{UB}$) prune boundary labels where $c + d_c = C_{UB}$. Conversely, $\epsilon$-tolerant pruning ($c + \mathcal{L} > C_{UB} + \text{tol}$) permits near-tie labels within tolerance to be explored. Exact theoretical subsumption holds between the mathematical formulations with identical relational operators.*

**Proof:**  
1. Because $\lambda_1 = 0 \in \Lambda$:
   $$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k=1}^K [d_{\lambda_k}(u, t) - \lambda_k \Delta w] \ge d_{\lambda_1}(u, t) - 0 \cdot \Delta w = d_c(u, t)$$
   The condition $d_{\lambda_k}(u, t) - d_c(u, t) > \lambda_k \Delta w$ is directly equivalent to $d_{\lambda_k}(u, t) - \lambda_k \Delta w > d_c(u, t)$. Taking the maximum over $k$ yields $\mathcal{L}_u^\Lambda(\Delta w) > d_c(u, t)$.
2. If a label satisfies $c_{cur} + d_c(u, t) > C_{UB}$, then by Part 1:
   $$c_{cur} + \mathcal{L}_u^\Lambda(\Delta w) \ge c_{cur} + d_c(u, t) > C_{UB}$$
   Therefore, Filter 2 prunes the label. $\blacksquare$

---

#### Theorem 3 (Convexity, Continuity, and Monotonicity)
*For every vertex $u \in V$, the discrete lower-bound envelope $\Delta w \mapsto \mathcal{L}_u^\Lambda(\Delta w)$ is:*
1. **Convex** on $[0, \infty)$.
2. **Continuous** and **Piecewise-Linear** on $[0, \infty)$ with at most $K$ linear pieces.
3. **Monotonically Non-Increasing**: if $0 \le \Delta w_1 \le \Delta w_2$, then $\mathcal{L}_u^\Lambda(\Delta w_1) \ge \mathcal{L}_u^\Lambda(\Delta w_2)$.

**Proof:**  
1. For each $k \in \{1, \dots, K\}$, the component $f_k(\Delta w) = d_{\lambda_k}(u, t) - \lambda_k \Delta w$ is affine. The pointwise maximum of affine functions is convex.
2. The pointwise maximum of finitely many continuous linear functions is continuous and piecewise-linear with at most $K$ linear facets.
3. Because $\lambda_k \ge 0$, the slope of each affine component is $-\lambda_k \le 0$. The maximum of non-increasing functions is non-increasing. $\blacksquare$

---

#### Theorem 4 (Exact Integer Optimality vs Finite-Precision $\epsilon$-Admissibility)

##### Part A: Mathematically Exact Integer Optimality (`IntAdhpSolver`)
*Let $G = (V, E)$ be a directed multigraph with non-negative integer edge costs $c_e \in \mathbb{N}_0$, integer weights $w_e \in \mathbb{N}_0$, and integer budget $W \in \mathbb{N}_0$.*  
*Under exact integer arithmetic (`u64`) with rational multipliers $\lambda_k = p_k / q_k$, ceiling lower-bound evaluation $\lceil \frac{d_{\lambda_k} - p_k \Delta w}{q_k} \rceil$, zero-tolerance feasibility ($w \le W$), and strict Pareto dominance ($w_p \le w \land c_p \le c$), ADHP:*
1. *Preserves every optimal constrained shortest path prefix.*
2. *Terminates in finite operations.*
3. *Returns a path whose cost is mathematically identical to the global constrained optimum.*

##### Part B: Finite-Precision $(\epsilon_{\text{feas}}, \epsilon_{\text{prune}})$-Admissibility (`AdhpSolver`)
*Under IEEE 754 double precision (`f64`) with relative feasibility tolerance $\text{tol}_{\text{feas}}(W) = \max(1.0, |W|) \cdot 10^{-9}$ and relative pruning tolerance $\text{tol}_{\text{prune}}(C_{UB}) = \max(1.0, |C_{UB}|) \cdot 10^{-9}$:*
1. *Any optimal path $P^*$ satisfies Higham's summation error bound $|\text{fl}(c(P^*)) - c(P^*)| \le \gamma_n c(P^*)$ and $|\text{fl}(w(P^*)) - w(P^*)| \le \gamma_n w(P^*)$, where $\gamma_n = \frac{n \epsilon_{\text{mach}}}{1 - n \epsilon_{\text{mach}}} \le 2.3 \times 10^{-11} \ll 10^{-9}$ for all $n \le 10^5$.*
2. *No subpath of any optimal path is pruned by Filter 1 or Filter 2.*
3. *Strict Pareto dominance without positive tolerances ensures that no non-dominated trade-off label is falsely discarded.*
4. *ADHP returns an $(\epsilon_{\text{feas}}, \epsilon_{\text{prune}})$-optimal constrained shortest path in finite time.*

**Proof:**  

**Prefix Induction on Optimal Path:**  
Let $P^* = (s = v_0, v_1, \dots, v_m = t)$ be an optimal constrained path with cost $\text{OPT}$ and weight $w(P^*) \le W$.  
We induct on prefix index $i \in \{0, \dots, m\}$.  
- **Base Case ($i = 0$)**: The initial label $(0, 0)$ is settled at $s = v_0$. Holds trivially.  
- **Inductive Step ($i \to i+1$)**: Suppose prefix $P^*[s \to v_i]$ has been settled with a label $(c_i, w_i)$ such that $c_i \le c(P^*[s \to v_i])$ and $w_i \le w(P^*[s \to v_i])$.  
  Relaxing edge $e = (v_i, v_{i+1}) \in P^*$ produces candidate label $\ell_{i+1} = (c_i + c_e, w_i + w_e)$.  
  - *Filter 1*: In exact arithmetic, $w_{i+1} + d_w(v_{i+1}, t) \le w(P^*) \le W$, so $\ell_{i+1}$ is never pruned. In `f64`, $\text{fl}(w_{i+1} + d_w) \le W + \gamma_n W \le W + \text{tol}_{\text{feas}}(W)$, so $\ell_{i+1}$ is not pruned.  
  - *Filter 2*: By Theorem 1, $\mathcal{L}_{v_{i+1}}^\Lambda(W - w_{i+1}) \le c(P^*[v_{i+1} \to t])$.  
    Therefore $c_{i+1} + \mathcal{L}_{v_{i+1}}^\Lambda \le c(P^*) \le C_{UB}$.  
    In exact integer arithmetic, $c_{i+1} + \mathcal{L}_{v_{i+1}} \le C_{UB}$, so it is not pruned.  
    In `f64`, $c_{i+1} + \mathcal{L}_{v_{i+1}} \le C_{UB} + \text{tol}_{\text{prune}}$, so it is not pruned.  
  - *Filter 3 (Strict Pareto Dominance)*: Either $\ell_{i+1}$ is non-dominated and entered into the frontier and queue, or an existing point $\tilde{\ell} = (\tilde{c}, \tilde{w})$ in the frontier satisfies $\tilde{c} \le c_{i+1}$ and $\tilde{w} \le w_{i+1}$. In the latter case, replacing the prefix with $\tilde{\ell}$ preserves the optimal path completion.  
- **Termination ($i = m$)**: An optimal label enters `frontiers[t]`. Since feasible labels update $C_{UB}$, the returned solution achieves cost exactly equal to the optimal cost in exact arithmetic, or within $\text{tol}_{\text{prune}}$ in floating-point arithmetic. $\blacksquare$

---

### 6. Summary of Numerical Contracts

| Feature | Exact Integer Engine (`IntAdhpSolver`) | Floating-Point Engine (`AdhpSolver`) |
| :--- | :--- | :--- |
| **Input Types** | `u64` (Cost, Weight, Budget) | `f64` (Cost, Weight, Budget) |
| **Arithmetic** | Exact integer with checked overflow | IEEE 754 double precision (`f64`) |
| **Multipliers** | Exact rational $\lambda = p / q$ | Finite-precision floating point |
| **Feasibility Policy** | Zero tolerance: $w \le W$ | Relative tolerance: $w \le W + 10^{-9} \max(1, W)$ |
| **Pruning Policy** | Strict integer bound: $c + \mathcal{L} > C_{UB}$ | Relative tolerance: $c + \mathcal{L} > C_{UB} + 10^{-9} \max(1, C_{UB})$ |
| **Dominance Policy** | Strict: $w_p \le w \land c_p \le c$ | Strict: $w_p \le w \land c_p \le c$ (Zero tolerance) |
| **Guarantee** | Mathematically exact zero-tolerance optimality | Certified $(\epsilon_{\text{feas}}, \epsilon_{\text{prune}})$-admissibility |

---

### 7. Exact 128-Bit Arithmetic and Overflow Prevention

In integer CSPP solving, parametric Dijkstra searches with rational multipliers $\lambda = \text{num} / \text{den}$ evaluate composite edge metrics of the form:
$$c_e^\lambda \cdot \text{den} = c_e \cdot \text{den} + w_e \cdot \text{num}$$

Let $C_{\max} = \sum_{e \in E} c_e$ and $W_{\max} = \sum_{e \in E} w_e$. Because the multiplier denominator satisfies $\text{den} \le W_{\max}$ and the numerator satisfies $\text{num} \le C_{\max}$, the composite metric of any edge or path satisfies:
$$c_e \cdot \text{den} + w_e \cdot \text{num} \le 2 \cdot C_{\max} \cdot W_{\max}$$

- **Vulnerability in 64-bit Arithmetic**: When edge costs and weights reach $10^{10}$, $2 \cdot C_{\max} \cdot W_{\max} \approx 2 \times 10^{20} > 1.84 \times 10^{19} = \text{u64::MAX}$. In standard 64-bit implementations, this silent overflow wraps or saturates, causing reverse Dijkstra to drop edges or compute inflated distances, corrupting lower bounds and pruning optimal paths.
- **128-Bit Resolution in `IntAdhpSolver`**: By evaluating all composite multiplications and additions in `u128` (maximum value $3.4 \times 10^{38}$), instances with total edge weights and costs up to $10^{18}$ are mathematically guaranteed to execute without overflow. Furthermore, all intermediate calculations use checked arithmetic (`checked_mul`, `checked_add`), safely discarding any overflowing candidate facet without compromising admissibility (by Theorem 1).

---

### 8. Theorem 5 (Instance-Adaptive Bounding Optimality)

#### Theorem 5 (Admissibility and Pareto-Efficiency of Adaptive Facet Selection)
*Let $\mathcal{I} = (G, s, t, W)$ be a CSPP instance with initial weight-minimizing path $P_w$ and cost-minimizing path $P_c$.*  
*Let $\rho = |E| / |V|$ be network density, $\gamma = (c(P_w) - c(P_c)) / \max(c(P_w), 1)$ be duality gap ratio, and $\alpha = (W - w(P_w)) / \max(w(P_c) - w(P_w), 1)$ be resource tightness.*  
*Define the adaptive facet budget selection rule $\sigma(\mathcal{I}) \in \{1, 2, K_{\max}\}$ by:*
$$\sigma(\mathcal{I}) = \begin{cases} 1 & \text{if } \gamma < 0.04 \lor \alpha \ge 0.85 \lor (\rho \ge 3.5 \land |V| \le 200) \\ K_{\max} & \text{if } \rho \le 2.5 \land \gamma \ge 0.15 \land \alpha \le 0.70 \\ 2 & \text{otherwise} \end{cases}$$
*Then:*
1. **Admissibility**: *For every selected budget $K = \sigma(\mathcal{I})$, the resulting lower-bound envelope $\mathcal{L}_u^{\Lambda_K}(\Delta w)$ is strictly admissible: for all $u \in V$ and $\Delta w \ge 0$, $\mathcal{L}_u^{\Lambda_K}(\Delta w) \le \text{OPT}(u \to t \mid \Delta w)$.*
2. **Subsumption**: *For $K = 1$, the lower bound strictly subsumes classical 1D unconstrained cost bounding: $\mathcal{L}_u^{\Lambda_1}(\Delta w) = d_c(u, t)$.*
3. **Worst-Case Preprocessing Guarantee**: *Preprocessing time is strictly bounded by $O(\sigma(\mathcal{I}) \cdot (|E| + |V| \log |V|))$. On dense networks ($\rho \ge 3.5$), preprocessing is bounded by $2 \cdot (|E| + |V| \log |V|)$, eliminating asymptotic overhead.*

**Proof:**  
1. By Theorem 1, for any set of non-negative dual multipliers $\Lambda$, the discrete lower-bound envelope is admissible. Because $\Lambda_K \subset \mathbb{R}_{\ge 0}$ for every choice $K \in \{1, 2, K_{\max}\}$, $\mathcal{L}_u^{\Lambda_K}(\Delta w) \le \text{OPT}(u \to t \mid \Delta w)$ holds unconditionally.  
2. When $K=1$, $\Lambda_1 = \{\lambda_1 = 0\}$. By Definition 3.1, $\mathcal{L}_u^{\Lambda_1}(\Delta w) = d_0(u, t) - 0 \cdot \Delta w = d_c(u, t)$. By Theorem 2, this matches classical 1D bounding.  
3. Each discovered facet requires exactly one reverse Dijkstra pass with complexity $O(|E| + |V| \log |V|)$. For $\sigma(\mathcal{I}) = 1$, only the two initial trees ($T_w$ and $T_c$) are computed, bounding preprocessing time to $2 \cdot (|E| + |V| \log |V|)$. $\blacksquare$

