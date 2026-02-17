"""
Multi-Scenario Forecasting Experiment
======================================

Tests forecasting conditions across 100 parametrically varied scenarios.
Each scenario has been pre-simulated for 1 period.

Conditions:
1. Baseline (100% information)
2. Shard Everything (varying info levels)
3. Shard Initial Only (varying info levels)

Metrics:
- Collapse probability (squared error / MSE)
- Novaris action prediction (accuracy)
- Tethys action prediction (accuracy)

Usage:
    python -u forecasting/run_multiscenario_experiment.py [--test] [--n-scenarios N]
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import re
import time
import argparse
import pandas as pd
import numpy as np
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.collapse_prompts_with_scenario import get_prompt_sections, INITIAL_SCENARIO

# Variant of INITIAL_SCENARIO with leaked intelligence on Novaris leadership hawkishness.
# Inserted into the KEY ACTORS / Novaris description.
INITIAL_SCENARIO_HAWKISH = INITIAL_SCENARIO.replace(
    '  • The People\'s Federation of Novaris (referred to as "Novaris"): Regional\n'
    '    hegemon with substantial military capabilities, claiming historical rights\n'
    '    to Tethys territory. Faces economic vulnerabilities due to sanctions and\n'
    '    internal ethnic divisions (15% of population is ethnic Tethyan).',

    '  • The People\'s Federation of Novaris (referred to as "Novaris"): Regional\n'
    '    hegemon with substantial military capabilities, claiming historical rights\n'
    '    to Tethys territory. Faces economic vulnerabilities due to sanctions and\n'
    '    internal ethnic divisions (15% of population is ethnic Tethyan).\n'
    '\n'
    '    INTELLIGENCE ASSESSMENT — NOVARIS LEADERSHIP: Novaris\'s senior decision-\n'
    '    makers are assessed as highly hawkish. The president has publicly stated\n'
    '    that Tethys must be "returned to the fold by any means necessary" and has\n'
    '    surrounded himself with military hardliners. Intelligence indicates the\n'
    '    inner circle views military action as preferable to prolonged negotiation,\n'
    '    and senior military commanders have standing authority to escalate without\n'
    '    civilian approval if crisis conditions intensify. Diplomatic back-channels\n'
    '    report that Novaris leadership views concessions as weakness and is willing\n'
    '    to absorb significant economic costs to achieve territorial objectives.'
)
# --- Backstory perspective variants (same facts, different analytical lens) ---

INITIAL_SCENARIO_AGGRESSOR = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INITIAL SITUATION REPORT: THE TETHYS CRISIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**THE CRISIS**

The People's Federation of Novaris has mobilized approximately 40% of its
military forces along the border with The Democratic Commonwealth of Tethys,
citing "historical reunification rights" and claiming Tethys is an inseparable
part of Novarian territory. Novaris has launched what it calls a "decisive
pressure campaign," combining military demonstrations, economic coercion, and
cyber operations. The scale and coordination of the campaign indicate serious
intent to compel reunification, by force if necessary.

Tethys has responded by mobilizing its defensive forces and appealing to the
international community. However, Tethys is significantly outmatched in
conventional military terms. Its asymmetric capabilities—cyber units, precision
strike capacity, and energy transit leverage—can impose costs on Novaris but
cannot prevent territorial loss if Novaris commits to a full offensive.

The crisis is escalating across multiple domains: cyber attacks are being
exchanged daily, economic warfare is beginning with trade restrictions and
financial sanctions, and intelligence suggests covert operations are underway
on both sides. Novaris holds the initiative and is dictating the tempo.

**RECENT TIMELINE**

  • Three months ago: Tethys president delivered speech declaring permanent
    independence, rejecting any reunification talks — a provocation Novaris
    has used to justify its mobilization

  • Two months ago: Novaris expelled Tethys diplomats and severed most trade
    ties, demonstrating willingness to absorb economic costs for strategic
    objectives

  • One month ago: Meridian Secretary of State visited Tethys capital,
    publicly reaffirmed security commitment — but offered no concrete
    military deployments or binding defense guarantees

  • Two weeks ago: Novaris began "Sovereign Shield" military exercises in
    waters near Tethys, simulating amphibious assault operations — a
    capability demonstration signaling readiness for invasion

  • Today: Forces remain mobilized on both sides; Novaris maintains
    operational momentum while international diplomacy has produced no
    concrete restraints on Novaris's options

**MILITARY SITUATION** (Day 0)

Novaris possesses decisive conventional superiority. While Tethys has
demonstrated capability for asymmetric resistance, its forces cannot hold
territory against a sustained Novaris offensive. Tethys's precision strike
and cyber capabilities impose costs but do not change the fundamental military
balance — Novaris can absorb those costs and still achieve territorial
objectives.

No territory has been seized yet, though Novaris controls adjacent waters and
airspace. Both sides have established defensive positions, but Novaris's
posture is offensive in nature. Military analysts assess that Novaris has the
capability to launch a successful ground campaign with its current deployment.

**ECONOMIC FACTORS**

Initial international sanctions have been imposed on Novaris, targeting financial
institutions and restricting technology exports. However, Novaris maintains
substantial energy export revenues and has demonstrated capacity to absorb
sanctions pressure. Approximately 30% of energy revenues flow through
Tethys-controlled pipelines, but Novaris has alternate routes and has signaled
willingness to sacrifice revenue for territorial goals.

Tethys faces severe economic pressure. Its trade routes are disrupted, its
economy is far smaller ($30B vs $100B GDP), and prolonged crisis will strain
fiscal capacity to sustain military mobilization. Economic attrition favors
Novaris decisively.

**DIPLOMATIC SITUATION**

International support for Tethys is vocal but constrained. Meridian, the
traditional ally, has reaffirmed its security commitment but faces domestic
political constraints on direct military intervention — no state has committed
troops, weapons deliveries, or binding defense guarantees. Aurelia is
coordinating diplomatic efforts but carefully hedging, dependent on Novaris
for energy supplies.

Valkoria, a neutral power with economic ties to both sides, is attempting to
facilitate dialogue but has no leverage to compel Novaris to stand down.
The International Organization has called emergency sessions but its track
record of preventing determined aggression by major powers is poor. The
diplomatic situation offers Tethys rhetorical support but no material
guarantee of survival.

**KEY ACTORS**

Primary Belligerents:
  • The People's Federation of Novaris (referred to as "Novaris"): Regional
    hegemon with substantial military capabilities, claiming historical rights
    to Tethys territory. Determined, escalation-ready, and willing to absorb
    economic costs. Faces internal ethnic divisions (15% ethnic Tethyan) but
    leadership views reunification as non-negotiable.

  • The Democratic Commonwealth of Tethys (referred to as "Tethys"): Smaller
    democratic state defending independence, possessing limited asymmetric
    military capabilities. Faces existential pressure — outmatched militarily,
    economically vulnerable, and dependent on uncertain external support.

External Powers:
  • Meridian: Traditional security ally of Tethys and democratic bloc leader.
    Has made verbal commitments but is constrained by domestic war-weariness
    and competing global priorities. No troops deployed, no binding guarantees.

  • Valkoria: Officially neutral power maintaining economic ties with Novaris.
    Attempting balanced relationships while facilitating diplomatic channels.
    Has no leverage over Novaris.

  • Aurelia: Regional diplomatic coordinator balancing energy dependence on
    Novaris against international pressure to support Tethys sovereignty.
    Unlikely to risk energy supply for Tethys.

  • International Organization: Multilateral body providing humanitarian
    coordination and diplomatic forum. Limited enforcement capability against
    a determined major power.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

INITIAL_SCENARIO_VULNERABILITY = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
international community. While Tethys possesses some asymmetric capabilities
including cyber units, precision strike capacity, and energy transit leverage,
the state faces simultaneous military, economic, and political pressure — a
combination that historically correlates with elevated state failure rates.

The crisis is escalating across multiple domains: cyber attacks are being
exchanged daily, economic warfare is beginning with trade restrictions and
financial sanctions, and intelligence suggests covert operations are underway
on both sides. The compounding nature of these stressors is a key risk factor.

**RECENT TIMELINE**

  • Three months ago: Tethys president delivered speech declaring permanent
    independence, rejecting any reunification talks — increasing political
    rigidity and narrowing off-ramps

  • Two months ago: Novaris expelled Tethys diplomats and severed most trade
    ties — eliminating bilateral channels and increasing economic isolation

  • One month ago: Meridian Secretary of State visited Tethys capital,
    publicly reaffirmed security commitment — verbal assurance without
    material deployment, a pattern historically associated with unreliable
    guarantees under sustained pressure

  • Two weeks ago: Novaris began "Sovereign Shield" military exercises in
    waters near Tethys, simulating amphibious assault operations — further
    compounding stress on Tethys defensive planning

  • Today: Forces remain mobilized on both sides; international diplomacy
    intensifying but no binding commitments secured

**MILITARY SITUATION** (Day 0)

Tethys has limited strategic depth and faces a numerically superior adversary.
While possessing asymmetric capabilities, Tethys's conventional forces cannot
match Novaris in sustained conflict. Historical analysis of similarly
positioned states — smaller, territorially exposed, facing a committed larger
adversary — shows high rates of territorial loss or state failure.

No territory has been seized yet, though Novaris controls adjacent waters and
airspace. Both sides have established defensive positions. The military
situation presents multiple compounding vulnerabilities: limited territory
at risk, dependence on external resupply, and a force structure designed for
deterrence rather than prolonged defense.

**ECONOMIC FACTORS**

Initial international sanctions have been imposed on Novaris, targeting financial
institutions and restricting technology exports. However, Novaris maintains
substantial energy export revenues (with approximately 30% flowing through
Tethys-controlled pipelines — a mutual vulnerability).

Tethys's economy is highly exposed. At $30B GDP versus Novaris's $100B,
Tethys lacks the fiscal reserves to sustain prolonged mobilization. Trade
route disruption directly threatens economic viability. States facing
simultaneous military threat and economic contraction face compounding
fragility — defense spending crowds out economic stabilization, while
economic deterioration undermines defense capacity.

**DIPLOMATIC SITUATION**

International support for Tethys exists but carries significant reliability
risk. Meridian has reaffirmed its security commitment but faces domestic
political constraints on direct military intervention. Historical analysis
shows that verbal security commitments from constrained democracies are
frequently downgraded under sustained pressure from a determined adversary.

Aurelia is coordinating diplomatic efforts while carefully balancing energy
dependence on Novaris. Valkoria, a neutral power, is attempting dialogue.
The International Organization has called emergency sessions. None of these
actors has made commitments that would materially alter the military balance
or guarantee Tethys's survival.

**KEY ACTORS**

Primary Belligerents:
  • The People's Federation of Novaris (referred to as "Novaris"): Regional
    hegemon with substantial military capabilities, claiming historical rights
    to Tethys territory. Faces economic vulnerabilities due to sanctions and
    internal ethnic divisions (15% ethnic Tethyan), but these are manageable
    stressors unlikely to prevent decisive action.

  • The Democratic Commonwealth of Tethys (referred to as "Tethys"): Smaller
    democratic state defending independence. Faces compounding vulnerabilities:
    military overstretch, economic fragility, territorial exposure, and
    dependence on external guarantees that may not materialize. Survival
    depends on factors largely outside its control.

External Powers:
  • Meridian: Traditional security ally of Tethys and democratic bloc leader.
    Has committed to defending Tethys but constrained by domestic war-weariness
    and competing global priorities. Commitment reliability is uncertain under
    escalation.

  • Valkoria: Officially neutral power maintaining economic ties with Novaris.
    Attempting balanced relationships while facilitating diplomatic channels.

  • Aurelia: Regional diplomatic coordinator balancing energy dependence on
    Novaris against international pressure to support Tethys sovereignty.

  • International Organization: Multilateral body providing humanitarian
    coordination and diplomatic forum. Track record of preventing state
    collapse against determined aggressors is limited.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

INITIAL_SCENARIO_ESCALATION = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
international community. Tethys possesses significant asymmetric capabilities
including advanced cyber units, precision strike capacity, and energy transit
leverage. However, the crisis is not static — it is actively escalating, with
each side's actions provoking further responses in a tightening spiral.

The crisis is escalating across multiple domains simultaneously: cyber attacks
are being exchanged daily with increasing severity, economic warfare is
intensifying through trade restrictions and financial sanctions, and
intelligence indicates covert operations are accelerating on both sides.
The multi-domain escalation creates compounding momentum that is narrowing
the window for diplomatic resolution.

**RECENT TIMELINE**

  • Three months ago: Tethys president delivered speech declaring permanent
    independence, rejecting any reunification talks — an escalatory move that
    hardened positions on both sides

  • Two months ago: Novaris expelled Tethys diplomats and severed most trade
    ties — eliminating key de-escalation channels and further raising the
    stakes

  • One month ago: Meridian Secretary of State visited Tethys capital,
    publicly reaffirmed security commitment — Novaris interpreted this as
    external interference, accelerating its timeline

  • Two weeks ago: Novaris began "Sovereign Shield" military exercises in
    waters near Tethys, simulating amphibious assault operations — forces
    positioned for exercises become forces positioned for action, and
    mobilization creates its own momentum

  • Today: Forces remain mobilized on both sides; each passing day of
    mobilization increases the likelihood of intentional or accidental
    escalation to active hostilities

**MILITARY SITUATION** (Day 0)

Forces are roughly matched despite Novaris's numerical advantage, but the
situation is defined by escalatory momentum rather than static balance. Both
sides have mobilized and established forward positions. Military exercises
are simulating combat operations. Cyber attacks are degrading command and
control systems. Each action invites counter-action.

No territory has been seized yet, but Novaris controls adjacent waters and
airspace. The transition from "crisis" to "active combat" requires
increasingly small triggers as forces remain in forward positions. Historical
analysis shows that prolonged mobilizations of this nature transition to
hostilities in the majority of cases — forces positioned for weeks become
forces that act.

**ECONOMIC FACTORS**

Initial international sanctions have been imposed on Novaris, targeting financial
institutions and restricting technology exports. However, Novaris maintains
substantial energy export revenues, and approximately 30% of these revenues flow
through Tethys-controlled pipelines — creating mutual economic dependence that
is itself a vector for escalation as both sides weaponize economic leverage.

The economic domain is actively escalating: trade restrictions are tightening,
sanctions are expanding, and both sides are preparing for economic decoupling.
Tethys faces disruption to trade routes and mounting fiscal pressure from
sustained mobilization, while Novaris calculates the cost of sustained
international isolation. Each round of economic retaliation narrows off-ramps
and deepens commitment to the current course.

**DIPLOMATIC SITUATION**

International support for Tethys is substantial but diplomacy is losing the
race against escalation. Meridian has reaffirmed its security commitment but
faces domestic political constraints on direct military intervention. Aurelia
is coordinating diplomatic efforts while balancing energy dependence on
Novaris. Off-ramps that existed months ago are closing as positions harden.

Valkoria, a neutral power, is attempting to facilitate dialogue, but each
escalatory step makes compromise more politically costly for both sides.
The International Organization has called emergency sessions, but the pace
of institutional diplomacy is slower than the pace of crisis escalation.
Covert operations and cyber attacks are eroding institutional stability and
trust in real-time, undermining the basis for negotiated settlement.

**KEY ACTORS**

Primary Belligerents:
  • The People's Federation of Novaris (referred to as "Novaris"): Regional
    hegemon with substantial military capabilities, claiming historical rights
    to Tethys territory. Committed to its pressure campaign and escalating
    steadily. Faces economic vulnerabilities due to sanctions and internal
    ethnic divisions (15% ethnic Tethyan), but has shown willingness to
    absorb costs and continue escalation.

  • The Democratic Commonwealth of Tethys (referred to as "Tethys"): Smaller
    democratic state defending independence, possessing asymmetric military
    capabilities and international sympathy. Equally committed — survival
    imperative leaves no room for concession, creating a collision course
    as both sides refuse to back down.

External Powers:
  • Meridian: Traditional security ally of Tethys and democratic bloc leader.
    Has committed to defending Tethys but constrained by domestic war-weariness
    and competing global priorities. Moving slower than the crisis.

  • Valkoria: Officially neutral power maintaining economic ties with Novaris.
    Attempting to facilitate dialogue, but the window for dialogue is closing.

  • Aurelia: Regional diplomatic coordinator balancing energy dependence on
    Novaris against international pressure to support Tethys sovereignty.

  • International Organization: Multilateral body providing humanitarian
    coordination and diplomatic forum. Institutional pace is slower than
    crisis momentum.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

INITIAL_SCENARIO_DOMESTIC = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
international community. Tethys possesses significant asymmetric capabilities
including advanced cyber units, precision strike capacity, and energy transit
leverage. However, as a democratic state, Tethys faces internal political
dynamics that constrain its crisis response — the government must maintain
public support, manage opposition politics, and hold together a coalition
under extreme stress.

The crisis is escalating across multiple domains: cyber attacks are being
exchanged daily, economic warfare is beginning with trade restrictions and
financial sanctions, and intelligence suggests covert operations are underway
on both sides. The external pressure is compounding existing internal tensions.

**RECENT TIMELINE**

  • Three months ago: Tethys president delivered speech declaring permanent
    independence, rejecting any reunification talks — a bold move that
    unified the public initially but committed the government to a position
    it must now defend at all costs

  • Two months ago: Novaris expelled Tethys diplomats and severed most trade
    ties — triggering immediate economic pain for Tethys citizens and
    businesses dependent on cross-border trade

  • One month ago: Meridian Secretary of State visited Tethys capital,
    publicly reaffirmed security commitment — boosting public morale but
    raising expectations of external rescue that may not materialize

  • Two weeks ago: Novaris began "Sovereign Shield" military exercises in
    waters near Tethys, simulating amphibious assault operations — causing
    public anxiety and political pressure on the government to respond
    decisively

  • Today: Forces remain mobilized on both sides; the economic and
    psychological toll on Tethys's population is mounting daily

**MILITARY SITUATION** (Day 0)

Forces are roughly matched despite Novaris's numerical advantage. Tethys holds
the defender's advantage on home terrain and has demonstrated willingness to
impose severe costs through asymmetric warfare. Novaris possesses superior
conventional forces but faces the risk of a costly quagmire.

No territory has been seized yet, though Novaris controls adjacent waters and
airspace. Both sides have established defensive positions. However, Tethys's
military effectiveness depends on sustained domestic cohesion — conscription,
civil defense, and economic sacrifice all require a population willing to
bear costs. If public will fractures, military capacity follows.

**ECONOMIC FACTORS**

Initial international sanctions have been imposed on Novaris, targeting financial
institutions and restricting technology exports. However, Novaris maintains
substantial energy export revenues, and approximately 30% of these revenues flow
through Tethys-controlled pipelines — creating mutual economic dependence.

The economic toll falls disproportionately on Tethys's civilian population.
Trade disruption is hitting small businesses and households. At $30B GDP versus
Novaris's $100B, Tethys has far less capacity to cushion its citizens from
economic pain. Rising prices, supply shortages, and uncertainty are eroding the
initial rally-around-flag solidarity. Opposition politicians are beginning to
question whether the government's rejection of negotiations was reckless.

**DIPLOMATIC SITUATION**

International support for Tethys is substantial and growing. Meridian has
reaffirmed its security commitment but faces domestic political constraints
on direct military intervention. Aurelia is coordinating diplomatic efforts
while balancing energy dependence on Novaris.

Valkoria, a neutral power, is attempting to facilitate dialogue. The
International Organization has called emergency sessions. Domestically,
Tethys's opposition parties are divided: some support the government's hard
line, others argue for negotiation before the situation deteriorates further.
The government's democratic legitimacy — normally a strength — means it cannot
ignore rising public discontent indefinitely.

**KEY ACTORS**

Primary Belligerents:
  • The People's Federation of Novaris (referred to as "Novaris"): Regional
    hegemon with substantial military capabilities, claiming historical rights
    to Tethys territory. Faces economic vulnerabilities due to sanctions and
    internal ethnic divisions (15% ethnic Tethyan). As an authoritarian state,
    Novaris can suppress domestic dissent — an advantage Tethys does not share.

  • The Democratic Commonwealth of Tethys (referred to as "Tethys"): Smaller
    democratic state defending independence, possessing asymmetric military
    capabilities and international sympathy. Faces internal political
    fragility: opposition parties, ethnic Novarian minority (uncertain
    loyalty under wartime pressure), economic pain eroding public support,
    and a government that must maintain democratic legitimacy while managing
    an existential crisis.

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

INITIAL_SCENARIO_INERTIA = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
international community. Tethys possesses significant asymmetric capabilities
including advanced cyber units, precision strike capacity against Novarian
mobilization centers, and economic leverage through control of critical energy
transit pipelines. The Tethys government remains functional, its institutions
intact, and its military command structure unified.

The crisis is escalating across multiple domains: cyber attacks are being
exchanged daily, economic warfare is beginning with trade restrictions and
financial sanctions, and intelligence suggests covert operations are underway
on both sides. However, escalation has not yet crossed the threshold into
active armed conflict, and governing institutions on both sides continue to
function.

**RECENT TIMELINE**

  • Three months ago: Tethys president delivered speech declaring permanent
    independence, rejecting any reunification talks

  • Two months ago: Novaris expelled Tethys diplomats and severed most trade
    ties — a significant but non-kinetic escalation that Tethys has absorbed
    without institutional disruption

  • One month ago: Meridian Secretary of State visited Tethys capital,
    publicly reaffirmed security commitment — reinforcing the existing
    international framework supporting Tethys

  • Two weeks ago: Novaris began "Sovereign Shield" military exercises in
    waters near Tethys, simulating amphibious assault operations — military
    posturing that has not translated into actual military action

  • Today: Forces remain mobilized on both sides; the situation is tense but
    the status quo persists — no territory has changed hands, no government
    has fallen, no military engagement has occurred

**MILITARY SITUATION** (Day 0)

Forces are roughly matched despite Novaris's numerical advantage. Tethys holds
the defender's advantage on home terrain and has demonstrated willingness to
impose severe costs on any invasion through asymmetric warfare. Novaris possesses
superior conventional forces but faces the risk of a costly quagmire.

No territory has been seized. No shots have been fired. Both sides have
established defensive positions. Government collapse requires a chain of
failures — military defeat, institutional breakdown, and loss of political
authority — none of which have begun. States under external pressure
typically degrade slowly rather than collapse suddenly, and Tethys's
institutions show no signs of acute failure.

**ECONOMIC FACTORS**

Initial international sanctions have been imposed on Novaris, targeting financial
institutions and restricting technology exports. However, Novaris maintains
substantial energy export revenues, and approximately 30% of these revenues flow
through Tethys-controlled pipelines — creating mutual economic dependence.

The economic pressure is moderate but manageable. Tethys faces disruption to
trade routes and is preparing for potential energy cutoffs, but its economy
continues to function. GDP contraction under crisis pressure is normal and
does not by itself indicate state failure — states routinely sustain
significant economic damage without government collapse. Novaris calculates
the cost of sustained international isolation.

**DIPLOMATIC SITUATION**

International support for Tethys is substantial and growing. Meridian, the
traditional ally and democratic bloc leader, has reaffirmed its security
commitment. While constrained on direct military intervention, Meridian's
engagement creates a deterrence framework that raises the costs of Novaris
aggression. Aurelia is coordinating diplomatic efforts while carefully
balancing its energy dependence on Novaris.

Valkoria, a neutral power with economic ties to both sides, is attempting to
facilitate dialogue. The International Organization has called emergency sessions
and is positioning humanitarian assistance capabilities. The diplomatic
architecture supporting Tethys remains intact and is actively expanding —
the international community has not abandoned Tethys, and each week of
sustained support strengthens the status quo.

**KEY ACTORS**

Primary Belligerents:
  • The People's Federation of Novaris (referred to as "Novaris"): Regional
    hegemon with substantial military capabilities, claiming historical rights
    to Tethys territory. Faces economic vulnerabilities due to sanctions and
    internal ethnic divisions (15% ethnic Tethyan). Has not yet committed to
    military action despite months of mobilization — suggesting the costs of
    invasion are giving Novaris pause.

  • The Democratic Commonwealth of Tethys (referred to as "Tethys"): Smaller
    democratic state defending independence, possessing asymmetric military
    capabilities and strong international sympathy. Government is intact,
    institutions are functioning, military is mobilized and unified. The
    burden of initiating state collapse falls on the aggressor, and Novaris
    has not yet acted.

External Powers:
  • Meridian: Traditional security ally of Tethys and democratic bloc leader.
    Has committed to defending Tethys but constrained by domestic war-weariness
    and competing global priorities. Continued engagement reinforces deterrence.

  • Valkoria: Officially neutral power maintaining economic ties with Novaris.
    Attempting balanced relationships while facilitating diplomatic channels.

  • Aurelia: Regional diplomatic coordinator balancing energy dependence on
    Novaris against international pressure to support Tethys sovereignty.

  • International Organization: Multilateral body providing humanitarian
    coordination and diplomatic forum for potential de-escalation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# All backstory perspectives for reframe condition: original + 5 variants
BACKSTORY_VARIANTS = [
    INITIAL_SCENARIO,
    INITIAL_SCENARIO_AGGRESSOR,
    INITIAL_SCENARIO_VULNERABILITY,
    INITIAL_SCENARIO_ESCALATION,
    INITIAL_SCENARIO_DOMESTIC,
    INITIAL_SCENARIO_INERTIA,
]

from forecasting.information_sharding import create_information_distribution, create_uniform_information_distribution
from forecasting.sharding_strategies import apply_sharding_strategy

# Prediction model
PREDICTION_MODEL = "deepseek/deepseek-v3.2"

# Load scenario events (actual events from simulation RDS files)
_EVENTS_FILE = Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario/scenario_events.json")
_SCENARIO_EVENTS = {}
if _EVENTS_FILE.exists():
    with open(_EVENTS_FILE, 'r') as f:
        _SCENARIO_EVENTS = json.load(f)
    print(f"Loaded events for {len(_SCENARIO_EVENTS)} scenarios")

SYSTEM_PROMPT = """You are an expert geopolitical analyst specializing in government stability forecasting.

