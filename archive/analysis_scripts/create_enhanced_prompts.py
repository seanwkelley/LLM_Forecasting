"""
Create enhanced prompts with KEY_FACTORS information (without probability)
"""

from pathlib import Path

# Directory paths
enhanced_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/human_forecasting/ENHANCED")
enhanced_dir.mkdir(parents=True, exist_ok=True)

standard_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/human_forecasting/TRUE")
assessment_dir = Path("D:/Northeastern/LLM_Forecasting/outputs")

print("Creating enhanced prompts with full aggregator analysis (NO probability)...")
print("=" * 80)

for period in range(1, 11):
    # Load standard prompt
    standard_file = standard_dir / f"period_{period:02d}.txt"
    with open(standard_file, 'r', encoding='utf-8') as f:
        standard_text = f.read()

    # Load assessment file
    assessment_file = assessment_dir / f"assessment_period_{period}.txt"
    with open(assessment_file, 'r', encoding='utf-8') as f:
        assessment_text = f.read()

    # Parse assessment file
    lines = assessment_text.strip().split('\n')
    probability = None
    confidence = None
    trend = None
    key_factors = None

    for line in lines:
        if line.startswith('PROBABILITY:'):
            probability = float(line.split(':')[1].strip())
        elif line.startswith('CONFIDENCE:'):
            confidence = line.split(':')[1].strip()
        elif line.startswith('TREND:'):
            trend = line.split(':')[1].strip()
        elif line.startswith('KEY_FACTORS:'):
            key_factors = line.split(':', 1)[1].strip()

    # Create enhanced information section (WITHOUT probability)
    enhanced_section = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETAILED INTELLIGENCE ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**TREND: {trend}**
**ANALYTIC CONFIDENCE: {confidence}**

"""

    # Add KEY_FACTORS if available
    if key_factors:
        enhanced_section += f"""**DETAILED ANALYSIS:**

{key_factors}

"""

    enhanced_section += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    # Insert enhanced section before "YOUR FORECAST"
    enhanced_text = standard_text.replace(
        "YOUR FORECAST",
        enhanced_section + "YOUR FORECAST"
    )

    # Save enhanced prompt
    enhanced_file = enhanced_dir / f"period_{period:02d}.txt"
    with open(enhanced_file, 'w', encoding='utf-8') as f:
        f.write(enhanced_text)

    print(f"Period {period:2d}: Created enhanced prompt (Truth: {probability*100:.0f}%, Trend: {trend})")

print()
print("=" * 80)
print(f"Enhanced prompts saved to: {enhanced_dir}")
print("=" * 80)
