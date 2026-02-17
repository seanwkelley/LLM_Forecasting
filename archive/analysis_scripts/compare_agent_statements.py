#!/usr/bin/env python3
"""
Compare what the SAME agents say across different scenarios.
The debate structure is fixed by design - question is whether CONTENT varies.
"""

import re
from pathlib import Path

output_file = Path("C:/Users/seanw/AppData/Local/Temp/claude/C--Users-seanw/tasks/b943d0a.output")

with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Split by scenario markers
scenario_splits = re.split(r'--- Simulating (scenario_\d+) ---', content)

# Extract MAJOR POWER coordination for each scenario
scenarios = {}
for i in range(1, len(scenario_splits), 2):
    sid = scenario_splits[i]
    text = scenario_splits[i+1] if i+1 < len(scenario_splits) else ""

    # Get major power coordination section
    match = re.search(
        r'Pre-action coordination within MAJOR POWER faction\.\.\.\n(.*?)(?=\[Step 3\])',
        text, re.DOTALL
    )
    if match:
        scenarios[sid] = match.group(1)

# Extract individual agent statements
def extract_statements(coord_text):
    """Extract each agent's statement with full text."""
    pattern = r'    ((?:General|Minister|Dr\.|Director|Deputy Minister|President)[^[]+)\[(\w+)\]: (.+?)(?=\n    (?:General|Minister|Dr\.|Director|Deputy|President)|\n  \[Step|\Z)'
    matches = re.findall(pattern, coord_text, re.DOTALL)
    statements = {}
    for name, stance, text in matches:
        name = name.strip()
        if name not in statements:
            statements[name] = []
        statements[name].append(text.strip())
    return statements

# Compare same agents across scenarios
print("="*70)
print("SAME-AGENT COMPARISON ACROSS SCENARIOS")
print("="*70)
print("\nQuestion: Does the same agent say different things in different scenarios?")
print("(Debate structure is fixed by design - we're checking content variation)\n")

# Get scenario parameters for context
params = {
    'scenario_001': 'Territory: 36.6% | Sanctions: 58.9% | Support: 72.3%',
    'scenario_002': 'Territory: 37.5% | Sanctions: 10.8% | Support: 57.5%',
    'scenario_003': 'Territory: 11.4% | Sanctions: 52.6% | Support: 73.1%',
}

all_statements = {}
for sid, coord in scenarios.items():
    all_statements[sid] = extract_statements(coord)

# Compare key agents
key_agents = [
    'General Viktor Krasnov',
    'Dr. Natasha Petrova',
    'Minister Dmitri Volkov',
]

for agent in key_agents:
    print(f"\n{'='*70}")
    print(f"AGENT: {agent}")
    print(f"{'='*70}")

    for sid in sorted(scenarios.keys()):
        stmts = all_statements.get(sid, {})
        agent_stmts = stmts.get(agent, [])

        print(f"\n  --- {sid} ({params.get(sid, '')}) ---")
        if agent_stmts:
            # Show first statement (opening position)
            first = agent_stmts[0]
            # Clean up and show first 300 chars
            first_clean = first.replace('\n', ' ').strip()
            print(f"  OPENING: {first_clean[:300]}...")

            if len(agent_stmts) > 1:
                second = agent_stmts[1]
                second_clean = second.replace('\n', ' ').strip()
                print(f"  REBUTTAL: {second_clean[:300]}...")
        else:
            print(f"  [No statements found]")

# Also compare SMALL POWER coordination
print(f"\n\n{'='*70}")
print("SMALL POWER FACTION - OPENING STATEMENTS")
print(f"{'='*70}")

for i in range(1, len(scenario_splits), 2):
    sid = scenario_splits[i]
    text = scenario_splits[i+1] if i+1 < len(scenario_splits) else ""

    match = re.search(
        r'Pre-action coordination within SMALL POWER faction\.\.\.\n(.*?)(?=\[Step 3\])',
        text, re.DOTALL
    )
    if match:
        sp_coord = match.group(1)
        # Get President's opening
        pres_match = re.search(r'President Elena Marchetti \[HAWK\]: (.+?)(?=\n    General)', sp_coord, re.DOTALL)
        if pres_match:
            opening = pres_match.group(1).replace('\n', ' ').strip()
            print(f"\n  --- {sid} ({params.get(sid, '')}) ---")
            print(f"  President Marchetti: {opening[:300]}...")

# Similarity check
print(f"\n\n{'='*70}")
print("DIVERSITY VERDICT")
print(f"{'='*70}")

# Check for verbatim repetition
for agent in key_agents:
    openings = []
    for sid in sorted(scenarios.keys()):
        stmts = all_statements.get(sid, {}).get(agent, [])
        if stmts:
            openings.append(stmts[0][:100])

    if len(openings) >= 2:
        # Check if any two are identical
        identical = any(openings[i] == openings[j]
                       for i in range(len(openings))
                       for j in range(i+1, len(openings)))

        # Check word overlap
        words_sets = [set(o.lower().split()) for o in openings]
        if len(words_sets) >= 2:
            overlaps = []
            for i in range(len(words_sets)):
                for j in range(i+1, len(words_sets)):
                    overlap = len(words_sets[i] & words_sets[j]) / max(len(words_sets[i] | words_sets[j]), 1)
                    overlaps.append(overlap)
            avg_overlap = sum(overlaps) / len(overlaps)
        else:
            avg_overlap = 0

        status = "[IDENTICAL]" if identical else f"[Word overlap: {avg_overlap:.0%}]"
        print(f"  {agent}: {status}")
