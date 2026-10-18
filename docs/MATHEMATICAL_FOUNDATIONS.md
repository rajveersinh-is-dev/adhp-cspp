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
#### Theorem 4 (Exact Global Optimality, Search Exhaustiveness, and Finite Termination)
Let $G = (V, E)$ be a directed multigraph with $c(e) \ge 0, w(e) \ge 0$. Let $W \ge 0$ be the resource budget. With relative pruning tolerance $\epsilon_{\text{prune}} = 10^{-9}$ and relative feasibility tolerance $\epsilon_{\text{feas}} = 10^{-9}$, ADHP terminates in finite time and returns an optimal constrained shortest path $P^*$ if one exists, or certifies infeasibility.

---

##### Complete Mathematical Proof

**Part 1: Search Exhaustiveness by Path-Prefix Induction.**
Let $\mathcal{P}_{s, t}^{\text{feas}} = \{ P \in \mathcal{P}_{s, t} : w(P) \le W \}$ denote the set of feasible $(s, t)$-paths. If $\mathcal{P}_{s, t}^{\text{feas}} = \emptyset$, unconstrained minimum-weight Dijkstra finds $d_w(s, t) > W + \max(1.0, W)\epsilon_{\text{feas}}$, and the algorithm immediately returns $\text{Infeasible}$ at initialization, which is certified correct.

Now assume $\mathcal{P}_{s, t}^{\text{feas}} \ne \emptyset$. There exists at least one optimal path $P^* = (s = v_0, v_1, \dots, v_k = t)$ achieving:
$$c(P^*) = \min_{P \in \mathcal{P}_{s, t}^{\text{feas}}} c(P) \le C_{UB}$$
We prove by induction on prefix length $i \in \{0, 1, \dots, k\}$ that for every optimal path $P^*$, either the exact prefix label corresponding to $P^*[s \to v_i]$ is settled, or an alternative prefix label $\ell'$ is settled at $v_i$ that weakly Pareto-dominates $P^*[s \to v_i]$:

1. **Base Case ($i = 0$)**:
   At source $s = v_0$, the initial label $\ell_0 = (0, 0)$ is generated and pushed to the priority queue. It represents the empty prefix $P^*[s \to s]$ with cost $0$ and weight $0$. The base case holds trivially.

2. **Inductive Step ($i \to i+1$)**:
   Suppose the induction hypothesis holds for prefix $P^*[s \to v_i]$: a label $\ell_i = (c_i, w_i)$ has been popped from the priority queue at vertex $v_i$ such that $c_i \le c(P^*[s \to v_i])$ and $w_i \le w(P^*[s \to v_i])$.
   When the solver relaxes outgoing edge $e = (v_i, v_{i+1}) \in P^*$, it generates candidate label $\ell_{i+1} = (c_i + c(e), w_i + w(e))$.
   We verify that $\ell_{i+1}$ cannot be pruned by any of ADHP's three filters:
   - **Filter 1 (Feasibility)**: By the inductive hypothesis, $w_i \le w(P^*[s \to v_i])$. The reverse minimum-weight distance satisfies $d_w(v_{i+1}, t) \le w(P^*[v_{i+1} \to t])$. Summing yields:
     $$w_{i+1} + d_w(v_{i+1}, t) = w_i + w(e) + d_w(v_{i+1}, t) \le w(P^*[s \to v_i]) + w(e) + w(P^*[v_{i+1} \to t]) = w(P^*) \le W$$
     With relative tolerance $W + \max(1.0, W)\epsilon_{\text{feas}}$, Filter 1 never prunes $\ell_{i+1}$.
   - **Filter 2 (Dual Envelope Lower Bound)**: By Theorem 1 (Admissibility), the remaining suffix $P^*[v_{i+1} \to t]$ has weight $w(P^*[v_{i+1} \to t]) \le W - w(P^*[s \to v_{i+1}]) \le W - w_{i+1} = \Delta w_{i+1}$.
     Hence:
     $$\mathcal{L}_{v_{i+1}}^\Lambda(\Delta w_{i+1}) \le c(P^*[v_{i+1} \to t])$$
     Adding $c_{i+1} \le c(P^*[s \to v_{i+1}])$:
     $$c_{i+1} + \mathcal{L}_{v_{i+1}}^\Lambda(\Delta w_{i+1}) \le c(P^*[s \to v_{i+1}]) + c(P^*[v_{i+1} \to t]) = c(P^*) \le C_{UB}$$
     Because Filter 2 prunes only when $c_{i+1} + \mathcal{L}_{v_{i+1}}^\Lambda(\Delta w_{i+1}) > C_{UB} + \max(1.0, C_{UB})\epsilon_{\text{prune}}$, $\ell_{i+1}$ is never pruned by Filter 2.
   - **Filter 3 (Local Pareto Frontier Dominance)**: At vertex $v_{i+1}$, either $\ell_{i+1}$ is non-dominated and successfully inserted into the frontier and priority queue, OR there already exists an earlier label $\tilde{\ell} = (\tilde{c}, \tilde{w})$ in `frontiers[v_{i+1}]` such that $\tilde{c} \le c_{i+1} \le c(P^*[s \to v_{i+1}])$ and $\tilde{w} \le w_{i+1} \le w(P^*[s \to v_{i+1}])$.
     In the latter case, $\tilde{\ell}$ is concatenated with suffix $P^*[v_{i+1} \to t]$ to produce a complete $(s, t)$-path with cost $\tilde{c} + c(P^*[v_{i+1} \to t]) \le c(P^*)$ and weight $\tilde{w} + w(P^*[v_{i+1} \to t]) \le w(P^*) \le W$.
     Thus, replacing the prefix with $\tilde{\ell}$ preserves the existence of an optimal path.

