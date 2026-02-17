import pandas as pd
import numpy as np

df = pd.read_csv(r'D:\Northeastern\LLM_Forecasting\experiment_results\pid_analysis_v311_crisis_full\raw_escalation_matrix.csv')
primary = df[df['priority'] == 'primary']

print("=== NOVARIS (primary only) ===")
nov = primary[primary['faction_name'] == 'Novaris']
print(f"Total primary rows: {len(nov)}")
for role in sorted(nov['agent_role'].unique()):
    sub = nov[nov['agent_role'] == role]
    esc = sub['proposed_escalation']
    print(f"\n  Role: {role}")
    print(f"    N scenarios: {sub['scenario_id'].nunique()}")
    print(f"    Unique proposed_escalation values: {esc.nunique()}")
    vc = esc.value_counts().sort_index()
    for val, cnt in vc.items():
        print(f"      escalation={val}: {cnt}")

print("\n\n=== TETHYS (primary only) ===")
teth = primary[primary['faction_name'] == 'Tethys']
print(f"Total primary rows: {len(teth)}")
for role in sorted(teth['agent_role'].unique()):
    sub = teth[teth['agent_role'] == role]
    esc = sub['proposed_escalation']
    print(f"\n  Role: {role}")
    print(f"    N scenarios: {sub['scenario_id'].nunique()}")
    print(f"    Unique proposed_escalation values: {esc.nunique()}")
    vc = esc.value_counts().sort_index()
    for val, cnt in vc.items():
        print(f"      escalation={val}: {cnt}")

# Ground truth
print("\n\n=== GROUND TRUTH ===")
gt = pd.read_csv(r'D:\Northeastern\LLM_Forecasting\outputs\multiscenario_v311\ground_truth.csv')
fcl = gt['final_crisis_level']
print(f"final_crisis_level:")
print(f"  min: {fcl.min():.4f}")
print(f"  max: {fcl.max():.4f}")
print(f"  mean: {fcl.mean():.4f}")
print(f"  median: {fcl.median():.4f}")
print(f"  std: {fcl.std():.4f}")
print(f"  N: {len(fcl)}")
print(f"  Distribution (histogram bins):")
bins = [0, 2, 4, 6, 8, 10, 10.01]
labels = ['[0-2)', '[2-4)', '[4-6)', '[6-8)', '[8-10)', '[10]']
gt['fcl_bin'] = pd.cut(fcl, bins=bins, labels=labels, right=False)
print(gt['fcl_bin'].value_counts().sort_index().to_string())

cp = gt['collapse_probability']
print(f"\ncollapse_probability:")
print(f"  min: {cp.min():.4f}")
print(f"  max: {cp.max():.4f}")
print(f"  mean: {cp.mean():.4f}")
print(f"  median: {cp.median():.4f}")
print(f"  std: {cp.std():.4f}")
print(f"  N: {len(cp)}")
