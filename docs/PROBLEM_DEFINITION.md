# PROBLEM DEFINITION & MATHEMATICAL SPECIFICATION
## Exact Weight-Constrained Shortest Path Problem (CSPP)

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/PROBLEM_DEFINITION.md`  

---

### 1. Formal Problem Statement

Let $G = (V, E)$ be a directed graph, where:
- $V$ is a finite set of vertices with $|V| = n$.
- $E \subseteq V \times V$ is a finite set of directed edges with $|E| = m$.
- $s \in V$ is the designated source vertex.
- $t \in V$ is the designated destination (target) vertex, with $s \neq t$.

We are given two non-negative weight functions on the edge set $E$:
1. **Cost function**: $c: E \to \mathbb{R}_{\ge 0}$, where $c(e)$ represents the traversal cost, monetary expenditure, or primary objective value of edge $e \in E$.
2. **Resource consumption function**: $w: E \to \mathbb{R}_{\ge 0}$, where $w(e)$ represents the delay, travel time, battery expenditure, or resource consumption of edge $e \in E$.

We are given a non-negative scalar budget:
- $W \in \mathbb{R}_{\ge 0}$, representing the maximum allowable cumulative resource consumption.

#### Definition 1.1 (Path and Simple Path)
A directed path $P$ from $u$ to $v$ in $G$ is a sequence of edges $P = (e_1, e_2, \dots, e_k)$ where $e_i = (v_{i-1}, v_i) \in E$ for $i \in \{1, \dots, k\}$, with $v_0 = u$ and $v_k = v$. The path is **simple** if all vertices $v_0, v_1, \dots, v_k$ are distinct.

We denote by $\mathcal{P}_{u, v}$ the set of all directed paths from $u$ to $v$ in $G$.

#### Definition 1.2 (Path Cost and Path Resource Consumption)
For any path $P \in \mathcal{P}_{u, v}$, its cumulative cost $c(P)$ and cumulative resource consumption $w(P)$ are defined additively:
$$c(P) = \sum_{e \in P} c(e), \qquad w(P) = \sum_{e \in P} w(e)$$

#### Definition 1.3 (Feasibility)
A path $P \in \mathcal{P}_{s, t}$ is **feasible** with respect to budget $W$ if and only if:
$$w(P) \le W$$
The set of all feasible $(s, t)$-paths is denoted:
$$\mathcal{P}_{s, t}^{\le W} = \{ P \in \mathcal{P}_{s, t} : w(P) \le W \}$$

---

### 2. The Optimization Problem

The **Weight-Constrained Shortest Path Problem (CSPP)** is formulated as:
$$\text{OPT}(G, s, t, W) = \min_{P \in \mathcal{P}_{s, t}^{\le W}} c(P)$$

#### Output Specification
An exact solver must return:
1. If $\mathcal{P}_{s, t}^{\le W} \neq \emptyset$: an optimal path $P^* \in \mathcal{P}_{s, t}^{\le W}$ such that $c(P^*) = \text{OPT}(G, s, t, W)$, along with its exact cost $c(P^*)$ and weight $w(P^*)$.
2. If $\mathcal{P}_{s, t}^{\le W} = \emptyset$: an authoritative certificate of infeasibility ($\text{OPT} = +\infty$).

---

### 3. Structural Properties and Axiomatic Assumptions

1. **Non-negativity**: $c(e) \ge 0$ and $w(e) \ge 0$ for all $e \in E$.
   - *Consequence*: Any path containing a directed cycle $C$ satisfies $c(P) \ge c(P \setminus C)$ and $w(P) \ge w(P \setminus C)$. Thus, the set of simple paths contains at least one optimal solution.
2. **Deterministic Inputs**: All costs, weights, and budgets are deterministic real numbers (represented computationally as 64-bit IEEE floating-point numbers or exact rational numbers).
3. **Graph Topology**: $G$ may contain cycles, multi-edges, and arbitrary degree distributions.
4. **Weak NP-Hardness**: CSPP is weakly NP-hard (Garey & Johnson 1979). When edge weights are integers, it is solvable in $O(m \cdot W)$ pseudo-polynomial time. For general non-negative real weights, it is NP-hard.

---

### 4. Baseline Bounds and Extreme Points

Let $d_c(u, v) = \min_{P \in \mathcal{P}_{u, v}} c(P)$ be the unconstrained shortest cost distance from $u$ to $v$.
Let $d_w(u, v) = \min_{P \in \mathcal{P}_{u, v}} w(P)$ be the unconstrained minimum weight distance from $u$ to $v$.

- **Trivial Infeasibility Condition**: If $d_w(s, t) > W$, then $\mathcal{P}_{s, t}^{\le W} = \emptyset$.
- **Trivial Optimality Condition**: If the cost-minimizing path $P_c^* \in \arg\min_{P \in \mathcal{P}_{s, t}} c(P)$ satisfies $w(P_c^*) \le W$, then $P_c^*$ is immediately optimal: $\text{OPT} = c(P_c^*)$.
- **Non-Trivial Regime**: The interesting and computationally challenging regime occurs when:
  $$d_w(s, t) \le W < w(P_c^*)$$
  In this regime, the unconstrained cost-minimizing path violates the budget, and the unconstrained weight-minimizing path incurs sub-optimal cost. The optimal solution is an intermediate Pareto-critical path.
