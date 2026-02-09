# Single-Period Collapse Test
# Tests: Given identical initial conditions, does the government collapse (yes/no)?
# Purpose: Measure simulation variance and identify decisive factors
#
# This is a SEPARATE analysis - does not modify the main simulation code

# Load dependencies
source("config.R")
source("src/agent_system.R")
source("src/enhanced_action_space.R")
source("src/integrated_agent_system.R")
source("src/action_execution.R")
source("src/event_generator.R")
source("src/interaction_engine.R")
source("src/agent_decision.R")
source("src/aggregator.R")

#' Run a single-period collapse test
#'
#' @param run_id Identifier for this run
#' @param initial_state Initial scenario state (fixed across runs)
#' @param agents List of agents (recreated each run for fresh state)
#' @param api_key OpenRouter API key
#' @param collapse_threshold Probability threshold for "collapse" (default 0.5)
#' @return List with run results
run_single_period_test <- function(run_id, initial_state, agent_configs, api_key,
                                    collapse_threshold = 0.5) {

  cat(sprintf("\n========== RUN %d ==========\n", run_id))

  # Create fresh agents for this run (important: agents have internal state)
  agents <- create_all_integrated_agents(list(AGENTS = agent_configs))

  # Initialize state for this run (copy to avoid mutation across runs)
  state <- list(
    scenario_state = initial_state$scenario_state,
    faction_capabilities = initial_state$faction_capabilities,
    events_history = list(),
    action_decisions = list(),
    action_results = list(),
    pre_action_coordination = list(),
    interactions_history = list(),
    aggregator_assessments = list()
  )

  period <- 1
  run_start <- Sys.time()

  # Step 1: Generate external events (stochastic element)
  cat("Step 1: Generating external events...\n")
  events <- generate_external_events(period, EXTERNAL_EVENTS)

  # Check for shock event
  shock <- generate_shock_event(period, state$scenario_state)
  if (!is.null(shock)) {
    events <- c(events, list(shock))
    cat(sprintf("  SHOCK EVENT: %s\n", shock$name))
  }

  state$events_history[[period]] <- events

  # Apply event effects to state
  for (event in events) {
    if (!is.null(event$impact_on_collapse)) {
      # Shock events directly affect collapse probability later
      cat(sprintf("  Event: %s (impact: %+.0f%%)\n",
                  event$name, event$impact_on_collapse * 100))
    }
    if (event$type == "battlefield") {
      # Battlefield events affect military balance
      if (!is.null(event$impact_type)) {
        if (event$impact_type == "defender_success") {
          state$scenario_state$military_balance <- min(1, state$scenario_state$military_balance + 0.1)
        } else if (event$impact_type == "aggressor_success") {
          state$scenario_state$military_balance <- max(-1, state$scenario_state$military_balance - 0.1)
        }
      }
    }
  }

  # Step 2: Run action decision phase (all 6 factions)
  cat("Step 2: Action decisions...\n")
  state <- run_action_decision_phase(agents, period, state, api_key)

  # Step 3: Run aggregator assessment
  cat("Step 3: Aggregator assessment...\n")

  # Build context for aggregator
  context <- list(
    period = period,
    scenario_state = state$scenario_state,
    recent_events = events,
    faction_capabilities = state$faction_capabilities,
    action_results = state$action_results[[period]]
  )

  # Get collapse probability from aggregator
  assessment <- run_aggregator_assessment(context, api_key)
  state$aggregator_assessments[[period]] <- assessment

  # Determine collapse outcome
  collapse_prob <- assessment$probability
  collapsed <- collapse_prob >= collapse_threshold

  run_end <- Sys.time()
  run_duration <- as.numeric(difftime(run_end, run_start, units = "secs"))

  # Compile results
  result <- list(
    run_id = run_id,
    timestamp = run_start,
    duration_seconds = run_duration,

    # Outcome
    collapse_probability = collapse_prob,
    collapsed = collapsed,

    # Events that occurred
    events = lapply(events, function(e) list(
      name = e$name,
      type = e$type,
      impact = if (!is.null(e$impact_on_collapse)) e$impact_on_collapse else NA
    )),
    shock_occurred = !is.null(shock),
    shock_name = if (!is.null(shock)) shock$name else NA,
    shock_impact = if (!is.null(shock)) shock$impact_on_collapse else NA,

    # Actions taken
    actions = lapply(names(state$action_results[[period]]), function(faction) {
      result <- state$action_results[[period]][[faction]]
      list(
        faction = faction,
        action = if (!is.null(result$action)) result$action else NA,
        success = if (!is.null(result$success)) result$success else NA
      )
    }),

    # Final state
    final_state = list(
      crisis_level = state$scenario_state$crisis_level,
      military_balance = state$scenario_state$military_balance,
      territory_controlled = state$scenario_state$territory_controlled,
      sanctions_level = state$scenario_state$sanctions_level
    ),

    # Aggregator reasoning
    aggregator_reasoning = assessment$reasoning
  )

  cat(sprintf("\nRUN %d RESULT: Collapse probability = %.1f%% → %s\n",
              run_id, collapse_prob * 100,
              if (collapsed) "COLLAPSED" else "SURVIVED"))

  return(result)
}


