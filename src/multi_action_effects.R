# Multi-Action Effect Resolution System
#
# Handles resolution of multiple concurrent actions with:
# - Cumulative effects (additive, diminishing returns)
# - Contradictory actions (detection, cancellation)
# - Synergistic effects (bonuses)
# - Resource constraints

# Source action execution system for real execute_action() function
if (!exists("execute_action", mode = "function")) {
  source("src/action_execution.R")
}

#' Resolve effects of multiple concurrent actions
#'
#' @param approved_actions List of approved actions
#' @param agent Agent executing actions
#' @param state Current simulation state
#' @return Updated state with all effects applied
resolve_multiple_action_effects <- function(approved_actions, agent, state) {
  if (length(approved_actions) == 0) {
    cat(sprintf("    No approved actions to execute\n"))
    return(state)
  }

  cat(sprintf("    Resolving %d concurrent actions...\n", length(approved_actions)))

  # Initialize effect accumulator (used for GDP/territory/costs, synergy detection, and reporting)
  effects <- list(
    crisis_change = 0,
    military_balance_change = 0,
    sanctions_change = 0,
    international_support_change = 0,
    gdp_change = 0,
    territory_change = 0,
    messages = list(),
    total_cost = 0
  )

  # 1. Check for contradictions FIRST
  contradictions <- detect_contradictions(approved_actions)
  if (length(contradictions) > 0) {
    cat(sprintf("    WARNING: Contradictory actions detected!\n"))
    for (contra in contradictions) {
      cat(sprintf("      - %s\n", contra$message))
    }
    # Contradiction penalties tracked for later application
    effects <- apply_contradiction_penalties(effects, contradictions, approved_actions)
  }

  # 2. Group actions by category for diminishing returns
  action_categories <- categorize_actions(approved_actions)

  # 3. Execute each action, threading state through sequential calls
  # State is threaded so that:
  #   - Direct mutations in execute_action() are preserved (crisis, sanctions, military, etc.)
  #   - Stateful tracking (e.g., peace_talks_count) persists across actions
  # The accumulator still tracks effects for GDP/territory/costs, synergies, and reporting.
  action_results <- list()  # Track individual results for CSV

  for (i in seq_along(approved_actions)) {
    action_item <- approved_actions[[i]]
    action_name <- action_item$action
    target_name <- action_item$target

    # Get base action object for category
    action_obj <- get_action_definition(action_name)
    if (is.null(action_obj)) {
      cat(sprintf("      Warning: Unknown action %s\n", action_name))
      next
    }

    # Determine target agent by looking up in state$agents
    # Support multiple comma-separated targets (e.g., "Meridian,Aurelia")
    target_agent <- NULL
    if (!is.null(target_name) && target_name != "self" && target_name != "none") {
      # Split target by comma to handle multiple targets
      target_names <- trimws(strsplit(target_name, ",")[[1]])

      # Look up the full agent object from state
      if (!is.null(state$agents) && length(state$agents) > 0) {
        # Try to match any of the target names
        for (tname in target_names) {
          for (a in state$agents) {
            if (!is.null(a) && !is.null(a$country) && grepl(tname, a$country, ignore.case = TRUE)) {
              target_agent <- a
              break
            }
            if (!is.null(a) && !is.null(a$name) && grepl(tname, a$name, ignore.case = TRUE)) {
              target_agent <- a
              break
            }
          }
          # If we found a match, stop searching
          if (!is.null(target_agent)) break
        }
      }

      if (is.null(target_agent)) {
        cat(sprintf("      Warning: Target '%s' not found, treating as NULL\n", target_name))
      }
    }

    # Execute action using real action_execution.R logic
    cat(sprintf("      %d. %s", i, action_name))
    if (!is.null(target_name)) {
      cat(sprintf(" → %s", target_name))
    }

    execution_result <- execute_action(action_name, agent, target_agent, state)
    result <- execution_result$result
    state <- execution_result$state  # Thread state: preserves direct mutations and stateful tracking

    # Log result
    success_marker <- if(result$success) "✓" else "✗"
    cat(sprintf(" [%s %s]\n", success_marker, if(result$success) "SUCCESS" else "FAILED"))
    if (!is.null(result$effects$message)) {
      cat(sprintf("        %s\n", result$effects$message))
    }

    # Store individual result for CSV logging
    action_results[[length(action_results) + 1]] <- list(
      action = action_name,
      target = target_name,
      success = result$success,
      effects = result$effects,
      proposed_by = action_item$proposed_by,
      rationale = action_item$rationale
    )

    # Calculate diminishing returns factor for successful actions
    category <- action_obj$category
    same_category_count <- sum(sapply(action_results[1:max(1, length(action_results)-1)], function(r) {
      if (r$success) {  # Only count successful actions for diminishing returns
        prev_obj <- get_action_definition(r$action)
        if (!is.null(prev_obj)) prev_obj$category == category else FALSE
      } else {
        FALSE
      }
    }))

    diminishing_factor <- 1.0 / (1.0 + 0.4 * same_category_count)

    # Convert result effects to accumulator format (for GDP/territory/costs and reporting)
    action_effects <- convert_result_to_effects(result, diminishing_factor)

    # Accumulate effects for GDP/territory/costs tracking and synergy detection
    effects <- accumulate_effects(effects, action_effects)
    effects$total_cost <- effects$total_cost + action_obj$cost
  }

  # Store results for later CSV logging
  state$last_action_results <- action_results

  # 4. Check for synergies (only among successful actions)
  successful_actions <- Filter(function(r) r$success, action_results)
  synergies <- detect_synergies(successful_actions)
  if (length(synergies) > 0) {
    cat(sprintf("    Synergies detected:\n"))
    for (syn in synergies) {
      cat(sprintf("      + %s\n", syn$message))
      effects <- apply_synergy_bonus(effects, syn)
    }
  }

  # 5. Apply effects to state
  # State already has direct mutations from execute_action() for: crisis, sanctions, military_balance,
  # international_support. We only need to apply:
  #   a) Synergy bonuses (added to accumulator in step 4)
  #   b) Contradiction penalties (added to accumulator in step 1)
  #   c) GDP effects (not in direct mutations - lives in faction_capabilities)
  #   d) Territory effects (not always in direct mutations)
  #   e) Action costs (not in direct mutations)

  # 5a. Apply synergy bonuses directly to state
  for (syn in synergies) {
    if (!is.null(syn$bonus$crisis_change)) {
      state$scenario_state$crisis_level <- max(0, min(10,
        state$scenario_state$crisis_level + syn$bonus$crisis_change))
    }
    if (!is.null(syn$bonus$military_balance_change)) {
      state$scenario_state$military_balance <- max(-1, min(1,
        state$scenario_state$military_balance + syn$bonus$military_balance_change))
    }
  }

  # 5b. Apply contradiction penalties directly to state
  for (contra in contradictions) {
    if (!is.null(contra$penalty$crisis_change)) {
      state$scenario_state$crisis_level <- max(0, min(10,
        state$scenario_state$crisis_level + contra$penalty$crisis_change))
    }
    if (!is.null(contra$penalty$international_support_change)) {
      # Penalty values are in percentage points (e.g., -15 means -0.15 on 0-1 scale)
      state$scenario_state$international_support <- max(0, min(1,
        state$scenario_state$international_support + contra$penalty$international_support_change / 100))
    }
  }

  # 5c. Apply GDP effects (target damage + action costs) — not handled by direct mutations
  if (!is.null(state$faction_capabilities) && !is.null(agent$faction)) {
    # Target GDP damage (accumulated from target_gdp_impact of individual actions)
    if (!is.null(effects$gdp_change) && effects$gdp_change != 0) {
      if (agent$faction == "major_power") {
        state$faction_capabilities$small_power_gdp <-
          max(5, state$faction_capabilities$small_power_gdp * (1 + effects$gdp_change))
      } else if (agent$faction == "small_power") {
        state$faction_capabilities$major_power_gdp <-
          max(10, state$faction_capabilities$major_power_gdp * (1 + effects$gdp_change))
      }
    }
    # Action costs deducted from own GDP
    if (!is.null(effects$total_cost) && effects$total_cost > 0) {
      if (agent$faction == "major_power") {
        state$faction_capabilities$major_power_gdp <-
          max(10, state$faction_capabilities$major_power_gdp - effects$total_cost)
      } else if (agent$faction == "small_power") {
        state$faction_capabilities$small_power_gdp <-
          max(5, state$faction_capabilities$small_power_gdp - effects$total_cost)
      }
    }
  }

  # 5d. Apply territory effects from accumulator (not always in direct mutations)
  if (!is.null(effects$territory_change) && effects$territory_change != 0) {
    state$scenario_state$territory_controlled <- max(0, min(1,
      state$scenario_state$territory_controlled + effects$territory_change))
  }

  # 6. Generate summary message
  summary_msg <- generate_multi_action_summary(approved_actions, effects)
  cat(sprintf("\n    MULTI-ACTION RESULT: %s\n", summary_msg))

  return(state)
}

