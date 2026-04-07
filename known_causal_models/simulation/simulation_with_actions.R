# Enhanced Simulation with Action Execution
# Agents not only discuss but actually take concrete actions

# Source all required modules
# NOTE: config.R is sourced by calling script (run_simulation_with_actions.R)
# to preserve the enhanced AGENTS list with agent_id fields
source("src/agent_system.R")
source("src/event_generator.R")
source("src/interaction_engine.R")
source("src/aggregator.R")
source("src/state_manager.R")
source("src/agent_decision.R")  # NEW: Action decision system
source("src/action_execution.R")  # NEW: Action execution
source("src/multi_action_system.R")  # Multi-action proposal/approval system
source("src/multi_action_effects.R")  # Multi-action effect resolution

#' Run a single period of the simulation with action execution
#'
#' @param state Simulation state object
#' @param period Period number
#' @param api_key OpenRouter API key
#' @param data_dir Data directory path
#' @param output_dir Output directory path
#' @return Updated simulation state
run_simulation_period_with_actions <- function(state, period, api_key, data_dir, output_dir) {
  cat(sprintf("\n========== PERIOD %d (Day %d) ==========\n",
              period, period * PERIOD_DURATION_DAYS))

  # Initialize action tracking in state if not present
  if (is.null(state$action_decisions)) {
    state$action_decisions <- list()
  }
  if (is.null(state$action_results)) {
    state$action_results <- list()
  }
  if (is.null(state$pre_action_coordination)) {
    state$pre_action_coordination <- list()
  }
  if (is.null(state$faction_capabilities)) {
    state$faction_capabilities <- list(
      major_power_military = 1.0,
      small_power_military = 0.6,
      major_power_gdp = 100.0,  # Billions
      small_power_gdp = 30.0
    )
  }

  # Step 1: Generate external events
  cat("\n1. Generating external events...\n")
  events <- generate_external_events(period, EXTERNAL_EVENTS)

  # Add specific event types based on scenario state
  if (runif(1) < 0.6) {
    battlefield_event <- generate_battlefield_event(
      period,
      state$scenario_state$military_balance
    )
    events <- c(events, list(battlefield_event))
  }

  # Check if we already have a commodity event before adding economic event
  has_commodity_event <- any(sapply(events, function(e) e$type == "commodity_shock"))

  if (runif(1) < 0.4 && !has_commodity_event) {
    economic_event <- generate_economic_event(
      period,
      state$scenario_state$sanctions_level
    )
    events <- c(events, list(economic_event))
  }

  if (runif(1) < 0.3) {
    diplomatic_event <- generate_diplomatic_event(period)
    events <- c(events, list(diplomatic_event))
  }

  # MULTI-DOMAIN EVENTS
  # Naval incidents (25% chance)
  if (runif(1) < 0.25) {
    naval_event <- generate_naval_event(period)
    events <- c(events, list(naval_event))
  }

  # Air warfare incidents (25% chance)
  if (runif(1) < 0.25) {
    air_event <- generate_air_event(period)
    events <- c(events, list(air_event))
  }

  # Cyber incidents (30% chance)
  if (runif(1) < 0.30) {
    cyber_event <- generate_cyber_event(period)
    events <- c(events, list(cyber_event))
  }

  # Information warfare (30% chance)
  if (runif(1) < 0.30) {
    info_event <- generate_information_event(period)
    events <- c(events, list(info_event))
  }

  # HIGH-IMPACT SHOCK EVENTS (leadership challenges, military disasters, etc.)
  shock_event <- generate_shock_event(period, state$scenario_state)
  if (!is.null(shock_event)) {
    events <- c(events, list(shock_event))
    cat(sprintf("  *** SHOCK EVENT: %s ***\n", shock_event$name))

    # Apply shock event effects to state
    if (!is.null(shock_event$impact_on_collapse)) {
      # Shock events affect territory, military balance, or crisis level
      if (grepl("military_disaster_small|coup_attempt", shock_event$type)) {
        # Catastrophic events cause territory loss
        state$scenario_state$territory_controlled <-
          min(0.5, state$scenario_state$territory_controlled + 0.05)
        state$scenario_state$military_balance <-
          max(-1, min(1, state$scenario_state$military_balance - 0.15))
      } else if (grepl("military_disaster_major|domestic_crisis_major", shock_event$type)) {
        # Events hurting aggressor improve defender position
        state$scenario_state$military_balance <-
          max(-1, min(1, state$scenario_state$military_balance + 0.10))
        state$scenario_state$momentum <-
          min(0.3, state$scenario_state$momentum + 0.15)
      } else if (grepl("leadership_challenge|economic_collapse", shock_event$type)) {
        # Political/economic instability increases crisis
        state$scenario_state$crisis_level <-
          min(10, state$scenario_state$crisis_level + 1)
      } else if (grepl("diplomatic_breakthrough", shock_event$type)) {
        # Positive diplomatic events reduce crisis
        state$scenario_state$crisis_level <-
          max(1, state$scenario_state$crisis_level - 2)
      }
    }
  }

  cat(sprintf("  Generated %d events\n", length(events)))
  for (event in events) {
    cat(sprintf("  - %s\n", event$name))
  }

  # Save events
  state$events_history[[period]] <- events

  # Step 2: Pre-Action Coordination
  # Agents within each faction discuss and debate what action to take
  cat("\n2. Pre-action coordination (intra-faction debate)...\n")

  # Step 3: Action Decision & Execution
  # Faction leaders decide and execute concrete actions based on coordination
  cat("\n3. Action decision & execution...\n")
  state <- run_action_decision_phase(state$agents, period, state, api_key)

  # Step 4: Post-Action Discussion
  # Agents react to results and coordinate responses
  # Skip for single-period runs (no subsequent period to use the discussions)
  skip_post_action <- identical(Sys.getenv("SKIP_POST_ACTION_DISCUSSIONS"), "1")
  if (!skip_post_action) {
    cat("\n4. Post-action discussion (agent interactions)...\n")
    context <- list(
      period = period,
      scenario_state = state$scenario_state,
      recent_events = events,
      action_results = state$action_results[[period]]  # Include what just happened
    )

    interaction_session <- create_interaction_session(
      period,
      state$agents,
      context
    )

    interaction_session <- run_interaction_session(interaction_session, api_key)

    cat(sprintf("  Completed %d interactions\n", interaction_session$interaction_count))

    # Save interactions to memory and CSV
    state$interactions_history[[period]] <- interaction_session
    save_interactions_to_csv(interaction_session)  # Save post-action discussions to CSV
  } else {
    cat("\n4. Post-action discussion SKIPPED (single-period mode)\n")
    interaction_session <- list(interactions = list(), interaction_count = 0)
    state$interactions_history[[period]] <- interaction_session
  }

  # Step 5: Update scenario state based on events AND actions
  cat("\n5. Updating scenario state...\n")
  # Note: update_scenario_state expects (state, period, events, assessment)
  # We'll call it without assessment for now, then update after aggregator runs
  state$scenario_state$current_day <- period * PERIOD_DURATION_DAYS

  # Update state based on external events
  # Design: Events are probabilistic in two ways:
  #   1. Whether the event occurs at all (probability in config.R EXTERNAL_EVENTS)
  #   2. Whether the event has a meaningful effect on state (effectiveness probability below)
  # Battlefield events have higher effectiveness (direct physical outcomes).
  # Other events have lower effectiveness (implementation challenges, enforcement gaps, etc.).
  # Effect magnitudes are also randomized within ranges for additional variance.
  for (event in events) {
    severity <- if (!is.null(event$severity)) event$severity else runif(1, 0.5, 1.0)

    if (event$type == "battlefield") {
      # Battlefield: 85% effectiveness (high - physical outcomes are concrete)
      if (!is.null(event$impact_type) && runif(1) < 0.85) {
        if (event$impact_type == "defender_success") {
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance + 0.1 * severity))
          # Defender recaptures territory (2-5%)
          territory_loss <- runif(1, 0.02, 0.05) * severity
          state$scenario_state$territory_controlled <-
            max(0, state$scenario_state$territory_controlled - territory_loss)
        } else if (event$impact_type == "aggressor_success") {
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance - 0.1 * severity))
          # Aggressor captures territory (3-8%)
          territory_gain <- runif(1, 0.03, 0.08) * severity
          state$scenario_state$territory_controlled <-
            min(1.0, state$scenario_state$territory_controlled + territory_gain)
        }
      }

    } else if (event$type == "sanctions") {
      # Sanctions: 70% effectiveness (enforcement challenges, workarounds)
      if (runif(1) < 0.70) {
        state$scenario_state$sanctions_level <-
          min(1.0, state$scenario_state$sanctions_level + runif(1, 0.05, 0.10) * severity)
      }

    } else if (event$type == "military_aid_defender") {
      # Military aid: 75% effectiveness (logistics, absorption capacity)
      if (runif(1) < 0.75) {
        state$scenario_state$military_balance <-
          max(-1, min(1, state$scenario_state$military_balance + 0.05 * severity))
        state$scenario_state$international_support <-
          min(1.0, state$scenario_state$international_support + 0.05 * severity)
      }

    } else if (event$type == "allied_support_wavers") {
      # Allied wavering: 65% effectiveness (political rhetoric vs actual policy change)
      if (runif(1) < 0.65) {
        state$scenario_state$international_support <-
          max(0, state$scenario_state$international_support - 0.05 * severity)
      }

    } else if (event$type == "diplomatic") {
      # Diplomacy: 50% effectiveness (talks often fail to produce results)
      if (runif(1) < 0.50) {
        state$scenario_state$crisis_level <-
          max(0, state$scenario_state$crisis_level - 0.5 * severity)
      }

    } else if (event$type == "public_opinion_aggressor") {
      # Domestic protests: 55% effectiveness (governments can suppress/ignore)
      if (runif(1) < 0.55) {
        state$scenario_state$crisis_level <-
          max(0, state$scenario_state$crisis_level - 0.5 * severity)
      }

    } else if (event$type == "defender_strain") {
      # War fatigue: 70% effectiveness (real economic/social pressure)
      if (runif(1) < 0.70) {
        state$scenario_state$crisis_level <-
          min(10, state$scenario_state$crisis_level + 0.5 * severity)
      }

    } else if (event$type == "economic_aggressor") {
      # Economic strain on aggressor: 60% effectiveness
      if (runif(1) < 0.60) {
        state$scenario_state$crisis_level <-
          max(0, state$scenario_state$crisis_level - 0.3 * severity)
      }

    } else if (event$type == "economic_defender") {
      # Economic strain on defender: 70% effectiveness
      if (runif(1) < 0.70) {
        state$scenario_state$crisis_level <-
          min(10, state$scenario_state$crisis_level + 0.5 * severity)
      }

    } else if (event$type == "commodity_shock") {
      # Commodity shock: 60% effectiveness (hedging, reserves can buffer)
      if (runif(1) < 0.60) {
        state$scenario_state$crisis_level <-
          min(10, state$scenario_state$crisis_level + 0.3 * severity)
      }

    } else if (event$type == "naval") {
      # Naval incidents: 65% effectiveness (physical confrontations at sea)
      if (runif(1) < 0.65) {
        # Naval events generally increase crisis
        state$scenario_state$crisis_level <-
          min(10, state$scenario_state$crisis_level + 0.3 * severity)
        # Shift military balance based on who benefits
        if (grepl("defender|defense_small|posturing_defender", event$impact_type)) {
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance + 0.02 * severity))
        } else if (grepl("escalation_major|blockade", event$impact_type)) {
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance - 0.02 * severity))
          # Quasi-blockades also raise sanctions pressure
          if (grepl("blockade", event$impact_type)) {
            state$scenario_state$sanctions_level <-
              min(1.0, state$scenario_state$sanctions_level + 0.03 * severity)
          }
        }
      }

    } else if (event$type == "air") {
      # Air incidents: 65% effectiveness (airspace violations are concrete)
      if (runif(1) < 0.65) {
        # Air events escalate crisis
        state$scenario_state$crisis_level <-
          min(10, state$scenario_state$crisis_level + 0.3 * severity)
        # Shootdowns and readiness shifts are more significant
        if (grepl("shootdown|drone_escalation", event$impact_type)) {
          state$scenario_state$crisis_level <-
            min(10, state$scenario_state$crisis_level + 0.2 * severity)
        }
        # Air defense deployments shift balance
        if (grepl("defense_small", event$impact_type)) {
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance + 0.02 * severity))
        } else if (grepl("defense_major", event$impact_type)) {
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance - 0.02 * severity))
        }
        # No-fly zone discussion is de-escalatory
        if (grepl("no_fly_zone", event$impact_type)) {
          state$scenario_state$crisis_level <-
            max(0, state$scenario_state$crisis_level - 0.3 * severity)
          state$scenario_state$international_support <-
            min(1.0, state$scenario_state$international_support + 0.03 * severity)
        }
      }

    } else if (event$type == "cyber") {
      # Cyber incidents: 60% effectiveness (attribution unclear, effects often temporary)
      if (runif(1) < 0.60) {
        # Cyber events increase crisis
        state$scenario_state$crisis_level <-
          min(10, state$scenario_state$crisis_level + 0.2 * severity)
        # Infrastructure/military cyber attacks shift balance
        if (grepl("defender", event$impact_type)) {
          # Attacks on defender degrade their capability
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance - 0.03 * severity))
        } else if (grepl("major", event$impact_type) || grepl("financial", event$impact_type)) {
          # Attacks on aggressor degrade their capability
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance + 0.03 * severity))
        }
        # Cyber defense upgrades benefit defender
        if (grepl("defense_upgrade", event$impact_type)) {
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance + 0.02 * severity))
          state$scenario_state$crisis_level <-
            max(0, state$scenario_state$crisis_level - 0.1 * severity)
        }
      }

    } else if (event$type == "information") {
      # Information warfare: 50% effectiveness (soft power, hard to quantify)
      if (runif(1) < 0.50) {
        # Narrative battles primarily affect international support
        if (grepl("victory_defender|opinion_defender|defense_success|failure_major", event$impact_type)) {
          state$scenario_state$international_support <-
            min(1.0, state$scenario_state$international_support + 0.05 * severity)
        } else if (grepl("victory_major", event$impact_type)) {
          state$scenario_state$international_support <-
            max(0, state$scenario_state$international_support - 0.05 * severity)
        }
        # Disinformation and leaks increase crisis
        if (grepl("warfare_active|leak|polarization", event$impact_type)) {
          state$scenario_state$crisis_level <-
            min(10, state$scenario_state$crisis_level + 0.2 * severity)
        }
        # Domestic opinion shifts can reduce crisis (war-weariness)
        if (grepl("domestic_opinion", event$impact_type)) {
          state$scenario_state$crisis_level <-
            max(0, state$scenario_state$crisis_level - 0.2 * severity)
        }
      }

    } else if (event$type == "economic") {
      # Economic events from generate_economic_event(): 65% effectiveness
      if (runif(1) < 0.65) {
        if (grepl("sanctions_increase", event$impact_type)) {
          state$scenario_state$sanctions_level <-
            min(1.0, state$scenario_state$sanctions_level + runif(1, 0.05, 0.10) * severity)
        } else if (grepl("sanctions_decrease", event$impact_type)) {
          state$scenario_state$sanctions_level <-
            max(0, state$scenario_state$sanctions_level - runif(1, 0.03, 0.07) * severity)
        } else if (grepl("commodity_surge", event$impact_type)) {
          state$scenario_state$crisis_level <-
            min(10, state$scenario_state$crisis_level + 0.3 * severity)
        } else if (grepl("commodity_decline", event$impact_type)) {
          state$scenario_state$crisis_level <-
            max(0, state$scenario_state$crisis_level - 0.2 * severity)
        } else if (grepl("gdp_decline", event$impact_type)) {
          # Aggressor GDP decline reduces their ability to sustain conflict
          state$scenario_state$crisis_level <-
            max(0, state$scenario_state$crisis_level - 0.2 * severity)
        }
        # gdp_stable_small has no direct state effect (already reflected in narrative)
      }
    }
  }

  # Apply action effects to state
  if (!is.null(state$action_results[[period]])) {
    for (faction in names(state$action_results[[period]])) {
      result <- state$action_results[[period]][[faction]]

      # Apply effects from action results
      if (!is.null(result$effects)) {
        effects <- result$effects

        # ECONOMIC EFFECTS - GDP damage to target
        if (!is.null(effects$target_gdp_impact)) {
          if (faction == "major_power") {
            state$faction_capabilities$small_power_gdp <-
              state$faction_capabilities$small_power_gdp * (1 + effects$target_gdp_impact)
          } else {
            state$faction_capabilities$major_power_gdp <-
              state$faction_capabilities$major_power_gdp * (1 + effects$target_gdp_impact)
          }
        }

        # ECONOMIC EFFECTS - Action costs deducted from actor GDP
        if (!is.null(effects$cost_billions)) {
          if (faction == "major_power") {
            state$faction_capabilities$major_power_gdp <-
              max(10, state$faction_capabilities$major_power_gdp - effects$cost_billions)
          } else if (faction == "small_power") {
            state$faction_capabilities$small_power_gdp <-
              max(5, state$faction_capabilities$small_power_gdp - effects$cost_billions)
          }
          # External actors have unlimited budgets for now
        }

        # Legacy actor_cost field (keep for backwards compatibility)
        if (!is.null(effects$actor_cost)) {
          if (faction == "major_power") {
            state$faction_capabilities$major_power_gdp <-
              max(10, state$faction_capabilities$major_power_gdp - effects$actor_cost)
          } else if (faction == "small_power") {
            state$faction_capabilities$small_power_gdp <-
              max(5, state$faction_capabilities$small_power_gdp - effects$actor_cost)
          }
        }

        # INTERNATIONAL SUPPORT - accumulate positive/negative effects
        if (!is.null(effects$international_support)) {
          state$scenario_state$international_support <-
            max(0, min(1, state$scenario_state$international_support + effects$international_support))
        }

        # INTERNATIONAL CONDEMNATION - reduces support
        if (!is.null(effects$international_condemnation)) {
          state$scenario_state$international_support <-
            max(0, state$scenario_state$international_support - effects$international_condemnation)
        }

        # SANCTIONS EFFECTS
        # Note: For multi-action factions, sanctions are applied via direct state mutation
        # inside execute_action() (state is threaded through sequential calls).
        # For single-action factions, sanctions are applied via direct state mutation
        # in the returned state. No additional application needed here.
        # Removed to prevent double-counting (Feb 2026 fix).

        # TRUST DAMAGE - affects future diplomatic options (stored for reference)
        if (!is.null(effects$trust_damage)) {
          if (is.null(state$accumulated_trust_damage)) {
            state$accumulated_trust_damage <- 0
          }
          state$accumulated_trust_damage <- state$accumulated_trust_damage + abs(effects$trust_damage)
        }

        # Check for simulation-ending events
        if (!is.null(effects$nuclear_war) && effects$nuclear_war) {
          state$simulation_ended <- TRUE
          state$end_reason <- "nuclear_war"
          cat("\n*** SIMULATION ENDED: NUCLEAR WAR ***\n")
        }
      }
    }
  }

  # ECONOMIC SUSTAINABILITY CHECK - war costs affect military capability
  # If GDP drops too low, military capability degrades
  if (state$faction_capabilities$major_power_gdp < 50) {
    # Major power struggling economically - 2% military degradation per period
    state$faction_capabilities$major_power_military <-
      state$faction_capabilities$major_power_military * 0.98
    cat("  [WARNING] Major power economy strained - military sustainment affected\n")
  }
  if (state$faction_capabilities$small_power_gdp < 15) {
    # Small power in economic crisis
    state$faction_capabilities$small_power_military <-
      state$faction_capabilities$small_power_military * 0.97
    cat("  [WARNING] Small power economy critical - military sustainment affected\n")
  }

  # Save agent states
  # Note: save_all_agent_states expects data_dir not output_dir
  save_all_agent_states(state$agents, period, data_dir)

  # Step 6: Aggregator assessment
  cat("\n6. Running aggregator assessment...\n")
  previous_assessment <- if (period > 1) {
    state$assessments_history[[period - 1]]
  } else {
    NULL
  }

  # Get previous state for delta calculation (v3.3)
  previous_state <- if (period > 1 && length(state$state_history) >= period - 1) {
    state$state_history[[period - 1]]$scenario_state
  } else {
    NULL
  }

  # Get this period's action results (v3.3)
  period_action_results <- if (length(state$action_results) >= period) {
    state$action_results[[period]]
  } else {
    NULL
  }

  # Build full history for aggregator (v3.3)
  full_history <- list(
    assessments_history = state$assessments_history,
    action_results = state$action_results,
    events_history = state$events_history,
    state_history = state$state_history
  )

  assessment <- run_aggregator_assessment(
    period,
    events,
    interaction_session,
    previous_assessment,
    state$scenario_state,
    api_key,
    action_results = period_action_results,
    previous_state = previous_state,
    full_history = full_history
  )

  # Save assessment
  state$assessments_history[[period]] <- assessment
  save_assessment(assessment, period, output_dir)

  # Update state tracking
  state$current_period <- period

  # Save state snapshot for period-by-period tracking
  state$state_history[[period]] <- list(
    period = period,
    timestamp = Sys.time(),
    scenario_state = state$scenario_state,
    faction_capabilities = state$faction_capabilities,
    peace_talks_count = if (!is.null(state$peace_talks_count)) state$peace_talks_count else 0,
    probability = assessment$probability,
    actions_taken = if (!is.null(state$action_results[[period]])) {
      sapply(state$action_results[[period]], function(r) r$action)
    } else {
      NULL
    }
  )

  return(state)
}

