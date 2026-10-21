# RESEARCH AUDIT & COMPREHENSIVE REPOSITORY BASELINE
## ADHP-CSPP: Post-Audit State Assessment, Vulnerabilities, and Strategic Research Plan

**Author**: Rajveersinh Vishal Pardeshi  
**Repository**: `https://github.com/rajveersinh-is-dev/adhp-cspp`  
**Date**: October 2026  
**Document**: `docs/RESEARCH_AUDIT.md`  

---

### 1. Current Architecture and Algorithmic Flow

The repository currently provides two primary solver engines and four baseline algorithms for the single-resource Weight-Constrained Shortest Path Problem (CSPP):

1. **Floating-Point Engine (`AdhpSolver` in `src/adhp.rs`)**:
   - Operates on `DirectedGraph` with `f64` edge traversal costs $c(e) \ge 0$ and resource weights $w(e) \ge 0$, subject to maximum resource budget $W \ge 0$.
   - **Step 1 (Backward Weight Preprocessing)**: Runs reverse Dijkstra on reversed graph $G^R$ from target $t$ with weight metric to compute $d_w(u, t)$ for all $u \in V$. If $d_w(s, t) > W$, certifies infeasibility immediately. If reachable, reconstructs forward path $P_w(s, t)$ to initialize the global upper bound $C_{\text{UB}} = c(P_w)$.
   - **Step 2 (Backward Cost Preprocessing)**: Runs reverse Dijkstra on $G^R$ from $t$ with cost metric ($\lambda_1 = 0$) to compute $d_c(u, t)$. If $w(P_c) \le W$, returns $P_c(s, t)$ as globally optimal in $O(m + n \log n)$ time.
   - **Step 3 (Adaptive Multiplier Bisection)**: Identifies dual slope breakpoints $\lambda_{mid} = \frac{c_r - c_l}{w_l - w_r}$ via recursive bisection. Uses backward tree duality (`dijkstra_backward_tree`) to simultaneously obtain reverse distance vector $d_{\lambda_{mid}}(\cdot, t)$ and forward candidate path $P_{mid}(s, t)$ in a single pass. Adopts the facet if marginal lower bound improvement at source $\delta > 0.02$.
   - **Step 4 (Forward Label Setting with Multi-Facet Pruning)**: Expands labels in min-heap ordered by $c_u + \mathcal{L}_u^\Lambda(W - w_u)$. Enforces three-stage pruning:
     - Filter 1: $w_u + w(e) + d_w(v, t) \le W + \varepsilon_{\text{feas}}$ (Resource Feasibility).
     - Filter 2: $c_u + c(e) + \mathcal{L}_v^\Lambda(W - (w_u + w(e))) \le C_{\text{UB}} + \varepsilon_{\text{prune}}$ (Dual Hull Bound).
     - Filter 3: Strict mathematical Pareto dominance via `VertexFrontier::is_dominated` in $O(\log |F|)$ time.

2. **Exact Integer Engine (`IntAdhpSolver` in `src/exact.rs`)**:
   - Operates on `IntDirectedGraph` with `u64` costs and weights, rational multipliers $\lambda = \frac{p}{q}$, and exact ceiling lower bounds $\lceil \mathcal{L}_u^\Lambda(\Delta w) \rceil = \max_k \lceil \frac{q_k \cdot d_{\lambda_k}(u, t) - p_k \cdot \Delta w}{q_k} \rceil$.
   - Intended for zero-tolerance exact discrete optimization.

3. **Baseline Solvers (`src/baselines/`)**:
   - `MartinsSolver`: Standard multi-label bicriteria Dijkstra (no preprocessing bounds).
   - `DumitrescuBolandSolver`: 1D orthogonal distance bounding ($d_c, d_w$).
   - `CarlyleWoodSolver`: Single-multiplier Lagrangian bounding via iterative LARAC preprocessing.
   - `PulseSolver`: Pruning-based depth-first search (Lozano & Medaglia 2013).

---

### 2. Mathematical Assumptions and Supported Input Domain

1. **Graph Structure**:
   - Directed multigraph $G = (V, E)$, $|V| = n$, $|E| = m$.
   - Non-negative edge costs $c(e) \ge 0$ and resource weights $w(e) \ge 0$.
   - Non-negative budget $W \ge 0$.
   - Distinct source $s$ and target $t$ (with trivial $s=t$ handled as 0 cost, 0 weight).

