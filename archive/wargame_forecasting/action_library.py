"""
Action library for the geopolitical simulation.

Contains all 68 actions available in the simulation (from action_execution.R),
organized by domain. Also supports frequency analysis from simulation outputs.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import Counter


def get_full_action_space() -> Dict[str, List[str]]:
    """
    Return the complete action space from the simulation (action_execution.R).

    This is the authoritative list of all 68 actions the simulation can execute,
    organized by the 7 domains defined in the R code.
    """
    return {
        'diplomatic': [
            'diplomatic_visit', 'peace_talks', 'trade_negotiation',
            'cultural_exchange', 'humanitarian_aid', 'mediation_offer',
            'coalition_building', 'backchannel_negotiations', 'formal_peace_talks',
            'prisoner_exchange', 'humanitarian_corridors', 'public_diplomatic_initiative',
            'formal_multilateral_engagement', 'international_observers'
        ],
        'intelligence': [
            'intelligence_gathering', 'surveillance_operation', 'counterintelligence',
            'spread_disinformation', 'propaganda_campaign', 'share_intelligence',
            'enhanced_intelligence_gathering', 'enhanced_surveillance', 'information_campaign'
        ],
        'economic': [
            'trade_agreement', 'economic_sanctions', 'financial_aid',
            'resource_embargo', 'currency_manipulation', 'cyber_theft',
            'trade_restrictions', 'targeted_sanctions', 'asset_seizure',
            'strategic_stockpiling', 'war_bonds'
        ],
        'military_posture': [
            'military_buildup', 'naval_deployment', 'air_patrols',
            'troop_movements', 'joint_exercises', 'arms_development',
            'defensive_fortification', 'defensive_reinforcements',
            'show_of_force', 'military_exercises', 'enhanced_patrols',
            'naval_patrols', 'naval_demonstration', 'reconnaissance'
        ],
        'covert_operations': [
            'sabotage', 'assassination_attempt', 'regime_destabilization',
            'proxy_support', 'false_flag_operation', 'cyber_attack',
            'leadership_targeting', 'political_warfare', 'cyber_defense'
        ],
        'open_conflict': [
            'border_incursion', 'limited_strike', 'precision_strike',
            'full_scale_attack', 'occupation', 'blockade', 'siege_warfare'
        ],
        'wmd': [
            'nuclear_development', 'chemical_weapons', 'biological_program',
            'tactical_nuclear_use', 'strategic_nuclear_strike'
        ]
    }


def get_all_valid_actions() -> Set[str]:
    """Return flat set of all valid action names."""
    actions = set()
    for domain_actions in get_full_action_space().values():
        actions.update(domain_actions)
    return actions


def get_action_domain_mapping() -> Dict[str, str]:
    """Return mapping of action_name -> domain for all 68 actions."""
    mapping = {}
    for domain, actions in get_full_action_space().items():
        for action in actions:
            mapping[action] = domain
    return mapping


def analyze_action_frequencies(interactions_dir: str = "D:/Northeastern/LLM_Forecasting/outputs/interactions",
                               n_periods: int = 10) -> pd.DataFrame:
    """
    Analyze action frequencies across all periods.

    Returns DataFrame with columns:
    - action: Action name
    - domain: Domain (military, intelligence, economic, diplomatic)
    - proposed_count: Times proposed (includes vetoed)
    - approved_count: Times approved
    - success_count: Times succeeded
    - approval_rate: approved / proposed
    - success_rate: succeeded / approved
    """
    all_actions = []

    for period in range(1, n_periods + 1):
        csv_path = Path(interactions_dir) / f"period_{period:02d}_actions.csv"

        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)
        all_actions.append(df)

    if not all_actions:
        raise ValueError("No action CSVs found")

    combined = pd.concat(all_actions, ignore_index=True)

    # Group by action and domain
    action_stats = []

    for action in combined['proposed_action'].unique():
        action_data = combined[combined['proposed_action'] == action]

        domain = action_data['domain'].mode()[0] if len(action_data) > 0 else 'unknown'
        proposed_count = len(action_data)
        approved_count = len(action_data[action_data['approval_status'] == 'approved'])
        success_count = len(action_data[action_data['success'] == True])

        approval_rate = approved_count / proposed_count if proposed_count > 0 else 0
        success_rate = success_count / approved_count if approved_count > 0 else 0

        action_stats.append({
            'action': action,
            'domain': domain,
            'proposed_count': proposed_count,
            'approved_count': approved_count,
            'success_count': success_count,
            'approval_rate': approval_rate,
            'success_rate': success_rate
        })

    return pd.DataFrame(action_stats).sort_values('proposed_count', ascending=False)


def create_plausible_actions_by_domain(action_frequencies: pd.DataFrame,
                                       min_proposed: int = 2,
                                       max_per_domain: int = 15) -> Dict[str, List[str]]:
    """
    Create plausible action sets per domain.

    Args:
        action_frequencies: DataFrame from analyze_action_frequencies()
        min_proposed: Minimum times action must be proposed to be included
        max_per_domain: Maximum actions per domain

    Returns:
        {
            'military': ['military_buildup', 'offensive_operation', ...],
            'intelligence': [...],
            'economic': [...],
            'diplomatic': [...]
        }
    """
    plausible = {}

    for domain in ['military', 'intelligence', 'economic', 'diplomatic', 'covert_ops']:
        domain_actions = action_frequencies[
            (action_frequencies['domain'] == domain) &
            (action_frequencies['proposed_count'] >= min_proposed)
        ].head(max_per_domain)

        plausible[domain] = domain_actions['action'].tolist()

    return plausible


def create_action_descriptions() -> Dict[str, str]:
    """
    Descriptions for all 68 actions in the simulation.

    Derived from action_execution.R effect descriptions and
    multi_action_system.R action category guidance.
    """
    descriptions = {
        # DIPLOMATIC (14)
        'diplomatic_visit': 'Formal diplomatic meeting to improve relations',
        'peace_talks': 'Formal negotiations to end conflict',
        'trade_negotiation': 'Seek economic partnerships and alternative trade routes',
        'cultural_exchange': 'Soft power initiatives to build people-to-people ties',
        'humanitarian_aid': 'Provide humanitarian assistance to affected populations',
        'mediation_offer': 'Third-party offer to broker peace between warring parties',
        'coalition_building': 'Build alliances and partnerships with other states',
        'backchannel_negotiations': 'Secret diplomatic dialogue outside official channels',
        'formal_peace_talks': 'High-level structured negotiations with framework agreements',
        'prisoner_exchange': 'Exchange captured personnel as humanitarian gesture',
        'humanitarian_corridors': 'Establish safe passage for civilians in conflict zones',
        'public_diplomatic_initiative': 'Public diplomacy campaign to shape international narrative',
        'formal_multilateral_engagement': 'Engage through international institutions for legitimacy',
        'international_observers': 'Deploy international monitors to conflict area',

        # INTELLIGENCE (9)
        'intelligence_gathering': 'Collect information on adversary capabilities and intentions',
        'surveillance_operation': 'Continuous monitoring of adversary activities',
        'counterintelligence': 'Protect against enemy intelligence operations',
        'spread_disinformation': 'Spread false narratives to confuse adversary',
        'propaganda_campaign': 'Information campaigns to shape domestic and international opinion',
        'share_intelligence': 'Provide intel to allies to coordinate strategy',
        'enhanced_intelligence_gathering': 'Intensive multi-source intelligence collection',
        'enhanced_surveillance': 'Comprehensive surveillance with expanded coverage',
        'information_campaign': 'Broader information warfare to influence target audiences',

        # ECONOMIC (11)
        'trade_agreement': 'Establish formal trade partnerships and economic cooperation',
        'economic_sanctions': 'Impose broad economic restrictions on adversary',
        'financial_aid': 'Provide financial support to allies or affected states',
        'resource_embargo': 'Target specific critical resources for restriction',
        'currency_manipulation': 'Financial warfare targeting adversary currency stability',
        'cyber_theft': 'Steal economic or technical secrets through cyber operations',
        'trade_restrictions': 'Impose trade barriers and export controls',
        'targeted_sanctions': 'Sanctions against specific individuals or entities',
        'asset_seizure': 'Freeze or seize foreign assets within jurisdiction',
        'strategic_stockpiling': 'Build reserves of critical supplies and materials',
        'war_bonds': 'Raise domestic financing for war effort through bond sales',

        # MILITARY POSTURE (14)
        'military_buildup': 'Concentrate forces and increase readiness along borders',
        'naval_deployment': 'Deploy naval forces to project power in region',
        'air_patrols': 'Establish air presence and patrol contested airspace',
        'troop_movements': 'Reposition ground forces to forward positions',
        'joint_exercises': 'Conduct military exercises with allied forces',
        'arms_development': 'Develop advanced weapons systems and military technology',
        'defensive_fortification': 'Fortify defensive positions and harden territory',
        'defensive_reinforcements': 'Send reinforcements to strengthen defensive lines',
        'show_of_force': 'Military demonstrations to signal resolve and capability',
        'military_exercises': 'Conduct military training exercises to improve readiness',
        'enhanced_patrols': 'Increase patrol frequency and coverage area',
        'naval_patrols': 'Maritime patrol operations for area security',
        'naval_demonstration': 'Naval demonstrations to project maritime power',
        'reconnaissance': 'Military reconnaissance to gather tactical intelligence',

        # COVERT OPERATIONS (9)
        'sabotage': 'Covertly damage adversary infrastructure or military assets',
        'assassination_attempt': 'Target key enemy leaders for elimination',
        'regime_destabilization': 'Secretly undermine adversary government stability',
        'proxy_support': 'Fund and train opposition groups or non-state actors',
        'false_flag_operation': 'Stage provocations to discredit opponent',
        'cyber_attack': 'Target digital infrastructure and critical systems',
        'leadership_targeting': 'Target enemy leadership for capture or compromise',
        'political_warfare': 'Undermine enemy cohesion through political influence',
        'cyber_defense': 'Strengthen own cyber defenses and harden systems',

        # OPEN CONFLICT (7)
        'border_incursion': 'Limited military incursion across border to seize territory',
        'limited_strike': 'Precision strike on specific military targets',
        'precision_strike': 'Targeted strike on high-value military assets',
        'full_scale_attack': 'Major military offensive to capture significant territory',
        'occupation': 'Occupy and hold captured territory with military forces',
        'blockade': 'Naval or economic blockade to restrict access and supplies',
        'siege_warfare': 'Siege of cities or fortified positions',

        # WMD (5)
        'nuclear_development': 'Develop nuclear weapons capability',
        'chemical_weapons': 'Develop or deploy chemical weapons',
        'biological_program': 'Biological weapons research and development',
        'tactical_nuclear_use': 'Deploy tactical nuclear weapons on battlefield',
        'strategic_nuclear_strike': 'Strategic nuclear exchange against population centers',
    }

    return descriptions


def format_plausible_actions_for_prompt(plausible_by_domain: Dict[str, List[str]],
                                        descriptions: Dict[str, str]) -> str:
    """
    Format plausible actions as text for LLM prompt.

    Returns:
        Formatted string with actions organized by domain.
    """
    output = []

    # Order matches simulation's action_execution.R domains
    domain_order = [
        'diplomatic', 'intelligence', 'economic', 'military_posture',
        'covert_operations', 'open_conflict', 'wmd'
    ]

    for domain in domain_order:
        if domain not in plausible_by_domain or not plausible_by_domain[domain]:
            continue

        display_name = domain.upper().replace('_', ' ')
        output.append(f"\n{display_name}:")

        for action in plausible_by_domain[domain]:
            desc = descriptions.get(action, "No description available")
            output.append(f"  - {action}: {desc}")

    return '\n'.join(output)


def save_plausible_actions(plausible_by_domain: Dict[str, List[str]],
                          descriptions: Dict[str, str],
                          output_path: str = "D:/Northeastern/LLM_Forecasting/forecasting/plausible_actions.json"):
    """Save plausible actions library to JSON."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        'by_domain': plausible_by_domain,
        'descriptions': descriptions,
        'metadata': {
            'total_actions': sum(len(actions) for actions in plausible_by_domain.values()),
            'n_domains': len(plausible_by_domain)
        }
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"[OK] Plausible actions library saved to: {output_file}")
    return output_file


