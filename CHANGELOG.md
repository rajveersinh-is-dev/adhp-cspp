# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-18

### Added
- Initial public release of **ADHP-CSPP** (Adaptive Dual Hull Pruning).
- Mathematical formalization of discrete $K$-faceted Legendre-Fenchel lower-bound envelopes.
- Proven admissibility, strict dominance, and global exactness theorems.
- High-performance Rust 2021 implementation with zero `.unwrap()` in lowering pipelines.
- Implemented four state-of-the-art baselines: Martins (1984), Dumitrescu-Boland (2003), Carlyle-Wood (2008), and Lozano-Medaglia Pulse (2013).
- High-resolution empirical benchmark suite across Anti-Correlated, 2D Grid, and Random ER graph families.
- Automated differential verification suite (30/30 verified instances) and mathematical property test suite.
- Complete research manuscript (`paper/main.tex` and compiled `paper/paper.pdf`).
