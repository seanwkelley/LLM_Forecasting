"""
Persona Generator - Creates reproducible cognitive profiles for personalized forecasters

Generates ~500 diverse personas using stratified sampling with fixed random seed.
All personas are reproducible given the same RANDOM_SEED value.
"""

import json
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Dict
from pathlib import Path
from datetime import datetime

# REPRODUCIBILITY: Fixed random seed
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# Generation parameters (for documentation)
GENERATION_CONFIG = {
    "n_personas": 500,
    "random_seed": RANDOM_SEED,
    "generation_date": datetime.now().isoformat(),
    "version": "1.0"
}


@dataclass
class CognitiveProfile:
    """
    Full cognitive and demographic profile for personalized forecasters

    Based on established cognitive science measures:
    - Big Five personality traits
    - Domain expertise areas
    - Cognitive abilities (Ravens, Bayesian updating, CRT, etc.)
    - Decision-making style and preferences
    """

    # Identity
    persona_id: str
    name: str
    age: int
    gender: str
    education: str  # "high_school", "bachelors", "masters", "phd"
    occupation: str

    # Big Five Personality (0-100 scale)
    openness: int
    conscientiousness: int
    extraversion: int
    agreeableness: int
    neuroticism: int

    # Domain Expertise (0-100 scale)
    geopolitical_expertise: int
    economic_expertise: int
    military_expertise: int
    statistical_expertise: int

    # Cognitive Measures (user requirements)
    general_intelligence: int          # Raven's Matrices equivalent (0-100)
    bayesian_updating_skill: int       # Philips & Edwards, 1966 (0-100)
    coherence_forecasting: int         # Coherence Forecasting Scale (0-100)
    cognitive_reflection_test: int     # CRT score (0-7)
    denominator_neglect: int           # Tendency (0-100, higher = more prone)
    decision_rule_competence: int      # ADMC-DR score (0-100)

    # Preferences
    risk_tolerance: int                # 0=risk averse, 100=risk seeking
    political_leaning: int             # 0=far left, 50=center, 100=far right

    # Cognitive Style
    thinking_style: str                # "analytical", "intuitive", "mixed"
    information_processing: str        # "systematic", "heuristic", "adaptive"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_natural_language(self) -> str:
        """
        Convert profile to natural language description for system prompt

        Target: 200-225 words for consistency across all personas.
        Uses qualitative descriptions instead of numbers for better LLM interpretation.
        """

        # Education map
        education_map = {
            "high_school": "high school education",
            "bachelors": "bachelor's degree",
            "masters": "master's degree",
            "phd": "PhD"
        }

        # === SECTION 1: Identity and Background (2 sentences) ===
        intro = f"You are {self.name}, a {self.age}-year-old {self.occupation} with a {education_map[self.education]}."

        # Add context based on occupation
        if "professor" in self.occupation.lower() or "phd" in self.education:
            background = "You bring an academic perspective with strong analytical training and research experience."
        elif "analyst" in self.occupation.lower():
            background = "You bring professional experience analyzing complex situations and advising on strategic decisions."
        elif "economist" in self.occupation.lower():
            background = "Your training emphasizes quantitative reasoning and systematic analysis of economic factors."
        elif "military" in self.occupation.lower() or "defense" in self.occupation.lower():
            background = "Your background provides practical understanding of strategic and operational considerations."
        elif "diplomat" in self.occupation.lower():
            background = "You bring experience in international relations and navigating complex political dynamics."
        else:
            background = "You bring diverse professional experience to analyzing geopolitical situations."

        # === SECTION 2: Personality (Big Five - always describe all 5) ===
        personality_parts = []

        # Openness
        if self.openness >= 70:
            personality_parts.append("highly open to new ideas and unconventional approaches")
        elif self.openness <= 30:
            personality_parts.append("prefer established methods and conventional wisdom")
        else:
            personality_parts.append("moderately open to new approaches while respecting tradition")

        # Conscientiousness
        if self.conscientiousness >= 70:
            personality_parts.append("extremely thorough and detail-oriented in your analysis")
        elif self.conscientiousness <= 30:
            personality_parts.append("focus on big-picture patterns rather than granular details")
        else:
            personality_parts.append("balance attention to detail with broader strategic thinking")

        # Extraversion (affects collaboration style)
        if self.extraversion >= 70:
            collab_style = "You are energized by discussing ideas with others and thinking aloud."
        elif self.extraversion <= 30:
            collab_style = "You prefer to reflect independently before forming conclusions."
        else:
            collab_style = "You value both independent reflection and collaborative discussion."

        # Agreeableness
        if self.agreeableness >= 70:
            personality_parts.append("seek consensus and value collaborative problem-solving")
        elif self.agreeableness <= 30:
            personality_parts.append("critically challenge assumptions and push back on weak arguments")
        else:
            personality_parts.append("balance cooperation with constructive skepticism")

        # Neuroticism (affects threat sensitivity)
        if self.neuroticism >= 70:
            threat_sense = "You are highly attuned to potential risks, threats, and downside scenarios."
        elif self.neuroticism <= 30:
            threat_sense = "You remain calm and emotionally stable when analyzing high-stakes situations."
        else:
            threat_sense = "You maintain composure while staying alert to potential risks."

        personality_text = f"Personality-wise, you are {', and '.join(personality_parts)}. {collab_style} {threat_sense}"

        # === SECTION 3: Domain Expertise (always describe all 4 domains) ===
        def expertise_level(score):
            if score >= 85: return "exceptional expertise in"
            elif score >= 70: return "strong expertise in"
            elif score >= 55: return "solid working knowledge of"
            elif score >= 40: return "basic familiarity with"
            else: return "limited background in"

        expertise_text = f"Regarding domain knowledge: you have {expertise_level(self.geopolitical_expertise)} geopolitical analysis and international relations, {expertise_level(self.economic_expertise)} economic factors and market dynamics, {expertise_level(self.military_expertise)} military strategy and conflict dynamics, and {expertise_level(self.statistical_expertise)} statistical reasoning and quantitative analysis."

        # === SECTION 4: Cognitive Profile (5-6 aspects) ===
        cognitive_parts = []

        # Intelligence
        if self.general_intelligence >= 85:
            cognitive_parts.append("You have exceptional analytical abilities and grasp complex multi-layered problems quickly")
        elif self.general_intelligence >= 70:
            cognitive_parts.append("You have strong analytical abilities and can work through complex reasoning systematically")
        elif self.general_intelligence >= 55:
            cognitive_parts.append("You have solid reasoning abilities for analyzing moderately complex situations")
        else:
            cognitive_parts.append("You rely more on accumulated experience and pattern recognition than complex analytical reasoning")

        # Bayesian updating
        if self.bayesian_updating_skill >= 75:
            cognitive_parts.append("You excel at updating your beliefs when presented with new evidence, adjusting probabilities fluidly")
        elif self.bayesian_updating_skill >= 55:
            cognitive_parts.append("You can incorporate new information into your thinking reasonably well")
        elif self.bayesian_updating_skill <= 35:
            cognitive_parts.append("You tend to anchor strongly on initial impressions and are slow to revise your views")
        else:
            cognitive_parts.append("You update your beliefs moderately when confronted with new evidence")

        # CRT and deliberate thinking
        if self.cognitive_reflection_test >= 6:
            cognitive_parts.append("You excel at catching intuitive errors through deliberate, careful reflection")
        elif self.cognitive_reflection_test >= 4:
            cognitive_parts.append("You can identify and correct intuitive mistakes with focused effort")
        elif self.cognitive_reflection_test <= 2:
            cognitive_parts.append("You rely heavily on intuition and first impressions rather than deliberate analytical checking")
        else:
            cognitive_parts.append("You use a mix of intuition and deliberate analysis in your reasoning")

        # Base rate attention (inverse of denominator neglect)
        if self.denominator_neglect <= 30:
            cognitive_parts.append("You are particularly attentive to base rates and statistical fundamentals when evaluating scenarios")
        elif self.denominator_neglect >= 70:
            cognitive_parts.append("You sometimes focus more on vivid specific cases than underlying base rates and probabilities")

        # Coherence
        if self.coherence_forecasting >= 75:
            cognitive_parts.append("Your probability judgments tend to be internally consistent and logically coherent")
        elif self.coherence_forecasting <= 35:
            cognitive_parts.append("You sometimes make probability estimates that may be inconsistent with each other")

        # Decision competence
        if self.decision_rule_competence >= 80:
            cognitive_parts.append("You consistently apply sound decision rules and avoid common reasoning pitfalls")
        elif self.decision_rule_competence <= 40:
            cognitive_parts.append("You occasionally fall into common decision-making traps and biases")

        cognitive_text = ". ".join(cognitive_parts) + "."

        # === SECTION 5: Forecasting Approach (risk tolerance + thinking style) ===
        if self.risk_tolerance >= 75:
            risk_desc = "You are comfortable with uncertainty and willing to stake out bold, contrarian positions when your analysis supports them"
        elif self.risk_tolerance >= 60:
            risk_desc = "You are moderately comfortable with uncertainty and will take calculated risks in your forecasts"
        elif self.risk_tolerance >= 40:
            risk_desc = "You take a balanced, moderate approach to risk in your probability estimates"
        elif self.risk_tolerance >= 25:
            risk_desc = "You lean toward caution and conservatism in your probability assessments"
        else:
            risk_desc = "You are quite cautious and conservative, preferring to avoid extreme probability estimates"

        style_map = {
            "analytical": "favor structured, systematic analysis breaking problems into components",
            "intuitive": "favor holistic pattern recognition and gut-level synthesis",
            "mixed": "flexibly combine analytical structure with intuitive pattern recognition"
        }

        process_map = {
            "systematic": "work methodically through information step-by-step",
            "heuristic": "rely on mental shortcuts and rules of thumb to process information efficiently",
            "adaptive": "adapt your information processing strategy based on the situation"
        }

        approach_text = f"{risk_desc}. In terms of cognitive style, you {style_map[self.thinking_style]}, and you {process_map[self.information_processing]}."

        # === SECTION 6: Political Worldview ===
        if self.political_leaning <= 20:
            political_desc = "strongly left-leaning (progressive)"
            influence_desc = "which may lead you to emphasize social justice concerns, skepticism of military force, and wariness of right-wing authoritarian actors"
        elif self.political_leaning <= 40:
            political_desc = "left-leaning (liberal)"
            influence_desc = "which may lead you to emphasize diplomatic solutions, international cooperation, and humanitarian concerns"
        elif self.political_leaning <= 48:
            political_desc = "center-left (moderate liberal)"
            influence_desc = "which may lead you to balance pragmatic realism with liberal democratic values"
        elif self.political_leaning <= 52:
            political_desc = "politically centrist"
            influence_desc = "which may help you consider multiple perspectives without strong ideological priors"
        elif self.political_leaning <= 60:
            political_desc = "center-right (moderate conservative)"
            influence_desc = "which may lead you to emphasize stability, order, and measured responses to threats"
        elif self.political_leaning <= 80:
            political_desc = "right-leaning (conservative)"
            influence_desc = "which may lead you to emphasize national security, strong deterrence, and skepticism of appeasement"
        else:
            political_desc = "strongly right-leaning (very conservative)"
            influence_desc = "which may lead you to emphasize military strength, wariness of adversaries, and preference for decisive action"

        worldview_text = f"Your worldview is {political_desc}, {influence_desc}."

        # === COMPILE FULL DESCRIPTION ===
        description = f"""{intro} {background}

{personality_text}

{expertise_text}

{cognitive_text}

{approach_text}

{worldview_text}"""

        return description