2. **Theoretical Guarantees Claimed**:
   - **Theorem 0 (Backward-Centric Tree Duality)**: Reverse Dijkstra on $G^R$ from $t$ with metric $c + \lambda w$ produces $d_\lambda(u, t)$ for all $u \in V$ and generates $P_\lambda(s, t)$ in forward order.
   - **Theorem 1 (Admissibility)**: For all $u \in V$ and $\Delta w \ge 0$, $\mathcal{L}_u^\Lambda(\Delta w) \le \min_{P \in \mathcal{P}_{u, t}, w(P) \le \Delta w} c(P)$.
   - **Theorem 2 (Dominance & Subsumption)**: $\mathcal{L}_u^\Lambda(\Delta w) \ge d_c(u, t)$ universally, with equality iff $\forall \lambda_k > 0$, $d_{\lambda_k}(u, t) - d_c(u, t) \le \lambda_k \Delta w$.
   - **Theorem 3 (Convexity & Monotonicity)**: $\Delta w \mapsto \mathcal{L}_u^\Lambda(\Delta w)$ is continuous, convex, and non-increasing.
   - **Theorem 4 (Exact Integer Optimality & Finite-Precision Error Bounds)**: Prefix-induction optimality for integer graphs; Higham $O(n u)$ error bounds for IEEE 754 floats.

---

### 3. Historical Code-Level Audit of Numerical & Overflow Risks (Resolved in Commits 107b5ed / f4f2995)

> [!NOTE]
> **Historical Audit Record**: The vulnerabilities below were documented during the initial baseline audit. All four defects have been fully resolved in the codebase in commits `107b5ed` and `f4f2995` with verified 128-bit checked arithmetic, fail-closed error handling, IEEE-754 `total_cmp` ordering, and adversarial regression tests.

#### Defect 3.1: Composite-Metric Integer Overflow in `src/exact.rs` [HISTORICAL — RESOLVED]
- **Historical Hazard**: In early versions of `src/exact.rs`, composite metrics $c_e \cdot \text{den} + w_e \cdot \text{num}$ were computed using 64-bit integers (`u64`). When edge metrics exceeded $10^9$ with similar multipliers, $c_e \cdot \text{den}$ overflowed `u64::MAX`, returning `u64::MAX` and silently discarding valid edges during Dijkstra exploration.
- **Resolution (Commits 107b5ed / f4f2995)**: Upgraded `src/exact.rs` entirely to 128-bit checked arithmetic (`u128`, maximum $\approx 3.4 \times 10^{38}$). Overflows are strictly detected via `checked_mul` / `checked_add` with `?` propagation, returning `Option::None` or `SolutionStatus::ArithmeticOverflow` fail-closed rather than silently dropping edges. Verified by `test_composite_metric_overflow_regression` in `tests/correctness_tests.rs`.

#### Defect 3.2: Subtrahend Overflow in Integer Lower-Bound Evaluation [HISTORICAL — RESOLVED]
- **Historical Hazard**: If `rem_w.checked_mul(self.num)` overflowed `u64`, the function returned 0 for the subtrahend, yielding an overestimated lower bound $\lceil d / \text{den} \rceil$ and causing illegal pruning.
- **Resolution (Commits 107b5ed / f4f2995)**: Computed in 128-bit precision with exact ceiling integer arithmetic: $\lceil (q_k d_{\lambda_k} - p_k \Delta w) / q_k \rceil$. If terms overflow $u128$, the solver returns `SolutionStatus::ArithmeticOverflow`.

#### Defect 3.3: Floating-Point Subtraction Cancellation [HISTORICAL — RESOLVED]
- **Historical Hazard**: Cancellation error in $d_{\lambda_k}(u, t) - \lambda_k \Delta w$ on large graphs.
- **Resolution (Commits 107b5ed / f4f2995)**: Documented Higham summation bounds $O(n u)$ in `docs/KNOWN_LIMITATIONS.md`. Implemented conservative relative pruning tolerance $\epsilon = 10^{-9}$ certified $(\epsilon_{\text{feas}}, \epsilon_{\text{prune}})$-admissible. For zero-tolerance discrete optimization, `IntAdhpSolver` with checked rational arithmetic is provided.

#### Defect 3.4: Priority Queue Min-Heap Key Ordering on Float NaN [HISTORICAL — RESOLVED]
- **Historical Hazard**: `partial_cmp(&self.key).unwrap_or(Ordering::Equal)` could treat NaNs as equal.
- **Resolution (Commits 107b5ed / f4f2995)**: Replaced with strict IEEE 754 total ordering via `other.key.total_cmp(&self.key).then_with(...)` in `src/adhp.rs` and `src/hybrid.rs`. Furthermore, `CsppInstance::validate()` rejects non-finite costs, weights, or budgets upfront fail-closed with `SolutionStatus::UnsupportedInput`.

