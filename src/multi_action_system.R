# Multi-Action Proposal and Approval System
#
# Implements domain expert proposal system where:
# 1. Each domain expert (Military, Intel, Diplomatic, Economic) proposes 1-3 actions
# 2. President/Government reviews all proposals and approves/vetoes
# 3. All approved actions execute in parallel
# 4. Effects resolved with cumulative/contradictory/synergistic logic

#' Generate domain expert action proposals
#'
#' @param faction Faction name
#' @param faction_agents List of agents in faction
#' @param coordination Coordination results from pre-action coordination
#' @param context Current context (scenario state, events, etc.)
#' @param api_key API key for LLM
#' @param state Full simulation state (for discussion history)
#' @return List of proposals by domain (military, intelligence, diplomatic, economic)
generate_domain_proposals <- function(faction, faction_agents, coordination, context, api_key, state = NULL) {
  cat(sprintf("  -> Generating domain expert proposals for %s...\n", toupper(faction)))

  # Identify available domain experts
  domains <- list()

  # Military domain
  mil_agents <- Filter(function(a) a$role == "military", faction_agents)
  if (length(mil_agents) > 0) {
    domains$military <- mil_agents[[1]]
  }

  # Intelligence domain
  intel_agents <- Filter(function(a) a$role == "intelligence", faction_agents)
  if (length(intel_agents) > 0) {
    domains$intelligence <- intel_agents[[1]]
  }

  # Diplomatic domain
  dip_agents <- Filter(function(a) a$role %in% c("diplomatic", "foreign_government"), faction_agents)
  if (length(dip_agents) > 0) {
    domains$diplomatic <- dip_agents[[1]]
  }

  # Economic domain
  econ_agents <- Filter(function(a) a$role == "economic", faction_agents)
  if (length(econ_agents) > 0) {
    domains$economic <- econ_agents[[1]]
  }

  # If no domain structure (external actors), return NULL (they use old single-action system)
  if (length(domains) < 2) {
    cat(sprintf("    Single decision maker faction - using traditional system\n"))
    return(NULL)
  }

  # v3.11: Sequential per-agent LLM calls
  # Each agent gets a focused prompt with only their domain info.
  # Later agents see prior agents' proposals (sequential conditioning).
  # This creates genuine inter-agent interaction for PID to detect.

  # Extract coordination summary (shared across all agents)
  coord_summary <- ""
  if (!is.null(coordination) && !is.null(coordination$messages)) {
    coord_summary <- "COORDINATION DISCUSSION SUMMARY:\n"
    for (msg in coordination$messages[1:min(6, length(coordination$messages))]) {
      coord_summary <- paste0(coord_summary,
                             sprintf("- %s recommended: %s\n",
                                    msg$sender_name,
                                    substr(msg$content, 1, 100)))
    }
  }

  # Get previous period discussions for context (v3.8.2)
  previous_discussions <- ""
  if (!is.null(state) && !is.null(context$period) && context$period > 1) {
    rep_agent <- domains[[1]]
    if (!is.null(rep_agent)) {
      previous_discussions <- format_previous_discussions(state, context$period, rep_agent)
    }
  }

  # Build shared situation context
  situation_context <- build_situation_context(context, faction)

  # Proposal order: military first, then intelligence, economic, diplomatic
  # (military sets the tone, others react)
  domain_order <- intersect(c("military", "intelligence", "economic", "diplomatic"), names(domains))

  proposals <- list()
  prior_proposals_text <- ""

  for (domain_name in domain_order) {
    agent <- domains[[domain_name]]
    cat(sprintf("    [%s] %s proposing...\n", toupper(domain_name), agent$name))

    # Build focused prompt for this single agent
    agent_prompt <- build_single_agent_prompt(
      domain_name = domain_name,
      agent = agent,
      faction = faction,
      situation_context = situation_context,
      coord_summary = coord_summary,
      prior_proposals = prior_proposals_text,
      previous_discussions = previous_discussions,
      context = context
    )

    system_prompt <- sprintf(
      "You are %s, the %s expert for your faction. Propose 1-3 actions from your domain of expertise.",
      agent$name, domain_name
    )

    # Individual LLM call for this agent
    response <- call_llm(system_prompt, agent_prompt, AGENT_MODEL, api_key)

    # Parse single-agent response
    agent_proposals <- parse_single_agent_proposal(response, domain_name, agent)

    if (!is.null(agent_proposals)) {
      proposals[[domain_name]] <- agent_proposals

      # Build text of this agent's proposals for next agent to see
      prior_proposals_text <- paste0(prior_proposals_text, sprintf(
        "\n%s (%s) has proposed:\n", toupper(domain_name), agent$name
      ))
      for (priority in c("primary", "secondary", "tertiary")) {
        if (!is.null(agent_proposals[[priority]])) {
          prior_proposals_text <- paste0(prior_proposals_text, sprintf(
            "  %s: %s%s\n",
            toupper(priority),
            agent_proposals[[priority]]$action,
            if (!is.null(agent_proposals[[priority]]$rationale) && nchar(agent_proposals[[priority]]$rationale) > 0)
              sprintf(" - %s", agent_proposals[[priority]]$rationale) else ""
          ))
        }
      }
    }
  }

  # Display proposals
  cat(sprintf("\n    PROPOSED ACTIONS:\n"))
  for (domain in names(proposals)) {
    cat(sprintf("    %s (%s):\n", toupper(domain), proposals[[domain]]$agent_name))
    if (!is.null(proposals[[domain]]$primary)) {
      cat(sprintf("      PRIMARY: %s\n", proposals[[domain]]$primary$action))
    }
    if (!is.null(proposals[[domain]]$secondary)) {
      cat(sprintf("      SECONDARY: %s\n", proposals[[domain]]$secondary$action))
    }
    if (!is.null(proposals[[domain]]$tertiary)) {
      cat(sprintf("      TERTIARY: %s\n", proposals[[domain]]$tertiary$action))
    }
  }
  cat("\n")

  return(proposals)
}


# ===========================================================================
# v3.11: Per-agent sequential proposal system
# ===========================================================================

#' Build shared situation context (used by all agents)
build_situation_context <- function(context, faction) {
  ss <- context$scenario_state
  situation_block <- sprintf(
    "CURRENT SITUATION:\n  Crisis Level: %.1f / 10\n  Military Balance: %+.2f (negative = favors Novaris, positive = favors Tethys)\n  Territory Under Enemy Control: %.1f%%\n  Economic Sanctions Severity: %.0f%%\n  International Support for Tethys: %.0f%%",
    if(!is.null(ss$crisis_level)) ss$crisis_level else 5,
    if(!is.null(ss$military_balance)) ss$military_balance else 0,
    if(!is.null(ss$territory_controlled)) ss$territory_controlled * 100 else 0,
    if(!is.null(ss$sanctions_level)) ss$sanctions_level * 100 else 0,
    if(!is.null(ss$international_support)) ss$international_support * 100 else 50
  )

  # Add events if present
  events_block <- ""
  if (!is.null(context$recent_events) && length(context$recent_events) > 0) {
    event_list <- paste(sapply(context$recent_events, function(e) {
      sprintf("  - %s: %s", e$name, e$description)
    }), collapse = "\n")
    events_block <- sprintf("\n\nRECENT EVENTS:\n%s", event_list)
  }

  paste0(situation_block, events_block)
}


