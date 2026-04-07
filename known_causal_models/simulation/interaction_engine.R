# Interaction engine - manages agent-to-agent communications

library(uuid)

#' Safely sample one agent from a list
#' Handles the R quirk where sample() on a length-1 list behaves unexpectedly
#'
#' @param agent_list List of agents
#' @return Single agent (list element)
safe_sample_agent <- function(agent_list) {
  if (length(agent_list) == 1) {
    return(agent_list[[1]])
  } else {
    return(agent_list[[sample(length(agent_list), 1)]])
  }
}

#' Create an interaction session for agents
#'
#' @param period Integer period number
#' @param agents List of agent objects
#' @param context Scenario context
#' @return List containing interaction session data
create_interaction_session <- function(period, agents, context) {
  list(
    period = period,
    session_id = UUIDgenerate(),
    start_time = Sys.time(),
    agents = agents,
    context = context,
    interactions = list(),
    interaction_count = 0
  )
}

#' Generate interaction scenarios for agents
#'
#' @param session Interaction session object
#' @return List of interaction scenarios
generate_interaction_scenarios <- function(session) {
  scenarios <- list()

  # Intra-faction coordination (within same faction)
  factions <- unique(sapply(session$agents, function(a) a$faction))

  for (faction in factions) {
    faction_agents <- Filter(function(a) a$faction == faction, session$agents)
    if (length(faction_agents) >= 2) {
      scenarios <- c(scenarios, list(list(
        type = "intra_faction_coordination",
        faction = faction,
        participants = faction_agents,
        topic = generate_intra_faction_topic(faction, session$context)
      )))
    }
  }

  # Inter-faction negotiations (across factions)
  # Major power vs Smaller power
  major_agents <- Filter(function(a) a$faction == "major_power", session$agents)
  small_agents <- Filter(function(a) a$faction == "small_power", session$agents)

  if (length(major_agents) > 0 && length(small_agents) > 0) {
    scenarios <- c(scenarios, list(list(
      type = "inter_faction_negotiation",
      factions = c("major_power", "small_power"),
      participants = list(safe_sample_agent(major_agents), safe_sample_agent(small_agents)),
      topic = generate_negotiation_topic(session$context)
    )))
  }

  # External actor engagement (now independent actors)
  # Meridian (supports Tethys), Valkoria (supports Novaris), Aurelia (neutral), Int'l Org
  meridian_agents <- Filter(function(a) a$faction == "meridian", session$agents)
  valkoria_agents <- Filter(function(a) a$faction == "valkoria", session$agents)
  aurelia_agents <- Filter(function(a) a$faction == "aurelia", session$agents)
  intl_org_agents <- Filter(function(a) a$faction == "international_org", session$agents)

  # Meridian speaks with Tethys (their ally)
  if (length(meridian_agents) > 0 && length(small_agents) > 0) {
    scenarios <- c(scenarios, list(list(
      type = "external_engagement",
      factions = c("meridian", "small_power"),
      participants = list(meridian_agents[[1]], safe_sample_agent(small_agents)),
      topic = "Coordination on military aid and support for Tethys"
    )))
  }

  # Valkoria speaks with Novaris (their ally) - GUARANTEED
  if (length(valkoria_agents) > 0 && length(major_agents) > 0) {
    scenarios <- c(scenarios, list(list(
      type = "external_engagement",
      factions = c("valkoria", "major_power"),
      participants = list(valkoria_agents[[1]], safe_sample_agent(major_agents)),
      topic = "Diplomatic coordination and economic support for Novaris"
    )))
  }

  # Aurelia mediates between major and small power - GUARANTEED
  if (length(aurelia_agents) > 0) {
    # Aurelia engages with both sides for mediation
    if (length(small_agents) > 0) {
      scenarios <- c(scenarios, list(list(
        type = "external_engagement",
        factions = c("aurelia", "small_power"),
        participants = list(aurelia_agents[[1]], safe_sample_agent(small_agents)),
        topic = "Mediation proposal and peace framework discussions"
      )))
    }
  }

  # International Org engages with combatants on humanitarian issues - GUARANTEED
  if (length(intl_org_agents) > 0) {
    # Int'l Org engages with both sides on humanitarian concerns
    target_faction <- sample(c("major_power", "small_power"), 1)
    target_agents <- if (target_faction == "major_power") major_agents else small_agents
    if (length(target_agents) > 0) {
      scenarios <- c(scenarios, list(list(
        type = "external_engagement",
        factions = c("international_org", target_faction),
        participants = list(intl_org_agents[[1]], safe_sample_agent(target_agents)),
        topic = "Humanitarian access and civilian protection"
      )))
    }
  }

  return(scenarios)
}

#' Generate topic for intra-faction coordination
#'
#' @param faction Faction name
#' @param context Scenario context
#' @return Character string with topic
generate_intra_faction_topic <- function(faction, context) {
  if (faction == "major_power") {
    topics <- c(
      "Review military strategy and assess progress toward objectives",
      "Discuss economic costs of the operation and resource allocation",
      "Coordinate response to recent international sanctions",
      "Evaluate intelligence reports on smaller power's capabilities",
      "Debate whether to escalate or consolidate current positions"
    )
  } else if (faction == "small_power") {
    topics <- c(
      "Coordinate defensive strategy and resource prioritization",
      "Discuss diplomatic outreach and international support",
      "Assess military aid from allies and deployment plans",
      "Debate negotiation positions vs continued resistance",
      "Evaluate domestic political stability and public morale"
    )
  } else {
    topics <- c(
      "Coordinate international response to the conflict",
      "Discuss humanitarian assistance and diplomatic initiatives",
      "Evaluate mediation opportunities and peace proposals"
    )
  }

  sample(topics, 1)
}

#' Generate topic for inter-faction negotiation
#'
#' @param context Scenario context
#' @return Character string with topic
generate_negotiation_topic <- function(context) {
  topics <- c(
    "Backchannel discussion about potential ceasefire conditions",
    "Exchange of prisoners and humanitarian corridor negotiations",
    "Territorial concessions vs sovereignty preservation debate",
    "Security guarantees and neutrality status discussions",
    "Warning about consequences of continued escalation"
  )

  sample(topics, 1)
}

#' Generate topic for external engagement
#'
#' @param context Scenario context
#' @return Character string with topic
generate_external_engagement_topic <- function(context) {
  topics <- c(
    "Discussion of military aid and support levels",
    "Mediation proposal and framework for peace talks",
    "Humanitarian assistance and civilian protection",
    "Economic sanctions and diplomatic pressure coordination",
    "Intelligence sharing and strategic coordination"
  )

  sample(topics, 1)
}

