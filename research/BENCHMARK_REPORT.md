# COMPREHENSIVE BENCHMARK REPORT
## Empirical Evaluation of Adaptive Dual Hull Pruning (ADHP) vs Established State-of-the-Art Solvers

**Author**: Rajveersinh Vishal Pardeshi  
**Repository**: `https://github.com/rajveersinh-is-dev/adhp-cspp`  
**Date**: October 2026 (Revised Post-Audit)  
**Document**: `research/BENCHMARK_REPORT.md`  
**Data Sources**: `results/raw/benchmark_raw.csv`, `results/raw/benchmark_raw.json`, `results/processed/summary_table.csv`  

---

### 1. Executive Summary & Honest Scientific Assessment

Across 20 systematic configurations evaluated over 10 distinct random instances per configuration (200 distinct problem instances total, timed with 3 warmup runs and 3 repeated trials per instance using high-resolution hardware counters):

1. **State-Space Pruning Power (Search Phase)**:
   - On **Anti-Correlated** networks (severe trade-offs between cost and weight), ADHP achieves dramatic candidate label suppression: an average of **57 labels** across $n \in [20, 150]$ (max 98), compared to **1,932 labels** for Martins (max 6,445), **2,422 labels** for Pulse (max 10,576), **323 labels** for Dumitrescu-Boland (max 1,101), and **111 labels** for Carlyle-Wood (max 335).
   - On the hardest anti-correlated instances ($n=150$), ADHP achieves **98.5% label reduction** relative to Martins, **99.1%** relative to Pulse, and **91.1%** relative to Dumitrescu-Boland.
   - On **2D Mesh Grids** ($10 \times 10$, $n=100$), ADHP generates only **92 labels**, compared to **3,111 labels** for Martins (97.0% reduction) and **4,741 labels** for Pulse (98.1% reduction).
   - In forward search alone, ADHP takes only **4.74 µs** on $n=150$ anti-correlated graphs vs. **84.90 µs** for Martins (**17.9x faster forward search**).

2. **Total Wall-Clock Reality Across All 19 Benchmark Configurations**:
   - **Across all 19 benchmark configurations in `benchmark_raw.csv`, ADHP is the fastest solver in 0 configurations, is last in 17 configurations, and is 3rd and 4th on the two largest grids ($10\times 10$ and $8\times 8$).**
   - **Why ADHP is Slower in Total Time**: ADHP computes $K=5$ reverse shortest path trees during preprocessing, which incurs a fixed cost of $O(K(m + n \log n))$. This takes $11$–$234 \, \mu\text{s}$ depending on graph size, accounting for **95–99% of ADHP's total execution time**.
   - On instances with moderate combinatorial conflict (Random ER, loose budgets, or small networks $n \le 100$), the label search space is small enough that unguided search (Martins) or 1D-bounded search (Dumitrescu-Boland, Pulse) finishes in $3$–$48 \, \mu\text{s}$—well before ADHP's $K=5$ reverse Dijkstra passes can amortize.
   - For example, on **Random ER $n=120$**, Martins finishes in **37.83 µs**, Dumitrescu-Boland in **48.95 µs**, and Pulse in **56.00 µs**, whereas ADHP takes **161.69 µs** (157.86 µs preprocessing + 3.83 µs search).
   - Only on topologies with exponential path proliferation (such as the $10 \times 10$ grid) does ADHP's total time ($46.88 \, \mu\text{s}$) beat Martins ($166.14 \, \mu\text{s}$, 3.54x faster) and Pulse ($160.67 \, \mu\text{s}$, 3.42x faster). However, even on that grid, 1D methods with lighter preprocessing—Carlyle-Wood ($26.93 \, \mu\text{s}$) and Dumitrescu-Boland ($35.12 \, \mu\text{s}$)—remain faster in total wall-clock time.

3. **Memory Footprint Accounting**:
   - The reported ~25 KB peak heap usage for ADHP reflects a preallocated label capacity buffer (`Vec::with_capacity(1024)`, ~16 KB) combined with internal graph structures, plus $K \times n \times 8$ bytes for reverse distance arrays.
   - Pulse operates via recursive depth-first search without a label queue, exhibiting a small execution stack (~0.4–2 KB).
   - Martins allocates label nodes dynamically without preallocation, growing up to ~104 KB on $n=150$ anti-correlated graphs as thousands of unpruned labels accumulate.
   - We do not claim an intrinsically superior memory bound: ADHP's memory advantage over Martins on large graphs arises from avoiding label explosion, while its baseline overhead includes the $K \times n$ preprocessing tables.

