# -*- coding: utf-8 -*-
"""Chapter 6: Monte Carlo Stress Test for Gold in Reserves"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import norm, t as t_dist

np.random.seed(2025)

# ===== Step 1: Portfolio Parameters =====
assets = ['USD Bonds','EUR Bonds','JPY Bonds',
          'GBP Bonds','Gold']
n_assets = 5

# Annualized parameters (2000-2025 estimates)
mu = np.array([0.032, 0.028, 0.008, 0.025, 0.082])
sigma = np.array([0.055, 0.062, 0.048, 0.058, 0.161])
corr = np.array([
    [1.00, 0.72, 0.45, 0.68, 0.15],
    [0.72, 1.00, 0.38, 0.82, 0.18],
    [0.45, 0.38, 1.00, 0.35, 0.08],
    [0.68, 0.82, 0.35, 1.00, 0.12],
    [0.15, 0.18, 0.08, 0.12, 1.00]])
cov = np.outer(sigma, sigma) * corr

# Two portfolios to compare
w_current = np.array([0.60,0.15,0.12,0.10,0.03])
w_proposed = np.array([0.55,0.14,0.11,0.12,0.08])
reserve_usd = 600e9  # $600 billion

# ===== Step 2: Scenario Definitions =====
scenarios = {
    'USD Credit Crisis': {
        'desc': 'US fiscal crisis, USD -20%, '
                'UST -15%, Gold +40%',
        'shocks': np.array([-0.15,-0.05,0.02,
                            -0.03,0.40])},
    'Sustained High Inflation': {
        'desc': 'CPI >6% for 2yr, rates surge, '
                'Gold +25%',
        'shocks': np.array([-0.12,-0.08,-0.02,
                            -0.06,0.25])},
    'Global Equity Crash': {
        'desc': 'S&P -40%, contagion, flight to '
                'safety, Gold +15%',
        'shocks': np.array([0.05,0.03,0.04,
                            0.02,0.15])},
    'Taiwan Strait Crisis': {
        'desc': 'Cross-strait tension, TWD -25%, '
                'USD frozen risk, Gold +50%',
        'shocks': np.array([-0.08,-0.03,0.05,
                            -0.02,0.50])},
}

# ===== Step 3: Deterministic Scenario Analysis =====
print('=== Deterministic Scenario Analysis ===')
print(f'{"Scenario":>28} {"Current(3%gold)":>16} '
      f'{"Proposed(8%gold)":>17} {"Difference":>12}')
print('-' * 75)
for name, sc in scenarios.items():
    loss_c = w_current @ sc['shocks'] * reserve_usd
    loss_p = w_proposed @ sc['shocks'] * reserve_usd
    diff = (loss_p - loss_c) / 1e9
    print(f'{name:>28} '
          f'{loss_c/1e9:>+14.1f}B '
          f'{loss_p/1e9:>+15.1f}B '
          f'{diff:>+10.1f}B')

# ===== Step 4: Monte Carlo Simulation =====
n_sims = 100000
horizon = 12  # months

# Monthly parameters
mu_m = mu / 12
cov_m = cov / 12

# Generate correlated returns (Student-t, df=5)
L = np.linalg.cholesky(cov_m)
df_t = 5  # Fat tails

def simulate_portfolio(w, n_sims, horizon):
    """Simulate portfolio paths over horizon."""
    terminal_values = np.zeros(n_sims)
    for sim in range(n_sims):
        port_val = 1.0
        for m in range(horizon):
            # Student-t innovations for fat tails
            z = t_dist.rvs(df_t, size=n_assets)
            r = mu_m + L @ z
            port_ret = w @ r
            port_val *= (1 + port_ret)
        terminal_values[sim] = port_val - 1
    return terminal_values

print('\nRunning Monte Carlo (100,000 paths)...')
mc_current = simulate_portfolio(
    w_current, n_sims, horizon)
mc_proposed = simulate_portfolio(
    w_proposed, n_sims, horizon)

# ===== Step 5: Risk Metrics =====
def risk_metrics(rets, name, reserve):
    print(f'\n=== {name} ===')
    print(f'  Mean return:  {np.mean(rets)*100:.2f}%')
    print(f'  Volatility:   {np.std(rets)*100:.2f}%')
    var95 = np.percentile(rets, 5)
    var99 = np.percentile(rets, 1)
    cvar95 = np.mean(rets[rets <= var95])
    cvar99 = np.mean(rets[rets <= var99])
    print(f'  VaR(95%):    {var95*100:.2f}% '
          f'(${var95*reserve/1e9:.1f}B)')
    print(f'  CVaR(95%):   {cvar95*100:.2f}% '
          f'(${cvar95*reserve/1e9:.1f}B)')
    print(f'  VaR(99%):    {var99*100:.2f}% '
          f'(${var99*reserve/1e9:.1f}B)')
    print(f'  CVaR(99%):   {cvar99*100:.2f}% '
          f'(${cvar99*reserve/1e9:.1f}B)')
    print(f'  Max drawdown: {np.min(rets)*100:.2f}%')
    return var95, cvar95, var99, cvar99

m1 = risk_metrics(mc_current, 'Current (3% Gold)',
                  reserve_usd)
m2 = risk_metrics(mc_proposed, 'Proposed (8% Gold)',
                  reserve_usd)

# ===== Step 6: Visualization =====
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Panel A: Return distributions
axes[0,0].hist(mc_current*100, bins=200,
    alpha=0.6, color='#3498DB', density=True,
    label='Current (3% Gold)')
axes[0,0].hist(mc_proposed*100, bins=200,
    alpha=0.6, color='#E74C3C', density=True,
    label='Proposed (8% Gold)')
axes[0,0].axvline(x=0, color='black',
    linestyle='--', linewidth=0.8)
axes[0,0].set_title(
    'Panel A: 12-Month Return Distribution',
    fontsize=12)
axes[0,0].set_xlabel('Return (%)')
axes[0,0].legend()

# Panel B: Left tail zoom
axes[0,1].hist(
    mc_current[mc_current < np.percentile(
        mc_current, 10)]*100,
    bins=100, alpha=0.6, color='#3498DB',
    density=True, label='Current')
axes[0,1].hist(
    mc_proposed[mc_proposed < np.percentile(
        mc_proposed, 10)]*100,
    bins=100, alpha=0.6, color='#E74C3C',
    density=True, label='Proposed')
axes[0,1].set_title(
    'Panel B: Left Tail (Worst 10%)', fontsize=12)
axes[0,1].legend()

# Panel C: Scenario comparison bar chart
sc_names = list(scenarios.keys())
losses_c = [w_current @ scenarios[s]['shocks']
            * reserve_usd / 1e9 for s in sc_names]
losses_p = [w_proposed @ scenarios[s]['shocks']
            * reserve_usd / 1e9 for s in sc_names]
x = np.arange(len(sc_names))
axes[1,0].bar(x-0.2, losses_c, 0.4,
    label='Current (3%)', color='#3498DB')
axes[1,0].bar(x+0.2, losses_p, 0.4,
    label='Proposed (8%)', color='#E74C3C')
axes[1,0].set_xticks(x)
axes[1,0].set_xticklabels(
    [s.replace(' ',  '\n') for s in sc_names],
    fontsize=9)
axes[1,0].set_ylabel('Portfolio Impact (USD Bn)')
axes[1,0].set_title(
    'Panel C: Scenario Impact Comparison',
    fontsize=12)
axes[1,0].legend()
axes[1,0].axhline(y=0, color='black',
    linewidth=0.8)

# Panel D: CVaR comparison
labels = ['VaR(95%)','CVaR(95%)',
          'VaR(99%)','CVaR(99%)']
vals_c = [m1[0]*100, m1[1]*100,
          m1[2]*100, m1[3]*100]
vals_p = [m2[0]*100, m2[1]*100,
          m2[2]*100, m2[3]*100]
x2 = np.arange(len(labels))
axes[1,1].bar(x2-0.2, vals_c, 0.4,
    label='Current', color='#3498DB')
axes[1,1].bar(x2+0.2, vals_p, 0.4,
    label='Proposed', color='#E74C3C')
axes[1,1].set_xticks(x2)
axes[1,1].set_xticklabels(labels)
axes[1,1].set_ylabel('Risk Measure (%)')
axes[1,1].set_title(
    'Panel D: Risk Metrics Comparison',
    fontsize=12)
axes[1,1].legend()

plt.suptitle('Monte Carlo Stress Test: '
    'Gold Allocation Impact\n'
    '(100,000 paths, Student-t(df=5), '
    '12-month horizon)', fontsize=14,
    fontweight='bold')
plt.tight_layout()
plt.savefig('fig6_1_monte_carlo.png',
    dpi=300, bbox_inches='tight')
print('\nFigure saved: fig6_1_monte_carlo.png')
