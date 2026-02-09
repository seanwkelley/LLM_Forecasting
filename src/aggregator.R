# Aggregator LLM - evaluates probability of government collapse

#' Prepare summary of simulation state for aggregator
#'
#' @param period Current period number
#' @param events List of events from this period
#' @param interactions List of interactions from this period
#' @param previous_assessment Previous probability assessment (if any)
#' @param scenario_state Current scenario state with metrics
#' @param action_results List of action results from this period (v3.3)
#' @param previous_state Previous period's scenario state for delta calculation (v3.3)
#' @param full_history List containing assessments_history, action_results, events_history, state_history (v3.3)
#' @return Character string with formatted summary
prepare_aggregator_context <- function(period, events, interactions, previous_assessment = NULL,
                                       scenario_state = NULL, action_results = NULL, previous_state = NULL,
                                       full_history = NULL) {

  # FULL HISTORY SUMMARY (v3.3) - Give aggregator complete picture
  history_text <- ""
  if (!is.null(full_history) && period > 1) {
    history_parts <- c()

    # Probability trajectory
    if (!is.null(full_history$assessments_history) && length(full_history$assessments_history) > 0) {
      prob_trajectory <- sapply(seq_len(period - 1), function(p) {
        if (p <= length(full_history$assessments_history) && !is.null(full_history$assessments_history[[p]])) {
          sprintf("P%.0f: %.0f%%", p, full_history$assessments_history[[p]]$probability * 100)
        } else {
          NULL
        }
      })
      prob_trajectory <- prob_trajectory[!sapply(prob_trajectory, is.null)]
      if (length(prob_trajectory) > 0) {
        history_parts <- c(history_parts,
                          sprintf("Probability trajectory: %s → Current period %.0f",
                                  paste(prob_trajectory, collapse = " → "), period))
      }
    }

    # Key state evolution
    if (!is.null(full_history$state_history) && length(full_history$state_history) > 0) {
      # Get first and most recent states for comparison
      first_state <- full_history$state_history[[1]]$scenario_state
      if (!is.null(first_state) && !is.null(scenario_state)) {
        cumulative_changes <- c()

        territory_change <- scenario_state$territory_controlled - first_state$territory_controlled
        if (abs(territory_change) > 0.01) {
          cumulative_changes <- c(cumulative_changes,
                                  sprintf("Territory: %.1f%% → %.1f%% (%+.1f%%)",
                                          first_state$territory_controlled * 100,
                                          scenario_state$territory_controlled * 100,
                                          territory_change * 100))
        }

        military_change <- scenario_state$military_balance - first_state$military_balance
        if (abs(military_change) > 0.05) {
          cumulative_changes <- c(cumulative_changes,
                                  sprintf("Military balance: %.2f → %.2f (%+.2f)",
                                          first_state$military_balance,
                                          scenario_state$military_balance,
                                          military_change))
        }

        crisis_change <- scenario_state$crisis_level - first_state$crisis_level
        if (crisis_change != 0) {
          cumulative_changes <- c(cumulative_changes,
                                  sprintf("Crisis: %.0f → %.0f (%+.0f)",
                                          first_state$crisis_level,
                                          scenario_state$crisis_level,
                                          crisis_change))
        }

        if (length(cumulative_changes) > 0) {
          history_parts <- c(history_parts,
                            paste("Cumulative state changes since Period 1:",
                                  paste(cumulative_changes, collapse = "; ")))
        }
      }
    }

    # Major actions summary (last 3 periods or all if fewer)
    if (!is.null(full_history$action_results)) {
      start_period <- max(1, period - 3)
      action_summary_lines <- c()

      for (p in start_period:(period - 1)) {
        if (p <= length(full_history$action_results) && length(full_history$action_results[[p]]) > 0) {
          period_actions <- sapply(full_history$action_results[[p]], function(ar) {
            sprintf("%s:%s", ar$actor_faction, ar$action)
          })
          action_summary_lines <- c(action_summary_lines,
                                   sprintf("P%.0f: %s", p, paste(period_actions, collapse = ", ")))
        }
      }

      if (length(action_summary_lines) > 0) {
        history_parts <- c(history_parts,
                          paste("Recent actions:", paste(action_summary_lines, collapse = " | ")))
      }
    }

    # Shock events history
    if (!is.null(full_history$events_history)) {
      shock_events <- c()
      for (p in seq_len(period - 1)) {
        if (p <= length(full_history$events_history)) {
          for (e in full_history$events_history[[p]]) {
            if (!is.null(e$is_shock) && e$is_shock) {
              shock_events <- c(shock_events, sprintf("P%.0f: %s", p, e$name))
            }
          }
        }
      }
      if (length(shock_events) > 0) {
        history_parts <- c(history_parts,
                          sprintf("Previous shock events: %s", paste(shock_events, collapse = "; ")))
      }
    }

    if (length(history_parts) > 0) {
      history_text <- paste(c("\nHISTORICAL CONTEXT:", history_parts), collapse = "\n- ")
    }
  }
  # Event summary - highlight shock events specially
  event_summary <- if (length(events) > 0) {
    paste(sapply(events, function(e) {
      if (!is.null(e$is_shock) && e$is_shock) {
        # Shock events get special formatting with impact indicator
        impact_direction <- if (!is.null(e$impact_on_collapse) && e$impact_on_collapse > 0) {
          sprintf(" [HIGH IMPACT: +%.0f%% collapse risk]", e$impact_on_collapse * 100)
        } else if (!is.null(e$impact_on_collapse) && e$impact_on_collapse < 0) {
          sprintf(" [HIGH IMPACT: %.0f%% collapse risk]", e$impact_on_collapse * 100)
        } else {
          ""
        }
        sprintf("*** SHOCK: %s ***: %s%s", e$name, e$description, impact_direction)
      } else {
        sprintf("- %s (%s): %s", e$name, e$type, e$description)
      }
    }), collapse = "\n")
  } else {
    "No major external events this period."
  }

  # ACTION RESULTS SUMMARY (v3.3) - Critical for understanding what happened
  action_summary <- if (!is.null(action_results) && length(action_results) > 0) {
    action_lines <- sapply(action_results, function(ar) {
      success_text <- if (!is.null(ar$success)) {
        if (ar$success) "SUCCESS" else "FAILED"
      } else {
        "EXECUTED"
      }

      # Build effects summary
      effects_text <- ""
      if (!is.null(ar$effects)) {
        effect_parts <- c()
        if (!is.null(ar$effects$territory_change) && ar$effects$territory_change != 0) {
          effect_parts <- c(effect_parts, sprintf("territory %+.1f%%", ar$effects$territory_change * 100))
        }
        if (!is.null(ar$effects$military_change) && ar$effects$military_change != 0) {
          effect_parts <- c(effect_parts, sprintf("military %+.0f%%", ar$effects$military_change * 100))
        }
        if (!is.null(ar$effects$crisis_change) && ar$effects$crisis_change != 0) {
          effect_parts <- c(effect_parts, sprintf("crisis %+.0f", ar$effects$crisis_change))
        }
        if (!is.null(ar$effects$gdp_change) && ar$effects$gdp_change != 0) {
          effect_parts <- c(effect_parts, sprintf("GDP %+.1fB", ar$effects$gdp_change))
        }
        if (length(effect_parts) > 0) {
          effects_text <- sprintf(" → Effects: %s", paste(effect_parts, collapse = ", "))
        }
      }

      sprintf("- %s executed %s: %s%s",
              ar$actor_faction, ar$action, success_text, effects_text)
    })
    paste(c("ACTIONS TAKEN THIS PERIOD:", action_lines), collapse = "\n")
  } else {
    "No faction actions recorded this period."
  }

  # STATE CHANGE DELTAS (v3.3) - Show how situation changed
  delta_text <- if (!is.null(previous_state) && !is.null(scenario_state)) {
    deltas <- c()

    territory_delta <- scenario_state$territory_controlled - previous_state$territory_controlled
    if (abs(territory_delta) > 0.001) {
      deltas <- c(deltas, sprintf("Territory: %+.1f%% (%.1f%% → %.1f%%)",
                                   territory_delta * 100,
                                   previous_state$territory_controlled * 100,
                                   scenario_state$territory_controlled * 100))
    }

    military_delta <- scenario_state$military_balance - previous_state$military_balance
    if (abs(military_delta) > 0.01) {
      deltas <- c(deltas, sprintf("Military balance: %+.2f (%.2f → %.2f)",
                                   military_delta,
                                   previous_state$military_balance,
                                   scenario_state$military_balance))
    }

    crisis_delta <- scenario_state$crisis_level - previous_state$crisis_level
    if (crisis_delta != 0) {
      deltas <- c(deltas, sprintf("Crisis level: %+.0f (%.0f → %.0f)",
                                   crisis_delta,
                                   previous_state$crisis_level,
                                   scenario_state$crisis_level))
    }

    if (length(deltas) > 0) {
      paste(c("\nSTATE CHANGES THIS PERIOD:", deltas), collapse = "\n- ")
    } else {
      "\nSTATE CHANGES THIS PERIOD: Minimal changes"
    }
  } else {
    ""
  }

  # Interaction summary
  interaction_summary <- if (length(interactions) > 0) {
    # Group by faction
    major_power_msgs <- list()
    small_power_msgs <- list()
    external_msgs <- list()

    for (int in interactions) {
      summary_text <- sprintf(
        "%s (%s): %.0f participants discussed '%s'",
        int$type,
        paste(unique(int$participant_factions), collapse = " & "),
        length(int$participants),
        int$topic
      )

      # Categorize by primary faction involved
      if ("major_power" %in% int$participant_factions &&
          "small_power" %in% int$participant_factions) {
        small_power_msgs <- c(small_power_msgs, summary_text)
      } else if ("major_power" %in% int$participant_factions) {
        major_power_msgs <- c(major_power_msgs, summary_text)
      } else if ("small_power" %in% int$participant_factions) {
        small_power_msgs <- c(small_power_msgs, summary_text)
      } else {
        external_msgs <- c(external_msgs, summary_text)
      }
    }

    parts <- character(0)
    if (length(major_power_msgs) > 0) {
      parts <- c(parts, "Major Power Internal Dynamics:",
                 paste("-", major_power_msgs, collapse = "\n"))
    }
    if (length(small_power_msgs) > 0) {
      parts <- c(parts, "\nSmaller Power Dynamics:",
                 paste("-", small_power_msgs, collapse = "\n"))
    }
    if (length(external_msgs) > 0) {
      parts <- c(parts, "\nExternal Actor Engagement:",
                 paste("-", external_msgs, collapse = "\n"))
    }

    paste(parts, collapse = "\n")
  } else {
    "No significant interactions recorded this period."
  }

  # Previous assessment context
  previous_text <- if (!is.null(previous_assessment)) {
    sprintf(
      "\nPREVIOUS ASSESSMENT (Period %.0f):\nProbability of government collapse: %.1f%%\nKey factors: %s",
      previous_assessment$period,
      previous_assessment$probability * 100,
      previous_assessment$key_factors
    )
  } else {
    "\nThis is the initial assessment at the start of the conflict."
  }

  # Scenario metrics context
  metrics_text <- if (!is.null(scenario_state)) {
    sprintf(
      "\nCURRENT SCENARIO METRICS:
- Territory controlled by aggressor: %.1f%%
- Military balance: %.2f (negative = aggressor advantage, positive = defender advantage)
- Crisis level: %.0f/10
- Sanctions level: %.1f%%
- International support for smaller power: %.1f%%
- Momentum: %.2f (negative = aggressor momentum, positive = defender momentum)
- Nuclear weapons used: %s",
      scenario_state$territory_controlled * 100,
      scenario_state$military_balance,
      scenario_state$crisis_level,
      scenario_state$sanctions_level * 100,
      scenario_state$international_support * 100,
      scenario_state$momentum,
      ifelse(scenario_state$nuclear_used, "YES - CRITICAL", "No")
    )
  } else {
    ""
  }

  context <- sprintf(
    "SIMULATION PERIOD %.0f - Day %.0f of Simulated Scenario
%s
%s
%s

%s

SIMULATED EXTERNAL EVENTS:
%s

AGENT INTERACTIONS AND SIMULATED DYNAMICS:
%s
%s

Based on this simulated information, provide your analytical assessment of the probability of government change in this theoretical scenario.

IMPORTANT: Pay close attention to SHOCK EVENTS (marked with ***) as these represent major developments that should significantly influence your probability estimate. Consider the HISTORICAL CONTEXT showing how the conflict has evolved, and note the STATE CHANGES showing how the situation evolved this period.",
    period,
    period * 7,  # Assuming 7 days per period
    metrics_text,
    history_text,
    delta_text,
    action_summary,
    event_summary,
    interaction_summary,
    previous_text
  )

  return(context)
}