#' Build dynamic conditional guidance for a specific domain
#' (Extracted from build_proposal_prompt for reuse in per-agent prompts)
build_domain_guidance <- function(domain_name, context, faction) {
  ss <- context$scenario_state
  crisis <- if(!is.null(ss$crisis_level)) ss$crisis_level else 5
  balance <- if(!is.null(ss$military_balance)) ss$military_balance else 0
  territory <- if(!is.null(ss$territory_controlled)) ss$territory_controlled else 0
  sanctions <- if(!is.null(ss$sanctions_level)) ss$sanctions_level else 0
  support <- if(!is.null(ss$international_support)) ss$international_support else 0.5

  is_novaris <- grepl("novaris|major", tolower(faction))
  effective_balance <- if (is_novaris) -balance else balance

  if (domain_name == "military") {
    if (effective_balance > 0.1) {
      return(sprintf("SITUATION: FAVORABLE (your advantage=%+.2f, crisis=%.1f, territory=%.0f%%)\nRECOMMENDED: Press the advantage with limited_strike, naval_deployment, or border_incursion.\nAVOID: Do NOT choose defensive actions when you have the initiative.", effective_balance, crisis, territory * 100))
    } else if (effective_balance < -0.2 || territory > 0.25) {
      return(sprintf("SITUATION: UNFAVORABLE (balance=%+.2f, territory=%.0f%%)\nRECOMMENDED: Stabilize with defensive_reinforcements, defensive_fortification, or enhanced_patrols.\nAVOID: Do NOT propose limited_strike or border_incursion when strained.", effective_balance, territory * 100))
    } else if (crisis > 8) {
      return(sprintf("SITUATION: CRISIS (crisis=%.1f)\nRECOMMENDED: Decisive action - limited_strike to break deadlock OR defensive_fortification to prevent collapse.\nAVOID: Do NOT choose show_of_force or military_exercises - time for posturing is past.", crisis))
    } else {
      return(sprintf("SITUATION: BALANCED (balance=%+.2f, crisis=%.1f)\nRECOMMENDED: Posture to shift balance with military_buildup, show_of_force, or naval_demonstration.\nAVOID: Do NOT default to military_buildup every time - vary your approach.", effective_balance, crisis))
    }
  }

  if (domain_name == "intelligence") {
    if (crisis < 5 && territory < 0.1) {
      return(sprintf("SITUATION: LOW THREAT (crisis=%.1f, territory=%.0f%%)\nRECOMMENDED: intelligence_gathering, enhanced_surveillance, or reconnaissance. Build the picture first.\nAVOID: Do NOT propose sabotage or cyber_attack - offensive operations risk escalating a manageable situation.", crisis, territory * 100))
    } else if (crisis < 5 && territory >= 0.1) {
      return(sprintf("SITUATION: LOW CRISIS, TERRITORIAL PRESSURE (crisis=%.1f, territory=%.0f%%)\nRECOMMENDED: counterintelligence or share_intelligence to protect operations. Consider information_campaign.\nAVOID: Do NOT default to sabotage - crisis is low enough that aggression risks blowback.", crisis, territory * 100))
    } else if (crisis >= 5 && crisis <= 7) {
      return(sprintf("SITUATION: MODERATE (crisis=%.1f)\nRECOMMENDED: cyber_defense, counterintelligence, or information_campaign to shape the info environment.\nAVOID: Do NOT default to sabotage - at moderate crisis, defensive intel and info ops are higher priority.", crisis))
    } else if (crisis > 7 && effective_balance > 0) {
      return(sprintf("SITUATION: HIGH CRISIS, FAVORABLE (crisis=%.1f, your advantage=%+.2f)\nRECOMMENDED: sabotage or cyber_attack to press advantage covertly.\nAVOID: Do NOT choose intelligence_gathering - you have the picture, now act on it.", crisis, effective_balance))
    } else {
      return(sprintf("SITUATION: HIGH CRISIS, DEFENSIVE (crisis=%.1f, balance=%+.2f)\nRECOMMENDED: counterintelligence to protect forces, then cyber_defense against enemy cyber ops.\nAVOID: Do NOT default to offensive cyber_attack when your own systems need protection first.", crisis, effective_balance))
    }
  }

  if (domain_name == "economic") {
    extra <- ""
    if (territory > 0.25) {
      extra <- sprintf(" Territory loss at %.0f%% - consider currency_manipulation or resource_embargo.", territory * 100)
    }
    if (sanctions > 0.6) {
      return(sprintf("SITUATION: SANCTIONS SATURATED (sanctions=%.0f%%)\nRECOMMENDED: war_bonds, trade_restrictions, or trade_negotiation. Additional sanctions have diminishing returns.\nAVOID: Do NOT propose strategic_stockpiling as PRIMARY - stockpiling is passive, your faction needs ACTIVE measures.%s", sanctions * 100, extra))
    } else if (sanctions > 0.3) {
      return(sprintf("SITUATION: MODERATE SANCTIONS (sanctions=%.0f%%, support=%.0f%%)\nRECOMMENDED: targeted_sanctions, economic_sanctions, or asset_seizure - room to tighten.\nAVOID: Do NOT default to strategic_stockpiling - sanctions still have room to bite.%s", sanctions * 100, support * 100, extra))
    } else if (support > 0.5) {
      return(sprintf("SITUATION: LOW SANCTIONS, COALITION OPPORTUNITY (sanctions=%.0f%%, support=%.0f%%)\nRECOMMENDED: economic_sanctions or resource_embargo backed by international coalition.\nAVOID: Do NOT choose strategic_stockpiling when you have unused economic leverage.%s", sanctions * 100, support * 100, extra))
    } else {
      return(sprintf("SITUATION: LOW SANCTIONS, LIMITED SUPPORT (sanctions=%.0f%%, support=%.0f%%)\nRECOMMENDED: trade_negotiation or financial_aid to build alliances and strengthen position.\nAVOID: Do NOT propose broad sanctions without coalition support.%s", sanctions * 100, support * 100, extra))
    }
  }

  if (domain_name == "diplomatic") {
    if (support > 0.7) {
      return(sprintf("SITUATION: STRONG SUPPORT (%.0f%%)\nRECOMMENDED: coalition_building, formal_multilateral_engagement, or international_observers.\nAVOID: Do NOT propose backchannel_negotiations - your public position is strong, use it openly.", support * 100))
    } else if (support > 0.5 && crisis > 7) {
      return(sprintf("SITUATION: MODERATE SUPPORT, HIGH CRISIS (support=%.0f%%, crisis=%.1f)\nRECOMMENDED: humanitarian_corridors or peace_talks for moral high ground, plus coalition_building.\nAVOID: Do NOT ignore humanitarian dimensions.", support * 100, crisis))
    } else if (support > 0.5) {
      return(sprintf("SITUATION: MODERATE SUPPORT, MANAGEABLE CRISIS (support=%.0f%%, crisis=%.1f)\nRECOMMENDED: public_diplomatic_initiative, formal_multilateral_engagement, or cultural_exchange.\nAVOID: Do NOT default to coalition_building - diversify your tools.", support * 100, crisis))
    } else if (crisis > 7) {
      return(sprintf("SITUATION: WEAK SUPPORT, HIGH CRISIS (support=%.0f%%, crisis=%.1f)\nRECOMMENDED: backchannel_negotiations and diplomatic_visit to find any off-ramp.\nAVOID: Do NOT propose coalition_building when support is too low.", support * 100, crisis))
    } else {
      return(sprintf("SITUATION: LOW SUPPORT (%.0f%%)\nRECOMMENDED: diplomatic_visit, backchannel_negotiations, trade_negotiation to build relationships.\nAVOID: Do NOT propose formal_multilateral_engagement without sufficient support base.", support * 100))
    }
  }

  return("")
}


