# REVISION LOG & ADVERSARIAL DEFECT RESOLUTION
## Autonomous Algorithm Discovery Lab: ADHP-CSPP Three-Persona Review Cycles

**Project Author**: Rajve  
**Date**: October 2026  
**Document**: `reviews/REVISION_LOG.md`  

---

### 1. Cycle 1: Mathematical Foundations & Boundary Clarifications

- **Reviewer Persona**: Reviewer A (Research Mathematician)
- **Defects Identified**:
  1. *Defect M1*: Incomplete formal specification of the boundary behavior of $\mathcal{L}_u^\Lambda(\Delta w)$ when $\Delta w < 0$ (partial path already exceeding budget).
  2. *Defect M2*: Clarification of potential ambiguity when multiple Pareto points share a collinear tangent with identical slope $-\lambda$.
- **Actions Taken**:
  1. Updated `docs/MATHEMATICAL_FOUNDATIONS.md` to formally restrict the domain of $\mathcal{L}_u^\Lambda$ to $[0, \infty)$, noting that $\Delta w < 0$ is pruned upstream by feasibility filtering.
  2. Proved that $d_\lambda(u, t) = \min_{P} (c(P) + \lambda w(P))$ is a unique scalar infimum regardless of the multiplicity of argmin paths.
- **Verification**: `tests/property_tests.rs` executes 100 continuous domain checks per vertex with zero failures.

---

### 2. Cycle 2: Parallel Edge Anomaly and Ground-Truth Differential Resolution

- **Reviewer Persona**: Reviewer C (Systems and Experimental Reviewer)
- **Defects Identified**:
  1. *Defect S1*: During independent differential verification across 30 instances, 29 instances agreed 100%, but 1 instance (`anticorr_n25_s3`) showed a discrepancy where ADHP and Carlyle-Wood reported Infeasible while Martins reported Optimal.
  2. *Root Cause Investigation*: The synthetic instance generator created multigraphs where backbone edges had parallel duplicate edges. In `dijkstra.rs`, path reconstruction did not preserve the specific edge relaxed by Dijkstra; when `evaluate_path` was called, it picked the first edge in the adjacency list, computing an inflated path weight exceeding the budget.
- **Actions Taken**:
  1. Augmented `ShortestPathTree` in `src/dijkstra.rs` with `predecessor_edges` to store the exact `(cost, weight)` of the relaxed edge.
  2. Added `reconstruct_path_with_metrics` to compute path cost and weight directly from the relaxed edges.
  3. Modified `src/adhp.rs` and `src/baselines/carlyle_wood.rs` to check the exact Dijkstra distance `tree_w.distances[t] > budget` rather than heuristic lookup.
  4. Updated `instance_generator.rs` to ensure generated instances are clean simple directed graphs without duplicate parallel edges.
- **Verification**: Reran `cargo run --bin verify_oracle --release`. Result: **30 / 30 instances verified with 100% agreement** across all 5 solvers.

---

### 3. Cycle 3: Algorithmic Classification & Break-Even Boundary

- **Reviewer Persona**: Reviewer B (Algorithms & Complexity Researcher)
- **Defects Identified**:
  1. *Defect A1*: Theoretical complexity claim must explicitly state that worst-case complexity remains exponential since CSPP is NP-hard.
  2. *Defect A2*: Runtime comparisons on small graphs ($n \le 60$) showed Dumitrescu-Boland running faster due to $K=5$ tree preprocessing overhead. Claims must reflect Level B/C rather than an unqualified "world's fastest" claim.
- **Actions Taken**:
  1. Updated `docs/COMPLEXITY_ANALYSIS.md` to state that worst-case theoretical complexity remains exponential in $n$ (or pseudo-polynomial in $W$).
  2. Explicitly documented the break-even frontier in `research/BENCHMARK_REPORT.md` and `README.md`: ADHP dominates on planar grids, dense Pareto frontiers, and larger instances where label explosion occurs, while 1D bounding is preferable for small graphs ($n \le 50$).
- **Verification**: Full benchmark suite re-executed with all data transparently documented in `results/raw/benchmark_raw.csv`.
