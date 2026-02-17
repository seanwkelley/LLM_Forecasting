#!/usr/bin/env python3
"""
Analyze variation in multi-scenario ground truth data
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load data
data_dir = Path(__file__).parent / "outputs" / "multiscenario"
scenarios = pd.read_csv(data_dir / "scenarios.csv")
ground_truth = pd.read_csv(data_dir / "ground_truth.csv")

# Merge to get full picture
df = scenarios.merge(ground_truth, on='scenario_id')

print("="*70)
print("MULTI-SCENARIO VARIATION ANALYSIS")
print("="*70)
print(f"\nNumber of scenarios: {len(df)}\n")

# 1. COLLAPSE PROBABILITY VARIATION
print("="*70)
print("1. COLLAPSE PROBABILITY VARIATION")
print("="*70)
print(f"\nMean:  {df['collapse_probability'].mean():.3f}")
print(f"Std:   {df['collapse_probability'].std():.3f}")
print(f"Min:   {df['collapse_probability'].min():.3f}")
print(f"Max:   {df['collapse_probability'].max():.3f}")
print(f"Range: {df['collapse_probability'].max() - df['collapse_probability'].min():.3f}")

print("\nPer-scenario breakdown:")
for _, row in df.iterrows():
    print(f"  {row['scenario_id']}: {row['collapse_probability']:.3f}")
    print(f"    Territory: {row['territory_controlled']*100:.1f}% | "
          f"Military: {row['military_balance']:.2f} | "
          f"Sanctions: {row['sanctions_level']*100:.0f}% | "
          f"Support: {row['international_support']*100:.0f}%")

# 2. NOVARIS (AGGRESSOR) ACTIONS VARIATION
print("\n" + "="*70)
print("2. NOVARIS (AGGRESSOR) ACTIONS VARIATION")
print("="*70)

# Parse action strings
df['novaris_action_list'] = df['novaris_actions'].str.split('|')
df['tethys_action_list'] = df['tethys_actions'].str.split('|')

print(f"\nNumber of actions per scenario:")
print(f"  Mean:  {df['n_novaris_actions'].mean():.1f}")
print(f"  Std:   {df['n_novaris_actions'].std():.1f}")
print(f"  Min:   {df['n_novaris_actions'].min()}")
print(f"  Max:   {df['n_novaris_actions'].max()}")
print(f"  Range: {df['n_novaris_actions'].max() - df['n_novaris_actions'].min()}")

print("\nActions by scenario:")
for _, row in df.iterrows():
    actions = row['novaris_action_list']
    print(f"  {row['scenario_id']} ({row['n_novaris_actions']} actions):")
    for action in actions:
        print(f"    - {action}")

# Action diversity
all_novaris_actions = [a for actions in df['novaris_action_list'] for a in actions]
unique_novaris_actions = set(all_novaris_actions)
print(f"\nUnique Novaris action types: {len(unique_novaris_actions)}")
action_counts = pd.Series(all_novaris_actions).value_counts()
print("\nMost common actions:")
for action, count in action_counts.items():
    print(f"  {action}: {count}")

# 3. TETHYS (DEFENDER) ACTIONS VARIATION
print("\n" + "="*70)
print("3. TETHYS (DEFENDER) ACTIONS VARIATION")
print("="*70)

print(f"\nNumber of actions per scenario:")
print(f"  Mean:  {df['n_tethys_actions'].mean():.1f}")
print(f"  Std:   {df['n_tethys_actions'].std():.1f}")
print(f"  Min:   {df['n_tethys_actions'].min()}")
print(f"  Max:   {df['n_tethys_actions'].max()}")
print(f"  Range: {df['n_tethys_actions'].max() - df['n_tethys_actions'].min()}")

print("\nActions by scenario:")
for _, row in df.iterrows():
    actions = row['tethys_action_list']
    print(f"  {row['scenario_id']} ({row['n_tethys_actions']} actions):")
    for action in actions:
        print(f"    - {action}")

# Action diversity
all_tethys_actions = [a for actions in df['tethys_action_list'] for a in actions]
unique_tethys_actions = set(all_tethys_actions)
print(f"\nUnique Tethys action types: {len(unique_tethys_actions)}")
action_counts = pd.Series(all_tethys_actions).value_counts()
print("\nMost common actions:")
for action, count in action_counts.items():
    print(f"  {action}: {count}")

# 4. CORRELATIONS WITH SCENARIO PARAMETERS
print("\n" + "="*70)
print("4. CORRELATIONS WITH SCENARIO PARAMETERS")
print("="*70)

params = ['territory_controlled', 'military_balance', 'sanctions_level',
          'international_support', 'crisis_level']

print("\nCollapse probability correlations:")
for param in params:
    corr = df['collapse_probability'].corr(df[param])
    print(f"  {param:25s}: {corr:+.3f}")

print("\n# Novaris actions correlations:")
for param in params:
    corr = df['n_novaris_actions'].corr(df[param])
    print(f"  {param:25s}: {corr:+.3f}")

print("\n# Tethys actions correlations:")
for param in params:
    corr = df['n_tethys_actions'].corr(df[param])
    print(f"  {param:25s}: {corr:+.3f}")

# 5. SUMMARY
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"""
KEY FINDINGS:

1. Collapse Probability:
   - Range: {df['collapse_probability'].min():.3f} to {df['collapse_probability'].max():.3f}
   - Variation: {df['collapse_probability'].std():.3f} (std dev)
   - All scenarios show moderate collapse risk (42-48%)

2. Novaris Actions:
   - Range: {df['n_novaris_actions'].min()} to {df['n_novaris_actions'].max()} actions per scenario
   - {len(unique_novaris_actions)} unique action types
   - Variation driven by strategic situation

3. Tethys Actions:
   - Range: {df['n_tethys_actions'].min()} to {df['n_tethys_actions'].max()} actions per scenario
   - {len(unique_tethys_actions)} unique action types
   - Shows defensive variety

NOTE: This is MOCK DATA for testing. Real R simulation will produce
      more realistic variation based on agent deliberation.
""")
print("="*70)
