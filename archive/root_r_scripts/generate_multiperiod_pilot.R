# Multi-Period Pilot for Temporal PID Analysis
# =============================================
#
# Runs a small number of scenarios for multiple periods to test temporal
# emergence — whether agents adapt to each other's actions over time.
#
# Unlike single-period generation, post-action discussions are ENABLED
# because they feed into the next period's context.
#
# Usage:
#   Rscript generate_multiperiod_pilot.R [n_scenarios] [n_periods]
#   Default: 10 scenarios × 5 periods
#
# Output:
#   outputs/multiperiod_pilot/

library(jsonlite)
library(uuid)

# Load configuration and simulation code
source("config.R")
source("src/integrated_agent_system.R")
source("src/agent_system.R")
source("src/event_generator.R")
source("src/interaction_engine.R")
source("src/aggregator.R")
source("src/state_manager.R")
source("src/agent_decision.R")
source("src/action_execution.R")
source("src/multi_action_system.R")
source("src/multi_action_effects.R")
source("src/simulation_with_actions.R")

# Source generation functions
source_env <- new.env(parent = globalenv())
exprs <- parse("generate_multiscenario_dataset.R")
for (expr in exprs) {
  expr_text <- deparse(expr)
  if (any(grepl("<-\\s*function", expr_text)) || any(grepl("^library\\(", expr_text))) {
    eval(expr, envir = source_env)
  }
}
for (fn_name in c("generate_scenario_parameters", "extract_ground_truth_from_state",
                   "map_scenario_to_preset", "get_preset_context")) {
  if (exists(fn_name, envir = source_env)) {
    assign(fn_name, get(fn_name, envir = source_env), envir = globalenv())
  }
}

cat(rep("=", 70), "\n", sep = "")
cat("MULTI-PERIOD PILOT (Temporal PID)\n")
cat(rep("=", 70), "\n\n", sep = "")

