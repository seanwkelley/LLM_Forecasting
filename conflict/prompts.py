"""
Conflict Agent Prompts -- System and user prompts for LLM faction agents.

Each agent receives:
- System prompt: Faction identity, role, worldview, persona (rich backstory)
- User prompt: Current conflict state, available actions
- Output: JSON {action, reasoning}

Agents see public state + their own faction's private info.
They do NOT see the opponent faction's resource levels.
"""

from __future__ import annotations

from conflict.engine import ACTION_SPACE, ConflictState


# =============================================================================
# CONFLICT HISTORY -- Shared context for all agents
# =============================================================================

CONFLICT_HISTORY = """\
The relationship between Novaris and Tethys spans three centuries. Tethys was \
incorporated into the Novaris Empire in 1742 and existed as an 'Autonomous Province' \
for 208 years. During the Great Continental War (1940-1950), Tethys declared \
independence on March 15, 1950. Novaris never formally recognized it.

Modern Tethys is 62% ethnic Tethyan, 28% ethnic Novaran (concentrated in eastern \
regions), and 10% other minorities -- fueling Novaris's claim to 'protect' ethnic \
Novarans.

**Previous Crises:**
- 2023 "Fishing Wars": Naval clash, 3 Tethyan sailors killed, resolved by mediation
- 2030 "Winter Crisis": Novaris cut gas supplies; 18 Tethyan civilians died from cold
- 2036 "Eastern Districts Seizure": After Tethys's Velvet Spring, Novaris-backed \
separatists seized two eastern districts; frozen conflict persisted for a decade
- 2042 "Infrastructure Cyberattack": Sophisticated attack disabled Tethyan power \
grids, hospitals, banking for 72 hours (attributed to Novaris)

**Current Trigger:** President Marchetti's March 2046 announcement that Tethys would \
seek Meridian Alliance membership crossed Novaris's declared 'red line.' Within 48 \
hours, Novaris mobilized forces. By June 2046, 180,000 Novaris troops massed on \
the border."""


# =============================================================================
# FACTION CONTEXT
# =============================================================================

NOVARIS_CONTEXT = """\
**Your Faction: NOVARIS (Major Power)**
Novaris is a major regional power that considers the Tethyan territories historically \
part of its sphere of influence. Novaris views Tethys's Western integration as an \
existential threat to its security buffer zone. Novaris has superior conventional \
military capability but faces economic pressure from international sanctions.

**Novaris Grievances:**
- Loss of historic territory and 'humiliation' of 1950 independence
- Treatment of ethnic Novarans in Tethys (perceived discrimination)
- Tethys's westward orientation seen as betrayal and encirclement
- Meridian Alliance expansion toward Novaris borders

**Strategic Objectives:**
- Maintain influence over Tethys and prevent Western alignment
- Protect the ethnic Novarian minority in Tethys
- Demonstrate military credibility to deter future challenges
- Minimize economic damage from sanctions"""

TETHYS_CONTEXT = """\
**Your Faction: TETHYS (Small Power / Defender)**
Tethys is a smaller nation fighting to maintain its sovereignty and territorial \
integrity against Novaris. Tethys relies on international support, asymmetric \
warfare, and diplomatic coalitions. Tethys has strong popular will to resist \
but limited conventional military capability.

**Tethys Grievances:**
- Centuries of imperial domination and cultural suppression
- 1950s-era massacres during independence struggle (officially denied by Novaris)
- 2030 gas cutoff that killed civilians
- 2036 territory seizure and ongoing support for separatists
- Constant interference in domestic politics and cyber warfare

**Strategic Objectives:**
- Defend sovereignty and territorial integrity
- Secure international support and military aid
- Make occupation unsustainably costly for Novaris
- Pursue diplomatic solutions from a position of strength"""

FACTION_CONTEXTS = {
    "novaris": NOVARIS_CONTEXT,
    "tethys": TETHYS_CONTEXT,
}


# =============================================================================
# SYSTEM PROMPT BUILDER
# =============================================================================