---

### 4. Audit of the Separate Branch & HiGHS ILP Verification Failure

In PR #1 (`ai-improve/hygiene-20261018-7461`, CI Run `39166197235`), the independent HiGHS ILP oracle step failed with:
```
TypeError: float() argument must be a string or a real number, not 'NoneType'
File "/home/runner/work/adhp-cspp/adhp-cspp/scripts/verify_against_ilp.py", line 162, in verify_instance
  adhp_cost = float(inst["adhp_cost"])
```
- **Root Cause**: The automated bot refactored `verify_against_ilp.py` by extracting a `verify_instance` helper function. Inside this helper, it executed `adhp_cost = float(inst["adhp_cost"])` unconditionally at the top of the function.
- Infeasible problem instances naturally serialize `adhp_cost: null`. In Python, `inst["adhp_cost"]` is `None`. Calling `float(None)` raises `TypeError`.
- **Verdict**: The failure was **100% a script refactoring defect** in the bot's PR, not a mathematical discrepancy in ADHP or a failure of the HiGHS solver. On `main`, `adhp_cost` is only evaluated when `adhp_status == "Optimal"`, which is why all 150/150 instances (100 float + 50 integer) pass cleanly on `main`.

---

### 5. Current Benchmark Methodology and Baseline Discrepancies

1. **Instance Accounting (Reconciled)**:
   - **25 Benchmark Configurations** (across 20 distinct problem instance sets):
     - 6 Anti-Correlated sizes ($n \in \{20, 40, 60, 80, 100, 150\}$).
     - 4 2D Mesh Grids ($4 \times 4, 6 \times 6, 8 \times 8, 10 \times 10$).
     - 4 Random Erdős–Rényi sizes ($n \in \{30, 60, 90, 120\}$).
     - 5 Budget Tightness values on $n=50$ anti-correlated graphs ($\alpha \in \{0.10, 0.25, 0.50, 0.75, 0.90\}$).
     - 6 Facet Ablation configurations ($K \in \{1, 2, 3, 5, 8, 12\}$ on controlled $n=70$ anti-correlated graphs).
   - **Evaluations & Deduplication**: 10 distinct random instances per configuration = **250 configuration-instance evaluations** total, comprising **200 distinct problem instances** (`adhp-canonical-v1`) and **164 distinct graph topologies** (`adhp-topology-v1`).
   - Evaluated with 5 discarded warmups and 3 timed trials per instance using in-process monotonic timing (`std::time::Instant`).

2. **Empirical Reality vs. Previous Narrative**:
   - **Where ADHP Wins in Total Runtime**: On **Grid $10 \times 10$ ($n = 100$)**, Adaptive Hybrid ADHP is the fastest solver overall at $19.97 \, \mu\text{s}$ (and fixed ADHP at $38.24 \, \mu\text{s}$ generating 105 labels), outperforming Dumitrescu-Boland ($32.22 \, \mu\text{s}$), Carlyle-Wood ($43.07 \, \mu\text{s}$), Pulse ($124.91 \, \mu\text{s}$, a $6.3\times$ speedup), and Martins ($163.82 \, \mu\text{s}$, an $8.2\times$ speedup).
   - **Where ADHP Loses in Total Runtime**: On dense anti-correlated graphs ($n \le 100$) and Random ER networks, backward Dijkstra preprocessing ($15$–$156 \, \mu\text{s}$) consumes 70–85% of total runtime. When the search space is small enough that unguided search (Martins) or 1D bounding (Dumitrescu-Boland) finishes in $< 50 \, \mu\text{s}$, those lightweight methods achieve lower total wall-clock times.
   - **Label Suppression**: ADHP suppresses candidate labels by **85% to 97%** relative to standard multi-label Dijkstra across all instances with severe cost-weight conflicts.

---

### 6. Implementation Status of High-Impact Improvements