def sample_occupation(education: str, rng: np.random.Generator) -> str:
    """
    Sample occupation conditional on education level
    Ensures realistic education-occupation pairings
    """
    occupations_by_education = {
        "high_school": [
            "journalist", "business analyst", "military veteran",
            "logistics coordinator", "sales manager"
        ],
        "bachelors": [
            "policy analyst", "financial analyst", "journalist",
            "business consultant", "military officer", "data analyst",
            "project manager", "government administrator"
        ],
        "masters": [
            "senior policy analyst", "economist", "intelligence analyst",
            "think tank researcher", "corporate strategist", "diplomat",
            "risk analyst", "defense contractor", "academic researcher"
        ],
        "phd": [
            "professor of political science", "professor of economics",
            "senior intelligence analyst", "think tank fellow",
            "research scientist", "quantitative analyst", "strategic advisor",
            "independent researcher"
        ]
    }

    return rng.choice(occupations_by_education[education])


def sample_expertise_correlated(education: str, occupation: str, rng: np.random.Generator) -> Dict[str, int]:
    """
    Sample domain expertise with realistic correlations

    - Higher education → generally higher expertise
    - Occupation influences expertise distribution
    - Some correlation between related domains
    """

    # Base expertise levels by education
    education_base = {
        "high_school": (30, 15),  # (mean, std)
        "bachelors": (50, 15),
        "masters": (65, 15),
        "phd": (75, 12)
    }

    mean, std = education_base[education]

    # Sample base expertise
    expertise = {
        "geopolitical_expertise": int(np.clip(rng.normal(mean, std), 0, 100)),
        "economic_expertise": int(np.clip(rng.normal(mean, std), 0, 100)),
        "military_expertise": int(np.clip(rng.normal(mean, std), 0, 100)),
        "statistical_expertise": int(np.clip(rng.normal(mean, std), 0, 100))
    }

    # Occupation-specific boosts
    occupation_boosts = {
        "economist": {"economic_expertise": 20, "statistical_expertise": 15},
        "intelligence analyst": {"geopolitical_expertise": 20, "military_expertise": 15},
        "military": {"military_expertise": 25, "geopolitical_expertise": 10},
        "think tank": {"geopolitical_expertise": 20, "economic_expertise": 10},
        "professor of economics": {"economic_expertise": 25, "statistical_expertise": 20},
        "professor of political science": {"geopolitical_expertise": 25},
        "quantitative analyst": {"statistical_expertise": 25, "economic_expertise": 15},
        "diplomat": {"geopolitical_expertise": 20},
        "journalist": {"geopolitical_expertise": 10}
    }

    # Apply occupation boosts
    for key_word, boosts in occupation_boosts.items():
        if key_word in occupation.lower():
            for domain, boost in boosts.items():
                expertise[domain] = min(100, expertise[domain] + boost)

    return expertise


