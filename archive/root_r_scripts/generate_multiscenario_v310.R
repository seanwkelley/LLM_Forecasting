# Generate Multi-Scenario Dataset with v3.10 Domain Differentiation
# ==================================================================
#
# Regenerates scenarios using the v3.10 prompt changes:
#   - Domain-constrained action lists (each expert proposes from their domain)
#   - Domain-specific parameter emphasis (each expert focuses on relevant params)
#
# Outputs to outputs/multiscenario_v310/ to preserve original data for comparison.
# Uses same LHS parameters (seed=42) as original for direct comparison.
#
# Usage:
#   Rscript generate_multiscenario_v310.R [n_scenarios]
#   Default: 50 scenarios

library(jsonlite)
library(uuid)

# Skip post-action discussions for single-period generation (faster)
Sys.setenv(SKIP_POST_ACTION_DISCUSSIONS = "1")

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

# Source the generation functions from the original script
# (generate_scenario_parameters, run_single_scenario_simulation, extract_ground_truth_from_state
#  are defined in generate_multiscenario_dataset.R but we can't source it directly since it
#  calls main() when non-interactive. Redefine here.)

source_env <- new.env(parent = globalenv())
# Parse without executing
exprs <- parse("generate_multiscenario_dataset.R")
# Evaluate only function definitions (not the main() call at the bottom)
for (expr in exprs) {
  expr_text <- deparse(expr)
  # Only evaluate function assignments and library calls
  if (any(grepl("<-\\s*function", expr_text)) || any(grepl("^library\\(", expr_text))) {
    eval(expr, envir = source_env)
  }
}
# Copy functions to global env
for (fn_name in c("generate_scenario_parameters", "run_single_scenario_simulation", "extract_ground_truth_from_state", "map_scenario_to_preset", "get_preset_context")) {
  if (exists(fn_name, envir = source_env)) {
    assign(fn_name, get(fn_name, envir = source_env), envir = globalenv())
  }
}

cat(rep("=", 70), "\n", sep="")
cat("MULTI-SCENARIO DATASET GENERATION (v3.10 Domain Differentiation)\n")
cat(rep("=", 70), "\n\n", sep="")

