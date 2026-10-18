#!/usr/bin/env python3
"""
Scientific Plotting and Analysis Script for ADHP-CSPP Benchmarks.
Generates publication-quality figures for:
1. Scaling of Label Generation across Graph Sizes (Log scale).
2. Runtime vs Problem Size Break-Even Analysis.
3. Pruning Ratio vs Baseline Solvers.
4. Ablation on K Facet Parameter.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional, Tuple

# Constants
RESULTS_DIR = "results"
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
PROCESSED_DIR = os.path.join(RESULTS_DIR, "processed")
RAW_DATA_PATH = os.path.join(RESULTS_DIR, "raw", "benchmark_raw.csv")

COLORS: Dict[str, str] = {
    'ADHP (Adaptive Dual Hull Pruning)': '#1f77b4',
    'Carlyle-Wood (LARAC Single-Multiplier Lagrangian Bounding)': '#ff7f0e',
    'Dumitrescu-Boland (1D-Bounded Label Setting)': '#2ca02c',
    'Martins (Standard Multi-Label Dijkstra)': '#d62728',
    'Pulse (Lozano & Medaglia 2013)': '#9467bd',
}

BUDGET_ALPHA_MAP: Dict[str, float] = {
    'budget_alpha_0.10': 0.10,
    'budget_alpha_0.25': 0.25,
    'budget_alpha_0.50': 0.50,
    'budget_alpha_0.75': 0.75,
    'budget_alpha_0.90': 0.90,
}

REQUIRED_COLUMNS: List[str] = [
    'benchmark_category', 'solver_name', 'nodes', 'instance_name',
    'mean_runtime_micros', 'mean_labels_generated', 'mean_preprocessing_micros'
]


def setup_directories() -> None:
    """Create necessary output directories if they don't exist."""
    os.makedirs(FIGURES_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)


def load_data() -> pd.DataFrame:
    """
    Load and validate benchmark data from CSV.
    
    Returns:
        pd.DataFrame: Validated benchmark data
    
    Raises:
        FileNotFoundError: If raw data file is missing
        ValueError: If required columns are missing
    """
    try:
        df = pd.read_csv(RAW_DATA_PATH)
    except FileNotFoundError:
        raise FileNotFoundError(f"Benchmark data not found at {RAW_DATA_PATH}")
    
    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    return df


def configure_plot_style() -> None:
    """Configure matplotlib style for publication-quality figures."""
    plt.style.use(
        'seaborn-v0_8-whitegrid'
        if 'seaborn-v0_8-whitegrid' in plt.style.available
        else 'default'
    )
    plt.rcParams.update({
        'font.sans-serif': 'Arial',
        'font.family': 'sans-serif',
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
    })


def plot_labels_generated_anticorr(df: pd.DataFrame) -> None:
    """
    Generate Figure 1: Label space scaling on anti-correlated graphs.
    
    Args:
        df: Benchmark data
    """
    plt.figure(figsize=(8, 5), dpi=300)
    anti_df = df[df['benchmark_category'] == 'Anti-Correlated Scaling']
    
    for solver, group in anti_df.groupby('solver_name'):
        group = group.sort_values('nodes')
        color = COLORS.get(solver, '#333333')
        plt.plot(
            group['nodes'],
            group['mean_labels_generated'],
            marker='o',
            linewidth=2,
            label=solver,
            color=color
        )
    
    plt.yscale('log')
    plt.xlabel('Graph Size (Number of Vertices $n$)')
    plt.ylabel('Candidate Labels Generated (Log Scale)')
    plt.title('Label Space Explosion Suppression on Anti-Correlated Networks')
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig1_labels_generated_anticorr.png'))
    plt.close()


def plot_runtime_grid(df: pd.DataFrame) -> None:
    """
    Generate Figure 2: Runtime scaling on 2D mesh grid graphs.
    
    Args:
        df: Benchmark data
    """
    plt.figure(figsize=(8, 5), dpi=300)
    grid_df = df[df['benchmark_category'] == 'Grid Scaling']
    
    for solver, group in grid_df.groupby('solver_name'):
        group = group.sort_values('nodes')
        color = COLORS.get(solver, '#333333')
        plt.plot(
            group['nodes'],
            group['mean_runtime_micros'],
            marker='s',
            linewidth=2,
            label=solver,
            color=color
        )
    
    plt.xlabel('Grid Vertices ($n = r \times c$)')
    plt.ylabel('Execution Time (µs)')
    plt.title('Runtime Scaling on 2D Mesh Grid Graphs')
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig2_runtime_grid.png'))
    plt.close()