Your task is to predict the probability of government collapse based on:
- Strategic context and background
- Current military, economic, and political situation
- Recent events and actions

Apply rigorous analytical reasoning. Be well-calibrated: your probability should reflect your genuine assessment of the evidence. Moderate probabilities (0.4-0.6) are appropriate when the evidence is mixed.

Output ONLY valid JSON in the exact format specified."""

# --- Domain sharding constants ---
DOMAIN_FRAMING = (
    "A geopolitical crisis is unfolding between The People's Federation of "
    "Novaris and The Democratic Commonwealth of Tethys. Novaris has mobilized "
    "forces and launched a pressure campaign. Tethys is defending its "
    "independence with international support."
)

DOMAINS = ['military', 'economic', 'diplomatic', 'crisis']

DOMAIN_SECTIONS = {
    'military': ['MILITARY SITUATION'],
    'economic': ['ECONOMIC FACTORS'],
    'diplomatic': ['DIPLOMATIC SITUATION', 'KEY ACTORS'],
    'crisis': ['THE CRISIS', 'RECENT TIMELINE'],
}

DOMAIN_SYSTEM_PROMPTS = {
    'military': """You are a military intelligence analyst specializing in conflict outcomes and territorial control.

Your task is to estimate the probability of government collapse based ONLY on military and territorial indicators. Focus on what the military data tells you — force balance, territory held, and defensive viability.

