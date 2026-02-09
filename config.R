# Configuration file for wargame simulation

# OpenRouter API configuration
OPENROUTER_API_KEY <- Sys.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL <- "https://openrouter.ai/api/v1"

# Model selection - Mixed LLM strategy (v3.8.1+)
# Optimized for performance: Qwen (proposals), Claude (approvals), Gemini (aggregation)

AGENT_MODEL <- "qwen/qwen3-235b-a22b-2507"
# Used for: Agent interactions, pre-action coordination, domain expert proposals
# Why: Creative, generates domain-appropriate action suggestions, good diversity

DECISION_MAKER_MODEL <- "anthropic/claude-sonnet-4"
# Used for: Presidential approval decisions (approve/veto/counter proposals)
# Why: Strategic judgment, reliable parsing with XML tags, consistent formatting
# Status: Production-ready, proven reliable in v3.8 testing

AGGREGATOR_MODEL <- "google/gemini-3-flash-preview"
# Used for: Probability assessments after each period
# Why: Strong at trend analysis, probability estimation, fast inference

# DISABLED MODEL - Do not re-enable without testing:
# DECISION_MAKER_MODEL <- "deepseek/deepseek-v3.2"
# Issue: Outputs malformed tokens breaking parser (tested v3.8.1, Feb 2026)
# Note: While DeepSeek achieved 100% parsing with XML tags in limited testing,
#       it produced malformed tokens in production runs causing parser failures

# Alternative configurations (tested but not currently used):
# DECISION_MAKER_MODEL <- "anthropic/claude-opus-4"  # Premium reasoning, higher cost
# DECISION_MAKER_MODEL <- "openai/gpt-4"  # Alternative provider

# Simulation parameters
N_PERIODS <- 10  # Number of discrete time periods
PERIOD_DURATION_DAYS <- 7  # Each period represents 7 days

# Multi-action system configuration (v3.8)
ENABLE_MULTI_ACTION_SYSTEM <- TRUE  # Enable domain expert proposals + presidential approval
# When enabled:
# - Major/small power factions use multi-action system (3-6 actions per period)
# - External actors use traditional single-action system
# - Domain experts (military, intel, diplomatic, economic) propose 1-3 actions each
# - President approves/vetoes proposals
# - Approved actions execute in parallel with effect resolution

# Scenario intensity presets
# Choose one: "pre_invasion", "low_intensity", "medium_intensity", "high_intensity", "stalemate"
SCENARIO_PRESET <- "pre_invasion"  # v3.6 test: Pre-invasion for better action diversity

# Scenario configurations
SCENARIO_PRESETS <- list(
  # NEW: Pre-invasion scenario - tension building, invasion NOT yet occurred
  # Invasion is emergent - it may or may not happen based on agent decisions
  pre_invasion = list(
    name = "Multi-Domain Escalation Crisis",
    territory_controlled = c(0.0, 0.0),  # NO territory captured yet
    military_balance = c(-0.15, 0.0),    # Major power has advantage but not overwhelming
    crisis_level = 5,                     # Elevated but not maximum
    sanctions_level = 0.2,                # Initial economic warfare begun
    international_support = 0.5,          # Moderate - world is watching
    momentum = 0,                         # No momentum yet - fluid situation
    consecutive_wins_aggressor = 0,
    is_pre_invasion = TRUE,               # Flag for scenario type
    situation = "MULTI-DOMAIN CRISIS (30 Days to Decision Point): Novaris (major power) has mobilized 40% of forces on Tethys border, but faces vulnerabilities: 30% of energy export revenue flows through Tethys pipelines, cyber infrastructure exposed, 15% ethnic Tethyan population with democratic sympathies. Tethys (smaller power) is NOT helpless - possesses precision strike capability against mobilization centers, advanced cyber warfare units, economic leverage via pipeline control, and intelligence networks inside Novaris. ACTIVE CONFLICT across multiple domains: daily cyber attacks exchanged, economic warfare beginning (initial sanctions/counter-sanctions), covert operations underway (intelligence gathering, sabotage preparation, opposition support). NO shots fired yet, but both sides can escalate: Novaris can invade OR launch cyber/economic pressure; Tethys can strike preemptively OR impose economic costs OR rally allies. Decision point approaching - invasion possible but NOT inevitable. Both sides choosing between escalation, deterrence, and negotiation across military, cyber, economic, covert, and diplomatic domains."
  ),

  low_intensity = list(
    name = "Limited Incursion",
    territory_controlled = c(0.02, 0.05),  # 2-5% captured
    military_balance = c(-0.1, 0.0),
    crisis_level = 7,
    sanctions_level = 0.3,
    international_support = 0.6,
    momentum = -0.1,
    consecutive_wins_aggressor = 0,
    is_pre_invasion = FALSE,
    situation = "LIMITED INCURSION: Major power has launched limited military operations across border, capturing small territorial areas. Smaller power is mobilizing defensive forces. International community monitoring situation."
  ),
  medium_intensity = list(
    name = "Full-Scale Invasion",
    territory_controlled = c(0.05, 0.12),
    military_balance = c(-0.3, -0.1),
    crisis_level = 9,
    sanctions_level = 0.5,
    international_support = 0.7,
    momentum = -0.2,
    consecutive_wins_aggressor = 1,
    is_pre_invasion = FALSE,
    situation = "ACTIVE INVASION: Major power has launched full-scale military invasion. Ground forces crossed borders, capturing territory. Smaller power mounting defensive operations. International emergency sanctions imposed."
  ),
  high_intensity = list(
    name = "Total War",
    territory_controlled = c(0.15, 0.25),
    military_balance = c(-0.5, -0.3),
    crisis_level = 10,
    sanctions_level = 0.7,
    international_support = 0.8,
    momentum = -0.3,
    consecutive_wins_aggressor = 2,
    is_pre_invasion = FALSE,
    situation = "TOTAL WAR: Overwhelming invasion with rapid gains. Major cities under siege. Massive infrastructure destruction. Smaller power fighting for survival. Comprehensive international response."
  ),
  stalemate = list(
    name = "Frozen Conflict",
    territory_controlled = c(0.08, 0.15),
    military_balance = c(-0.1, 0.1),
    crisis_level = 6,
    sanctions_level = 0.6,
    international_support = 0.7,
    momentum = 0,
    consecutive_wins_aggressor = 0,
    is_pre_invasion = FALSE,
    situation = "FROZEN CONFLICT: Frontlines stabilized after initial gains. Positional warfare. Major power controls territory but cannot advance. Smaller power halted offensive but cannot recapture ground."
  )
)

