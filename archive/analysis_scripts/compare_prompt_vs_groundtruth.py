"""
Compare information in prompts vs ground truth reasoning

Checks if ground truth assessments are justified by prompt content
"""

import pandas as pd
from pathlib import Path

# Load ground truth
ground_truth = pd.read_csv("D:/Northeastern/LLM_Forecasting/outputs/assessments.csv")

# Key periods to analyze
periods_to_check = [1, 5, 8, 10]

print("=" * 80)
print("COMPARING PROMPT CONTENT vs GROUND TRUTH REASONING")
print("=" * 80)
print()

prompts_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/human_forecasting/TRUE")

for period in periods_to_check:
    gt_row = ground_truth[ground_truth['period'] == period].iloc[0]

    print(f"PERIOD {period}")
    print("=" * 80)
    print(f"Ground Truth Probability: {gt_row['probability']*100:.0f}%")
    print(f"Trend: {gt_row['trend']}")
    print()

    # Read prompt
    prompt_path = prompts_dir / f"period_{period:02d}.txt"
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_text = f.read()

    # Extract key sections
    if "MAJOR EVENTS" in prompt_text:
        events_start = prompt_text.find("**MAJOR EVENTS**")
        events_end = prompt_text.find("</external_events>")
        events_text = prompt_text[events_start:events_end]

        print("ESCALATING SIGNALS IN PROMPT:")
        print("-" * 40)
        for line in events_text.split('\n'):
            line = line.strip()
            if line.startswith('•'):
                # Check if it's actually escalating
                escalation_words = ['crisis', 'buckle', 'collapse', 'threat', 'attack',
                                   'gains', 'encircle', 'breakthrough', 'deteriorat',
                                   'worsening', 'pressure']
                if any(word in line.lower() for word in escalation_words):
                    print(f"  {line}")

        print()
        print("STABILIZING SIGNALS IN PROMPT:")
        print("-" * 40)
        for line in events_text.split('\n'):
            line = line.strip()
            if line.startswith('•'):
                stability_words = ['defend', 'stabilize', 'support', 'position',
                                  'maintain', 'hold', 'advantage']
                if any(word in line.lower() for word in stability_words):
                    print(f"  {line}")

    # Check for key status line
    if "CURRENT SITUATION" in prompt_text:
        situation_start = prompt_text.find("CURRENT SITUATION")
        situation_end = prompt_text.find("CURRENT PERIOD DEVELOPMENTS")
        situation_text = prompt_text[situation_start:situation_end]

        print()
        print("CURRENT SITUATION SUMMARY:")
        print("-" * 40)
        for line in situation_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('━') and not line.startswith('CURRENT'):
                if 'evenly matched' in line.lower() or 'territory' in line.lower() or 'sanctions' in line.lower() or 'support' in line.lower():
                    print(f"  {line}")

    # Show ground truth reasoning
    print()
    print("GROUND TRUTH REASONING (From Simulation):")
    print("-" * 40)
    if pd.notna(gt_row['key_factors']):
        reasoning = str(gt_row['key_factors'])
        # Truncate if too long
        if len(reasoning) > 400:
            reasoning = reasoning[:400] + "..."
        print(f"  {reasoning}")
    else:
        print("  [No detailed reasoning provided]")

    print()
    print("ANALYSIS:")
    print("-" * 40)

    # Check for information asymmetry
    gt_reasoning_lower = str(gt_row['key_factors']).lower() if pd.notna(gt_row['key_factors']) else ""
    prompt_lower = prompt_text.lower()

    # Key concepts in GT but possibly not in prompt
    gt_only_concepts = []
    if 'internal' in gt_reasoning_lower and 'internal' not in prompt_lower:
        gt_only_concepts.append("internal dynamics")
    if 'faction' in gt_reasoning_lower and 'faction' not in prompt_lower:
        gt_only_concepts.append("internal factions")
    if '%.%' in gt_reasoning_lower:  # percentage mentioned
        gt_only_concepts.append("specific numerical data (e.g., 4.4% territory loss)")
    if 'buckling' in gt_reasoning_lower and 'buckle' not in prompt_lower:
        gt_only_concepts.append("internal buckling")

    if gt_only_concepts:
        print(f"  INFORMATION GAP: Ground truth reasoning uses:")
        for concept in gt_only_concepts:
            print(f"    - {concept} (not clearly stated in prompt)")

    # Check if prompt is ambiguous
    has_escalation = any(word in prompt_lower for word in ['buckle', 'gains', 'encircle', 'threat', 'attack'])
    has_stability = 'strong' in prompt_lower and 'support' in prompt_lower

    if has_escalation and has_stability:
        print(f"  MIXED SIGNALS: Prompt contains both escalating and stabilizing information")

    # Check for contradictions
    if 'no territory has changed hands' in prompt_lower and 'territorial gain' in prompt_lower:
        print(f"  CONTRADICTION: Prompt says both 'territorial gains' and 'no territory changed'")

    print()
    print("=" * 80)
    print()