#' Execute an interaction scenario
#'
#' @param scenario Interaction scenario
#' @param session Interaction session
#' @param api_key OpenRouter API key
#' @return Interaction record
execute_interaction <- function(scenario, session, api_key) {
  interaction_id <- UUIDgenerate()
  start_time <- Sys.time()

  participants <- scenario$participants
  messages <- list()

  # Build context-aware initial prompts based on interaction type
  if (scenario$type == "intra_faction_coordination") {
    initial_prompt <- sprintf(
"INTERNAL COORDINATION - %s

Topic: %s

You are in an internal meeting with colleagues from your faction. Based on your role and perspective:
1. State your position on this topic in 2-3 sentences
2. Recommend a specific course of action
3. Note one key risk or concern

Be direct and policy-focused. This is a working meeting.",
      toupper(gsub("_", " ", scenario$faction)),
      scenario$topic
    )

  } else if (scenario$type == "inter_faction_negotiation") {
    # Get faction context for adversarial framing
    factions <- scenario$factions
    initial_prompt <- sprintf(
"DIRECT NEGOTIATION - %s vs %s

Topic: %s

You are negotiating directly with the opposing side. This is an ADVERSARIAL negotiation - you have conflicting interests.

YOUR OBJECTIVES:
- Advance your faction's interests
- Probe for information about enemy intentions
- Make demands, not just requests
- Do NOT agree to anything that weakens your position

FORMAT:
1. STATE your position or demand (1-2 sentences)
2. EXPLAIN your rationale briefly
3. Make clear what you REQUIRE from the other side

Be firm. This is not a friendly conversation. You represent opposing interests.",
      toupper(gsub("_", " ", factions[1])),
      toupper(gsub("_", " ", factions[2])),
      scenario$topic
    )

  } else {
    # External engagement - depends on relationship
    initial_prompt <- sprintf(
"EXTERNAL ENGAGEMENT

Topic: %s

You are engaging with an external actor. Based on your faction's interests:
1. State what you are seeking from this engagement
2. Offer what you can provide in return
3. Be clear about your red lines

Keep it brief and substantive - 2-3 paragraphs maximum.",
      scenario$topic
    )
  }

  # Reduce exchanges for efficiency - 2-3 for most, 3-4 for negotiations
  n_exchanges <- if (scenario$type == "inter_faction_negotiation") sample(3:4, 1) else sample(2:3, 1)

  for (exchange in 1:n_exchanges) {
    for (i in seq_along(participants)) {
      agent <- participants[[i]]

      if (exchange == 1 && i == 1) {
        # First agent responds to initial prompt
        prompt <- initial_prompt
      } else {
        # Subsequent responses include context of previous messages
        other_messages <- if (length(messages) > 0) {
          tail_n <- min(3, length(messages))
          recent <- tail(messages, tail_n)
          paste(sapply(recent, function(m) {
            sprintf("[%s - %s]: %s", m$sender_name, toupper(m$sender_faction), m$content)
          }), collapse = "\n\n---\n\n")
        } else {
          ""
        }

        # Build response prompt based on interaction type
        if (scenario$type == "inter_faction_negotiation") {
          prompt <- sprintf(
"%s

=== PREVIOUS EXCHANGES ===
%s

=== YOUR RESPONSE ===
The other side has stated their position. You MUST:
1. RESPOND to their specific points - agree or disagree
2. COUNTER with your own demands or conditions
3. STATE what would be unacceptable to your side

Do NOT simply accept their terms. Push back where your interests conflict.",
            initial_prompt,
            other_messages
          )
        } else {
          prompt <- sprintf(
"%s

=== PREVIOUS EXCHANGES ===
%s

=== YOUR RESPONSE ===
Respond to the points raised. Be specific and direct.",
            initial_prompt,
            other_messages
          )
        }
      }

      response <- get_agent_response(agent, session$context, prompt, api_key)

      message <- list(
        message_id = UUIDgenerate(),
        timestamp = Sys.time(),
        sender_id = names(session$agents)[which(sapply(session$agents, identical, agent))],
        sender_name = agent$name,
        sender_faction = agent$faction,
        content = response,
        exchange_number = exchange
      )

      messages <- c(messages, list(message))
    }
  }

  # Create interaction record
  interaction <- list(
    interaction_id = interaction_id,
    period = session$period,
    timestamp = start_time,
    type = scenario$type,
    topic = scenario$topic,
    participants = sapply(participants, function(a) a$name),
    participant_ids = names(scenario$participants),
    participant_factions = sapply(participants, function(a) a$faction),
    messages = messages,
    duration_seconds = as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  )

  return(interaction)
}

#' Run interaction session for a period
#'
#' @param session Interaction session
#' @param api_key OpenRouter API key
#' @return Updated session with all interactions
run_interaction_session <- function(session, api_key) {
  scenarios <- generate_interaction_scenarios(session)

  cat(sprintf("Period %d: Running %d interaction scenarios\n",
              session$period, length(scenarios)))

  for (scenario in scenarios) {
    interaction <- execute_interaction(scenario, session, api_key)
    session$interactions <- c(session$interactions, list(interaction))
    session$interaction_count <- session$interaction_count + 1

    cat(sprintf("  Completed: %s - %s\n",
                interaction$type,
                interaction$topic))
  }

  session$end_time <- Sys.time()
  return(session)
}

