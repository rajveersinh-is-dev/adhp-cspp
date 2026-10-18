# REVISION LOG & ADVERSARIAL DEFECT RESOLUTION
## Autonomous Algorithm Discovery Lab: ADHP-CSPP Three-Persona Review Cycles

**Project Author**: Rajveersinh Vishal Pardeshi  
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

---

### 4. Cycle 4: Rigorous External Audit Resolution (20-Point Remediation)

- **Audit Origin**: Independent External Review of Mathematical Foundations, Benchmarking, and Reporting
- **Items Addressed & Remediations**:
  1. *Grid Benchmark Claims*: Fully restored all 5 solvers (Dumitrescu-Boland, Pulse, Carlyle-Wood, Martins, ADHP) in all tables. Clarified that ADHP beats Martins (3.54x) and Pulse (3.42x) on $10 \times 10$ grids, while Carlyle-Wood and Dumitrescu-Boland have faster total wall-clock time due to lower preprocessing overhead.
  2. *Anti-Correlated Runtimes*: Clearly documented that total runtime for ADHP on small graphs ($n \le 100$) is dominated by $K=5$ reverse Dijkstra passes ($234 \, \mu\text{s}$ at $n=150$), so 1D methods have faster total runtime, while ADHP's forward search is 17.9x faster (4.74 µs vs 84.90 µs for Martins).
  3. *Label Suppression Transparency*: Explicitly identified comparisons against Martins (97.0% suppression) and Pulse (97.6% suppression), while reporting exact label counts alongside Carlyle-Wood and Dumitrescu-Boland.
  4. *Break-Even Boundary*: Accurately stated that break-even is achieved on dense combinatorial planar grids where label explosion dominates, and that 1D bounds are faster on small graphs ($n \le 100$).
  5. *Multi-Instance Evaluation*: Replaced single-instance benchmarking with 10 distinct random instances per configuration (250 distinct instances total), reporting mean, median, standard deviation, and peak memory.
  6. *Ablation with $K=1$ Baseline*: Added $K=1$ (pure 1D cost bounding) to the ablation study ($K \in [1, 2, 3, 5, 8, 12]$), demonstrating the dramatic 67.6% label drop from $K=1$ (148 labels) to $K=2$ (48 labels) and saturation at $K=5$ (40 labels).
  7. *Preprocessing Overhead Accounting*: Separated preprocessing time from search time in all empirical tables and discussion sections.
  8. *Peak Memory Reporting*: Added heap memory tracking (`peak_memory_bytes`) across all 5 solvers and reported memory consumption in all benchmark tables.
  9. *Theorem 2 Tightness Conditions*: Stated exact strict dominance conditions ($d_{\lambda_k} - d_c > \lambda_k \Delta w$) taking into account min-weight ties among cost-optimal paths, and formally showed that Filter 1 + Filter 2 subsume 1D bounds.
  10. *Theorem 4 Formal Proof*: Expanded into a complete 4-part proof establishing admissibility, Pareto dominance preservation, zero-cost/zero-weight cycle termination, and floating-point epsilon safety.
  11. *Floating-Point Epsilon Safety*: Implemented conservative tolerance `PRUNE_EPSILON = 1e-9` in all solvers.
  12. *Prior Literature Context*: Accurately credited Handler & Zang (1980), Carlyle & Wood (2008), Muhandiramge & Boland (2009), Dumitrescu & Boland (2003), and Lozano & Medaglia (2013).
  13. *Motivation Scoping*: Clarified that the implemented algorithm targets canonical single-resource CSPP with $c \ge 0, w \ge 0$.
  14. *Differential Oracle Scaling*: Scaled oracle testing to 100 diverse instances across all 5 solvers and validated against SciPy/HiGHS 0-1 ILP solver with 100% agreement.
  15. *Scientific Terminology*: Replaced "certified differential oracle" with "differentially verified against independent oracles across 100 instances".
  16. *Removed Leaked Terminology*: Cleaned up prompt references and framework jargon.
  17. *Rust Toolchain Synchronization*: Updated `rust-version = "1.80"` in `Cargo.toml` and synchronized all badges.
  18. *Dual Licensing*: Split `LICENSE` into standard `LICENSE-MIT` and `LICENSE-APACHE`.
  19. *LaTeX and Math Formatting*: Corrected KaTeX formatting and unified theorem numbering across `README.md` and `docs/`.
  20. *Algorithm Specification Completeness*: Added adaptive multiplier discovery pseudocode and complexity breakdown to `README.md`.