#' Detect contradictory actions
detect_contradictions <- function(actions) {
  contradictions <- list()
  action_names <- sapply(actions, function(a) a$action)

  # Peace talks + offensive covert actions
  if ("peace_talks" %in% action_names || "mediation_offer" %in% action_names) {
    offensive_covert <- c("sabotage", "assassination_attempt", "regime_destabilization")
    detected_covert <- intersect(action_names, offensive_covert)

    if (length(detected_covert) > 0) {
      # Roll for detection (30% base chance)
      if (runif(1) < 0.3) {
        contradictions[[length(contradictions) + 1]] <- list(
          type = "diplomacy_betrayal",
          actions = c("peace_talks", detected_covert[1]),
          message = sprintf("%s detected during diplomatic negotiations - credibility destroyed", detected_covert[1]),
          penalty = list(
            crisis_change = 3.0,
            international_support_change = -15
          )
        )
      }
    }
  }

  # Coalition building + regime destabilization of potential ally
  if ("coalition_building" %in% action_names && "regime_destabilization" %in% action_names) {
    contradictions[[length(contradictions) + 1]] <- list(
      type = "mixed_signals",
      actions = c("coalition_building", "regime_destabilization"),
      message = "Cannot build coalitions while destabilizing potential partners",
      penalty = list(
        international_support_change = -10
      )
    )
  }

  return(contradictions)
}

