import pandas as pd
import numpy as np
import sys

outfile = r'D:\Northeastern\LLM_Forecasting\experiment_results\pid_analysis_v311_crisis_full\analysis_output.txt'
with open(outfile, 'w') as f:
    df = pd.read_csv(r'D:\Northeastern\LLM_Forecasting\experiment_results\pid_analysis_v311_crisis_full\raw_escalation_matrix.csv')
    primary = df[df['priority'] == 'primary']

    f.write("=== NOVARIS (primary only) ===\n")
    nov = primary[primary['faction_name'] == 'Novaris']
    f.write(f"Total primary rows: {len(nov)}\n")
    for role in sorted(nov['agent_role'].unique()):
        sub = nov[nov['agent_role'] == role]
        esc = sub['proposed_escalation']
        f.write(f"\n  Role: {role}\n")
        f.write(f"    N scenarios: {sub['scenario_id'].nunique()}\n")
        f.write(f"    Unique proposed_escalation values: {esc.nunique()}\n")
        vc = esc.value_counts().sort_index()
        for val, cnt in vc.items():
            f.write(f"      escalation={val}: {cnt}\n")

    f.write("\n\n=== TETHYS (primary only) ===\n")
    teth = primary[primary['faction_name'] == 'Tethys']
    f.write(f"Total primary rows: {len(teth)}\n")
    for role in sorted(teth['agent_role'].unique()):
        sub = teth[teth['agent_role'] == role]
        esc = sub['proposed_escalation']
        f.write(f"\n  Role: {role}\n")
        f.write(f"    N scenarios: {sub['scenario_id'].nunique()}\n")
        f.write(f"    Unique proposed_escalation values: {esc.nunique()}\n")
        vc = esc.value_counts().sort_index()
        for val, cnt in vc.items():
            f.write(f"      escalation={val}: {cnt}\n")

    f.write("\n\n=== GROUND TRUTH ===\n")
    gt = pd.read_csv(r'D:\Northeastern\LLM_Forecasting\outputs\multiscenario_v311\ground_truth.csv')
    fcl = gt['final_crisis_level']
    f.write(f"final_crisis_level:\n")
    f.write(f"  min: {fcl.min():.4f}\n")
    f.write(f"  max: {fcl.max():.4f}\n")
    f.write(f"  mean: {fcl.mean():.4f}\n")
    f.write(f"  median: {fcl.median():.4f}\n")
    f.write(f"  std: {fcl.std():.4f}\n")
    f.write(f"  N: {len(fcl)}\n")

    # Distribution with finer bins
    f.write(f"  Distribution:\n")
    for threshold in [7, 8, 9, 9.5, 10]:
        count_below = (fcl < threshold).sum()
        count_at_or_above = (fcl >= threshold).sum()
        f.write(f"    < {threshold}: {count_below}  |  >= {threshold}: {count_at_or_above}\n")

    f.write(f"  Quintiles:\n")
    for q in [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
        f.write(f"    {q*100:.0f}th percentile: {fcl.quantile(q):.4f}\n")

    cp = gt['collapse_probability']
    f.write(f"\ncollapse_probability:\n")
    f.write(f"  min: {cp.min():.4f}\n")
    f.write(f"  max: {cp.max():.4f}\n")
    f.write(f"  mean: {cp.mean():.4f}\n")
    f.write(f"  median: {cp.median():.4f}\n")
    f.write(f"  std: {cp.std():.4f}\n")
    f.write(f"  N: {len(cp)}\n")

    # Also show proposed_action value_counts for context
    f.write("\n\n=== NOVARIS proposed_action by role (primary) ===\n")
    for role in sorted(nov['agent_role'].unique()):
        sub = nov[nov['agent_role'] == role]
        f.write(f"\n  Role: {role}\n")
        vc = sub['proposed_action'].value_counts()
        for val, cnt in vc.items():
            f.write(f"    {val}: {cnt}\n")

    f.write("\n\n=== TETHYS proposed_action by role (primary) ===\n")
    for role in sorted(teth['agent_role'].unique()):
        sub = teth[teth['agent_role'] == role]
        f.write(f"\n  Role: {role}\n")
        vc = sub['proposed_action'].value_counts()
        for val, cnt in vc.items():
            f.write(f"    {val}: {cnt}\n")

print("Done - output written to", outfile)
