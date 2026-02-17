"""
Simplified persona system: Domain expertise + strategic orientation only.

Removes cognitive noise (Big Five, cognitive measures) to focus on
task-relevant attributes.
"""

import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List
from datetime import datetime


@dataclass
class SimplifiedProfile:
    """Simplified cognitive profile - expertise-focused"""

    # Identity
    persona_id: str
    name: str
    occupation: str

    # Domain Expertise (0-100)
    geopolitical_expertise: int
    military_expertise: int
    economic_expertise: int

    # Strategic Orientation
    strategic_orientation: str  # "hawkish", "dovish", "pragmatic"

    # Risk Tolerance (0-100)
    risk_tolerance: int = 50

    def to_natural_language(self) -> str:
        """Convert profile to prompt-friendly description"""

        # Expertise descriptions
        def expertise_level(score):
            if score >= 80: return "expert-level"
            elif score >= 60: return "strong"
            elif score >= 40: return "moderate"
            else: return "limited"

        geo_level = expertise_level(self.geopolitical_expertise)
        mil_level = expertise_level(self.military_expertise)
        econ_level = expertise_level(self.economic_expertise)

        # Strategic orientation description
        orientation_desc = {
            "hawkish": "You favor decisive action and tend to emphasize security threats and military options.",
            "dovish": "You favor diplomatic solutions and tend to emphasize de-escalation and cooperative approaches.",
            "pragmatic": "You weigh costs and benefits carefully and favor practical, evidence-based solutions."
        }

        # Risk tolerance description
        if self.risk_tolerance >= 75:
            risk_label = "HIGH"
            risk_desc = "You are comfortable with uncertainty and willing to stake out bold positions when your analysis supports it."
        elif self.risk_tolerance >= 50:
            risk_label = "MODERATE-HIGH"
            risk_desc = "You are fairly comfortable with uncertainty and will deviate from consensus when evidence warrants it."
        elif self.risk_tolerance >= 25:
            risk_label = "MODERATE-LOW"
            risk_desc = "You prefer well-supported estimates and tend to stay closer to base rates unless evidence is compelling."
        else:
            risk_label = "LOW"
            risk_desc = "You are cautious and conservative, preferring to stay close to base rates and conventional wisdom."

        desc = f"""You are {self.name}, a {self.occupation}.

EXPERTISE PROFILE:
- Geopolitical Analysis: {geo_level} ({self.geopolitical_expertise}/100)
- Military Strategy: {mil_level} ({self.military_expertise}/100)
- Economic Analysis: {econ_level} ({self.economic_expertise}/100)

STRATEGIC ORIENTATION: {self.strategic_orientation.upper()}
{orientation_desc[self.strategic_orientation]}

RISK TOLERANCE: {risk_label} ({self.risk_tolerance}/100)
{risk_desc}

When analyzing scenarios, draw on your areas of expertise and strategic perspective."""

        return desc


def generate_simplified_personas(n_personas: int = 100, seed: int = 42) -> List[SimplifiedProfile]:
    """
    Generate diverse simplified personas.

    Strategy:
    - 1/3 specialists (high in one domain, low in others)
    - 1/3 balanced generalists (moderate in all domains)
    - 1/3 dual-expertise (high in two domains)
    """
    random.seed(seed)
    personas = []

    # Occupation templates
    occupations = {
        "military": [
            "retired military intelligence officer",
            "defense policy analyst",
            "former military strategist",
            "national security consultant",
            "military historian"
        ],
        "diplomatic": [
            "former UN diplomat",
            "foreign policy advisor",
            "international relations professor",
            "diplomatic affairs analyst",
            "former ambassador"
        ],
        "economic": [
            "international economics professor",
            "global trade analyst",
            "economic policy consultant",
            "financial markets strategist",
            "development economics researcher"
        ],
        "generalist": [
            "geopolitical risk analyst",
            "intelligence analyst",
            "think tank researcher",
            "policy advisor",
            "strategic forecasting consultant"
        ]
    }

    # First/last names for diversity
    first_names = [
        "Sarah", "James", "Maria", "David", "Li", "Ahmed", "Emma", "Michael",
        "Priya", "Carlos", "Fatima", "John", "Yuki", "Anna", "Hassan", "Sofia",
        "Wei", "Olga", "Omar", "Elena", "Kwame", "Lucia", "Raj", "Ingrid"
    ]

    last_names = [
        "Mitchell", "Chen", "Rodriguez", "Smith", "Patel", "Kim", "Johnson",
        "Ivanova", "Martinez", "O'Brien", "Nakamura", "Singh", "Petrov", "Garcia",
        "Williams", "Hassan", "Kowalski", "Diaz", "Anderson", "Okonkwo", "Brown"
    ]

    # Generate personas
    for i in range(n_personas):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        persona_id = f"simplified_{i+1:03d}"

        # Determine persona type
        persona_type = i % 3  # 0=specialist, 1=generalist, 2=dual-expertise

        if persona_type == 0:  # Specialist
            specialist_domain = random.choice(["military", "diplomatic", "economic"])

            if specialist_domain == "military":
                geo = random.randint(40, 70)
                mil = random.randint(80, 95)
                econ = random.randint(20, 40)
                occupation = random.choice(occupations["military"])
                orientation = random.choice(["hawkish", "hawkish", "pragmatic"])  # weighted toward hawkish

            elif specialist_domain == "diplomatic":
                geo = random.randint(75, 95)
                mil = random.randint(20, 40)
                econ = random.randint(40, 70)
                occupation = random.choice(occupations["diplomatic"])
                orientation = random.choice(["dovish", "dovish", "pragmatic"])  # weighted toward dovish

            else:  # economic
                geo = random.randint(40, 70)
                mil = random.randint(20, 40)
                econ = random.randint(80, 95)
                occupation = random.choice(occupations["economic"])
                orientation = random.choice(["pragmatic", "pragmatic", "dovish"])

        elif persona_type == 1:  # Generalist
            geo = random.randint(50, 75)
            mil = random.randint(50, 75)
            econ = random.randint(50, 75)
            occupation = random.choice(occupations["generalist"])
            orientation = random.choice(["hawkish", "dovish", "pragmatic"])

        else:  # Dual-expertise
            domains = random.sample(["geo", "mil", "econ"], 2)

            geo = random.randint(75, 90) if "geo" in domains else random.randint(30, 50)
            mil = random.randint(75, 90) if "mil" in domains else random.randint(30, 50)
            econ = random.randint(75, 90) if "econ" in domains else random.randint(30, 50)

            # Pick occupation based on highest expertise
            if mil > max(geo, econ):
                occupation = random.choice(occupations["military"])
            elif geo > econ:
                occupation = random.choice(occupations["diplomatic"])
            else:
                occupation = random.choice(occupations["economic"])

            orientation = random.choice(["hawkish", "dovish", "pragmatic"])

        # Generate risk tolerance: normal(50, 25) clamped to [0, 100]
        # Slight bias: hawkish analysts tend higher risk tolerance, dovish tend lower
        if orientation == "hawkish":
            risk_mean = 60
        elif orientation == "dovish":
            risk_mean = 40
        else:
            risk_mean = 50
        risk_tolerance = int(max(0, min(100, random.gauss(risk_mean, 25))))

        personas.append(SimplifiedProfile(
            persona_id=persona_id,
            name=name,
            occupation=occupation,
            geopolitical_expertise=geo,
            military_expertise=mil,
            economic_expertise=econ,
            strategic_orientation=orientation,
            risk_tolerance=risk_tolerance
        ))

    random.seed()  # Reset seed
    return personas