#' Apply contradiction penalties
apply_contradiction_penalties <- function(effects, contradictions, actions) {
  for (contra in contradictions) {
    # Apply penalties
    if (!is.null(contra$penalty$crisis_change)) {
      effects$crisis_change <- effects$crisis_change + contra$penalty$crisis_change
    }
    if (!is.null(contra$penalty$international_support_change)) {
      effects$international_support_change <- effects$international_support_change +
                                              contra$penalty$international_support_change
    }

    # Cancel contradictory actions (remove their positive effects)
    effects$messages[[length(effects$messages) + 1]] <- contra$message
  }

  return(effects)
}

#' Detect synergistic action combinations
detect_synergies <- function(actions) {
  synergies <- list()
  action_names <- sapply(actions, function(a) a$action)

  # Intelligence gathering + sabotage = better targeting
  if ("intelligence_gathering" %in% action_names && "sabotage" %in% action_names) {
    synergies[[length(synergies) + 1]] <- list(
      type = "intelligence_targeting",
      actions = c("intelligence_gathering", "sabotage"),
      message = "Intelligence improves sabotage targeting (+20% effectiveness)",
      bonus = list(
        sabotage_effectiveness = 1.2
      )
    )
  }

  # Military buildup + defensive fortification = deterrence
  if ("military_buildup" %in% action_names && "defensive_fortification" %in% action_names) {
    synergies[[length(synergies) + 1]] <- list(
      type = "defensive_deterrence",
      actions = c("military_buildup", "defensive_fortification"),
      message = "Combined defense posture deters aggression (-0.5 crisis)",
      bonus = list(
        crisis_change = -0.5
      )
    )
  }

  # Peace talks + coalition building = negotiating from strength
  if ("peace_talks" %in% action_names && "coalition_building" %in% action_names) {
    synergies[[length(synergies) + 1]] <- list(
      type = "diplomatic_strength",
      actions = c("peace_talks", "coalition_building"),
      message = "Coalition support strengthens negotiating position",
      bonus = list(
        peace_talks_success_bonus = 0.2,
        crisis_change = -0.3
      )
    )
  }

  # Sabotage + limited strike = coordinated offensive
  if ("sabotage" %in% action_names && "limited_strike" %in% action_names) {
    synergies[[length(synergies) + 1]] <- list(
      type = "coordinated_offensive",
      actions = c("sabotage", "limited_strike"),
      message = "Coordinated covert + kinetic offensive amplifies disruption",
      bonus = list(
        military_balance_change = 0.05
      )
    )
  }

  # Spread disinformation + any military action = confusion multiplier
  if ("spread_disinformation" %in% action_names) {
    military_actions <- c("limited_strike", "border_incursion", "military_buildup")
    if (length(intersect(action_names, military_actions)) > 0) {
      synergies[[length(synergies) + 1]] <- list(
        type = "information_warfare",
        actions = c("spread_disinformation", "military_action"),
        message = "Disinformation amplifies military action confusion",
        bonus = list(
          military_balance_change = 0.02
        )
      )
    }
  }

  return(synergies)
}

