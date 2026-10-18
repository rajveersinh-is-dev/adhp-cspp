# Engineering Changelog & Audit Remediation Log
## ADHP-CSPP: Autonomous Algorithm Discovery & Audit Record

**Project Author**: Rajveersinh Vishal Pardeshi  
**Repository**: `https://github.com/rajveersinh-is-dev/adhp-cspp`  
**Date**: October 2026  
**Document**: `reviews/REVISION_LOG.md`  

---

### 1. Internal Automated Verification Cycles (Pre-Release Testing)

*Note: These internal cycles were automated quality gates executed during algorithm implementation, not independent third-party human reviews.*

#### Automated Check 1: Mathematical Foundations & Boundary Clarifications
- **Defects Identified**:
  1. Formal boundary behavior of $\mathcal{L}_u^\Lambda(\Delta w)$ when $\Delta w < 0$ (partial path already exceeding budget).
  2. Multiple Pareto points sharing a collinear tangent with identical slope $-\lambda$.
- **Actions Taken**:
  1. Updated `docs/MATHEMATICAL_FOUNDATIONS.md` to formally define $\mathcal{L}_u^\Lambda$ over $[0, \infty)$, noting that $\Delta w < 0$ is pruned upstream by feasibility filtering.
  2. Formally proved that $d_\lambda(u, t) = \min_{P} (c(P) + \lambda w(P))$ is a unique scalar infimum regardless of the multiplicity of argmin paths.
- **Verification**: `tests/property_tests.rs` executed 100 continuous domain checks per vertex with zero failures.

#### Automated Check 2: Parallel Edge Disambiguation & Differential Consistency
- **Defects Identified**:
  1. Path reconstruction via vertex indices alone (`[u, v]`) is ambiguous when parallel multigraph edges exist, leading to potential discrepancies in path cost evaluation.
  2. Instance generators could produce multigraphs with identical endpoints.
- **Actions Taken**:
  1. Augmented `ShortestPathTree` in `src/dijkstra.rs` with `predecessor_edge_ids` to store the exact edge ID relaxed during Dijkstra exploration.
  2. Stored `edge_path: Vec<usize>` directly in `CsppSolution` and implemented `evaluate_edge_path(&self, edges: &[usize])`.
  3. Updated `instance_generator.rs` to enforce clean graph construction.
- **Verification**: Reran differential oracle testing across all baseline solvers.

#### Automated Check 3: Complexity & Runtime Classification
- **Defects Identified**:
  1. CSPP is NP-hard; worst-case theoretical complexity remains exponential in $n$ or pseudo-polynomial in $W$.
  2. Preprocessing overhead ($K$ reverse Dijkstra trees) dominates execution time on small graphs ($n \le 60$).
- **Actions Taken**:
  1. Updated `docs/COMPLEXITY_ANALYSIS.md` to state clearly that worst-case complexity remains exponential.
  2. Separated preprocessing time from forward search time across all benchmark reporting.

---

### 2. External Audit 1 Remediation Log

- **Audit Focus**: Initial review of README claims, benchmark tables, and baseline comparisons.
- **Remediations**:
  1. *Grid Benchmark Reporting*: Restored all 5 solvers (Dumitrescu-Boland, Pulse, Carlyle-Wood, Martins, ADHP) in all tables.
  2. *Anti-Correlated Runtimes*: Clarified that total runtime for ADHP on small graphs is dominated by $K=5$ reverse Dijkstra passes.
  3. *Preprocessing Overhead Accounting*: Separated preprocessing time from forward search time in all empirical tables.
  4. *Multi-Instance Evaluation*: Expanded benchmark runs to 10 distinct random instances per configuration.
  5. *Ablation with $K=1$ Baseline*: Added $K=1$ (pure 1D cost bounding) to the ablation study ($K \in [1, 2, 3, 5, 8, 12]$).
  6. *Theorem 2 Tightness*: Documented strict dominance conditions taking into account min-weight ties.
  7. *Theorem 4 Formal Proof*: Formulated 4-part proof establishing admissibility, dominance preservation, termination, and epsilon safety.
  8. *Floating-Point Epsilon*: Implemented tolerance `PRUNE_EPSILON = 1e-9`.
  9. *Prior Literature Context*: Accurately cited Handler & Zang (1980), Carlyle & Wood (2008), Muhandiramge & Boland (2009), Dumitrescu & Boland (2003), and Lozano & Medaglia (2013).

---

### 3. External Audit 2 Remediation Log (Comprehensive 17-Point Resolution)