Output ONLY valid JSON in the exact format specified.""",

    'economic': """You are an economic analyst specializing in wartime economic resilience and state fiscal viability.

Your task is to estimate the probability of government collapse based ONLY on economic indicators. Focus on what the economic data tells you — GDP trends, sanctions pressure, and economic sustainability under crisis.

Output ONLY valid JSON in the exact format specified.""",

    'diplomatic': """You are a diplomatic affairs analyst specializing in international coalitions and external intervention.

Your task is to estimate the probability of government collapse based ONLY on diplomatic indicators. Focus on what the diplomatic data tells you — international support levels, external actor behavior, and alliance dynamics.

Output ONLY valid JSON in the exact format specified.""",

    'crisis': """You are a crisis dynamics analyst specializing in escalation patterns and event-driven tipping points.

Your task is to estimate the probability of government collapse based ONLY on crisis indicators. Focus on what the crisis data tells you — crisis severity, recent events, and escalation trajectory.

Output ONLY valid JSON in the exact format specified.""",
}

DOMAIN_INSTRUCTIONS = {
    'military': """
YOUR FORECASTING TASK — MILITARY ASSESSMENT

Based on the military and territorial data provided, forecast the probability
that Tethys's government will collapse or be removed from power by the end
of Period 1.

Focus your analysis on:
1. How much territory has Tethys lost? Is the loss survivable?
2. What does the military balance indicate about Tethys's defensive viability?
3. Given these military realities, how likely is regime collapse?