main <- function() {
  # Parse command line args
  args <- commandArgs(trailingOnly = TRUE)
  n_scenarios <- if (length(args) >= 1) as.integer(args[1]) else 50

  # Check API key
  api_key <- Sys.getenv("OPENROUTER_API_KEY")
  if (api_key == "") {
    stop("OPENROUTER_API_KEY environment variable not set")
  }

  # Output to separate directory
  output_dir <- "outputs/multiscenario_v310"
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(file.path(output_dir, "temp"), recursive = TRUE, showWarnings = FALSE)

  cat(sprintf("Output directory: %s\n", output_dir))
  cat(sprintf("Scenarios to generate: %d\n\n", n_scenarios))

  # Generate scenario parameters (same seed as original for comparability)
  scenarios <- generate_scenario_parameters(n_scenarios = n_scenarios, seed = 42)

  # Save scenario parameters
  scenarios_file <- file.path(output_dir, "scenarios.csv")
  write.csv(scenarios, scenarios_file, row.names = FALSE)
  cat(sprintf("\nSaved scenario parameters: %s\n\n", scenarios_file))

  # Create enhanced agents
  cat("Creating enhanced cognitive agents...\n")
  enhanced_agents <- create_all_integrated_agents(
    config = list(AGENTS = AGENTS),
    country_mapping = list(
      major_power = "Novaris",
      small_power = "Tethys",
      external = "External"
    )
  )

  # Check for already-completed scenarios (resume support)
  completed_scenarios <- c()
  existing_ground_truth <- list()
  for (i in 1:nrow(scenarios)) {
    scenario_dir <- file.path(output_dir, sprintf("scenario_%03d", i))
    state_file <- file.path(output_dir, sprintf("scenario_%03d.rds", i))
    if (file.exists(state_file) && dir.exists(scenario_dir)) {
      interaction_files <- list.files(scenario_dir, pattern = "\\.csv$")
      if (length(interaction_files) >= 3) {
        completed_scenarios <- c(completed_scenarios, i)
        saved_state <- readRDS(state_file)

        collapse_prob <- NA
        if (!is.null(saved_state$aggregator_assessments) && length(saved_state$aggregator_assessments) > 0) {
          assessment <- saved_state$aggregator_assessments[[1]]
          if (!is.null(assessment$probability)) collapse_prob <- assessment$probability
        } else if (!is.null(saved_state$assessments_history) && length(saved_state$assessments_history) > 0) {
          assessment <- saved_state$assessments_history[[1]]
          if (!is.null(assessment$probability)) collapse_prob <- assessment$probability
        }

        novaris_actions <- character(0)
        tethys_actions <- character(0)
        if (!is.null(saved_state$action_decisions) && length(saved_state$action_decisions) > 0) {
          if (!is.null(saved_state$action_decisions[[1]]$major_power$approved_actions)) {
            novaris_actions <- sapply(saved_state$action_decisions[[1]]$major_power$approved_actions, function(a) a$action)
          }
          if (!is.null(saved_state$action_decisions[[1]]$small_power$approved_actions)) {
            tethys_actions <- sapply(saved_state$action_decisions[[1]]$small_power$approved_actions, function(a) a$action)
          }
        }

        existing_ground_truth[[i]] <- list(
          scenario_id = scenarios$scenario_id[i],
          period = 1,
          collapse_probability = collapse_prob,
          novaris_actions = novaris_actions,
          tethys_actions = tethys_actions,
          n_novaris_actions = length(novaris_actions),
          n_tethys_actions = length(tethys_actions),
          final_territory = saved_state$scenario_state$territory_controlled,
          final_military_balance = saved_state$scenario_state$military_balance,
          final_crisis_level = saved_state$scenario_state$crisis_level,
          final_sanctions = saved_state$scenario_state$sanctions_level,
          final_support = saved_state$scenario_state$international_support
        )
      }
    }
  }

  # Run simulations
  cat("\n", rep("=", 70), "\n")
  cat("RUNNING SIMULATIONS (v3.10 prompts)\n")
  cat(rep("=", 70), "\n")

  if (length(completed_scenarios) > 0) {
    cat(sprintf("\n[RESUME] Found %d already-completed scenarios, skipping them.\n", length(completed_scenarios)))
    cat(sprintf("[RESUME] Remaining: %d scenarios to run\n\n", n_scenarios - length(completed_scenarios)))
  }

  all_ground_truth <- existing_ground_truth
  successful_count <- length(completed_scenarios)
  failed_count <- 0
  start_time <- Sys.time()

  for (i in 1:nrow(scenarios)) {
    if (i > n_scenarios) break
    if (i %in% completed_scenarios) next

    scenario_row <- scenarios[i, ]

    # Clean temp directory
    temp_assessment <- file.path(output_dir, "temp", "assessments.csv")
    if (file.exists(temp_assessment)) file.remove(temp_assessment)

    result <- run_single_scenario_simulation(
      scenario_params = scenario_row,
      agents = enhanced_agents,
      api_key = api_key
    )

    if (result$success) {
      all_ground_truth[[i]] <- result$ground_truth
      successful_count <- successful_count + 1

      # Save detailed state
      state_file <- file.path(output_dir, sprintf("scenario_%03d.rds", i))
      saveRDS(result$state, state_file)

      # Copy interaction CSVs
      scenario_dir <- file.path(output_dir, sprintf("scenario_%03d", i))
      dir.create(scenario_dir, recursive = TRUE, showWarnings = FALSE)

      interaction_files <- list.files("outputs/interactions", pattern = "^period_01_", full.names = TRUE)
      if (length(interaction_files) > 0) {
        file.copy(interaction_files, scenario_dir, overwrite = TRUE)
      }

      assessment_file <- file.path(output_dir, "temp", "assessments.csv")
      if (file.exists(assessment_file)) {
        file.copy(assessment_file, scenario_dir, overwrite = TRUE)
      }

      elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "mins"))
      rate <- elapsed / (successful_count - length(completed_scenarios))
      remaining <- (n_scenarios - i) * rate
      cat(sprintf("  Saved to %s (%.1f min elapsed, ~%.0f min remaining)\n",
                  scenario_dir, elapsed, remaining))

    } else {
      failed_count <- failed_count + 1
      all_ground_truth[[i]] <- list(
        scenario_id = scenario_row$scenario_id,
        success = FALSE,
        error = result$error
      )
    }

    # Save ground truth incrementally
    ground_truth_df_partial <- do.call(rbind, lapply(all_ground_truth, function(gt) {
      if (is.null(gt) || is.null(gt$collapse_probability)) return(NULL)
      data.frame(
        scenario_id = gt$scenario_id,
        period = gt$period,
        collapse_probability = gt$collapse_probability,
        novaris_actions = paste(gt$novaris_actions, collapse = "|"),
        tethys_actions = paste(gt$tethys_actions, collapse = "|"),
        n_novaris_actions = gt$n_novaris_actions,
        n_tethys_actions = gt$n_tethys_actions,
        final_territory = gt$final_territory,
        final_military_balance = gt$final_military_balance,
        final_crisis_level = gt$final_crisis_level,
        final_sanctions = gt$final_sanctions,
        final_support = gt$final_support,
        stringsAsFactors = FALSE
      )
    }))
    ground_truth_file <- file.path(output_dir, "ground_truth.csv")
    write.csv(ground_truth_df_partial, ground_truth_file, row.names = FALSE)

    if (i %% 10 == 0) {
      cat(sprintf("\nProgress: %d/%d scenarios completed (%d successful, %d failed)\n\n",
                  i, n_scenarios, successful_count, failed_count))
    }
  }

  # Final summary
  total_time <- as.numeric(difftime(Sys.time(), start_time, units = "mins"))
  cat("\n", rep("=", 70), "\n")
  cat("DATASET GENERATION COMPLETE (v3.10)\n")
  cat(rep("=", 70), "\n")
  cat(sprintf("Scenarios generated: %d\n", n_scenarios))
  cat(sprintf("Simulations successful: %d\n", successful_count))
  cat(sprintf("Simulations failed: %d\n", failed_count))
  cat(sprintf("Total time: %.1f minutes (%.1f min/scenario)\n", total_time,
              total_time / max(1, successful_count - length(completed_scenarios))))
  cat(sprintf("\nOutput directory: %s\n", output_dir))
  cat(sprintf("\nTo run PID analysis on this data:\n"))
  cat(sprintf("  python forecasting/run_pid_emergence_analysis.py --data-dir %s --output-dir experiment_results/pid_analysis_v310\n", output_dir))
  cat(rep("=", 70), "\n")
}

if (!interactive()) {
  main()
}
