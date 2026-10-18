# VERIFIED CURRICULUM VITAE (CV) ENTRY
## Autonomous Mathematical Algorithm Discovery Lab: ADHP-CSPP

**Author**: Rajve  
**Date**: October 2026  
**Document**: `docs/CV_ENTRY.md`  

---

### Ready-to-Use CV Entry

**Adaptive Dual Hull Pruning (ADHP) for the Constrained Shortest Path Problem — Independent Research & Algorithm Engineering**
- Formulated and proved the mathematical admissibility, strict dominance, and exact global optimality of an adaptive multi-faceted discrete Legendre-Fenchel lower-bound envelope for the NP-hard Weight-Constrained Shortest Path Problem (CSPP).
- Implemented the algorithm in production-grade Rust (zero warnings on `cargo clippy --all-targets -- -D warnings`), featuring sublinear dual envelope evaluation, lazy dominance checks, and reverse shortest path trees.
- Evaluated against four classical and modern baselines (Martins Multi-Label Dijkstra, Dumitrescu-Boland 1D-bounded solver, Carlyle-Wood LARAC Lagrangian bounding, and Lozano-Medaglia Pulse algorithm) across 250 timed executions with in-process hardware performance counters and 5 discarded warmup runs.
- Measured a 96.7% suppression of candidate Pareto labels on anti-correlated networks and a 2.64x wall-clock speedup on 2D mesh grid networks, while rigorously characterizing the small-graph preprocessing break-even frontier.
- Verified exactness through 100% agreement on 30 differential oracle tests and mathematical property suites against independent Integer Linear Programming (HiGHS/SciPy).
- Published open-source code, mathematical proofs, experimental logs, and research paper at [https://github.com/rajveersinh-is-dev/adhp-cspp](https://github.com/rajveersinh-is-dev/adhp-cspp).