#' Run multiple single-period tests with identical initial conditions
#'
#' @param n_runs Number of runs to perform
#' @param scenario_preset Scenario preset name (from config.R)
#' @param collapse_threshold Probability threshold for collapse determination
#' @param output_file Path to save results CSV
#' @return Data frame with all run results
run_collapse_test_battery <- function(n_runs = 10,
                                       scenario_preset = "medium_intensity",
                                       collapse_threshold = 0.5,
                                       output_file = "outputs/collapse_test_results.csv") {

  cat("==============================================\n")
  cat("SINGLE-PERIOD COLLAPSE TEST BATTERY\n")
  cat("==============================================\n")
  cat(sprintf("Runs: %d\n", n_runs))
  cat(sprintf("Scenario: %s\n", scenario_preset))
  cat(sprintf("Collapse threshold: %.0f%%\n", collapse_threshold * 100))
  cat("==============================================\n\n")

  # Get API key
  api_key <- Sys.getenv("OPENROUTER_API_KEY")
  if (api_key == "") {
    stop("OPENROUTER_API_KEY not set. Please set it in your environment.")
  }

  # Initialize identical starting conditions
  preset <- SCENARIO_PRESETS[[scenario_preset]]
  if (is.null(preset)) {
    stop(sprintf("Unknown scenario preset: %s", scenario_preset))
  }

  # Extract values from preset (handle vector fields)
  territory_val <- if (length(preset$territory_controlled) == 2) {
    mean(preset$territory_controlled)
  } else {
    preset$territory_controlled
  }

  military_bal <- if (length(preset$military_balance) == 2) {
    mean(preset$military_balance)
  } else {
    preset$military_balance
  }

  initial_state <- list(
    scenario_state = list(
      crisis_level = preset$crisis_level,
      military_balance = military_bal,
      territory_controlled = territory_val,
      sanctions_level = if (!is.null(preset$sanctions_level)) preset$sanctions_level else 0.3,
      nuclear_used = FALSE
    ),
    faction_capabilities = list(
      major_power_military = 1.0,
      small_power_military = 0.6,
      major_power_gdp = 100,  # Default values
      small_power_gdp = 30
    )
  )

  cat("INITIAL CONDITIONS (identical for all runs):\n")
  cat(sprintf("  Crisis Level: %.1f/10\n", initial_state$scenario_state$crisis_level))
  cat(sprintf("  Military Balance: %.2f (negative = favors aggressor)\n", initial_state$scenario_state$military_balance))
  cat(sprintf("  Territory Controlled by Aggressor: %.1f%%\n", initial_state$scenario_state$territory_controlled * 100))
  cat(sprintf("  Sanctions Level: %.1f%%\n", initial_state$scenario_state$sanctions_level * 100))
  cat(sprintf("  Major Power Military: %.1f\n", initial_state$faction_capabilities$major_power_military))
  cat(sprintf("  Small Power Military: %.1f\n", initial_state$faction_capabilities$small_power_military))
  cat("\n")

  # Store agent configs (not agents themselves - those are recreated each run)
  agent_configs <- AGENTS

  # Run tests
  results <- list()
  battery_start <- Sys.time()

  for (i in 1:n_runs) {
    result <- tryCatch({
      run_single_period_test(i, initial_state, agent_configs, api_key, collapse_threshold)
    }, error = function(e) {
      cat(sprintf("\nERROR in run %d: %s\n", i, e$message))
      list(
        run_id = i,
        error = TRUE,
        error_message = e$message,
        collapsed = NA,
        collapse_probability = NA
      )
    })

    results[[i]] <- result

    # Brief pause between runs to avoid rate limiting
    if (i < n_runs) {
      Sys.sleep(2)
    }
  }

  battery_end <- Sys.time()
  total_duration <- as.numeric(difftime(battery_end, battery_start, units = "mins"))

  # Compile summary statistics
  valid_results <- Filter(function(r) is.null(r$error) || !r$error, results)
  n_valid <- length(valid_results)

  if (n_valid == 0) {
    cat("\nNo valid results to analyze.\n")
    return(NULL)
  }

  collapse_probs <- sapply(valid_results, function(r) r$collapse_probability)
  collapsed_count <- sum(sapply(valid_results, function(r) r$collapsed))
  shock_count <- sum(sapply(valid_results, function(r) r$shock_occurred))

  cat("\n==============================================\n")
  cat("SUMMARY STATISTICS\n")
  cat("==============================================\n")
  cat(sprintf("Valid runs: %d / %d\n", n_valid, n_runs))
  cat(sprintf("Total time: %.1f minutes\n", total_duration))
  cat(sprintf("\nCollapse probability distribution:\n"))
  cat(sprintf("  Mean: %.1f%%\n", mean(collapse_probs) * 100))
  cat(sprintf("  Std Dev: %.1f%%\n", sd(collapse_probs) * 100))
  cat(sprintf("  Min: %.1f%%\n", min(collapse_probs) * 100))
  cat(sprintf("  Max: %.1f%%\n", max(collapse_probs) * 100))
  cat(sprintf("\nBinary outcome (threshold = %.0f%%):\n", collapse_threshold * 100))
  cat(sprintf("  Collapsed: %d (%.1f%%)\n", collapsed_count, collapsed_count / n_valid * 100))
  cat(sprintf("  Survived: %d (%.1f%%)\n", n_valid - collapsed_count, (n_valid - collapsed_count) / n_valid * 100))
  cat(sprintf("\nShock events occurred in: %d runs (%.1f%%)\n",
              shock_count, shock_count / n_valid * 100))

  # Create results dataframe
  results_df <- data.frame(
    run_id = sapply(valid_results, function(r) r$run_id),
    collapse_probability = collapse_probs,
    collapsed = sapply(valid_results, function(r) r$collapsed),
    shock_occurred = sapply(valid_results, function(r) r$shock_occurred),
    shock_name = sapply(valid_results, function(r) if (is.na(r$shock_name)) "" else r$shock_name),
    shock_impact = sapply(valid_results, function(r) if (is.na(r$shock_impact)) 0 else r$shock_impact),
    final_crisis = sapply(valid_results, function(r) r$final_state$crisis_level),
    final_military_balance = sapply(valid_results, function(r) r$final_state$military_balance),
    final_territory = sapply(valid_results, function(r) r$final_state$territory_controlled),
    duration_seconds = sapply(valid_results, function(r) r$duration_seconds),
    stringsAsFactors = FALSE
  )

  # Save results
  dir.create("outputs", showWarnings = FALSE)
  write.csv(results_df, output_file, row.names = FALSE)
  cat(sprintf("\nResults saved to: %s\n", output_file))

  # Save full results as RDS for detailed analysis
  rds_file <- sub("\\.csv$", ".rds", output_file)
  saveRDS(results, rds_file)
  cat(sprintf("Full results saved to: %s\n", rds_file))

  return(results_df)
}