def generate_persona_name(persona_id: int, gender: str, rng: np.random.Generator) -> str:
    """Generate realistic analyst names"""

    first_names_male = [
        "James", "Michael", "Robert", "David", "William", "Richard", "Thomas", "Charles",
        "Daniel", "Matthew", "Andrew", "Joseph", "Christopher", "Mark", "Paul", "Steven",
        "Kenneth", "Brian", "Edward", "Ronald", "Kevin", "Jason", "Jeffrey", "Ryan"
    ]

    first_names_female = [
        "Mary", "Jennifer", "Linda", "Patricia", "Elizabeth", "Susan", "Jessica", "Sarah",
        "Karen", "Nancy", "Lisa", "Margaret", "Betty", "Sandra", "Ashley", "Dorothy",
        "Kimberly", "Emily", "Michelle", "Carol", "Amanda", "Melissa", "Deborah", "Laura"
    ]

    first_names_neutral = [
        "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn"
    ]

    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
        "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
        "Clark", "Lewis", "Robinson", "Walker", "Hall", "Allen", "Young", "King",
        "Wright", "Scott", "Green", "Baker", "Adams", "Nelson", "Hill", "Carter",
        "Mitchell", "Roberts", "Turner", "Phillips", "Campbell", "Parker", "Evans"
    ]

    if gender == "male":
        first = rng.choice(first_names_male)
    elif gender == "female":
        first = rng.choice(first_names_female)
    else:
        first = rng.choice(first_names_neutral)

    last = rng.choice(last_names)

    return f"{first} {last}"