3. **Conclusion of Induction ($i = k$)**:
   At destination vertex $v_k = t$, an optimal label with cost $\le c(P^*)$ and weight $\le W$ must enter `frontiers[t]`. Since candidate solutions update $C_{UB}$ whenever a feasible label reaches $t$, the final returned path achieves cost exactly $c(P^*)$. Search exhaustiveness is therefore proved.

---

**Part 2: Floating-Point Roundoff and Relative Tolerance Analysis.**
In IEEE 754 double precision (`f64`), the machine epsilon is $\epsilon_{\text{mach}} \approx 2.22 \times 10^{-16}$.
For an arbitrary path $P$ with length $|P| \le n$, the accumulated floating-point error in summing edge costs and weights satisfies Higham's standard summation bound:
$$|\text{fl}(c(P)) - c(P)| \le \gamma_n c(P), \quad |\text{fl}(w(P)) - w(P)| \le \gamma_n w(P)$$
where $\gamma_n = \frac{n \epsilon_{\text{mach}}}{1 - n \epsilon_{\text{mach}}}$. For $n \le 10^5$, $\gamma_n \le 2.3 \times 10^{-11}$.
Furthermore, in evaluating the discrete envelope $\mathcal{L}_u^\Lambda(\Delta w) = \max_{k} [d_{\lambda_k}(u, t) - \lambda_k \Delta w]$, the subtractive error is bounded by $\gamma_3 (|d_{\lambda_k}| + \lambda_k |\Delta w|)$.
By employing relative scaling:
$$\text{tol}_{\text{feas}}(W) = \max(1.0, |W|) \cdot 10^{-9}, \quad \text{tol}_{\text{prune}}(C_{UB}) = \max(1.0, |C_{UB}|) \cdot 10^{-9}$$
we guarantee that:
$$\gamma_n \cdot \max(c, w) \ll 10^{-9} \cdot \max(1.0, c, w)$$
for all problem instances up to $n = 100,000$ and arbitrary cost/weight magnitudes (including $10^9$).
Additionally, decimal representations like $0.1 + 0.2 = 0.30000000000000004$ exceed $0.3$ by only $4 \times 10^{-17}$, which is strictly absorbed by $0.3 \times 10^{-9} = 3 \times 10^{-10}$, eliminating false pruning on decimal inputs.

---

**Part 3: Finite Termination.**
1. **Graph Finiteness**: $V$ and $E$ are finite.
2. **Positive-Cost or Positive-Weight Cycles**: Any cycle $C$ with $c(C) + w(C) > 0$ strictly increases cost or weight upon each traversal. Because Filter 1 prunes labels when $w > W + \text{tol}_{\text{feas}}$, and Filter 2 prunes labels when $c > C_{UB} + \text{tol}_{\text{prune}}$, no infinite sequence of labels can be generated by repeatedly traversing cycles with positive cost or weight.
3. **Zero-Cost and Zero-Weight Directed Cycles**: Suppose $G$ contains a cycle $C$ such that $\sum_{e \in C} c(e) = 0$ and $\sum_{e \in C} w(e) = 0$.
   Traversing $C$ from vertex $v$ returns to $v$ with identical cost $c_v$ and weight $w_v$.
   The frontier at $v$ already contains $(c_v, w_v)$. Filter 3 checks weak Pareto dominance:
   $$c_v \le c_v \quad \land \quad w_v \le w_v$$
   which evaluates to `true`. Thus, the returned label is immediately discarded by Filter 3 and never enqueued.
   Zero-cost, zero-weight cycles cannot be traversed more than once.

Because the priority queue only receives finite labels and each pop removes an element without infinite cycling, the queue becomes empty in finite steps. ADHP terminates. $\blacksquare$

---

### 5. Boundary Analysis and Edge Cases

1. **Disconnected Target**: If $t$ is unreachable from $s$, $d_w(s, t) = +\infty > W$. The algorithm terminates in $O(m + n \log n)$ time reporting infeasibility.
2. **Zero-Budget ($W = 0$)**: Valid. Any edge with $w_e > 0$ cannot be traversed unless weight is 0. Evaluated exactly.
3. **Budget Exceeds Unconstrained Minimum Cost**: If $w(P_c^*) \le W$, unconstrained Dijkstra immediately yields $C_{UB} = c(P_c^*)$. The root lower bound matches $C_{UB}$ and terminates in 0 label expansions.
4. **Degenerate Costs / Weights ($c_e = 0$ or $w_e = 0$)**: Fully supported; edge weights $c_e + \lambda_k w_e$ remain non-negative, and Dijkstra is well-defined.
5. **Zero-Cost and Zero-Weight Directed Cycles**: Fully supported and formally proven to terminate via weak Pareto dominance elimination.
6. **Multi-edges / Parallel Edges**: Fully supported. Outgoing edges are identified by unique `edge_id`, and `CsppSolution` records the exact `edge_path: Vec<usize>` traversed, eliminating multi-edge path evaluation ambiguity.
7. **Invalid Inputs**: Strict validation catches NaN, non-finite values, negative budgets, and out-of-bounds vertex indices, safely returning `Infeasible`.