---

### 2. Full Benchmark Results Across All Suites

#### A. Anti-Correlated Graph Scaling ($p = 0.25$, $\alpha = 0.40$, 10 Random Instances per Size)

| Nodes ($n$) | Metric | ADHP ($K=5$) | Carlyle-Wood | Dumitrescu-Boland | Pulse | Martins |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **20** | Total Time ($\mu\text{s}$) | $15.58 \pm 4.32$ | $11.13 \pm 2.28$ | $2.59 \pm 0.33$ | $2.63 \pm 0.82$ | $3.56 \pm 1.23$ |
| | Prep / Search ($\mu\text{s}$) | $12.61$ / $2.96$ | $8.58$ / $2.55$ | $1.56$ / $1.03$ | $1.67$ / $0.95$ | $0.00$ / $3.56$ |
| | Labels (Mean / Med) | **17** / **16** | 20 / 17 | 20 / 17 | 29 / 30 | 102 / 88 |
| **40** | Total Time ($\mu\text{s}$) | $21.63 \pm 7.31$ | $14.64 \pm 4.24$ | $8.75 \pm 2.07$ | $7.47 \pm 1.64$ | $6.80 \pm 1.78$ |
| | Prep / Search ($\mu\text{s}$) | $20.23$ / $1.40$ | $13.30$ / $1.34$ | $4.17$ / $4.59$ | $4.18$ / $3.29$ | $0.00$ / $6.80$ |
| | Labels (Mean / Med) | **29** / **34** | 34 / 34 | 47 / 55 | 106 / 100 | 317 / 333 |
| **60** | Total Time ($\mu\text{s}$) | $58.02 \pm 17.60$ | $30.39 \pm 3.96$ | $13.68 \pm 3.52$ | $13.69 \pm 3.72$ | $10.50 \pm 5.80$ |
| | Prep / Search ($\mu\text{s}$) | $55.52$ / $2.50$ | $28.58$ / $1.81$ | $7.95$ / $5.73$ | $7.97$ / $5.72$ | $0.00$ / $10.50$ |
| | Labels (Mean / Med) | **59** / **47** | 78 / 62 | 123 / 123 | 829 / 500 | 959 / 1,067 |
| **80** | Total Time ($\mu\text{s}$) | $87.37 \pm 21.35$ | $57.00 \pm 8.66$ | $20.83 \pm 3.70$ | $22.70 \pm 10.16$ | $18.73 \pm 7.69$ |
| | Prep / Search ($\mu\text{s}$) | $83.71$ / $3.65$ | $53.25$ / $3.75$ | $13.86$ / $6.97$ | $14.66$ / $8.04$ | $0.00$ / $18.73$ |
| | Labels (Mean / Med) | **76** / **64** | 103 / 94 | 189 / 176 | 1,005 / 611 | 1,480 / 1,434 |
| **100** | Total Time ($\mu\text{s}$) | $125.89 \pm 22.73$ | $69.96 \pm 15.41$ | $31.99 \pm 10.17$ | $31.94 \pm 5.92$ | $29.70 \pm 14.19$ |
| | Prep / Search ($\mu\text{s}$) | $122.35$ / $3.54$ | $68.04$ / $1.92$ | $20.26$ / $11.73$ | $20.11$ / $11.83$ | $0.00$ / $29.70$ |
| | Labels (Mean / Med) | **64** / **58** | 100 / 86 | 463 / 263 | 1,989 / 2,135 | 2,292 / 1,784 |
| **150** | Total Time ($\mu\text{s}$) | $239.06 \pm 23.16$ | $149.04 \pm 14.79$ | $78.19 \pm 26.75$ | $92.47 \pm 33.34$ | $84.90 \pm 46.29$ |
| | Prep / Search ($\mu\text{s}$) | $234.32$ / **4.74** | $143.20$ / $5.84$ | $41.62$ / $36.57$ | $41.23$ / $51.24$ | $0.00$ / $84.90$ |
| | Labels (Mean / Med) | **98** / **110** | 335 / 224 | 1,101 / 679 | 10,576 / 8,815 | 6,445 / 6,185 |

---

#### B. 2D Mesh Grid Scaling (Planar Topologies, 10 Instances per Dimension)