#' Initialize simulation with enhanced state tracking
#'
#' @param config Configuration object
#' @return Initial simulation state
initialize_simulation_with_actions <- function(config) {
  state <- initialize_simulation(config)

  # Add action tracking
  state$action_decisions <- list()
  state$action_results <- list()
  state$faction_capabilities <- list(
    major_power_military = 1.0,
    small_power_military = 0.6,
    major_power_gdp = 100.0,
    small_power_gdp = 30.0
  )

  # Add state history tracking for period-by-period analysis
  state$state_history <- list()
  state$peace_talks_count <- 0  # Track for diminishing returns

  return(state)
}

#' Run complete simulation with action execution
#'
#' @param n_periods Number of periods to simulate
#' @param api_key OpenRouter API key
#' @param output_dir Output directory
#' @param resume_from_period Period to resume from (optional)
#' @return Final simulation state
run_simulation_with_actions <- function(n_periods = N_PERIODS,
                                        api_key = OPENROUTER_API_KEY,
                                        output_dir = "outputs",
                                        resume_from_period = NULL) {

  data_dir <- "data"

  # Initialize or load state
  if (!is.null(resume_from_period)) {
    cat(sprintf("Resuming simulation from period %d...\n", resume_from_period))
    state <- load_simulation_state(output_dir)
    start_period <- resume_from_period
  } else {
    cat("Initializing new simulation with action execution...\n")
    config <- list(
      agents = AGENTS,
      n_periods = n_periods,
      external_events = EXTERNAL_EVENTS
    )
    state <- initialize_simulation_with_actions(config)
    start_period <- 1
  }

  cat(sprintf("\nSimulation ID: %s\n", state$simulation_id))
  cat(sprintf("Simulating %d periods (%d days total)\n",
              n_periods, n_periods * PERIOD_DURATION_DAYS))
  cat(sprintf("Number of agents: %d\n", length(state$agents)))
  cat("Enhanced features: Action Execution, Worldviews, Deception, Information Asymmetry\n")

  # Main simulation loop
  for (period in start_period:n_periods) {
    state <- run_simulation_period_with_actions(state, period, api_key, data_dir, output_dir)

    # Save state after each period
    save_simulation_state(state, output_dir)

    # Check for simulation-ending conditions
    if (!is.null(state$simulation_ended) && state$simulation_ended) {
      cat(sprintf("\n*** SIMULATION ENDED: %s ***\n", state$end_reason))
      break
    }

    # Check for early termination based on probability (symmetric thresholds)
    assessment <- state$assessments_history[[period]]
    if (!is.na(assessment$probability)) {
      if (assessment$probability > 0.95) {
        cat("\n*** Government collapse highly likely (>95%) - ending simulation ***\n")
        state$simulation_ended <- TRUE
        state$end_reason <- "collapse_imminent"
        break
      } else if (assessment$probability < 0.05) {
        cat("\n*** Government collapse highly unlikely (<5%) - ending simulation ***\n")
        state$simulation_ended <- TRUE
        state$end_reason <- "stability_achieved"
        break
      }
    }
  }

  state$end_time <- Sys.time()
  save_simulation_state(state, output_dir)

  cat("\n========== SIMULATION COMPLETE ==========\n")
  cat(sprintf("Total runtime: %.1f minutes\n",
              as.numeric(difftime(state$end_time, state$start_time, units = "mins"))))
  cat(sprintf("Periods simulated: %d\n", state$current_period))
  cat(sprintf("Total interactions: %d\n",
              sum(sapply(state$interactions_history, function(s) s$interaction_count))))
  cat(sprintf("Total actions executed: %d\n", length(state$action_results)))

  # Print action summary
  cat("\n--- ACTION SUMMARY ---\n")
  for (p in 1:length(state$action_results)) {
    if (!is.null(state$action_results[[p]])) {
      cat(sprintf("Period %d:\n", p))
      for (faction in names(state$action_results[[p]])) {
        result <- state$action_results[[p]][[faction]]
        cat(sprintf("  %s: %s - %s\n",
                   faction,
                   result$action,
                   if (result$success) "SUCCESS" else "FAILED"))
      }
    }
  }

  # Print final state
  cat("\n--- FINAL STATE ---\n")
  cat(sprintf("Crisis Level: %.1f/10\n", state$scenario_state$crisis_level))
  cat(sprintf("Military Balance: %.2f\n", state$scenario_state$military_balance))
  cat(sprintf("Sanctions Level: %.2f\n", state$scenario_state$sanctions_level))
  if (!is.null(state$faction_capabilities$major_power_military)) {
    cat(sprintf("Major Power Military: %.2f\n", state$faction_capabilities$major_power_military))
  }
  if (!is.null(state$faction_capabilities$small_power_military)) {
    cat(sprintf("Small Power Military: %.2f\n", state$faction_capabilities$small_power_military))
  }

  # Final assessment summary
  cat("\n--- FINAL ASSESSMENT ---\n")
  final_assessment <- state$assessments_history[[state$current_period]]
  if (!is.null(final_assessment)) {
    cat(sprintf("Probability of government collapse: %.1f%%\n",
                final_assessment$probability * 100))
    cat(sprintf("Confidence: %s\n", final_assessment$confidence))
    cat(sprintf("Trend: %s\n", final_assessment$trend))
    cat(sprintf("Key factors: %s\n", final_assessment$key_factors))
  }

  return(state)
}