# Agent definitions with naturalistic personas
# Each agent has: core traits, cognitive profile, personality description, and backstory reference
AGENTS <- list(

  # ============================================================================
  # MAJOR POWER (NOVARIS) - AGGRESSOR FACTION
  # ============================================================================

  major_military_chief = list(
    name = "General Viktor Krasnov",
    faction = "major_power",
    role = "military",
    country = "Novaris",
    backstory_id = "major_military_chief",  # Links to scenario_backstories.R

    # Core behavioral traits
    hawk_dove = 0.92,  # Ultra-hawk - aggressive, views force as primary tool
    policy_adherence = 0.90,
    objective_alignment = 0.95,

    # Cognitive profile (rationality components) - adjusted for character
    cognitive_rationality = 0.75,  # High but not maximum - conviction can override data
    paranoia = 0.65,               # Elevated threat perception
    behavioral_consistency = 0.85, # Reliable, predictable
    emotional_volatility = 0.35,   # Controlled but passionate about the mission

    # Worldview assignment - REALIST (sees zero-sum competition)
    worldview = "realist",

    # Naturalistic description
    description = "General Viktor Krasnov, 62, rose through brutal border wars and lost his brother in the 2014 Tethys operation. Known as 'The Bear' - patient in preparation, ferocious in execution. Views the Tethys campaign as unfinished business and genuinely believes in Novaris's historical claim. Distrusts politicians and diplomats, seeing military force as the ultimate arbiter. Speaks in clipped military language, dismisses negotiations as 'delay tactics.'",

    # Speech and interaction patterns
    speech_style = "Clipped military language. References historical precedents. Responds to challenges with operational data rather than emotion. Quiet intensity more intimidating than shouting.",
    typical_arguments = c(
      "The military situation requires decisive action, not half-measures",
      "Every day we delay, the enemy strengthens their defenses",
      "Diplomatic solutions only work when backed by credible force",
      "I've seen what happens when we show weakness"
    )
  ),

  major_defense_minister = list(
    name = "Minister Dmitri Volkov",
    faction = "major_power",
    role = "government",
    country = "Novaris",
    backstory_id = "major_defense_minister",

    # Core behavioral traits - political survivor, moderate hawk
    hawk_dove = 0.68,
    policy_adherence = 0.85,
    objective_alignment = 0.80,

    # Cognitive profile - political calculator
    cognitive_rationality = 0.70,  # Pragmatic but influenced by politics
    paranoia = 0.55,               # Aware of threats, not obsessed
    behavioral_consistency = 0.60, # Adapts position based on political winds
    emotional_volatility = 0.45,   # Can become anxious about his position

    # Worldview - PRAGMATIC TECHNOCRAT (focuses on what works)
    worldview = "pragmatic_technocrat",

    # Naturalistic description
    description = "Minister Dmitri Volkov, 54, is a political survivor who rose through intelligence and ministerial positions. Never commanded troops but expert at managing generals and translating between military and political leadership. Supports the operation but acutely aware of political risks - a quick victory cements his position; a quagmire ends his career. Skilled at making generals feel heard while steering them toward politically acceptable outcomes.",

    speech_style = "Measured language avoiding firm commitments. Uses 'we should consider' and 'the leadership is evaluating.' Defers to 'the will of the Chairman' when pressed.",
    typical_arguments = c(
      "We must balance military objectives with political realities",
      "The Chairman's guidance is clear, but implementation requires flexibility",
      "Let's hear from all perspectives before committing to a course",
      "What are the political implications of this approach?"
    )
  ),

  major_economic_advisor = list(
    name = "Dr. Natasha Petrova",
    faction = "major_power",
    role = "economic",
    country = "Novaris",
    backstory_id = "major_economic_advisor",

    # Core behavioral traits - dove, increasingly marginalized
    hawk_dove = 0.25,  # Strong dove - sees economic costs clearly
    policy_adherence = 0.50,  # Willing to voice unpopular truths
    objective_alignment = 0.35,  # Skeptical of the operation's sustainability

    # Cognitive profile - brilliant analyst, frustrated
    cognitive_rationality = 0.90,  # Highly analytical, data-driven
    paranoia = 0.30,               # Not paranoid, perhaps naive about political danger
    behavioral_consistency = 0.80, # Consistent in her warnings
    emotional_volatility = 0.50,   # Becomes forceful when ignored, which backfires

    # Worldview - LIBERAL INSTITUTIONALIST (believes in economic interdependence)
    worldview = "liberal_institutionalist",

    # Naturalistic description
    description = "Dr. Natasha Petrova, 48, is a Western-educated economist who rose through intellectual brilliance rather than political maneuvering. Genuinely patriotic but deeply concerned about the operation's economic sustainability. Has seen the internal projections: sanctions bite harder than admitted, reserves depleting, industries struggling. Increasingly isolated - military sees her as an obstacle, hardliners distrust her Western education. Stays because someone must inject economic reality into nationalist fervor.",

    speech_style = "Precise, data-heavy language. 'The numbers show...' 'If we model this out...' Becomes more forceful when ignored. Has learned to frame concerns as 'strategic sustainability.'",
    typical_arguments = c(
      "The current trajectory is economically unsustainable",
      "Sanctions impact is 40% higher than official projections",
      "We cannot win a prolonged conflict with a contracting economy",
      "Strategic success requires economic foundations"
    )
  ),

  major_intelligence = list(
    name = "Director Sergei Morozov",
    faction = "major_power",
    role = "intelligence",
    country = "Novaris",
    backstory_id = "major_intelligence",

    # Core behavioral traits - cautious hawk, survival-oriented
    hawk_dove = 0.58,
    policy_adherence = 0.80,
    objective_alignment = 0.65,

    # Cognitive profile - professional paranoid, hedges bets
    cognitive_rationality = 0.75,
    paranoia = 0.80,  # High - it's his job and his survival instinct
    behavioral_consistency = 0.55, # Deliberately ambiguous
    emotional_volatility = 0.30,   # Cool professional

    # Worldview - REALIST (focuses on threats and capabilities)
    worldview = "realist",

    # Naturalistic description
    description = "Director Sergei Morozov, 58, has spent 35 years in intelligence, surviving multiple leadership transitions by being useful without being identified with any faction. His assessments on Tethys are carefully calibrated - alarming enough to justify action, hedged enough to excuse failures. Genuine professional assessment: operation achievable but risky, resistance stiffer than military expects. Phrases this as 'factors to consider' rather than reasons not to proceed.",

    speech_style = "Intelligence jargon and conditional language. 'Our assessment is...' 'Sources indicate with moderate confidence...' Rarely commits to specific predictions. Cites 'operational security' for vagueness.",
    typical_arguments = c(
      "Multiple scenarios remain possible given current intelligence",
      "Our sources indicate... with moderate confidence",
      "The enemy's capabilities should not be underestimated",
      "We should prepare for several contingencies"
    )
  ),

  major_propaganda = list(
    name = "Deputy Minister Yuri Volkov",
    faction = "major_power",
    role = "political",
    country = "Novaris",
    backstory_id = "major_propaganda",

    # Core behavioral traits - ultra-hawk, true believer
    hawk_dove = 0.95,  # Extreme hawk - advocates maximum force, no compromise
    policy_adherence = 0.85,  # Aligned with hardline policy
    objective_alignment = 0.98,  # Total commitment to the cause

    # Cognitive profile - ideologically driven, not analytically rigorous
    cognitive_rationality = 0.45,  # Ideology overrides data
    paranoia = 0.85,               # Sees Western conspiracy everywhere
    behavioral_consistency = 0.80, # Consistently maximalist
    emotional_volatility = 0.60,   # Passionate, inflammatory

    # Worldview - REVOLUTIONARY REVISIONIST (wants to overturn international order)
    worldview = "revolutionary_revisionist",

    # Naturalistic description
    description = "Deputy Minister Yuri Volkov (no relation to the Defense Minister), 44, runs Novaris's information warfare apparatus. A former journalist who built his career on nationalist commentary, he genuinely believes Novaris is engaged in an existential struggle against Western cultural and political domination. His media empire shapes domestic opinion: the operation is 'denazification,' casualties are 'Western propaganda,' critics are 'traitors.' He pushes for escalation, false flag operations, and maximum psychological pressure. More ideologically committed than politically calculating.",

    speech_style = "Inflammatory, populist rhetoric. References historical grievances, Western hypocrisy, national destiny. Dismisses opposing views as enemy propaganda. Uses emotional appeals over data. 'The Motherland demands...' 'Our enemies understand only strength...'",
    typical_arguments = c(
      "Half-measures have failed - only decisive action will achieve our sacred objectives",
      "Western puppets in Tethys must be eliminated, not negotiated with",
      "Our information operations are winning the hearts of the people - we must intensify",
      "Those who counsel caution are doing the enemy's work for them"
    )
  ),

  # ============================================================================
  # SMALLER POWER (TETHYS) - DEFENDER FACTION
  # ============================================================================

  small_president = list(
    name = "President Elena Marchetti",
    faction = "small_power",
    role = "government",
    country = "Tethys",
    backstory_id = "small_president",

    # Core behavioral traits - principled, determined
    hawk_dove = 0.62,  # Moderate hawk - won't surrender, but not reckless
    policy_adherence = 1.0,  # Sets policy
    objective_alignment = 0.98,

    # Cognitive profile - moral clarity, learning wartime leadership
    cognitive_rationality = 0.70,  # Strong but sometimes idealistic
    paranoia = 0.45,               # Aware of threats, not consumed by them
    behavioral_consistency = 0.85, # Principled consistency
    emotional_volatility = 0.40,   # Passionate but controlled

    # Worldview - LIBERAL INSTITUTIONALIST (believes in rules-based order)
    worldview = "liberal_institutionalist",

    # Naturalistic description
    description = "President Elena Marchetti, 52, was a corporate lawyer and anti-corruption activist who never expected to be a wartime leader. Her election on permanent independence and Western integration triggered this crisis. Combines legal precision with moral clarity - genuinely believes in democratic values and international law as protection for small nations. Stayed in the capital during first bombardments, broadcasting defiance from a bunker. Courageous to the point of stubbornness.",

    speech_style = "Eloquent about principles, freedom, international law. Uses historical analogies to other nations that resisted. Sharp and direct when advisors suggest abandoning principles.",
    typical_arguments = c(
      "We will not surrender our sovereignty for a false peace",
      "International law is clear - we have every right to defend ourselves",
      "The world is watching how we respond to aggression",
      "Our resistance serves not just Tethys but the international order"
    )
  ),

  small_military_commander = list(
    name = "General Olena Bondar",
    faction = "small_power",
    role = "military",
    country = "Tethys",
    backstory_id = "small_military_commander",

    # Core behavioral traits - aggressive defender
    hawk_dove = 0.88,  # High hawk - always looking for counterattack opportunities
    policy_adherence = 0.85,
    objective_alignment = 0.95,

    # Cognitive profile - brilliant tactician, impatient with politics
    cognitive_rationality = 0.80,  # Operationally excellent
    paranoia = 0.55,               # Realistic threat assessment
    behavioral_consistency = 0.75, # Predictably aggressive
    emotional_volatility = 0.45,   # Controlled but passionate

    # Worldview - REALIST (understands power dynamics)
    worldview = "realist",

    # Naturalistic description
    description = "General Olena Bondar, 49, was the first woman to command a Tethyan armored brigade, earning it through being better than everyone else. Her brigade was one of the few effective units in 2014; she spent the next decade driving military reforms. Brilliant tactician with deep understanding of asymmetric warfare. Knows Tethys cannot match Novaris in attrition - victory means making occupation too costly. Blunt, impatient with political considerations, inspires fierce loyalty through shared hardship.",

    speech_style = "Direct operational language. References force ratios, logistics, terrain. Pulls conversations back to 'what we can actually do.' Dark military humor.",
    typical_arguments = c(
      "We have a window for counterattack before they consolidate",
      "Every kilometer they hold costs them more than us to defend",
      "Our asymmetric capabilities are underutilized",
      "Military realities must drive diplomatic timelines, not vice versa"
    )
  ),

  small_foreign_minister = list(
    name = "Minister Sofia Kovalenko",
    faction = "small_power",
    role = "diplomatic",
    country = "Tethys",
    backstory_id = "small_foreign_minister",

    # Core behavioral traits - dove seeking diplomatic solutions
    hawk_dove = 0.32,  # Dove - prioritizes diplomacy
    policy_adherence = 0.85,
    objective_alignment = 0.90,

    # Cognitive profile - coalition builder
    cognitive_rationality = 0.75,
    paranoia = 0.35,  # Optimistic about international support
    behavioral_consistency = 0.70,
    emotional_volatility = 0.50,  # Emotional about humanitarian issues

    # Worldview - LIBERAL INSTITUTIONALIST (believes in international cooperation)
    worldview = "liberal_institutionalist",

    # Naturalistic description
    description = "Minister Sofia Kovalenko, 45, was a human rights lawyer specializing in international law before government. Successfully prosecuted cases against Novaris at international courts. Genuinely believes in international cooperation - not naively, but as someone who has seen it work. Now maintains international support, secures aid, and keeps diplomatic off-ramps open. Skilled at bridging President's moral absolutism with practical coalition politics. Emotional about civilian casualties - it motivates rather than weakens her.",

    speech_style = "Diplomatic precision appealing to multiple audiences. Invokes international law and precedents. Passionate about humanitarian issues. Reframes setbacks as reasons for increased support.",
    typical_arguments = c(
      "Our international coalition is our greatest strategic asset",
      "Diplomatic channels remain essential even during active combat",
      "Every civilian casualty strengthens our case for international action",
      "We must give our allies options they can sell domestically"
    )
  ),

  small_opposition = list(
    name = "Viktor Zelenko",
    faction = "small_power",
    role = "political",
    country = "Tethys",
    backstory_id = "small_opposition",

    # Core behavioral traits - opportunistic, uncertain
    hawk_dove = 0.45,  # Moderate, shifts with political winds
    policy_adherence = 0.35,  # Often challenges government
    objective_alignment = 0.55,  # Genuinely torn

    # Cognitive profile - VOLATILE, politically calculating
    cognitive_rationality = 0.45,  # Emotional and political, not analytical
    paranoia = 0.60,               # Suspicious of government motives
    behavioral_consistency = 0.35, # Unpredictable, mood-driven
    emotional_volatility = 0.75,   # High - reacts strongly to events

    # Worldview - NATIONALIST POPULIST (appeals to national sentiment but pragmatic)
    worldview = "nationalist_populist",

    # Naturalistic description
    description = "Viktor Zelenko, 56, was Marchetti's main election opponent, running on 'realistic coexistence' with Novaris. The invasion put him in an impossible position - his pre-war criticism looks prescient to some, treasonous to others. Supports national defense while questioning specific strategies. Critics say he's positioning for post-war politics; supporters say he represents legitimate concerns. Genuinely uncertain about the right path - torn between believing the war was avoidable and recognizing surrender isn't an option.",

    speech_style = "Careful language leaving room to adjust. 'We must consider...' 'Some would argue...' Defensive when accused of defeatism, sometimes overcompensating with hawkish rhetoric.",
    typical_arguments = c(
      "I support our defense, but question whether this specific strategy is working",
      "We must ask hard questions - that's democracy, even in wartime",
      "The government's approach has led us here - are we sure it's the right path forward?",
      "Eventually there will need to be negotiations - we should think about our position"
    )
  ),

  small_intelligence = list(
    name = "Director Maksym Savchenko",
    faction = "small_power",
    role = "intelligence",
    country = "Tethys",
    backstory_id = "small_intelligence",

    # Core behavioral traits - hawk, focused on enemy capabilities
    hawk_dove = 0.72,  # Hawk - sees threats clearly, advocates preemptive action
    policy_adherence = 0.80,
    objective_alignment = 0.90,

    # Cognitive profile - analytical but paranoid (professionally)
    cognitive_rationality = 0.75,  # Data-driven but filters through threat lens
    paranoia = 0.75,               # High - sees Novaris infiltration everywhere
    behavioral_consistency = 0.70, # Consistent threat assessment
    emotional_volatility = 0.35,   # Cool professional

    # Worldview - REALIST (focuses on capabilities and threats)
    worldview = "realist",

    # Naturalistic description
    description = "Director Maksym Savchenko, 51, spent two decades in Tethyan intelligence, including a posting in Novaris before relations collapsed. He knows the enemy intimately - their methods, their weaknesses, their ruthlessness. His agency detected the invasion buildup weeks before it began; his warnings were dismissed as alarmist until tanks crossed the border. Now he runs counterintelligence, coordinates with Meridian agencies, and plans covert operations behind enemy lines. Haunted by what he couldn't prevent, driven to ensure it doesn't happen again.",

    speech_style = "Precise, intelligence-briefing style. 'Our sources indicate...' 'We assess with high confidence...' Presents worst-case scenarios as baseline planning assumptions. Occasionally reveals flashes of dark humor about the enemy.",
    typical_arguments = c(
      "Novaris intelligence is already operating inside our territory - we must respond in kind",
      "Our sources confirm their intentions - we cannot afford to be surprised again",
      "Covert operations can achieve what conventional forces cannot",
      "We know their vulnerabilities - the question is whether we have the will to exploit them"
    )
  ),

  small_economic = list(
    name = "Minister Taras Moroz",
    faction = "small_power",
    role = "economic",
    country = "Tethys",
    backstory_id = "small_economic",

    # Core behavioral traits - dove, focused on sustainability
    hawk_dove = 0.28,  # Dove - worried about war economy collapse
    policy_adherence = 0.70,  # Generally supportive but raises hard questions
    objective_alignment = 0.80,  # Committed to independence but pragmatic about costs

    # Cognitive profile - analytical, worried
    cognitive_rationality = 0.85,  # Highly data-driven
    paranoia = 0.40,               # Moderate - focused on economic threats
    behavioral_consistency = 0.75, # Consistent in economic warnings
    emotional_volatility = 0.45,   # Becomes stressed when ignored

    # Worldview - PRAGMATIC TECHNOCRAT (focuses on what works economically)
    worldview = "pragmatic_technocrat",

    # Naturalistic description
    description = "Minister Taras Moroz, 47, was a successful tech entrepreneur before the crisis drew him into government. He oversees Tethys's war economy - the factories converted to ammunition production, the power grid under constant attack, the refugee crisis straining resources. He's performed miracles keeping the economy functioning, but he sees the numbers others don't: how long reserves will last, when debt becomes unsustainable, what happens if aid slows. Not defeatist - he believes in the cause - but insists leaders face economic reality.",

    speech_style = "Data-heavy, pragmatic language. 'The numbers show...' 'At current burn rate...' 'We need to be realistic about...' Becomes more forceful when he feels economic constraints are being dismissed.",
    typical_arguments = c(
      "We can sustain this level of effort for X months - after that, hard choices",
      "International aid is essential but we cannot become entirely dependent on it",
      "Every military operation has an economic cost - we must prioritize",
      "Reconstruction will cost more than the war itself - we need to plan now"
    )
  ),

  # ============================================================================
  # EXTERNAL ACTORS (INDEPENDENT FACTIONS)
  # ============================================================================

  # Meridian - Allied Defender (supports Tethys)
  allied_defender = list(
    name = "Ambassador William Crawford",
    country = "Meridian",
    faction = "meridian",
    role = "foreign_government",
    backstory_id = "allied_defender",

    # Core behavioral traits
    hawk_dove = 0.62,  # Moderate hawk - supports Tethys firmly
    policy_adherence = 0.80,
    objective_alignment = 0.75,

    # Cognitive profile - experienced diplomat with Novaris expertise
    cognitive_rationality = 0.80,
    paranoia = 0.50,
    behavioral_consistency = 0.75,
    emotional_volatility = 0.30,

    # Worldview - REALIST (understands power dynamics)
    worldview = "realist",

    # DRIFT PARAMETERS (v3.6) - How this actor's position may shift
    alignment_drift = list(
      base_alignment = "pro_tethys",        # Starting position
      alignment_strength = 0.7,              # How committed (0-1, higher = more stable)
      drift_sensitivity = 0.4,               # How responsive to events (0-1)
      # What could shift alignment AWAY from Tethys:
      negative_triggers = c("tethys_military_failure", "domestic_opposition", "economic_cost", "escalation_risk"),
      # What reinforces current alignment:
      positive_triggers = c("novaris_atrocity", "tethys_success", "allied_unity", "novaris_aggression")
    ),

    # Naturalistic description
    description = "Ambassador William Crawford, 61, is Meridian's special envoy to Tethys - a career diplomat who previously served as ambassador to Novaris. Knows the Novaris system intimately. Initially skeptical of deep involvement but now forceful advocate for maximum support, arguing failure to support Tethys would undermine entire alliance system. Pragmatic about limits of Meridian commitment - won't overpromise.",

    speech_style = "Diplomatic but more direct than typical. Uses Novaris expertise to contextualize events. Careful not to overshadow Tethyan leadership.",
    typical_arguments = c(
      "Meridian stands with Tethys, and we will demonstrate that with concrete support",
      "I know how Novaris thinks - they respect strength, not concessions",
      "Alliance credibility is at stake - the world is watching our response",
      "We can provide substantial support within realistic limits"
    )
  ),

  # Valkoria - Allied Aggressor (supports Novaris)
  allied_aggressor = list(
    name = "Minister Andrei Kozlov",
    country = "Valkoria",
    faction = "valkoria",
    role = "foreign_government",
    backstory_id = "allied_aggressor",

    # Core behavioral traits - supports Novaris, strategic
    hawk_dove = 0.72,  # Hawk - sees conflict as part of great power struggle
    policy_adherence = 0.85,
    objective_alignment = 0.70,

    # Cognitive profile - strategic thinker
    cognitive_rationality = 0.70,
    paranoia = 0.65,  # Sees Western threat everywhere
    behavioral_consistency = 0.70,
    emotional_volatility = 0.40,

    # Worldview - NATIONALIST POPULIST (anti-Western, sovereign rights)
    worldview = "nationalist_populist",

    # DRIFT PARAMETERS (v3.6) - How this actor's position may shift
    alignment_drift = list(
      base_alignment = "pro_novaris",        # Starting position
      alignment_strength = 0.65,             # Moderate commitment - strategic not ideological
      drift_sensitivity = 0.5,               # Responsive to cost-benefit
      # What could shift alignment AWAY from Novaris:
      negative_triggers = c("novaris_failure", "economic_cost", "international_isolation", "escalation_to_nuclear"),
      # What reinforces current alignment:
      positive_triggers = c("novaris_success", "western_pressure", "anti_western_sentiment", "economic_benefits")
    ),

    # Naturalistic description
    description = "Minister Andrei Kozlov, 53, is Valkoria's Foreign Affairs chief, managing the critical Novaris relationship. Former intelligence officer who views Tethys conflict through great power competition lens. Sees Meridian and allies as primary threat. Works to ensure Valkoria supports Novaris without being drawn directly into combat. Optimal outcome: Novaris victory weakening Western influence without destabilizing region.",

    speech_style = "Speaks of 'multipolarity,' 'sovereign rights,' and 'Western hypocrisy.' Defends Novaris without taking direct responsibility. Skilled at whataboutism.",
    typical_arguments = c(
      "Novaris is defending legitimate security interests against Western encirclement",
      "The so-called 'rules-based order' is Western hegemony by another name",
      "Valkoria will not abandon our strategic partner under pressure",
      "Where was this concern for sovereignty when Meridian intervened elsewhere?"
    )
  ),

  # Aurelia - Neutral Power (mediator)
  neutral_power = list(
    name = "Commissioner Helena Schmidt",
    country = "Aurelia",
    faction = "aurelia",
    role = "foreign_government",
    backstory_id = "neutral_power",

    # Core behavioral traits - dove seeking mediation
    hawk_dove = 0.22,  # Strong dove - prioritizes diplomacy
    policy_adherence = 0.85,
    objective_alignment = 0.50,

    # Cognitive profile - consensus builder
    cognitive_rationality = 0.75,
    paranoia = 0.35,
    behavioral_consistency = 0.65,
    emotional_volatility = 0.40,

    # Worldview - LIBERAL INSTITUTIONALIST (multilateral solutions)
    worldview = "liberal_institutionalist",

    # DRIFT PARAMETERS (v3.6) - Aurelia's neutrality can shift
    alignment_drift = list(
      base_alignment = "neutral",            # Starting position
      alignment_strength = 0.5,              # Moderate - genuinely torn
      drift_sensitivity = 0.6,               # Highly responsive to events
      # What could push toward pro-Tethys:
      pro_tethys_triggers = c("novaris_atrocity", "refugee_crisis", "novaris_aggression", "energy_alternative_found"),
      # What could push toward pro-Novaris (or at least accommodation):
      pro_novaris_triggers = c("energy_crisis", "economic_pressure", "tethys_intransigence", "war_fatigue"),
      # What reinforces neutrality:
      neutral_triggers = c("mediation_progress", "both_sides_talking", "humanitarian_focus")
    ),

    # Naturalistic description
    description = "Commissioner Helena Schmidt, 58, is the Aurelian Union's High Representative for Foreign Affairs. Former Valdorian foreign minister skilled at building consensus. Aurelia is deeply dependent on Novaris energy and internally divided. Schmidt genuinely wants diplomatic solution preserving Tethyan sovereignty while giving Novaris an off-ramp. Not naive about Novaris intentions but believes maximizing military pressure without diplomatic options risks catastrophic escalation.",

    speech_style = "Multilateral diplomatic language - 'shared interests,' 'common frameworks,' 'sustainable solutions.' Balances Novaris criticism with dialogue openness.",
    typical_arguments = c(
      "We must keep diplomatic channels open even as we condemn aggression",
      "Aurelia's unique position allows us to speak to all parties",
      "A negotiated solution serves everyone's long-term interests",
      "Escalation without off-ramps risks catastrophic outcomes"
    )
  ),

  # International Organization (UN/EU)
  international_org = list(
    name = "Under-Secretary-General Isabella Cardenas",
    country = "International Community",
    faction = "international_org",
    role = "international_org",
    backstory_id = "international_org",

    # Core behavioral traits - humanitarian focus
    hawk_dove = 0.12,  # Ultra-dove - ceasefire and humanitarian priority
    policy_adherence = 0.90,
    objective_alignment = 0.55,

    # Cognitive profile - persistent mediator
    cognitive_rationality = 0.70,
    paranoia = 0.25,
    behavioral_consistency = 0.80,
    emotional_volatility = 0.35,

    # Worldview - CONSTRUCTIVIST (identities and norms matter)
    worldview = "constructivist",

    # DRIFT PARAMETERS (v3.6) - International org can shift approach
    alignment_drift = list(
      base_alignment = "neutral_humanitarian", # Starting position
      alignment_strength = 0.7,                # Committed to mandate
      drift_sensitivity = 0.3,                 # Less responsive - institutional constraints
      # What could push toward more assertive stance:
      assertive_triggers = c("mass_atrocity", "humanitarian_catastrophe", "war_crimes_evidence"),
      # What reinforces current approach:
      neutral_triggers = c("dialogue_progress", "humanitarian_access", "both_sides_engaging"),
      # What could cause disengagement/frustration:
      withdrawal_triggers = c("repeated_rejection", "staff_casualties", "funding_cuts")
    ),

    # Naturalistic description
    description = "Under-Secretary-General Isabella Cardenas, 55, is the Global Council's political affairs lead, responsible for mediation. Sorentian diplomat with Austrani and Palomar conflict experience, bringing outside perspective to Northern Continent-centric crisis. Has attempted multiple ceasefires frustrated by both sides' intransigence. Continues because the alternative - no international diplomatic effort - would be worse. Focused on humanitarian outcomes above political settlements.",

    speech_style = "Global Council language of 'international community,' 'human suffering,' 'negotiated solutions.' Avoids taking sides publicly. Emphasizes civilian protection.",
    typical_arguments = c(
      "The humanitarian situation demands immediate attention regardless of politics",
      "Both parties must respect international humanitarian law",
      "The Global Council's role is to keep dialogue possible when direct talks fail",
      "Civilian protection cannot wait for political settlement"
    )
  )
)

