# MATHEMATICAL FOUNDATIONS & FORMAL PROOFS
## Adaptive Dual Hull Pruning (ADHP) for the Constrained Shortest Path Problem

**Author**: Rajve  
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
$$\mathcal{L}_u^*(\Delta w) = \sup_{\lambda \ge 0} \left\{ d_\lambda(u, t) - \lambda \Delta w \right\}$$

Notice that $\mathcal{L}_u^*(\Delta w)$ is precisely the **Legendre-Fenchel conjugate** of the concave function $\lambda \mapsto d_\lambda(u, t)$, evaluated at $-\Delta w$.

---

### 3. The $K$-Faceted Adaptive Dual Hull (ADH)

In practice, computing the continuous supremum $\sup_{\lambda \ge 0}$ for all intermediate nodes is computationally prohibitive. 

The core mathematical innovation of **ADHP** is to construct a **Discrete $K$-Faceted Lower-Bound Envelope** supported by a finite, adaptively chosen set of dual multipliers:
$$\Lambda = \{\lambda_1, \lambda_2, \dots, \lambda_K\}, \quad \text{where } 0 = \lambda_1 < \lambda_2 < \dots < \lambda_K < \infty$$

#### Definition 2.3 ($K$-Faceted Lower-Bound Envelope)
For any vertex $u \in V$ and remaining budget $\Delta w \ge 0$, the $K$-faceted envelope $\mathcal{L}_u^\Lambda(\Delta w)$ is defined as:
$$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k \in \{1, \dots, K\}} \left\{ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right\}$$

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
$$c(P) \ge \max_{k \in \{1, \dots, K\}} \left\{ d_{\lambda_k}(u, t) - \lambda_k \Delta w \right\} = \mathcal{L}_u^\Lambda(\Delta w)$$
This completes the proof. $\blacksquare$

---

#### Theorem 2 (Strict Dominance over Classical 1-Dimensional Bounds)
*Let $d_c(u, t) = \min_{P \in \mathcal{P}_{u, t}} c(P)$ be the unconstrained cost distance from $u$ to $t$.*
*If $0 = \lambda_1 \in \Lambda$, then:*
1. $\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$ *for all $\Delta w \ge 0$.*
2. *Whenever the cost-minimizing path from $u$ to $t$ has resource consumption $w(P_c^*) > \Delta w$, and there exists $\lambda_k \in \Lambda$ such that $\lambda_k > 0$ and $d_{\lambda_k}(u, t) - d_c(u, t) > \lambda_k \Delta w$, the bound is strictly tighter:*
   $$\mathcal{L}_u^\Lambda(\Delta w) > d_c(u, t)$$

**Proof:**
1. Since $\lambda_1 = 0 \in \Lambda$, by definition of the discrete envelope:
   $$\mathcal{L}_u^\Lambda(\Delta w) = \max_{k=1}^K \{ d_{\lambda_k}(u, t) - \lambda_k \Delta w \} \ge d_{\lambda_1}(u, t) - \lambda_1 \Delta w = d_0(u, t) - 0 \cdot \Delta w = d_c(u, t)$$
   Thus $\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$ holds universally.

2. Now suppose $w(P_c^*) > \Delta w$. For any path $P \in \mathcal{P}_{u, t}$, we have $c(P) + \lambda_k w(P) \ge d_{\lambda_k}(u, t)$.
   If there exists $\lambda_k > 0$ such that $d_{\lambda_k}(u, t) - \lambda_k \Delta w > d_c(u, t)$, then:
   $$\mathcal{L}_u^\Lambda(\Delta w) = \max_{j=1}^K \{ d_{\lambda_j}(u, t) - \lambda_j \Delta w \} \ge d_{\lambda_k}(u, t) - \lambda_k \Delta w > d_c(u, t)$$
   This proves strict dominance. $\blacksquare$

---

#### Theorem 3 (Convexity, Continuity, and Monotonicity)
*For every vertex $u \in V$, the discrete lower-bound envelope $\Delta w \mapsto \mathcal{L}_u^\Lambda(\Delta w)$ is:*
1. **Convex** on $[0, \infty)$.
2. **Continuous** and **Piecewise-Linear** on $[0, \infty)$ with at most $K$ linear segments.
3. **Monotonically Non-Increasing**: if $0 \le \Delta w_1 \le \Delta w_2$, then $\mathcal{L}_u^\Lambda(\Delta w_1) \ge \mathcal{L}_u^\Lambda(\Delta w_2)$.

