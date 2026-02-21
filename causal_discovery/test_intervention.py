"""
Quick smoke test for the intervention interface.

Tests all three intervention types on both engines using rule-based agents.
No LLM calls required.

Usage:
    python causal_discovery/test_intervention.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.intervention import (
    Intervention, run_market_intervention, run_conflict_intervention,
    format_result_for_agent,
)


def test_market_interventions():
    """Test all three intervention types on the market engine."""
    from market.agents_config import create_agents
    from market.engine import MarketState, run_period
    from market.shocks import generate_shock_sequence, apply_shocks, generate_scenario_configs

    print("=" * 60)
    print("MARKET ENGINE INTERVENTION TESTS")
    print("=" * 60)

    # Set up a scenario
    configs = generate_scenario_configs(n_scenarios=1, n_periods=30, seed=42)
    config = configs[0]
    agents, base_params = create_agents(config)
    shocks = config["shocks"]

    state = MarketState(agents=agents)

    # Run 10 warm-up periods (rule-based)
    from causal_discovery.intervention import _market_rule_based_orders
    for t in range(10):
        apply_shocks(agents, shocks, t, base_params)
        orders = _market_rule_based_orders(agents, state)
        run_period(state, orders)

    print(f"\nWarm-up complete. Period={state.period}, "
          f"Last price=${state.price_history[-1]:.2f}")

    # --- Test 1: Action override ---
    print("\n--- Test 1: Action Override (force producer_A limit_price=50) ---")
    intervention = Intervention(
        type="action",
        target={"agent_id": "producer_A", "param": "limit_price", "value": 50.0},
        run_periods=3,
        description="Force producer_A to sell at $50",
    )
    result = run_market_intervention(
        state_snapshot=state,
        agents_snapshot=agents,
        base_params=base_params,
        shocks=shocks,
        start_period=state.period,
        intervention=intervention,
    )
    print(format_result_for_agent(result))

    # --- Test 2: Trait override ---
    print("\n--- Test 2: Trait Override (set producer_A production_cost=30) ---")
    intervention = Intervention(
        type="trait",
        target={"agent_id": "producer_A", "param": "production_cost", "value": 30.0},
        run_periods=3,
        description="Reduce producer_A production cost to $30",
    )
    result = run_market_intervention(
        state_snapshot=state,
        agents_snapshot=agents,
        base_params=base_params,
        shocks=shocks,
        start_period=state.period,
        intervention=intervention,
    )
    print(format_result_for_agent(result))

    # --- Test 3: Event override ---
    print("\n--- Test 3: Event Override (inject supply_disruption, magnitude=1.5) ---")
    intervention = Intervention(
        type="event",
        target={"shock_type": "supply_disruption", "magnitude": 1.5},
        run_periods=3,
        description="Force a supply disruption shock",
    )
    result = run_market_intervention(
        state_snapshot=state,
        agents_snapshot=agents,
        base_params=base_params,
        shocks=shocks,
        start_period=state.period,
        intervention=intervention,
    )
    print(format_result_for_agent(result))

    # --- Test 4: Role-level trait override ---
    print("\n--- Test 4: Role-Level Trait Override (set ALL producers production_cost=200) ---")
    intervention = Intervention(
        type="trait",
        target={"role": "producer", "param": "production_cost", "value": 200.0},
        run_periods=3,
        description="Set all producers production cost to $200",
    )
    result = run_market_intervention(
        state_snapshot=state,
        agents_snapshot=agents,
        base_params=base_params,
        shocks=shocks,
        start_period=state.period,
        intervention=intervention,
    )
    print(format_result_for_agent(result))

    # Verify the override actually modified all producers in the rollout
    # (check that intervention trajectory differs from baseline)
    baseline_prices = [p.get("clearing_price") for p in result.baseline_trajectory]
    int_prices = [p.get("clearing_price") for p in result.intervention_trajectory]
    price_diff = any(
        abs((b or 0) - (i or 0)) > 0.01
        for b, i in zip(baseline_prices, int_prices)
    )
    assert price_diff, "Role-level trait override had no effect on prices!"
    print("[OK] Role-level override produced detectable price change")

    # Verify original state wasn't mutated
    assert state.period == 10, f"State mutated! period={state.period}, expected 10"
    print("\n[OK] Original state not mutated")
    print("[OK] All market intervention tests passed")


def test_conflict_interventions():
    """Test all three intervention types on the conflict engine."""
    from conflict.engine import initialize_state, run_period, aggregate_faction_action
    from conflict.agents_config import create_agents
    from conflict.shocks import generate_shock_sequence, apply_shocks, generate_scenario_configs

    print("\n" + "=" * 60)
    print("CONFLICT ENGINE INTERVENTION TESTS")
    print("=" * 60)

    # Set up a scenario
    configs = generate_scenario_configs(n_scenarios=1, n_periods=30, seed=42)
    config = configs[0]
    agents_config, faction_agents = create_agents(config)
    shocks = config["shocks"]

    state = initialize_state(config)

    # Run 10 warm-up periods (rule-based)
    from causal_discovery.intervention import _conflict_rule_based_recommendations
    for t in range(10):
        apply_shocks(state, shocks, t)
        recs = _conflict_rule_based_recommendations(agents_config, state)
        novaris_recs = [r for r in recs if r["faction"] == "novaris"]
        tethys_recs = [r for r in recs if r["faction"] == "tethys"]
        nov_action = aggregate_faction_action(novaris_recs, "novaris")
        teth_action = aggregate_faction_action(tethys_recs, "tethys")
        run_period(state, nov_action, teth_action)

    print(f"\nWarm-up complete. Period={state.period}, "
          f"EI={state.escalation_index:.2f}")

    # --- Test 1: Action override ---
    print("\n--- Test 1: Action Override (force krasnov to play peace_talks) ---")
    intervention = Intervention(
        type="action",
        target={"agent_id": "krasnov", "value": "peace_talks"},
        run_periods=3,
        description="Force hawk krasnov to recommend peace_talks",
    )
    result = run_conflict_intervention(
        state_snapshot=state,
        agents_config=agents_config,
        faction_agents=faction_agents,
        shocks=shocks,
        start_period=state.period,
        intervention=intervention,
    )
    print(format_result_for_agent(result))

    # --- Test 2: Trait override ---
    print("\n--- Test 2: Trait Override (set krasnov hawk_dove=0.1) ---")
    intervention = Intervention(
        type="trait",
        target={"agent_id": "krasnov", "param": "hawk_dove", "value": 0.1},
        run_periods=3,
        description="Make krasnov very dovish",
    )
    result = run_conflict_intervention(
        state_snapshot=state,
        agents_config=agents_config,
        faction_agents=faction_agents,
        shocks=shocks,
        start_period=state.period,
        intervention=intervention,
    )
    print(format_result_for_agent(result))

    # --- Test 3: Event override ---
    print("\n--- Test 3: Event Override (inject border_incident, magnitude=1.2) ---")
    intervention = Intervention(
        type="event",
        target={"shock_type": "border_incident", "magnitude": 1.2},
        run_periods=3,
        description="Force a border incident",
    )
    result = run_conflict_intervention(
        state_snapshot=state,
        agents_config=agents_config,
        faction_agents=faction_agents,
        shocks=shocks,
        start_period=state.period,
        intervention=intervention,
    )
    print(format_result_for_agent(result))

    # --- Test 4: Faction-level trait override ---
    print("\n--- Test 4: Faction-Level Trait Override (set ALL novaris hawk_dove=0.1) ---")
    intervention = Intervention(
        type="trait",
        target={"faction": "novaris", "param": "hawk_dove", "value": 0.1},
        run_periods=3,
        description="Make all Novaris agents very dovish",
    )
    result = run_conflict_intervention(
        state_snapshot=state,
        agents_config=agents_config,
        faction_agents=faction_agents,
        shocks=shocks,
        start_period=state.period,
        intervention=intervention,
    )
    print(format_result_for_agent(result))

    # Verify the override actually affected escalation
    baseline_ei = [p.get("escalation_index") for p in result.baseline_trajectory]
    int_ei = [p.get("escalation_index") for p in result.intervention_trajectory]
    ei_diff = any(
        abs((b or 0) - (i or 0)) > 0.01
        for b, i in zip(baseline_ei, int_ei)
    )
    assert ei_diff, "Faction-level trait override had no effect on escalation!"
    print("[OK] Faction-level override produced detectable EI change")

    # Verify original state wasn't mutated
    assert state.period == 10, f"State mutated! period={state.period}, expected 10"
    print("\n[OK] Original state not mutated")
    print("[OK] All conflict intervention tests passed")


if __name__ == "__main__":
    test_market_interventions()
    test_conflict_interventions()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
