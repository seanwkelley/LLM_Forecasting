# Main simulation orchestrator

# Source all required modules
source("config.R")
source("src/agent_system.R")
source("src/event_generator.R")
source("src/interaction_engine.R")
source("src/aggregator.R")
source("src/state_manager.R")

#' Run a single period of the simulation
#'
#' @param state Simulation state object
#' @param period Period number
#' @param api_key OpenRouter API key
#' @param data_dir Data directory path
#' @param output_dir Output directory path
#' @return Updated simulation state
run_simulation_period <- function(state, period, api_key, data_dir, output_dir) {
  cat(sprintf("\n========== PERIOD %d (Day %d) ==========\n",
              period, period * PERIOD_DURATION_DAYS))

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

  # Generate potential shock event (high-impact, low-probability)
  shock_event <- generate_shock_event(period, state$scenario_state)
  if (!is.null(shock_event)) {
    events <- c(events, list(shock_event))
  }

  # Display events
  if (length(events) > 0) {
    cat(sprintf("   Generated %d events:\n", length(events)))
    for (event in events) {
      cat(sprintf("   - %s: %s\n", event$name, event$description))
    }
  } else {
    cat("   No major events this period.\n")
  }

  state$events_history[[period]] <- events

  # Step 2: Update scenario context for agents
  state$scenario_state$recent_events <- sapply(events, function(e) e$description)

  # Step 3: Run agent interactions
  cat("\n2. Running agent interactions...\n")
  session <- create_interaction_session(
    period,
    state$agents,
    state$scenario_state
  )

  session <- run_interaction_session(session, api_key)
  state$interactions_history[[period]] <- session

  # Step 4: Save interaction data
  if (SAVE_FULL_TRANSCRIPTS) {
    cat("\n3. Saving interaction data...\n")
    save_interaction_session(session, data_dir)
  }

  if (SAVE_NETWORK_DATA) {
    save_network_data(session$interactions, period, data_dir)
  }

  # Step 5: Run aggregator assessment
  cat("\n4. Running aggregator assessment...\n")
  previous_assessment <- if (period > 1) {
    state$assessments_history[[period - 1]]
  } else {
    NULL
  }

  assessment <- run_aggregator_assessment(
    period,
    events,
    session,
    previous_assessment,
    state$scenario_state,
    api_key
  )

  state$assessments_history[[period]] <- assessment

  # Step 6: Save assessment
  save_assessment(assessment, period, output_dir)

  # Step 7: Update scenario state based on events and assessment
  state <- update_scenario_state(state, period, events, assessment)

  # Step 8: Save agent states
  save_all_agent_states(state$agents, period, data_dir)

  # Step 9: Update current period
  state$current_period <- period

  cat(sprintf("\nPeriod %d complete. Current collapse probability: %.1f%%\n",
              period, assessment$probability * 100))

  return(state)
}

#' Run the full simulation
#'
#' @param n_periods Number of periods to simulate
#' @param api_key OpenRouter API key
#' @param output_dir Output directory path
#' @param resume_from_period If specified, resume from this period
#' @return Final simulation state
run_simulation <- function(n_periods = N_PERIODS,
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
    cat("Initializing new simulation...\n")
    config <- list(
      agents = AGENTS,
      n_periods = n_periods,
      external_events = EXTERNAL_EVENTS
    )
    state <- initialize_simulation(config)
    start_period <- 1
  }

  cat(sprintf("\nSimulation ID: %s\n", state$simulation_id))
  cat(sprintf("Simulating %d periods (%d days total)\n",
              n_periods, n_periods * PERIOD_DURATION_DAYS))
  cat(sprintf("Number of agents: %d\n", length(state$agents)))

  # Main simulation loop
  for (period in start_period:n_periods) {
    state <- run_simulation_period(state, period, api_key, data_dir, output_dir)

    # Save state after each period
    save_simulation_state(state, output_dir)

    # Check for early termination
    assessment <- state$assessments_history[[period]]
    if (!is.na(assessment$probability)) {
      if (assessment$probability > 0.9) {
        cat("\n*** Government collapse highly likely - ending simulation ***\n")
        break
      } else if (assessment$probability < 0.05) {
        cat("\n*** Government collapse highly unlikely - ending simulation ***\n")
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

  # Final assessment summary
  final_assessment <- state$assessments_history[[state$current_period]]
  cat(sprintf("\nFINAL ASSESSMENT:\n"))
  cat(sprintf("  Probability of government collapse: %.1f%%\n",
              final_assessment$probability * 100))
  cat(sprintf("  Confidence: %s\n", final_assessment$confidence))
  cat(sprintf("  Trend: %s\n", final_assessment$trend))

  return(state)
}

#' Quick start function with default settings
#'
#' @param n_periods Number of periods (default from config)
#' @export
start_simulation <- function(n_periods = N_PERIODS) {
  if (OPENROUTER_API_KEY == "") {
    stop("Please set OPENROUTER_API_KEY environment variable")
  }

  state <- run_simulation(n_periods = n_periods)
  return(state)
}