OUTPUT FORMAT (JSON):
{
  "probability": 0.XX,
  "confidence": "low|medium|high",
  "rationale": "2-3 sentence explanation of key military factors driving your estimate"
}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
Base your estimate on the military evidence provided.""",

    'economic': """
YOUR FORECASTING TASK — ECONOMIC ASSESSMENT

Based on the economic data provided, forecast the probability that Tethys's
government will collapse or be removed from power by the end of Period 1.

Focus your analysis on:
1. How have Tethys's and Novaris's GDPs shifted? What does this imply for sustainability?
2. What is the sanctions pressure on Novaris? Does it constrain or enable aggression?
3. Given these economic realities, how likely is regime collapse?

OUTPUT FORMAT (JSON):
{
  "probability": 0.XX,
  "confidence": "low|medium|high",
  "rationale": "2-3 sentence explanation of key economic factors driving your estimate"
}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
Base your estimate on the economic evidence provided.""",

    'diplomatic': """
YOUR FORECASTING TASK — DIPLOMATIC ASSESSMENT

Based on the diplomatic data provided, forecast the probability that Tethys's
government will collapse or be removed from power by the end of Period 1.

Focus your analysis on:
1. How strong is international support for Tethys? Is it growing or eroding?
2. What are external actors doing — supporting, hedging, or abandoning Tethys?
3. Given the diplomatic landscape, how likely is regime collapse?

OUTPUT FORMAT (JSON):
{
  "probability": 0.XX,
  "confidence": "low|medium|high",
  "rationale": "2-3 sentence explanation of key diplomatic factors driving your estimate"
}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
Base your estimate on the diplomatic evidence provided.""",

    'crisis': """
YOUR FORECASTING TASK — CRISIS DYNAMICS ASSESSMENT

Based on the crisis data provided, forecast the probability that Tethys's
government will collapse or be removed from power by the end of Period 1.

Focus your analysis on:
1. How severe is the crisis level? What trajectory does it suggest?
2. What do recent external events signal about escalation or de-escalation?
3. Given the crisis dynamics, how likely is regime collapse?

OUTPUT FORMAT (JSON):
{
  "probability": 0.XX,
  "confidence": "low|medium|high",
  "rationale": "2-3 sentence explanation of key crisis factors driving your estimate"
}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
Base your estimate on the crisis evidence provided.""",
}


def load_multiscenario_data(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load scenario parameters and ground truth data."""
    scenarios = pd.read_csv(data_dir / "scenarios.csv")
    ground_truth = pd.read_csv(data_dir / "ground_truth.csv")

    print(f"Loaded {len(scenarios)} scenarios")
    print(f"Ground truth for {len(ground_truth)} scenarios")

    return scenarios, ground_truth


def create_scenario_prompt(scenario_params: pd.Series, ground_truth: pd.Series,
                           scenario_variant: str = "standard") -> Tuple[str, str, str, str]:
    """
    Create prompt sections for a single scenario.

    Args:
        scenario_variant: "standard" for baseline backstory,
                          "hawkish" for backstory with leaked Novaris leadership intel.

    Returns:
        (initial_scenario, historical_summary, current_period_data, instructions)
    """

    # Select backstory variant
    if scenario_variant == "hawkish":
        initial_scenario = INITIAL_SCENARIO_HAWKISH
    else:
        initial_scenario = INITIAL_SCENARIO

    # No historical summary for period 1
    historical_summary = ""

    # Build events section from actual scenario data
    scenario_id = scenario_params['scenario_id']
    events_data = _SCENARIO_EVENTS.get(scenario_id, {})

    events_text = ""
    external_events = events_data.get('external_events', [])
    if external_events:
        for i, evt in enumerate(external_events, 1):
            evt_type = evt.get('type', 'unknown').replace('_', ' ').title()
            evt_name = evt.get('name', '')
            evt_desc = evt.get('description', '')
            events_text += f"  {i}. [{evt_type}] {evt_name}: {evt_desc}\n"
    else:
        events_text = "  (No external events recorded this period)\n"

    # External actor actions (these are observable, not what we're predicting)
    ext_actor_text = ""
    ext_actions = events_data.get('external_actor_actions', [])
    if ext_actions:
        for ea in ext_actions:
            faction = ea.get('faction', 'unknown').replace('_', ' ').title()
            action = ea.get('action', 'unknown').replace('_', ' ')
            ext_actor_text += f"  - {faction}: {action}\n"
    else:
        ext_actor_text = "  (No external actor actions recorded)\n"

    # Build current period data from scenario parameters
    current_period_data = f"""
{'='*80}
PERIOD 1 SITUATION UPDATE
{'='*80}

CURRENT STATE:
- Tethys Territory Remaining: {(1 - scenario_params['territory_controlled']) * 100:.1f}%
- Tethys GDP: ${scenario_params['tethys_gdp']:.1f}B (baseline: $30B)
- Novaris GDP: ${scenario_params['novaris_gdp']:.1f}B (baseline: $100B)
- Military Balance: {scenario_params['military_balance']:.2f} (-1=Novaris advantage, +1=Tethys advantage)
- International Support for Tethys: {scenario_params['international_support'] * 100:.0f}%
- Sanctions on Novaris: {scenario_params['sanctions_level'] * 100:.0f}%
- Crisis Level: {scenario_params['crisis_level']:.0f}/10

EXTERNAL EVENTS THIS PERIOD:
{events_text}
EXTERNAL ACTOR ACTIONS THIS PERIOD:
{ext_actor_text}
ACTIONS TAKEN BY NOVARIS AND TETHYS THIS PERIOD:
(Forecaster must predict these - actual actions withheld)
"""

    # Instructions
    instructions = """
{'='*80}
YOUR FORECASTING TASK
{'='*80}

Forecast the probability that Tethys's government will collapse or be removed
from power by the end of Period 1.

Government collapse includes:
- Military defeat leading to regime change
- Internal coup or revolution
- Economic collapse forcing government resignation
- Loss of governing capacity due to territorial loss
- Capitulation or forced settlement removing current leadership

CRITICAL INSTRUCTIONS:
- Output a probability between 0.0 and 1.0 (not a percentage)
- Be well-calibrated: moderate probabilities (0.4-0.6) are appropriate when evidence is mixed
- Consider ALL factors: military, economic, political, international

Think step-by-step:
1. Assess Tethys's current military/territorial position
2. Evaluate economic sustainability and internal stability
3. Consider external support and diplomatic situation
4. Analyze crisis level and momentum
5. Estimate overall collapse probability

OUTPUT FORMAT (JSON):
{
  "probability": 0.XX
}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
"""

    return initial_scenario, historical_summary, current_period_data, instructions