#' Generate aggregator system prompt
#'
#' @return Character string with system prompt
generate_aggregator_prompt <- function() {
  prompt <- "You are an expert analyst in an academic geopolitical simulation, tasked with forecasting government stability outcomes.

CONTEXT: This is a research simulation studying decision-making in theoretical conflict scenarios. You are analyzing simulated data from LLM agents representing different stakeholders.

Your analytical role:
1. Analyze simulated conflict dynamics from agent interactions
2. Consider military, economic, political, and diplomatic factors
3. Assess the theoretical stability of the smaller power's government in this simulation
4. Provide a probabilistic forecast (0-100%) of government change

DEFINITION: Government change in this simulation means the smaller power's current government loses control through:
- Loss of territorial control
- Internal political change
- Negotiated political transition
- Loss of governing capacity

Analytical factors to consider:
- Simulated military situation: territorial control, operational momentum
- Economic conditions: sanctions impact, resource constraints
- Political dynamics: internal cohesion, opposition activity
- International factors: external support, diplomatic pressure
- Domestic factors: public support levels, institutional resilience
- Strategic commitment: resource expenditure, policy sustainability

CRITICAL GUIDANCE ON PROBABILITY UPDATES:
- SHOCK EVENTS (marked with ***) should cause SIGNIFICANT probability changes (+/- 10-30%)
- Military actions that succeed/fail should move probability meaningfully
- Do NOT smooth your estimates too much - real conflicts have dramatic turns
- If territory is lost rapidly, probability should spike
- If a coup attempt occurs, this is a near-collapse event - probability should jump dramatically
- Conversely, major defensive victories should significantly reduce probability
- Your estimates should reflect the DRAMA of the situation, not trend toward gradual change

Examples of appropriate magnitude:
- Coup attempt: +25-35% to collapse probability
- Capital under siege: +20-30%
- Major military disaster: +15-25%
- Successful peace breakthrough: -15-25%
- Allied abandonment: +10-20%

Provide your assessment in this structured format:
PROBABILITY: [number between 0 and 1, e.g., 0.35 for 35%]
CONFIDENCE: [LOW/MEDIUM/HIGH]
KEY_FACTORS: [brief analytical explanation of main factors]
TREND: [INCREASING/STABLE/DECREASING compared to previous period if applicable]

Base your forecast on the simulated evidence and theoretical frameworks for government stability."

  return(prompt)
}