def load_plausible_actions(input_path: str = "D:/Northeastern/LLM_Forecasting/forecasting/plausible_actions.json") -> Tuple[Dict, Dict]:
    """Load plausible actions library from JSON."""
    with open(input_path, 'r') as f:
        data = json.load(f)

    return data['by_domain'], data['descriptions']


def print_action_library_summary(plausible_by_domain: Dict[str, List[str]]):
    """Print summary of action library."""
    print("\n" + "="*80)
    print("ACTION LIBRARY SUMMARY")
    print("="*80)

    print(f"\n{'Domain':<25} {'Actions':<10}")
    print("-"*40)

    total_actions = 0

    for domain in ['diplomatic', 'intelligence', 'economic', 'military_posture',
                    'covert_operations', 'open_conflict', 'wmd']:
        if domain not in plausible_by_domain:
            continue

        actions = plausible_by_domain[domain]
        n_actions = len(actions)
        total_actions += n_actions

        print(f"{domain:<25} {n_actions:<10}")

    print("-"*40)
    print(f"{'TOTAL':<25} {total_actions:<10}")
    print("="*80)


if __name__ == "__main__":
    print("Building full action library from simulation action space...")

    # Use the complete action space from action_execution.R
    full_actions = get_full_action_space()
    descriptions = create_action_descriptions()

    # Print summary
    print_action_library_summary(full_actions)

    # Save library
    output_path = save_plausible_actions(full_actions, descriptions)

    # Print formatted output
    print("\n" + "="*80)
    print("FORMATTED OUTPUT FOR PROMPTS:")
    print("="*80)
    formatted = format_plausible_actions_for_prompt(full_actions, descriptions)
    print(formatted)

    print(f"\n[OK] Action library creation complete!")
    print(f"     Total actions: {sum(len(a) for a in full_actions.values())}")
    print(f"     Domains: {len(full_actions)}")
    print(f"     Saved to: {output_path}")