def extract_backstory_sections(scenario_text: str) -> Dict[str, str]:
    """Parse INITIAL_SCENARIO into named sections by **SECTION** markers.

    Returns dict mapping section name (e.g. 'THE CRISIS') to its body text.
    """
    pattern = r'\*\*([^*]+)\*\*[^\n]*\n'
    matches = list(re.finditer(pattern, scenario_text))
    sections = {}
    for i, match in enumerate(matches):
        header = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(scenario_text)
        sections[header] = scenario_text[start:end].strip()
    return sections


def create_domain_prompt(
    scenario_params: pd.Series,
    ground_truth: pd.Series,
    domain: str
) -> Tuple[str, str, str, str]:
    """
    Create prompt sections for one scenario filtered to a single analytical domain.

    Each agent gets:
    - Minimal framing (DOMAIN_FRAMING)
    - Domain-specific backstory section(s) from INITIAL_SCENARIO
    - Domain-specific numeric data fields
    - Full instructions (unchanged from baseline)

    Returns:
        (initial_scenario, historical_summary, current_period_data, instructions)
    """
    # --- Backstory ---
    sections = extract_backstory_sections(INITIAL_SCENARIO)
    backstory_parts = []
    for name in DOMAIN_SECTIONS[domain]:
        for key, text in sections.items():
            if name in key:
                backstory_parts.append(f"**{key}**\n\n{text}")
                break

    initial_scenario = DOMAIN_FRAMING + "\n\n" + "\n\n".join(backstory_parts)

    # No historical summary for period 1
    historical_summary = ""

    # --- Domain-specific current period data ---
    scenario_id = scenario_params['scenario_id']
    events_data = _SCENARIO_EVENTS.get(scenario_id, {})

    # Numeric state lines per domain
    state_lines = []
    if domain == 'military':
        state_lines.append(
            f"- Tethys Territory Remaining: "
            f"{(1 - scenario_params['territory_controlled']) * 100:.1f}%")
        state_lines.append(
            f"- Military Balance: {scenario_params['military_balance']:.2f} "
            f"(-1=Novaris advantage, +1=Tethys advantage)")
    elif domain == 'economic':
        state_lines.append(
            f"- Tethys GDP: ${scenario_params['tethys_gdp']:.1f}B (baseline: $30B)")
        state_lines.append(
            f"- Novaris GDP: ${scenario_params['novaris_gdp']:.1f}B (baseline: $100B)")
        state_lines.append(
            f"- Sanctions on Novaris: {scenario_params['sanctions_level'] * 100:.0f}%")
    elif domain == 'diplomatic':
        state_lines.append(
            f"- International Support for Tethys: "
            f"{scenario_params['international_support'] * 100:.0f}%")
    elif domain == 'crisis':
        state_lines.append(
            f"- Crisis Level: {scenario_params['crisis_level']:.0f}/10")

    state_text = "\n".join(state_lines)

    # Events/actions sections for relevant domains
    extra_sections = ""

    if domain == 'crisis':
        external_events = events_data.get('external_events', [])
        if external_events:
            events_text = ""
            for i, evt in enumerate(external_events, 1):
                evt_type = evt.get('type', 'unknown').replace('_', ' ').title()
                evt_name = evt.get('name', '')
                evt_desc = evt.get('description', '')
                events_text += f"  {i}. [{evt_type}] {evt_name}: {evt_desc}\n"
        else:
            events_text = "  (No external events recorded this period)\n"
        extra_sections += f"\nEXTERNAL EVENTS THIS PERIOD:\n{events_text}"

    if domain == 'diplomatic':
        ext_actions = events_data.get('external_actor_actions', [])
        if ext_actions:
            ext_actor_text = ""
            for ea in ext_actions:
                faction = ea.get('faction', 'unknown').replace('_', ' ').title()
                action = ea.get('action', 'unknown').replace('_', ' ')
                ext_actor_text += f"  - {faction}: {action}\n"
        else:
            ext_actor_text = "  (No external actor actions recorded)\n"
        extra_sections += f"\nEXTERNAL ACTOR ACTIONS THIS PERIOD:\n{ext_actor_text}"

    current_period_data = f"""
{'='*80}
PERIOD 1 SITUATION UPDATE — {domain.upper()} DOMAIN
{'='*80}

CURRENT STATE:
{state_text}
{extra_sections}
ACTIONS TAKEN BY NOVARIS AND TETHYS THIS PERIOD:
(Forecaster must predict these - actual actions withheld)
"""

    instructions = DOMAIN_INSTRUCTIONS[domain]

    return initial_scenario, historical_summary, current_period_data, instructions


def run_single_prediction(
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    sharding_strategy: str,
    information_fraction: float,
    agent_id: int,
    model: str = PREDICTION_MODEL,
    system_prompt: str = None
) -> Dict:
    """Run a single agent's collapse probability prediction."""
    forecaster = BaseLLMForecaster(model=model, temperature=1.0)

    prompt = apply_sharding_strategy(
        strategy=sharding_strategy,
        initial_scenario=initial_scenario,
        historical_summary=historical_summary,
        current_period_data=current_period_data,
        instructions=instructions,
        information_fraction=information_fraction,
        seed=agent_id
    )

    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=system_prompt or SYSTEM_PROMPT,
            response_format="json"
        )

        if not success or not response_text or response_text.strip() == "":
            return {'probability': 0.5, 'confidence': 'low', 'rationale': 'Error', '_fallback': 'api_error'}

        # Strip markdown fences
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)

        prob = result.get('probability', None)
        if prob is None:
            result['probability'] = 0.5
            result['_fallback'] = 'missing_probability_key'
        elif not (0.0 <= prob <= 1.0):
            result['probability'] = max(0.0, min(1.0, prob))
            result['_fallback'] = 'out_of_range'

        return result

    except json.JSONDecodeError:
        return {'probability': 0.5, 'confidence': 'low', 'rationale': 'JSON parse error', '_fallback': 'json_error'}
    except Exception as e:
        return {'probability': 0.5, 'confidence': 'low', 'rationale': str(e), '_fallback': 'exception'}


# --- Two-stage prediction ---

STAGE1_SYSTEM_PROMPT = """You are an expert geopolitical analyst specializing in predicting state behavior during crises.

Given a crisis scenario and current indicators, predict the most likely actions taken by each faction this period. Consider their strategic position, capabilities, and incentives.

Output ONLY valid JSON in the exact format specified."""

STAGE1_INSTRUCTIONS = """
Based on the situation above, what actions did Novaris and Tethys most likely take this period?

Consider:
- Novaris is the aggressor with military superiority, pursuing reunification
- Tethys is the defender with asymmetric capabilities and international support
- Actions span military, diplomatic, economic, intelligence, and covert domains
- Each faction typically takes 5-8 actions per period

OUTPUT FORMAT (JSON):
{
  "novaris_actions": ["action1", "action2", "..."],
  "tethys_actions": ["action1", "action2", "..."],
  "reasoning": "Brief explanation of why these actions are most likely"
}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
"""


# --- Debate constants ---

