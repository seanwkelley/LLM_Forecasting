"""
Conflict Engine Tests -- Verify determinism, escalation computation,
and state updates.

Usage:
    python conflict/test_engine.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from conflict.engine import (
    Action, ConflictState, FactionState, ACTION_SPACE,
    compute_escalation, update_faction_states, run_period,
    initialize_state, aggregate_faction_action, closest_action,
)
from conflict.shocks import generate_scenario_configs, generate_shock_sequence
from conflict.agents_config import create_agents


def test_action_from_name():
    """Test Action.from_name creates valid actions."""
    action = Action.from_name("novaris", "military_buildup")
    assert action.faction_id == "novaris"
    assert action.action_name == "military_buildup"
    assert action.escalation_delta == 0.4
    assert action.cost == 1.0
    assert action.category == "military"

    # Invalid name falls back to intelligence_gathering
    action = Action.from_name("tethys", "invalid_action")
    assert action.action_name == "intelligence_gathering"
    print("  [OK] test_action_from_name")


def test_compute_escalation_mutual_escalation():
    """Mutual escalation should amplify (interaction=1.2)."""
    state = ConflictState(
        factions={
            "novaris": FactionState(faction_id="novaris"),
            "tethys": FactionState(faction_id="tethys"),
        },
        escalation_index=5.0,
    )

    nov = Action.from_name("novaris", "military_buildup")    # delta=0.4
    teth = Action.from_name("tethys", "military_buildup")    # delta=0.4

    new_ei = compute_escalation(state, nov, teth)
    # Expected: 5.0 + (0.4 + 0.4) * 1.2 + (-0.05 * 0) = 5.0 + 0.96 = 5.96
    expected = 5.0 + 0.8 * 1.2 + 0.0
    assert abs(new_ei - expected) < 0.01, f"Expected {expected}, got {new_ei}"
    print("  [OK] test_compute_escalation_mutual_escalation")


def test_compute_escalation_mutual_deescalation():
    """Mutual de-escalation should amplify (interaction=1.3)."""
    state = ConflictState(
        factions={
            "novaris": FactionState(faction_id="novaris"),
            "tethys": FactionState(faction_id="tethys"),
        },
        escalation_index=5.0,
    )

    nov = Action.from_name("novaris", "peace_talks")       # delta=-0.8
    teth = Action.from_name("tethys", "ceasefire_offer")   # delta=-0.6

    new_ei = compute_escalation(state, nov, teth)
    # Expected: 5.0 + (-0.8 + -0.6) * 1.3 + 0 = 5.0 - 1.82 = 3.18
    expected = 5.0 + (-1.4) * 1.3
    assert abs(new_ei - expected) < 0.01, f"Expected {expected}, got {new_ei}"
    print("  [OK] test_compute_escalation_mutual_deescalation")


def test_compute_escalation_asymmetric():
    """Asymmetric actions should dampen (interaction=0.8)."""
    state = ConflictState(
        factions={
            "novaris": FactionState(faction_id="novaris"),
            "tethys": FactionState(faction_id="tethys"),
        },
        escalation_index=5.0,
    )

    nov = Action.from_name("novaris", "limited_strike")    # delta=1.5
    teth = Action.from_name("tethys", "peace_talks")       # delta=-0.8

    new_ei = compute_escalation(state, nov, teth)
    # Expected: 5.0 + (1.5 + -0.8) * 0.8 + 0 = 5.0 + 0.56 = 5.56
    expected = 5.0 + 0.7 * 0.8
    assert abs(new_ei - expected) < 0.01, f"Expected {expected}, got {new_ei}"
    print("  [OK] test_compute_escalation_asymmetric")


def test_mean_reversion():
    """EI should mean-revert toward 5.0 at extremes."""
    # High EI
    state_high = ConflictState(
        factions={
            "novaris": FactionState(faction_id="novaris"),
            "tethys": FactionState(faction_id="tethys"),
        },
        escalation_index=9.0,
    )
    # Same actions, but high EI should produce lower result due to momentum
    nov = Action.from_name("novaris", "intelligence_gathering")  # delta=0.1
    teth = Action.from_name("tethys", "intelligence_gathering")  # delta=0.1
    ei_high = compute_escalation(state_high, nov, teth)

    # Low EI
    state_low = ConflictState(
        factions={
            "novaris": FactionState(faction_id="novaris"),
            "tethys": FactionState(faction_id="tethys"),
        },
        escalation_index=1.0,
    )
    ei_low = compute_escalation(state_low, nov, teth)

    # Mean reversion: starting from 9.0 should push down, from 1.0 should push up
    # So with same neutral actions, the change from 9.0 should be less positive
    # (or more negative) than the change from 1.0
    change_high = ei_high - 9.0
    change_low = ei_low - 1.0
    assert change_low > change_high, \
        f"Mean reversion not working: change from 1.0={change_low:.3f}, from 9.0={change_high:.3f}"
    print(f"  [OK] test_mean_reversion (from 9.0: {ei_high:.2f}, from 1.0: {ei_low:.2f})")


def test_ei_clamping():
    """EI should stay within [0, 10]."""
    # Try to go below 0
    state = ConflictState(
        factions={
            "novaris": FactionState(faction_id="novaris"),
            "tethys": FactionState(faction_id="tethys"),
        },
        escalation_index=0.5,
    )
    nov = Action.from_name("novaris", "troop_withdrawal")   # delta=-1.0
    teth = Action.from_name("tethys", "peace_talks")        # delta=-0.8
    ei = compute_escalation(state, nov, teth)
    assert ei >= 0.0, f"EI below 0: {ei}"

    # Try to go above 10
    state.escalation_index = 9.5
    nov = Action.from_name("novaris", "full_scale_attack")   # delta=2.5
    teth = Action.from_name("tethys", "border_incursion")    # delta=1.2
    ei = compute_escalation(state, nov, teth)
    assert ei <= 10.0, f"EI above 10: {ei}"
    print("  [OK] test_ei_clamping")


def test_determinism():
    """Same inputs should produce identical outputs."""
    config = generate_scenario_configs(1, n_periods=10, seed=42)[0]
    state1 = initialize_state(config)
    state2 = initialize_state(config)

    actions = [
        ("military_buildup", "intelligence_gathering"),
        ("limited_strike", "military_buildup"),
        ("peace_talks", "peace_talks"),
        ("cyber_attack", "humanitarian_aid"),
        ("economic_sanctions", "trade_agreement"),
    ]

    for nov_name, teth_name in actions:
        nov = Action.from_name("novaris", nov_name)
        teth = Action.from_name("tethys", teth_name)
        run_period(state1, nov, teth)

        nov2 = Action.from_name("novaris", nov_name)
        teth2 = Action.from_name("tethys", teth_name)
        run_period(state2, nov2, teth2)

    assert state1.escalation_history == state2.escalation_history, "Non-deterministic!"
    assert state1.military_balance == state2.military_balance, "Non-deterministic military balance!"
    print("  [OK] test_determinism")


def test_resource_depletion():
    """Expensive actions should deplete resources."""
    state = ConflictState(
        factions={
            "novaris": FactionState(faction_id="novaris", resources=6.0),
            "tethys": FactionState(faction_id="tethys", resources=6.0),
        },
        escalation_index=5.0,
    )

    # full_scale_attack costs 5.0
    nov = Action.from_name("novaris", "full_scale_attack")
    teth = Action.from_name("tethys", "intelligence_gathering")  # costs 0.3
    run_period(state, nov, teth)

    # Novaris should have much less resources (6 - 5 + regen)
    assert state.factions["novaris"].resources < 3.0, \
        f"Resources too high after expensive action: {state.factions['novaris'].resources}"
    print(f"  [OK] test_resource_depletion (novaris resources: {state.factions['novaris'].resources:.1f})")


def test_closest_action():
    """closest_action should find the nearest action by delta."""
    action = closest_action(0.0)
    assert action.action_name in ("intelligence_gathering", "backchannel_talks"), f"Got {action.action_name}"

    action = closest_action(-0.7)
    assert action.action_name in ("peace_talks", "ceasefire_offer"), f"Got {action.action_name}"

    action = closest_action(2.0)
    assert action.action_name in ("limited_strike", "full_scale_attack"), f"Got {action.action_name}"
    print("  [OK] test_closest_action")


def test_aggregate_faction_action():
    """Aggregation should weight by role relevance."""
    recs = [
        {"agent_id": "krasnov", "agent_role": "military_chief",
         "action": "full_scale_attack", "reasoning": "Attack now"},
        {"agent_id": "petrova", "agent_role": "economic_advisor",
         "action": "peace_talks", "reasoning": "Economy can't sustain war"},
        {"agent_id": "volkov", "agent_role": "defense_minister",
         "action": "military_buildup", "reasoning": "Prepare first"},
        {"agent_id": "morozov", "agent_role": "intelligence_chief",
         "action": "cyber_attack", "reasoning": "Probe their defenses"},
    ]

    action = aggregate_faction_action(recs, "novaris")
    assert action.action_name in ACTION_SPACE, f"Invalid action: {action.action_name}"
    # With 4 agents pulling in different directions, expect moderate result
    print(f"  [OK] test_aggregate_faction_action (result: {action.action_name})")


def test_full_simulation_baseline():
    """Run a short baseline simulation to verify no crashes."""
    from conflict.run_conflict_sim import run_baseline_simulation

    config = generate_scenario_configs(1, n_periods=10, seed=42)[0]
    result = run_baseline_simulation(config, verbose=False)

    assert len(result["escalation_history"]) == 10
    assert result["summary"]["std_ei"] >= 0
    assert not result["errors"] or all("stuck" not in e for e in result["errors"])

    ei = result["escalation_history"]
    print(f"  [OK] test_full_simulation_baseline "
          f"(EI: {min(ei):.2f} - {max(ei):.2f}, "
          f"mean={sum(ei)/len(ei):.2f})")


def test_scenario_configs():
    """Verify scenario config generation."""
    configs = generate_scenario_configs(5, n_periods=30, seed=42)
    assert len(configs) == 5

    # Check variation in starting conditions
    escalations = [c["starting_escalation"] for c in configs]
    assert max(escalations) > min(escalations), "No variation in starting escalation"

    # Check shock sequences exist
    for c in configs:
        assert isinstance(c["shocks"], list)

    print("  [OK] test_scenario_configs")


def test_agents_config():
    """Verify agent configuration."""
    config = generate_scenario_configs(1, seed=42)[0]
    agents, faction_agents = create_agents(config)

    assert len(agents) == 7, f"Expected 7 agents, got {len(agents)}"
    assert len(faction_agents["novaris"]) == 4, f"Expected 4 novaris agents"
    assert len(faction_agents["tethys"]) == 3, f"Expected 3 tethys agents"

    # Check all agents have required fields
    for agent in agents:
        assert "agent_id" in agent
        assert "faction" in agent
        assert "role" in agent
        assert "hawk_dove" in agent
        assert 0 <= agent["hawk_dove"] <= 1

    print("  [OK] test_agents_config")


def main():
    print("=" * 50)
    print("CONFLICT ENGINE TESTS")
    print("=" * 50)

    tests = [
        test_action_from_name,
        test_compute_escalation_mutual_escalation,
        test_compute_escalation_mutual_deescalation,
        test_compute_escalation_asymmetric,
        test_mean_reversion,
        test_ei_clamping,
        test_determinism,
        test_resource_depletion,
        test_closest_action,
        test_aggregate_faction_action,
        test_full_simulation_baseline,
        test_scenario_configs,
        test_agents_config,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