def generate_personas(n_personas: int = 500, seed: int = RANDOM_SEED) -> List[CognitiveProfile]:
    """
    Generate N diverse personas using stratified sampling

    Uses fixed random seed for reproducibility.
    Ensures good coverage across:
    - Demographics (age, gender, education)
    - Personality dimensions
    - Cognitive abilities
    - Expertise domains

    Args:
        n_personas: Number of personas to generate (default 500)
        seed: Random seed for reproducibility (default RANDOM_SEED)

    Returns:
        List of CognitiveProfile objects
    """

    # Create reproducible random generator
    rng = np.random.default_rng(seed)

    personas = []

    print(f"Generating {n_personas} personas with seed={seed}...")

    for i in range(n_personas):
        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1}/{n_personas} personas...")

        # Demographics - stratified sampling
        age = int(rng.integers(25, 71))  # 25-70
        gender = rng.choice(["male", "female", "non-binary"], p=[0.48, 0.48, 0.04])

        # Education - realistic distribution
        education = rng.choice(
            ["high_school", "bachelors", "masters", "phd"],
            p=[0.05, 0.30, 0.40, 0.25]
        )

        occupation = sample_occupation(education, rng)
        name = generate_persona_name(i, gender, rng)

        # Big Five - normal distributions centered at 50
        big_five = {
            "openness": int(np.clip(rng.normal(50, 20), 0, 100)),
            "conscientiousness": int(np.clip(rng.normal(50, 20), 0, 100)),
            "extraversion": int(np.clip(rng.normal(50, 20), 0, 100)),
            "agreeableness": int(np.clip(rng.normal(50, 20), 0, 100)),
            "neuroticism": int(np.clip(rng.normal(50, 20), 0, 100))
        }

        # Domain expertise - correlated with education/occupation
        expertise = sample_expertise_correlated(education, occupation, rng)

        # Cognitive measures - realistic distributions

        # General intelligence: normal(70, 15) - slightly above average for analyst population
        general_intelligence = int(np.clip(rng.normal(70, 15), 0, 100))

        # Bayesian updating: correlated with intelligence and education
        bayesian_base = 50 + (general_intelligence - 70) * 0.3
        bayesian_updating_skill = int(np.clip(rng.normal(bayesian_base, 15), 0, 100))

        # Coherence: correlated with conscientiousness and intelligence
        coherence_base = 50 + (big_five["conscientiousness"] - 50) * 0.3 + (general_intelligence - 70) * 0.2
        coherence_forecasting = int(np.clip(rng.normal(coherence_base, 15), 0, 100))

        # CRT: discrete (0-7), correlated with intelligence
        crt_mean = 2.0 + (general_intelligence - 50) / 15  # Higher IQ → higher CRT
        cognitive_reflection_test = int(np.clip(rng.normal(crt_mean, 1.5), 0, 7))

        # Denominator neglect: inversely correlated with statistical expertise
        dn_base = 50 - (expertise["statistical_expertise"] - 50) * 0.4
        denominator_neglect = int(np.clip(rng.normal(dn_base, 20), 0, 100))

        # Decision rule competence: correlated with intelligence and CRT
        drc_base = 50 + (general_intelligence - 70) * 0.3 + cognitive_reflection_test * 3
        decision_rule_competence = int(np.clip(rng.normal(drc_base, 15), 0, 100))

        # Preferences
        risk_tolerance = int(np.clip(rng.normal(50, 25), 0, 100))
        political_leaning = int(np.clip(rng.normal(50, 25), 0, 100))

        # Cognitive style - categorical based on traits
        if expertise["statistical_expertise"] > 60 and general_intelligence > 65:
            thinking_style = "analytical"
        elif big_five["openness"] > 70:
            thinking_style = "intuitive"
        else:
            thinking_style = rng.choice(["analytical", "intuitive", "mixed"])

        if big_five["conscientiousness"] > 65:
            information_processing = "systematic"
        elif cognitive_reflection_test < 3:
            information_processing = "heuristic"
        else:
            information_processing = rng.choice(["systematic", "heuristic", "adaptive"])

        # Create persona
        persona = CognitiveProfile(
            persona_id=f"persona_{i:04d}",
            name=name,
            age=age,
            gender=gender,
            education=education,
            occupation=occupation,
            **big_five,
            **expertise,
            general_intelligence=general_intelligence,
            bayesian_updating_skill=bayesian_updating_skill,
            coherence_forecasting=coherence_forecasting,
            cognitive_reflection_test=cognitive_reflection_test,
            denominator_neglect=denominator_neglect,
            decision_rule_competence=decision_rule_competence,
            risk_tolerance=risk_tolerance,
            political_leaning=political_leaning,
            thinking_style=thinking_style,
            information_processing=information_processing
        )

        personas.append(persona)

    print(f"[OK] Generated {len(personas)} personas")
    return personas