#' Get probability assessment from aggregator LLM
#'
#' @param context Formatted context string
#' @param api_key OpenRouter API key
#' @return List with probability, confidence, factors, and trend
assess_collapse_probability <- function(context, api_key) {
  system_prompt <- generate_aggregator_prompt()
  response <- call_llm(system_prompt, context, AGGREGATOR_MODEL, api_key)

  # Parse the response
  probability <- NA
  confidence <- "MEDIUM"
  key_factors <- ""
  trend <- "STABLE"

  # Extract probability - handle various formats like "0.35", "**0.35**", "35%", "**35%**"
  # First try to find any number after PROBABILITY:
  prob_match <- regexpr("PROBABILITY:\\s*\\**([0-9.]+)%?\\**", response, perl = TRUE)
  if (prob_match > 0) {
    prob_text <- regmatches(response, prob_match)
    # Extract just the numeric part
    num_match <- regexpr("[0-9.]+", prob_text)
    if (num_match > 0) {
      prob_value <- as.numeric(regmatches(prob_text, num_match))
      # If value > 1, assume it's a percentage and convert
      if (!is.na(prob_value) && prob_value > 1) {
        prob_value <- prob_value / 100
      }
      probability <- prob_value
    }
  }

  # Extract confidence - handle markdown formatting like **HIGH**
  conf_match <- regexpr("CONFIDENCE:\\s*\\**\\s*(LOW|MEDIUM|HIGH)", response, perl = TRUE, ignore.case = TRUE)
  if (conf_match > 0) {
    conf_text <- regmatches(response, conf_match)
    # Extract just LOW/MEDIUM/HIGH
    level_match <- regexpr("(LOW|MEDIUM|HIGH)", conf_text, ignore.case = TRUE)
    if (level_match > 0) {
      confidence <- toupper(regmatches(conf_text, level_match))
    }
  }

  # Extract key factors
  factors_match <- regexpr("KEY_FACTORS:\\s*(.+?)(?=\\nTREND:|$)", response, perl = TRUE)
  if (factors_match > 0) {
    factors_text <- regmatches(response, factors_match)
    key_factors <- sub("KEY_FACTORS:\\s*", "", factors_text)
    key_factors <- trimws(key_factors)
  }

  # Extract trend - handle markdown formatting like **INCREASING**
  trend_match <- regexpr("TREND:\\s*\\**\\s*(INCREASING|STABLE|DECREASING)", response, perl = TRUE, ignore.case = TRUE)
  if (trend_match > 0) {
    trend_text <- regmatches(response, trend_match)
    # Extract just the trend word
    dir_match <- regexpr("(INCREASING|STABLE|DECREASING)", trend_text, ignore.case = TRUE)
    if (dir_match > 0) {
      trend <- toupper(regmatches(trend_text, dir_match))
    }
  }

  assessment <- list(
    probability = probability,
    confidence = confidence,
    key_factors = key_factors,
    trend = trend,
    full_response = response,
    timestamp = Sys.time()
  )

  return(assessment)
}