| Rank | Potential Improvement | Target Dimension | Implementation Status |
|:---:|---|---|---|
| **1** | **128-Bit Overflow-Safe Arithmetic in Exact Engine** | Numerical Exactness & Purity | **COMPLETED**: Upgraded `src/exact.rs` to checked `u128` arithmetic; overflow returns `SolutionStatus::ArithmeticOverflow` fail-closed. |
| **2** | **Instance-Adaptive Hybrid Solver (`HybridAdhpSolver`)** | Total Wall-Clock Runtime | **COMPLETED**: Implemented in `src/hybrid.rs`; dynamically selects $K \in \{1, 2, 5\}$ in $O(1)$ time based on density $\rho$, duality gap $\gamma$, and budget factor $\alpha$. |
| **3** | **Bi-directional Dual Pruning (Forward Bound + Backward Envelope)** | Search Pruning Power | **Open Research**: Promising direction for future work; requires maintaining bi-directional frontiers. |
| **4** | **Input Domain Validation & Formal Error Handling** | Software Engineering & Usability | **COMPLETED**: Added `CsppInstance::validate()`, `IntDirectedGraph::validate()`, and `IntCsppInstance::validate()` returning `SolutionStatus::UnsupportedInput` fail-closed across all 7 solvers. |
| **5** | **Independent Brute-Force & DFS Exact Oracle** | Independent Verification | **COMPLETED**: Implemented `ExactDfsOracle` in `tests/correctness_tests.rs` and SciPy HiGHS MILP oracle in `scripts/verify_against_ilp.py` (150/150 verified). |
| **6** | **Redundant Facet Elimination & Dominance Filtering** | Preprocessing Efficiency | **Open Research**: Evaluated in ablation; diminishing returns beyond $K=3$ documented in `docs/KNOWN_LIMITATIONS.md`. |
| **7** | **Ablation Automation & Metric Traceability Script** | Scientific Reproducibility | **COMPLETED**: Built `scripts/verify_benchmarks.py` and `scripts/sync_published_claims.py` verifying all 800 claims fail-closed. |
| **8** | **Comprehensive Literature Matrix (`docs/RELATED_WORK.md`)** | Novelty & Academic Credibility | **COMPLETED**: Maintained in `docs/RELATED_WORK.md` citing Mehlhorn-Ziegelmann (2000), Handler-Zang (1980), Carlyle-Wood (2005), and Lozano-Medaglia (2013). |
| **9** | **Memory-Localized Cache-Oblivious Adjacency Storage** | Systems Performance | **Open Engineering**: Future optimization candidate for very large sparse graphs ($n > 10^5$). |
| **10** | **Publication Manuscript Overhaul (`paper/main.tex` & `paper/main.typ`)** | Dissemination Quality | **COMPLETED**: All benchmark numbers, theorems, and hybrid formulations fully synchronized with raw CSV data. |

---

### 7. Separation of Verified Facts, Hypotheses, and Unresolved Questions

#### A. Verified Facts (Established by Code & Data)
1. ADHP strictly subsumes classical 1D cost bounding (Filter 2 is pointwise $\ge d_c(u, t)$).
2. ADHP achieves dramatic label suppression (up to 97% fewer labels than Martins, up to 98% fewer than Pulse).
3. On planar grids ($10 \times 10$), Adaptive Hybrid ADHP is the fastest solver in total wall-clock time ($19.97 \, \mu\text{s}$ vs $32.22 \, \mu\text{s}$ for Dumitrescu-Boland, $38.24 \, \mu\text{s}$ for fixed ADHP, $43.07 \, \mu\text{s}$ for Carlyle-Wood, $124.91 \, \mu\text{s}$ for Pulse, and $163.82 \, \mu\text{s}$ for Martins).
4. On dense random and anti-correlated graphs with small $n$, ADHP's multi-tree preprocessing overhead exceeds the search time of unguided or 1D methods.
5. In `src/exact.rs`, composite metric overflow in `u64` can cause silent edge drops and false pruning.
6. The CI failure on PR #1 was caused by an unhandled `NoneType` bug in their Python script refactoring.

#### B. Hypotheses (To Be Tested & Measured)
1. **Hypothesis 1 (128-Bit Exactness)**: Upgrading `src/exact.rs` to checked `u128` arithmetic will eliminate all composite overflow risks for edge costs/weights up to $10^{15}$ while preserving identical execution speeds.
2. **Hypothesis 2 (Adaptive Hybrid Solver)**: An instance-adaptive hybrid solver that estimates whether the search phase will exceed preprocessing cost (using density $m/n$, budget factor $\alpha$, and grid-likeness) can achieve state-of-the-art total runtime across both dense and grid topologies.
3. **Hypothesis 3 (Redundant Facet Pruning)**: Pruning dual facets that are globally dominated across all vertices will reduce the per-label evaluation cost in `eval_envelope` without sacrificing pruning power.

#### C. Unresolved Questions
1. Can an adaptive heuristic policy predict search complexity accurately enough to make the hybrid solver win on held-out benchmark distributions without data leakage?
2. What is the tightest theoretical upper bound on the number of non-redundant lower-hull facets across arbitrary planar graphs?