#' Get action categories for a specific domain
get_domain_actions <- function(domain_name) {
  if (domain_name == "military") {
    return("YOUR ACTION OPTIONS:
  Defensive: defensive_fortification, defensive_reinforcements, troop_movements, air_patrols, enhanced_patrols, reconnaissance
  Posturing: military_buildup, show_of_force, military_exercises, naval_deployment, naval_patrols, naval_demonstration
  Offensive: limited_strike, border_incursion, occupation, blockade, siege_warfare")
  }
  if (domain_name == "intelligence") {
    return("YOUR ACTION OPTIONS:
  Collection: intelligence_gathering, enhanced_intelligence_gathering, surveillance_operation, enhanced_surveillance, share_intelligence
  Defense: counterintelligence, cyber_defense
  Offensive: sabotage, cyber_attack, cyber_theft, leadership_targeting, false_flag_operation
  Information: spread_disinformation, propaganda_campaign, information_campaign")
  }
  if (domain_name == "economic") {
    return("YOUR ACTION OPTIONS:
  Punishment: economic_sanctions, targeted_sanctions, resource_embargo, trade_restrictions, asset_seizure
  Incentives: trade_agreement, financial_aid, trade_negotiation
  Financial warfare: currency_manipulation, strategic_stockpiling, war_bonds")
  }
  if (domain_name == "diplomatic") {
    return("YOUR ACTION OPTIONS:
  De-escalation: peace_talks, formal_peace_talks, diplomatic_visit, mediation_offer, cultural_exchange
  Coalition: coalition_building, backchannel_negotiations, joint_exercises, formal_multilateral_engagement, international_observers
  Humanitarian: prisoner_exchange, humanitarian_corridors, humanitarian_aid, public_diplomatic_initiative")
  }
  return("")
}


#' Build a focused prompt for a single domain expert
build_single_agent_prompt <- function(domain_name, agent, faction, situation_context,
                                      coord_summary, prior_proposals, previous_discussions,
                                      context) {
  hawk_pct <- round(agent$hawk_dove * 100)
  worldview <- if(!is.null(agent$worldview)) agent$worldview else "pragmatic"

  # Get dynamic guidance for this domain
  guidance <- build_domain_guidance(domain_name, context, faction)

  # Get action categories for this domain only
  actions <- get_domain_actions(domain_name)

  # Build prior proposals block (empty for first agent)
  prior_block <- ""
  if (nchar(prior_proposals) > 0) {
    prior_block <- sprintf("
OTHER EXPERTS HAVE ALREADY PROPOSED:
%s
Consider how your proposal COMPLEMENTS or BALANCES their actions.
If they are escalating, you might provide a defensive or stabilizing option, or reinforce their approach.
If they are being cautious, you might push for more assertive action in your domain, or support their restraint.
Your proposal should reflect awareness of what has already been proposed.
", prior_proposals)
  }

  # Build previous discussions block
  prev_block <- ""
  if (nchar(previous_discussions) > 0) {
    prev_block <- sprintf("\n%s\n", previous_discussions)
  }

  prompt <- sprintf("
You are %s, %s expert (%d%% hawk, worldview: %s).
Faction: %s

%s
%s
%s%s
STRATEGIC GUIDANCE FOR YOUR DOMAIN:
%s

%s

%s

Propose 1-3 actions from YOUR domain:
- PRIMARY: Your most important action (REQUIRED). Follow the RECOMMENDED action from your guidance above.
- SECONDARY: A supporting action from your domain (optional)
- TERTIARY: An additional action if warranted (optional)

Your hawk/dove orientation should influence HOW AGGRESSIVELY you act within the recommended category,
not WHETHER you follow the recommendation.

RESPOND IN THIS EXACT FORMAT (nothing else):

<proposals>
PRIMARY: action_name [TARGET: target] - Brief rationale (1 sentence)
SECONDARY: action_name [TARGET: target] - Brief rationale (1 sentence)
TERTIARY: action_name [TARGET: target] - Brief rationale (1 sentence)
</proposals>

TARGET OPTIONS: Tethys, Novaris, self, none, or specific country names.
Use EXACT action names from the list above. Keep rationales to 1 sentence.
",
    agent$name, domain_name, hawk_pct, worldview,
    toupper(gsub("_", " ", faction)),
    situation_context,
    coord_summary,
    prior_block,
    prev_block,
    guidance,
    actions,
    if (nchar(prior_block) > 0) "Remember: other experts have already proposed actions. Your proposal should complement theirs." else ""
  )

  return(prompt)
}


#' Parse a single agent's proposal response
parse_single_agent_proposal <- function(response, domain_name, agent) {
  proposal <- list(
    agent_name = agent$name,
    agent_role = agent$role,
    agent_hawk_dove = agent$hawk_dove
  )

  # Extract content between <proposals> tags
  content <- response
  prop_match <- regexpr("<proposals>(.+?)</proposals>", response, perl = TRUE, ignore.case = TRUE)
  if (prop_match > 0) {
    content <- regmatches(response, prop_match)[[1]]
    content <- sub("<proposals>\\s*", "", content, ignore.case = TRUE)
    content <- sub("\\s*</proposals>", "", content, ignore.case = TRUE)
  }

  lines <- strsplit(content, "\n")[[1]]

  for (line in lines) {
    line <- trimws(line)
    if (line == "") next

    if (grepl("^(PRIMARY|SECONDARY|TERTIARY):", line, ignore.case = TRUE)) {
      priority_match <- regmatches(line, regexpr("^(PRIMARY|SECONDARY|TERTIARY)", line, ignore.case = TRUE))
      if (length(priority_match) > 0) {
        priority <- tolower(priority_match[1])

        rest <- sub("^(PRIMARY|SECONDARY|TERTIARY):\\s*", "", line, ignore.case = TRUE)
        parts <- strsplit(rest, " - ")[[1]]

        if (length(parts) >= 1) {
          action_part <- trimws(parts[1])
          rationale <- if(length(parts) >= 2) trimws(paste(parts[-1], collapse = " - ")) else ""

          # Extract target
          target <- NULL
          if (grepl("\\[TARGET:", action_part, ignore.case = TRUE)) {
            target_match <- regmatches(action_part, regexpr("\\[TARGET:[^]]+\\]", action_part, ignore.case = TRUE))
            if (length(target_match) > 0) {
              target <- sub("\\[TARGET:\\s*", "", target_match, ignore.case = TRUE)
              target <- sub("\\]", "", target)
              target <- trimws(target)
            }
            action_part <- sub("\\[TARGET:[^]]+\\]", "", action_part, ignore.case = TRUE)
            action_part <- trimws(action_part)
          }

          proposal[[priority]] <- list(
            action = action_part,
            target = target,
            rationale = rationale
          )
        }
      }
    }
  }

  # Verify we got at least a primary
  if (is.null(proposal$primary)) {
    cat(sprintf("    WARNING: Failed to parse %s proposal, attempting fallback\n", domain_name))
    # Try to find any action name in the response
    all_actions <- c("intelligence_gathering", "enhanced_intelligence_gathering", "surveillance_operation",
                     "enhanced_surveillance", "share_intelligence", "counterintelligence", "cyber_defense",
                     "sabotage", "cyber_attack", "cyber_theft", "leadership_targeting", "false_flag_operation",
                     "spread_disinformation", "propaganda_campaign", "information_campaign",
                     "military_buildup", "show_of_force", "military_exercises", "naval_deployment",
                     "defensive_fortification", "defensive_reinforcements", "limited_strike",
                     "enhanced_patrols", "naval_demonstration", "reconnaissance",
                     "coalition_building", "backchannel_negotiations", "peace_talks", "humanitarian_corridors",
                     "diplomatic_visit", "international_observers", "humanitarian_aid",
                     "economic_sanctions", "targeted_sanctions", "resource_embargo", "trade_restrictions",
                     "strategic_stockpiling", "war_bonds", "trade_negotiation", "financial_aid",
                     "asset_seizure", "currency_manipulation", "trade_agreement")
    for (act in all_actions) {
      if (grepl(act, response, ignore.case = TRUE)) {
        proposal$primary <- list(action = act, target = NULL, rationale = "fallback parse")
        cat(sprintf("    Fallback found: %s\n", act))
        break
      }
    }
  }

  if (is.null(proposal$primary)) {
    cat(sprintf("    ERROR: Could not parse any proposal for %s\n", domain_name))
    return(NULL)
  }

  return(proposal)
}


# ===========================================================================
# Legacy: Original combined prompt builder (kept for reference, no longer called)
# ===========================================================================

#' Build prompt for domain expert proposals (LEGACY - replaced by per-agent system)
build_proposal_prompt <- function(domains, coordination, context, faction, state = NULL) {
  # Extract coordination summary
  coord_summary <- ""
  if (!is.null(coordination) && !is.null(coordination$messages)) {
    coord_summary <- "COORDINATION DISCUSSION SUMMARY:\n"
    for (msg in coordination$messages[1:min(6, length(coordination$messages))]) {
      coord_summary <- paste0(coord_summary,
                             sprintf("- %s recommended: %s\n",
                                    msg$sender_name,
                                    substr(msg$content, 1, 100)))
    }
  }

  # Get previous period discussions for context (v3.8.2)
  previous_discussions <- ""
  if (!is.null(state) && !is.null(context$period) && context$period > 1) {
    # Get a representative agent from this faction to filter relevant discussions
    rep_agent <- domains[[1]]
    if (!is.null(rep_agent)) {
      previous_discussions <- format_previous_discussions(state, context$period, rep_agent)
      # Debug: Log if discussion memory is active for multi-action system
      if (nchar(previous_discussions) > 0) {
        cat(sprintf("    DEBUG: Multi-action discussion memory active - %d chars included in proposal prompt\n", nchar(previous_discussions)))
      }
    }
  }

  # Build domain expert descriptions with domain-specific parameter emphasis
  # and primary action guidance (v3.10+: domain differentiation for emergent coordination)
  # v3.11: Dynamic conditional guidance computed from ACTUAL scenario parameters
  #        to produce genuine parameter-sensitive action variation across scenarios

  ss <- context$scenario_state
  crisis <- if(!is.null(ss$crisis_level)) ss$crisis_level else 5
  balance <- if(!is.null(ss$military_balance)) ss$military_balance else 0
  territory <- if(!is.null(ss$territory_controlled)) ss$territory_controlled else 0
  sanctions <- if(!is.null(ss$sanctions_level)) ss$sanctions_level else 0
  support <- if(!is.null(ss$international_support)) ss$international_support else 0.5

  # Determine faction role (aggressor vs defender)
  is_novaris <- grepl("novaris|major", tolower(faction))

  # Effective balance from THIS faction's perspective
  # military_balance: negative = favors Novaris, positive = favors Tethys
  # For Novaris: flip sign so positive = their advantage
  effective_balance <- if (is_novaris) -balance else balance

  # --- MILITARY conditional guidance (dynamic) ---
  if (effective_balance > 0.1) {
    mil_situation <- "FAVORABLE"
    mil_recommendation <- "You have a military advantage. Press it: limited_strike, naval_deployment, or border_incursion to exploit momentum before the window closes."
    mil_avoid <- "Do NOT choose purely defensive actions (defensive_fortification, enhanced_patrols) when you have the initiative."
  } else if (effective_balance < -0.2 || territory > 0.25) {
    mil_situation <- "UNFAVORABLE"
    mil_recommendation <- "Your forces are under pressure. Prioritize: defensive_reinforcements, defensive_fortification, or enhanced_patrols to stabilize before considering offensive action."
    mil_avoid <- "Do NOT propose limited_strike or border_incursion when your forces are already strained."
  } else if (crisis > 8) {
    mil_situation <- "CRISIS"
    mil_recommendation <- "Extreme crisis demands decisive action. Choose: limited_strike to break the deadlock, OR defensive_fortification to prevent collapse. No half-measures."
    mil_avoid <- "Do NOT choose show_of_force or military_exercises — the time for posturing is past."
  } else {
    mil_situation <- "BALANCED"
    mil_recommendation <- "Forces are roughly balanced. Posture to shift the balance: military_buildup, show_of_force, or military_exercises. Signal strength without overcommitting."
    mil_avoid <- "Do NOT default to military_buildup every time — consider show_of_force or naval_demonstration for variety."
  }

  # --- INTELLIGENCE conditional guidance (dynamic) ---
  if (crisis < 5 && territory < 0.1) {
    intel_situation <- "LOW THREAT"
    intel_recommendation <- "Low crisis with stable positions. YOUR PRIORITY: intelligence_gathering, enhanced_surveillance, or reconnaissance. Build the intelligence picture before acting. Offensive operations are premature and risk escalation."
    intel_primary <- "intelligence_gathering or enhanced_surveillance"
    intel_avoid <- "Do NOT propose sabotage or cyber_attack in a low-crisis environment — you risk escalating a manageable situation."
  } else if (crisis < 5 && territory >= 0.1) {
    intel_situation <- "LOW CRISIS, TERRITORIAL PRESSURE"
    intel_recommendation <- "Crisis is low but territory is contested. YOUR PRIORITY: counterintelligence and share_intelligence to protect your own operations. Consider information_campaign to shape narratives."
    intel_primary <- "counterintelligence or share_intelligence"
    intel_avoid <- "Do NOT default to sabotage — the crisis is low enough that covert aggression risks blowback."
  } else if (crisis >= 5 && crisis <= 7) {
    intel_situation <- "MODERATE"
    intel_recommendation <- "Moderate crisis requires active intelligence operations. YOUR PRIORITY: cyber_defense and counterintelligence if the enemy has cyber capabilities, OR spread_disinformation and information_campaign to shape the information environment."
    intel_primary <- "counterintelligence, cyber_defense, or information_campaign"
    intel_avoid <- "Do NOT default to sabotage — at moderate crisis, information operations and defensive intel are higher priority."
  } else if (crisis > 7 && effective_balance > 0) {
    intel_situation <- "HIGH CRISIS, FAVORABLE POSITION"
    intel_recommendation <- "High crisis but you have advantage. YOUR PRIORITY: sabotage or cyber_attack to press the advantage covertly. Exploit enemy vulnerabilities while conventional forces hold."
    intel_primary <- "sabotage or cyber_attack"
    intel_avoid <- "Do NOT choose intelligence_gathering — you already have the picture, now act on it."
  } else if (crisis > 7 && effective_balance <= 0) {
    intel_situation <- "HIGH CRISIS, DEFENSIVE"
    intel_recommendation <- "High crisis under pressure. YOUR PRIORITY: counterintelligence to protect your forces, then cyber_defense against enemy cyber operations. Sabotage only if you can disrupt enemy logistics."
    intel_primary <- "counterintelligence or cyber_defense"
    intel_avoid <- "Do NOT default to offensive cyber_attack when your own systems need protection first."
  } else {
    intel_situation <- "ACTIVE"
    intel_recommendation <- "Active conflict requires calibrated intelligence operations. Assess whether offensive (sabotage, cyber_attack) or defensive (counterintelligence, cyber_defense) operations serve the current military situation better."
    intel_primary <- "based on military situation assessment"
    intel_avoid <- "Do NOT always choose the same action — different situations demand different intelligence postures."
  }

  # --- ECONOMIC conditional guidance (dynamic) ---
  if (sanctions > 0.6) {
    econ_situation <- "SANCTIONS SATURATED"
    econ_recommendation <- sprintf("Sanctions are already at %.0f%% — additional sanctions have DIMINISHING RETURNS. YOUR PRIORITY: war_bonds to fund the war effort, OR trade_restrictions to deny specific resources, OR trade_negotiation to find alternative suppliers.", sanctions * 100)
    econ_primary <- "war_bonds, trade_restrictions, or trade_negotiation"
    econ_avoid <- "Do NOT propose strategic_stockpiling as your PRIMARY action — stockpiling is passive. Your faction needs ACTIVE economic measures."
  } else if (sanctions > 0.3 && sanctions <= 0.6) {
    econ_situation <- "MODERATE SANCTIONS"
    econ_recommendation <- sprintf("Sanctions at %.0f%% — room to tighten. YOUR PRIORITY: targeted_sanctions on key sectors, OR economic_sanctions for broader pressure, OR asset_seizure to hit adversary elites.", sanctions * 100)
    econ_primary <- "targeted_sanctions, economic_sanctions, or asset_seizure"
    econ_avoid <- "Do NOT default to strategic_stockpiling — sanctions still have room to bite."
  } else if (sanctions <= 0.3 && support > 0.5) {
    econ_situation <- "LOW SANCTIONS, COALITION OPPORTUNITY"
    econ_recommendation <- sprintf("Sanctions only at %.0f%% with %.0f%% international support — MAJOR opportunity for coalition economic pressure. YOUR PRIORITY: economic_sanctions or resource_embargo backed by international coalition.", sanctions * 100, support * 100)
    econ_primary <- "economic_sanctions or resource_embargo"
    econ_avoid <- "Do NOT choose strategic_stockpiling or war_bonds when you have unused economic leverage."
  } else if (sanctions <= 0.3 && support <= 0.5) {
    econ_situation <- "LOW SANCTIONS, LIMITED SUPPORT"
    econ_recommendation <- sprintf("Sanctions at %.0f%% but only %.0f%% international support — unilateral sanctions may backfire. YOUR PRIORITY: trade_negotiation to build economic alliances, OR financial_aid to strengthen your position.", sanctions * 100, support * 100)
    econ_primary <- "trade_negotiation or financial_aid"
    econ_avoid <- "Do NOT propose broad economic_sanctions without coalition support — they'll leak."
  } else {
    econ_situation <- "TRANSITIONAL"
    econ_recommendation <- "Reassess economic tools based on current leverage and coalition support."
    econ_primary <- "based on sanctions level and support assessment"
    econ_avoid <- "Do NOT default to strategic_stockpiling as a reflex — consider whether offensive or defensive economic action serves your faction better."
  }

  # Extra for high territory loss
  if (territory > 0.25) {
    econ_recommendation <- paste0(econ_recommendation, sprintf(" NOTE: %.0f%% territory lost — consider currency_manipulation or resource_embargo for economic warfare.", territory * 100))
  }

  # --- DIPLOMATIC conditional guidance (dynamic) ---
  if (support > 0.7) {
    diplo_recommendation <- sprintf("Strong international support (%.0f%%). Leverage it: coalition_building, formal_multilateral_engagement, or international_observers to lock in alliances.", support * 100)
    diplo_avoid <- "Do NOT propose backchannel_negotiations — your public position is strong, use it openly."
  } else if (support > 0.5 && crisis > 7) {
    diplo_recommendation <- sprintf("Moderate support (%.0f%%) under high crisis. Balance: humanitarian_corridors or peace_talks to maintain moral high ground, alongside coalition_building to solidify support.", support * 100)
    diplo_avoid <- "Do NOT ignore humanitarian dimensions — they preserve coalition cohesion."
  } else if (support > 0.5 && crisis <= 7) {
    diplo_recommendation <- sprintf("Moderate support (%.0f%%) in manageable crisis. Build frameworks: public_diplomatic_initiative, formal_multilateral_engagement, or cultural_exchange for long-term positioning.", support * 100)
    diplo_avoid <- "Do NOT default to coalition_building if support is already moderate — diversify your diplomatic tools."
  } else if (support <= 0.5 && crisis > 7) {
    diplo_recommendation <- sprintf("Weak support (%.0f%%) under high crisis — dangerous combination. YOUR PRIORITY: backchannel_negotiations and diplomatic_visit to find any off-ramp. Consider mediation_offer.", support * 100)
    diplo_avoid <- "Do NOT propose coalition_building when support is too low to build from."
  } else {
    diplo_recommendation <- sprintf("Low support (%.0f%%) in low crisis. Focus on relationship building: diplomatic_visit, backchannel_negotiations, trade_negotiation to improve your position before crisis escalates.", support * 100)
    diplo_avoid <- "Do NOT propose formal_multilateral_engagement without sufficient support base."
  }

  domain_param_emphasis <- list(
    military = list(
      params = "Military Balance and Crisis Level are your primary indicators. Territory Under Enemy Control determines operational urgency.",
      primary_actions = "MILITARY POSTURE and OPEN CONFLICT actions",
      secondary_note = "You may also consider COVERT OPERATIONS when conventional options are exhausted or too costly.",
      conditional_guidance = sprintf("YOUR SITUATION ASSESSMENT: %s (balance=%+.2f, crisis=%.1f, territory=%.0f%%)
    RECOMMENDED PRIMARY: %s
    %s", mil_situation, effective_balance, crisis, territory * 100, mil_recommendation, mil_avoid)
    ),
    intelligence = list(
      params = "Territory Under Enemy Control and Military Balance reveal the adversary's posture and vulnerabilities. Crisis Level determines operational tempo.",
      primary_actions = "INTELLIGENCE and COVERT OPERATIONS actions",
      secondary_note = "You may also consider INFORMATION actions (disinformation, propaganda) that leverage your intelligence networks.",
      conditional_guidance = sprintf("YOUR SITUATION ASSESSMENT: %s (crisis=%.1f, balance=%+.2f, territory=%.0f%%)
    %s
    RECOMMENDED PRIMARY ACTION: %s
    %s", intel_situation, crisis, effective_balance, territory * 100, intel_recommendation, intel_avoid)
    ),
    economic = list(
      params = "Economic Sanctions Severity and Territory Under Enemy Control determine your economic leverage. International Support affects coalition economic pressure.",
      primary_actions = "ECONOMIC actions",
      secondary_note = "You may also consider actions in other domains only when economic tools are genuinely inadequate for the situation.",
      conditional_guidance = sprintf("YOUR SITUATION ASSESSMENT: %s (sanctions=%.0f%%, support=%.0f%%, territory=%.0f%%)
    %s
    RECOMMENDED PRIMARY ACTION: %s
    %s", econ_situation, sanctions * 100, support * 100, territory * 100, econ_recommendation, econ_primary, econ_avoid)
    ),
    diplomatic = list(
      params = "International Support for Tethys is your primary indicator of coalition strength. Sanctions Severity and Crisis Level determine diplomatic urgency and leverage.",
      primary_actions = "DIPLOMATIC actions",
      secondary_note = "You may also consider ECONOMIC actions (trade negotiations, sanctions) that complement diplomatic strategy.",
      conditional_guidance = sprintf("YOUR SITUATION ASSESSMENT: support=%.0f%%, crisis=%.1f, territory=%.0f%%
    %s
    %s", support * 100, crisis, territory * 100, diplo_recommendation, diplo_avoid)
    )
  )

  domain_descs <- ""
  for (domain_name in names(domains)) {
    agent <- domains[[domain_name]]
    hawk_pct <- round(agent$hawk_dove * 100)

    # Get domain-specific guidance
    dpe <- domain_param_emphasis[[domain_name]]
    if (is.null(dpe)) {
      dpe <- list(
        params = "All scenario parameters are relevant to your assessment.",
        primary_actions = "actions within your area of expertise",
        secondary_note = "Consider the full range of options available."
      )
    }

    # Include conditional guidance if available
    cond_block <- ""
    if (!is.null(dpe$conditional_guidance)) {
      cond_block <- sprintf("\n  ACTION SELECTION GUIDANCE:\n  %s\n", dpe$conditional_guidance)
    }

    domain_descs <- paste0(domain_descs, sprintf(
      "\n%s (%s, %d%% hawk):\n  Role: %s\n  Worldview: %s\n  KEY PARAMETERS FOR YOUR ASSESSMENT: %s\n  PRIMARY ACTION DOMAIN: %s\n  %s%s\n",
      toupper(domain_name), agent$name, hawk_pct, agent$role,
      if(!is.null(agent$worldview)) agent$worldview else "pragmatic",
      dpe$params,
      dpe$primary_actions,
      dpe$secondary_note,
      cond_block
    ))
  }

  # Build detailed situation parameters block
  ss <- context$scenario_state
  situation_block <- sprintf(
    "Situation: %s\n\nCURRENT SCENARIO PARAMETERS (use these exact values to calibrate your proposals):\n  Crisis Level: %.1f / 10\n  Military Balance: %+.2f (negative = favors Novaris, positive = favors Tethys)\n  Territory Under Enemy Control: %.1f%%\n  Economic Sanctions Severity: %.0f%%\n  International Support for Tethys: %.0f%%",
    if(!is.null(ss$situation_summary)) substr(ss$situation_summary, 1, 500) else "Ongoing crisis",
    if(!is.null(ss$crisis_level)) ss$crisis_level else 5,
    if(!is.null(ss$military_balance)) ss$military_balance else 0,
    if(!is.null(ss$territory_controlled)) ss$territory_controlled * 100 else 0,
    if(!is.null(ss$sanctions_level)) ss$sanctions_level * 100 else 0,
    if(!is.null(ss$international_support)) ss$international_support * 100 else 50
  )

  # Build domain-specific event briefings (v3.11: events visible to experts)
  events_block <- ""
  if (!is.null(context$recent_events) && length(context$recent_events) > 0) {
    # Generic event list
    event_list <- paste(sapply(context$recent_events, function(e) {
      sprintf("  - %s: %s", e$name, e$description)
    }), collapse = "\n")

    # Domain-specific interpretations of events
    domain_interpretations <- list()
    for (e in context$recent_events) {
      etype <- if (!is.null(e$type)) e$type else ""
      ename <- if (!is.null(e$name)) e$name else "Event"
      edesc <- if (!is.null(e$description)) e$description else ""
      esev <- if (!is.null(e$severity)) round(e$severity, 2) else 0.5
      eimpact <- if (!is.null(e$impact_type)) e$impact_type else ""

      mil_note <- ""
      intel_note <- ""
      econ_note <- ""
      diplo_note <- ""

      if (etype == "battlefield") {
        mil_note <- sprintf("DIRECT: %s — reassess force posture and deployments", edesc)
        intel_note <- sprintf("Battlefield shift affects adversary morale and logistics — intelligence opportunity")
        econ_note <- sprintf("Military developments affect war costs and reconstruction burden")
        diplo_note <- sprintf("Battlefield outcome shifts negotiating leverage")
      } else if (etype == "economic" || etype == "economic_defender" || etype == "economic_aggressor") {
        mil_note <- sprintf("Economic pressure may affect military sustainment and equipment procurement")
        intel_note <- sprintf("Economic disruption creates intelligence collection opportunities")
        econ_note <- sprintf("DIRECT: %s — recalibrate sanctions/trade strategy", edesc)
        diplo_note <- sprintf("Economic developments create openings for economic diplomacy")
      } else if (etype == "diplomatic") {
        mil_note <- sprintf("Diplomatic shifts may change rules of engagement or alliance commitments")
        intel_note <- sprintf("Diplomatic developments require intelligence on counterparty intentions")
        econ_note <- sprintf("Diplomatic moves may unlock or constrain economic tools")
        diplo_note <- sprintf("DIRECT: %s — adjust coalition and negotiation strategy", edesc)
      } else if (etype == "naval" || etype == "air") {
        mil_note <- sprintf("DIRECT: %s — assess escalation risk and defensive response", edesc)
        intel_note <- sprintf("Incident reveals adversary capabilities and intentions — collection priority")
        econ_note <- sprintf("Maritime/air incidents may disrupt trade routes and insurance costs")
        diplo_note <- sprintf("Incident creates diplomatic crisis requiring international response")
      } else if (etype == "cyber") {
        mil_note <- sprintf("Cyber attack may degrade military command and control systems")
        intel_note <- sprintf("DIRECT: %s — assess attribution, damage, and counter-cyber options", edesc)
        econ_note <- sprintf("Cyber incident may target financial systems and critical infrastructure")
        diplo_note <- sprintf("Cyber attribution creates diplomatic leverage or complications")
      } else if (etype == "information") {
        mil_note <- sprintf("Information operations may affect troop morale and public support for operations")
        intel_note <- sprintf("DIRECT: %s — assess disinformation and counter-narrative needs", edesc)
        econ_note <- sprintf("Public narrative shifts can affect investor confidence and sanctions support")
        diplo_note <- sprintf("Narrative developments affect international opinion and coalition cohesion")
      } else {
        # Shock events or other types
        mil_note <- sprintf("Assess military implications: %s", edesc)
        intel_note <- sprintf("Assess intelligence implications: %s", edesc)
        econ_note <- sprintf("Assess economic implications: %s", edesc)
        diplo_note <- sprintf("Assess diplomatic implications: %s", edesc)
      }

      domain_interpretations[[length(domain_interpretations) + 1]] <- list(
        event = ename,
        military = mil_note,
        intelligence = intel_note,
        economic = econ_note,
        diplomatic = diplo_note
      )
    }

    # Build per-domain event briefing sections
    domain_event_blocks <- list()
    for (dname in c("military", "intelligence", "economic", "diplomatic")) {
      notes <- sapply(domain_interpretations, function(di) {
        sprintf("    %s → %s", di$event, di[[dname]])
      })
      domain_event_blocks[[dname]] <- paste(notes, collapse = "\n")
    }

    events_block <- sprintf(
      "\n\nRECENT EVENTS THIS PERIOD:\n%s\n\nDOMAIN-SPECIFIC EVENT ANALYSIS (each expert should focus on THEIR section):\n  MILITARY analyst read:\n%s\n  INTELLIGENCE analyst read:\n%s\n  ECONOMIC analyst read:\n%s\n  DIPLOMATIC analyst read:\n%s",
      event_list,
      domain_event_blocks[["military"]],
      domain_event_blocks[["intelligence"]],
      domain_event_blocks[["economic"]],
      domain_event_blocks[["diplomatic"]]
    )
  }

  prompt <- sprintf("
<meeting_context>
=== GOVERNMENT STRATEGY MEETING: DOMAIN EXPERT PROPOSALS ===

Faction: %s
%s
</meeting_context>

<coordination_summary>
%s
</coordination_summary>

%s

<task>
Each domain expert will now propose 1-3 ACTIONS drawing primarily from their own area of expertise.
Your value to the faction comes from your SPECIALIZED PERSPECTIVE - propose actions where your domain knowledge gives you the clearest judgment of costs, risks, and feasibility.

IMPORTANT: Calibrate your proposals to the EXACT scenario parameters AND recent events above.
Each expert should focus on the KEY PARAMETERS listed for their domain AND the domain-specific event analysis for their section.
Events that are marked DIRECT for your domain demand an immediate response from you.
Events in other domains should inform but not replace your domain-specific analysis.
Higher crisis levels, worse military balance, more territory lost, and stronger sanctions should lead to more decisive and urgent actions. Lower values should lead to more measured responses.

- PRIMARY: Most important action from YOUR domain (required)
- SECONDARY: Supporting action, preferably from your domain (optional)
- TERTIARY: Opportunistic action from any domain if your own options are exhausted (optional)
</task>

<domain_experts>
%s
</domain_experts>

<instructions>
For each domain expert present, generate their proposals based on:
1. Their ACTION SELECTION GUIDANCE — this contains a SPECIFIC RECOMMENDED PRIMARY ACTION based on the current scenario parameters. You MUST follow this recommendation unless you have a compelling domain-specific reason to deviate.
2. Their PRIMARY ACTION DOMAIN - proposals should come mainly from the expert's own category
3. Their KEY PARAMETERS - each expert reads the situation through their domain-specific indicators
4. Their hawk/dove orientation (hawks propose more aggressive actions WITHIN their recommended category, doves propose more cautious ones)
5. Their worldview (shapes what they see as threats/opportunities)
6. The coordination discussion (but they can disagree with consensus)

CRITICAL RULES:
- Each expert's PRIMARY proposal MUST follow their ACTION SELECTION GUIDANCE. The guidance is computed from the current scenario parameters to ensure appropriate responses.
- Each expert MUST use DIFFERENT actions across different scenario conditions. An intelligence expert who always proposes cyber_attack regardless of crisis level is not doing their job.
- Experts should use the FULL RANGE of their domain: Collection, Defense, Offensive, and Information for intelligence; Punishment, Incentives, and Financial warfare for economic.
- If the guidance says AVOID a specific action, do NOT propose it as PRIMARY.
</instructions>

<creativity_guidance>
- Follow the RECOMMENDED PRIMARY ACTION in your guidance, but choose SECONDARY and TERTIARY creatively
- Hawks should choose the more aggressive option within the recommended category
- Doves should choose the more defensive option within the recommended category
- Example: if guidance recommends counterintelligence, a hawk might add cyber_attack as SECONDARY; a dove might add share_intelligence
</creativity_guidance>

<action_categories>
Each expert should propose PRIMARILY from their own domain category below.

MILITARY DOMAIN [PRIMARY for: MILITARY expert]:
  Defensive: defensive_fortification, defensive_reinforcements, troop_movements, air_patrols, enhanced_patrols, reconnaissance
  Posturing: military_buildup, show_of_force, military_exercises, naval_deployment, naval_patrols, naval_demonstration
  Offensive: limited_strike, border_incursion, occupation, blockade, siege_warfare

INTELLIGENCE DOMAIN [PRIMARY for: INTELLIGENCE expert]:
  Collection: intelligence_gathering, enhanced_intelligence_gathering, surveillance_operation, enhanced_surveillance, share_intelligence
  Defense: counterintelligence, cyber_defense
  Offensive: sabotage, cyber_attack, cyber_theft, leadership_targeting, false_flag_operation
  Information: spread_disinformation, propaganda_campaign, information_campaign

DIPLOMATIC DOMAIN [PRIMARY for: DIPLOMATIC expert]:
  De-escalation: peace_talks, formal_peace_talks, diplomatic_visit, mediation_offer, cultural_exchange
  Coalition: coalition_building, backchannel_negotiations, joint_exercises, formal_multilateral_engagement, international_observers
  Humanitarian: prisoner_exchange, humanitarian_corridors, humanitarian_aid, public_diplomatic_initiative

ECONOMIC DOMAIN [PRIMARY for: ECONOMIC expert]:
  Punishment: economic_sanctions, targeted_sanctions, resource_embargo, trade_restrictions, asset_seizure
  Incentives: trade_agreement, financial_aid, trade_negotiation
  Financial warfare: currency_manipulation, strategic_stockpiling, war_bonds

COVERT/REGIME [available to INTELLIGENCE and MILITARY if situation demands]:
  regime_destabilization, proxy_support, political_warfare
</action_categories>

<required_format>
CRITICAL: Your response MUST follow this EXACT format:

<proposals>
DOMAIN_NAME:
  PRIMARY: action_name [TARGET: target_name] - Brief rationale (1 sentence)
  SECONDARY: action_name [TARGET: target_name] - Brief rationale (1 sentence) [OPTIONAL]
  TERTIARY: action_name [TARGET: target_name] - Brief rationale (1 sentence) [OPTIONAL]

DOMAIN_NAME:
  PRIMARY: action_name [TARGET: target_name] - Brief rationale (1 sentence)
  [... etc for each domain]
</proposals>

TARGET OPTIONS:
- For offensive actions: Tethys, Novaris, or specific country names
- For diplomatic actions: Can be multiple (e.g., Meridian,Aurelia)
- For self-directed actions: self or none
- Default if omitted: opponent

RULES:
1. Use EXACT domain names: MILITARY, INTELLIGENCE, DIPLOMATIC, ECONOMIC
2. Each domain header followed by colon
3. PRIMARY is required, SECONDARY and TERTIARY are optional
4. Use exact action names from categories above
5. Include TARGET in square brackets after action name
6. Separate action name and rationale with space-dash-space
7. Keep rationales brief (1 sentence)
8. NO text before <proposals> or after </proposals>
</required_format>
",
    toupper(gsub("_", " ", faction)),
    paste0(situation_block, events_block),  # v3.11: events appended to situation
    coord_summary,
    previous_discussions,  # v3.8.2: Include previous period discussions
    domain_descs
  )

  return(prompt)
}

#' Parse domain proposals from LLM response (JSON format)
parse_domain_proposals <- function(response, domains) {
  proposals <- list()

  # Try JSON parsing first (new format)
  json_parsed <- FALSE
  tryCatch({
    # Extract JSON from <proposals> tags
    json_match <- regexpr("<proposals>\\s*(.+?)\\s*</proposals>", response, perl = TRUE, ignore.case = TRUE)

    if (json_match > 0) {
      # Extract the content between tags
      json_text <- regmatches(response, json_match)[[1]]
      json_text <- sub("<proposals>\\s*", "", json_text, ignore.case = TRUE)
      json_text <- sub("\\s*</proposals>", "", json_text, ignore.case = TRUE)

      # Parse JSON
      json_data <- jsonlite::fromJSON(json_text, simplifyVector = FALSE)

      # Convert JSON to expected structure
      for (domain_name in names(json_data)) {
        domain_lower <- tolower(domain_name)

        if (domain_lower %in% names(domains)) {
          proposals[[domain_lower]] <- list(
            agent_name = domains[[domain_lower]]$name,
            agent_role = domains[[domain_lower]]$role,
            agent_hawk_dove = domains[[domain_lower]]$hawk_dove
          )

          # Add actions for each priority level
          domain_data <- json_data[[domain_name]]
          for (priority in c("primary", "secondary", "tertiary")) {
            if (!is.null(domain_data[[priority]])) {
              proposals[[domain_lower]][[priority]] <- list(
                action = domain_data[[priority]]$action,
                target = if(!is.null(domain_data[[priority]]$target)) domain_data[[priority]]$target else NULL,
                rationale = domain_data[[priority]]$rationale
              )
            }
          }
        }
      }

      json_parsed <- TRUE
      cat("    ✓ Parsed proposals from JSON format\n")
    }
  }, error = function(e) {
    cat(sprintf("    ⚠ JSON parsing failed: %s\n", e$message))
    cat("    → Falling back to text parsing\n")
  })

  # FALLBACK: Text parsing (old format) if JSON fails
  if (!json_parsed) {
    lines <- strsplit(response, "\n")[[1]]
    current_domain <- NULL
    current_priority <- NULL

    for (line in lines) {
      line <- trimws(line)
      if (line == "") next

      # Check for domain header
      if (grepl("^(MILITARY|INTELLIGENCE|DIPLOMATIC|ECONOMIC):", line, ignore.case = TRUE)) {
        domain_match <- regmatches(line, regexpr("^(MILITARY|INTELLIGENCE|DIPLOMATIC|ECONOMIC)", line, ignore.case = TRUE))
        if (length(domain_match) > 0) {
          current_domain <- tolower(domain_match[1])
          if (current_domain %in% names(domains)) {
            proposals[[current_domain]] <- list(
              agent_name = domains[[current_domain]]$name,
              agent_role = domains[[current_domain]]$role,
              agent_hawk_dove = domains[[current_domain]]$hawk_dove
            )
          }
        }
        next
      }

      # Check for priority level (PRIMARY, SECONDARY, TERTIARY)
      if (grepl("^(PRIMARY|SECONDARY|TERTIARY):", line, ignore.case = TRUE)) {
        priority_match <- regmatches(line, regexpr("^(PRIMARY|SECONDARY|TERTIARY)", line, ignore.case = TRUE))
        if (length(priority_match) > 0) {
          current_priority <- tolower(priority_match[1])

          # Extract action, target, and rationale
          rest <- sub("^(PRIMARY|SECONDARY|TERTIARY):\\s*", "", line, ignore.case = TRUE)
          parts <- strsplit(rest, " - ")[[1]]

          if (length(parts) >= 1 && !is.null(current_domain)) {
            action_part <- trimws(parts[1])
            rationale <- if(length(parts) >= 2) trimws(paste(parts[-1], collapse = " - ")) else ""

            # Extract target if present: action_name [TARGET: target_name]
            target <- NULL
            if (grepl("\\[TARGET:", action_part, ignore.case = TRUE)) {
              target_match <- regmatches(action_part, regexpr("\\[TARGET:[^]]+\\]", action_part, ignore.case = TRUE))
              if (length(target_match) > 0) {
                target <- sub("\\[TARGET:\\s*", "", target_match, ignore.case = TRUE)
                target <- sub("\\]", "", target)
                target <- trimws(target)
              }
              # Remove target from action_part
              action_part <- sub("\\[TARGET:[^]]+\\]", "", action_part, ignore.case = TRUE)
              action_part <- trimws(action_part)
            }

            action <- action_part

            proposals[[current_domain]][[current_priority]] <- list(
              action = action,
              target = target,
              rationale = rationale
            )
          }
        }
      }
    }
  }

  # FALLBACK: Detect misplaced diplomatic actions (works for both JSON and text)
  diplomatic_actions <- c(
    "peace_talks", "diplomatic_visit", "mediation_offer", "cultural_exchange",
    "coalition_building", "backchannel_negotiations", "joint_exercises",
    "prisoner_exchange", "humanitarian_corridors", "humanitarian_aid"
  )

  if ("diplomatic" %in% names(domains) && is.null(proposals[["diplomatic"]])) {
    for (domain_name in names(proposals)) {
      if (domain_name == "diplomatic") next

      for (priority in c("primary", "secondary", "tertiary")) {
        if (!is.null(proposals[[domain_name]][[priority]])) {
          action <- proposals[[domain_name]][[priority]]$action
          if (action %in% diplomatic_actions) {
            if (is.null(proposals[["diplomatic"]])) {
              proposals[["diplomatic"]] <- list(
                agent_name = domains[["diplomatic"]]$name,
                agent_role = domains[["diplomatic"]]$role,
                agent_hawk_dove = domains[["diplomatic"]]$hawk_dove
              )
            }

            proposals[["diplomatic"]][[priority]] <- proposals[[domain_name]][[priority]]
            cat(sprintf("    ⚠ FALLBACK: Moved %s from %s to diplomatic domain\n",
                       action, domain_name))
            proposals[[domain_name]][[priority]] <- NULL
          }
        }
      }
    }
  }

  return(proposals)
}

#' Presidential approval of domain proposals
#'
#' @param proposals Domain expert proposals
#' @param faction Faction name
#' @param faction_agents All agents in faction
#' @param context Current context
#' @param api_key API key
#' @param state Full simulation state (for discussion history)
#' @return List of approved actions
presidential_approval <- function(proposals, faction, faction_agents, context, api_key, state = NULL) {
  cat(sprintf("  → Presidential review of proposals...\n"))

  # Find President/Government leader
  gov_agents <- Filter(function(a) a$role == "government", faction_agents)
  if (length(gov_agents) == 0) {
    # Fallback to first agent
    president <- faction_agents[[1]]
  } else {
    president <- gov_agents[[1]]
  }

  cat(sprintf("    Decision maker: %s\n", president$name))

  # Build approval prompt (now with state for discussion history)
  approval_prompt <- build_approval_prompt(proposals, president, context, faction, state)

  system_prompt <- sprintf(
    "You are %s, the leader making final decisions on proposed actions. You have strategic agency - you can choose to escalate or de-escalate based on your judgment, not just reacting to events.",
    president$name
  )

  # Call LLM for approval decisions
  cat(sprintf("    Calling LLM for approval decisions...\n"))
  response <- call_llm(system_prompt, approval_prompt, DECISION_MAKER_MODEL, api_key)

  # Debug: Show response preview if parsing might fail
  if (nchar(response) < 100) {
    cat(sprintf("    WARNING: Very short response (%d chars): %s\n", nchar(response), response))
  }

  # Debug: Always show first 500 chars of response to diagnose parsing issues
  cat(sprintf("    DEBUG: Response preview (first 500 chars):\n"))
  cat(sprintf("    %s\n", substr(response, 1, 500)))
  cat(sprintf("    [...response continues for %d total chars]\n", nchar(response)))

  # Parse approvals
  approvals <- parse_approvals(response, proposals)

  # Display approvals
  cat(sprintf("\n    APPROVAL DECISIONS:\n"))
  approved_count <- 0
  counter_count <- 0
  for (domain in names(approvals)) {
    cat(sprintf("    %s:\n", toupper(domain)))
    for (priority in c("primary", "secondary", "tertiary")) {
      if (!is.null(approvals[[domain]][[priority]])) {
        decision <- approvals[[domain]][[priority]]

        # Check if decision is valid
        if (is.null(decision$approved)) {
          cat(sprintf("      ⚠ WARNING: Invalid decision for %s - skipping\n", toupper(priority)))
          next
        }

        # Determine symbol and message based on decision type
        if (!is.null(decision$is_counter) && decision$is_counter) {
          symbol <- "↻ COUNTER"
          cat(sprintf("      %s %s: %s (was: %s) - %s\n",
                     symbol, toupper(priority),
                     decision$action, decision$original_action, decision$rationale))
          approved_count <- approved_count + 1
          counter_count <- counter_count + 1
        } else {
          symbol <- if(decision$approved) "✓ APPROVE" else "✗ VETO"
          cat(sprintf("      %s %s: %s - %s\n",
                     symbol, toupper(priority),
                     decision$action, decision$rationale))
          if (decision$approved) approved_count <- approved_count + 1
        }
      }
    }
  }
  cat(sprintf("\n    Total approved: %d actions", approved_count))
  if (counter_count > 0) {
    cat(sprintf(" (%d counter-proposals)", counter_count))
  }
  cat("\n\n")

  return(approvals)
}

#' Build prompt for presidential approval
build_approval_prompt <- function(proposals, president, context, faction, state = NULL) {
  # Get previous discussions for context (v3.8.2)
  previous_discussions <- ""
  if (!is.null(state) && !is.null(context$period) && context$period > 1) {
    previous_discussions <- format_previous_discussions(state, context$period, president)
  }

  # Build proposal summary
  proposal_summary <- ""
  total_cost <- 0

  for (domain in names(proposals)) {
    proposal_summary <- paste0(proposal_summary, sprintf("\n%s (%s):\n",
                                                         toupper(domain),
                                                         proposals[[domain]]$agent_name))
    for (priority in c("primary", "secondary", "tertiary")) {
      if (!is.null(proposals[[domain]][[priority]])) {
        action <- proposals[[domain]][[priority]]$action
        rationale <- proposals[[domain]][[priority]]$rationale

        # Estimate cost (simplified - could be more sophisticated)
        cost <- estimate_action_cost(action)
        total_cost <- total_cost + cost

        proposal_summary <- paste0(proposal_summary, sprintf(
          "  %s: %s (cost: $%.1fB)\n    Rationale: %s\n",
          toupper(priority), action, cost, rationale
        ))
      }
    }
  }

  # Get president's characteristics
  hawk_pct <- round(president$hawk_dove * 100)
  worldview <- if(!is.null(president$worldview)) president$worldview else "pragmatic"

  # Build detailed situation parameters block for president
  ss <- context$scenario_state
  situation_params <- sprintf(
    "CURRENT SCENARIO PARAMETERS:\n  Crisis Level: %.1f / 10\n  Military Balance: %+.2f (negative = favors Novaris, positive = favors Tethys)\n  Territory Under Enemy Control: %.1f%%\n  Economic Sanctions Severity: %.0f%%\n  International Support for Tethys: %.0f%%",
    if(!is.null(ss$crisis_level)) ss$crisis_level else 5,
    if(!is.null(ss$military_balance)) ss$military_balance else 0,
    if(!is.null(ss$territory_controlled)) ss$territory_controlled * 100 else 0,
    if(!is.null(ss$sanctions_level)) ss$sanctions_level * 100 else 0,
    if(!is.null(ss$international_support)) ss$international_support * 100 else 50
  )

  prompt <- sprintf("
<presidential_decision>
=== PRESIDENTIAL DECISION: APPROVE OR VETO PROPOSED ACTIONS ===

<leader_profile>
You are %s, leader of %s.
Your worldview: %s
Your hawk/dove orientation: %d%% hawk / %d%% dove
%s
</leader_profile>

<strategic_assessment>
YOUR STRATEGIC ASSESSMENT:
You have AGENCY - you can choose to escalate or de-escalate based on YOUR strategic judgment.
Crisis level informs but does NOT determine your decisions.
Consider the EXACT scenario parameters above when making your decisions.

A DOVE leader might de-escalate even in high crisis (believing diplomacy is the only path).
A HAWK leader might escalate even in low crisis (seizing the initiative).
A LIBERAL INSTITUTIONALIST might prioritize international norms even under pressure.
A REALIST might approve risky actions if they serve strategic interests.
</strategic_assessment>

%s

<proposals>
Your advisors have proposed the following actions:

%s

TOTAL ESTIMATED COST: $%.1fB
(Your faction can afford roughly $68-100B per period depending on GDP)
</proposals>

<strategic_options>
STRATEGIC OPTIONS:
A. DE-ESCALATE: Approve only diplomatic/defensive actions, veto offensive
B. MAINTAIN POSTURE: Approve defensive + diplomatic, veto high-risk offensive
C. APPLY PRESSURE: Approve some offensive actions alongside defensive
D. FULL ESCALATION: Approve most/all proposals including high-risk actions
</strategic_options>

<approval_considerations>
APPROVAL CONSIDERATIONS:
1. STRATEGIC COHERENCE: Do actions support your chosen strategy?
2. CONTRADICTIONS: Do any actions contradict each other? (e.g., peace talks + sabotage)
3. RESOURCE LIMITS: Can you afford all approved actions?
4. RISK vs REWARD: What are consequences if risky actions fail or are detected?
5. YOUR WORLDVIEW: What does someone with YOUR beliefs think is right?

DEFAULT: Approve domain experts' PRIMARY recommendations unless compelling reason to veto.
Your ministers are experts - trust their judgment unless it clearly conflicts with your strategy.
</approval_considerations>

<decision_types>
DECISION TYPES - You have THREE options for each proposal:

1. APPROVE - Execute the proposal exactly as suggested
2. VETO - Reject the proposal entirely
3. COUNTER: [alternative_action] - Approve a DIFFERENT action instead

WHEN TO COUNTER-PROPOSE:
- Expert suggests something TOO RISKY → Counter with safer alternative
  Example: sabotage → COUNTER: intelligence_gathering
- Expert suggests something TOO WEAK → Counter with stronger alternative
  Example: diplomatic_visit → COUNTER: peace_talks
- Expert suggests RIGHT DOMAIN, WRONG ACTION → Counter with better fit
  Example: limited_strike → COUNTER: show_of_force

Your counter-proposals should reflect YOUR worldview:
- HAWKS might counter UP (surveillance → sabotage)
- DOVES might counter DOWN (sabotage → intelligence_gathering)
- LIBERAL INSTITUTIONALISTS might counter to norm-compliant alternatives
- REALISTS might counter based on strategic effectiveness
</decision_types>

<format_requirements>
CRITICAL: Your response MUST follow this EXACT format:

<approval_decisions>
DOMAIN_NAME:
  PRIMARY: APPROVE - Brief rationale
  SECONDARY: VETO - Brief rationale
  TERTIARY: COUNTER: alternative_action - Brief rationale

DOMAIN_NAME:
  PRIMARY: APPROVE - Brief rationale
  [... etc for each proposed domain]
</approval_decisions>

RULES:
1. Use EXACT domain names: MILITARY, INTELLIGENCE, DIPLOMATIC, ECONOMIC
2. Each domain header followed by colon
3. Make a decision for EVERY priority level that was proposed
4. For APPROVE/VETO: Just state decision and brief rationale
5. For COUNTER: Use format COUNTER: alternative_action - rationale
6. Alternative actions must be from same domain's action list
7. NO text before <approval_decisions> or after </approval_decisions>
</format_requirements>
</presidential_decision>

Only include domains and priorities that were proposed. You MUST make a decision for EVERY proposal.
",
    president$name,
    toupper(gsub("_", " ", faction)),
    worldview,
    hawk_pct, 100 - hawk_pct,
    situation_params,
    previous_discussions,  # v3.8.2: Include previous period discussions
    proposal_summary,
    total_cost
  )

  return(prompt)
}

#' Estimate action cost (simplified)
estimate_action_cost <- function(action) {
  # Simplified cost estimates in billions
  costs <- list(
    military_buildup = 5.0,
    defensive_fortification = 3.0,
    limited_strike = 2.0,
    border_incursion = 1.5,
    troop_movements = 2.0,
    financial_aid = 2.0,
    economic_sanctions = 0.5,
    peace_talks = 0.2,
    diplomatic_visit = 0.1,
    intelligence_gathering = 0.3,
    sabotage = 0.5,
    cyber_attack = 0.3,
    coalition_building = 1.0,
    proxy_support = 1.0,
    spread_disinformation = 0.2,
    regime_destabilization = 1.5
  )

  if (action %in% names(costs)) {
    return(costs[[action]])
  } else {
    return(1.0)  # Default cost
  }
}

#' Parse approval decisions (JSON format)
parse_approvals <- function(response, proposals) {
  approvals <- list()
  json_parsed <- FALSE

  # Try JSON parsing first (new format)
  tryCatch({
    # Extract JSON from <approval_decisions> tags
    json_match <- regexpr("<approval_decisions>\\s*(.+?)\\s*</approval_decisions>", response, perl = TRUE, ignore.case = TRUE)

    if (json_match > 0) {
      # Extract the content between tags
      json_text <- regmatches(response, json_match)[[1]]
      json_text <- sub("<approval_decisions>\\s*", "", json_text, ignore.case = TRUE)
      json_text <- sub("\\s*</approval_decisions>", "", json_text, ignore.case = TRUE)

      # Parse JSON
      json_data <- jsonlite::fromJSON(json_text, simplifyVector = FALSE)

      # Convert JSON to expected structure
      for (domain_name in names(json_data)) {
        domain_lower <- tolower(domain_name)

        if (domain_lower %in% names(proposals)) {
          approvals[[domain_lower]] <- list()
          domain_data <- json_data[[domain_name]]

          for (priority in c("primary", "secondary", "tertiary")) {
            if (!is.null(domain_data[[priority]]) && !is.null(proposals[[domain_lower]][[priority]])) {
              decision_data <- domain_data[[priority]]
              decision_type <- toupper(decision_data$decision)

              if (decision_type == "COUNTER") {
                # Counter-proposal
                approvals[[domain_lower]][[priority]] <- list(
                  action = decision_data$alternative,
                  approved = TRUE,
                  is_counter = TRUE,
                  original_action = proposals[[domain_lower]][[priority]]$action,
                  rationale = decision_data$rationale,
                  proposal_rationale = proposals[[domain_lower]][[priority]]$rationale,
                  proposed_by = proposals[[domain_lower]]$agent_name,
                  proposed_by_role = proposals[[domain_lower]]$agent_role,
                  target = if(!is.null(proposals[[domain_lower]][[priority]]$target)) proposals[[domain_lower]][[priority]]$target else NA
                )
              } else {
                # APPROVE or VETO
                approvals[[domain_lower]][[priority]] <- list(
                  action = proposals[[domain_lower]][[priority]]$action,
                  approved = (decision_type == "APPROVE"),
                  is_counter = FALSE,
                  rationale = decision_data$rationale,
                  proposal_rationale = proposals[[domain_lower]][[priority]]$rationale,
                  proposed_by = proposals[[domain_lower]]$agent_name,
                  proposed_by_role = proposals[[domain_lower]]$agent_role,
                  target = if(!is.null(proposals[[domain_lower]][[priority]]$target)) proposals[[domain_lower]][[priority]]$target else NA
                )
              }
            }
          }
        }
      }

      json_parsed <- TRUE
      cat("    ✓ Parsed approval decisions from JSON format\n")
    }
  }, error = function(e) {
    cat(sprintf("    ⚠ JSON parsing failed: %s\n", e$message))
    cat("    → Falling back to text parsing\n")
  })

  # FALLBACK: Text parsing (old format) if JSON fails
  if (!json_parsed) {
    lines <- strsplit(response, "\n")[[1]]
    current_domain <- NULL

    for (line in lines) {
      line <- trimws(line)
      if (line == "") next

      # Check for domain header
      if (grepl("^(MILITARY|INTELLIGENCE|DIPLOMATIC|ECONOMIC):", line, ignore.case = TRUE)) {
        domain_match <- regmatches(line, regexpr("^(MILITARY|INTELLIGENCE|DIPLOMATIC|ECONOMIC)", line, ignore.case = TRUE))
        if (length(domain_match) > 0) {
          current_domain <- tolower(domain_match[1])
          if (current_domain %in% names(proposals)) {
            approvals[[current_domain]] <- list()
          }
        }
        next
      }

      # Check for priority + approval decision (including COUNTER)
      if (grepl("^(PRIMARY|SECONDARY|TERTIARY):\\s*(APPROVE|VETO|COUNTER)", line, ignore.case = TRUE)) {
        priority_match <- regmatches(line, regexpr("^(PRIMARY|SECONDARY|TERTIARY)", line, ignore.case = TRUE))

        if (length(priority_match) > 0 && !is.null(current_domain)) {
          priority <- tolower(priority_match[1])
          is_counter <- grepl("COUNTER:", line, ignore.case = TRUE)

          if (is_counter) {
            counter_match <- regmatches(line, regexpr("COUNTER:\\s*([a-z_]+)", line, ignore.case = TRUE))
            if (length(counter_match) > 0) {
              counter_action <- sub("COUNTER:\\s*", "", counter_match[1], ignore.case = TRUE)
              counter_action <- trimws(strsplit(counter_action, "\\s")[[1]][1])
              rationale_part <- sub("^.*COUNTER:\\s*[a-z_]+\\s*-\\s*", "", line, ignore.case = TRUE)

              if (!is.null(proposals[[current_domain]][[priority]])) {
                approvals[[current_domain]][[priority]] <- list(
                  action = counter_action,
                  approved = TRUE,
                  is_counter = TRUE,
                  original_action = proposals[[current_domain]][[priority]]$action,
                  rationale = rationale_part,
                  proposal_rationale = proposals[[current_domain]][[priority]]$rationale,
                  proposed_by = proposals[[current_domain]]$agent_name,
                  proposed_by_role = proposals[[current_domain]]$agent_role,
                  target = if(!is.null(proposals[[current_domain]][[priority]]$target)) proposals[[current_domain]][[priority]]$target else NA
                )
              }
            }
          } else {
            approval_match <- regmatches(line, regexpr("(APPROVE|VETO)", line, ignore.case = TRUE))
            if (length(approval_match) > 0) {
              approved <- tolower(approval_match[1]) == "approve"
              rationale_part <- sub("^(PRIMARY|SECONDARY|TERTIARY):\\s*(APPROVE|VETO)\\s*-?\\s*", "", line, ignore.case = TRUE)

              if (!is.null(proposals[[current_domain]][[priority]])) {
                approvals[[current_domain]][[priority]] <- list(
                  action = proposals[[current_domain]][[priority]]$action,
                  approved = approved,
                  is_counter = FALSE,
                  rationale = rationale_part,
                  proposal_rationale = proposals[[current_domain]][[priority]]$rationale,
                  proposed_by = proposals[[current_domain]]$agent_name,
                  proposed_by_role = proposals[[current_domain]]$agent_role,
                  target = if(!is.null(proposals[[current_domain]][[priority]]$target)) proposals[[current_domain]][[priority]]$target else NA
                )
              }
            }
          }
        }
      }
    }
  }

  # Validate that all proposals have corresponding approvals
  for (domain in names(proposals)) {
    if (!domain %in% c("agent_name", "agent_role", "agent_hawk_dove")) {
      if (!domain %in% names(approvals)) {
        cat(sprintf("      WARNING: Missing or invalid decision for %s\n", domain))
      } else {
        for (priority in c("primary", "secondary", "tertiary")) {
          if (!is.null(proposals[[domain]][[priority]]) && is.null(approvals[[domain]][[priority]])) {
            cat(sprintf("      WARNING: Missing or invalid decision for %s/%s - skipping\n", domain, priority))
          }
        }
      }
    }
  }

  return(approvals)
}

#' Extract approved actions from approval decisions
#'
#' @param approvals Approval decisions
#' @return List of approved action objects ready for execution
extract_approved_actions <- function(approvals) {
  approved_actions <- list()

  for (domain in names(approvals)) {
    for (priority in names(approvals[[domain]])) {
      decision <- approvals[[domain]][[priority]]
      if (!is.null(decision) && !is.null(decision$approved) && decision$approved) {
        action_item <- list(
          action = decision$action,
          domain = domain,
          priority = priority,
          rationale = decision$proposal_rationale,
          approval_rationale = decision$rationale,
          proposed_by = decision$proposed_by,
          proposed_by_role = decision$proposed_by_role,
          target = decision$target
        )

        # Add counter-proposal metadata if applicable
        if (!is.null(decision$is_counter) && decision$is_counter) {
          action_item$is_counter <- TRUE
          action_item$original_action <- decision$original_action
        } else {
          action_item$is_counter <- FALSE
        }

        approved_actions[[length(approved_actions) + 1]] <- action_item
      }
    }
  }

  return(approved_actions)
}

#' Extract ALL actions with approval status (approved, vetoed, counter-proposed)
#'
#' @param proposals Domain expert proposals
#' @param approvals Presidential approval decisions
#' @return List of all action objects with approval status
extract_all_actions_with_status <- function(proposals, approvals) {
  all_actions <- list()

  for (domain in names(proposals)) {
    # Skip the metadata fields (agent_name, agent_role, etc.)
    for (priority in c("primary", "secondary", "tertiary")) {
      if (!is.null(proposals[[domain]][[priority]])) {
        proposal <- proposals[[domain]][[priority]]
        decision <- approvals[[domain]][[priority]]

        # Determine approval status
        # Check if decision exists and has approved field
        if (is.null(decision) || is.null(decision$approved)) {
          cat(sprintf("      WARNING: Missing or invalid decision for %s/%s - skipping\n", domain, priority))
          next
        }

        if (decision$approved) {
          if (!is.null(decision$is_counter) && decision$is_counter) {
            approval_status <- "counter_proposed"
          } else {
            approval_status <- "approved"
          }
        } else {
          approval_status <- "vetoed"
        }

        action_item <- list(
          # Proposal information
          proposed_action = proposal$action,
          proposed_by = proposals[[domain]]$agent_name,
          proposed_by_role = proposals[[domain]]$agent_role,
          proposal_rationale = proposal$rationale,
          target = if(!is.null(proposal$target)) proposal$target else NA,

          # Decision information
          approval_status = approval_status,
          final_action = decision$action,  # Could differ if counter-proposed
          decision_rationale = decision$rationale,

          # Metadata
          domain = domain,
          priority = priority,
          is_counter = if(!is.null(decision$is_counter)) decision$is_counter else FALSE,
          original_action = if(!is.null(decision$original_action)) decision$original_action else NA
        )

        all_actions[[length(all_actions) + 1]] <- action_item
      }
    }
  }

  return(all_actions)
}
