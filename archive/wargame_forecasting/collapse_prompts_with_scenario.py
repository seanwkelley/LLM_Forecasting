"""
Collapse probability forecasting prompts WITH initial scenario description.

Includes the rich backstory from period_01.txt that frames the conflict.
"""

from typing import Dict, List


# Initial scenario description extracted from outputs/human_forecasting/TRUE/period_01.txt
INITIAL_SCENARIO = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INITIAL SITUATION REPORT: THE TETHYS CRISIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**THE CRISIS**

The People's Federation of Novaris has mobilized approximately 40% of its
military forces along the border with The Democratic Commonwealth of Tethys,
citing "historical reunification rights" and claiming Tethys is an inseparable
part of Novarian territory. Novaris has launched what it calls a "decisive
pressure campaign," combining military demonstrations, economic coercion, and
cyber operations.

Tethys has responded by mobilizing its defensive forces and appealing to the
international community. While militarily smaller, Tethys possesses significant
asymmetric capabilities including advanced cyber units, precision strike capacity
against Novarian mobilization centers, and economic leverage through control of
critical energy transit pipelines.

The crisis is escalating across multiple domains: cyber attacks are being
exchanged daily, economic warfare is beginning with trade restrictions and
financial sanctions, and intelligence suggests covert operations are underway
on both sides.

**RECENT TIMELINE**

  • Three months ago: Tethys president delivered speech declaring permanent
    independence, rejecting any reunification talks

  • Two months ago: Novaris expelled Tethys diplomats and severed most trade
    ties in retaliation

  • One month ago: Meridian Secretary of State visited Tethys capital,
    publicly reaffirmed security commitment

  • Two weeks ago: Novaris began "Sovereign Shield" military exercises in
    waters near Tethys, simulating amphibious assault operations

  • Today: Forces remain mobilized on both sides; international diplomacy
    intensifying

**MILITARY SITUATION** (Day 0)

Forces are roughly matched despite Novaris's numerical advantage. Tethys holds
the defender's advantage on home terrain and has demonstrated willingness to
impose severe costs on any invasion through asymmetric warfare. Novaris possesses
superior conventional forces but faces the risk of a costly quagmire.

No territory has been seized yet, though Novaris controls adjacent waters and
airspace. Both sides have established defensive positions. Military analysts
assess the situation as highly volatile but not yet in active combat phase.

**ECONOMIC FACTORS**

Initial international sanctions have been imposed on Novaris, targeting financial
institutions and restricting technology exports. However, Novaris maintains
substantial energy export revenues, and approximately 30% of these revenues flow
through Tethys-controlled pipelines—creating mutual economic dependence.

The economic pressure is moderate but growing. Tethys faces disruption to trade
routes and is preparing for potential energy cutoffs, while Novaris calculates
the cost of sustained international isolation.

**DIPLOMATIC SITUATION**

International support for Tethys is substantial and growing. Meridian, the
traditional ally and democratic bloc leader, has reaffirmed its security
commitment but faces domestic political constraints on direct military
intervention. Aurelia, a major regional power, is coordinating diplomatic
efforts while carefully balancing its energy dependence on Novaris against
pressure to support Tethys.

Valkoria, a neutral power with economic ties to both sides, is attempting to
facilitate dialogue. The International Organization has called emergency sessions
and is positioning humanitarian assistance capabilities.

**KEY ACTORS**

Primary Belligerents:
  • The People's Federation of Novaris (referred to as "Novaris"): Regional
    hegemon with substantial military capabilities, claiming historical rights
    to Tethys territory. Faces economic vulnerabilities due to sanctions and
    internal ethnic divisions (15% of population is ethnic Tethyan).

  • The Democratic Commonwealth of Tethys (referred to as "Tethys"): Smaller
    democratic state defending independence, possessing asymmetric military
    capabilities and strong international sympathy. Vulnerable to protracted
    conflict but motivated by survival imperative.

External Powers:
  • Meridian: Traditional security ally of Tethys and democratic bloc leader.
    Has committed to defending Tethys but constrained by domestic war-weariness
    and competing global priorities.

  • Valkoria: Officially neutral power maintaining economic ties with Novaris.
    Attempting balanced relationships while facilitating diplomatic channels.

  • Aurelia: Regional diplomatic coordinator balancing energy dependence on
    Novaris against international pressure to support Tethys sovereignty.

  • International Organization: Multilateral body providing humanitarian
    coordination and diplomatic forum for potential de-escalation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def create_collapse_forecast_prompt_with_scenario(
    period: int,
    state_before: Dict,
    external_events: List[str],
    novaris_actions: List[str],
    tethys_actions: List[str],
    historical_summary: str = ""
) -> str:
    """
    Create collapse forecast prompt WITH initial scenario backstory.

    Convenience function that combines all 4 sections into a single prompt.
    For sharding experiments, use get_prompt_sections() instead.

    Returns:
        Complete prompt string
    """
    scenario, history, data, instructions = get_prompt_sections(
        period, state_before, external_events, novaris_actions,
        tethys_actions, historical_summary
    )

    parts = [scenario]
    if history:
        parts.append(history)
    parts.append(data)
    parts.append(instructions)
    return "\n".join(parts)


def get_initial_scenario_text() -> str:
    """Return the initial scenario description for separate sharding."""
    return INITIAL_SCENARIO


