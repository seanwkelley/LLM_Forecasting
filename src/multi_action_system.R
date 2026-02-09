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
  cat(sprintf("  → Generating domain expert proposals for %s...\n", toupper(faction)))

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

  # Build proposal prompt (now with state for discussion history)
  proposal_prompt <- build_proposal_prompt(domains, coordination, context, faction, state)

  system_prompt <- "You are facilitating a government strategy meeting where domain experts propose actions in their areas of expertise."

  # Call LLM to generate all proposals in one call
  cat(sprintf("    Calling LLM for domain proposals...\n"))
  response <- call_llm(system_prompt, proposal_prompt, AGENT_MODEL, api_key)

  # Parse proposals
  proposals <- parse_domain_proposals(response, domains)

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

#' Build prompt for domain expert proposals
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

  # Build domain expert descriptions
  domain_descs <- ""
  for (domain_name in names(domains)) {
    agent <- domains[[domain_name]]
    hawk_pct <- round(agent$hawk_dove * 100)
    domain_descs <- paste0(domain_descs, sprintf(
      "\n%s (%s, %d%% hawk):\n  Role: %s\n  Worldview: %s\n",
      toupper(domain_name), agent$name, hawk_pct, agent$role,
      if(!is.null(agent$worldview)) agent$worldview else "pragmatic"
    ))
  }

  prompt <- sprintf("
<meeting_context>
=== GOVERNMENT STRATEGY MEETING: DOMAIN EXPERT PROPOSALS ===

Faction: %s
Current Crisis Level: %.0f/10
Situation: %s
</meeting_context>

<coordination_summary>
%s
</coordination_summary>

%s

<task>
Each domain expert will now propose 1-3 ACTIONS in their area of expertise:
- PRIMARY: Most important action (required)
- SECONDARY: Supporting action if resources allow (optional)
- TERTIARY: Opportunistic action if feasible (optional)
</task>

<domain_experts>
%s
</domain_experts>

<instructions>
For each domain expert present, generate their proposals based on:
1. Their role and expertise
2. Their hawk/dove orientation (hawks propose more aggressive actions)
3. Their worldview (shapes what they see as threats/opportunities)
4. The coordination discussion (but they can disagree with consensus)
</instructions>

<creativity_guidance>
- Think ASYMMETRICALLY - what unconventional options exist?
- Consider MULTI-DOMAIN approaches (land, sea, air, cyber, information, economic)
- Don't default to obvious choices - what would a creative strategist propose?
- Consider both ESCALATION and DE-ESCALATION options
- Think about INDIRECT effects and second-order consequences
</creativity_guidance>

<action_categories>
MILITARY (consider ALL domains: land, naval, air, cyber):
  Defensive: defensive_fortification, troop_movements, air_patrols, enhanced_patrols
  Posturing: military_buildup, show_of_force, military_exercises, naval_deployment
  Offensive: limited_strike, border_incursion, occupation, blockade

INTELLIGENCE (both collection AND operations):
  Collection: intelligence_gathering, surveillance_operation, share_intelligence
  Defense: counterintelligence
  Offensive: sabotage, cyber_attack, cyber_theft, leadership_targeting, false_flag_operation

DIPLOMATIC (both pressure AND engagement):
  De-escalation: peace_talks, diplomatic_visit, mediation_offer, cultural_exchange
  Coalition: coalition_building, backchannel_negotiations, joint_exercises
  Humanitarian: prisoner_exchange, humanitarian_corridors, humanitarian_aid

ECONOMIC (both sticks AND carrots):
  Punishment: economic_sanctions, resource_embargo, trade_restrictions, asset_seizure
  Incentives: trade_agreement, financial_aid, trade_negotiation
  Sophisticated: currency_manipulation, strategic_stockpiling, war_bonds

COVERT/INFORMATION (shape perceptions):
  Information: spread_disinformation, propaganda_campaign, information_campaign
  Indirect: regime_destabilization, proxy_support, political_warfare
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
    if(!is.null(context$scenario_state$crisis_level)) context$scenario_state$crisis_level else 5,
    if(!is.null(context$scenario_state$situation)) substr(context$scenario_state$situation, 1, 200) else "Ongoing crisis",
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

  prompt <- sprintf("
<presidential_decision>
=== PRESIDENTIAL DECISION: APPROVE OR VETO PROPOSED ACTIONS ===

<leader_profile>
You are %s, leader of %s.
Your worldview: %s
Your hawk/dove orientation: %d%% hawk / %d%% dove
Current crisis level: %.0f/10
</leader_profile>

<strategic_assessment>
YOUR STRATEGIC ASSESSMENT:
You have AGENCY - you can choose to escalate or de-escalate based on YOUR strategic judgment.
Crisis level informs but does NOT determine your decisions.

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
    if(!is.null(context$scenario_state$crisis_level)) context$scenario_state$crisis_level else 5,
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
