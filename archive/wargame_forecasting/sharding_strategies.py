"""
Information sharding strategies for collapse probability forecasting.

Implements two approaches:
1. Shard Everything: Shard all data sections (scenario + history + current period data)
2. Shard Initial Only: Shard initial scenario, keep history + current period data intact

Instructions/output format are NEVER sharded - always appended in full.
"""

from forecasting.information_sharding import split_into_sentences
import random as random_module


def shard_everything_strategy(
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    information_fraction: float,
    seed: int
) -> str:
    """
    Shard all data sections combined, then append full instructions.

    Args:
        initial_scenario: Initial backstory text (sharded)
        historical_summary: Historical context (sharded)
        current_period_data: Current state/events/actions (sharded)
        instructions: Forecasting task + output format (PROTECTED)
        information_fraction: Fraction to keep (0.0-1.0)
        seed: Random seed

    Returns:
        Sharded data + full instructions
    """
    if information_fraction >= 1.0:
        parts = [initial_scenario]
        if historical_summary:
            parts.append(historical_summary)
        parts.append(current_period_data)
        parts.append(instructions)
        return "\n".join(parts)

    # Combine all DATA sections (not instructions)
    data_parts = [initial_scenario]
    if historical_summary:
        data_parts.append(historical_summary)
    data_parts.append(current_period_data)
    full_data = "\n".join(data_parts)

    # Thread-safe random instance
    rng = random_module.Random(seed)
    sentences = split_into_sentences(full_data)

    if not sentences:
        return full_data + "\n" + instructions

    # Sample sentences
    n_keep = max(1, int(len(sentences) * information_fraction))
    indices = sorted(rng.sample(range(len(sentences)), n_keep))
    sampled_sentences = [sentences[i] for i in indices]

    # Sharded data + FULL instructions (always protected)
    return '\n'.join(sampled_sentences) + "\n" + instructions


def shard_initial_only_strategy(
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    information_fraction: float,
    seed: int
) -> str:
    """
    Shard only the initial scenario, keep everything else intact.

    Args:
        initial_scenario: Initial backstory text (SHARDED)
        historical_summary: Historical context (FULL)
        current_period_data: Current state/events/actions (FULL)
        instructions: Forecasting task + output format (PROTECTED)
        information_fraction: Fraction of INITIAL SCENARIO to keep
        seed: Random seed

    Returns:
        Sharded initial + full history + full current data + full instructions
    """
    if information_fraction >= 1.0:
        parts = [initial_scenario]
        if historical_summary:
            parts.append(historical_summary)
        parts.append(current_period_data)
        parts.append(instructions)
        return "\n".join(parts)

    # Thread-safe random instance
    rng = random_module.Random(seed)
    sentences = split_into_sentences(initial_scenario)

    if not sentences:
        sharded_initial = initial_scenario
    else:
        n_keep = max(1, int(len(sentences) * information_fraction))
        indices = sorted(rng.sample(range(len(sentences)), n_keep))
        sampled_sentences = [sentences[i] for i in indices]
        sharded_initial = '\n'.join(sampled_sentences)

    # Combine sharded initial + full everything else
    parts = [sharded_initial]
    if historical_summary:
        parts.append(historical_summary)
    parts.append(current_period_data)
    parts.append(instructions)
    return "\n".join(parts)


def apply_sharding_strategy(
    strategy: str,
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    information_fraction: float,
    seed: int
) -> str:
    """
    Apply the specified sharding strategy.

    Instructions are NEVER sharded regardless of strategy.

    Args:
        strategy: "none", "shard_everything", or "shard_initial_only"
        initial_scenario: Initial backstory
        historical_summary: Historical context
        current_period_data: Current state/events/actions
        instructions: Forecasting task + output format
        information_fraction: Fraction to keep
        seed: Random seed

    Returns:
        Prompt with sharded data + full instructions
    """
    if strategy == "none" or information_fraction >= 1.0:
        # Baseline - no sharding, full everything
        parts = [initial_scenario]
        if historical_summary:
            parts.append(historical_summary)
        parts.append(current_period_data)
        parts.append(instructions)
        return "\n".join(parts)

    elif strategy == "shard_everything":
        return shard_everything_strategy(
            initial_scenario, historical_summary, current_period_data,
            instructions, information_fraction, seed
        )

    elif strategy == "shard_initial_only":
        return shard_initial_only_strategy(
            initial_scenario, historical_summary, current_period_data,
            instructions, information_fraction, seed
        )

    else:
        raise ValueError(f"Unknown sharding strategy: {strategy}")


if __name__ == "__main__":
    print("Testing sharding strategies...")

    # Test data
    initial = "This is the initial scenario. It has multiple sentences. Each one provides context."
    history = "Period 1: Some actions happened. Period 2: More actions happened."
    current = "Period 3: Current state is X. Events are Y. Actions are Z."
    instruct = "YOUR TASK: Predict collapse probability.\nOUTPUT FORMAT: {\"probability\": 0.XX}"

    print(f"\nOriginal lengths:")
    print(f"  Initial: {len(initial)} chars")
    print(f"  History: {len(history)} chars")
    print(f"  Current: {len(current)} chars")
    print(f"  Instructions: {len(instruct)} chars")
    total = len(initial + history + current + instruct)
    print(f"  Total: {total} chars")

    # Test baseline
    baseline = apply_sharding_strategy("none", initial, history, current, instruct, 0.5, 42)
    print(f"\nBaseline: {len(baseline)} chars")
    assert instruct in baseline, "Instructions missing from baseline!"

    # Test shard everything at 50%
    shard_all = apply_sharding_strategy("shard_everything", initial, history, current, instruct, 0.5, 42)
    print(f"Shard Everything (50%): {len(shard_all)} chars")
    assert instruct in shard_all, "Instructions missing from shard_everything!"

    # Test shard initial only at 50%
    shard_init = apply_sharding_strategy("shard_initial_only", initial, history, current, instruct, 0.5, 42)
    print(f"Shard Initial Only (50%): {len(shard_init)} chars")
    assert instruct in shard_init, "Instructions missing from shard_initial_only!"

    # Test thread safety - multiple seeds shouldn't interfere
    results = []
    for seed in range(10):
        r = apply_sharding_strategy("shard_everything", initial, history, current, instruct, 0.5, seed)
        results.append(r)

    # Same seed should produce same result
    r1 = apply_sharding_strategy("shard_everything", initial, history, current, instruct, 0.5, 42)
    r2 = apply_sharding_strategy("shard_everything", initial, history, current, instruct, 0.5, 42)
    assert r1 == r2, "Same seed produced different results!"

    print("\n[OK] Sharding strategies working correctly!")
    print("[OK] Instructions always protected!")
    print("[OK] Thread-safe random!")