DEBATE_ROUND1_INSTRUCTIONS = """
{'='*80}
YOUR FORECASTING TASK
{'='*80}

Forecast the probability that Tethys's government will collapse or be removed
from power by the end of Period 1.

Government collapse includes:
- Military defeat leading to regime change
- Internal coup or revolution
- Economic collapse forcing government resignation
- Loss of governing capacity due to territorial loss
- Capitulation or forced settlement removing current leadership

CRITICAL INSTRUCTIONS:
- Output a probability between 0.0 and 1.0 (not a percentage)
- Be well-calibrated: moderate probabilities (0.4-0.6) are appropriate when evidence is mixed
- Consider ALL factors: military, economic, political, international

Think step-by-step:
1. Assess Tethys's current military/territorial position
2. Evaluate economic sustainability and internal stability
3. Consider external support and diplomatic situation
4. Analyze crisis level and momentum
5. Estimate overall collapse probability

OUTPUT FORMAT (JSON):
{
  "probability": 0.XX,
  "rationale": "2-3 sentence explanation of key factors driving your probability estimate"
}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
"""

DEBATE_ROUND2_SYSTEM_PROMPT = """You are an expert geopolitical analyst specializing in government stability forecasting.

You have already made an initial assessment of a crisis scenario. Now you have seen your colleagues' independent analyses of the same situation. Some identified risks you may have missed; others found stabilizing factors you didn't weigh heavily enough.

Genuinely reassess the evidence in light of these perspectives. Update your probability estimate if the arguments warrant it — but do not change your view just to conform. Your revised estimate should reflect your best judgment after considering all the analyses.

Output ONLY valid JSON in the exact format specified."""

DEBATE_ROUND2_INSTRUCTIONS_TEMPLATE = """
You previously estimated the collapse probability at {own_probability:.2f}.

Here is a summary of all analysts' independent assessments:

{debate_brief}

Now provide your updated forecast. Consider:
- Arguments from colleagues who disagree with you — did they identify factors you underweighted?
- Whether the range of estimates suggests genuine uncertainty you should reflect
- Your own original reasoning — was it sound, or did you miss something?

OUTPUT FORMAT (JSON):
{{
  "probability": 0.XX
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
"""


def run_two_stage_prediction(
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    agent_id: int,
    model: str = PREDICTION_MODEL,
    system_prompt: str = None
) -> Dict:
    """
    Two-stage prediction: first predict actions, then predict collapse
    conditioned on those predicted actions.
    """
    forecaster = BaseLLMForecaster(model=model, temperature=1.0)

    # --- Stage 1: Predict actions ---
    stage1_parts = [initial_scenario]
    if historical_summary:
        stage1_parts.append(historical_summary)
    # Strip the "actions withheld" line from current data for stage 1
    stage1_data = current_period_data.replace(
        "ACTIONS TAKEN BY NOVARIS AND TETHYS THIS PERIOD:\n(Forecaster must predict these - actual actions withheld)",
        "")
    stage1_parts.append(stage1_data)
    stage1_parts.append(STAGE1_INSTRUCTIONS)
    stage1_prompt = "\n".join(stage1_parts)

    predicted_actions_text = ""
    try:
        response_text, success = forecaster.call_llm(
            user_prompt=stage1_prompt,
            system_prompt=STAGE1_SYSTEM_PROMPT,
            response_format="json"
        )
        if success and response_text and response_text.strip():
            clean = response_text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()
            actions = json.loads(clean)
            nov = actions.get('novaris_actions', [])
            teth = actions.get('tethys_actions', [])
            predicted_actions_text = (
                f"Novaris: {', '.join(nov)}\n"
                f"Tethys: {', '.join(teth)}")
    except Exception:
        pass  # Fall through with empty actions

    if not predicted_actions_text:
        predicted_actions_text = "(Action prediction failed — assess based on indicators alone)"

    # --- Stage 2: Predict collapse with predicted actions ---
    enriched_data = current_period_data.replace(
        "ACTIONS TAKEN BY NOVARIS AND TETHYS THIS PERIOD:\n(Forecaster must predict these - actual actions withheld)",
        f"PREDICTED ACTIONS THIS PERIOD (analyst estimate):\n{predicted_actions_text}")

    stage2_parts = [initial_scenario]
    if historical_summary:
        stage2_parts.append(historical_summary)
    stage2_parts.append(enriched_data)
    stage2_parts.append(instructions)
    stage2_prompt = "\n".join(stage2_parts)

    try:
        response_text, success = forecaster.call_llm(
            user_prompt=stage2_prompt,
            system_prompt=system_prompt or SYSTEM_PROMPT,
            response_format="json"
        )

        if not success or not response_text or response_text.strip() == "":
            return {'probability': 0.5, 'confidence': 'low', 'rationale': 'Error', '_fallback': 'api_error'}

        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)

        prob = result.get('probability', None)
        if prob is None:
            result['probability'] = 0.5
            result['_fallback'] = 'missing_probability_key'
        elif not (0.0 <= prob <= 1.0):
            result['probability'] = max(0.0, min(1.0, prob))
            result['_fallback'] = 'out_of_range'

        result['_predicted_actions'] = predicted_actions_text
        return result

    except json.JSONDecodeError:
        return {'probability': 0.5, 'confidence': 'low', 'rationale': 'JSON parse error', '_fallback': 'json_error'}
    except Exception as e:
        return {'probability': 0.5, 'confidence': 'low', 'rationale': str(e), '_fallback': 'exception'}


def _debate_round2_call(forecaster, prompt):
    """Helper for Round 2 LLM call in debate condition."""
    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=DEBATE_ROUND2_SYSTEM_PROMPT,
            response_format="json"
        )

        if not success or not response_text or response_text.strip() == "":
            return {'probability': 0.5, '_fallback': 'api_error'}

        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)
        prob = result.get('probability', None)
        if prob is None:
            result['probability'] = 0.5
            result['_fallback'] = 'missing_probability_key'
        elif not (0.0 <= prob <= 1.0):
            result['probability'] = max(0.0, min(1.0, prob))
            result['_fallback'] = 'out_of_range'
        return result

    except json.JSONDecodeError:
        return {'probability': 0.5, '_fallback': 'json_error'}
    except Exception as e:
        return {'probability': 0.5, '_fallback': 'exception'}