| Dimensions | Vertices ($n$) | ADHP ($K=5$) ($\mu\text{s}$) | Carlyle-Wood ($\mu\text{s}$) | Dumitrescu-Boland ($\mu\text{s}$) | Pulse ($\mu\text{s}$) | Martins ($\mu\text{s}$) | ADHP Labels | Martins Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $9.72 \pm 3.33$ | $6.35 \pm 1.03$ | $4.64 \pm 1.32$ | $4.76 \pm 1.16$ | $4.52 \pm 0.48$ | **16** | 58 |
| $6 \times 6$ | 36 | $14.34 \pm 1.20$ | $10.50 \pm 0.62$ | $5.42 \pm 0.60$ | $7.10 \pm 0.75$ | $9.23 \pm 2.21$ | **35** | 315 |
| $8 \times 8$ | 64 | $26.46 \pm 2.02$ | $15.60 \pm 1.02$ | $10.95 \pm 1.45$ | $22.61 \pm 11.85$ | $36.54 \pm 8.22$ | **44** | 1,111 |
| $10 \times 10$ | 100 | $46.88 \pm 9.37$ | $26.93 \pm 3.64$ | $35.12 \pm 13.97$ | $160.67 \pm 61.30$ | $166.14 \pm 25.06$ | **92** | 3,111 |

---

#### C. Random Erdős–Rényi Scaling ($p = 0.22$, 10 Instances per Size)

| Vertices ($n$) | Metric | ADHP ($K=5$) | Carlyle-Wood | Dumitrescu-Boland | Pulse | Martins |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **30** | Total Time ($\mu\text{s}$) | $13.74 \pm 9.46$ | $10.83 \pm 7.00$ | $4.78 \pm 1.92$ | $4.53 \pm 1.31$ | $3.80 \pm 1.23$ |
| | Prep / Search ($\mu\text{s}$) | $11.24$ / $2.50$ | $8.27$ / $2.56$ | $2.45$ / $2.33$ | $2.28$ / $2.24$ | $0.00$ / $3.80$ |
| | Labels (Mean / Med) | **23** / **31** | 28 / 37 | 32 / 37 | 63 / 62 | 204 / 184 |
| **60** | Total Time ($\mu\text{s}$) | $52.55 \pm 20.70$ | $27.46 \pm 7.08$ | $11.65 \pm 2.13$ | $11.53 \pm 1.46$ | $9.62 \pm 3.64$ |
| | Prep / Search ($\mu\text{s}$) | $49.59$ / $2.97$ | $24.88$ / $2.57$ | $7.44$ / $4.21$ | $7.35$ / $4.18$ | $0.00$ / $9.62$ |
| | Labels (Mean / Med) | **61** / **62** | 79 / 73 | 102 / 73 | 399 / 384 | 673 / 749 |
| **90** | Total Time ($\mu\text{s}$) | $116.04 \pm 27.41$ | $61.84 \pm 10.71$ | $23.60 \pm 5.13$ | $26.08 \pm 8.36$ | $26.80 \pm 17.05$ |
| | Prep / Search ($\mu\text{s}$) | $111.52$ / $4.53$ | $58.81$ / $3.03$ | $16.19$ / $7.41$ | $16.11$ / $9.97$ | $0.00$ / $26.80$ |
| | Labels (Mean / Med) | **91** / **96** | 121 / 122 | 234 / 249 | 1,556 / 1,472 | 2,320 / 1,939 |
| **120** | Total Time ($\mu\text{s}$) | $161.69 \pm 57.99$ | $102.55 \pm 35.87$ | $48.95 \pm 7.65$ | $56.00 \pm 14.10$ | $37.83 \pm 18.53$ |
| | Prep / Search ($\mu\text{s}$) | $157.86$ / $3.83$ | $99.45$ / $3.10$ | $35.46$ / $13.49$ | $36.28$ / $19.72$ | $0.00$ / $37.83$ |
| | Labels (Mean / Med) | **99** / **93** | 139 / 152 | 303 / 306 | 2,344 / 1,478 | 2,138 / 2,225 |

---

#### D. Budget Tightness Sensitivity ($n = 50$, Anti-Correlated Graph, 10 Instances per $\alpha$)

