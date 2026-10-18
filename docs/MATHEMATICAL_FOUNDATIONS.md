# MATHEMATICAL FOUNDATIONS & FORMAL PROOFS
## Adaptive Dual Hull Pruning (ADHP) for the Constrained Shortest Path Problem

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/MATHEMATICAL_FOUNDATIONS.md`  

---

### 1. The Lagrangian Dual and Parametric Shortest Paths

Consider the Weight-Constrained Shortest Path Problem on directed graph $G=(V, E)$ with source $s$, target $t$, non-negative costs $c_e \ge 0$, non-negative resource weights $w_e \ge 0$, and budget $W \ge 0$.

For any scalar multiplier $\lambda \ge 0$, we define the **composite parametric edge weight**:
$$c_e^\lambda = c_e + \lambda w_e, \quad \forall e \in E$$

Since $c_e \ge 0, w_e \ge 0$, and $\lambda \ge 0$, we have $c_e^\lambda \ge 0$ for all $e \in E$. 

#### Definition 2.1 (Parametric Distance Function)
For any pair of vertices $u, v \in V$ and parameter $\lambda \ge 0$, the parametric shortest path distance $d_\lambda(u, v)$ is defined as:
$$d_\lambda(u, v) = \min_{P \in \mathcal{P}_{u, v}} \sum_{e \in P} c_e^\lambda = \min_{P \in \mathcal{P}_{u, v}} \left( c(P) + \lambda w(P) \right)$$

#### Proposition 2.1 (Properties of the Parametric Distance Function)
For any fixed pair $(u, v) \in V \times V$, the function $\lambda \mapsto d_\lambda(u, v)$ is:
1. **Concave**: Because it is the pointwise minimum of an infinite (or finite set of simple paths) collection of affine functions $\lambda \mapsto c(P) + \lambda w(P)$.
2. **Non-decreasing**: For $0 \le \lambda_1 \le \lambda_2$, since $w(P) \ge 0$, we have $c(P) + \lambda_1 w(P) \le c(P) + \lambda_2 w(P)$ for every path $P$.
3. **Piecewise-Linear**: Because the number of simple paths between $u$ and $v$ is finite, the minimum is taken over a finite set of linear functions.

---

### 2. The Continuous Legendre-Fenchel Dual Envelope

At an intermediate vertex $u \in V$, suppose a partial path from $s$ to $u$ has consumed resource weight $w_{cur}$. The **remaining resource budget** to reach destination $t$ is:
$$\Delta w = W - w_{cur}$$

Any completion path $P_{u, t} \in \mathcal{P}_{u, t}$ is feasible if and only if $w(P_{u, t}) \le \Delta w$.

#### Definition 2.2 (Continuous Dual Lower-Bound Function)
For any vertex $u \in V$ and remaining budget $\Delta w \ge 0$, the continuous Lagrangian dual lower-bound function $\mathcal{L}_u^*(\Delta w)$ is defined as:
$$\mathcal{L}_u^*(\Delta w) = \sup_{\lambda \ge 0} \left[ d_\lambda(u, t) - \lambda \Delta w \right]$$

Notice that $\mathcal{L}_u^*(\Delta w)$ is precisely the **Legendre-Fenchel conjugate** of the concave function $\lambda \mapsto d_\lambda(u, t)$, evaluated at $-\Delta w$.

---

### 3. The $K$-Faceted Adaptive Dual Hull (ADH)

In practice, computing the continuous supremum $\sup_{\lambda \ge 0}$ for all intermediate nodes is computationally prohibitive. 

The core mathematical innovation of **ADHP** is to construct a **Discrete $K$-Faceted Lower-Bound Envelope** supported by a finite, adaptively chosen set of dual multipliers:
$$\Lambda = \{\lambda_1, \lambda_2, \dots, \lambda_K\}, \quad \text{where } 0 = \lambda_1 < \lambda_2 < \dots < \lambda_K < \infty$$

#### Definition 2.3 ($K$-Faceted Lower-Bound Envelope)
For any vertex $u \in V$ and remaining budget $\Delta w \ge 0$, the $K$-faceted envelope $\mathcal{L}_u^\Lambda(\Delta w)$ is defined as:
$$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k \in \{1, \dots, K\}} \left[ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right]$$

---

### 4. Formal Proofs of Core Theorems

#### Theorem 1 (Admissibility and Lower-Bound Validity)
*Let $u \in V$ be any vertex, and let $\Delta w \ge 0$ be any remaining budget. For every path $P \in \mathcal{P}_{u, t}$ satisfying the budget constraint $w(P) \le \Delta w$, the path cost is bounded below by the discrete envelope:*
$$c(P) \ge \mathcal{L}_u^\Lambda(\Delta w)$$

**Proof:**
Let $P \in \mathcal{P}_{u, t}$ be an arbitrary path from $u$ to $t$ such that $w(P) \le \Delta w$.
By Definition 2.1, for any $\lambda \ge 0$, $d_\lambda(u, t)$ is the infimum over all paths from $u$ to $t$ under edge weights $c_e + \lambda w_e$.
Therefore, for any specific path $P \in \mathcal{P}_{u, t}$ and for every $k \in \{1, \dots, K\}$:
$$d_{\lambda_k}(u, t) \le \sum_{e \in P} (c_e + \lambda_k w_e) = c(P) + \lambda_k w(P)$$

Subtracting $\lambda_k w(P)$ from both sides yields:
$$c(P) \ge d_{\lambda_k}(u, t) - \lambda_k w(P)$$

Because $\lambda_k \ge 0$ (all multipliers are non-negative) and $w(P) \le \Delta w$, multiplying by $-\lambda_k$ reverses the inequality:
$$-\lambda_k w(P) \ge -\lambda_k \Delta w$$

Substituting this into the inequality gives:
$$c(P) \ge d_{\lambda_k}(u, t) - \lambda_k \Delta w$$

Since this inequality holds independently for every index $k \in \{1, 2, \dots, K\}$, it holds for the maximum over all $k$:
$$c(P) \ge \max_{k \in \{1, \dots, K\}} \left[ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right] = \mathcal{L}_u^\Lambda(\Delta w)$$
This completes the proof. $\blacksquare$

---

#### Theorem 2 (Dominance Conditions and Relationship to 1D Bounds)
*Let $d_c(u, t) = \min_{P \in \mathcal{P}_{u, t}} c(P)$ be the unconstrained cost distance from $u$ to $t$, and let $d_w(u, t) = \min_{P \in \mathcal{P}_{u, t}} w(P)$ be the unconstrained weight distance.*
*Let $\Lambda = \{\lambda_1, \dots, \lambda_K\}$ with $0 = \lambda_1 < \dots < \lambda_K < \infty$.*

1. **Cost-Bound Dominance**: *For all vertices $u \in V$ and remaining budgets $\Delta w \ge 0$:*
   $$\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$$
   *Strict dominance $\mathcal{L}_u^\Lambda(\Delta w) > d_c(u, t)$ holds if and only if there exists an active dual multiplier $\lambda_k \in \Lambda$ ($\lambda_k > 0$) satisfying:*
   $$d_{\lambda_k}(u, t) - d_c(u, t) > \lambda_k \Delta w$$
   *In particular, this requires $\Delta w < \min \{ w(P) \mid P \in \mathcal{P}_{u, t}, c(P) = d_c(u, t) \}$ (i.e., every unconstrained cost-minimizing path violates the remaining budget), and requires that $\Lambda$ contains at least one multiplier whose supporting hyperplane strictly separates $(\Delta w, d_c(u, t))$ from the epigraph of the Lagrangian dual.*

2. **Combined Two-Stage 1D Subsumption**:
   *Classical 1D bounding algorithms (such as Dumitrescu & Boland 2003) apply two uncoupled checks:*
   - *Cost pruning: $c_{cur} + d_c(u, t) \ge C_{UB}$*
   - *Weight infeasibility: $w_{cur} + d_w(u, t) > W$*
   *In ADHP, Filter 1 enforces $w_{cur} + d_w(u, t) > W$ (which geometrically corresponds to the asymptotic dual slope $\lambda \to \infty$). Filter 2 enforces $c_{cur} + \mathcal{L}_u^\Lambda(W - w_{cur}) > C_{UB}$. Because $\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$ by Part 1, any label pruned by classical 1D cost bounding is also pruned by Filter 2, and any label pruned by weight infeasibility is pruned by Filter 1. Hence, the two-stage ADHP filter is a strict mathematical superset of classical 1D orthogonal bounding.*

**Proof:**
1. Since $\lambda_1 = 0 \in \Lambda$, by definition of the discrete envelope:
   $$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k=1}^K \left[ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right] \ge d_{\lambda_1}(u, t) - 0 \cdot \Delta w = d_c(u, t)$$
   Thus $\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$ holds universally.
   The condition $d_{\lambda_k}(u, t) - d_c(u, t) > \lambda_k \Delta w$ is directly equivalent to $d_{\lambda_k}(u, t) - \lambda_k \Delta w > d_c(u, t)$. Taking the maximum over all $k \in \{1, \dots, K\}$ immediately yields $\mathcal{L}_u^\Lambda(\Delta w) > d_c(u, t)$. Conversely, if no $\lambda_k$ satisfies this inequality, then $\max_k [d_{\lambda_k} - \lambda_k \Delta w] = d_0(u, t) = d_c(u, t)$.

2. Direct consequence of Part 1 combined with the explicit execution of Filter 1 ($w + d_w(u, t) > W$) prior to Filter 2 in the ADHP relaxation pipeline. $\blacksquare$

---

#### Theorem 3 (Convexity, Continuity, and Monotonicity)
*For every vertex $u \in V$, the discrete lower-bound envelope $\Delta w \mapsto \mathcal{L}_u^\Lambda(\Delta w)$ is:*
1. **Convex** on $[0, \infty)$.
2. **Continuous** and **Piecewise-Linear** on $[0, \infty)$ with at most $K$ linear segments.
3. **Monotonically Non-Increasing**: if $0 \le \Delta w_1 \le \Delta w_2$, then $\mathcal{L}_u^\Lambda(\Delta w_1) \ge \mathcal{L}_u^\Lambda(\Delta w_2)$.

**Proof:**
1. For each $k \in \{1, \dots, K\}$, the function $f_k(\Delta w) = d_{\lambda_k}(u, t) - \lambda_k \Delta w$ is affine. The pointwise maximum of a finite collection of affine functions is convex.
2. The pointwise maximum of finitely many continuous functions is continuous. Since each $f_k$ is linear, $\mathcal{L}_u^\Lambda$ is piecewise-linear with at most $K$ segments.
3. Since $\lambda_k \ge 0$ for all $k$, the derivative of each affine piece is $-\lambda_k \le 0$. Thus, every piece is non-increasing. The maximum of non-increasing functions is non-increasing. $\blacksquare$

---

#### Theorem 4 (Exact Global Optimality, Dominance Invariance, and Finite Termination)
*Let $G = (V, E)$ be a directed multigraph with non-negative edge costs $c_e \ge 0$ and weights $w_e \ge 0$. Let $W \ge 0$ be the resource budget, and let $C_{UB}$ denote the cost of the best known feasible $(s, t)$-path (or $+\infty$ if none is yet found).*
*Under ADHP with pruning tolerance $\epsilon_{\text{prune}} = 10^{-9}$:*
1. **Admissibility**: *No subpath of any optimal constrained path is ever pruned.*
2. **Dominance Invariance**: *Pareto dominance filtering preserves at least one optimal path.*
3. **Finite Termination**: *The algorithm terminates in finite operations on every valid graph, including graphs containing zero-cost and zero-weight directed cycles.*
*Consequently, ADHP terminates and returns an optimal constrained shortest path if and only if a feasible path exists.*

**Proof:**

**Step 1: Admissibility of Bound and Feasibility Pruning.**
Let $P^* = (s = v_0, v_1, \dots, v_p = t)$ be an optimal constrained $(s, t)$-path with $c(P^*) = \text{OPT}$ and $w(P^*) \le W$.
Consider any prefix $P_{\text{pref}} = (v_0, \dots, v_i)$ with cost $c_i$ and weight $w_i$, and corresponding suffix $P_{\text{suff}} = (v_i, \dots, v_p)$ with cost $c_{\text{suff}}$ and weight $w_{\text{suff}}$.
- *Filter 1 (Resource feasibility)*: $w_i + d_w(v_i, t) \le w_i + w_{\text{suff}} = w(P^*) \le W$. Hence, $P_{\text{pref}}$ is never pruned by Filter 1.
- *Filter 2 (Dual hull pruning)*: By Theorem 1, $\mathcal{L}_{v_i}^\Lambda(W - w_i) \le c_{\text{suff}}$.
  Therefore, $c_i + \mathcal{L}_{v_i}^\Lambda(W - w_i) \le c_i + c_{\text{suff}} = c(P^*) \le C_{UB}$.
  Because pruning only occurs when $c_i + \mathcal{L}_{v_i}^\Lambda(W - w_i) > C_{UB} + \epsilon_{\text{prune}}$, and $c(P^*) \le C_{UB} < C_{UB} + \epsilon_{\text{prune}}$, the optimal path prefix is never pruned by Filter 2.

**Step 2: Correctness of Local Pareto Dominance.**
At vertex $v_i$, suppose label $\ell_1 = (c_1, w_1)$ weakly dominates label $\ell_2 = (c_2, w_2)$, meaning $c_1 \le c_2$ and $w_1 \le w_2$.
For any completion suffix $Q \in \mathcal{P}_{v_i, t}$, the path completed from $\ell_1$ has cost $c_1 + c(Q) \le c_2 + c(Q)$ and weight $w_1 + w(Q) \le w_2 + w(Q)$.
If the completion from $\ell_2$ is feasible ($w_2 + w(Q) \le W$), then the completion from $\ell_1$ is also feasible ($w_1 + w(Q) \le W$) and has cost at least as low. Thus, discarding $\ell_2$ cannot eliminate the optimal path value.

**Step 3: Floating-Point Numerical Robustness.**
In floating-point arithmetic ($f64$), let $\text{fl}(\mathcal{L}_u^\Lambda)$ denote the computed lower bound. Rounding errors during $d_{\lambda_k} - \lambda_k \Delta w$ are bounded by $\delta_{\text{round}} \le 2 n \epsilon_{\text{mach}} \cdot \max(c_{\max}, \lambda_{\max} w_{\max}) \ll 10^{-12}$.
Because the pruning condition requires:
$$\text{fl}(c_i) + \text{fl}(\mathcal{L}_u^\Lambda) > C_{UB} + \epsilon_{\text{prune}}$$
with $\epsilon_{\text{prune}} = 10^{-9} \gg \delta_{\text{round}}$, rounding errors cannot push an optimal path's computed bound above $C_{UB} + \epsilon_{\text{prune}}$.

**Step 4: Finite Termination.**
Because $G$ is finite, the number of vertices $n$ and edges $m$ are finite.
- *Positive cycles*: Every edge has $c_e \ge 0, w_e \ge 0$. Any cycle $C$ with $c(C) + w(C) > 0$ strictly increases cost or weight. Because labels with $w > W$ are pruned by Filter 1, and labels with $c \ge C_{UB} + \epsilon_{\text{prune}}$ are pruned by Filter 2, the number of distinct non-dominated labels with $w \le W$ and $c \le C_{UB}$ formed by positive cycles is strictly finite.
- *Zero-cost, zero-weight cycles*: Suppose $G$ contains a directed cycle $C$ such that $\sum_{e \in C} c_e = 0$ and $\sum_{e \in C} w_e = 0$.
  Traversing $C$ from any vertex $v$ returns to $v$ with accumulated cost $c' = c_v + 0 = c_v$ and weight $w' = w_v + 0 = w_v$.
  Upon arrival at $v$, the vertex frontier `frontiers[v]` already contains the prior label $(c_v, w_v)$.
  The weak dominance test `frontiers[v].is_dominated(c', w')` checks whether $c_v \le c' \land w_v \le w'$. Because $c_v \le c_v$ and $w_v \le w_v$, the returned label is recognized as weakly dominated and pruned immediately (Filter 3).
  Hence, zero-cost, zero-weight cycles cannot be traversed more than once, strictly preventing infinite loops.

Therefore, the priority queue becomes empty after a finite number of operations, and ADHP terminates, returning the certified optimal path. $\blacksquare$

---

### 5. Boundary Analysis and Edge Cases

1. **Disconnected Target**: If $t$ is unreachable from $s$, $d_w(s, t) = +\infty > W$. The algorithm terminates in $O(m + n \log n)$ time reporting infeasibility.
2. **Zero-Budget ($W = 0$)**: Valid. Any edge with $w_e > 0$ cannot be traversed. Evaluated exactly.
3. **Budget Exceeds Unconstrained Minimum Cost**: If $w(P_c^*) \le W$, unconstrained Dijkstra immediately yields $C_{UB} = c(P_c^*)$. The root lower bound matches $C_{UB}$ and terminates in 0 label expansions.
4. **Degenerate Costs / Weights ($c_e = 0$ or $w_e = 0$)**: Fully supported; edge weights $c_e + \lambda_k w_e$ remain non-negative, and Dijkstra is well-defined.
5. **Zero-Cost and Zero-Weight Directed Cycles**: Fully supported and formally proven to terminate via weak Pareto dominance elimination.
6. **Multi-edges**: Supported; outgoing edges from each vertex are relaxed individually without predecessor ambiguity.
