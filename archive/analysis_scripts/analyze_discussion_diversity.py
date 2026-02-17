#!/usr/bin/env python3
"""
Analyze diversity in agent debate transcripts across scenarios
"""

import re
from pathlib import Path
from collections import Counter

output_file = Path("C:/Users/seanw/AppData/Local/Temp/claude/C--Users-seanw/tasks/b943d0a.output")

with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Split into scenarios
scenarios = re.split(r'--- Simulating (scenario_\d+) ---', content)

print("="*70)
print("DISCUSSION DIVERSITY ANALYSIS")
print("="*70)

# Keywords to track
economic_keywords = ['economic', 'economy', 'sanctions', 'reserves', 'inflation', 'GDP', 'cost']
military_keywords = ['military', 'frontline', 'battlefield', 'forces', 'victory', 'defeat', 'troops']
diplomatic_keywords = ['diplomatic', 'international', 'coalition', 'support', 'allies', 'isolation']
strategic_keywords = ['strategy', 'strategic', 'long-term', 'sustainable', 'escalation', 'de-escalate']
domestic_keywords = ['domestic', 'public', 'morale', 'political', 'support', 'legitimacy']

keyword_sets = {
    'Economic': economic_keywords,
    'Military': military_keywords,
    'Diplomatic': diplomatic_keywords,
    'Strategic': strategic_keywords,
    'Domestic': domestic_keywords
}

for i in range(1, len(scenarios), 2):
    scenario_id = scenarios[i]
    scenario_text = scenarios[i+1] if i+1 < len(scenarios) else ""

    if not scenario_text:
        continue

    # Extract coordination section (up to action execution)
    coord_match = re.search(r'Pre-action coordination.*?(?=\[Step 3\])', scenario_text, re.DOTALL)
    if not coord_match:
        continue

    coordination = coord_match.group(0)

    print(f"\n{'='*70}")
    print(f"{scenario_id.upper()}")
    print(f"{'='*70}")

    # Count agent statements
    agent_statements = re.findall(r'((?:General|Minister|Dr\.|Director|Deputy|President|Under-Secretary)[^:]+):', coordination)
    agent_counts = Counter(agent_statements)

    print(f"\nAgent participation ({len(agent_statements)} total statements):")
    for agent, count in sorted(agent_counts.items(), key=lambda x: -x[1])[:6]:
        print(f"  {agent}: {count} statements")

    # Extract actual arguments (first round only for comparison)
    first_round = re.findall(r'\[(?:HAWK|DOVE|MODERATE)\]: ([^\n]+)', coordination)

    print(f"\nSample arguments (first 3):")
    for j, arg in enumerate(first_round[:3], 1):
        preview = arg[:120] + "..." if len(arg) > 120 else arg
        print(f"  {j}. {preview}")

    # Theme analysis
    print(f"\nThematic focus:")
    coord_lower = coordination.lower()
    for theme, keywords in keyword_sets.items():
        count = sum(coord_lower.count(kw) for kw in keywords)
        print(f"  {theme}: {count} mentions")

    # Unique phrases (look for distinctive arguments)
    print(f"\nDistinctive phrases:")
    distinctive_phrases = [
        ("economic strain", coord_lower.count("economic strain")),
        ("reserves", coord_lower.count("reserves")),
        ("frontline", coord_lower.count("frontline")),
        ("sanctions", coord_lower.count("sanctions")),
        ("diplomatic", coord_lower.count("diplomatic")),
        ("coalition", coord_lower.count("coalition")),
        ("escalation", coord_lower.count("escalation")),
    ]
    for phrase, count in sorted(distinctive_phrases, key=lambda x: -x[1])[:5]:
        if count > 0:
            print(f"  '{phrase}': {count}")

# Cross-scenario comparison
print(f"\n{'='*70}")
print("CROSS-SCENARIO DIVERSITY ASSESSMENT")
print(f"{'='*70}")

print("""
To assess if discussions are meaningfully different across scenarios,
we look for:

1. Different thematic emphasis (economic vs military focus)
2. Different agent participation patterns
3. Scenario-specific arguments (references to specific parameters)
4. Debate structure variation (length, back-and-forth)

With only N=3, we expect:
- Some overlap in general themes (all war scenarios)
- Variation in specific emphasis based on scenario parameters
- Different argument priorities (e.g., more economic focus with high sanctions)
""")

print("\nRecommendation: Full assessment requires N=10+ scenarios to see clear patterns.")
print("="*70)