def get_system_prompt(agent: dict) -> str:
    """Build the full system prompt for a conflict agent.

    Parameters
    ----------
    agent : dict
        Agent template from agents_config.py.

    Returns
    -------
    Full system prompt with faction context, role, rich persona, and conflict history.
    """
    faction = agent["faction"]
    hawk_score = agent["hawk_dove"]
    hawk_label = ("strong hawk" if hawk_score > 0.7 else
                  "moderate hawk" if hawk_score > 0.5 else
                  "dove" if hawk_score < 0.35 else
                  "moderate")

    worldview_descriptions = {
        "realist": "You see international relations as a zero-sum competition for power. Military strength is the ultimate arbiter. Trust is earned through deterrence, not promises.",
        "liberal_institutionalist": "You believe in the power of international norms, institutions, and mutual benefit. Cooperation and diplomacy can produce lasting security that military force cannot.",
        "pragmatic_technocrat": "You are data-driven and outcome-focused. You evaluate options based on costs, benefits, and probabilities. Ideology is secondary to results.",
    }

    worldview_desc = worldview_descriptions.get(
        agent["worldview"],
        "You evaluate situations pragmatically based on available evidence."
    )

    # Build personality section from enriched fields
    personality_section = ""
    if "personality_traits" in agent:
        traits = "\n".join(f"  - {t}" for t in agent["personality_traits"])
        personality_section += f"\n**Your Personality:**\n{traits}\n"
    if "speech_patterns" in agent:
        personality_section += f"\n**How You Communicate:** {agent['speech_patterns']}\n"
    if "key_relationships" in agent:
        rels = "\n".join(f"  - {r}" for r in agent["key_relationships"])
        personality_section += f"\n**Key Relationships:**\n{rels}\n"

    return f"""\
You are {agent['name']} in a geopolitical crisis simulation between Novaris and Tethys.

**Your Role:** {agent['role'].replace('_', ' ').title()}
**Your Disposition:** {hawk_label} (hawk/dove score: {hawk_score:.2f})
**Your Worldview:** {worldview_desc}

**Your Background:**
{agent['backstory']}
{personality_section}
{FACTION_CONTEXTS[faction]}

**Conflict History:**
{CONFLICT_HISTORY}

**Your Task:** Each period, recommend ONE action for your faction based on the current \
situation. Your recommendation will be combined with your colleagues' recommendations \
to determine the faction's actual action.

You must respond with ONLY valid JSON. No other text."""


def get_system_prompt_no_persona(agent: dict) -> str:
    """Build a minimal system prompt with role and faction but no persona.

    Strips: personal name, backstory, personality traits, speech patterns,
    key relationships, hawk/dove score, worldview description.

    Keeps: role title, faction identity, faction context, conflict history,
    task instructions. This is the "generic LLM advisor" condition.
    """
    faction = agent["faction"]
    role_title = agent["role"].replace("_", " ").title()

    return f"""\
You are an advisor in a geopolitical crisis simulation between Novaris and Tethys.

**Your Role:** {role_title}
**Your Faction:** {faction.upper()}

{FACTION_CONTEXTS[faction]}

**Conflict History:**
{CONFLICT_HISTORY}

**Your Task:** Each period, recommend ONE action for your faction based on the current \
situation. Your recommendation will be combined with your colleagues' recommendations \
to determine the faction's actual action.

You must respond with ONLY valid JSON. No other text."""


# =============================================================================
# USER PROMPT BUILDER
# =============================================================================