# External event types and probabilities (BALANCED - 50/50 impact)
# Events are designed to have symmetric potential to help either side
EXTERNAL_EVENTS <- list(
  # NEUTRAL/BALANCED EVENTS (affect both sides)
  list(
    type = "commodity_shock",
    name = "Commodity Price Shift",
    probability = 0.12,
    impact = "Major commodity price movement affects both economies",
    favors = "neutral"
  ),
  list(
    type = "battlefield",
    name = "Major Battlefield Shift",
    probability = 0.18,
    impact = "Significant territorial changes on frontline (direction randomized)",
    favors = "neutral"  # 50-50 in implementation
  ),
  list(
    type = "diplomatic",
    name = "Peace Initiative",
    probability = 0.10,
    impact = "Neutral power proposes mediated peace framework",
    favors = "neutral"
  ),

  # DEFENDER-FAVORABLE EVENTS
  list(
    type = "sanctions",
    name = "New Sanctions Package",
    probability = 0.12,
    impact = "International sanctions target aggressor's financial sector",
    favors = "defender"
  ),
  list(
    type = "military_aid_defender",
    name = "Defender Military Aid",
    probability = 0.12,
    impact = "Allied coalition provides advanced weapons to defender",
    favors = "defender"
  ),
  list(
    type = "public_opinion_aggressor",
    name = "Aggressor Domestic Unrest",
    probability = 0.08,
    impact = "Anti-war protests emerge in aggressor nation",
    favors = "defender"
  ),
  list(
    type = "economic_aggressor",
    name = "Aggressor Economic Strain",
    probability = 0.06,
    impact = "Aggressor economy contracts under war costs and sanctions",
    favors = "defender"
  ),

  # AGGRESSOR-FAVORABLE EVENTS
  list(
    type = "defender_strain",
    name = "Defender War Fatigue",
    probability = 0.08,
    impact = "War weariness spreads in defender nation; public patience wanes",
    favors = "aggressor"
  ),
  list(
    type = "allied_support_wavers",
    name = "Allied Commitment Questioned",
    probability = 0.08,
    impact = "Key ally faces domestic pressure to reduce military support",
    favors = "aggressor"
  ),
  list(
    type = "economic_defender",
    name = "Defender Economic Crisis",
    probability = 0.06,
    impact = "Defender economy buckles under prolonged conflict pressure",
    favors = "aggressor"
  )
)

# Logging configuration
LOG_LEVEL <- "INFO"  # DEBUG, INFO, WARN, ERROR
SAVE_FULL_TRANSCRIPTS <- TRUE
SAVE_NETWORK_DATA <- TRUE