def save_simplified_personas(personas: List[SimplifiedProfile],
                             filepath: str = None) -> str:
    """Save personas to JSON file"""
    if filepath is None:
        filepath = Path(__file__).parent / "persona_profiles_simplified.json"
    else:
        filepath = Path(filepath)

    # Convert to dict
    personas_dict = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "n_personas": len(personas),
            "version": "simplified_v1"
        },
        "personas": [asdict(p) for p in personas]
    }

    with open(filepath, 'w') as f:
        json.dump(personas_dict, f, indent=2)

    print(f"[OK] Saved {len(personas)} simplified personas to: {filepath}")
    return str(filepath)


def load_simplified_personas(filepath: str = None) -> List[SimplifiedProfile]:
    """Load personas from JSON file"""
    if filepath is None:
        filepath = Path(__file__).parent / "persona_profiles_simplified.json"
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        print(f"[WARNING] Persona file not found: {filepath}")
        print(f"Generating new personas...")
        personas = generate_simplified_personas()
        save_simplified_personas(personas, filepath)
        return personas

    with open(filepath, 'r') as f:
        data = json.load(f)

    personas = [SimplifiedProfile(**p) for p in data["personas"]]

    print(f"[OK] Loaded {len(personas)} simplified personas from: {filepath}")
    print(f"    Generated at: {data['metadata']['generated_at']}")

    return personas


if __name__ == "__main__":
    # Generate and save personas
    print("="*80)
    print("GENERATING SIMPLIFIED PERSONAS")
    print("="*80)

    personas = generate_simplified_personas(n_personas=500, seed=42)

    # Show distribution
    orientations = [p.strategic_orientation for p in personas]
    print(f"\nStrategic Orientation Distribution:")
    print(f"  Hawkish:   {orientations.count('hawkish')}/500")
    print(f"  Dovish:    {orientations.count('dovish')}/500")
    print(f"  Pragmatic: {orientations.count('pragmatic')}/500")

    # Risk tolerance distribution
    risk_vals = [p.risk_tolerance for p in personas]
    print(f"\nRisk Tolerance Distribution:")
    print(f"  Mean: {sum(risk_vals)/len(risk_vals):.1f}")
    print(f"  Min: {min(risk_vals)}, Max: {max(risk_vals)}")
    print(f"  Low (0-25): {sum(1 for r in risk_vals if r <= 25)}")
    print(f"  Mod-Low (26-49): {sum(1 for r in risk_vals if 26 <= r <= 49)}")
    print(f"  Mod-High (50-74): {sum(1 for r in risk_vals if 50 <= r <= 74)}")
    print(f"  High (75-100): {sum(1 for r in risk_vals if r >= 75)}")

    # Show examples
    print(f"\nExample Personas:")
    for i in [0, 1, 2]:
        p = personas[i]
        print(f"\n{i+1}. {p.name} ({p.occupation})")
        print(f"   Geo: {p.geopolitical_expertise}, Mil: {p.military_expertise}, Econ: {p.economic_expertise}")
        print(f"   Orientation: {p.strategic_orientation}, Risk Tolerance: {p.risk_tolerance}")

    # Save
    save_simplified_personas(personas)

    print("\n[OK] Simplified persona system ready!")
