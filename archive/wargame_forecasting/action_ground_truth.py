"""
Extract ground truth action sets from simulation outputs.

Reads period_XX_actions.csv files and extracts approved actions per faction.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple


def extract_period_actions(period: int,
                           interactions_dir: str = "D:/Northeastern/LLM_Forecasting/outputs/interactions") -> Dict:
    """
    Extract all approved actions for a single period.

    Args:
        period: Period number (1-10)
        interactions_dir: Directory containing period CSVs

    Returns:
        {
            'major_power': {
                'actions': ['military_buildup', 'precision_strike', ...],
                'by_domain': {'military': [...], 'intelligence': [...], ...},
                'priorities': ['primary', 'secondary', ...],
                'successes': [False, True, ...],
                'n_actions': 6
            },
            'small_power': {...}
        }
    """
    csv_path = Path(interactions_dir) / f"period_{period:02d}_actions.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Actions CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    result = {}

    for faction in ['major_power', 'small_power']:
        # Filter to approved OR counter-proposed actions (both are final actions taken)
        faction_data = df[
            (df['faction'] == faction) &
            (df['approval_status'].isin(['approved', 'counter_proposed']))
        ].copy()

        # Extract fields
        actions = faction_data['final_action'].tolist()
        domains = faction_data['domain'].tolist()
        priorities = faction_data['priority'].tolist()
        successes = faction_data['success'].tolist()

        # Group by domain
        by_domain = {}
        for action, domain in zip(actions, domains):
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(action)

        result[faction] = {
            'actions': actions,
            'by_domain': by_domain,
            'priorities': priorities,
            'successes': successes,
            'n_actions': len(actions),
            'success_rate': sum(successes) / len(successes) if successes else 0.0
        }

    return result


def extract_all_periods(interactions_dir: str = "D:/Northeastern/LLM_Forecasting/outputs/interactions",
                        n_periods: int = 10) -> Dict:
    """
    Extract approved actions for all periods.

    Returns:
        {
            1: {'major_power': {...}, 'small_power': {...}},
            2: {...},
            ...
        }
    """
    all_periods = {}

    for period in range(1, n_periods + 1):
        try:
            all_periods[period] = extract_period_actions(period, interactions_dir)
        except FileNotFoundError as e:
            print(f"[WARNING] {e}")
            continue

    return all_periods


def save_ground_truth(ground_truth: Dict,
                      output_path: str = "D:/Northeastern/LLM_Forecasting/forecasting/ground_truth_actions.json"):
    """Save ground truth to JSON file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(ground_truth, f, indent=2)

    print(f"[OK] Ground truth saved to: {output_file}")
    return output_file


def load_ground_truth(input_path: str = "D:/Northeastern/LLM_Forecasting/forecasting/ground_truth_actions.json") -> Dict:
    """Load ground truth from JSON file."""
    with open(input_path, 'r') as f:
        data = json.load(f)

    # Convert string keys back to integers
    return {int(k): v for k, v in data.items()}


def print_ground_truth_summary(ground_truth: Dict):
    """Print summary statistics of ground truth actions."""
    print("\n" + "="*80)
    print("GROUND TRUTH ACTION SET SUMMARY")
    print("="*80)

    total_novaris = 0
    total_tethys = 0

    print(f"\n{'Period':<8} {'Novaris Actions':<20} {'Tethys Actions':<20}")
    print("-"*80)

    for period in sorted(ground_truth.keys()):
        data = ground_truth[period]
        n_novaris = data['major_power']['n_actions']
        n_tethys = data['small_power']['n_actions']

        total_novaris += n_novaris
        total_tethys += n_tethys

        novaris_domains = ', '.join(f"{d}:{len(a)}" for d, a in data['major_power']['by_domain'].items())
        tethys_domains = ', '.join(f"{d}:{len(a)}" for d, a in data['small_power']['by_domain'].items())

        print(f"{period:<8} {n_novaris} ({novaris_domains[:18]})  {n_tethys} ({tethys_domains[:18]})")

    print("-"*80)
    print(f"{'TOTAL':<8} {total_novaris:<20} {total_tethys:<20}")
    print(f"{'MEAN':<8} {total_novaris/len(ground_truth):<20.1f} {total_tethys/len(ground_truth):<20.1f}")

    # Domain breakdown
    print(f"\n{'='*80}")
    print("DOMAIN BREAKDOWN")
    print("="*80)

    domain_counts = {'military': 0, 'intelligence': 0, 'economic': 0, 'diplomatic': 0}

    for period_data in ground_truth.values():
        for faction_data in [period_data['major_power'], period_data['small_power']]:
            for domain, actions in faction_data['by_domain'].items():
                domain_counts[domain] += len(actions)

    print(f"\n{'Domain':<15} {'Count':<10} {'%':<10}")
    print("-"*40)
    total_actions = sum(domain_counts.values())
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        pct = count / total_actions * 100 if total_actions > 0 else 0
        print(f"{domain:<15} {count:<10} {pct:<10.1f}%")

    print("="*80)


def get_faction_display_name(faction: str) -> str:
    """Convert faction code to display name."""
    mapping = {
        'major_power': 'Novaris',
        'small_power': 'Tethys',
        'meridian': 'Meridian',
        'valkoria': 'Valkoria',
        'aurelia': 'Aurelia',
        'international_org': 'International Org'
    }
    return mapping.get(faction, faction)


if __name__ == "__main__":
    print("Extracting ground truth from simulation outputs...")

    # Extract all periods
    ground_truth = extract_all_periods()

    # Print summary
    print_ground_truth_summary(ground_truth)

    # Save to file
    output_path = save_ground_truth(ground_truth)

    print(f"\n[OK] Ground truth extraction complete!")
    print(f"     Extracted {len(ground_truth)} periods")
    print(f"     Saved to: {output_path}")