#' Run aggregator assessment for a period
#'
#' @param period Current period
#' @param events Events from this period
#' @param interaction_session Completed interaction session
#' @param previous_assessment Previous assessment (if any)
#' @param scenario_state Current scenario state
#' @param api_key OpenRouter API key
#' @param action_results List of action results from this period (v3.3)
#' @param previous_state Previous period's scenario state for delta calculation (v3.3)
#' @param full_history List with assessments_history, action_results, events_history, state_history (v3.3)
#' @return Assessment object
run_aggregator_assessment <- function(period, events, interaction_session,
                                     previous_assessment = NULL, scenario_state = NULL, api_key,
                                     action_results = NULL, previous_state = NULL,
                                     full_history = NULL) {
  cat(sprintf("\nPeriod %.0f: Running aggregator assessment...\n", period))

  context <- prepare_aggregator_context(
    period,
    events,
    interaction_session$interactions,
    previous_assessment,
    scenario_state,
    action_results,
    previous_state,
    full_history
  )

  assessment <- assess_collapse_probability(context, api_key)
  assessment$period <- period

  cat(sprintf("  Probability of government collapse: %.1f%%\n",
              assessment$probability * 100))
  cat(sprintf("  Confidence: %s\n", assessment$confidence))
  cat(sprintf("  Trend: %s\n", assessment$trend))

  return(assessment)
}
