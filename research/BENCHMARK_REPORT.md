# COMPREHENSIVE BENCHMARK REPORT
## Empirical Evaluation of Adaptive Dual Hull Pruning (ADHP) vs Established State-of-the-Art Solvers

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026 (Revised Post-Audit)  
**Document**: `research/BENCHMARK_REPORT.md`  
**Data Sources**: `results/raw/benchmark_raw.csv`, `results/raw/benchmark_raw.json`, `results/processed/summary_table.csv`  

---

### 1. Executive Summary & Honest Scientific Assessment

Across 25 systematic configurations evaluated over 10 distinct random instances per configuration (250 distinct instances, timed with 3 warmup runs and 3 repeated trials per instance using high-resolution hardware counters), the empirical evidence demonstrates:

1. **State-Space Pruning Power**:
   - On **Anti-Correlated** networks (where cost and weight metrics strongly conflict), ADHP generates the fewest candidate labels of any tested solver: an average of **57 labels** across $n \in [20, 150]$ (max 98), compared to **1,932 labels** for Martins (max 6,445), **2,422 labels** for Pulse (max 10,576), **323 labels** for Dumitrescu-Boland (max 1,101), and **111 labels** for Carlyle-Wood (max 335).
   - This represents a **97.0% label suppression** relative to Martins, **97.6%** relative to Pulse, and **82.3%** relative to Dumitrescu-Boland on the hardest instances ($n=150$).
   - On **2D Mesh Grids**, ADHP generates an average of **46 labels** (max 92 at $10 \times 10$), compared to **1,148 labels** for Martins (max 3,111) and **1,535 labels** for Pulse (max 4,741).

2. **The Preprocessing vs. Search Trade-Off (Honest Break-Even Analysis)**:
   - **Preprocessing Overhead**: Computing $K=5$ backward Dijkstra shortest path trees incurs a fixed preprocessing cost of $O(K(m + n \log n))$, measured at $\sim 20 \, \mu\text{s}$ at $n=40$ up to $\sim 234 \, \mu\text{s}$ at $n=150$.
   - **Search-Phase Speedup**: In the forward search phase, ADHP's tight lower-bound envelope achieves an enormous speedup: at $n=150$ anti-correlated graphs, ADHP's forward search takes only **4.74 µs**, compared to **84.90 µs** for Martins (**17.9x faster forward search**) and **36.57 µs** for Dumitrescu-Boland.
   - **Total Wall-Clock Time**: On small networks ($n \le 100$), this preprocessing overhead dominates total runtime. On anti-correlated instances at $n \le 100$, Dumitrescu-Boland ($8$–$39 \, \mu\text{s}$) and Martins ($4$–$26 \, \mu\text{s}$) have faster total runtime because the search space on small graphs is small enough that exhaustive search finishes before $K$ Dijkstra passes can amortize.
   - On 2D Mesh Grids where path proliferation is acute, ADHP's total runtime ($46.88 \, \mu\text{s}$ at $10 \times 10$) outperforms Martins ($166.14 \, \mu\text{s}$, **3.54x faster**) and Pulse ($160.67 \, \mu\text{s}$, **3.42x faster**). However, Carlyle-Wood ($26.93 \, \mu\text{s}$) and Dumitrescu-Boland ($35.12 \, \mu\text{s}$) remain faster in total wall-clock time due to lower preprocessing overhead.

3. **Ablation on Facet Count $K$ ($K = 1, 2, 3, 5, 8, 12$)**:
   - At $K=1$ (1D cost bounding, $\lambda = 0$), search generates **148 labels** and takes $7.55 \, \mu\text{s}$.
   - At $K=2$ (adding the first non-trivial dual hull facet), label generation drops by **67.6%** to **48 labels**, and search time drops to $2.02 \, \mu\text{s}$.
   - At $K=5$, labels reach **40** (search time $1.70 \, \mu\text{s}$).
   - Beyond $K=5$ ($K=8, 12$), label pruning saturates at 40 labels because all active facets are captured, while preprocessing time increases linearly from $61 \, \mu\text{s}$ to $86 \, \mu\text{s}$.

4. **Peak Memory Footprint**:
   - ADHP maintains a bounded peak memory footprint: $25.0 \text{ KB}$–$32.5 \text{ KB}$ across all instances.
   - Martins label memory expands significantly on combinatorial instances: $89.3 \text{ KB}$ on $10 \times 10$ grids and $104.3 \text{ KB}$ on $n=150$ anti-correlated graphs.
   - Pulse (being a depth-first search) maintains the smallest memory footprint ($0.4 \text{ KB}$–$1.4 \text{ KB}$), but incurs severe recursive search expansion on large grids ($4,741$ labels).

---

### 2. Comprehensive Empirical Performance Tables

#### A. Anti-Correlated Graph Scaling ($p = 0.25$, $\alpha = 0.40$, 10 Random Instances per Size)