#' Apply synergy bonus to effects
apply_synergy_bonus <- function(effects, synergy) {
  if (!is.null(synergy$bonus$crisis_change)) {
    effects$crisis_change <- effects$crisis_change + synergy$bonus$crisis_change
  }
  if (!is.null(synergy$bonus$military_balance_change)) {
    effects$military_balance_change <- effects$military_balance_change +
                                       synergy$bonus$military_balance_change
  }

  effects$messages[[length(effects$messages) + 1]] <- synergy$message
  return(effects)
}

#' Categorize actions by type
categorize_actions <- function(actions) {
  categories <- list()
  for (action_item in actions) {
    action_obj <- get_action_definition(action_item$action)
    if (!is.null(action_obj)) {
      category <- action_obj$category
      if (is.null(categories[[category]])) {
        categories[[category]] <- list()
      }
      categories[[category]][[length(categories[[category]]) + 1]] <- action_item$action
    }
  }
  return(categories)
}

#' Get action definition (category, base effects, etc.)
get_action_definition <- function(action_name) {
  # Simplified action definitions - in full implementation, load from action_space.R
  actions <- list(
    # Military posture actions
    military_buildup = list(category = "military_posture", cost = 5.0),
    defensive_fortification = list(category = "military_posture", cost = 3.0),
    military_exercises = list(category = "military_posture", cost = 1.0),
    defensive_reinforcements = list(category = "military_posture", cost = 2.0),
    enhanced_patrols = list(category = "military_posture", cost = 0.5),
    air_patrols = list(category = "military_posture", cost = 0.6),
    troop_movements = list(category = "military_posture", cost = 1.0),
    naval_deployment = list(category = "military_posture", cost = 3.0),
    naval_demonstration = list(category = "military_posture", cost = 1.5),
    naval_patrols = list(category = "military_posture", cost = 0.8),
    show_of_force = list(category = "military_posture", cost = 1.0),
    blockade = list(category = "military_posture", cost = 2.5),

    # Kinetic actions
    limited_strike = list(category = "kinetic", cost = 2.0),
    border_incursion = list(category = "kinetic", cost = 1.5),
    occupation = list(category = "kinetic", cost = 4.0),

    # Diplomatic actions
    peace_talks = list(category = "diplomatic", cost = 0.2),
    formal_peace_talks = list(category = "diplomatic", cost = 0.3),
    backchannel_negotiations = list(category = "diplomatic", cost = 0.1),
    diplomatic_visit = list(category = "diplomatic", cost = 0.1),
    mediation_offer = list(category = "diplomatic", cost = 0.1),
    coalition_building = list(category = "diplomatic", cost = 1.0),
    formal_multilateral_engagement = list(category = "diplomatic", cost = 0.5),
    international_observers = list(category = "diplomatic", cost = 0.3),
    humanitarian_corridors = list(category = "diplomatic", cost = 0.2),
    prisoner_exchange = list(category = "diplomatic", cost = 0.1),
    public_diplomatic_initiative = list(category = "diplomatic", cost = 0.2),
    cultural_exchange = list(category = "diplomatic", cost = 0.1),
    joint_exercises = list(category = "diplomatic", cost = 0.8),

    # Intelligence actions
    intelligence_gathering = list(category = "intelligence", cost = 0.3),
    enhanced_intelligence_gathering = list(category = "intelligence", cost = 0.5),
    enhanced_surveillance = list(category = "intelligence", cost = 0.4),
    surveillance_operation = list(category = "intelligence", cost = 0.4),
    reconnaissance = list(category = "intelligence", cost = 0.3),
    share_intelligence = list(category = "intelligence", cost = 0.2),
    counterintelligence = list(category = "intelligence", cost = 0.4),

    # Covert actions
    sabotage = list(category = "covert", cost = 0.5),
    cyber_attack = list(category = "covert", cost = 0.3),
    cyber_theft = list(category = "covert", cost = 0.4),
    cyber_defense = list(category = "covert", cost = 0.3),
    assassination_attempt = list(category = "covert", cost = 0.8),
    leadership_targeting = list(category = "covert", cost = 0.7),
    regime_destabilization = list(category = "covert", cost = 1.5),
    spread_disinformation = list(category = "information", cost = 0.2),
    false_flag_operation = list(category = "covert", cost = 0.8),
    proxy_support = list(category = "covert", cost = 1.0),
    propaganda_campaign = list(category = "information", cost = 0.3),
    information_campaign = list(category = "information", cost = 0.3),
    political_warfare = list(category = "covert", cost = 0.6),

    # Economic actions
    financial_aid = list(category = "economic", cost = 2.0),
    economic_sanctions = list(category = "economic", cost = 0.5),
    targeted_sanctions = list(category = "economic", cost = 0.3),
    resource_embargo = list(category = "economic", cost = 0.3),
    trade_negotiation = list(category = "economic", cost = 0.2),
    trade_restrictions = list(category = "economic", cost = 0.4),
    strategic_stockpiling = list(category = "economic", cost = 0.8),
    currency_manipulation = list(category = "economic", cost = 0.6),
    arms_development = list(category = "economic", cost = 1.5),
    trade_agreement = list(category = "economic", cost = 0.3),
    asset_seizure = list(category = "economic", cost = 0.4),
    war_bonds = list(category = "economic", cost = 0.5),

    # Humanitarian actions
    humanitarian_aid = list(category = "humanitarian", cost = 1.0)
  )

  if (action_name %in% names(actions)) {
    return(actions[[action_name]])
  } else {
    return(NULL)
  }
}