def run_debate_condition(
    scenario_id: str,
    scenario_params: pd.Series,
    ground_truth: pd.Series,
    n_agents: int,
    max_workers: int,
    model_pool: List[str],
    model: str
) -> Dict:
    """
    Debate condition: two rounds of prediction.

    Round 1: All agents independently predict collapse probability with rationale.
    Round 2: Each agent sees a debate brief (all Round 1 predictions + rationales)
             and provides an updated estimate.

    Final ensemble uses Round 2 predictions.
    """
    # Build prompts (standard, full-info)
    prompt_tuple = create_scenario_prompt(scenario_params, ground_truth)
    initial_scenario, historical_summary, current_period_data, _ = prompt_tuple

    # Per-agent model assignment
    if model_pool:
        agent_models = [model_pool[i % len(model_pool)] for i in range(n_agents)]
    else:
        agent_models = [model] * n_agents

    start_time = time.time()

    # --- Round 1: Independent predictions with rationale ---
    round1_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n_agents):
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)
            future = executor.submit(
                run_single_prediction,
                initial_scenario,
                historical_summary,
                current_period_data,
                DEBATE_ROUND1_INSTRUCTIONS,
                "none",   # no sharding
                1.0,      # full information
                i,
                agent_models[i],
                None      # default system prompt
            )
            futures.append((i, future))

        for i, future in futures:
            try:
                result = future.result()
                result['_agent_id'] = i
                round1_results.append(result)
            except Exception:
                round1_results.append({
                    'probability': 0.5, 'rationale': 'Error',
                    '_fallback': 'future_exception', '_agent_id': i
                })

    # --- Compile debate brief ---
    brief_lines = []
    for r in sorted(round1_results, key=lambda x: x.get('probability', 0.5)):
        p = r.get('probability', 0.5)
        rationale = r.get('rationale', 'No rationale provided')
        brief_lines.append(f"  Analyst (p={p:.2f}): {rationale}")
    debate_brief = "\n".join(brief_lines)

    # Map agent_id -> round1 result for own-probability lookup
    r1_by_agent = {r['_agent_id']: r for r in round1_results}

    # --- Round 2: Reassessment with debate brief ---
    round2_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n_agents):
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)

            own_prob = r1_by_agent.get(i, {}).get('probability', 0.5)
            round2_instructions = DEBATE_ROUND2_INSTRUCTIONS_TEMPLATE.format(
                own_probability=own_prob,
                debate_brief=debate_brief
            )

            # Build full prompt (same scenario data + debate instructions)
            prompt = apply_sharding_strategy(
                strategy="none",
                initial_scenario=initial_scenario,
                historical_summary=historical_summary,
                current_period_data=current_period_data,
                instructions=round2_instructions,
                information_fraction=1.0,
                seed=i
            )

            forecaster = BaseLLMForecaster(model=agent_models[i], temperature=1.0)
            future = executor.submit(
                _debate_round2_call,
                forecaster, prompt
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                round2_results.append(result)
            except Exception:
                round2_results.append({'probability': 0.5, '_fallback': 'future_exception'})

    duration = time.time() - start_time

    # Ensemble from Round 2
    probabilities = [r.get('probability', 0.5) for r in round2_results]
    ensemble_prob = np.mean(probabilities)
    true_prob = ground_truth['collapse_probability']
    squared_error = (ensemble_prob - true_prob) ** 2
    fallback_count = sum(1 for r in round2_results if '_fallback' in r)

    return {
        'scenario_id': scenario_id,
        'condition': 'debate',
        'sharding_strategy': 'none',
        'n_agents': n_agents,
        'duration_seconds': duration,
        'ensemble_probability': ensemble_prob,
        'ground_truth_probability': true_prob,
        'squared_error': squared_error,
        'probability_mean': np.mean(probabilities),
        'probability_std': np.std(probabilities),
        'probability_min': np.min(probabilities),
        'probability_max': np.max(probabilities),
        'fallback_count': fallback_count,
        'fallback_rate': fallback_count / n_agents
    }


def run_scenario_condition(
    scenario_id: str,
    scenario_params: pd.Series,
    ground_truth: pd.Series,
    condition_name: str,
    sharding_strategy: str,
    n_agents: int,
    max_workers: int = 5,
    model: str = PREDICTION_MODEL,
    uniform_fraction: float = None,
    scenario_variant: str = "standard",
    model_pool: List[str] = None
) -> Dict:
    """
    Run N agents for one scenario/condition combination.

    Args:
        uniform_fraction: If set, all agents receive this fraction of information
            (uniform sharding). If None, fractions drawn from Uniform(0.05, 0.95).
        scenario_variant: "standard", "hawkish", "domain_shard", "reframe", or "debate" backstory variant.
        model_pool: If set, cycle agents through these models instead of using
            a single model for all agents.

    Returns:
        Result dict with predictions and statistics
    """

    # Debate condition has its own multi-round flow
    if scenario_variant == "debate":
        return run_debate_condition(
            scenario_id=scenario_id,
            scenario_params=scenario_params,
            ground_truth=ground_truth,
            n_agents=n_agents,
            max_workers=max_workers,
            model_pool=model_pool,
            model=model
        )

    # Build per-agent prompt tuples, system prompts, and information fractions
    if scenario_variant == "domain_shard":
        # Domain sharding: each agent sees one complete analytical domain
        agent_prompts = []
        agent_sys_prompts = []
        for i in range(n_agents):
            domain = DOMAINS[i % len(DOMAINS)]
            agent_prompts.append(
                create_domain_prompt(scenario_params, ground_truth, domain))
            agent_sys_prompts.append(DOMAIN_SYSTEM_PROMPTS[domain])
        info_fractions = [1.0] * n_agents
    elif scenario_variant == "reframe":
        # Backstory reframing: each agent reads a different analytical perspective
        agent_prompts = []
        for i in range(n_agents):
            variant_scenario = BACKSTORY_VARIANTS[i % len(BACKSTORY_VARIANTS)]
            # Standard prompt but with the assigned backstory variant
            _, hist, cpd, instr = create_scenario_prompt(scenario_params, ground_truth)
            agent_prompts.append((variant_scenario, hist, cpd, instr))
        agent_sys_prompts = [None] * n_agents
        info_fractions = [1.0] * n_agents
    elif scenario_variant == "two_stage":
        # Two-stage: predict actions first, then collapse — uses standard prompts
        prompt_tuple = create_scenario_prompt(scenario_params, ground_truth)
        agent_prompts = [prompt_tuple] * n_agents
        agent_sys_prompts = [None] * n_agents
        info_fractions = [1.0] * n_agents
    else:
        # Standard / hawkish: all agents get the same prompt sections
        prompt_tuple = create_scenario_prompt(
            scenario_params, ground_truth, scenario_variant=scenario_variant)
        agent_prompts = [prompt_tuple] * n_agents
        agent_sys_prompts = [None] * n_agents  # uses default SYSTEM_PROMPT
        if uniform_fraction is not None:
            info_fractions = create_uniform_information_distribution(n_agents, uniform_fraction)
        else:
            info_fractions = create_information_distribution(n_agents)

    # Per-agent model assignment
    if model_pool:
        agent_models = [model_pool[i % len(model_pool)] for i in range(n_agents)]
    else:
        agent_models = [model] * n_agents

    # Build per-agent metadata for logging
    variant_names = ['original', 'aggressor', 'vulnerability', 'escalation', 'domestic', 'inertia']
    agent_metadata = []
    for i in range(n_agents):
        meta = {'agent_id': i, 'model': agent_models[i]}
        if scenario_variant == "reframe":
            meta['backstory_variant'] = variant_names[i % len(BACKSTORY_VARIANTS)]
        elif scenario_variant == "domain_shard":
            meta['domain'] = DOMAINS[i % len(DOMAINS)]
        else:
            meta['backstory_variant'] = scenario_variant
        agent_metadata.append(meta)

    # Run predictions in parallel
    start_time = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n_agents):
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)

            if scenario_variant == "two_stage":
                future = executor.submit(
                    run_two_stage_prediction,
                    agent_prompts[i][0],
                    agent_prompts[i][1],
                    agent_prompts[i][2],
                    agent_prompts[i][3],
                    i,
                    agent_models[i],
                    agent_sys_prompts[i]
                )
            else:
                future = executor.submit(
                    run_single_prediction,
                    agent_prompts[i][0],
                    agent_prompts[i][1],
                    agent_prompts[i][2],
                    agent_prompts[i][3],
                    sharding_strategy,
                    info_fractions[i],
                    i,
                    agent_models[i],
                    agent_sys_prompts[i]
                )
            futures.append((i, future))

        for i, future in futures:
            try:
                result = future.result()
                result.update(agent_metadata[i])
                results.append(result)
            except Exception as e:
                fallback = {'probability': 0.5, 'confidence': 'low', 'rationale': 'Error', '_fallback': 'future_exception'}
                fallback.update(agent_metadata[i])
                results.append(fallback)

    duration = time.time() - start_time

    # Extract predictions
    probabilities = [pred.get('probability', 0.5) for pred in results]
    ensemble_prob = np.mean(probabilities)

    # Calculate squared error (not Brier score - truth is continuous, not binary)
    true_prob = ground_truth['collapse_probability']
    squared_error = (ensemble_prob - true_prob) ** 2

    # Track fallbacks
    fallback_count = sum(1 for pred in results if '_fallback' in pred)

    return {
        'scenario_id': scenario_id,
        'condition': condition_name,
        'sharding_strategy': sharding_strategy,
        'n_agents': n_agents,
        'duration_seconds': duration,
        'ensemble_probability': ensemble_prob,
        'ground_truth_probability': true_prob,
        'squared_error': squared_error,
        'probability_mean': np.mean(probabilities),
        'probability_std': np.std(probabilities),
        'probability_min': np.min(probabilities),
        'probability_max': np.max(probabilities),
        'fallback_count': fallback_count,
        'fallback_rate': fallback_count / n_agents,
        '_agent_predictions': results,
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-Scenario Forecasting Experiment")
    parser.add_argument("--test", action="store_true", help="Quick test: 3 scenarios, 2 conditions, N=5")
    parser.add_argument("--n-scenarios", type=int, default=None, help="Number of scenarios to process")
    parser.add_argument("--n-agents", type=int, default=None, help="Number of agents per condition")
    parser.add_argument("--conditions", nargs="+", default=None,
                       help="Conditions to run (baseline, shard_everything, shard_initial_only, shard_uniform)")
    parser.add_argument("--uniform-fractions", nargs="+", type=float, default=[0.20, 0.50, 0.80],
                       help="Information fractions for shard_uniform conditions (default: 0.20 0.50 0.80)")
    parser.add_argument("--model", type=str, default=None,
                       help="Model to use for predictions (default: deepseek/deepseek-v3.2)")
    parser.add_argument("--models", nargs="+", type=str, default=None,
                       help="Model pool — agents cycle through these models within each ensemble")
    args = parser.parse_args()

    prediction_model = args.model or PREDICTION_MODEL
    model_pool = args.models  # None means single-model mode

    # Configuration
    data_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario")
    output_dir = Path("D:/Northeastern/LLM_Forecasting/experiment_results/multiscenario_forecasting")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build conditions list as (name, strategy, uniform_fraction, scenario_variant)
    if args.test:
        n_scenarios = 3
        n_agents = args.n_agents or 5
        conditions = [
            ("baseline", "none", None, "standard"),
            ("shard_everything", "shard_everything", None, "standard"),
        ]
    else:
        n_scenarios = args.n_scenarios or 100
        n_agents = args.n_agents or 100
        if args.conditions:
            # (strategy, uniform_fraction, scenario_variant)
            condition_map = {
                "baseline":           ("none", None, "standard"),
                "shard_everything":   ("shard_everything", None, "standard"),
                "shard_initial_only": ("shard_initial_only", None, "standard"),
                "leaked_hawkish":     ("none", None, "hawkish"),
                "domain_shard":       ("none", None, "domain_shard"),
                "two_stage":          ("none", None, "two_stage"),
                "debate":             ("none", None, "debate"),
                "reframe":            ("none", None, "reframe"),
            }
            conditions = []
            for name in args.conditions:
                if name == "shard_uniform":
                    for frac in args.uniform_fractions:
                        pct = int(frac * 100)
                        conditions.append((f"shard_uniform_{pct}", "shard_everything", frac, "standard"))
                else:
                    strategy, uf, variant = condition_map[name]
                    conditions.append((name, strategy, uf, variant))
        else:
            conditions = [
                ("baseline", "none", None, "standard"),
                ("shard_everything", "shard_everything", None, "standard"),
                ("shard_initial_only", "shard_initial_only", None, "standard"),
            ]

    print("=" * 70)
    print("MULTI-SCENARIO FORECASTING EXPERIMENT")
    print("=" * 70)
    print(f"Scenarios: {n_scenarios}")
    print(f"Agents per scenario/condition: {n_agents}")
    print(f"Conditions: {[c[0] for c in conditions]}")
    if model_pool:
        print(f"Model pool: {model_pool}")
    else:
        print(f"Model: {prediction_model}")
    if args.test:
        print("[TEST MODE]")
    print("=" * 70)

    # Load data
    print("\nLoading scenario data...")
    scenarios, ground_truth = load_multiscenario_data(data_dir)

    # Merge scenarios with ground truth
    data = scenarios.merge(ground_truth, on='scenario_id', how='inner')

    # Limit to requested number
    if n_scenarios < len(data):
        data = data.head(n_scenarios)
        print(f"Limited to first {n_scenarios} scenarios")

    # Run experiments
    print(f"\nRunning {len(data)} scenarios × {len(conditions)} conditions...")
    all_results = []

    # Set up incremental CSV save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = output_dir / f"experiment_results_{timestamp}.csv"
    agent_results_file = output_dir / f"agent_predictions_{timestamp}.csv"
    csv_header_written = False
    agent_csv_header_written = False

    for idx, row in data.iterrows():
        scenario_id = row['scenario_id']
        print(f"\n[{idx+1}/{len(data)}] {scenario_id}")
        print(f"  Territory: {row['territory_controlled']*100:.1f}% | "
              f"Balance: {row['military_balance']:.2f} | "
              f"Sanctions: {row['sanctions_level']*100:.0f}% | "
              f"Truth: {row['collapse_probability']:.3f}")

        for cond_name, strategy, uf, variant in conditions:
            try:
                result = run_scenario_condition(
                    scenario_id=scenario_id,
                    scenario_params=row,
                    ground_truth=row,
                    condition_name=cond_name,
                    sharding_strategy=strategy,
                    n_agents=n_agents,
                    max_workers=5,
                    model=prediction_model,
                    uniform_fraction=uf,
                    scenario_variant=variant,
                    model_pool=model_pool
                )
                # Extract agent predictions before saving ensemble result
                agent_preds = result.pop('_agent_predictions', [])
                all_results.append(result)

                # Incremental save — ensemble level
                pd.DataFrame([result]).to_csv(
                    results_file, mode='a', index=False,
                    header=not csv_header_written)
                csv_header_written = True

                # Incremental save — agent level
                for pred in agent_preds:
                    agent_row = {
                        'scenario_id': scenario_id,
                        'condition': cond_name,
                        'agent_id': pred.get('agent_id', ''),
                        'model': pred.get('model', ''),
                        'backstory_variant': pred.get('backstory_variant', ''),
                        'domain': pred.get('domain', ''),
                        'probability': pred.get('probability', ''),
                        'ground_truth_probability': row['collapse_probability'],
                    }
                    pd.DataFrame([agent_row]).to_csv(
                        agent_results_file, mode='a', index=False,
                        header=not agent_csv_header_written)
                    agent_csv_header_written = True

                print(f"  {cond_name:<20} Ens: {result['ensemble_probability']:.3f} | "
                      f"SE: {result['squared_error']:.4f} | "
                      f"Fallbacks: {result['fallback_count']}/{n_agents}")

            except Exception as e:
                print(f"  [ERROR] {cond_name} failed: {e}")

    # Final full save (overwrites incremental file to ensure consistency)
    results_df = pd.DataFrame(all_results)
    results_df.to_csv(results_file, index=False)

    # Summary statistics
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}")

    summary = results_df.groupby('condition').agg({
        'squared_error': ['mean', 'std', 'min', 'max'],
        'probability_std': 'mean',
        'fallback_rate': 'mean'
    }).round(4)

    print(summary)

    # Statistical significance tests (paired by scenario)
    condition_names = results_df['condition'].unique()
    if len(condition_names) >= 2:
        from scipy import stats as scipy_stats

        print(f"\n{'='*70}")
        print("STATISTICAL SIGNIFICANCE TESTS")
        print(f"{'='*70}")

        for i in range(len(condition_names)):
            for j in range(i + 1, len(condition_names)):
                c1, c2 = condition_names[i], condition_names[j]
                df1 = results_df[results_df['condition'] == c1].sort_values('scenario_id')
                df2 = results_df[results_df['condition'] == c2].sort_values('scenario_id')

                # Align by scenario
                merged = df1[['scenario_id', 'squared_error']].merge(
                    df2[['scenario_id', 'squared_error']],
                    on='scenario_id', suffixes=(f'_{c1}', f'_{c2}')
                )

                if len(merged) < 3:
                    print(f"\n  {c1} vs {c2}: Too few paired observations ({len(merged)})")
                    continue

                se_1 = merged[f'squared_error_{c1}'].values
                se_2 = merged[f'squared_error_{c2}'].values
                diff = se_1 - se_2

                # Paired t-test
                t_stat, t_pval = scipy_stats.ttest_rel(se_1, se_2)

                # Wilcoxon signed-rank test (non-parametric)
                try:
                    w_stat, w_pval = scipy_stats.wilcoxon(se_1, se_2)
                except ValueError:
                    w_stat, w_pval = float('nan'), float('nan')

                # Effect size (Cohen's d for paired samples)
                d = np.mean(diff) / np.std(diff, ddof=1) if np.std(diff, ddof=1) > 0 else 0

                mean_1 = np.mean(se_1)
                mean_2 = np.mean(se_2)
                pct_change = ((mean_2 - mean_1) / mean_1) * 100 if mean_1 > 0 else 0

                print(f"\n  {c1} vs {c2} (N={len(merged)} paired scenarios)")
                print(f"    Mean SE: {mean_1:.4f} vs {mean_2:.4f} ({pct_change:+.1f}%)")
                print(f"    Paired t-test:   t={t_stat:.3f}, p={t_pval:.4f} {'***' if t_pval < 0.001 else '**' if t_pval < 0.01 else '*' if t_pval < 0.05 else 'ns'}")
                print(f"    Wilcoxon test:   W={w_stat:.1f}, p={w_pval:.4f} {'***' if w_pval < 0.001 else '**' if w_pval < 0.01 else '*' if w_pval < 0.05 else 'ns'}")
                print(f"    Cohen's d:       {d:.3f} ({'large' if abs(d) > 0.8 else 'medium' if abs(d) > 0.5 else 'small' if abs(d) > 0.2 else 'negligible'})")
                print(f"    Scenarios where {c1} better: {np.sum(diff < 0)}/{len(merged)}")
                print(f"    Scenarios where {c2} better: {np.sum(diff > 0)}/{len(merged)}")

    # Save summary
    summary_file = output_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    summary.to_csv(summary_file)

    print(f"\n{'='*70}")
    print(f"EXPERIMENT COMPLETE")
    print(f"Results: {results_file}")
    print(f"Agent predictions: {agent_results_file}")
    print(f"Summary: {summary_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