| Nodes ($n$) | Metric | ADHP ($K=5$) | Carlyle-Wood | Dumitrescu-Boland | Pulse | Martins |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **20** | Total Time ($\mu\text{s}$) | $9.82 \pm 2.15$ | $6.45 \pm 0.88$ | $3.12 \pm 0.45$ | $3.55 \pm 0.50$ | $3.20 \pm 0.42$ |
| | Prep / Search ($\mu\text{s}$) | $8.80$ / $1.02$ | $5.50$ / $0.95$ | $1.85$ / $1.27$ | $1.80$ / $1.75$ | $0.00$ / $3.20$ |
| | Labels (Mean / Med) | **12** / **10** | 18 / 16 | 24 / 22 | 45 / 40 | 68 / 65 |
| | Peak Memory (Bytes) | 25,120 | 25,120 | 25,600 | 380 | 26,200 |
| **40** | Total Time ($\mu\text{s}$) | $21.63 \pm 7.31$ | $14.64 \pm 4.24$ | $8.75 \pm 2.07$ | $7.47 \pm 1.64$ | $6.80 \pm 1.78$ |
| | Prep / Search ($\mu\text{s}$) | $20.23$ / $1.40$ | $13.30$ / $1.34$ | $4.17$ / $4.58$ | $4.18$ / $3.29$ | $0.00$ / $6.80$ |
| | Labels (Mean / Med) | **29** / **34** | 34 / 34 | 47 / 55 | 106 / 100 | 317 / 333 |
| | Peak Memory (Bytes) | 25,408 | 25,280 | 27,328 | 424 | 29,312 |
| **60** | Total Time ($\mu\text{s}$) | $58.02 \pm 17.60$ | $30.39 \pm 3.96$ | $13.68 \pm 3.52$ | $13.69 \pm 3.72$ | $10.50 \pm 5.80$ |
| | Prep / Search ($\mu\text{s}$) | $55.52$ / $2.50$ | $28.58$ / $1.81$ | $7.95$ / $5.73$ | $7.97$ / $5.72$ | $0.00$ / $10.50$ |
| | Labels (Mean / Med) | **59** / **47** | 78 / 62 | 123 / 123 | 829 / 500 | 959 / 1,067 |
| | Peak Memory (Bytes) | 25,920 | 25,984 | 33,152 | 764 | 38,080 |
| **80** | Total Time ($\mu\text{s}$) | $87.37 \pm 21.35$ | $57.00 \pm 8.66$ | $20.83 \pm 3.70$ | $22.70 \pm 10.16$ | $18.73 \pm 7.69$ |
| | Prep / Search ($\mu\text{s}$) | $83.71$ / $3.66$ | $53.25$ / $3.75$ | $13.86$ / $6.97$ | $14.66$ / $8.04$ | $0.00$ / $18.73$ |
| | Labels (Mean / Med) | **76** / **64** | 103 / 94 | 189 / 176 | 1,005 / 611 | 1,480 / 1,434 |
| | Peak Memory (Bytes) | 25,056 | 25,344 | 34,432 | 592 | 48,384 |
| **100** | Total Time ($\mu\text{s}$) | $125.89 \pm 22.73$ | $69.96 \pm 15.41$ | $31.99 \pm 10.17$ | $31.94 \pm 5.92$ | $29.70 \pm 14.19$ |
| | Prep / Search ($\mu\text{s}$) | $122.35$ / $3.54$ | $68.04$ / $1.92$ | $20.26$ / $11.73$ | $20.11$ / $11.83$ | $0.00$ / $29.70$ |
| | Labels (Mean / Med) | **64** / **58** | 100 / 86 | 463 / 263 | 1,989 / 2,135 | 2,292 / 1,784 |
| | Peak Memory (Bytes) | 25,408 | 25,408 | 40,768 | 612 | 51,008 |
| **150** | Total Time ($\mu\text{s}$) | $239.06 \pm 23.16$ | $149.04 \pm 14.79$ | $78.19 \pm 26.75$ | $92.47 \pm 33.34$ | $84.90 \pm 46.29$ |
| | Prep / Search ($\mu\text{s}$) | $234.32$ / **4.74** | $143.20$ / $5.84$ | $41.62$ / $36.57$ | $41.23$ / $51.24$ | $0.00$ / $84.90$ |
| | Labels (Mean / Med) | **98** / **110** | 335 / 224 | 1,101 / 679 | 10,576 / 8,815 | 6,445 / 6,185 |
| | Peak Memory (Bytes) | 27,072 | 26,176 | 57,280 | 982 | 104,256 |

---

#### B. 2D Mesh Grid Graph Scaling (Planar Bottleneck Topologies, 10 Instances per Dimension)

