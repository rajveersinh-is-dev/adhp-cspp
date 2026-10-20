# COMPREHENSIVE BENCHMARK REPORT
## Empirical Evaluation of Adaptive Dual Hull Pruning (ADHP) and Adaptive Hybrid Solver vs Established State-of-the-Art Solvers

**Author**: Rajveersinh Vishal Pardeshi  
**Repository**: [https://github.com/rajveersinh-is-dev/adhp-cspp](https://github.com/rajveersinh-is-dev/adhp-cspp)  
**Date**: October 2026 (Revised Post-Audit)  
**Document**: `research/BENCHMARK_REPORT.md`  
**Data Sources**: `results/raw/benchmark_raw.csv`, `results/raw/benchmark_raw.json`, `results/processed/summary_table.csv`  

---

### 1. Executive Summary & Honest Scientific Assessment

Across **25 systematic configurations comprising 250 configuration-instance evaluations across 200 distinct generated graphs** (190 distinct graphs across Suites 1–4 plus 10 controlled repeated graphs in Suite 5), evaluated under 5 discarded warmup runs and 3 repeated trials per instance using in-process monotonic timing (`std::time::Instant`):

1. **State-Space Pruning Power (Search Phase)**:
   - On **Anti-Correlated** networks (severe trade-offs between cost and resource consumption), ADHP and Adaptive Hybrid ADHP achieve orders-of-magnitude candidate label suppression:
     - On $n=100$ anti-correlated graphs: ADHP generates only **79 labels** vs. **2,751 labels** for Martins (**97.1% label reduction**).
     - On $n=150$ anti-correlated graphs: ADHP generates **964 labels** and Adaptive Hybrid ADHP generates **1,101 labels**, compared to **6,319 labels** for Martins and **10,801 labels** for Pulse (**89.8% reduction vs Pulse**).
   - On **2D Mesh Grids** ($10 \times 10$, $n=100$): ADHP generates only **105 labels** and Adaptive Hybrid ADHP generates **136 labels**, compared to **3,111 labels** for Martins (**95.6% reduction**) and **4,741 labels** for Pulse (**97.1% reduction**).

2. **Total End-to-End Wall-Clock Performance Across All Graph Topologies**:
   - **Planar Grid Networks ($10 \times 10$)**: Where candidate paths proliferate exponentially, Adaptive Hybrid ADHP is the **fastest solver overall at $19.97 \, \mu\text{s}** (and fixed ADHP at $38.24 \, \mu\text{s}), outperforming Dumitrescu-Boland ($32.22 \, \mu\text{s}), Carlyle-Wood ($43.07 \, \mu\text{s}), Pulse ($124.91 \, \mu\text{s}$, a **$6.3\times$ speedup**), and Martins ($163.82 \, \mu\text{s}$, a **$8.2\times$ speedup**).
   - **Large Anti-Correlated Networks ($n = 150$)**: In dense, high-tradeoff regimes, Dumitrescu-Boland achieves $69.13 \, \mu\text{s}$, Martins achieves $73.51 \, \mu\text{s}$, and Adaptive Hybrid ADHP achieves $74.23 \, \mu\text{s}$, outperforming Pulse ($87.92 \, \mu\text{s}$), fixed ADHP ($114.03 \, \mu\text{s}$), and Carlyle-Wood ($162.91 \, \mu\text{s}$).
   - **Random Erdős–Rényi Networks ($n = 90$)**: Martins achieves $26.44 \, \mu\text{s}$ and Adaptive Hybrid ADHP achieves $28.47 \, \mu\text{s}$, outperforming Pulse ($37.85 \, \mu\text{s}$), Dumitrescu-Boland ($39.14 \, \mu\text{s}$), fixed ADHP ($45.08 \, \mu\text{s}$), and Carlyle-Wood ($66.83 \, \mu\text{s}$).

3. **Honest Accounting of Limitations & Baselines**:
   - **Where Martins Wins**: On small graphs ($n \le 40$) and small random networks, unguided search settles so quickly ($< 15 \, \mu\text{s}$) that zero-preprocessing Martins achieves the lowest wall-clock time (e.g., $3.89 \, \mu\text{s}$ on Random ER $n=30$ vs $5.70 \, \mu\text{s}$ for Adaptive Hybrid ADHP).
   - **Where Pulse Wins**: On small grid graphs ($6 \times 6$), Pulse's depth-first search finds the optimum in $15.03 \, \mu\text{s}$.
   - **Ablation Plateau**: The marginal utility of dual facets plateaus beyond $K=2$. Adding facets beyond $K=3$ increases preprocessing time without further reducing forward search labels.

---

### 2. Full Benchmark Results Across All 5 Suites

#### A. Anti-Correlated Graph Scaling ($p = 0.25$, $\alpha = 0.40$, 10 Instances per Size)

| Nodes ($n$) | Metric | Adaptive Hybrid ADHP | ADHP ($K=5$) | Carlyle-Wood | Dumitrescu-Boland | Pulse | Martins |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **20** | Total Time ($\mu\text{s}$) | $6.18 \pm 1.02$ | $10.92 \pm 2.98$ | $15.33 \pm 2.49$ | **$3.39 \pm 0.36$** | $3.89 \pm 0.82$ | $3.50 \pm 0.86$ |
| | Prep / Search ($\mu\text{s}$) | $3.33$ / $2.85$ | $8.37$ / $2.56$ | $12.81$ / $2.52$ | $1.90$ / $1.49$ | $1.98$ / $1.91$ | $0.00$ / $3.50$ |
| | Labels (Mean / Med) | 20 / 16 | **18** / **15** | 20 / 16 | 20 / 16 | 25 / 24 | 97 / 75 |
| **40** | Total Time ($\mu\text{s}$) | $9.81 \pm 1.97$ | $13.52 \pm 3.92$ | $14.09 \pm 3.83$ | $10.84 \pm 2.34$ | $11.80 \pm 2.13$ | **$6.87 \pm 2.26$** |
| | Prep / Search ($\mu\text{s}$) | $6.63$ / $3.19$ | $12.02$ / $1.50$ | $12.95$ / $1.14$ | $7.63$ / $3.21$ | $9.10$ / $2.69$ | $0.00$ / $6.87$ |
| | Labels (Mean / Med) | 46 / 55 | **38** / **39** | 34 / 34 | 47 / 55 | 94 / 86 | 316 / 333 |
| **60** | Total Time ($\mu\text{s}$) | $17.35 \pm 3.06$ | $30.80 \pm 10.10$ | $35.99 \pm 6.08$ | $19.91 \pm 3.56$ | $20.30 \pm 3.90$ | **$11.88 \pm 5.60$** |
| | Prep / Search ($\mu\text{s}$) | $11.19$ / $6.16$ | $27.49$ / $3.31$ | $33.88$ / $2.12$ | $12.97$ / $6.94$ | $12.94$ / $7.36$ | $0.00$ / $11.88$ |
| | Labels (Mean / Med) | 123 / 123 | **87** / **94** | 76 / 52 | 123 / 123 | 502 / 475 | 957 / 1068 |
| **80** | Total Time ($\mu\text{s}$) | $27.22 \pm 6.38$ | $35.33 \pm 12.62$ | $45.92 \pm 7.97$ | $21.80 \pm 3.98$ | $21.45 \pm 3.48$ | **$16.15 \pm 6.67$** |
| | Prep / Search ($\mu\text{s}$) | $19.45$ / $7.77$ | $32.57$ / $2.76$ | $44.44$ / $1.48$ | $15.03$ / $6.77$ | $15.30$ / $6.15$ | $0.00$ / $16.15$ |
| | Labels (Mean / Med) | 191 / 176 | **140** / **94** | 103 / 94 | 191 / 176 | 681 / 603 | 1478 / 1418 |
| **100** | Total Time ($\mu\text{s}$) | $32.80 \pm 8.32$ | $64.08 \pm 20.95$ | $77.75 \pm 15.85$ | $32.55 \pm 7.97$ | $32.52 \pm 5.62$ | **$25.67 \pm 16.70$** |
| | Prep / Search ($\mu\text{s}$) | $22.38$ / $10.42$ | $62.40$ / $1.68$ | $75.60$ / $2.14$ | $22.35$ / $10.20$ | $21.97$ / $10.55$ | $0.00$ / $25.67$ |
| | Labels (Mean / Med) | 495 / 263 | **79** / **80** | 103 / 86 | 495 / 263 | 1886 / 1960 | 2751 / 1884 |
| **150** | Total Time ($\mu\text{s}$) | $74.23 \pm 21.14$ | $114.03 \pm 19.96$ | $162.91 \pm 25.88$ | **$69.13 \pm 19.27$** | $87.92 \pm 30.06$ | $73.51 \pm 54.79$ |
| | Prep / Search ($\mu\text{s}$) | $46.84$ / $27.39$ | $94.61$ / $19.42$ | $155.65$ / $7.26$ | $45.03$ / $24.10$ | $46.57$ / $41.35$ | $0.00$ / $73.51$ |
| | Labels (Mean / Med) | 1101 / 679 | **964** / **542** | 335 / 224 | 1101 / 679 | 8641 / 7664 | 6319 / 5550 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **20** | Total Time ($\mu\text{s}$) | $6.18 \pm 1.02$ | $10.92 \pm 2.98$ | $15.33 \pm 2.49$ | **$3.39 \pm 0.36$** | $3.89 \pm 0.82$ | $3.50 \pm 0.86$ |
| | Prep / Search ($\mu\text{s}$) | $3.33$ / $2.85$ | $8.37$ / $2.56$ | $12.81$ / $2.52$ | $1.90$ / $1.49$ | $1.98$ / $1.91$ | $0.00$ / $3.50$ |
| | Labels (Mean / Med) | 20 / 16 | **18** / **15** | 20 / 16 | 20 / 16 | 25 / 24 | 97 / 75 |
| **40** | Total Time ($\mu\text{s}$) | $9.81 \pm 1.97$ | $13.52 \pm 3.92$ | $14.09 \pm 3.83$ | $10.84 \pm 2.34$ | $11.80 \pm 2.13$ | **$6.87 \pm 2.26$** |
| | Prep / Search ($\mu\text{s}$) | $6.63$ / $3.19$ | $12.02$ / $1.50$ | $12.95$ / $1.14$ | $7.63$ / $3.21$ | $9.10$ / $2.69$ | $0.00$ / $6.87$ |
| | Labels (Mean / Med) | 46 / 55 | **38** / **39** | 34 / 34 | 47 / 55 | 94 / 86 | 316 / 333 |
| **60** | Total Time ($\mu\text{s}$) | $17.35 \pm 3.06$ | $30.80 \pm 10.10$ | $35.99 \pm 6.08$ | $19.91 \pm 3.56$ | $20.30 \pm 3.90$ | **$11.88 \pm 5.60$** |
| | Prep / Search ($\mu\text{s}$) | $11.19$ / $6.16$ | $27.49$ / $3.31$ | $33.88$ / $2.12$ | $12.97$ / $6.94$ | $12.94$ / $7.36$ | $0.00$ / $11.88$ |
| | Labels (Mean / Med) | 123 / 123 | **87** / **94** | 76 / 52 | 123 / 123 | 502 / 475 | 957 / 1068 |
| **80** | Total Time ($\mu\text{s}$) | $27.22 \pm 6.38$ | $35.33 \pm 12.62$ | $45.92 \pm 7.97$ | $21.80 \pm 3.98$ | $21.45 \pm 3.48$ | **$16.15 \pm 6.67$** |
| | Prep / Search ($\mu\text{s}$) | $19.45$ / $7.77$ | $32.57$ / $2.76$ | $44.44$ / $1.48$ | $15.03$ / $6.77$ | $15.30$ / $6.15$ | $0.00$ / $16.15$ |
| | Labels (Mean / Med) | 191 / 176 | **140** / **94** | 103 / 94 | 191 / 176 | 681 / 603 | 1478 / 1418 |
| **100** | Total Time ($\mu\text{s}$) | $32.80 \pm 8.32$ | $64.08 \pm 20.95$ | $77.75 \pm 15.85$ | $32.55 \pm 7.97$ | $32.52 \pm 5.62$ | **$25.67 \pm 16.70$** |
| | Prep / Search ($\mu\text{s}$) | $22.38$ / $10.42$ | $62.40$ / $1.68$ | $75.60$ / $2.14$ | $22.35$ / $10.20$ | $21.97$ / $10.55$ | $0.00$ / $25.67$ |
| | Labels (Mean / Med) | 495 / 263 | **79** / **80** | 103 / 86 | 495 / 263 | 1886 / 1960 | 2751 / 1884 |
| **150** | Total Time ($\mu\text{s}$) | $74.23 \pm 21.14$ | $114.03 \pm 19.96$ | $162.91 \pm 25.88$ | **$69.13 \pm 19.27$** | $87.92 \pm 30.06$ | $73.51 \pm 54.79$ |
| | Prep / Search ($\mu\text{s}$) | $46.84$ / $27.39$ | $94.61$ / $19.42$ | $155.65$ / $7.26$ | $45.03$ / $24.10$ | $46.57$ / $41.35$ | $0.00$ / $73.51$ |
| | Labels (Mean / Med) | 1101 / 679 | **964** / **542** | 335 / 224 | 1101 / 679 | 8641 / 7664 | 6319 / 5550 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **20** | Total Time ($\mu\text{s}$) | $6.18 \pm 1.02$ | $10.92 \pm 2.98$ | $15.33 \pm 2.49$ | **$3.39 \pm 0.36$** | $3.89 \pm 0.82$ | $3.50 \pm 0.86$ |
| | Prep / Search ($\mu\text{s}$) | $3.33$ / $2.85$ | $8.37$ / $2.56$ | $12.81$ / $2.52$ | $1.90$ / $1.49$ | $1.98$ / $1.91$ | $0.00$ / $3.50$ |
| | Labels (Mean / Med) | 20 / 16 | **18** / **15** | 20 / 16 | 20 / 16 | 25 / 24 | 97 / 75 |
| **40** | Total Time ($\mu\text{s}$) | $9.81 \pm 1.97$ | $13.52 \pm 3.92$ | $14.09 \pm 3.83$ | $10.84 \pm 2.34$ | $11.80 \pm 2.13$ | **$6.87 \pm 2.26$** |
| | Prep / Search ($\mu\text{s}$) | $6.63$ / $3.19$ | $12.02$ / $1.50$ | $12.95$ / $1.14$ | $7.63$ / $3.21$ | $9.10$ / $2.69$ | $0.00$ / $6.87$ |
| | Labels (Mean / Med) | 46 / 55 | **38** / **39** | 34 / 34 | 47 / 55 | 94 / 86 | 316 / 333 |
| **60** | Total Time ($\mu\text{s}$) | $17.35 \pm 3.06$ | $30.80 \pm 10.10$ | $35.99 \pm 6.08$ | $19.91 \pm 3.56$ | $20.30 \pm 3.90$ | **$11.88 \pm 5.60$** |
| | Prep / Search ($\mu\text{s}$) | $11.19$ / $6.16$ | $27.49$ / $3.31$ | $33.88$ / $2.12$ | $12.97$ / $6.94$ | $12.94$ / $7.36$ | $0.00$ / $11.88$ |
| | Labels (Mean / Med) | 123 / 123 | **87** / **94** | 76 / 52 | 123 / 123 | 502 / 475 | 957 / 1068 |
| **80** | Total Time ($\mu\text{s}$) | $27.22 \pm 6.38$ | $35.33 \pm 12.62$ | $45.92 \pm 7.97$ | $21.80 \pm 3.98$ | $21.45 \pm 3.48$ | **$16.15 \pm 6.67$** |
| | Prep / Search ($\mu\text{s}$) | $19.45$ / $7.77$ | $32.57$ / $2.76$ | $44.44$ / $1.48$ | $15.03$ / $6.77$ | $15.30$ / $6.15$ | $0.00$ / $16.15$ |
| | Labels (Mean / Med) | 191 / 176 | **140** / **94** | 103 / 94 | 191 / 176 | 681 / 603 | 1478 / 1418 |
| **100** | Total Time ($\mu\text{s}$) | $32.80 \pm 8.32$ | $64.08 \pm 20.95$ | $77.75 \pm 15.85$ | $32.55 \pm 7.97$ | $32.52 \pm 5.62$ | **$25.67 \pm 16.70$** |
| | Prep / Search ($\mu\text{s}$) | $22.38$ / $10.42$ | $62.40$ / $1.68$ | $75.60$ / $2.14$ | $22.35$ / $10.20$ | $21.97$ / $10.55$ | $0.00$ / $25.67$ |
| | Labels (Mean / Med) | 495 / 263 | **79** / **80** | 103 / 86 | 495 / 263 | 1886 / 1960 | 2751 / 1884 |
| **150** | Total Time ($\mu\text{s}$) | $74.23 \pm 21.14$ | $114.03 \pm 19.96$ | $162.91 \pm 25.88$ | **$69.13 \pm 19.27$** | $87.92 \pm 30.06$ | $73.51 \pm 54.79$ |
| | Prep / Search ($\mu\text{s}$) | $46.84$ / $27.39$ | $94.61$ / $19.42$ | $155.65$ / $7.26$ | $45.03$ / $24.10$ | $46.57$ / $41.35$ | $0.00$ / $73.51$ |
| | Labels (Mean / Med) | 1101 / 679 | **964** / **542** | 335 / 224 | 1101 / 679 | 8641 / 7664 | 6319 / 5550 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **20** | Total Time ($\mu\text{s}$) | $5.72 \pm 0.90$ | $12.27 \pm 4.30$ | $16.19 \pm 3.10$ | **$3.19 \pm 0.60$** | $3.65 \pm 0.80$ | $3.94 \pm 1.20$ |
| | Prep / Search ($\mu\text{s}$) | $3.80$ / $1.92$ | $10.15$ / $2.12$ | $13.50$ / $2.69$ | $2.10$ / $1.09$ | $2.05$ / $1.60$ | $0.00$ / $3.94$ |
| | Labels (Mean / Med) | 20 / 16 | **18** / **15** | 20 / 16 | 20 / 16 | 32 / 34 | 97 / 75 |
| **40** | Total Time ($\mu\text{s}$) | $10.47 \pm 2.10$ | $13.61 \pm 3.20$ | $16.89 \pm 4.10$ | $8.13 \pm 1.80$ | **$7.41 \pm 1.50$** | $7.50 \pm 1.90$ |
| | Prep / Search ($\mu\text{s}$) | $7.50$ / $2.97$ | $10.80$ / $2.81$ | $14.20$ / $2.69$ | $5.20$ / $2.93$ | $4.80$ / $2.61$ | $0.00$ / $7.50$ |
| | Labels (Mean / Med) | 46 / 42 | **38** / **39** | 34 / 34 | 47 / 55 | 106 / 100 | 316 / 333 |
| **60** | Total Time ($\mu\text{s}$) | $19.41 \pm 4.50$ | $31.09 \pm 8.20$ | $34.66 \pm 5.64$ | $17.52 \pm 3.92$ | $19.41 \pm 6.29$ | **$13.35 \pm 6.95$** |
| | Prep / Search ($\mu\text{s}$) | $14.20$ / $5.21$ | $26.50$ / $4.59$ | $32.45$ / $2.21$ | $10.68$ / $6.84$ | $10.52$ / $8.89$ | $0.00$ / $13.35$ |
| | Labels (Mean / Med) | 123 / 123 | **87** / **94** | 76 / 52 | 123 / 123 | 855 / 515 | 957 / 1068 |
| **80** | Total Time ($\mu\text{s}$) | $29.24 \pm 6.69$ | $41.68 \pm 20.29$ | $62.01 \pm 12.81$ | $26.98 \pm 3.63$ | $30.45 \pm 11.52$ | **$25.65 \pm 14.02$** |
| | Prep / Search ($\mu\text{s}$) | $19.35$ / $9.89$ | $38.05$ / $3.63$ | $59.46$ / $2.55$ | $18.31$ / $8.67$ | $18.70$ / $11.75$ | $0.00$ / $25.65$ |
| | Labels (Mean / Med) | 191 / 176 | **140** / **94** | 103 / 94 | 191 / 176 | 1087 / 700 | 1478 / 1418 |
| **100** | Total Time ($\mu\text{s}$) | $45.41 \pm 16.01$ | $75.89 \pm 22.89$ | $70.13 \pm 12.08$ | $35.21 \pm 8.73$ | $38.15 \pm 6.85$ | **$33.34 \pm 22.85$** |
| | Prep / Search ($\mu\text{s}$) | $27.83$ / $17.58$ | $72.84$ / $3.05$ | $67.88$ / $2.25$ | $22.61$ / $12.60$ | $22.27$ / $15.88$ | $0.00$ / $33.34$ |
| | Labels (Mean / Med) | 495 / 263 | **79** / **80** | 103 / 86 | 495 / 263 | 2021 / 2135 | 2751 / 1884 |
| **150** | Total Time ($\mu\text{s}$) | **$76.92 \pm 28.29$** | $98.67 \pm 15.99$ | $160.42 \pm 22.11$ | $97.87 \pm 54.96$ | $141.58 \pm 52.02$ | $90.25 \pm 65.97$ |
| | Prep / Search ($\mu\text{s}$) | $45.24$ / $31.68$ | $80.93$ / $17.74$ | $153.69$ / $6.73$ | $50.91$ / $46.96$ | $63.55$ / $78.03$ | $0.00$ / $90.25$ |
| | Labels (Mean / Med) | 1101 / 679 | **964** / **542** | 335 / 224 | 1101 / 679 | 10801 / 8939 | 6319 / 5550 |

---

#### B. 2D Mesh Grid Scaling (Planar Directed Acyclic Graph Topologies: right, down, diagonal transitions; 10 Instances per Dimension)

| Dimensions | Vertices ($n$) | Adaptive Hybrid ADHP | ADHP ($K=5$) | Carlyle-Wood | Dumitrescu-Boland | Pulse | Martins |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $7.52 \pm 1.23$ | $6.64 \pm 1.52$ | $11.82 \pm 3.22$ | $9.31 \pm 0.81$ | $12.77 \pm 1.57$ | **$6.38 \pm 0.63$** |
| $6 \times 6$ | 36 | $17.81 \pm 2.13$ | $20.21 \pm 3.90$ | $22.58 \pm 1.64$ | **$10.16 \pm 1.23$** | $15.43 \pm 1.87$ | $14.23 \pm 2.58$ |
| $8 \times 8$ | 64 | $20.10 \pm 3.04$ | $40.73 \pm 7.34$ | $31.43 \pm 4.96$ | **$17.62 \pm 2.12$** | $26.93 \pm 12.25$ | $31.67 \pm 4.16$ |
| $10 \times 10$ | 100 | **$19.97 \pm 4.22$** | $38.24 \pm 14.09$ | $43.07 \pm 8.52$ | $32.22 \pm 12.08$ | $124.91 \pm 51.29$ | $163.82 \pm 35.61$ |

---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $7.52 \pm 1.23$ | $6.64 \pm 1.52$ | $11.82 \pm 3.22$ | $9.31 \pm 0.81$ | $12.77 \pm 1.57$ | **$6.38 \pm 0.63$** |
| $6 \times 6$ | 36 | $17.81 \pm 2.13$ | $20.21 \pm 3.90$ | $22.58 \pm 1.64$ | **$10.16 \pm 1.23$** | $15.43 \pm 1.87$ | $14.23 \pm 2.58$ |
| $8 \times 8$ | 64 | $20.10 \pm 3.04$ | $40.73 \pm 7.34$ | $31.43 \pm 4.96$ | **$17.62 \pm 2.12$** | $26.93 \pm 12.25$ | $31.67 \pm 4.16$ |
| $10 \times 10$ | 100 | **$19.97 \pm 4.22$** | $38.24 \pm 14.09$ | $43.07 \pm 8.52$ | $32.22 \pm 12.08$ | $124.91 \pm 51.29$ | $163.82 \pm 35.61$ |

---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $7.52 \pm 1.23$ | $6.64 \pm 1.52$ | $11.82 \pm 3.22$ | $9.31 \pm 0.81$ | $12.77 \pm 1.57$ | **$6.38 \pm 0.63$** |
| $6 \times 6$ | 36 | $17.81 \pm 2.13$ | $20.21 \pm 3.90$ | $22.58 \pm 1.64$ | **$10.16 \pm 1.23$** | $15.43 \pm 1.87$ | $14.23 \pm 2.58$ |
| $8 \times 8$ | 64 | $20.10 \pm 3.04$ | $40.73 \pm 7.34$ | $31.43 \pm 4.96$ | **$17.62 \pm 2.12$** | $26.93 \pm 12.25$ | $31.67 \pm 4.16$ |
| $10 \times 10$ | 100 | **$19.97 \pm 4.22$** | $38.24 \pm 14.09$ | $43.07 \pm 8.52$ | $32.22 \pm 12.08$ | $124.91 \pm 51.29$ | $163.82 \pm 35.61$ |

---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $4 \times 4$ | 16 | $11.79 \pm 4.55$ | $9.73 \pm 0.94$ | $11.32 \pm 2.50$ | $9.29 \pm 0.82$ | $10.72 \pm 0.70$ | **$6.03 \pm 0.58$** |
| $6 \times 6$ | 36 | $18.36 \pm 7.30$ | $16.89 \pm 3.47$ | $18.15 \pm 0.94$ | $21.49 \pm 25.16$ | **$15.03 \pm 3.31$** | $15.88 \pm 2.25$ |
| $8 \times 8$ | 64 | $16.48 \pm 2.44$ | $25.38 \pm 5.49$ | $34.73 \pm 7.19$ | **$16.00 \pm 4.17$** | $42.76 \pm 16.87$ | $55.89 \pm 25.98$ |
| $10 \times 10$ | 100 | **$33.74 \pm 14.23$** | $38.96 \pm 16.07$ | $54.82 \pm 14.64$ | $46.40 \pm 20.46$ | $189.17 \pm 64.00$ | $242.01 \pm 77.37$ |

*Labels Generated on Grid $10 \times 10$*:
- **ADHP ($K=5$)**: **105 labels** (96.6% reduction vs Martins)
- **Adaptive Hybrid ADHP**: **136 labels** (95.6% reduction vs Martins)
- Carlyle-Wood: 115 labels
- Dumitrescu-Boland: 662 labels
- Martins: 3,111 labels
- Pulse: 4,741 labels

---

#### C. Random Erdős–Rényi Scaling ($p = 0.20$, 10 Instances per Size)

| Vertices ($n$) | Metric | Adaptive Hybrid ADHP | ADHP ($K=5$) | Carlyle-Wood | Dumitrescu-Boland | Pulse | Martins |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **30** | Total Time ($\mu\text{s}$) | $5.70 \pm 1.26$ | $12.38 \pm 6.63$ | $11.23 \pm 7.35$ | $5.48 \pm 0.81$ | $6.09 \pm 0.98$ | **$3.89 \pm 1.32$** |
| | Prep / Search ($\mu\text{s}$) | $3.59$ / $2.11$ | $9.74$ / $2.64$ | $9.02$ / $2.21$ | $3.13$ / $2.35$ | $3.10$ / $2.99$ | $0.00$ / $3.89$ |
| | Labels (Mean / Med) | 27 / 37 | **24** / **31** | 28 / 37 | 32 / 37 | 47 / 44 | 204 / 184 |
| **60** | Total Time ($\mu\text{s}$) | **$15.41 \pm 2.79$** | $24.85 \pm 8.89$ | $32.30 \pm 5.81$ | $16.43 \pm 1.81$ | $17.20 \pm 1.69$ | $84.56 \pm 220.39$ |
| | Prep / Search ($\mu\text{s}$) | $11.27$ / $4.15$ | $22.13$ / $2.71$ | $29.63$ / $2.67$ | $11.02$ / $5.41$ | $11.77$ / $5.43$ | $0.00$ / $84.56$ |
| | Labels (Mean / Med) | 102 / 73 | **84** / **73** | 79 / 73 | 102 / 73 | 293 / 217 | 673 / 749 |
| **90** | Total Time ($\mu\text{s}$) | $28.47 \pm 7.49$ | $45.08 \pm 14.71$ | $66.83 \pm 15.67$ | $39.14 \pm 9.31$ | $37.85 \pm 10.56$ | **$26.44 \pm 21.61$** |
| | Prep / Search ($\mu\text{s}$) | $21.19$ / $7.28$ | $41.55$ / $3.52$ | $64.11$ / $2.73$ | $26.21$ / $12.93$ | $24.55$ / $13.29$ | $0.00$ / $26.44$ |
| | Labels (Mean / Med) | 234 / 249 | **181** / **116** | 121 / 122 | 234 / 249 | 964 / 855 | 2320 / 1939 |
| **120** | Total Time ($\mu\text{s}$) | $50.92 \pm 6.38$ | $79.41 \pm 26.86$ | $115.58 \pm 35.08$ | $50.91 \pm 9.71$ | $53.21 \pm 15.83$ | **$21.50 \pm 11.31$** |
| | Prep / Search ($\mu\text{s}$) | $40.92$ / $10.00$ | $74.41$ / $5.00$ | $111.99$ / $3.59$ | $40.65$ / $10.26$ | $38.42$ / $14.79$ | $0.00$ / $21.50$ |
| | Labels (Mean / Med) | 300 / 306 | **190** / **218** | 139 / 152 | 303 / 306 | 1966 / 1428 | 2138 / 2225 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **30** | Total Time ($\mu\text{s}$) | $5.70 \pm 1.26$ | $12.38 \pm 6.63$ | $11.23 \pm 7.35$ | $5.48 \pm 0.81$ | $6.09 \pm 0.98$ | **$3.89 \pm 1.32$** |
| | Prep / Search ($\mu\text{s}$) | $3.59$ / $2.11$ | $9.74$ / $2.64$ | $9.02$ / $2.21$ | $3.13$ / $2.35$ | $3.10$ / $2.99$ | $0.00$ / $3.89$ |
| | Labels (Mean / Med) | 27 / 37 | **24** / **31** | 28 / 37 | 32 / 37 | 47 / 44 | 204 / 184 |
| **60** | Total Time ($\mu\text{s}$) | **$15.41 \pm 2.79$** | $24.85 \pm 8.89$ | $32.30 \pm 5.81$ | $16.43 \pm 1.81$ | $17.20 \pm 1.69$ | $84.56 \pm 220.39$ |
| | Prep / Search ($\mu\text{s}$) | $11.27$ / $4.15$ | $22.13$ / $2.71$ | $29.63$ / $2.67$ | $11.02$ / $5.41$ | $11.77$ / $5.43$ | $0.00$ / $84.56$ |
| | Labels (Mean / Med) | 102 / 73 | **84** / **73** | 79 / 73 | 102 / 73 | 293 / 217 | 673 / 749 |
| **90** | Total Time ($\mu\text{s}$) | $28.47 \pm 7.49$ | $45.08 \pm 14.71$ | $66.83 \pm 15.67$ | $39.14 \pm 9.31$ | $37.85 \pm 10.56$ | **$26.44 \pm 21.61$** |
| | Prep / Search ($\mu\text{s}$) | $21.19$ / $7.28$ | $41.55$ / $3.52$ | $64.11$ / $2.73$ | $26.21$ / $12.93$ | $24.55$ / $13.29$ | $0.00$ / $26.44$ |
| | Labels (Mean / Med) | 234 / 249 | **181** / **116** | 121 / 122 | 234 / 249 | 964 / 855 | 2320 / 1939 |
| **120** | Total Time ($\mu\text{s}$) | $50.92 \pm 6.38$ | $79.41 \pm 26.86$ | $115.58 \pm 35.08$ | $50.91 \pm 9.71$ | $53.21 \pm 15.83$ | **$21.50 \pm 11.31$** |
| | Prep / Search ($\mu\text{s}$) | $40.92$ / $10.00$ | $74.41$ / $5.00$ | $111.99$ / $3.59$ | $40.65$ / $10.26$ | $38.42$ / $14.79$ | $0.00$ / $21.50$ |
| | Labels (Mean / Med) | 300 / 306 | **190** / **218** | 139 / 152 | 303 / 306 | 1966 / 1428 | 2138 / 2225 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **30** | Total Time ($\mu\text{s}$) | $5.70 \pm 1.26$ | $12.38 \pm 6.63$ | $11.23 \pm 7.35$ | $5.48 \pm 0.81$ | $6.09 \pm 0.98$ | **$3.89 \pm 1.32$** |
| | Prep / Search ($\mu\text{s}$) | $3.59$ / $2.11$ | $9.74$ / $2.64$ | $9.02$ / $2.21$ | $3.13$ / $2.35$ | $3.10$ / $2.99$ | $0.00$ / $3.89$ |
| | Labels (Mean / Med) | 27 / 37 | **24** / **31** | 28 / 37 | 32 / 37 | 47 / 44 | 204 / 184 |
| **60** | Total Time ($\mu\text{s}$) | **$15.41 \pm 2.79$** | $24.85 \pm 8.89$ | $32.30 \pm 5.81$ | $16.43 \pm 1.81$ | $17.20 \pm 1.69$ | $84.56 \pm 220.39$ |
| | Prep / Search ($\mu\text{s}$) | $11.27$ / $4.15$ | $22.13$ / $2.71$ | $29.63$ / $2.67$ | $11.02$ / $5.41$ | $11.77$ / $5.43$ | $0.00$ / $84.56$ |
| | Labels (Mean / Med) | 102 / 73 | **84** / **73** | 79 / 73 | 102 / 73 | 293 / 217 | 673 / 749 |
| **90** | Total Time ($\mu\text{s}$) | $28.47 \pm 7.49$ | $45.08 \pm 14.71$ | $66.83 \pm 15.67$ | $39.14 \pm 9.31$ | $37.85 \pm 10.56$ | **$26.44 \pm 21.61$** |
| | Prep / Search ($\mu\text{s}$) | $21.19$ / $7.28$ | $41.55$ / $3.52$ | $64.11$ / $2.73$ | $26.21$ / $12.93$ | $24.55$ / $13.29$ | $0.00$ / $26.44$ |
| | Labels (Mean / Med) | 234 / 249 | **181** / **116** | 121 / 122 | 234 / 249 | 964 / 855 | 2320 / 1939 |
| **120** | Total Time ($\mu\text{s}$) | $50.92 \pm 6.38$ | $79.41 \pm 26.86$ | $115.58 \pm 35.08$ | $50.91 \pm 9.71$ | $53.21 \pm 15.83$ | **$21.50 \pm 11.31$** |
| | Prep / Search ($\mu\text{s}$) | $40.92$ / $10.00$ | $74.41$ / $5.00$ | $111.99$ / $3.59$ | $40.65$ / $10.26$ | $38.42$ / $14.79$ | $0.00$ / $21.50$ |
| | Labels (Mean / Med) | 300 / 306 | **190** / **218** | 139 / 152 | 303 / 306 | 1966 / 1428 | 2138 / 2225 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **30** | Total Time ($\mu\text{s}$) | $8.61 \pm 1.20$ | $11.17 \pm 2.30$ | $20.84 \pm 4.10$ | $7.67 \pm 1.50$ | $10.90 \pm 3.20$ | **$5.74 \pm 1.10$** |
| | Prep / Search ($\mu\text{s}$) | $5.90$ / $2.71$ | $8.90$ / $2.27$ | $18.20$ / $2.64$ | $4.80$ / $2.87$ | $4.70$ / $6.20$ | $0.00$ / $5.74$ |
| | Labels (Mean / Med) | 27 / 24 | **24** / **24** | 28 / 28 | 32 / 32 | 63 / 63 | 204 / 195 |
| **60** | Total Time ($\mu\text{s}$) | $15.66 \pm 2.80$ | $31.11 \pm 5.40$ | $46.62 \pm 6.80$ | $18.76 \pm 3.20$ | $20.37 \pm 4.50$ | **$13.92 \pm 3.80$** |
| | Prep / Search ($\mu\text{s}$) | $11.20$ / $4.46$ | $26.80$ / $4.31$ | $43.10$ / $3.52$ | $12.40$ / $6.36$ | $12.10$ / $8.27$ | $0.00$ / $13.92$ |
| | Labels (Mean / Med) | 102 / 102 | **84** / **84** | 79 / 79 | 102 / 102 | 399 / 384 | 673 / 640 |
| **90** | Total Time ($\mu\text{s}$) | **$32.40 \pm 5.60$** | $50.80 \pm 8.90$ | $87.48 \pm 12.40$ | $36.90 \pm 6.10$ | $37.82 \pm 7.80$ | $42.18 \pm 15.20$ |
| | Prep / Search ($\mu\text{s}$) | $21.50$ / $10.90$ | $44.20$ / $6.60$ | $82.40$ / $5.08$ | $23.80$ / $13.10$ | $23.10$ / $14.72$ | $0.00$ / $42.18$ |
| | Labels (Mean / Med) | 234 / 234 | **181** / **181** | 121 / 121 | 234 / 234 | 1556 / 1472 | 2320 / 1939 |
| **120** | Total Time ($\mu\text{s}$) | $42.17 \pm 8.40$ | $62.12 \pm 11.50$ | $88.48 \pm 14.80$ | $43.54 \pm 7.90$ | $50.59 \pm 11.20$ | **$29.39 \pm 9.80$** |
| | Prep / Search ($\mu\text{s}$) | $28.60$ / $13.57$ | $54.10$ / $8.02$ | $82.90$ / $5.58$ | $28.10$ / $15.44$ | $28.00$ / $22.59$ | $0.00$ / $29.39$ |
| | Labels (Mean / Med) | 300 / 300 | **190** / **190** | 139 / 139 | 303 / 306 | 2344 / 1478 | 2138 / 2225 |

---

#### D. Budget Tightness Sensitivity ($n = 50$, Anti-Correlated Graph)

| Budget Factor ($\alpha$) | Metric | Adaptive Hybrid ADHP | ADHP ($K=5$) | Carlyle-Wood | Dumitrescu-Boland | Pulse | Martins |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0.10 (Extremely Tight)** | Total Time ($\mu\text{s}$) | $14.56 \pm 1.55$ | $24.75 \pm 7.59$ | $21.82 \pm 4.83$ | $10.76 \pm 1.12$ | $10.29 \pm 0.76$ | **$5.24 \pm 1.79$** |
| | Labels (Mean / Med) | 65 / 64 | **42** / **43** | 42 / 43 | 65 / 64 | 68 / 62 | 429 / 442 |
| **0.25 (Tight)** | Total Time ($\mu\text{s}$) | $10.75 \pm 1.81$ | $17.39 \pm 5.80$ | $27.98 \pm 3.03$ | $10.25 \pm 1.89$ | $8.37 \pm 1.57$ | **$4.80 \pm 2.84$** |
| | Labels (Mean / Med) | 60 / 55 | **33** / **29** | 36 / 29 | 60 / 55 | 87 / 85 | 477 / 572 |
| **0.50 (Medium)** | Total Time ($\mu\text{s}$) | $8.38 \pm 0.93$ | $11.91 \pm 2.54$ | $17.27 \pm 2.13$ | $8.17 \pm 0.95$ | $8.51 \pm 1.82$ | **$5.75 \pm 2.70$** |
| | Labels (Mean / Med) | 58 / 48 | **44** / **41** | 44 / 43 | 58 / 48 | 232 / 109 | 437 / 245 |
| **0.75 (Loose)** | Total Time ($\mu\text{s}$) | $10.50 \pm 2.19$ | $15.80 \pm 6.48$ | $20.04 \pm 3.37$ | $9.46 \pm 1.28$ | $9.43 \pm 1.80$ | **$7.59 \pm 2.41$** |
| | Labels (Mean / Med) | 93 / 72 | **75** / **69** | 64 / 60 | 93 / 72 | 387 / 358 | 563 / 544 |
| **0.90 (Very Loose)** | Total Time ($\mu\text{s}$) | $8.82 \pm 1.55$ | $10.26 \pm 1.51$ | $16.35 \pm 5.03$ | $8.66 \pm 1.30$ | $7.72 \pm 0.77$ | **$6.67 \pm 3.73$** |
| | Labels (Mean / Med) | 70 / 53 | **68** / **53** | 73 / 55 | 71 / 53 | 156 / 161 | 451 / 331 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0.10 (Extremely Tight)** | Total Time ($\mu\text{s}$) | $14.56 \pm 1.55$ | $24.75 \pm 7.59$ | $21.82 \pm 4.83$ | $10.76 \pm 1.12$ | $10.29 \pm 0.76$ | **$5.24 \pm 1.79$** |
| | Labels (Mean / Med) | 65 / 64 | **42** / **43** | 42 / 43 | 65 / 64 | 68 / 62 | 429 / 442 |
| **0.25 (Tight)** | Total Time ($\mu\text{s}$) | $10.75 \pm 1.81$ | $17.39 \pm 5.80$ | $27.98 \pm 3.03$ | $10.25 \pm 1.89$ | $8.37 \pm 1.57$ | **$4.80 \pm 2.84$** |
| | Labels (Mean / Med) | 60 / 55 | **33** / **29** | 36 / 29 | 60 / 55 | 87 / 85 | 477 / 572 |
| **0.50 (Medium)** | Total Time ($\mu\text{s}$) | $8.38 \pm 0.93$ | $11.91 \pm 2.54$ | $17.27 \pm 2.13$ | $8.17 \pm 0.95$ | $8.51 \pm 1.82$ | **$5.75 \pm 2.70$** |
| | Labels (Mean / Med) | 58 / 48 | **44** / **41** | 44 / 43 | 58 / 48 | 232 / 109 | 437 / 245 |
| **0.75 (Loose)** | Total Time ($\mu\text{s}$) | $10.50 \pm 2.19$ | $15.80 \pm 6.48$ | $20.04 \pm 3.37$ | $9.46 \pm 1.28$ | $9.43 \pm 1.80$ | **$7.59 \pm 2.41$** |
| | Labels (Mean / Med) | 93 / 72 | **75** / **69** | 64 / 60 | 93 / 72 | 387 / 358 | 563 / 544 |
| **0.90 (Very Loose)** | Total Time ($\mu\text{s}$) | $8.82 \pm 1.55$ | $10.26 \pm 1.51$ | $16.35 \pm 5.03$ | $8.66 \pm 1.30$ | $7.72 \pm 0.77$ | **$6.67 \pm 3.73$** |
| | Labels (Mean / Med) | 70 / 53 | **68** / **53** | 73 / 55 | 71 / 53 | 156 / 161 | 451 / 331 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0.10 (Extremely Tight)** | Total Time ($\mu\text{s}$) | $14.56 \pm 1.55$ | $24.75 \pm 7.59$ | $21.82 \pm 4.83$ | $10.76 \pm 1.12$ | $10.29 \pm 0.76$ | **$5.24 \pm 1.79$** |
| | Labels (Mean / Med) | 65 / 64 | **42** / **43** | 42 / 43 | 65 / 64 | 68 / 62 | 429 / 442 |
| **0.25 (Tight)** | Total Time ($\mu\text{s}$) | $10.75 \pm 1.81$ | $17.39 \pm 5.80$ | $27.98 \pm 3.03$ | $10.25 \pm 1.89$ | $8.37 \pm 1.57$ | **$4.80 \pm 2.84$** |
| | Labels (Mean / Med) | 60 / 55 | **33** / **29** | 36 / 29 | 60 / 55 | 87 / 85 | 477 / 572 |
| **0.50 (Medium)** | Total Time ($\mu\text{s}$) | $8.38 \pm 0.93$ | $11.91 \pm 2.54$ | $17.27 \pm 2.13$ | $8.17 \pm 0.95$ | $8.51 \pm 1.82$ | **$5.75 \pm 2.70$** |
| | Labels (Mean / Med) | 58 / 48 | **44** / **41** | 44 / 43 | 58 / 48 | 232 / 109 | 437 / 245 |
| **0.75 (Loose)** | Total Time ($\mu\text{s}$) | $10.50 \pm 2.19$ | $15.80 \pm 6.48$ | $20.04 \pm 3.37$ | $9.46 \pm 1.28$ | $9.43 \pm 1.80$ | **$7.59 \pm 2.41$** |
| | Labels (Mean / Med) | 93 / 72 | **75** / **69** | 64 / 60 | 93 / 72 | 387 / 358 | 563 / 544 |
| **0.90 (Very Loose)** | Total Time ($\mu\text{s}$) | $8.82 \pm 1.55$ | $10.26 \pm 1.51$ | $16.35 \pm 5.03$ | $8.66 \pm 1.30$ | $7.72 \pm 0.77$ | **$6.67 \pm 3.73$** |
| | Labels (Mean / Med) | 70 / 53 | **68** / **53** | 73 / 55 | 71 / 53 | 156 / 161 | 451 / 331 |

---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0.10 (Extremely Tight)** | Total Time ($\mu\text{s}$) | $12.72 \pm 2.40$ | $27.24 \pm 5.80$ | $36.24 \pm 8.20$ | $8.81 \pm 1.40$ | $15.80 \pm 4.20$ | **$7.62 \pm 2.10$** |
| | Labels (Mean / Med) | 69 / 64 | **52** / **43** | 51 / 43 | 69 / 64 | 420 / 300 | 471 / 442 |
| **0.25 (Tight)** | Total Time ($\mu\text{s}$) | $11.45 \pm 2.10$ | $18.40 \pm 4.10$ | $25.60 \pm 5.10$ | $8.40 \pm 1.20$ | $12.30 \pm 3.10$ | **$6.80 \pm 1.80$** |
| **0.50 (Medium)** | Total Time ($\mu\text{s}$) | $10.80 \pm 1.90$ | $15.20 \pm 3.40$ | $21.40 \pm 4.20$ | $8.10 \pm 1.10$ | $11.10 \pm 2.80$ | **$6.14 \pm 1.50$** |
| **0.75 (Loose)** | Total Time ($\mu\text{s}$) | $9.80 \pm 1.70$ | $13.10 \pm 2.90$ | $18.20 \pm 3.80$ | $7.90 \pm 1.00$ | $9.80 \pm 2.10$ | **$5.90 \pm 1.40$** |
| **0.90 (Very Loose)** | Total Time ($\mu\text{s}$) | $8.20 \pm 1.50$ | $10.80 \pm 2.20$ | $15.40 \pm 3.10$ | $7.60 \pm 0.90$ | $8.50 \pm 1.90$ | **$5.50 \pm 1.20$** |

---

#### E. Ablation Analysis on Facet Count $K$ ($n = 70$, Anti-Correlated Graph)

| Facet Configuration | Preprocessing ($\mu\text{s}$) | Search Time ($\mu\text{s}$) | Total Runtime ($\mu\text{s}$) | Labels Generated (Mean / Med) | Dual-Pruned Labels |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **ADHP ($K=1$)** | $11.74$ | $4.83$ | **$16.57$** | **146** / **170** | 40 |
| **ADHP ($K=2$)** | $18.37$ | $2.61$ | **$20.99$** | **91** / **42** (-37.7%) | 39 |
| **ADHP ($K=3$)** | $23.30$ | $2.81$ | **$26.11$** | **91** / **42** | 39 |
| **ADHP ($K=5$)** | $26.36$ | $2.39$ | **$28.75$** | **91** / **42** | 39 |
| **ADHP ($K=8$)** | $27.46$ | $2.36$ | **$29.82$** | **91** / **42** | 39 |
| **ADHP ($K=12$)** | $27.13$ | $2.17$ | **$29.30$** | **91** / **42** | 39 |

---:|:---:|:---:|:---:|:---:|:---:|
| **ADHP ($K=1$)** | $11.74$ | $4.83$ | **$16.57$** | **146** / **170** | 40 |
| **ADHP ($K=2$)** | $18.37$ | $2.61$ | **$20.99$** | **91** / **42** (-37.7%) | 39 |
| **ADHP ($K=3$)** | $23.30$ | $2.81$ | **$26.11$** | **91** / **42** | 39 |
| **ADHP ($K=5$)** | $26.36$ | $2.39$ | **$28.75$** | **91** / **42** | 39 |
| **ADHP ($K=8$)** | $27.46$ | $2.36$ | **$29.82$** | **91** / **42** | 39 |
| **ADHP ($K=12$)** | $27.13$ | $2.17$ | **$29.30$** | **91** / **42** | 39 |

---:|:---:|:---:|:---:|:---:|:---:|
| **ADHP ($K=1$)** | $11.74$ | $4.83$ | **$16.57$** | **146** / **170** | 40 |
| **ADHP ($K=2$)** | $18.37$ | $2.61$ | **$20.99$** | **91** / **42** (-37.7%) | 39 |
| **ADHP ($K=3$)** | $23.30$ | $2.81$ | **$26.11$** | **91** / **42** | 39 |
| **ADHP ($K=5$)** | $26.36$ | $2.39$ | **$28.75$** | **91** / **42** | 39 |
| **ADHP ($K=8$)** | $27.46$ | $2.36$ | **$29.82$** | **91** / **42** | 39 |
| **ADHP ($K=12$)** | $27.13$ | $2.17$ | **$29.30$** | **91** / **42** | 39 |

---:|:---:|:---:|:---:|:---:|:---:|
| **ADHP ($K=1$)** | $11.06$ | $4.60$ | **$15.66$** | 146 / 170 | 40 |
| **ADHP ($K=2$)** | $17.78$ | $2.32$ | **$20.10$** | **91** / **42** (-37.7%) | 39 |
| **ADHP ($K=3$)** | $20.78$ | $2.20$ | **$22.98$** | **91** / **42** | 39 |
| **ADHP ($K=5$)** | $25.86$ | $2.21$ | **$28.07$** | **91** / **42** | 39 |
| **ADHP ($K=8$)** | $25.10$ | $2.13$ | **$27.23$** | **91** / **42** | 39 |
| **ADHP ($K=12$)** | $25.39$ | $2.29$ | **$27.68$** | **91** / **42** | 39 |

---

### 3. Summary of Overall Solver Rankings

| Graph Family / Topology | 1st Place (Fastest) | 2nd Place | 3rd Place | ADHP Pruning Reduction |
| :--- | :--- | :--- | :--- | :--- |
| **Planar Grid $10 \times 10$ ($n=100$)** | **Adaptive Hybrid ADHP ($19.97 \, \mu\text{s}$)** | Dumitrescu-Boland ($32.22 \, \mu\text{s}$) | ADHP ($K=5$) ($38.24 \, \mu\text{s}$) | **95.6% vs Martins** |
| **Anti-Correlated $n=150$** | **Dumitrescu-Boland ($69.13 \, \mu\text{s}$)** | Martins ($73.51 \, \mu\text{s}$) | Adaptive Hybrid ADHP ($74.23 \, \mu\text{s}$) | **84.7% vs Martins** |
| **Random ER $n=60$** | **Adaptive Hybrid ADHP ($15.41 \, \mu\text{s}$)** | Dumitrescu-Boland ($16.43 \, \mu\text{s}$) | Pulse ($17.20 \, \mu\text{s}$) | **87.5% vs Martins** |
| **Planar Grid $6 \times 6$ ($n=36$)** | **Dumitrescu-Boland ($10.16 \, \mu\text{s}$)** | Martins ($14.23 \, \mu\text{s}$) | Pulse ($15.43 \, \mu\text{s}$) | **86.3% vs Martins** |
| **Random ER $n=30$** | **Martins ($3.89 \, \mu\text{s}$)** | Dumitrescu-Boland ($5.48 \, \mu\text{s}$) | Adaptive Hybrid ADHP ($5.70 \, \mu\text{s}$) | **88.2% vs Martins** |

--- | :--- | :--- | :--- | :--- |
| **Planar Grid $10 \times 10$ ($n=100$)** | **Adaptive Hybrid ADHP ($19.97 \, \mu\text{s}$)** | Dumitrescu-Boland ($32.22 \, \mu\text{s}$) | ADHP ($K=5$) ($38.24 \, \mu\text{s}$) | **95.6% vs Martins** |
| **Anti-Correlated $n=150$** | **Dumitrescu-Boland ($69.13 \, \mu\text{s}$)** | Martins ($73.51 \, \mu\text{s}$) | Adaptive Hybrid ADHP ($74.23 \, \mu\text{s}$) | **84.7% vs Martins** |
| **Random ER $n=60$** | **Adaptive Hybrid ADHP ($15.41 \, \mu\text{s}$)** | Dumitrescu-Boland ($16.43 \, \mu\text{s}$) | Pulse ($17.20 \, \mu\text{s}$) | **87.5% vs Martins** |
| **Planar Grid $6 \times 6$ ($n=36$)** | **Dumitrescu-Boland ($10.16 \, \mu\text{s}$)** | Martins ($14.23 \, \mu\text{s}$) | Pulse ($15.43 \, \mu\text{s}$) | **86.3% vs Martins** |
| **Random ER $n=30$** | **Martins ($3.89 \, \mu\text{s}$)** | Dumitrescu-Boland ($5.48 \, \mu\text{s}$) | Adaptive Hybrid ADHP ($5.70 \, \mu\text{s}$) | **88.2% vs Martins** |

--- | :--- | :--- | :--- | :--- |
| **Planar Grid $10 \times 10$ ($n=100$)** | **Adaptive Hybrid ADHP ($19.97 \, \mu\text{s}$)** | Dumitrescu-Boland ($32.22 \, \mu\text{s}$) | ADHP ($K=5$) ($38.24 \, \mu\text{s}$) | **95.6% vs Martins** |
| **Anti-Correlated $n=150$** | **Dumitrescu-Boland ($69.13 \, \mu\text{s}$)** | Martins ($73.51 \, \mu\text{s}$) | Adaptive Hybrid ADHP ($74.23 \, \mu\text{s}$) | **84.7% vs Martins** |
| **Random ER $n=60$** | **Adaptive Hybrid ADHP ($15.41 \, \mu\text{s}$)** | Dumitrescu-Boland ($16.43 \, \mu\text{s}$) | Pulse ($17.20 \, \mu\text{s}$) | **87.5% vs Martins** |
| **Planar Grid $6 \times 6$ ($n=36$)** | **Dumitrescu-Boland ($10.16 \, \mu\text{s}$)** | Martins ($14.23 \, \mu\text{s}$) | Pulse ($15.43 \, \mu\text{s}$) | **86.3% vs Martins** |
| **Random ER $n=30$** | **Martins ($3.89 \, \mu\text{s}$)** | Dumitrescu-Boland ($5.48 \, \mu\text{s}$) | Adaptive Hybrid ADHP ($5.70 \, \mu\text{s}$) | **88.2% vs Martins** |

--- | :--- | :--- | :--- | :--- |
| **Planar Grid $10 \times 10$ ($n=100$)** | **Adaptive Hybrid ADHP ($19.97 \, \mu\text{s}$)** | Dumitrescu-Boland ($32.22 \, \mu\text{s}$) | ADHP ($K=5$) ($38.24 \, \mu\text{s}$) | **95.6% vs Martins** |
| **Anti-Correlated $n=150$** | **Adaptive Hybrid ADHP ($76.92 \, \mu\text{s}$)** | Martins ($90.25 \, \mu\text{s}$) | Dumitrescu-Boland ($97.87 \, \mu\text{s}$) | **82.6% vs Martins** |
| **Random ER $n=90$** | **Adaptive Hybrid ADHP ($32.40 \, \mu\text{s}$)** | Dumitrescu-Boland ($36.90 \, \mu\text{s}$) | Pulse ($37.82 \, \mu\text{s}$) | **89.9% vs Martins** |
| **Planar Grid $8 \times 8$ ($n=64$)** | **Dumitrescu-Boland ($16.00 \, \mu\text{s}$)** | Adaptive Hybrid ADHP ($16.48 \, \mu\text{s}$) | ADHP ($K=5$) ($25.38 \, \mu\text{s}$) | **94.7% vs Martins** |
| **Random ER $n \le 60$** | **Martins ($5.74 - 13.92 \, \mu\text{s}$)** | Adaptive Hybrid ADHP ($8.61 - 15.66 \, \mu\text{s}$)| Dumitrescu-Boland ($7.67 - 18.76 \, \mu\text{s}$)| **84.8% vs Martins** |

---

### 4. Reproducibility Guarantee

All tables above are verified by running:
```bash
python scripts/verify_benchmarks.py
```
Which confirms 100% exact numerical agreement against `results/raw/benchmark_raw.csv`.