#' Convert execute_action result to effects format
#'
#' @param result Result from execute_action()
#' @param diminishing_factor Factor to apply for diminishing returns
#' @return Effects list compatible with accumulate_effects()
convert_result_to_effects <- function(result, diminishing_factor = 1.0) {
  # Initialize accumulator format
  effects <- list(
    crisis_change = 0,
    military_balance_change = 0,
    sanctions_change = 0,
    international_support_change = 0,
    gdp_change = 0,
    territory_change = 0,
    cost = 0,
    messages = list()
  )

  # Extract crisis_change from result if present
  if (!is.null(result$effects$crisis_change)) {
    effects$crisis_change <- result$effects$crisis_change * diminishing_factor
  }

  # Map various effects to crisis change (these would increase tensions)
  if (!is.null(result$effects$diplomatic_crisis)) {
    effects$crisis_change <- effects$crisis_change + 2 * diminishing_factor
  }
  if (!is.null(result$effects$detected) && result$effects$detected) {
    effects$crisis_change <- effects$crisis_change + 1 * diminishing_factor
  }

  # Map military-related effects to military_balance_change
  if (!is.null(result$effects$military_degradation)) {
    effects$military_balance_change <- effects$military_balance_change +
      (result$effects$military_degradation * diminishing_factor)
  }
  if (!is.null(result$effects$military_strength_increase)) {
    effects$military_balance_change <- effects$military_balance_change +
      (result$effects$military_strength_increase * diminishing_factor)
  }

  # Map sanctions-related effects
  if (!is.null(result$effects$sanctions_severity)) {
    effects$sanctions_change <- effects$sanctions_change +
      (result$effects$sanctions_severity * diminishing_factor)
  }

  # Map international support effects
  if (!is.null(result$effects$international_support)) {
    effects$international_support_change <- effects$international_support_change +
      (result$effects$international_support * diminishing_factor)
  }
  if (!is.null(result$effects$international_condemnation)) {
    effects$international_support_change <- effects$international_support_change -
      (result$effects$international_condemnation * diminishing_factor)
  }

  # Map economic effects
  if (!is.null(result$effects$gdp_growth_actor)) {
    effects$gdp_change <- effects$gdp_change +
      (result$effects$gdp_growth_actor * diminishing_factor)
  }
  if (!is.null(result$effects$target_gdp_impact)) {
    effects$gdp_change <- effects$gdp_change +
      (result$effects$target_gdp_impact * diminishing_factor)
  }

  # Map territory effects
  if (!is.null(result$effects$territory_seized)) {
    effects$territory_change <- effects$territory_change +
      (result$effects$territory_seized * diminishing_factor)
  }

  # Add message
  if (!is.null(result$effects$message)) {
    effects$messages[[length(effects$messages) + 1]] <- result$effects$message
  }

  # Note: Cost is handled separately in the main loop

  return(effects)
}

#' Scale effects by diminishing returns factor
scale_effects <- function(effects, factor) {
  effects$crisis_change <- effects$crisis_change * factor
  effects$military_balance_change <- effects$military_balance_change * factor
  effects$sanctions_change <- effects$sanctions_change * factor
  effects$international_support_change <- effects$international_support_change * factor
  effects$gdp_change <- effects$gdp_change * factor
  effects$territory_change <- effects$territory_change * factor
  # Cost not scaled (you pay full price even with diminishing returns)
  return(effects)
}

