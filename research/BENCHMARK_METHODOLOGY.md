# BENCHMARK METHODOLOGY & EXPERIMENTAL CONTROLS
## Autonomous Algorithm Discovery Lab: Empirical Evaluation of ADHP-CSPP

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `research/BENCHMARK_METHODOLOGY.md`  

---

### 1. Hardware and Environmental Controls

To ensure strict scientific reproducibility and eliminate measurement artifacts:
- **Processor**: 11th Gen Intel(R) Core(TM) i5-11260H @ 2.60GHz
- **Microarchitecture**: Tiger Lake (6 physical cores, 12 logical threads, 12 MB L3 Cache)
- **Memory**: 16 GB DDR4 RAM (16,893,382,656 bytes)
- **Operating System**: Microsoft Windows 11 Home Single Language (Build 26100)
- **Compiler Toolchain**: rustc 1.98.1 (48a229cea 2026-09-01), cargo 1.98.1
- **Optimization Flags**: Release profile with `opt-level = 3`, `lto = true`, `codegen-units = 1`, `panic = "abort"`.
- **Timing Mechanism**: In-process hardware performance counters using `std::time::Instant` with sub-microsecond resolution.

---

### 2. Experimental Protocols

1. **Warmup Protocol**:
   - Every individual test configuration was executed for **5 discarded warmup runs** immediately prior to timing. This ensured that CPU branch predictors, instruction caches, and data caches reached steady state before data collection began.
2. **Repetition & Statistical Aggregation**:
   - Each configuration was measured across **10 timed repetitions**.
   - Reported statistics include the arithmetic mean ($\mu$) and sample standard deviation ($\sigma$).
3. **Execution Purity**:
   - All algorithms were compiled in the same binary under identical compiler flags, executing in a single thread without concurrency jitter.
   - No precomputed constants, synthetic benchmark lookup tables, or shortcut function-name matching were permitted.
   - All graph instances were generated deterministically using an explicit Linear Congruential Generator (LCG) initialized with documented seeds.

---

### 3. Benchmark Suites and Input Topology Families

1. **Anti-Correlated Scaling Suite**:
   - Graph sizes $n \in \{20, 40, 60, 80, 100\}$.
   - Edge density $p = 0.25$.
   - Cost and weight generated with strong negative correlation: $w_e = 100 - c_e + \epsilon$, where $\epsilon \sim \text{Uniform}(-5, 5)$.
   - *Rationale*: Classic hard benchmark from operations research literature where unconstrained shortest cost paths severely violate the budget, inducing massive Pareto frontiers.
2. **2D Mesh Grid Scaling Suite**:
   - Grid dimensions $4\times 4, 6\times 6, 8\times 8, 9\times 9$ ($n \in \{16, 36, 64, 81\}$).
   - Planar-like topologies with directed transitions (right, down, diagonal).
   - *Rationale*: Models transportation networks, VLSI routing, and robot grid navigation with localized spatial bottlenecks.
3. **Random Erdős-Rényi Scaling Suite**:
   - Graph sizes $n \in \{30, 60, 90, 120\}$.
   - Edge density $p = 0.20$.
   - Uncorrelated uniform costs and weights in $[1, 100]$.
4. **Budget Sensitivity Suite**:
   - Fixed graph size $n = 50$, varying budget tightness factor $\alpha \in \{0.10, 0.25, 0.50, 0.75, 0.90\}$ where $W = W_{\min} + \alpha(W_{\max} - W_{\min})$.
   - *Rationale*: Tests solver behavior from extremely constrained (near-infeasible) to loose budget regimes.
5. **Ablation Study on Facet Count $K$**:
   - Fixed instance ($n = 70$, anti-correlated), varying $K \in \{2, 3, 5, 8, 12\}$.
   - Evaluates the marginal benefit of additional supporting hyperplanes versus the added preprocessing cost.

---

### 4. Competitors Evaluated

1. **ADHP (Adaptive Dual Hull Pruning)** (This Work):
   - Multi-faceted adaptive dual lower-bound envelope with $K=5$ facets.
2. **Martins (1984)**:
   - Canonical standard multi-label Dijkstra with Pareto dominance (no dual bounds).
3. **Dumitrescu & Boland (2003)**:
   - State-of-the-art 1D-bounded label-setting solver ($d_c, d_w$).
4. **Carlyle & Wood (2008)**:
   - LARAC single-multiplier Lagrangian bounding solver.
5. **Pulse Algorithm (Lozano & Medaglia 2013)**:
   - Exact recursive DFS with 1D bounds and local pulse memory dominance.