- **Audit Origin**: In-depth second-round code and paper review addressing implementation integrity, benchmark completeness, and claim calibration.
- **Remediations & Verification**:

#### A. Computation Integrity & ILP Verification
1. **Actual HiGHS ILP Execution in `scripts/verify_against_ilp.py`**:
   - *Issue*: `scripts/verify_against_ilp.py` defined `solve_cspp_ilp` but never called it, printing a static pass message.
   - *Fix*: `src/bin/verify_oracle.rs` was updated to serialize full graph instance topologies (`results/raw/verification_instances.json`). `scripts/verify_against_ilp.py` now loads all 100 instances, executes `scipy.optimize.milp` with the HiGHS backend, and asserts exact cost and status equivalence (`abs(ilp_cost - adhp_cost) < 1e-4` and matching infeasibility).
   - *Verification*: Executed in CI: 98 optimal matches, 2 infeasible matches, 0 discrepancies across all 100 instances.

2. **Complete Disclosure of All 19 Benchmark Configurations**:
   - *Issue*: The benchmark report, README, and paper omitted the Random ER (4 sizes) and Budget Sensitivity (5 values) suites, hiding configurations where ADHP performs worst. Across all 19 configurations in `benchmark_raw.csv`, ADHP is fastest in none, slowest in 17, and 3rd or 4th on the two largest grids.
   - *Fix*: Added full benchmark tables for Random ER ($n \in \{30, 60, 90, 120\}$) and Budget Sensitivity ($\alpha \in \{0.10, 0.25, 0.50, 0.75, 0.90\}$) to `research/BENCHMARK_REPORT.md`, `README.md`, and the paper. Explicitly reported that ADHP is slower in total wall-clock time on 17/19 configurations due to $K=5$ reverse Dijkstra preprocessing overhead (60–240 µs), whereas simple search on unconstrained or loose instances terminates in 3–35 µs.

3. **Instance Count Correction (200 Instances)**:
   - *Issue*: The text previously claimed 25 configurations / 250 instances. In reality, there are 20 distinct configuration sets (the six $K$ ablation settings share the same 10 instances of the $10 \times 10$ grid), totaling 200 distinct problem instances.
   - *Fix*: Corrected all references across README, report, and paper to "20 benchmark configurations / 200 distinct problem instances".

4. **Honest Memory Accounting (Dropped Misleading Peak Memory Claims)**:
   - *Issue*: The reported ~25 KB flat peak memory was primarily the fixed `Vec::with_capacity(1024)` label pool (16 KB), sampled only when the priority queue reached a new peak, and omitted the $K \times n$ preprocessing float arrays. Pulse’s 424 B reflected recursive DFS stack accounting without a label pool. Claiming bounded memory advantage over Martins was invalid.
   - *Fix*: Completely removed all claims of superior memory bounds. Documented exact memory allocation mechanisms: ADHP maintains a fixed preallocated label pool plus $K \times n$ floats for reverse trees; Pulse uses recursive DFS; Martins dynamically allocates labels without preallocation.

5. **Wall-Clock Headline Recalibration**:
   - *Issue*: The headline "3.54x faster than Martins" applies only to the single $10 \times 10$ grid instance and loses to Carlyle-Wood and Dumitrescu-Boland. The "17.9x search speedup" ignores preprocessing time (95–99% of total runtime). The planar grids are not "dense" ($n=100, m \approx 261$).
   - *Fix*: Removed all claims of "dominates on grids" or "world's fastest solver". Replaced with precise, scoped statements: ADHP provides up to 97.6% label suppression over unguided label-setting on planar grids with combinatorial trade-offs, but 1D methods (Carlyle-Wood, Dumitrescu-Boland) are faster in overall wall-clock time on almost all tested graphs due to lower preprocessing overhead.

6. **Prior Art: Mehlhorn–Ziegelmann (2000) Lower Hull Context**:
   - *Issue*: The multiplier discovery mechanism via recursive bisection is the parametric lower hull method introduced by Mehlhorn & Ziegelmann (2000) ("Resource Constrained Shortest Paths"). Claiming discovery of hull bisection overstated novelty.
   - *Fix*: Explicitly cited Mehlhorn & Ziegelmann (2000) and Handler & Zang (1980) across all documents. Clarified that ADHP’s specific contribution is utilizing the discovered hull facets to construct simultaneous multi-faceted lower bounding hyperplanes $\mathcal{L}_u^\Lambda(\Delta w)$ to prune intermediate label queues during forward search.