def plot_ablation_facets(df: pd.DataFrame) -> None:
    """
    Generate Figure 3: Ablation study on facet count K.
    
    Args:
        df: Benchmark data
    """
    plt.figure(figsize=(7, 4.5), dpi=300)
    abl_df = df[df['benchmark_category'] == 'Ablation K Facets']
    
    if abl_df.empty:
        return
    
    # Extract K values from solver names
    k_vals = []
    for name in abl_df['solver_name']:
        try:
            k = int(name.replace('ADHP (K=', '').replace(')', ''))
            k_vals.append(k)
        except ValueError:
            continue
    
    if not k_vals:
        return
    
    prep_times = abl_df['mean_preprocessing_micros'].values
    total_times = abl_df['mean_runtime_micros'].values
    
    # Sort by K values
    idx = np.argsort(k_vals)
    k_vals = np.array(k_vals)[idx]
    prep_times = prep_times[idx]
    total_times = total_times[idx]
    
    plt.plot(k_vals, total_times, marker='o', color='#1f77b4', linewidth=2, label='Total Runtime')
    plt.plot(k_vals, prep_times, marker='^', color='#ff7f0e', linestyle='--', linewidth=2, label='Preprocessing Time')
    
    plt.xlabel('Dual Facet Count $K$')
    plt.ylabel('Time (µs)')
    plt.title('Ablation Study: Trade-off between Preprocessing and Search')
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig3_ablation_facets.png'))
    plt.close()


def plot_runtime_random_er(df: pd.DataFrame) -> None:
    """
    Generate Figure 4: Runtime scaling on random Erdős–Rényi graphs.
    
    Args:
        df: Benchmark data
    """
    plt.figure(figsize=(8, 5), dpi=300)
    er_df = df[df['benchmark_category'] == 'Random ER Scaling']
    
    for solver, group in er_df.groupby('solver_name'):
        group = group.sort_values('nodes')
        color = COLORS.get(solver, '#333333')
        plt.plot(
            group['nodes'],
            group['mean_runtime_micros'],
            marker='^',
            linewidth=2,
            label=solver,
            color=color
        )
    
    plt.xlabel('Number of Vertices ($n$)')
    plt.ylabel('Execution Time (µs)')
    plt.title('Runtime Scaling on Random Erdős–Rényi Graphs ($p=0.22$)')
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig4_runtime_random_er.png'))
    plt.close()


def plot_budget_sensitivity(df: pd.DataFrame) -> None:
    """
    Generate Figure 5: Budget sensitivity analysis.
    
    Args:
        df: Benchmark data
    """
    plt.figure(figsize=(8, 5), dpi=300)
    bs_df = df[df['benchmark_category'] == 'Budget Sensitivity'].copy()
    
    if bs_df.empty:
        return
    
    bs_df['alpha'] = bs_df['instance_name'].map(BUDGET_ALPHA_MAP)
    # Remove rows where mapping failed
    bs_df = bs_df.dropna(subset=['alpha'])
    
    if bs_df.empty:
        return
    
    for solver, group in bs_df.groupby('solver_name'):
        group = group.sort_values('alpha')
        color = COLORS.get(solver, '#333333')
        plt.plot(
            group['alpha'],
            group['mean_runtime_micros'],
            marker='d',
            linewidth=2,
            label=solver,
            color=color
        )
    
    plt.xlabel('Budget Tightness Factor $\alpha$ (0.10 = Tight, 0.90 = Loose)')
    plt.ylabel('Execution Time (µs)')
    plt.title('Budget Sensitivity Analysis ($n=50$ Anti-Correlated Graph)')
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'fig5_budget_sensitivity.png'))
    plt.close()


def generate_summary_table(df: pd.DataFrame) -> None:
    """
    Generate summary statistics CSV file.
    
    Args:
        df: Benchmark data
    """
    summary_table = []
    for cat, group in df.groupby('benchmark_category'):
        for solver, s_group in group.groupby('solver_name'):
            summary_table.append({
                'Category': cat,
                'Solver': solver,
                'Avg Runtime (µs)': round(s_group['mean_runtime_micros'].mean(), 2),
                'Max Runtime (µs)': round(s_group['mean_runtime_micros'].max(), 2),
                'Avg Labels Generated': int(s_group['mean_labels_generated'].mean()),
                'Max Labels Generated': int(s_group['mean_labels_generated'].max()),
            })
    
    sum_df = pd.DataFrame(summary_table)
    output_path = os.path.join(PROCESSED_DIR, 'summary_table.csv')
    sum_df.to_csv(output_path, index=False)


def main() -> None:
    """Main execution function."""
    setup_directories()
    df = load_data()
    configure_plot_style()
    
    plot_labels_generated_anticorr(df)
    plot_runtime_grid(df)
    plot_ablation_facets(df)
    plot_runtime_random_er(df)
    plot_budget_sensitivity(df)
    generate_summary_table(df)
    
    print(
        "Figures and summary table generated successfully in "
        f"{FIGURES_DIR}/ and {PROCESSED_DIR}/."
    )


if __name__ == "__main__":
    main()