**Proof:**
1. For each $k \in \{1, \dots, K\}$, the function $f_k(\Delta w) = d_{\lambda_k}(u, t) - \lambda_k \Delta w$ is an affine function of $\Delta w$. The pointwise maximum of a finite collection of affine functions is convex.
2. The pointwise maximum of finitely many continuous functions is continuous. Since each $f_k$ is linear, $\mathcal{L}_u^\Lambda$ is piecewise-linear with at most $K$ segments.
3. Since $\lambda_k \ge 0$ for all $k$, the derivative of each affine piece is $-\lambda_k \le 0$. Thus, every piece is non-increasing. The maximum of non-increasing functions is non-increasing. $\blacksquare$

---

#### Theorem 4 (Exact Global Optimality of ADHP)
*Let $C_{UB}$ denote the cost of the best known feasible $(s, t)$-path (or $+\infty$ if none is yet found).*
*During search, let a label $\ell = (u, c_{cur}, w_{cur})$ represent a path $P_{s, u}$.*
*If:*
$$c_{cur} + \mathcal{L}_u^\Lambda(W - w_{cur}) \ge C_{UB}$$
*then pruning label $\ell$ does not eliminate any path that could strictly improve upon $C_{UB}$.*
*Consequently, upon termination, ADHP returns a path $P^*$ that attains the exact global minimum $\text{OPT}(G, s, t, W)$.*

**Proof:**
Let $P_{s, u}$ be the prefix path represented by label $\ell$, with $c(P_{s, u}) = c_{cur}$ and $w(P_{s, u}) = w_{cur}$.
Suppose for contradiction that there exists a suffix completion path $P_{u, t} \in \mathcal{P}_{u, t}$ such that the concatenated path $P = P_{s, u} \circ P_{u, t}$ is feasible and strictly better than the current best solution:
$$w(P) = w_{cur} + w(P_{u, t}) \le W \iff w(P_{u, t}) \le W - w_{cur}$$
$$c(P) = c_{cur} + c(P_{u, t}) < C_{UB}$$

Since $w(P_{u, t}) \le W - w_{cur}$, by Theorem 1 with $\Delta w = W - w_{cur}$:
$$c(P_{u, t}) \ge \mathcal{L}_u^\Lambda(W - w_{cur})$$

Adding $c_{cur}$ to both sides:
$$c(P) = c_{cur} + c(P_{u, t}) \ge c_{cur} + \mathcal{L}_u^\Lambda(W - w_{cur})$$

However, the pruning condition asserts:
$$c_{cur} + \mathcal{L}_u^\Lambda(W - w_{cur}) \ge C_{UB}$$

Combining these inequalities:
$$c(P) \ge C_{UB}$$
This directly contradicts $c(P) < C_{UB}$.
Therefore, no completion of label $\ell$ can strictly improve upon $C_{UB}$, and pruning $\ell$ is provably exact.
Since no optimal path prefix is ever pruned, and since all costs are non-negative and the state space is finite, the algorithm must terminate and discover an optimal path $P^*$ attaining $\text{OPT}$. $\blacksquare$

---

### 5. Boundary Analysis and Edge Cases

1. **Disconnected Target**: If $t$ is unreachable from $s$, $d_w(s, t) = +\infty > W$. The algorithm terminates in $O(m + n \log n)$ time reporting infeasibility.
2. **Zero-Budget ($W = 0$)**: Valid. Any edge with $w_e > 0$ cannot be traversed. Evaluated exactly.
3. **Budget Exceeds Unconstrained Minimum Cost**: If $w(P_c^*) \le W$, unconstrained Dijkstra immediately yields $C_{UB} = c(P_c^*)$. The root lower bound matches $C_{UB}$ and terminates in 0 label expansions.
4. **Degenerate Costs / Weights ($c_e = 0$ or $w_e = 0$)**: Fully supported; edge weights $c_e + \lambda_k w_e$ remain non-negative, and Dijkstra is well-defined.
5. **Multi-edges and Cycles**: Directed cycles have non-negative cost and weight, preventing negative cycle anomalies.
