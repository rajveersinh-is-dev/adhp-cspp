# BENCHMARK METHODOLOGY & EXPERIMENTAL PROTOCOL
## Rigorous, Reproducible Evaluation of Constrained Shortest Path Solvers

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/BENCHMARK_METHODOLOGY.md`  
**Repository**: [https://github.com/rajveersinh-is-dev/adhp-cspp](https://github.com/rajveersinh-is-dev/adhp-cspp)

---

### 1. Core Principles of Computational Honesty

To eliminate benchmark bias, synthetic inflation, and reproducibility defects, all experiments in this repository strictly adhere to five non-negotiable principles:

1. **Zero Precomputed Lookup Tables**: No hardcoded recurrence answers, precomputed trees, or cached graph outputs exist in any solver. Every problem is solved from first principles dynamically.
2. **Real In-Process Monotonic Execution**: All execution timings are measured in-process using high-resolution hardware counters via Rust's `std::time::Instant` (backed by `QueryPerformanceCounter` on Windows and `clock_gettime(CLOCK_MONOTONIC)` on Linux).
3. **Mandatory Warmup Runs**: Every solver execution on every instance is preceded by **at least 5 discarded warmup runs** to warm instruction and data caches and eliminate CPU frequency governor ramp-up artifacts.
4. **Multi-Instance Distributional Evaluation**: Rather than reporting single-instance anomalies, each benchmark configuration evaluates **10 distinct pseudo-random problem instances** generated with deterministic random seeds. For each instance, 3 timed repetitions are averaged to filter transient operating system interrupts.
5. **End-to-End Accounting**: All reported execution times strictly include **preprocessing time** (backward trees, bisection, and initial lower bound construction) in addition to priority search time. A reduction in search time is never claimed as a speedup if preprocessing costs more than it saves.

---

### 2. Experimental Benchmark Suites & Instance Accounting

The benchmark harness (`src/bin/benchmark_suite.rs`) evaluates 6 competitive solvers across 5 distinct benchmark suites comprising **25 configurations, 250 configuration-instance evaluations, and 200 distinct generated graphs**:

| Suite | Category | Graph Topology | Parameter Range | Evaluations | Distinct Graphs | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Suite 1** | Anti-Correlated Scaling | Random Directed ($p=0.25$), $c_e$ vs $w_e$ negatively correlated | $n \in \{20, 40, 60, 80, 100, 150\}$ | 60 | 60 | Tests label explosion when low cost implies high resource consumption. |
| **Suite 2** | 2D Mesh Grid Scaling | Directed 2D Planar Mesh Grids | $4\times4, 6\times6, 8\times8, 10\times10$ ($n=16$ to $100$) | 40 | 40 | Tests performance on sparse planar networks with long hop diameters and exponential simple paths. |
| **Suite 3** | Random Erdős–Rényi | Directed Erdős–Rényi ($p=0.20$), Uniform Cost & Weight | $n \in \{30, 60, 90, 120\}$ ($m$ up to $3000$) | 40 | 40 | Evaluates dense networks with small hop diameter and tests dual preprocessing overhead. |
| **Suite 4** | Budget Factor Sensitivity | Anti-Correlated Graph ($n=50$) | $\alpha \in \{0.10, 0.25, 0.50, 0.75, 0.90\}$ | 50 | 50 | Tests transition from severely tight budget ($\alpha=0.10$) to loose budget ($\alpha=0.90$). |
| **Suite 5** | Ablation Analysis | Anti-Correlated Graph ($n=70$) | $K \in \{1, 2, 3, 5, 8, 12\}$ | 60 | 10 | Isolates the causal impact of dual facet count $K$ on the exact same 10 controlled graphs. |
| **Total** | **All 5 Suites** | **Diverse Topologies** | **25 Configurations** | **250** | **200** | **Comprehensive empirical evaluation across distinct and controlled graphs.** |

> [!NOTE]
> **Evaluation Count vs. Distinct Graph Count**:
> In Suites 1–4, each evaluated instance is a newly generated random graph (totaling $60 + 40 + 40 + 50 = 190$ distinct graphs across 19 configurations).
> In Suite 5 (Ablation), a controlled repeated-graph design evaluates 6 different facet settings ($K \in \{1, 2, 3, 5, 8, 12\}$) on the **exact same 10 generated graphs** to isolate the causal effect of $K$ without graph generation variance.
> Therefore, the benchmark suite conducts **250 configuration-instance evaluations across 200 distinct problem graphs**.

---

### 3. Evaluated Solvers and Fair Comparison Protocol

All solvers are compiled under identical release configurations (`cargo build --release`, Opt-level 3, LTO enabled):
1. **ADHP (Adaptive Dual Hull Pruning)**: Proposed multi-faceted solver with fixed $K=5$.
2. **Adaptive Hybrid ADHP**: Instance-adaptive preprocessing heuristic dynamically selecting $K \in \{1, 2, 5\}$ based on $O(1)$ instance observables.
3. **Carlyle-Wood (LARAC)**: Lagrangian relaxation single-multiplier bisection with 1D lower-bound label setting.
4. **Dumitrescu-Boland**: Preprocessed 1D unconstrained cost ($d_c$) and weight ($d_w$) label setting.
5. **Pulse (Lozano & Medaglia 2013)**: Recursive depth-first search with pulse propagation and pruning.
6. **Martins (1984)**: Classical multiobjective label setting (Pareto frontier Dijkstra).

#### Held-Out Evaluation Protocol for Adaptive Hybrid Heuristic
To prevent circular evaluation and overfitting:
- **Tuning Set**: Initial decision boundary thresholds ($\rho \ge 3.5, \gamma < 0.04, \alpha \ge 0.85$) were calibrated on a small development set of synthetic graphs ($n=50$).
- **Held-Out Evaluation**: The full benchmark suite ($n=20$ to $150$, grid dimensions $4\times4$ to $10\times10$, budget alphas $0.10$ to $0.90$) served as the independent held-out evaluation set.
- **Transparent Regression Reporting**: The hybrid solver is an empirical heuristic and is **not** a universal speedup theorem. On small random Erdős–Rényi graphs ($n \le 60$) and small anti-correlated graphs ($n \le 80$), Martins remains faster than both ADHP and Hybrid ADHP because sparse/small graphs exhibit negligible Pareto label collisions, making any preprocessing overhead unamortized. All such regressions are retained and reported without omission.

---

### 4. Machine and Environmental Context

- **Operating System**: Microsoft Windows 11 Enterprise (64-bit)
- **Rust Toolchain**: `rustc 1.80+` / `cargo` (Profile: `release`, codegen-units = 1)
- **Python Environment**: Python 3.11/3.14 with `numpy`, `scipy` (HiGHS MILP 1.7+), `pandas`, `matplotlib`
- **Compiler Flags**: Default Cargo release optimizations (`-C opt-level=3`)

---

### 5. Automated Verification & Reproducibility Workflow

To reproduce all experimental results, figures, and verification records from a clean checkout:

```bash
# 1. Run all unit, property, and adversarial regression tests (22 tests)
cargo test

# 2. Run differential verification against 4 baselines (100 instances)
cargo run --bin verify_oracle --release

# 3. Run independent HiGHS ILP oracle verification (SciPy MILP)
python scripts/verify_against_ilp.py

# 4. Execute the full empirical benchmark suite (250 instances, 5 warmups)
cargo run --bin benchmark_suite --release

# 5. Generate publication figures and summary tables
python scripts/plot_results.py

# 6. Run automated consistency verification (fails if CSV disagrees with reported numbers)
python scripts/verify_benchmarks.py
```