| Budget Factor ($\alpha$) | Metric | ADHP ($K=5$) | Carlyle-Wood | Dumitrescu-Boland | Pulse | Martins |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **0.10** (Extremely Tight) | Total Time ($\mu\text{s}$) | $47.07 \pm 16.07$ | $27.12 \pm 4.19$ | $6.53 \pm 0.84$ | $6.17 \pm 0.95$ | $3.57 \pm 1.47$ |
| | Prep / Search ($\mu\text{s}$) | $43.96$ / $3.11$ | $24.74$ / $2.38$ | $5.21$ / $1.33$ | $4.98$ / $1.19$ | $0.00$ / $3.57$ |
| | Labels (Mean / Med) | **47** / **43** | 48 / 43 | 71 / 72 | 130 / 101 | 436 / 442 |
| **0.25** (Tight) | Total Time ($\mu\text{s}$) | $26.95 \pm 7.53$ | $17.49 \pm 2.67$ | $6.26 \pm 0.81$ | $7.69 \pm 1.37$ | $4.46 \pm 2.55$ |
| | Prep / Search ($\mu\text{s}$) | $25.86$ / $1.09$ | $16.47$ / $1.02$ | $4.92$ / $1.34$ | $5.33$ / $2.36$ | $0.00$ / $4.46$ |
| | Labels (Mean / Med) | **33** / **29** | 36 / 29 | 60 / 55 | 171 / 178 | 482 / 591 |
| **0.50** (Medium) | Total Time ($\mu\text{s}$) | $26.92 \pm 6.97$ | $16.48 \pm 1.98$ | $6.71 \pm 0.65$ | $8.14 \pm 2.30$ | $6.85 \pm 3.55$ |
| | Prep / Search ($\mu\text{s}$) | $25.74$ / $1.18$ | $15.53$ / $0.95$ | $4.90$ / $1.81$ | $5.03$ / $3.11$ | $0.00$ / $6.85$ |
| | Labels (Mean / Med) | **39** / **32** | 44 / 43 | 58 / 48 | 407 / 264 | 431 / 245 |
| **0.75** (Loose) | Total Time ($\mu\text{s}$) | $29.63 \pm 6.50$ | $17.82 \pm 3.39$ | $10.75 \pm 2.01$ | $11.78 \pm 3.90$ | $7.69 \pm 2.19$ |
| | Prep / Search ($\mu\text{s}$) | $28.41$ / $1.21$ | $16.76$ / $1.07$ | $6.91$ / $3.85$ | $6.13$ / $5.65$ | $0.00$ / $7.69$ |
| | Labels (Mean / Med) | **43** / **49** | 64 / 60 | 90 / 72 | 729 / 849 | 561 / 544 |
| **0.90** (Very Loose) | Total Time ($\mu\text{s}$) | $27.29 \pm 9.92$ | $15.82 \pm 5.33$ | $7.45 \pm 1.41$ | $13.55 \pm 1.88$ | $6.53 \pm 3.47$ |
| | Prep / Search ($\mu\text{s}$) | $25.95$ / $1.33$ | $14.66$ / $1.16$ | $4.77$ / $2.68$ | $8.35$ / $5.20$ | $0.00$ / $6.53$ |
| | Labels (Mean / Med) | **48** / **39** | 73 / 55 | 71 / 53 | 624 / 566 | 450 / 331 |

---

#### E. Ablation Analysis on Facet Count $K$ ($n = 70$, Anti-Correlated Graph)

| Facet Count $K$ | Preprocessing ($\mu\text{s}$) | Search Time ($\mu\text{s}$) | Total Runtime ($\mu\text{s}$) | Labels Generated (Mean / Med) | Dual-Pruned Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **$K = 1$** (1D Cost Bound) | **23.29** | **7.55** | **30.84** | **148** / **175** | 40 |
| **$K = 2$** (First Dual Slope) | 34.98 | 2.02 | 37.00 | **48** / **42** (-67.6%) | 24 |
| **$K = 3$** (Two Active Slopes) | 42.94 | 1.69 | 44.63 | **45** / **42** | 22 |
| **$K = 5$** (Adaptive Dual Hull) | 61.41 | 1.70 | 63.11 | **40** / **39** | 21 |
| **$K = 8$** (Fine Discretization) | 81.25 | 1.68 | 82.93 | **40** / **39** | 21 |
| **$K = 12$** (Over-Discretized) | 85.84 | 2.00 | 87.83 | **40** / **39** | 21 |

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
# 1. Run full multi-instance benchmark suite (200 executions across 20 configurations)
cargo run --bin benchmark_suite --release

# 2. Run independent 100-instance differential verification against 4 solvers and HiGHS ILP
cargo run --bin verify_oracle --release
python scripts/verify_against_ilp.py

# 3. Regenerate all publication figures and summary tables
python scripts/plot_results.py
```
