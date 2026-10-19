# KNOWN LIMITATIONS & NEGATIVE RESULTS
## Honest Algorithmic Boundaries and Practical Trade-offs for ADHP-CSPP

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/KNOWN_LIMITATIONS.md`  
**Repository**: [https://github.com/rajveersinh-is-dev/adhp-cspp](https://github.com/rajveersinh-is-dev/adhp-cspp)

---

### 1. Preprocessing Overhead on Dense and Small-Diameter Networks

The primary trade-off in dual lower-bounding algorithms is the balance between **preprocessing effort** and **search space reduction**.

- **Empirical Observation**: On dense Erdős–Rényi graphs ($p=0.20$, $m/n \ge 3.5$) with moderate size ($n \le 60$), the hop diameter is small ($k \approx 3-5$ hops). On such graphs, classical label setting (Martins) settles the optimal path in only $5-14 \, \mu\text{s}$ because very few non-dominated Pareto trade-offs exist.
- **Fixed ADHP Overhead**: Fixed ADHP ($K=5$) computes multiple reverse Dijkstra trees during preprocessing, consuming $25-50 \, \mu\text{s}$. Consequently, fixed ADHP is slower in end-to-end wall-clock time than Martins on small dense networks, even though it explores fewer forward labels.
- **Mitigation & Boundary**: The `HybridAdhpSolver` detects $\rho \ge 3.5$ and caps preprocessing at $K=1$, reducing total runtime from $31.11 \, \mu\text{s}$ down to $15.66 \, \mu\text{s}$ at $n=60$. However, on tiny instances ($n \le 20$), zero-preprocessing solvers remain faster.

---

### 2. Diminishing Returns for Dual Facet Count $K > 3$

A critical negative result uncovered by our ablation study (Suite 5, $n=70$ Anti-Correlated network) is that the marginal utility of additional dual facets drops precipitously beyond $K=2$:

| Facet Count $K$ | Preprocessing Time (µs) | Search Time (µs) | Total Runtime (µs) | Forward Labels Generated | Dual Labels Pruned |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **$K = 1$** | $11.06$ | $4.60$ | **$15.66$** | $146$ | $40$ |
| **$K = 2$** | $17.78$ | $2.32$ | **$20.10$** | **$91$** (37.7% drop) | $39$ |
| **$K = 3$** | $20.78$ | $2.20$ | **$22.98$** | **$91$** | $39$ |
| **$K = 5$** | $25.86$ | $2.21$ | **$28.07$** | **$91$** | $39$ |
| **$K = 8$** | $25.10$ | $2.13$ | **$27.23$** | **$91$** | $39$ |
| **$K = 12$** | $25.39$ | $2.29$ | **$27.68$** | **$91$** | $39$ |

- **Analytical Finding**: Moving from $K=1$ (single 1D cost tree) to $K=2$ (adding the primary lower hull bisector) cuts forward search labels from 146 to 91 and halves search time ($4.60 \, \mu\text{s} \to 2.32 \, \mu\text{s}$).
- **The Plateau**: For $K \ge 3$, forward labels plateau at 91 because the dual envelope already approximates the lower convex hull closely enough that additional facets do not intersect any reachable intermediate label states. Every additional facet beyond $K=3$ purely consumes extra Dijkstra passes without further pruning.
- **Conclusion**: Users should configure $K \in \{2, 3\}$ for general instances, or use `HybridAdhpSolver` which dynamically chooses between $K=1, 2, 5$.

---

### 3. Arithmetic and Numerical Boundaries

#### 3.1 128-Bit Integer Domain Bounds (`IntAdhpSolver`)
- The composite metric evaluated in Dijkstra is $c_e \cdot \text{den} + w_e \cdot \text{num}$.
- The maximum possible composite path length is bounded by $2 \cdot C_{\max} \cdot W_{\max}$.
- Because `IntAdhpSolver` uses `u128`, the maximum allowable sum of edge costs and weights is $\approx 1.3 \times 10^{19}$. If total edge costs or weights exceed this, integer overflow is signaled and the solver returns `SolutionStatus::Infeasible` with zero corruption.

#### 3.2 Floating-Point Epsilon Tolerances (`AdhpSolver`)
- Under IEEE 754 double precision (`f64`), recursive addition of edge weights along long paths accumulates rounding error bounded by Higham's summation theorem ($|\text{fl}(S) - S| \le \gamma_n S \approx 2.3 \times 10^{-11} S$).
- To prevent premature pruning of near-tie optimal paths, `AdhpSolver` applies a conservative relative tolerance $\epsilon = 10^{-9}$. While certified $(\epsilon_{\text{feas}}, \epsilon_{\text{prune}})$-admissible, paths differing by less than $10^{-9}$ relative cost may not be distinguished in floating-point mode. For exact discrete optimization, `IntAdhpSolver` should always be preferred.

---

### 4. Memory Footprint Comparison

- Unlike Martins' algorithm, which stores unrestricted Pareto frontiers at all vertices (potentially exponential in $|V|$ in the worst case), ADHP aggressively prunes labels via Filter 2.
- On all evaluated benchmark instances (up to $n=150$ and 10x10 grids), the peak priority queue size for ADHP and Adaptive Hybrid ADHP remained below 500 active labels, consuming less than 16 KB of label memory.
- In contrast, the Pulse algorithm uses a recursion stack with $O(|V|)$ memory, which is advantageous for embedded devices with tight RAM limits, though at the expense of higher tail latency on grid graphs.