#' Analyze collapse test results
#'
#' @param results_file Path to results CSV or RDS
#' @return Analysis summary
analyze_collapse_results <- function(results_file) {
  if (grepl("\\.rds$", results_file)) {
    results <- readRDS(results_file)
    results_df <- data.frame(
      run_id = sapply(results, function(r) r$run_id),
      collapse_probability = sapply(results, function(r) r$collapse_probability),
      collapsed = sapply(results, function(r) r$collapsed),
      shock_occurred = sapply(results, function(r) r$shock_occurred),
      shock_impact = sapply(results, function(r) if (is.na(r$shock_impact)) 0 else r$shock_impact)
    )
  } else {
    results_df <- read.csv(results_file)
  }

  cat("\n=== COLLAPSE TEST ANALYSIS ===\n\n")

  # Overall statistics
  cat("1. OUTCOME DISTRIBUTION\n")
  cat(sprintf("   Total runs: %d\n", nrow(results_df)))
  cat(sprintf("   Collapse rate: %.1f%%\n", mean(results_df$collapsed) * 100))
  cat(sprintf("   Mean probability: %.1f%% (SD: %.1f%%)\n",
              mean(results_df$collapse_probability) * 100,
              sd(results_df$collapse_probability) * 100))

  # Effect of shock events
  cat("\n2. SHOCK EVENT EFFECT\n")
  with_shock <- results_df[results_df$shock_occurred, ]
  without_shock <- results_df[!results_df$shock_occurred, ]

  if (nrow(with_shock) > 0 && nrow(without_shock) > 0) {
    cat(sprintf("   With shock (%d runs): Mean prob = %.1f%%\n",
                nrow(with_shock), mean(with_shock$collapse_probability) * 100))
    cat(sprintf("   Without shock (%d runs): Mean prob = %.1f%%\n",
                nrow(without_shock), mean(without_shock$collapse_probability) * 100))
    cat(sprintf("   Difference: %+.1f percentage points\n",
                (mean(with_shock$collapse_probability) - mean(without_shock$collapse_probability)) * 100))
  }

  # Variance analysis
  cat("\n3. VARIANCE ANALYSIS\n")
  cat(sprintf("   Coefficient of variation: %.2f\n",
              sd(results_df$collapse_probability) / mean(results_df$collapse_probability)))
  cat(sprintf("   Range: %.1f%% to %.1f%%\n",
              min(results_df$collapse_probability) * 100,
              max(results_df$collapse_probability) * 100))

  # Consistency check
  cat("\n4. CONSISTENCY CHECK\n")
  if (sd(results_df$collapse_probability) < 0.05) {
    cat("   LOW VARIANCE: Simulation produces consistent outcomes\n")
  } else if (sd(results_df$collapse_probability) < 0.15) {
    cat("   MODERATE VARIANCE: Some stochasticity but generally consistent\n")
  } else {
    cat("   HIGH VARIANCE: Outcomes highly dependent on random factors\n")
  }

  return(invisible(results_df))
}


# Main execution
if (interactive()) {
  cat("Single-Period Collapse Test loaded.\n")
  cat("\nUsage:\n")
  cat("  results <- run_collapse_test_battery(n_runs = 10)\n")
  cat("  analyze_collapse_results('outputs/collapse_test_results.csv')\n")
  cat("\nOptions:\n")
  cat("  n_runs: Number of identical runs (default 10)\n")
  cat("  scenario_preset: 'low_intensity', 'medium_intensity', 'high_intensity', 'stalemate'\n")
  cat("  collapse_threshold: Probability cutoff for 'collapsed' determination (default 0.5)\n")
} else {
  # If run as script, execute with defaults
  results <- run_collapse_test_battery(n_runs = 10)
}