def save_personas(personas: List[CognitiveProfile], output_path: str = None) -> str:
    """
    Save personas to JSON file with generation metadata

    Args:
        personas: List of CognitiveProfile objects
        output_path: Path to save JSON file (default: forecasting/persona_profiles.json)

    Returns:
        Path where file was saved
    """

    if output_path is None:
        output_path = Path(__file__).parent / "persona_profiles.json"
    else:
        output_path = Path(output_path)

    # Convert personas to dictionaries
    personas_data = [p.to_dict() for p in personas]

    # Create output with metadata
    output = {
        "metadata": GENERATION_CONFIG,
        "personas": personas_data
    }

    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(personas)} personas to: {output_path}")
    return str(output_path)


def load_personas(input_path: str = None) -> List[CognitiveProfile]:
    """
    Load personas from JSON file

    Args:
        input_path: Path to JSON file (default: forecasting/persona_profiles.json)

    Returns:
        List of CognitiveProfile objects
    """

    if input_path is None:
        input_path = Path(__file__).parent / "persona_profiles.json"
    else:
        input_path = Path(input_path)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    personas = [CognitiveProfile(**p) for p in data["personas"]]

    print(f"[OK] Loaded {len(personas)} personas from: {input_path}")
    print(f"    Generated with seed={data['metadata']['random_seed']} on {data['metadata']['generation_date']}")

    return personas