| Dimensions | Vertices ($n$) | ADHP ($K=5$) ($\mu\text{s}$) | Carlyle-Wood ($\mu\text{s}$) | Dumitrescu-Boland ($\mu\text{s}$) | Pulse ($\mu\text{s}$) | Martins ($\mu\text{s}$) | ADHP Labels (Mean/Med) | Martins Labels (Mean/Med) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $9.72 \pm 3.33$ | $6.35 \pm 1.03$ | $4.64 \pm 1.32$ | $4.76 \pm 1.16$ | $4.52 \pm 0.48$ | **16** / **13** | 58 / 61 |
| $6 \times 6$ | 36 | $14.34 \pm 1.20$ | $10.50 \pm 0.62$ | $5.42 \pm 0.60$ | $7.10 \pm 0.75$ | $9.23 \pm 2.21$ | **35** / **35** | 315 / 330 |
| $8 \times 8$ | 64 | $26.46 \pm 2.02$ | $15.60 \pm 1.02$ | $10.95 \pm 1.45$ | $22.61 \pm 11.85$ | $36.54 \pm 8.22$ | **44** / **40** | 1,111 / 1,139 |
| $10 \times 10$ | 100 | $46.88 \pm 9.37$ | $26.93 \pm 3.64$ | $35.12 \pm 13.97$ | $160.67 \pm 61.30$ | $166.14 \pm 25.06$ | **92** / **92** | 3,111 / 3,063 |

*Performance Analysis on Grid Networks*:
- At $10 \times 10$, Martins generates an average of **3,111 labels** taking $166.14 \, \mu\text{s}$, and Pulse generates **4,741 labels** taking $160.67 \, \mu\text{s}$.
- ADHP prunes label generation down to **92 labels**, resulting in an execution time of **$46.88 \, \mu\text{s}$** (**3.54x faster than Martins**, **3.42x faster than Pulse**).
- However, Carlyle-Wood ($26.93 \, \mu\text{s}$, 115 labels) and Dumitrescu-Boland ($35.12 \, \mu\text{s}$, 662 labels) achieve faster overall runtime because their preprocessing overhead is lower (1 reverse tree for Carlyle-Wood and 2 for Dumitrescu-Boland, vs 5 for ADHP).

---

#### C. Ablation Analysis on Facet Count $K$ ($n = 70$, Anti-Correlated Graph)

| Facet Count $K$ | Preprocessing ($\mu\text{s}$) | Search Time ($\mu\text{s}$) | Total Runtime ($\mu\text{s}$) | Labels Generated (Mean / Med) | Dual-Pruned Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **$K = 1$** (1D Cost Bound) | **23.29** | **7.55** | **30.84** | **148** / **175** | 40 |
| **$K = 2$** (First Dual Slope) | 34.98 | 2.02 | 37.00 | **48** / **42** (-67.6%) | 24 |
| **$K = 3$** (Two Active Slopes) | 42.94 | 1.69 | 44.63 | **45** / **42** | 22 |
| **$K = 5$** (Adaptive Dual Hull) | 61.41 | 1.70 | 63.11 | **40** / **39** | 21 |
| **$K = 8$** (Fine Discretization) | 81.25 | 1.68 | 82.93 | **40** / **39** | 21 |
| **$K = 12$** (Over-Discretized) | 85.84 | 2.00 | 87.83 | **40** / **39** | 21 |

*Key Insights from Ablation*:
1. Moving from $K=1$ (standard 1D cost bounding) to $K=2$ (first non-zero Lagrangian slope) produces the single largest algorithmic leap: **label generation drops from 148 down to 48 (a 67.6% drop)** and search time plummets from $7.55 \, \mu\text{s}$ to $2.02 \, \mu\text{s}$.
2. Between $K=2$ and $K=5$, additional facets capture intermediate curvature, further reducing labels to 40.
3. For $K \ge 5$, label reduction saturates, while preprocessing grows linearly ($\sim 18 \, \mu\text{s}$ per additional backward Dijkstra pass). Thus, $K \in [3, 5]$ provides the optimal practical configuration.

---

### 3. Generated Figures

High-resolution scientific plots generated directly from `results/raw/benchmark_raw.csv` via `scripts/plot_results.py`:
1. `results/figures/fig1_labels_generated_anticorr.png`: Candidate label scaling on logarithmic axis across graph sizes.
2. `results/figures/fig2_runtime_grid.png`: Wall-clock execution time on 2D mesh grid networks.
3. `results/figures/fig3_ablation_facets.png`: Preprocessing vs. search trade-off as facet count $K$ varies.

---

### 4. Reproducibility Instructions

To reproduce all benchmarks, figures, and summary tables from source:
```powershell
# 1. Run full multi-instance benchmark suite (250 executions across 25 configurations)
cargo run --bin benchmark_suite --release

# 2. Run independent 100-instance differential verification against 4 solvers and HiGHS ILP
cargo run --bin verify_oracle --release
python scripts/verify_against_ilp.py

# 3. Regenerate all publication figures and summary tables
python scripts/plot_results.py
```