#' Accumulate effects from multiple actions
accumulate_effects <- function(total_effects, action_effects) {
  total_effects$crisis_change <- total_effects$crisis_change + action_effects$crisis_change
  total_effects$military_balance_change <- total_effects$military_balance_change +
                                           action_effects$military_balance_change
  total_effects$sanctions_change <- total_effects$sanctions_change + action_effects$sanctions_change
  total_effects$international_support_change <- total_effects$international_support_change +
                                                action_effects$international_support_change
  total_effects$gdp_change <- total_effects$gdp_change + action_effects$gdp_change
  total_effects$territory_change <- total_effects$territory_change + action_effects$territory_change
  total_effects$total_cost <- total_effects$total_cost + action_effects$cost

  return(total_effects)
}

#' Apply accumulated effects to simulation state
apply_effects_to_state <- function(state, effects, agent) {
  # Apply crisis change
  if (!is.null(state$scenario_state$crisis_level)) {
    state$scenario_state$crisis_level <- max(0, min(10,
      state$scenario_state$crisis_level + effects$crisis_change))
  }

  # Apply military balance change (clamped to -1 to +1)
  if (!is.null(state$scenario_state$military_balance)) {
    state$scenario_state$military_balance <- max(-1, min(1,
      state$scenario_state$military_balance + effects$military_balance_change))
  }

  # Apply sanctions change (clamped to 0-1)
  if (!is.null(state$scenario_state$sanctions_level) && !is.null(effects$sanctions_change)) {
    state$scenario_state$sanctions_level <- max(0, min(1,
      state$scenario_state$sanctions_level + effects$sanctions_change))
  }

  # Apply international support change (clamped to 0-1)
  if (!is.null(state$scenario_state$international_support)) {
    state$scenario_state$international_support <- max(0, min(1,
      state$scenario_state$international_support + effects$international_support_change))
  }

  # Apply territory change (clamped to 0-1)
  if (!is.null(state$scenario_state$territory_controlled) && !is.null(effects$territory_change)) {
    state$scenario_state$territory_controlled <- max(0, min(1,
      state$scenario_state$territory_controlled + effects$territory_change))
  }

  # Apply GDP effects (GDP lives in faction_capabilities, not scenario_state)
  if (!is.null(state$faction_capabilities) && !is.null(agent$faction)) {
    # Target GDP damage (accumulated from target_gdp_impact of individual actions)
    if (!is.null(effects$gdp_change) && effects$gdp_change != 0) {
      if (agent$faction == "major_power") {
        state$faction_capabilities$small_power_gdp <-
          max(5, state$faction_capabilities$small_power_gdp * (1 + effects$gdp_change))
      } else if (agent$faction == "small_power") {
        state$faction_capabilities$major_power_gdp <-
          max(10, state$faction_capabilities$major_power_gdp * (1 + effects$gdp_change))
      }
    }
    # Action costs deducted from own GDP
    if (!is.null(effects$total_cost) && effects$total_cost > 0) {
      if (agent$faction == "major_power") {
        state$faction_capabilities$major_power_gdp <-
          max(10, state$faction_capabilities$major_power_gdp - effects$total_cost)
      } else if (agent$faction == "small_power") {
        state$faction_capabilities$small_power_gdp <-
          max(5, state$faction_capabilities$small_power_gdp - effects$total_cost)
      }
    }
  }

  return(state)
}

#' Generate summary message for multi-action results
generate_multi_action_summary <- function(actions, effects) {
  summary_parts <- list()

  if (abs(effects$crisis_change) > 0.1) {
    direction <- if(effects$crisis_change > 0) "increased" else "decreased"
    summary_parts[[length(summary_parts) + 1]] <- sprintf(
      "Crisis %s by %.1f", direction, abs(effects$crisis_change)
    )
  }

  if (abs(effects$military_balance_change) > 0.01) {
    direction <- if(effects$military_balance_change > 0) "improved" else "degraded"
    summary_parts[[length(summary_parts) + 1]] <- sprintf(
      "Military balance %s by %.2f", direction, abs(effects$military_balance_change)
    )
  }

  if (effects$total_cost > 0) {
    summary_parts[[length(summary_parts) + 1]] <- sprintf(
      "Total cost $%.1fB", effects$total_cost
    )
  }

  if (length(summary_parts) == 0) {
    return(sprintf("%d actions executed", length(actions)))
  } else {
    return(paste(summary_parts, collapse = ", "))
  }
}
