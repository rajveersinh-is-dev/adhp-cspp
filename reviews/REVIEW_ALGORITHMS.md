# ADVERSARIAL PEER REVIEW: ALGORITHMS & COMPLEXITY
## Reviewer B (Algorithms and Theoretical Complexity Persona)

**Evaluation Date**: October 2026  
**Document Reviewed**: `docs/ALGORITHM_SPECIFICATION.md`, `docs/COMPLEXITY_ANALYSIS.md`, `research/NOVELTY_ASSESSMENT.md`  
**Overall Algorithmic Verdict**: STRONG CONTRIBUTION; LEVEL B/C EMPIRICAL AND STRUCTURAL NOVELTY  

---

### 1. Algorithmic Novelty Assessment

The paper introduces **Adaptive Dual Hull Pruning (ADHP)** for the NP-hard Weight-Constrained Shortest Path Problem. 

Prior work in the literature falls into three paradigms:
1. Pure Label-Setting (Martins 1984, Desrochers & Soumis 1988): no lower bounds; vulnerable to combinatorial explosion.
2. 1D Orthogonal Bounding (Dumitrescu & Boland 2003, Lozano & Medaglia 2013 Pulse): uses only extreme projections $d_c(u, t)$ and $d_w(u, t)$ (corresponding to $\lambda = 0$ and $\lambda = \infty$).
3. Single-Multiplier Global Lagrangian Bounding (Carlyle & Wood 2008): solves LARAC once for root $(s, t)$ and applies a static slope $\lambda^*_{s,t}$.

**Novelty Verdict**: 
The synthesis of an adaptive multi-point discrete Legendre-Fenchel envelope $\mathcal{L}_u^\Lambda(\Delta w)$ constructed across all vertices via $K$ reverse Dijkstra trees is a genuine algorithmic innovation. It addresses a recognized 20-year blind spot in CSPP: intermediate vertices have localized Pareto trade-off slopes that cannot be captured by the root multiplier $\lambda^*_{s,t}$ alone.

---

### 2. Algorithmic Critique & Required Tightening

#### Critique B1: Worst-Case Complexity Claim
- *Issue*: The author states complexity as $O(K(m + n \log n) + m \cdot |\mathcal{P}_{\text{filtered}}|)$. 
- *Challenge*: Since CSPP is NP-hard, what is the worst-case bound on $|\mathcal{P}_{\text{filtered}}|$?
- *Analysis*: In the worst-case, there exist pathological graph constructions (e.g. series-parallel graphs with exponentially many Pareto-optimal paths lying on a strictly convex arc) where even an exact convex envelope does not prune all labels. Thus $|\mathcal{P}_{\text{filtered}}|$ can still be $O(2^{n/2})$ in the theoretical worst-case.
- *Requirement*: The paper must explicitly acknowledge that ADHP does not alter the NP-hardness of the problem and that worst-case theoretical complexity remains exponential in $n$ (or pseudo-polynomial $O(mW)$ for integral weights). The contribution is output-sensitive state space suppression and practical dominance on combinatorial bottleneck instances.

#### Critique B2: Relationship to Bi-Objective A* and Heuristic Search
- *Issue*: How does ADHP compare conceptually to modern Bi-Objective $A^*$ (BOA*) algorithms (Hernandez et al. 2023)?
- *Analysis*: BOA* uses $g_1(u) + h_1(u)$ and $g_2(u) + h_2(u)$ with scalar heuristics. ADHP goes beyond scalar heuristics by constructing a multi-hyperplane convex lower bound that links $g_1$ and $g_2$ directly through the dual slope $\lambda$. This connection should be noted in Related Work.

#### Critique B3: Parameter Sensitivity ($K$)
- *Issue*: How sensitive is the algorithm to the choice of $K$?
- *Finding*: The ablation study in `research/BENCHMARK_REPORT.md` nicely shows that $K \in \{3, 5, 8\}$ provides near-identical pruning power, with $K=5$ yielding the optimal balance between tree preprocessing and label expansion. The paper should recommend $K=5$ as the default parameter.

---

### 3. Algorithmic Score: 9.3 / 10

The mechanism is mathematically sound, cleanly differentiated from prior art, and represents a real algorithmic advance in constrained routing.
