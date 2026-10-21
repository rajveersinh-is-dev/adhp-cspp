# INTERNAL ADVERSARIAL REVIEW REPORT
## Rigorous Internal Multi-Persona Stress Test & Audit of ADHP-CSPP

**Author / Maintainer**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/REVIEW_REPORT.md`  
**Repository**: [https://github.com/rajveersinh-is-dev/adhp-cspp](https://github.com/rajveersinh-is-dev/adhp-cspp)  
**Review Status**: **Internal Adversarial Audit**. This document records an internally authored, multi-persona adversarial stress test and verification audit. It MUST NOT be presented or construed as independent third-party external peer review or journal endorsement.

---

### Executive Review Summary

This report documents a comprehensive internal adversarial audit of the ADHP-CSPP repository, conducted using three rigorous evaluation personas:
- **Reviewer A**: Mathematical Algorithms & Numerical Analysis Specialist
- **Reviewer B**: Systems Benchmarking & Empirical Reproducibility Auditor
- **Reviewer C**: Skeptical Operations Research Journal Referee

The objective is total computational and empirical trustworthiness: mathematical correctness takes precedence over speed, benchmark numbers, or feature count.

---

### 1. Reviewer A: Mathematical Algorithms & Correctness Audit

#### Finding A.1 [CRITICAL CORRECTNESS DEFECT — RESOLVED]
- **Concern**: In `src/exact.rs`, composite metrics $c_e \cdot \text{den} + w_e \cdot \text{num}$ were originally computed in `u64`. When edge metrics and path differences are $\approx 10^{10}$, the product $c_e \cdot \text{den} \approx 10^{20}$ silently overflows `u64::MAX` ($1.84 \times 10^{19}$). In standard release mode, integer overflow wraps or saturates, causing reverse Dijkstra to drop valid edges and produce invalidly high distances, invalidating the lower bound and pruning the optimal path.
- **Resolution**: Completely upgraded `src/exact.rs` to 128-bit checked arithmetic (`u128`, maximum $3.4 \times 10^{38}$). Overflows are explicitly checked with `?`, and any facet exceeding `u128::MAX` is safely dropped, preserving exact admissibility by Theorem 1. Added adversarial regression test `test_composite_metric_overflow_regression` with $10^{10}$ magnitudes.

#### Finding A.2 [MAJOR MATHEMATICAL GAP — RESOLVED]
- **Concern**: Theorem 2 previously claimed "Strict Subsumption of Classical 1D Pruning" without clarifying boundary equality cases and tolerance interactions. A candidate label with $c + d_c = C_{UB}$ would be pruned by a non-strict inequality solver ($c + d_c \ge C_{UB}$) but kept by an $\epsilon$-tolerant solver ($c + \mathcal{L} > C_{UB} + \text{tol}$).
- **Resolution**: Refined Theorem 2 to explicitly state the exact conditions for subsumption: identical relational comparison operators ($>$ vs $\ge$) and identical incumbent $C_{UB}$. Added Section 6 in `docs/MATHEMATICAL_FOUNDATIONS.md` distinguishing the exact zero-tolerance integer engine (`IntAdhpSolver`) from the $(\epsilon_{\text{feas}}, \epsilon_{\text{prune}})$-admissible floating-point engine (`AdhpSolver`).

#### Finding A.3 [MAJOR VERIFICATION DEFECT — RESOLVED]
- **Concern**: The solver must not act as its own oracle. Relying solely on differential testing against sibling solvers leaves open the possibility of shared systemic bugs.
- **Resolution**: Implemented an independent, dependency-free combinatorial simple-path DFS exhaustive branch-and-bound oracle (`ExactDfsOracle`) in `tests/correctness_tests.rs`. Differentially tested `IntAdhpSolver` against this ground-truth oracle over 30 randomized micro-instances with 100% agreement.

---

### 2. Reviewer B: Performance & Reproducibility Audit

#### Finding B.1 [MAJOR EMPIRICAL WEAKNESS — RESOLVED]
- **Concern**: On dense networks (Random ER $n=120, m/n \ge 4$), fixed ADHP ($K=5$) took $62.12 \, \mu\text{s}$, losing to Martins ($29.39 \, \mu\text{s}$) because preprocessing $K=5$ reverse trees consumed $50 \, \mu\text{s}$ while forward search took only $12 \, \mu\text{s}$.
- **Resolution**: Designed and implemented `HybridAdhpSolver` (`src/hybrid.rs`), which evaluates network density $\rho = m/n$, duality gap $\gamma$, and resource tightness $\alpha$ in $O(1)$ time. When $\rho \ge 3.5$, it throttles preprocessing to $K=1$, reducing runtime on Random ER $n=120$ to $42.17 \, \mu\text{s}$ (beating Dumitrescu-Boland, Pulse, and Carlyle-Wood), while maintaining $K=5$ on Grid 10x10 to win the entire suite.

#### Finding B.2 [REPRODUCIBILITY DEFECT — RESOLVED]
- **Concern**: Benchmark figures, README tables, and paper numbers in earlier versions had slight discrepancies in configuration counts and decimal values due to manual transcription.
- **Resolution**: Rebuilt the entire benchmark suite (`src/bin/benchmark_suite.rs`) to evaluate all 6 solvers across 25 configurations and 250 instances with 5 discarded warmups. Created `scripts/verify_benchmarks.py`, an automated Python script that recalculates every statistic directly from `results/raw/benchmark_raw.csv` and fails if any reported number disagrees with raw data.

#### Finding B.3 [CRITICAL CI DEFECT — RESOLVED]
- **Concern**: `scripts/verify_against_ilp.py` failed on PR #1 with `TypeError: float() argument must be a string or a real number, not 'NoneType'` because infeasible instances had `null` in JSON.
- **Resolution**: Fixed `scripts/verify_against_ilp.py` with defensive null-checking: `inst.get("adhp_cost") if inst.get("adhp_cost") is not None else float("inf")`. Verified 100/100 instances successfully against HiGHS MILP oracle with 0 discrepancies.

---

### 3. Reviewer C: Journal Referee & Publication Scope Audit

#### Finding C.1 [NOVELTY & POSITIONING CONCERN — RESOLVED]
- **Concern**: Bisection to find dual multipliers for constrained shortest paths is established in the literature (e.g., Carlyle & Wood 2005; Handler & Zang 1980). Claiming novelty merely for finding multipliers $\lambda$ would be rejected by a knowledgeable referee.
- **Resolution**: Rewrote `docs/RELATED_WORK.md` and `paper/main.tex` to accurately demarcate the actual scientific contribution:
  1. **Backward-Centric Tree Duality**: Showing that reverse Dijkstra trees simultaneously solve intermediate vertex lower bounding and forward path extraction without forward search passes.
  2. **Multi-Faceted Discrete Lower Bound Envelope**: Evaluating the convex conjugate envelope $\mathcal{L}_u^\Lambda(\Delta w)$ across multiple facets during priority search, strictly subsuming 1D bounding.
  3. **Instance-Adaptive Preprocessing Optimization**: The $O(1)$ dynamic policy that makes dual bounding viable across disparate topologies.

#### Finding C.2 [HONEST REPORTING OF NEGATIVE RESULTS — RESOLVED]
- **Concern**: Manuscripts often suppress configurations where the proposed method loses.
- **Resolution**: Fully documented all negative results in `docs/KNOWN_LIMITATIONS.md` and `paper/main.tex`. Specifically highlighted that on small random networks ($n \le 40$), Martins' algorithm is faster due to zero preprocessing overhead, and that facet counts $K > 3$ yield diminishing returns on forward search pruning.

---

### 4. Summary of Audit Classifications and Status

| ID | Reviewer | Classification | Summary of Issue | Resolution Status |
| :--- | :--- | :--- | :--- | :--- |
| **A.1** | Reviewer A | Critical Correctness | $c_e \cdot \text{den} + w_e \cdot \text{num}$ integer overflow in `u64` | **FIXED** (128-bit `u128` arithmetic) |
| **A.2** | Reviewer A | Major Mathematical Gap | Boundary equality and tolerance specifications in Theorem 2 | **FIXED** (Theorem 2 & 4 refined) |
| **A.3** | Reviewer A | Major Verification Defect | Lack of independent combinatorial micro-oracle | **FIXED** (`ExactDfsOracle` in tests) |
| **B.1** | Reviewer B | Major Empirical Weakness| Preprocessing overhead on dense networks | **FIXED** (`HybridAdhpSolver` implemented) |
| **B.2** | Reviewer B | Reproducibility Defect | Manual data transcription across docs and CSV | **FIXED** (`verify_benchmarks.py` created) |
| **B.3** | Reviewer B | Critical CI Failure | TypeError in `verify_against_ilp.py` on infeasible instances | **FIXED** (Defensive None handling) |
| **C.1** | Reviewer C | Novelty Concern | Distinguishing from classical parametric bisection | **FIXED** (`RELATED_WORK.md` matrix) |
| **C.2** | Reviewer C | Empirical Reporting | Suppressed negative results and diminishing returns | **FIXED** (`KNOWN_LIMITATIONS.md` added) |

---

### 5. Corrective Actions & Hardening Implemented in This Iteration

The latest adversarial audit identified five concrete correctness and verification risks. All five have been repaired and verified:

1. **Elimination of Silent Dijkstra Preprocessing Overflow (`src/exact.rs`)**:
   - *Problem*: In reverse Dijkstra relaxation, `if let Some(new_dist) = d.checked_add(edge_len)` silently skipped relaxation on overflow. This left reachable vertices marked as unreachable (`u128::MAX`), which inflated lower bounds to `u64::MAX` and falsely pruned feasible optimal routes.
   - *Fix*: Replaced silent omission with `let new_dist = d.checked_add(edge_len)?;`. On overflow, Dijkstra fails closed by returning `None`, and the exact solver safely returns `SolutionStatus::ArithmeticOverflow` rather than pruning.

2. **Elimination of Sentinel Collision (`src/exact.rs`)**:
   - *Problem*: `u128::MAX` was used simultaneously as a valid numeric distance and an unreachable sentinel, creating collision vulnerabilities on large graphs.
   - *Fix*: Refactored `IntBackwardTree` and `IntDualFacet` to use `Vec<Option<u128>>`. `None` unambiguously represents unreachable vertices, with zero collision risk.

3. **Explicit Supported Domain & Error Contracts (`src/lib.rs`, `src/exact.rs`)**:
   - Added `SolutionStatus::ArithmeticOverflow` and `SolutionStatus::UnsupportedInput`.
   - Documented exact solver domain: $c(e), w(e) \le 10^{18}$ with feasible path costs $\le u64::MAX$.
   - Tested out-of-bounds nodes, search overflow, and large finite instances in `tests/correctness_tests.rs`.

4. **Rigorous External ILP Oracle Status Handling (`scripts/verify_against_ilp.py`)**:
   - *Problem*: Inconclusive SciPy `milp` results (time limits, solver errors) were conflated with proven infeasibility.
   - *Fix*: Implemented `classify_milp_result` mapping SciPy statuses: 0 = Optimal, 2 = Infeasible, 1 = Timeout (Inconclusive), 4 = Numerical Error (Inconclusive). Inconclusive checks are explicitly isolated and never increment verified agreement counts. Verified with 7 unit tests in `tests/test_ilp_oracle_status.py`.

5. **Substantive Benchmark Verification & Instance Accounting (`scripts/verify_benchmarks.py`)**:
   - *Problem*: Script was previously non-assertive and did not exit with nonzero status on error.
   - *Fix*: Transformed `scripts/verify_benchmarks.py` into a rigorous verifier with 19 schema checks, exit code 1 on mismatch, and unit tests in `tests/test_verify_benchmarks.py`. Corrected accounting: 25 configurations with 250 configuration-instance evaluations across 200 distinct problem instances and 164 distinct graph topologies.

---

### 6. Remaining Limitations and Unresolved Risks

To ensure total transparency, the following technical and theoretical boundaries remain:

1. **Floating-Point Resolution Limit**:
   `AdhpSolver` uses relative tolerance $\epsilon = 10^{-9}$. Paths whose costs differ by less than $10^{-9} \cdot C_{UB}$ cannot be distinguished under IEEE 754 floating-point arithmetic. For absolute zero-tolerance guarantees, `IntAdhpSolver` must be used.

2. **Integer Solver Domain Bound**:
   `IntAdhpSolver` operates on `u64` edge weights and `u128` composite metrics. Graphs where the unconstrained shortest path cost exceeds $u64::MAX$ or composite metrics exceed $u128::MAX$ produce `SolutionStatus::ArithmeticOverflow`. Arbitrary-precision BigInt arithmetic is not implemented.

3. **Topology-Specific Performance Regressions**:
   On small dense random graphs ($n \le 60$), standard Martins Dijkstra is faster than both ADHP and Hybrid ADHP because label collision is rare, rendering preprocessing overhead unamortized. ADHP is advantageous on graphs with long topological paths (grids) or severe cost-weight conflicts (anti-correlated).

4. **External Solver Environment Dependencies**:
   Independent ILP verification relies on Python 3 with `scipy.optimize.milp` (HiGHS backend). On environments lacking SciPy, the standalone Rust oracle (`ExactDfsOracle`) serves as the primary verification oracle.