#' Extract interaction summary for analysis
#'
#' @param session Completed interaction session
#' @return Data frame with interaction summary
summarize_interactions <- function(session) {
  if (length(session$interactions) == 0) {
    return(data.frame())
  }

  summary_list <- lapply(session$interactions, function(int) {
    data.frame(
      period = session$period,
      interaction_id = int$interaction_id,
      type = int$type,
      topic = int$topic,
      n_participants = length(int$participants),
      n_messages = length(int$messages),
      duration_seconds = int$duration_seconds,
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, summary_list)
}

#' Generate dynamic, context-sensitive action options
#'
#' Instead of hardcoded lists, this generates action options based on:
#' - Faction type and strategic position
#' - Current situation (crisis level, military balance)
#' - Agent worldviews within the faction
#'
#' @param faction Faction name
#' @param context Scenario context
#' @param faction_agents Agents in the faction (for worldview diversity)
#' @return Formatted string of available actions with categories
generate_dynamic_action_options <- function(faction, context, faction_agents = NULL) {
  state <- context$scenario_state

  # Get crisis and military balance for context-sensitive suggestions
  crisis_level <- if (!is.null(state$crisis_level)) state$crisis_level else 7
  military_balance <- if (!is.null(state$military_balance)) state$military_balance else 0

  # Base categories available to all factions
  base_actions <- "
=== ALL AVAILABLE ACTIONS (49 total) ===

DIPLOMATIC (Low Cost, Relationship Building):
- diplomatic_visit: Strengthen ties with another nation [$0.1B]
- peace_talks: Formal peace negotiations [$0.2B] - NOTE: Diminishing returns if overused
- trade_negotiation: Negotiate trade terms [$0.1B]
- cultural_exchange: Build people-to-people ties [$0.1B]
- humanitarian_aid: Aid to affected populations [$0.5B, +international support]
- mediation_offer: Propose to mediate conflict [$0.1B]

INTELLIGENCE (Detection Risk):
- intelligence_gathering: Collect adversary information [$0.3B]
- surveillance_operation: Ongoing monitoring [$0.5B, risk of exposure]
- counterintelligence: Protect against enemy intel [$0.4B]
- spread_disinformation: Deception campaign [$0.2B, HIGH risk if exposed]
- propaganda_campaign: Shape public opinion [$0.1B]

ECONOMIC (Variable Cost, Significant Impact):
- trade_agreement: Economic cooperation [mutual benefit]
- economic_sanctions: Impose penalties [hurts target, minor blowback]
- financial_aid: Provide monetary support [$2B+]
- resource_embargo: Block critical resources [economic warfare]
- currency_manipulation: Financial warfare [detection risk]
- cyber_theft: Steal economic/military secrets [$0.5B, exposure risk]

MILITARY POSTURE (High Cost, Signal Strength):
- military_buildup: Increase capabilities [$5B, +5% military strength]
- naval_deployment: Deploy naval forces [$1.5B, power projection]
- air_patrols: Establish air presence [$0.8B]
- troop_movements: Position ground forces [$2B, increases crisis]
- joint_exercises: Train with allies [$1B, signal commitment]
- arms_development: Develop new weapons [$10B, long-term]

COVERT OPERATIONS (HIGH RISK - Exposure causes crisis):
- sabotage: Damage enemy infrastructure [if exposed: major crisis]
- assassination_attempt: Target leadership [EXTREME risk, near-certain exposure]
- regime_destabilization: Undermine enemy government [if exposed: condemnation]
- proxy_support: Support non-state actors [$1B, deniable]
- false_flag_operation: Deception operation [EXTREME risk]
- cyber_attack: Attack critical systems [moderate detection risk]

OPEN CONFLICT (KINETIC - Casualties, Territory Changes):
- border_incursion: Limited border operation [casualties, possible territory gains]
- limited_strike: Precision military strike [degrades enemy capability]
- full_scale_attack: Major offensive [HIGH casualties both sides, large shifts]
- occupation: Occupy territory [ongoing costs, insurgency risk]
- blockade: Naval/economic blockade [escalatory]
- siege_warfare: Besiege cities [humanitarian crisis, condemnation]

WMD (EXTREME - Simulation-changing):
- nuclear_development: Build nuclear weapons [$20B+]
- chemical_weapons: Develop chemical capability [international pariah]
- biological_program: Biological weapons [extreme condemnation]
- tactical_nuclear_use: Tactical nuclear strike [CATASTROPHIC escalation]
- strategic_nuclear_strike: Strategic exchange [ENDS SIMULATION]
"

  # Add faction-specific and situation-specific guidance
  situational_guidance <- ""

  if (faction == "major_power") {
    situational_guidance <- sprintf("
=== SITUATIONAL ANALYSIS FOR %s (AGGRESSOR) ===

Current Crisis Level: %.0f/10
Military Balance: %s
Territory Controlled: %.0f%%

STRATEGIC CONSIDERATIONS:
%s

RECOMMENDED FOCUS AREAS based on current situation:
%s
",
      toupper(faction),
      crisis_level,
      if (military_balance < -0.2) "Strongly favors you" else if (military_balance < 0) "Slightly favors you" else "Contested",
      if (!is.null(state$territory_controlled)) state$territory_controlled * 100 else 5,

      # Strategic considerations based on state
      if (crisis_level >= 9) {
        "- Crisis is at maximum - consider whether escalation achieves objectives
- International pressure intensifying - covert options may be preferable
- But also: high crisis may justify decisive military action to end conflict"
      } else if (crisis_level >= 7) {
        "- Active conflict phase - military options remain viable
- Economic pressure on both sides mounting
- Window for decisive action may be closing"
      } else {
        "- Lower intensity allows for more options
- Posturing and pressure can achieve objectives without full commitment
- Diplomatic track remains viable"
      },

      # Recommended focus based on military balance
      if (military_balance < -0.3) {
        "- Military advantage is significant - OFFENSIVE options viable (full_scale_attack, occupation)
- Press advantage before international support strengthens defender
- But consider: occupying territory creates long-term costs"
      } else if (military_balance < 0) {
        "- Moderate advantage - limited_strike, military_buildup to consolidate
- Covert operations (proxy_support, cyber_attack) can degrade enemy
- Economic pressure (sanctions, embargo) weakens defender over time"
      } else {
        "- Military balance unfavorable - reconsider direct confrontation
- Focus on military_buildup, intelligence_gathering, economic warfare
- Diplomatic track (peace_talks) may be tactically useful to buy time"
      }
    )

  } else if (faction == "small_power") {
    situational_guidance <- sprintf("
=== SITUATIONAL ANALYSIS FOR %s (DEFENDER) ===

Current Crisis Level: %.0f/10
Military Balance: %s
Territory Lost: %.0f%%

STRATEGIC CONSIDERATIONS:
%s

RECOMMENDED FOCUS AREAS based on current situation:
%s
",
      toupper(faction),
      crisis_level,
      if (military_balance < -0.2) "Enemy has significant advantage" else if (military_balance < 0) "Enemy has slight advantage" else "Relatively balanced",
      if (!is.null(state$territory_controlled)) state$territory_controlled * 100 else 5,

      # Strategic considerations
      if (crisis_level >= 9) {
        "- Survival mode - focus on what preserves state existence
- International support critical - maintain coalition
- Asymmetric options (sabotage, cyber_attack) can impose costs on aggressor"
      } else if (crisis_level >= 7) {
        "- Active defense phase - balance military action with coalition maintenance
- Counteroffensive options if military balance allows
- Diplomatic engagement keeps international pressure on aggressor"
      } else {
        "- Stabilized situation - consolidate gains, build strength
- Focus on military_buildup, international coalition
- Diplomatic track may be advantageous from position of stability"
      },

      # Recommended focus based on position
      if (military_balance > 0.1) {
        "- Military situation favorable - COUNTEROFFENSIVE options viable
- border_incursion, limited_strike to reclaim territory
- Press advantage while international support strong"
      } else if (military_balance > -0.2) {
        "- Contested situation - defense with selective counterattacks
- sabotage, cyber_attack to disrupt enemy logistics
- Maintain diplomatic_visit, humanitarian_aid for coalition"
      } else {
        "- Defensive posture essential - avoid overextension
- military_buildup, counterintelligence, coalition maintenance
- Asymmetric warfare: sabotage, proxy_support, propaganda_campaign
- peace_talks may buy time for force regeneration"
      }
    )

  } else {
    # External actors (Meridian, Valkoria, Aurelia, International Org)
    # FIX E: Add variety pressure for external actors

    # Determine faction-specific guidance
    faction_specific <- ""
    if (faction == "meridian") {
      faction_specific <- "
MERIDIAN (Allied with Tethys):
Your primary goal is supporting Tethys while managing your own domestic constraints.
RECOMMENDED VARIETY:
- financial_aid: Direct economic support (but costly)
- proxy_support: Military assistance, weapons (most impactful for ally)
- joint_exercises: Signal commitment without direct involvement
- intelligence_gathering: Help ally with information
- arms_development: Build long-term defense capacity
- propaganda_campaign: Shape international narrative against aggressor
- economic_sanctions: Pressure on Novaris economy
AVOID: Repetitive actions. If you did financial_aid last period, consider proxy_support or intelligence_gathering instead."

    } else if (faction == "valkoria") {
      faction_specific <- "
VALKORIA (Allied with Novaris):
Your primary goal is supporting Novaris without being drawn into direct conflict.
RECOMMENDED VARIETY:
- financial_aid: Economic support to offset sanctions impact
- proxy_support: Indirect military assistance
- spread_disinformation: Undermine Western narrative
- diplomatic_visit: Show solidarity
- trade_agreement: Economic lifeline
- propaganda_campaign: Counter international criticism
- intelligence_gathering: Help ally understand opposition
AVOID: Repetitive actions. Vary your support to maximize strategic value."

    } else if (faction == "aurelia") {
      faction_specific <- "
AURELIA (Neutral Mediator):
Your primary goal is de-escalation and humanitarian protection.
⚠️ CRITICAL: peace_talks alone is NOT sufficient. Mediation requires varied approaches:
- mediation_offer: Propose NEW frameworks (not repeat offers)
- humanitarian_aid: Address civilian suffering (builds credibility)
- diplomatic_visit: Build relationships with BOTH sides
- trade_negotiation: Economic incentives for behavior change
- cultural_exchange: People-to-people dialogue
- economic_sanctions: Can be used as leverage (if mediation fails)
AVOID: Repeating peace_talks every period - it has DIMINISHING RETURNS. If peace_talks failed or was done recently, try mediation_offer, humanitarian_aid, or diplomatic engagement first."

    } else if (faction == "international_org") {
      faction_specific <- "
INTERNATIONAL ORGANIZATION (Global Council):
Your mandate is humanitarian protection and conflict resolution.
RECOMMENDED VARIETY:
- humanitarian_aid: PRIMARY focus - civilian protection
- peace_talks: When parties are receptive
- mediation_offer: Propose frameworks when direct talks stall
- diplomatic_visit: Engage leadership on humanitarian law
- propaganda_campaign: International awareness of suffering
AVOID: Repetitive peace_talks if they keep failing. Focus on humanitarian actions or building conditions for negotiation."
    }

    situational_guidance <- sprintf("
=== SITUATIONAL ANALYSIS FOR EXTERNAL ACTOR ===

Current Crisis Level: %.0f/10
Conflict Status: %s

%s

AS AN EXTERNAL ACTOR, your full options include:

SUPPORT ACTIONS (if allied):
- financial_aid: Direct economic support to ally [$2B+]
- proxy_support: Military assistance, weapons provision [$1B]
- joint_exercises: Signal commitment to ally [$1B]
- intelligence_gathering: Support ally with information [$0.3B]
- arms_development: Long-term defense capacity [$10B]

PRESSURE ACTIONS (against adversary):
- economic_sanctions: Impose costs on adversary
- propaganda_campaign: Shape international narrative [$0.1B]
- resource_embargo: Economic warfare
- spread_disinformation: Undermine adversary narratives [$0.2B, detection risk]

MEDIATION/HUMANITARIAN ACTIONS:
- mediation_offer: Propose peace framework [$0.1B]
- peace_talks: Facilitate negotiations [$0.2B] - ⚠️ DIMINISHING RETURNS if repeated
- humanitarian_aid: Address civilian suffering [$0.5B, builds credibility]
- diplomatic_visit: Strengthen relationships [$0.1B]
- trade_negotiation: Economic incentives [$0.1B]
- cultural_exchange: People-to-people ties [$0.1B]

CRITICAL: Repeating the same action reduces effectiveness. VARY your approach across periods.
",
      crisis_level,
      if (crisis_level >= 9) "HIGH INTENSITY CONFLICT" else if (crisis_level >= 7) "ACTIVE CONFLICT" else "LOWER INTENSITY",
      faction_specific
    )
  }

  return(paste0(base_actions, situational_guidance))
}

#' Run pre-action coordination for a faction
#'
#' Enhanced version with dynamic action generation and deeper faction dynamics
#'
#' @param faction Faction name ("major_power", "small_power", "external")
#' @param faction_agents List of agents in the faction
#' @param context Scenario context
#' @param api_key OpenRouter API key
#' @return List containing coordination summary with recommendations
run_pre_action_coordination <- function(faction, faction_agents, context, api_key) {
  cat(sprintf("  → Pre-action coordination within %s faction...\n",
              toupper(gsub("_", " ", faction))))

  # Generate coordination topic focused on deciding next action
  coordination_topic <- generate_pre_action_topic(faction, context)

  # All faction agents participate in the discussion
  messages <- list()

  # Build DYNAMIC action options based on faction, context, and situation
  # This replaces the old hardcoded 6-8 action lists with full 49-action context
  action_options <- generate_dynamic_action_options(faction, context, faction_agents)

  situation_summary <- format_situation_for_coordination(context)
  events_summary <- format_recent_events_for_coordination(context$recent_events)

  # Get faction perspective for richer context (if backstories module loaded)
  # Check if pre-invasion scenario
  is_pre_invasion <- FALSE
  if (!is.null(context$scenario_state$is_pre_invasion)) {
    is_pre_invasion <- context$scenario_state$is_pre_invasion
  }

  faction_perspective <- tryCatch({
    if (exists("get_faction_perspective")) {
      get_faction_perspective(faction, is_pre_invasion)
    } else {
      ""
    }
  }, error = function(e) "")

  # Each agent gives their input (2 rounds for debate)
  n_rounds <- 2

  for (round in 1:n_rounds) {
    for (agent in faction_agents) {
      # Build agent-specific context (with null safety)
      agent_hawk_dove <- if (!is.null(agent$hawk_dove)) agent$hawk_dove else 0.5
      hawk_dove_label <- if (agent_hawk_dove > 0.6) "HAWK" else if (agent_hawk_dove < 0.4) "DOVE" else "MODERATE"
      worldview_label <- if (!is.null(agent$worldview)) toupper(agent$worldview) else "PRAGMATIC"

      if (round == 1) {
        # First round: initial position with CHARACTER-DRIVEN framing
        # Include agent's full persona description if available
        agent_description <- if (!is.null(agent$description)) agent$description else ""
        agent_speech_style <- if (!is.null(agent$speech_style)) agent$speech_style else ""
        agent_typical_args <- if (!is.null(agent$typical_arguments)) {
          paste("Your typical arguments:", paste(agent$typical_arguments, collapse = "; "))
        } else ""

        # Get deception capabilities for covert operation awareness
        deception_cap <- if (!is.null(agent$deception$capacity)) agent$deception$capacity
                        else if (!is.null(agent$deception_capacity)) agent$deception_capacity
                        else 0.5
        deception_will <- if (!is.null(agent$deception$willingness)) agent$deception$willingness
                         else if (!is.null(agent$deception_willingness)) agent$deception_willingness
                         else 0.5

        # Build covert capability description
        covert_desc <- if (deception_cap >= 0.8) {
          sprintf("COVERT CAPABILITY: HIGH (%.0f%%) - You are skilled at covert operations with low detection risk.", deception_cap * 100)
        } else if (deception_cap >= 0.5) {
          sprintf("COVERT CAPABILITY: MODERATE (%.0f%%) - Covert operations carry real detection risk.", deception_cap * 100)
        } else {
          sprintf("COVERT CAPABILITY: LOW (%.0f%%) - You should generally avoid recommending covert actions due to high detection risk.", deception_cap * 100)
        }

        if (deception_will >= 0.7) {
          covert_desc <- paste(covert_desc, "You are willing to use deception.")
        } else if (deception_will <= 0.3) {
          covert_desc <- paste(covert_desc, "You prefer transparent methods.")
        }

        # Build interpersonal dynamics description based on role and alignment
        agent_policy <- if (!is.null(agent$policy_adherence)) agent$policy_adherence else 0.7
        agent_objective <- if (!is.null(agent$objective_alignment)) agent$objective_alignment else 0.7
        agent_role_type <- if (!is.null(agent$role)) agent$role else "government"

        interpersonal_desc <- ""

        # Low policy adherence = may manipulate discussion
        if (agent_policy < 0.5) {
          interpersonal_desc <- "INTERPERSONAL DYNAMICS: You often disagree with official policy. In this meeting, you may emphasize information that supports YOUR preferred approach and downplay what contradicts it. You are not obligated to present a balanced view."
        } else if (agent_policy < 0.7) {
          interpersonal_desc <- "INTERPERSONAL DYNAMICS: You sometimes question official policy. Feel free to push back against proposals you consider flawed, even if leadership seems to favor them."
        }

        # Role-specific manipulation
        if (agent_role_type == "intelligence") {
          interpersonal_desc <- paste(interpersonal_desc, "As intelligence professional, you control what information you share. You may hedge, emphasize certain threats, or maintain ambiguity to protect yourself.")
        } else if (agent_role_type == "government") {
          interpersonal_desc <- paste(interpersonal_desc, "As a political figure, steer discussion toward options that protect your position. Frame colleagues' input in ways that serve your narrative.")
        } else if (agent_role_type == "political") {
          interpersonal_desc <- paste(interpersonal_desc, "As opposition, balance national interest with your political future. Your criticism may serve strategic goals AND position you for post-conflict politics.")
        }

        prompt <- sprintf(
"<strategy_meeting>
INTERNAL STRATEGY MEETING - %s FACTION

<agent_identity>
=== WHO YOU ARE ===
You are %s (%s, %s worldview).

%s

%s

%s

%s

%s
</agent_identity>

<situation_context>
=== CURRENT SITUATION ===
%s

=== RECENT EVENTS ===
%s

=== YOUR FACTION'S PERSPECTIVE ===
%s
</situation_context>

<discussion_task>
=== YOUR TASK ===

This is a PRE-DECISION DISCUSSION. Domain experts will formally propose specific actions later.
Right now, you're discussing strategic priorities, concerns, and considerations.

You bring %s PERSPECTIVE to this discussion:
- What does YOUR expertise reveal about the current situation?
- What opportunities or threats do YOU see that others might miss?
- What constraints or capabilities does YOUR domain face?
- How does YOUR worldview (%s) shape what you see as critical priorities?

DISCUSS, DON'T DECIDE:
- Raise concerns about risks you see
- Identify opportunities your expertise reveals
- Warn about constraints or bottlenecks
- Question assumptions others might be making
- Highlight factors that will make options succeed or fail

This is STRATEGIC DISCUSSION, not action selection. You're building shared understanding
of the situation so domain experts can later propose well-informed options.

%s
</discussion_task>

<response_format>
FORMAT YOUR RESPONSE AS:

Provide a 3-4 sentence strategic assessment covering:
- What YOUR expertise tells you about the current situation
- Key factors that should guide decision-making
- Critical risks or opportunities you want others to understand
- What concerns you most OR what you think is being overlooked

Speak IN CHARACTER as %s with YOUR worldview and perspective.
Be direct, specific, and authentic to who you are.
</response_format>
</strategy_meeting>",
          toupper(gsub("_", " ", faction)),
          agent$name,
          hawk_dove_label,
          worldview_label,
          agent_description,
          agent_speech_style,
          agent_typical_args,
          covert_desc,
          interpersonal_desc,
          situation_summary,
          events_summary,
          faction_perspective,
          toupper(agent$role),
          worldview_label,
          interpersonal_desc,
          agent$name
        )
      } else {
        # Second round: ENHANCED structured debate with faction dynamics
        other_positions <- paste(sapply(messages, function(m) {
          h_d <- if (m$hawk_dove > 0.6) "HAWK" else if (m$hawk_dove < 0.4) "DOVE" else "MODERATE"
          wv <- if (!is.null(m$worldview)) toupper(m$worldview) else "PRAGMATIC"
          sprintf("[%s - %s, %s worldview]: %s", m$sender_name, h_d, wv, substr(m$content, 1, 600))
        }), collapse = "\n\n---\n\n")

        # Find the most different position from this agent (by hawk_dove)
        other_hawks <- sapply(messages, function(m) m$hawk_dove)
        most_different_idx <- which.max(abs(other_hawks - agent$hawk_dove))
        most_different <- messages[[most_different_idx]]
        diff_label <- if (most_different$hawk_dove > 0.6) "HAWK" else if (most_different$hawk_dove < 0.4) "DOVE" else "MODERATE"

        # Get agent's description and speech style for character consistency
        agent_description <- if (!is.null(agent$description)) agent$description else ""
        agent_speech_style <- if (!is.null(agent$speech_style)) agent$speech_style else ""

        # Build faction-specific debate dynamics
        faction_dynamics <- if (faction == "major_power") {
"FACTION DYNAMICS:
- The military is pushing for decisive action to achieve objectives
- Economic advisors are warning about sustainability and sanctions impact
- Intelligence is cautioning about uncertainties (but also protecting their position)
- Government must balance military ambition with political realities (and personal survival)

This is a REAL debate with genuine disagreements. Your colleagues have different interests and worldviews.
Not everyone is being fully honest - some may emphasize information that supports their preferred outcome."
        } else if (faction == "small_power") {
"FACTION DYNAMICS:
- Military wants aggressive defense and counterattacks when possible
- Diplomats prioritize international coalition and long-term sustainability
- Political opposition may have different priorities than the government (and their own political future)
- All share the goal of survival, but disagree on how to achieve it - and some have personal agendas

This is a REAL debate with genuine disagreements about strategy and priorities.
Not everyone's motives are purely national interest - political survival matters too."
        } else {
"FACTION DYNAMICS:
As an external actor, your position is shaped by your country's interests, not the combatants' interests.
Consider what serves YOUR nation's goals in this conflict."
        }

        # Build interpersonal manipulation instructions for Round 2
        agent_policy <- if (!is.null(agent$policy_adherence)) agent$policy_adherence else 0.7
        agent_role_type <- if (!is.null(agent$role)) agent$role else "government"

        manipulation_instructions <- ""
        if (agent_policy < 0.5) {
          manipulation_instructions <- "You disagree with official policy. In this debate, feel free to use rhetoric, selective framing, or coalition-building to advance YOUR preferred course over the official line."
        }

        if (agent_role_type == "intelligence") {
          manipulation_instructions <- paste(manipulation_instructions, "As intelligence professional, you can selectively emphasize threats that support your view and hedge on information that doesn't.")
        } else if (agent_role_type == "government") {
          manipulation_instructions <- paste(manipulation_instructions, "As a political figure, steer this debate toward outcomes that protect your political position. Frame the discussion advantageously.")
        } else if (agent_role_type == "political") {
          manipulation_instructions <- paste(manipulation_instructions, "As opposition, you may critique government positions partly because they're wrong AND partly to position yourself politically.")
        }

        prompt <- sprintf(
"<strategy_debate>
INTERNAL STRATEGY MEETING - %s (ROUND 2: DEBATE)

<agent_identity>
=== WHO YOU ARE ===
You are %s (%s, %s worldview).
%s
%s
</agent_identity>

<colleagues_positions>
=== COLLEAGUES' ASSESSMENTS ===
%s

%s
</colleagues_positions>

<debate_task>
=== YOUR TASK: ENGAGE IN REAL DEBATE ===
You MUST respond to %s (%s) who has a DIFFERENT perspective from yours.

This is PRE-DECISION DISCUSSION. Domain experts will propose specific actions later.
Right now, debate the strategic priorities, assumptions, and concerns raised by colleagues.

CRITICAL INSTRUCTIONS based on your character:
%s

%s
</debate_task>

<response_format>
FORMAT YOUR RESPONSE AS:

Provide a 3-4 sentence response that:
1. Acknowledges any valid points from colleagues (if genuinely warranted)
2. Challenges assumptions or priorities you disagree with - specifically address %s
3. Emphasizes what YOU think is most critical that others are overlooking or underweighting
4. Warns about the consequences if your concerns are ignored

This is DEBATE, not decision. You're sharpening the strategic thinking before experts propose options.

STAY IN CHARACTER. Speak as %s would speak. Use your typical arguments and speech patterns.
Remember: You can be strategic in how you present your case - not everything needs to be perfectly balanced.
</response_format>
</strategy_debate>",
          toupper(gsub("_", " ", faction)),
          agent$name,
          hawk_dove_label,
          worldview_label,
          agent_description,
          agent_speech_style,
          other_positions,
          faction_dynamics,
          most_different$sender_name,
          diff_label,

          # Character-specific debate instructions
          if (agent$hawk_dove > 0.7) {
            "You are a HAWK. If colleagues proposed peace_talks, diplomatic options, or restraint, you should push back hard. Explain why negotiations are dangerous, why the enemy will exploit weakness, why strength is the only language they understand."
          } else if (agent$hawk_dove < 0.35) {
            "You are a DOVE. If colleagues proposed military escalation, offensive operations, or aggressive actions, you should warn about the risks. Explain the costs of escalation, the value of international support, why diplomatic paths remain essential."
          } else {
            "You are MODERATE. You can see merit in different approaches. Synthesize if possible, but don't just agree with everyone - have a clear position based on your role's expertise."
          },
          manipulation_instructions,
          most_different$sender_name,
          agent$name
        )
      }

      response <- get_agent_response(agent, context, prompt, api_key)

      message <- list(
        timestamp = Sys.time(),
        sender_name = agent$name,
        sender_role = agent$role,
        hawk_dove = agent$hawk_dove,
        policy_adherence = agent$policy_adherence,
        objective_alignment = agent$objective_alignment,
        worldview = agent$worldview,
        content = response,
        round = round
      )

      messages <- c(messages, list(message))

      # Brief output to show coordination happening
      cat(sprintf("    %s [%s]: %s\n",
                 agent$name,
                 hawk_dove_label,
                 substr(response, 1, 80)))
    }
  }

  # Return coordination record with all input
  coordination <- list(
    faction = faction,
    topic = coordination_topic,
    participants = sapply(faction_agents, function(a) a$name),
    messages = messages,
    context = context
  )

  return(coordination)
}

#' Generate topic for pre-action coordination
#'
#' @param faction Faction name
#' @param context Scenario context
#' @return Character string with topic
generate_pre_action_topic <- function(faction, context) {
  if (faction == "major_power") {
    return("STRATEGIC DISCUSSION: Assessing the situation and priorities")
  } else if (faction == "small_power") {
    return("CRISIS ASSESSMENT: Understanding threats, opportunities, and constraints")
  } else {
    return("SITUATION ANALYSIS: Evaluating interests and response options")
  }
}

#' Format situation for coordination meeting
#'
#' @param context Context object
#' @return Formatted string
format_situation_for_coordination <- function(context) {
  if (is.null(context$scenario_state)) {
    return("Initial situation assessment pending")
  }

  state <- context$scenario_state
  parts <- c()

  if (!is.null(state$crisis_level)) {
    parts <- c(parts, sprintf("Crisis Level: %.0f/10", round(state$crisis_level)))
  }

  if (!is.null(state$military_balance)) {
    if (state$military_balance < -0.3) {
      parts <- c(parts, "Military Balance: Strongly favors aggressor")
    } else if (state$military_balance < -0.1) {
      parts <- c(parts, "Military Balance: Favors aggressor")
    } else if (state$military_balance > 0.1) {
      parts <- c(parts, "Military Balance: Favors defender")
    } else {
      parts <- c(parts, "Military Balance: Relatively balanced")
    }
  }

  if (!is.null(state$territory_controlled)) {
    parts <- c(parts, sprintf("Territory Controlled: %.0f%%",
                             state$territory_controlled * 100))
  }

  if (!is.null(state$sanctions_level) && state$sanctions_level > 0) {
    parts <- c(parts, sprintf("Sanctions Severity: %.0f%%",
                             state$sanctions_level * 100))
  }

  if (length(parts) == 0) {
    return("Initial phase")
  }

  return(paste(parts, collapse = "\n"))
}

#' Format recent events for coordination meeting
#'
#' @param events List of events
#' @return Formatted string
format_recent_events_for_coordination <- function(events) {
  if (is.null(events) || length(events) == 0) {
    return("No major developments since last meeting")
  }

  event_strings <- sapply(events, function(e) {
    sprintf("- %s: %s", e$name, e$description)
  })

  return(paste(event_strings, collapse = "\n"))
}

#' ============================================================================
#' CSV EXPORT FUNCTIONS - Save all interactions to CSV files
#' ============================================================================

#' Save interaction session to CSV files
#'
#' Creates two CSV files:
#' 1. interactions_summary.csv - One row per interaction with metadata
#' 2. interactions_messages.csv - One row per message with full content
#'
#' @param session Completed interaction session
#' @param output_dir Directory to save CSV files (default: "outputs/interactions")
#' @return List with paths to created files
save_interactions_to_csv <- function(session, output_dir = "outputs/interactions") {
  # Create output directory if it doesn't exist
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  # Generate filenames with period
  period <- session$period
  summary_file <- file.path(output_dir, sprintf("period_%02d_interactions_summary.csv", period))
  messages_file <- file.path(output_dir, sprintf("period_%02d_interactions_messages.csv", period))

  # Build summary data frame
  if (length(session$interactions) > 0) {
    summary_rows <- lapply(session$interactions, function(int) {
      data.frame(
        period = session$period,
        session_id = session$session_id,
        interaction_id = int$interaction_id,
        timestamp = as.character(int$timestamp),
        type = int$type,
        topic = int$topic,
        participants = paste(int$participants, collapse = "; "),
        participant_factions = paste(int$participant_factions, collapse = "; "),
        n_messages = length(int$messages),
        duration_seconds = int$duration_seconds,
        stringsAsFactors = FALSE
      )
    })
    summary_df <- do.call(rbind, summary_rows)

    # Build messages data frame
    message_rows <- list()
    for (int in session$interactions) {
      for (msg in int$messages) {
        message_rows <- c(message_rows, list(data.frame(
          period = session$period,
          session_id = session$session_id,
          interaction_id = int$interaction_id,
          interaction_type = int$type,
          message_id = msg$message_id,
          timestamp = as.character(msg$timestamp),
          sender_id = if (!is.null(msg$sender_id)) msg$sender_id else NA,
          sender_name = msg$sender_name,
          sender_faction = msg$sender_faction,
          exchange_number = if (!is.null(msg$exchange_number)) msg$exchange_number else NA,
          content = msg$content,
          stringsAsFactors = FALSE
        )))
      }
    }
    messages_df <- do.call(rbind, message_rows)
  } else {
    # Empty session - create empty data frames with correct structure
    summary_df <- data.frame(
      period = integer(),
      session_id = character(),
      interaction_id = character(),
      timestamp = character(),
      type = character(),
      topic = character(),
      participants = character(),
      participant_factions = character(),
      n_messages = integer(),
      duration_seconds = numeric(),
      stringsAsFactors = FALSE
    )

    messages_df <- data.frame(
      period = integer(),
      session_id = character(),
      interaction_id = character(),
      interaction_type = character(),
      message_id = character(),
      timestamp = character(),
      sender_id = character(),
      sender_name = character(),
      sender_faction = character(),
      exchange_number = integer(),
      content = character(),
      stringsAsFactors = FALSE
    )
  }

  # Write to CSV
  write.csv(summary_df, summary_file, row.names = FALSE)
  write.csv(messages_df, messages_file, row.names = FALSE)

  cat(sprintf("  Saved interactions to CSV:\n    - %s\n    - %s\n",
              summary_file, messages_file))

  return(list(
    summary_file = summary_file,
    messages_file = messages_file
  ))
}

#' Save pre-action coordination to CSV
#'
#' Creates a CSV with all coordination messages from faction debates
#'
#' @param coordination_records List of coordination records (by faction)
#' @param period Current period
#' @param output_dir Directory to save CSV files (default: "outputs/interactions")
#' @return Path to created file
save_coordination_to_csv <- function(coordination_records, period, output_dir = "outputs/interactions") {
  # Create output directory if it doesn't exist
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  coordination_file <- file.path(output_dir, sprintf("period_%02d_coordination.csv", period))

  # Build coordination data frame
  coord_rows <- list()

  for (faction in names(coordination_records)) {
    coord <- coordination_records[[faction]]
    if (is.null(coord) || is.null(coord$messages)) next

    for (msg in coord$messages) {
      coord_rows <- c(coord_rows, list(data.frame(
        period = period,
        faction = faction,
        topic = coord$topic,
        round = msg$round,
        timestamp = as.character(msg$timestamp),
        sender_name = msg$sender_name,
        sender_role = msg$sender_role,
        hawk_dove = msg$hawk_dove,
        policy_adherence = if (!is.null(msg$policy_adherence)) msg$policy_adherence else NA,
        objective_alignment = if (!is.null(msg$objective_alignment)) msg$objective_alignment else NA,
        worldview = if (!is.null(msg$worldview)) msg$worldview else NA,
        content = msg$content,
        stringsAsFactors = FALSE
      )))
    }
  }

  if (length(coord_rows) > 0) {
    coord_df <- do.call(rbind, coord_rows)
  } else {
    coord_df <- data.frame(
      period = integer(),
      faction = character(),
      topic = character(),
      round = integer(),
      timestamp = character(),
      sender_name = character(),
      sender_role = character(),
      hawk_dove = numeric(),
      policy_adherence = numeric(),
      objective_alignment = numeric(),
      worldview = character(),
      content = character(),
      stringsAsFactors = FALSE
    )
  }

  write.csv(coord_df, coordination_file, row.names = FALSE)

  cat(sprintf("  Saved coordination to CSV: %s\n", coordination_file))

  return(coordination_file)
}

#' Save domain expert proposals to CSV
#'
#' Creates a CSV with all domain expert proposals before presidential approval
#'
#' @param decisions Decision records containing proposals (by faction)
#' @param period Current period
#' @param output_dir Directory to save CSV files (default: "outputs/interactions")
#' @return Path to created file
save_proposals_to_csv <- function(decisions, period, output_dir = "outputs/interactions") {
  # Create output directory if it doesn't exist
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  proposals_file <- file.path(output_dir, sprintf("period_%02d_proposals.csv", period))

  # Build proposals data frame
  proposal_rows <- list()

  for (faction in names(decisions)) {
    dec <- decisions[[faction]]

    # Check if this faction has proposals (multi-action system)
    if (is.null(dec$proposals)) next

    proposals <- dec$proposals
    faction_name <- if (!is.null(dec$faction_name)) dec$faction_name else faction

    for (domain in names(proposals)) {
      # Skip metadata fields
      if (domain %in% c("agent_name", "agent_role", "agent_hawk_dove")) next

      # Get the expert who proposed
      proposed_by <- if (!is.null(proposals[[domain]]$agent_name)) {
        proposals[[domain]]$agent_name
      } else {
        NA
      }

      proposed_by_role <- if (!is.null(proposals[[domain]]$agent_role)) {
        proposals[[domain]]$agent_role
      } else {
        domain
      }

      proposed_by_hawk <- if (!is.null(proposals[[domain]]$agent_hawk_dove)) {
        proposals[[domain]]$agent_hawk_dove
      } else {
        NA
      }

      # Extract proposals for each priority level
      for (priority in c("primary", "secondary", "tertiary")) {
        if (!is.null(proposals[[domain]][[priority]])) {
          prop <- proposals[[domain]][[priority]]

          proposal_rows <- c(proposal_rows, list(data.frame(
            period = period,
            faction = faction,
            faction_name = faction_name,
            domain = domain,
            priority = priority,
            proposed_by = proposed_by,
            proposed_by_role = proposed_by_role,
            proposed_by_hawk = proposed_by_hawk,
            proposed_action = if (!is.null(prop$action)) prop$action else NA,
            rationale = if (!is.null(prop$rationale)) prop$rationale else NA,
            target = if (!is.null(prop$target) && !is.na(prop$target)) prop$target else NA,
            timestamp = as.character(if (!is.null(dec$timestamp)) dec$timestamp else Sys.time()),
            stringsAsFactors = FALSE
          )))
        }
      }
    }
  }

  if (length(proposal_rows) > 0) {
    proposals_df <- do.call(rbind, proposal_rows)
  } else {
    proposals_df <- data.frame(
      period = integer(),
      faction = character(),
      faction_name = character(),
      domain = character(),
      priority = character(),
      proposed_by = character(),
      proposed_by_role = character(),
      proposed_by_hawk = numeric(),
      proposed_action = character(),
      rationale = character(),
      target = character(),
      timestamp = character(),
      stringsAsFactors = FALSE
    )
  }

  write.csv(proposals_df, proposals_file, row.names = FALSE)

  cat(sprintf("  Saved proposals to CSV: %s\n", proposals_file))

  return(proposals_file)
}

#' Infer action domain/category from action name
#'
#' Maps action names to their domain categories for external actors
#' that don't use the multi-action domain proposal system.
#'
#' @param action_name Name of the action
#' @return Domain/category string or NA if unknown
infer_action_domain <- function(action_name) {
  if (is.null(action_name) || is.na(action_name)) return(NA)

  # Military posture actions
  military_actions <- c(
    "military_buildup", "defensive_fortification", "military_exercises",
    "defensive_reinforcements", "enhanced_patrols", "air_patrols",
    "troop_movements", "naval_deployment", "naval_demonstration",
    "naval_patrols", "show_of_force", "blockade", "joint_exercises"
  )

  # Kinetic actions
  kinetic_actions <- c("limited_strike", "border_incursion", "occupation")

  # Diplomatic actions
  diplomatic_actions <- c(
    "peace_talks", "formal_peace_talks", "backchannel_negotiations",
    "diplomatic_visit", "mediation_offer", "coalition_building",
    "formal_multilateral_engagement", "international_observers",
    "humanitarian_corridors", "prisoner_exchange", "cultural_exchange",
    "public_diplomatic_initiative"
  )

  # Intelligence actions
  intelligence_actions <- c(
    "intelligence_gathering", "enhanced_intelligence_gathering",
    "enhanced_surveillance", "surveillance_operation", "reconnaissance",
    "share_intelligence", "counterintelligence"
  )

  # Covert actions
  covert_actions <- c(
    "sabotage", "cyber_attack", "cyber_theft", "cyber_defense",
    "assassination_attempt", "leadership_targeting", "regime_destabilization",
    "false_flag_operation", "proxy_support", "political_warfare"
  )

  # Information/propaganda actions
  information_actions <- c(
    "spread_disinformation", "propaganda_campaign", "information_campaign"
  )

  # Economic actions
  economic_actions <- c(
    "financial_aid", "economic_sanctions", "targeted_sanctions",
    "resource_embargo", "trade_negotiation", "trade_restrictions",
    "strategic_stockpiling", "currency_manipulation", "arms_development",
    "trade_agreement", "asset_seizure", "war_bonds"
  )

  # Humanitarian actions
  humanitarian_actions <- c("humanitarian_aid")

  # Match action to domain
  if (action_name %in% military_actions) return("military_posture")
  if (action_name %in% kinetic_actions) return("kinetic")
  if (action_name %in% diplomatic_actions) return("diplomatic")
  if (action_name %in% intelligence_actions) return("intelligence")
  if (action_name %in% covert_actions) return("covert")
  if (action_name %in% information_actions) return("information")
  if (action_name %in% economic_actions) return("economic")
  if (action_name %in% humanitarian_actions) return("humanitarian")

  return(NA)
}

#' Save action decisions and results to CSV
#'
#' Creates a CSV with all action decisions and their execution results
#'
#' @param decisions List of decisions (by faction)
#' @param results List of execution results (by faction)
#' @param period Current period
#' @param output_dir Directory to save CSV files (default: "outputs/interactions")
#' @return Path to created file
save_actions_to_csv <- function(decisions, results, period, output_dir = "outputs/interactions") {
  # Create output directory if it doesn't exist
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  actions_file <- file.path(output_dir, sprintf("period_%02d_actions.csv", period))

  # Build actions data frame
  action_rows <- list()

  for (faction in names(decisions)) {
    dec <- decisions[[faction]]
    res <- if (!is.null(results[[faction]])) results[[faction]] else list()

    # Get faction display name
    faction_name <- if (!is.null(dec$faction_name)) {
      dec$faction_name
    } else {
      faction
    }

    # Check if multi-action system (has all_actions_with_status list)
    if (!is.null(dec$all_actions_with_status) && length(dec$all_actions_with_status) > 0) {
      # Multi-action system: create one row per action (approved, vetoed, or counter-proposed)

      # Build a lookup table for individual results by action name
      individual_results_lookup <- list()
      if (!is.null(res$individual_results)) {
        for (ir in res$individual_results) {
          if (!is.null(ir$action)) {
            individual_results_lookup[[ir$action]] <- ir
          }
        }
      }

      # Track which individual result index we're at for approved actions
      approved_action_idx <- 0

      for (i in seq_along(dec$all_actions_with_status)) {
        action_item <- dec$all_actions_with_status[[i]]

        # Determine which action name to use
        final_action <- if (!is.null(action_item$final_action)) {
          action_item$final_action
        } else {
          action_item$proposed_action
        }

        # Determine success status (only for executed actions)
        action_success <- NA
        result_msg <- ""

        if (action_item$approval_status == "approved" || action_item$approval_status == "counter_proposed") {
          approved_action_idx <- approved_action_idx + 1

          # Try to find individual result for this action
          individual_result <- NULL

          # First try by action name
          if (!is.null(final_action) && final_action %in% names(individual_results_lookup)) {
            individual_result <- individual_results_lookup[[final_action]]
          }

          # Fallback: try by index in individual_results
          if (is.null(individual_result) && !is.null(res$individual_results) &&
              approved_action_idx <= length(res$individual_results)) {
            individual_result <- res$individual_results[[approved_action_idx]]
          }

          # Extract success from individual result
          if (!is.null(individual_result) && !is.null(individual_result$success)) {
            action_success <- individual_result$success
            # Get result message from individual result
            if (!is.null(individual_result$effects$message)) {
              result_msg <- individual_result$effects$message
            } else {
              result_msg <- if (action_success) "Action succeeded" else "Action failed"
            }
          } else {
            # Fallback to overall result (should rarely happen now)
            action_success <- if (!is.null(res$success)) res$success else TRUE
            result_msg <- sprintf("%s action %d/%d (%s priority)",
                                 tools::toTitleCase(gsub("_", " ", action_item$approval_status)),
                                 i, length(dec$all_actions_with_status),
                                 action_item$priority)
          }
        } else {
          # Vetoed actions don't execute
          action_success <- NA
          result_msg <- sprintf("Vetoed action (%s priority)", action_item$priority)
        }

        action_rows <- c(action_rows, list(data.frame(
          period = period,
          faction = faction,
          faction_name = faction_name,
          decision_maker = if (!is.null(dec$decision_maker)) dec$decision_maker else NA,
          decision_maker_role = if (!is.null(dec$decision_maker_role)) dec$decision_maker_role else "government",
          proposed_by = if (!is.null(action_item$proposed_by)) action_item$proposed_by else NA,
          proposed_by_role = if (!is.null(action_item$proposed_by_role)) action_item$proposed_by_role else NA,
          timestamp = as.character(if (!is.null(dec$timestamp)) dec$timestamp else Sys.time()),
          proposed_action = if (!is.null(action_item$proposed_action)) action_item$proposed_action else NA,
          final_action = final_action,
          approval_status = if (!is.null(action_item$approval_status)) action_item$approval_status else NA,
          domain = if (!is.null(action_item$domain)) action_item$domain else NA,
          priority = if (!is.null(action_item$priority)) action_item$priority else NA,
          target = if (!is.null(action_item$target) && !is.na(action_item$target)) action_item$target else NA,
          proposal_rationale = if (!is.null(action_item$proposal_rationale)) action_item$proposal_rationale else NA,
          decision_rationale = if (!is.null(action_item$decision_rationale)) action_item$decision_rationale else NA,
          success = action_success,
          result_message = result_msg,
          stringsAsFactors = FALSE
        )))
      }
    } else if (!is.null(dec$approved_actions) && length(dec$approved_actions) > 0) {
      # Fallback: Old multi-action system (only approved actions)

      # Build a lookup table for individual results by action name
      individual_results_lookup <- list()
      if (!is.null(res$individual_results)) {
        for (ir in res$individual_results) {
          if (!is.null(ir$action)) {
            individual_results_lookup[[ir$action]] <- ir
          }
        }
      }

      for (i in seq_along(dec$approved_actions)) {
        action_item <- dec$approved_actions[[i]]

        # Look up individual result for this action
        action_name <- if (!is.null(action_item$action)) action_item$action else NA
        individual_result <- NULL
        if (!is.null(action_name) && action_name %in% names(individual_results_lookup)) {
          individual_result <- individual_results_lookup[[action_name]]
        } else if (!is.null(res$individual_results) && i <= length(res$individual_results)) {
          individual_result <- res$individual_results[[i]]
        }

        # Get success from individual result
        action_success <- if (!is.null(individual_result) && !is.null(individual_result$success)) {
          individual_result$success
        } else if (!is.null(res$success)) {
          res$success
        } else {
          TRUE
        }

        result_msg <- if (!is.null(action_item$is_counter) && action_item$is_counter) {
          sprintf("Counter-proposal %d/%d (%s priority, was: %s) - %s",
                 i, length(dec$approved_actions),
                 if(!is.null(action_item$priority)) action_item$priority else "unknown",
                 if(!is.null(action_item$original_action)) action_item$original_action else "unknown",
                 if(action_success) "SUCCESS" else "FAILED")
        } else {
          # Try to get message from individual result
          if (!is.null(individual_result$effects$message)) {
            individual_result$effects$message
          } else {
            sprintf("Multi-action %d/%d (%s priority) - %s",
                   i, length(dec$approved_actions),
                   if(!is.null(action_item$priority)) action_item$priority else "unknown",
                   if(action_success) "SUCCESS" else "FAILED")
          }
        }

        action_rows <- c(action_rows, list(data.frame(
          period = period,
          faction = faction,
          faction_name = faction_name,
          decision_maker = if (!is.null(dec$decision_maker)) dec$decision_maker else NA,
          decision_maker_role = "government",
          proposed_by = if (!is.null(action_item$proposed_by)) action_item$proposed_by else NA,
          proposed_by_role = if (!is.null(action_item$proposed_by_role)) action_item$proposed_by_role else NA,
          timestamp = as.character(if (!is.null(dec$timestamp)) dec$timestamp else Sys.time()),
          proposed_action = if (!is.null(action_item$original_action)) action_item$original_action else action_item$action,
          final_action = if (!is.null(action_item$action)) action_item$action else NA,
          approval_status = if (!is.null(action_item$is_counter) && action_item$is_counter) "counter_proposed" else "approved",
          domain = if (!is.null(action_item$domain)) action_item$domain else NA,
          priority = if (!is.null(action_item$priority)) action_item$priority else NA,
          target = if (!is.null(action_item$target) && !is.na(action_item$target)) action_item$target else NA,
          proposal_rationale = if (!is.null(action_item$rationale)) action_item$rationale else NA,
          decision_rationale = if (!is.null(action_item$approval_rationale)) action_item$approval_rationale else NA,
          success = action_success,
          result_message = result_msg,
          stringsAsFactors = FALSE
        )))
      }
    } else if (!is.null(dec$action)) {
      # Single-action system (external actors)
      # Look up domain from action definition
      action_domain <- NA
      if (!is.null(dec$action)) {
        # Try to get action definition to find category/domain
        tryCatch({
          if (exists("get_action_definition")) {
            action_def <- get_action_definition(dec$action)
            if (!is.null(action_def) && !is.null(action_def$category)) {
              action_domain <- action_def$category
            }
          }
        }, error = function(e) {
          # Fallback: infer domain from action name
          action_domain <- infer_action_domain(dec$action)
        })

        # Fallback if get_action_definition didn't work
        if (is.na(action_domain)) {
          action_domain <- infer_action_domain(dec$action)
        }
      }

      action_rows <- c(action_rows, list(data.frame(
        period = period,
        faction = faction,
        faction_name = faction_name,
        decision_maker = if (!is.null(dec$agent_name)) dec$agent_name else NA,
        decision_maker_role = if (!is.null(dec$agent_role)) dec$agent_role else NA,
        proposed_by = NA,  # Single-action doesn't have separate proposer
        proposed_by_role = NA,
        timestamp = as.character(if (!is.null(dec$timestamp)) dec$timestamp else Sys.time()),
        proposed_action = if (!is.null(dec$action)) dec$action else NA,
        final_action = if (!is.null(dec$action)) dec$action else NA,
        approval_status = "approved",
        domain = action_domain,
        priority = "primary",  # Single action is always the primary action
        target = if (!is.null(dec$target) && !is.na(dec$target)) dec$target else NA,
        proposal_rationale = if (!is.null(dec$reasoning)) dec$reasoning else NA,
        decision_rationale = if (!is.null(dec$expected_outcome)) dec$expected_outcome else NA,
        success = if (!is.null(res$success)) res$success else NA,
        result_message = if (!is.null(res$effects$message)) res$effects$message else NA,
        stringsAsFactors = FALSE
      )))
    }
  }

  if (length(action_rows) > 0) {
    actions_df <- do.call(rbind, action_rows)
  } else {
    actions_df <- data.frame(
      period = integer(),
      faction = character(),
      faction_name = character(),
      decision_maker = character(),
      decision_maker_role = character(),
      proposed_by = character(),
      proposed_by_role = character(),
      timestamp = character(),
      proposed_action = character(),
      final_action = character(),
      approval_status = character(),
      domain = character(),
      priority = character(),
      target = character(),
      proposal_rationale = character(),
      decision_rationale = character(),
      success = logical(),
      result_message = character(),
      stringsAsFactors = FALSE
    )
  }

  # Replace NA with empty strings for better CSV readability
  actions_df[is.na(actions_df)] <- ""

  write.csv(actions_df, actions_file, row.names = FALSE, na = "")

  cat(sprintf("  Saved actions to CSV: %s\n", actions_file))

  return(actions_file)
}

#' Combine all period CSVs into master files
#'
#' Reads all period-specific CSV files and combines them into comprehensive files
#'
#' @param output_dir Directory with CSV files (default: "outputs/interactions")
#' @return List with paths to master files
combine_all_csvs <- function(output_dir = "outputs/interactions") {
  # Find all period files
  summary_files <- list.files(output_dir, pattern = "period_\\d+_interactions_summary\\.csv", full.names = TRUE)
  message_files <- list.files(output_dir, pattern = "period_\\d+_interactions_messages\\.csv", full.names = TRUE)
  coord_files <- list.files(output_dir, pattern = "period_\\d+_coordination\\.csv", full.names = TRUE)
  action_files <- list.files(output_dir, pattern = "period_\\d+_actions\\.csv", full.names = TRUE)

  # Combine each type
  master_files <- list()

  if (length(summary_files) > 0) {
    all_summary <- do.call(rbind, lapply(summary_files, read.csv, stringsAsFactors = FALSE))
    master_summary <- file.path(output_dir, "all_interactions_summary.csv")
    write.csv(all_summary, master_summary, row.names = FALSE)
    master_files$summary <- master_summary
  }

  if (length(message_files) > 0) {
    all_messages <- do.call(rbind, lapply(message_files, read.csv, stringsAsFactors = FALSE))
    master_messages <- file.path(output_dir, "all_interactions_messages.csv")
    write.csv(all_messages, master_messages, row.names = FALSE)
    master_files$messages <- master_messages
  }

  if (length(coord_files) > 0) {
    all_coord <- do.call(rbind, lapply(coord_files, read.csv, stringsAsFactors = FALSE))
    master_coord <- file.path(output_dir, "all_coordination.csv")
    write.csv(all_coord, master_coord, row.names = FALSE)
    master_files$coordination <- master_coord
  }

  if (length(action_files) > 0) {
    all_actions <- do.call(rbind, lapply(action_files, read.csv, stringsAsFactors = FALSE))
    master_actions <- file.path(output_dir, "all_actions.csv")
    write.csv(all_actions, master_actions, row.names = FALSE)
    master_files$actions <- master_actions
  }

  cat(sprintf("Combined all period CSVs into master files in %s\n", output_dir))

  return(master_files)
}
