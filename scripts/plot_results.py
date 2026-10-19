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
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

os.makedirs("results/figures", exist_ok=True)
os.makedirs("results/processed", exist_ok=True)

df = pd.read_csv("results/raw/benchmark_raw.csv")

# Set publication style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10

colors = {
    'ADHP (Adaptive Dual Hull Pruning)': '#1f77b4',
    'Adaptive Hybrid ADHP': '#00a86b',
    'Carlyle-Wood (LARAC Single-Multiplier Lagrangian Bounding)': '#ff7f0e',
    'Dumitrescu-Boland (1D-Bounded Label Setting)': '#2ca02c',
    'Martins (Standard Multi-Label Dijkstra)': '#d62728',
    'Pulse (Lozano & Medaglia 2013)': '#9467bd',
}

# -------------------------------------------------------------
# Figure 1: Labels Generated Scaling on Anti-Correlated Graphs
# -------------------------------------------------------------
plt.figure(figsize=(8, 5), dpi=300)
anti_df = df[df['benchmark_category'] == 'Anti-Correlated Scaling']

for solver, group in anti_df.groupby('solver_name'):
    group = group.sort_values('nodes')
    color = colors.get(solver, '#333333')
    plt.plot(group['nodes'], group['mean_labels_generated'], marker='o', linewidth=2, label=solver, color=color)

plt.yscale('log')
plt.xlabel('Graph Size (Number of Vertices $n$)')
plt.ylabel('Candidate Labels Generated (Log Scale)')
plt.title('Label Space Explosion Suppression on Anti-Correlated Networks')
plt.legend(frameon=True)
plt.tight_layout()
plt.savefig('results/figures/fig1_labels_generated_anticorr.png')
plt.close()

# -------------------------------------------------------------
# Figure 2: Runtime Scaling on 2D Mesh Grid Graphs
# -------------------------------------------------------------
plt.figure(figsize=(8, 5), dpi=300)
grid_df = df[df['benchmark_category'] == 'Grid Scaling']

for solver, group in grid_df.groupby('solver_name'):
    group = group.sort_values('nodes')
    color = colors.get(solver, '#333333')
    plt.plot(group['nodes'], group['mean_runtime_micros'], marker='s', linewidth=2, label=solver, color=color)

plt.xlabel('Grid Vertices ($n = r \\times c$)')
plt.ylabel('Execution Time (µs)')
plt.title('Runtime Scaling on 2D Mesh Grid Graphs')
plt.legend(frameon=True)
plt.tight_layout()
plt.savefig('results/figures/fig2_runtime_grid.png')
plt.close()

# -------------------------------------------------------------
# Figure 3: Ablation Study on Facet Count K
# -------------------------------------------------------------
plt.figure(figsize=(7, 4.5), dpi=300)
abl_df = df[df['benchmark_category'] == 'Ablation K Facets']

if not abl_df.empty:
    k_vals = [int(s.replace('ADHP (K=', '').replace(')', '')) for s in abl_df['solver_name']]
    prep_times = abl_df['mean_preprocessing_micros'].values
    total_times = abl_df['mean_runtime_micros'].values

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
    plt.savefig('results/figures/fig3_ablation_facets.png')
    plt.close()

# -------------------------------------------------------------
# Figure 4: Runtime Scaling on Random Erdős–Rényi Graphs
# -------------------------------------------------------------
plt.figure(figsize=(8, 5), dpi=300)
er_df = df[df['benchmark_category'] == 'Random ER Scaling']

for solver, group in er_df.groupby('solver_name'):
    group = group.sort_values('nodes')
    color = colors.get(solver, '#333333')
    plt.plot(group['nodes'], group['mean_runtime_micros'], marker='^', linewidth=2, label=solver, color=color)

plt.xlabel('Number of Vertices ($n$)')
plt.ylabel('Execution Time (µs)')
plt.title('Runtime Scaling on Random Erdős–Rényi Graphs ($p=0.22$)')
plt.legend(frameon=True)
plt.tight_layout()
plt.savefig('results/figures/fig4_runtime_random_er.png')
plt.close()

# -------------------------------------------------------------
# Figure 5: Budget Sensitivity
# -------------------------------------------------------------
plt.figure(figsize=(8, 5), dpi=300)
bs_df = df[df['benchmark_category'] == 'Budget Sensitivity'].copy()

alpha_map = {
    'budget_alpha_0.10': 0.10,
    'budget_alpha_0.25': 0.25,
    'budget_alpha_0.50': 0.50,
    'budget_alpha_0.75': 0.75,
    'budget_alpha_0.90': 0.90,
}
bs_df['alpha'] = bs_df['instance_name'].map(alpha_map)

for solver, group in bs_df.groupby('solver_name'):
    group = group.sort_values('alpha')
    color = colors.get(solver, '#333333')
    plt.plot(group['alpha'], group['mean_runtime_micros'], marker='d', linewidth=2, label=solver, color=color)

plt.xlabel('Budget Tightness Factor $\\alpha$ (0.10 = Tight, 0.90 = Loose)')
plt.ylabel('Execution Time (µs)')
plt.title('Budget Sensitivity Analysis ($n=50$ Anti-Correlated Graph)')
plt.legend(frameon=True)
plt.tight_layout()
plt.savefig('results/figures/fig5_budget_sensitivity.png')
plt.close()


# -------------------------------------------------------------
# Processed Summary Table
# -------------------------------------------------------------
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
sum_df.to_csv("results/processed/summary_table.csv", index=False)
print("Figures and summary table generated successfully in results/figures/ and results/processed/.")