if __name__ == "__main__":
    # Generate and save personas
    print("=" * 70)
    print("PERSONA GENERATOR - Reproducible Cognitive Profiles")
    print("=" * 70)
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Target personas: {GENERATION_CONFIG['n_personas']}")
    print()

    personas = generate_personas(n_personas=500, seed=RANDOM_SEED)

    # Save to file
    save_path = save_personas(personas)

    # Print summary statistics
    print()
    print("=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)

    # Education distribution
    education_counts = {}
    for p in personas:
        education_counts[p.education] = education_counts.get(p.education, 0) + 1
    print(f"Education: {education_counts}")

    # Gender distribution
    gender_counts = {}
    for p in personas:
        gender_counts[p.gender] = gender_counts.get(p.gender, 0) + 1
    print(f"Gender: {gender_counts}")

    # Age range
    ages = [p.age for p in personas]
    print(f"Age: mean={np.mean(ages):.1f}, std={np.std(ages):.1f}, range=[{min(ages)}, {max(ages)}]")

    # Intelligence distribution
    intelligence = [p.general_intelligence for p in personas]
    print(f"Intelligence: mean={np.mean(intelligence):.1f}, std={np.std(intelligence):.1f}")

    # CRT distribution
    crt = [p.cognitive_reflection_test for p in personas]
    print(f"CRT: mean={np.mean(crt):.2f}, std={np.std(crt):.2f}")

    print()
    print("=" * 70)
    print("EXAMPLE PERSONAS")
    print("=" * 70)

    # Show 3 example personas
    for i in [0, 250, 499]:
        print(f"\n{personas[i].persona_id}: {personas[i].name}")
        print("-" * 70)
        print(personas[i].to_natural_language())

    print()
    print("=" * 70)
    print("[OK] Persona generation complete!")
    print(f"[OK] File saved to: {save_path}")
    print("=" * 70)
