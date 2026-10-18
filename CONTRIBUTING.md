# Contributing to ADHP-CSPP

Thank you for your interest in contributing to the Adaptive Dual Hull Pruning (ADHP) project!

## Development Guidelines

1. **Mathematical Rigor & Purity**:
   - Zero preloaded numbers, lookup tables, or synthetic benchmark values.
   - All timings must be measured in-process using high-resolution performance counters.
   - Code must pass `cargo clippy --all-targets -- -D warnings` with 0 warnings.
2. **Testing**:
   - Every algorithmic change or bug fix must include regression tests.
   - Run the full test suite before submitting:
     ```bash
     cargo test
     cargo run --bin verify_oracle --release
     ```
3. **Pull Request Process**:
   - Submit PRs against the `main` branch.
   - Ensure continuous integration checks pass cleanly.
