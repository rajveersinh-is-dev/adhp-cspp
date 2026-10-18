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

1. **Multi-Instance Sample Evaluation**:
   - Rather than repeatedly timing a single synthetic instance, every configuration is evaluated across **10 distinct random instances** generated with independent seeds (200 distinct problem instances total across 20 configuration sets).
   - For each instance, 3 discarded warmup runs ensure instruction and data cache warmness, followed by 3 timed runs to eliminate transient OS scheduling jitter.
2. **Statistical Distribution Metrics**:
   - Reports the sample arithmetic mean ($\mu$), sample median, and sample standard deviation ($\sigma$) across the 10 instances.
   - Preprocessing time and forward search time are measured and reported separately to isolate the algorithmic cost of bound construction from search-space exploration.
   - Peak heap memory allocation (in bytes) is tracked by monitoring active priority queue capacity, path pool capacity, and vertex Pareto frontier point arrays.
3. **Execution Purity**:
   - All algorithms are compiled in the same binary under identical release profile flags (`opt-level = 3`, `lto = true`, `codegen-units = 1`), executing single-threaded on a dedicated core.
   - Zero precomputed lookup tables or shortcut heuristic stubs. All bounds and shortest path trees are computed dynamically from first principles.
   - All graph instances are deterministically generated using an explicit Linear Congruential Generator (LCG) with documented seeds.

---

### 3. Benchmark Suites and Input Topology Families

1. **Anti-Correlated Scaling Suite**:
   - Graph sizes $n \in \{20, 40, 60, 80, 100, 150\}$.
   - Edge density $p = 0.25$.
   - Cost and weight generated with strong negative correlation: $w_e = 100 - c_e + \epsilon$, where $\epsilon \sim \text{Uniform}(-5, 5)$.
   - Evaluated across 10 distinct random instances per size (60 instances total).
   - *Rationale*: Classic hard benchmark from operations research literature where unconstrained shortest cost paths severely violate the budget, inducing massive Pareto frontiers.
2. **2D Mesh Grid Scaling Suite**:
   - Grid dimensions $4\times 4, 6\times 6, 8\times 8, 10\times 10$ ($n \in \{16, 36, 64, 100\}$).
   - Planar-like topologies with directed transitions (right, down, diagonal).
   - Evaluated across 10 distinct random instances per dimension (40 instances total).
   - *Rationale*: Models transportation networks, VLSI routing, and robot grid navigation with localized spatial bottlenecks.
3. **Random Erdős-Rényi Scaling Suite**:
   - Graph sizes $n \in \{30, 60, 90, 120\}$.
   - Edge density $p = 0.20$.
   - Uncorrelated uniform costs and weights in $[1, 100]$ across 10 instances per size.
4. **Budget Sensitivity Suite**:
   - Fixed graph size $n = 50$, varying budget tightness factor $\alpha \in \{0.10, 0.25, 0.50, 0.75, 0.90\}$ where $W = W_{\min} + \alpha(W_{\max} - W_{\min})$.
   - 10 distinct instances per $\alpha$ level (50 instances total).
5. **Ablation Study on Facet Count $K$**:
   - Multi-facet instances ($n = 70$, anti-correlated), testing $K \in \{1, 2, 3, 5, 8, 12\}$.
   - Explicitly evaluates $K=1$ (single 1D cost bounding) through $K=12$ (fine discretization).

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