main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  n_scenarios <- if (length(args) >= 1) as.integer(args[1]) else 10
  n_periods <- if (length(args) >= 2) as.integer(args[2]) else 5

  api_key <- Sys.getenv("OPENROUTER_API_KEY")
  if (api_key == "") stop("OPENROUTER_API_KEY environment variable not set")

  output_dir <- "outputs/multiperiod_pilot"
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(file.path(output_dir, "temp"), recursive = TRUE, showWarnings = FALSE)

  cat(sprintf("Output directory: %s\n", output_dir))
  cat(sprintf("Scenarios: %d × %d periods = %d total periods\n\n",
              n_scenarios, n_periods, n_scenarios * n_periods))

  # Generate scenario parameters — pick diverse scenarios across presets
  all_scenarios <- generate_scenario_parameters(n_scenarios = n_scenarios, seed = 123)

  # Save scenario parameters
  write.csv(all_scenarios, file.path(output_dir, "scenarios.csv"), row.names = FALSE)

  # Create agents
  cat("Creating enhanced cognitive agents...\n")
  enhanced_agents <- create_all_integrated_agents(
    config = list(AGENTS = AGENTS),
    country_mapping = list(major_power = "Novaris", small_power = "Tethys", external = "External")
  )

  # Check for already-completed scenarios (resume support)
  completed_scenarios <- c()
  for (i in 1:nrow(all_scenarios)) {
    state_file <- file.path(output_dir, sprintf("scenario_%03d.rds", i))
    if (file.exists(state_file)) {
      saved <- readRDS(state_file)
      if (!is.null(saved$current_period) && saved$current_period >= n_periods) {
        completed_scenarios <- c(completed_scenarios, i)
      }
    }
  }

  cat("\n", rep("=", 70), "\n")
  cat(sprintf("RUNNING %d-PERIOD SIMULATIONS\n", n_periods))
  cat(rep("=", 70), "\n")

  if (length(completed_scenarios) > 0) {
    cat(sprintf("\n[RESUME] Found %d completed scenarios, skipping them.\n",
                length(completed_scenarios)))
  }

  all_ground_truth <- list()
  successful_count <- length(completed_scenarios)
  failed_count <- 0
  start_time <- Sys.time()

  for (i in 1:nrow(all_scenarios)) {
    if (i > n_scenarios) break
    if (i %in% completed_scenarios) next

    scenario_row <- all_scenarios[i, ]
    scenario_id <- scenario_row$scenario_id

    cat(sprintf("\n%s\n", paste(rep("=", 60), collapse = "")))
    cat(sprintf("SCENARIO %d/%d: %s [%s]\n", i, n_scenarios, scenario_id, scenario_row$preset))
    cat(sprintf("  Territory: %.1f%% | Balance: %+.2f | Sanctions: %.1f%% | Support: %.1f%% | Crisis: %d\n",
                scenario_row$territory_controlled * 100,
                scenario_row$military_balance,
                scenario_row$sanctions_level * 100,
                scenario_row$international_support * 100,
                scenario_row$crisis_level))
    cat(sprintf("%s\n", paste(rep("=", 60), collapse = "")))

    # Map to preset
    preset_name <- map_scenario_to_preset(scenario_row)
    preset_ctx <- get_preset_context(preset_name, scenario_row)

    # Initialize state
    state <- list(
      simulation_id = scenario_id,
      start_time = Sys.time(),
      current_period = 0,
      scenario_preset = preset_name,
      agents = enhanced_agents,
      events_history = list(),
      interactions_history = list(),
      assessments_history = list(),
      state_history = list(),
      scenario_state = list(
        current_day = 0,
        situation_summary = preset_ctx$situation_summary,
        recent_events = preset_ctx$recent_events,
        military_balance = scenario_row$military_balance,
        sanctions_level = scenario_row$sanctions_level,
        international_support = scenario_row$international_support,
        crisis_level = scenario_row$crisis_level,
        territory_controlled = scenario_row$territory_controlled,
        nuclear_used = FALSE,
        momentum = scenario_row$momentum,
        consecutive_wins_defender = 0,
        consecutive_wins_aggressor = ifelse(scenario_row$territory_controlled > 0.1, 1, 0)
      ),
      faction_capabilities = list(
        major_power_military = 1.0,
        small_power_military = 0.6,
        major_power_gdp = scenario_row$novaris_gdp,
        small_power_gdp = scenario_row$tethys_gdp
      ),
      action_decisions = list(),
      action_results = list(),
      pre_action_coordination = list()
    )
    class(state) <- c("simulation_state", "list")

    scenario_dir <- file.path(output_dir, sprintf("scenario_%03d", i))
    dir.create(scenario_dir, recursive = TRUE, showWarnings = FALSE)

    scenario_failed <- FALSE

    # Run multiple periods
    for (period in 1:n_periods) {
      cat(sprintf("\n  --- Period %d/%d ---\n", period, n_periods))

      result <- tryCatch({
        final_state <- run_simulation_period_with_actions(
          state = state,
          period = period,
          api_key = api_key,
          data_dir = "data",
          output_dir = file.path(output_dir, "temp")
        )

        # Copy this period's interaction CSVs to scenario directory
        period_prefix <- sprintf("period_%02d", period)
        interaction_files <- list.files("outputs/interactions",
                                        pattern = paste0("^", period_prefix, "_"),
                                        full.names = TRUE)
        if (length(interaction_files) > 0) {
          file.copy(interaction_files, scenario_dir, overwrite = TRUE)
        }

        # Copy assessment
        assessment_file <- file.path(output_dir, "temp", "assessments.csv")
        if (file.exists(assessment_file)) {
          file.copy(assessment_file,
                    file.path(scenario_dir, sprintf("period_%02d_assessments.csv", period)),
                    overwrite = TRUE)
        }

        # Extract period ground truth
        if (!is.null(final_state$assessments_history[[period]])) {
          prob <- final_state$assessments_history[[period]]$probability
          cat(sprintf("  Collapse probability: %.3f\n", prob))
        }

        list(success = TRUE, state = final_state)
      }, error = function(e) {
        cat(sprintf("  ✗ Period %d failed: %s\n", period, e$message))
        list(success = FALSE, error = e$message)
      })

      if (!result$success) {
        scenario_failed <- TRUE
        failed_count <- failed_count + 1
        break
      }

      state <- result$state
    }

    if (!scenario_failed) {
      successful_count <- successful_count + 1

      # Save full state
      saveRDS(state, file.path(output_dir, sprintf("scenario_%03d.rds", i)))

      # Extract ground truth per period
      for (period in 1:n_periods) {
        if (!is.null(state$assessments_history[[period]])) {
          prob <- state$assessments_history[[period]]$probability

          novaris_actions <- c()
          tethys_actions <- c()
          if (!is.null(state$action_decisions[[period]])) {
            if (!is.null(state$action_decisions[[period]]$major_power$approved_actions)) {
              novaris_actions <- sapply(state$action_decisions[[period]]$major_power$approved_actions,
                                       function(a) a$action)
            }
            if (!is.null(state$action_decisions[[period]]$small_power$approved_actions)) {
              tethys_actions <- sapply(state$action_decisions[[period]]$small_power$approved_actions,
                                      function(a) a$action)
            }
          }

          all_ground_truth[[length(all_ground_truth) + 1]] <- list(
            scenario_id = scenario_id,
            period = period,
            collapse_probability = prob,
            novaris_actions = paste(novaris_actions, collapse = "|"),
            tethys_actions = paste(tethys_actions, collapse = "|"),
            n_novaris_actions = length(novaris_actions),
            n_tethys_actions = length(tethys_actions),
            territory = state$state_history[[period]]$scenario_state$territory_controlled,
            military_balance = state$state_history[[period]]$scenario_state$military_balance,
            crisis_level = state$state_history[[period]]$scenario_state$crisis_level,
            sanctions_level = state$state_history[[period]]$scenario_state$sanctions_level,
            support = state$state_history[[period]]$scenario_state$international_support
          )
        }
      }

      elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "mins"))
      cat(sprintf("\n  ✓ Scenario complete (%.1f min elapsed)\n", elapsed))
    }

    # Save ground truth incrementally
    if (length(all_ground_truth) > 0) {
      gt_df <- do.call(rbind, lapply(all_ground_truth, as.data.frame,
                                      stringsAsFactors = FALSE))
      write.csv(gt_df, file.path(output_dir, "ground_truth.csv"), row.names = FALSE)
    }
  }

  # Final summary
  total_time <- as.numeric(difftime(Sys.time(), start_time, units = "mins"))
  cat("\n", rep("=", 70), "\n")
  cat("MULTI-PERIOD PILOT COMPLETE\n")
  cat(rep("=", 70), "\n")
  cat(sprintf("Scenarios: %d (%d successful, %d failed)\n",
              n_scenarios, successful_count, failed_count))
  cat(sprintf("Periods per scenario: %d\n", n_periods))
  cat(sprintf("Total time: %.1f minutes\n", total_time))
  cat(sprintf("Output: %s\n", output_dir))
  cat(rep("=", 70), "\n")
}

if (!interactive()) {
  main()
}