def build_user_prompt(
    agent: dict,
    state: ConflictState,
    shock_description: str = "",
    history_window: int = 5,
) -> str:
    """Build the per-period user prompt for an LLM conflict agent.

    Parameters
    ----------
    agent : dict
        Agent template dict.
    state : ConflictState
        Current conflict state.
    shock_description : str
        Active shock descriptions.
    history_window : int
        Number of past periods to show.
    """
    parts = []
    faction = agent["faction"]
    own_faction = state.factions[faction]

    # --- Period header ---
    parts.append(f"=== PERIOD {state.period + 1} ===\n")

    # --- Escalation history (public) ---
    if state.escalation_history:
        parts.append("## Escalation History")
        start = max(0, len(state.escalation_history) - history_window)
        parts.append(f"{'Period':>6} | {'EI':>6} | {'Change':>8} | {'Your Action':>18} | {'Opponent Action':>18}")
        parts.append(f"{'------':>6} | {'------':>6} | {'--------':>8} | {'------------------':>18} | {'------------------':>18}")

        for i in range(start, len(state.escalation_history)):
            ei = state.escalation_history[i]
            if i > 0:
                delta = ei - state.escalation_history[i - 1]
                delta_str = f"{delta:+7.2f}"
            else:
                delta_str = "    n/a"

            # Show actions from history
            if i < len(state.action_history):
                actions = state.action_history[i]
                if faction == "novaris":
                    own_act = actions[0].action_name
                    opp_act = actions[1].action_name
                else:
                    own_act = actions[1].action_name
                    opp_act = actions[0].action_name
            else:
                own_act = "n/a"
                opp_act = "n/a"

            parts.append(f"{i+1:6d} | {ei:6.2f} | {delta_str} | {own_act:>18} | {opp_act:>18}")

        # Trend summary
        if len(state.escalation_history) >= 2:
            last = state.escalation_history[-1]
            prev = state.escalation_history[-2]
            change = last - prev
            direction = "ESCALATING" if change > 0.1 else "DE-ESCALATING" if change < -0.1 else "STABLE"
            parts.append(f"\nCurrent EI: {last:.2f}/10.0 ({direction}, {change:+.2f})")
        else:
            parts.append(f"\nCurrent EI: {state.escalation_history[-1]:.2f}/10.0")
        parts.append("")
    else:
        parts.append("## Situation")
        parts.append(f"Starting Escalation Index: {state.escalation_index:.2f}/10.0")
        parts.append("No action history yet (this is the first period).")
        parts.append("")

    # --- Current state (public) ---
    parts.append("## Current Situation")
    balance_desc = ("Novaris dominant" if state.military_balance < -0.15 else
                    "Tethys dominant" if state.military_balance > 0.15 else
                    "roughly balanced")
    parts.append(f"- Military Balance: {balance_desc} ({state.military_balance:+.2f})")
    parts.append(f"- Territory Controlled by Novaris: {state.territory_controlled*100:.1f}%")
    parts.append(f"- Sanctions on Novaris: {state.sanctions_level*100:.0f}%")
    parts.append(f"- International Support for Tethys: {state.international_support*100:.0f}%")
    parts.append("")

    # --- Faction private info ---
    parts.append("## Your Faction's Status")
    parts.append(f"- GDP: {own_faction.gdp:.2f}")
    parts.append(f"- Military Strength: {own_faction.military_strength:.2f}")
    parts.append(f"- Political Stability: {own_faction.political_stability:.2f}")
    parts.append(f"- Available Resources: {own_faction.resources:.1f}")
    parts.append("")

    # --- Shock info ---
    if shock_description:
        parts.append("## Special Conditions")
        parts.append(shock_description)
        parts.append("")

    # --- Available actions ---
    parts.append("## Available Actions")
    parts.append(f"{'Action':<25} | {'Effect':>7} | {'Cost':>5} | {'Category':>12}")
    parts.append(f"{'-'*25} | {'-'*7} | {'-'*5} | {'-'*12}")

    for name in sorted(ACTION_SPACE.keys(), key=lambda n: ACTION_SPACE[n]["escalation_delta"]):
        spec = ACTION_SPACE[name]
        # Skip actions the faction can't afford
        affordable = "  " if spec["cost"] <= own_faction.resources else "$ "
        effect_str = f"{spec['escalation_delta']:+.1f}"
        parts.append(f"{affordable}{name:<23} | {effect_str:>7} | {spec['cost']:5.1f} | {spec['category']:>12}")

    parts.append("")
    parts.append("Actions marked with '$' exceed your current resources and cannot be chosen.")
    parts.append("")

    # --- Response format ---
    action_names = [n for n in ACTION_SPACE.keys()
                    if ACTION_SPACE[n]["cost"] <= own_faction.resources]
    parts.append("Respond with ONLY this JSON (no other text):")
    parts.append("```json")
    parts.append("{")
    parts.append(f'  "action": "<one of: {", ".join(sorted(action_names))}>",')
    parts.append('  "reasoning": "<brief explanation from your perspective>"')
    parts.append("}")
    parts.append("```")

    return "\n".join(parts)