7. **Removal of Self-Scorecards and Synthetic Personas**:
   - *Issue*: `research/FINAL_EVALUATION.md` (9.2/10 self-score) and `research/NOVELTY_ASSESSMENT.md` read as self-grading, and "Reviewer A/B/C" personas in `reviews/` gave the appearance of independent external review.
   - *Fix*: Deleted `FINAL_EVALUATION.md`, `NOVELTY_ASSESSMENT.md`, and individual reviewer persona files via `git rm`. Rewrote `reviews/REVISION_LOG.md` as an engineering log distinguishing internal automated tests from external audit feedback.

#### B. Algorithmic & Mathematical Tightening
8. **Decimal Floating-Point Precision & Feasibility Epsilon**:
   - *Issue*: In IEEE 754 arithmetic, decimal edge weights such as $0.1 + 0.2 = 0.30000000000000004 > 0.3$. In a test graph with edges of weight 0.1 and 0.2 (cost 1 each) and budget 0.3, all five solvers previously returned a direct edge of cost 100 because Filter 1 and budget checks pruned the true optimum (cost 2) due to strict float comparison without epsilon.
   - *Fix*: Implemented relative feasibility tolerance: `w <= budget + budget.abs().max(1.0) * FEASIBILITY_EPSILON` (where `FEASIBILITY_EPSILON = 1e-9`) across all 5 solvers. Added unit test `test_decimal_floating_point_precision_case` confirming all solvers return cost 2.0.

9. **Theorem 4 Proof of Search Exhaustiveness**:
   - *Issue*: The proof established admissibility and dominance preservation, but did not formally show search exhaustiveness (that the optimal path cannot be missed).
   - *Fix*: Expanded Theorem 4 in `docs/MATHEMATICAL_FOUNDATIONS.md`, `paper/main.typ`, and `paper/main.tex` with a formal proof by induction on path length showing that every prefix of an optimal Pareto path $P^*$ remains unpruned by Filter 1, Filter 2, and Filter 3.

10. **Parallel Edge Disambiguation in Solution Representation**:
    - *Issue*: `CsppSolution` previously stored only vertex indices `path: Vec<usize>`. In multigraphs with parallel edges between the same endpoints, `evaluate_path` was ambiguous.
    - *Fix*: Added `id: usize` to `Edge`, `edge_id` to `HalfEdge`, and `edge_path: Vec<usize>` to `CsppSolution`. Implemented `evaluate_edge_path` for unambiguous evaluation and updated `evaluate_path` to resolve parallel edges by minimal cost subject to remaining budget.

11. **Strict Input Validation**:
    - *Issue*: `add_edge` returned a `bool` that was ignored, silently dropping invalid edges; NaN budgets returned "Optimal".
    - *Fix*: Marked `add_edge` with `#[must_use]`. Added strict validation in all solvers: returns `Infeasible` immediately if `budget.is_nan()`, `!budget.is_finite()`, `budget < 0.0`, or if source/target indices are invalid. Added unit tests for invalid inputs.

12. **Redundant Preprocessing Elimination (Early Exit Dijkstra)**:
    - *Issue*: Forward Dijkstra during $\lambda$ bisection explored the entire graph even though only $d_\lambda(s, t)$ was needed.
    - *Fix*: Implemented `dijkstra_forward_target` in `src/dijkstra.rs` with early termination upon settling the target vertex $t$.

13. **Instance Generator Precedence Bug**:
    - *Issue*: In `instance_generator.rs`, line 113 applied `.max(1.0)` only to the random noise `rng.gen_range(-5.0, 5.0).max(1.0)` due to missing parentheses, making the noise strictly non-negative.
    - *Fix*: Corrected to `(100.0 - c + rng.gen_range(-5.0, 5.0)).max(1.0)`. Added `assert!(graph.add_edge(...))` across all generator methods.

14. **Permanent Integer-DP Fuzz Oracle**:
    - *Issue*: Correctness tests lacked an independent ground-truth oracle with completely decoupled logic.
    - *Fix*: Implemented `test_integer_dp_oracle_fuzz` in `tests/correctness_tests.rs`, computing ground-truth optimum via 2D dynamic programming table `dp[v][w]` with zero shared code.

15. **Stale Text Updates**:
    - *CHANGELOG*: Synchronized to 100/100 verified against HiGHS ILP.
    - *CI Workflow*: Renamed oracle step to "Differential & Ground-Truth Oracle Verification (100 Instances)".
    - *VRPTW Application*: Scoped accurately to single-resource constrained pricing subproblems in column generation.