def get_prompt_sections(
    period: int,
    state_before: Dict,
    external_events: List[str],
    novaris_actions: List[str],
    tethys_actions: List[str],
    historical_summary: str = ""
) -> tuple:
    """
    Return prompt split into sections for selective sharding.

    Returns:
        (initial_scenario, historical_summary, current_period_data, instructions)
        - initial_scenario: Rich backstory (shardable)
        - historical_summary: Prior period history (shardable)
        - current_period_data: Current state/events/actions (shardable)
        - instructions: Forecasting task + output format (NEVER sharded)
    """

    # Format events
    if external_events:
        events_text = "\n".join([f"  {i}. {e}" for i, e in enumerate(external_events, 1)])
    else:
        events_text = "  (No major external events this period)"

    # Format actions
    novaris_text = ", ".join(novaris_actions) if novaris_actions else "(No actions)"
    tethys_text = ", ".join(tethys_actions) if tethys_actions else "(No actions)"

    # Current period DATA (shardable)
    current_period_data = f"""
{'='*80}
PERIOD {period} SITUATION UPDATE
{'='*80}

CURRENT STATE (End of Period {period-1}):
- Tethys Territory Remaining: {(1-state_before.get('territory_controlled', 0))*100:.1f}%
- Tethys GDP: ${state_before.get('tethys_gdp', 30):.1f}B (started at $30B)
- Novaris GDP: ${state_before.get('novaris_gdp', 100):.1f}B (started at $100B)
- Military Balance: {state_before.get('military_balance', 0):.2f} (-1=Novaris advantage, +1=Tethys advantage)
- International Support for Tethys: {state_before.get('international_support', 0.5)*100:.0f}%
- Sanctions on Novaris: {state_before.get('sanctions_level', 0)*100:.0f}%

EXTERNAL EVENTS THIS PERIOD:
{events_text}

ACTIONS TAKEN THIS PERIOD:
Novaris: {novaris_text}
Tethys: {tethys_text}
"""

    # Instructions (NEVER sharded - always included in full)
    instructions = f"""
{'='*80}
YOUR FORECASTING TASK
{'='*80}

Forecast the probability that Tethys's government will collapse or be removed
from power by the end of Period {period}.

Government collapse includes:
- Military defeat leading to regime change
- Internal coup or revolution
- Economic collapse forcing government resignation
- Loss of governing capacity due to territorial loss
- Capitulation or forced settlement removing current leadership

CRITICAL INSTRUCTIONS:
- Output a probability between 0.0 and 1.0 (not a percentage)
- USE THE FULL PROBABILITY RANGE - don't cluster around 0.5
- Be calibrated: 0.2 means 20% chance, 0.8 means 80% chance
- Consider ALL factors: military, economic, political, international

Think step-by-step:
1. Assess Tethys's current military/territorial position
2. Evaluate economic sustainability and internal stability
3. Consider external support and diplomatic situation
4. Analyze this period's events and actions
5. Estimate overall collapse probability

OUTPUT FORMAT (JSON):
{{
  "probability": 0.XX,
  "confidence": "low|medium|high",
  "rationale": "2-3 sentence explanation of key factors driving your probability estimate"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
Use the FULL range 0.0 to 1.0 based on the actual situation - don't default to middle values.
"""

    return (INITIAL_SCENARIO, historical_summary, current_period_data, instructions)


if __name__ == "__main__":
    print("Testing collapse forecast prompt with scenario...")

    test_state = {
        'territory_controlled': 0.0, 'military_balance': 0.0,
        'novaris_gdp': 100.0, 'tethys_gdp': 30.0,
        'international_support': 0.5, 'sanctions_level': 0.0
    }

    # Test 4-part sections (Period 1, no history)
    scenario, history, data, instructions = get_prompt_sections(
        period=1,
        state_before=test_state,
        external_events=["Initial skirmishes"],
        novaris_actions=['military_buildup'],
        tethys_actions=['show_of_force']
    )

    print(f"\nSection lengths (Period 1):")
    print(f"  Initial scenario: {len(scenario)} chars")
    print(f"  History: {len(history)} chars")
    print(f"  Current period data: {len(data)} chars")
    print(f"  Instructions: {len(instructions)} chars")

    # Verify instructions contain output format
    assert "probability" in instructions, "Instructions missing probability!"
    assert "JSON" in instructions, "Instructions missing JSON format!"
    assert "YOUR FORECASTING TASK" in instructions, "Instructions missing task header!"

    # Verify data does NOT contain instructions
    assert "YOUR FORECASTING TASK" not in data, "Data should not contain instructions!"
    assert "OUTPUT FORMAT" not in data, "Data should not contain output format!"

    # Test combined prompt
    prompt = create_collapse_forecast_prompt_with_scenario(
        period=1, state_before=test_state,
        external_events=["Initial skirmishes"],
        novaris_actions=['military_buildup'],
        tethys_actions=['show_of_force']
    )
    print(f"\nFull prompt length: {len(prompt)} chars")

    # Verify JSON braces render correctly
    assert '{{' not in instructions, "Double braces in instructions - f-string escaping error!"
    assert '{' in instructions, "JSON example braces missing from instructions!"

    print("\n[OK] 4-part section split working correctly!")
    print("[OK] Instructions separated from data!")
    print("[OK] JSON format renders correctly!")
