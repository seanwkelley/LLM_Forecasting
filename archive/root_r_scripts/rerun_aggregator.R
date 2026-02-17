#!/usr/bin/env Rscript
#' Re-run aggregator assessments on completed scenarios with updated prompt.
#'
#' This script loads saved scenario states (.rds files), re-runs the aggregator
#' with the updated prompt (continuous probabilities, full 0-1 range), and
#' updates ground_truth.csv.
#'
#' Usage:
#'   Rscript rerun_aggregator.R                   # Re-run all completed scenarios
#'   Rscript rerun_aggregator.R --scenarios 1-10   # Re-run specific range

# Load dependencies
library(httr)
library(jsonlite)

# Source all required modules
source("config.R")
source("src/agent_system.R")  # contains call_llm()
source("src/aggregator.R")

# Parse command line args
args <- commandArgs(trailingOnly = TRUE)
scenario_range <- NULL
if (length(args) >= 2 && args[1] == "--scenarios") {
  range_parts <- strsplit(args[2], "-")[[1]]
  scenario_range <- seq(as.integer(range_parts[1]), as.integer(range_parts[2]))
}

# Setup
output_dir <- "outputs/multiscenario"
api_key <- Sys.getenv("OPENROUTER_API_KEY")
if (api_key == "") {
  stop("OPENROUTER_API_KEY environment variable not set")
}

cat("======================================================================\n")
cat("RE-RUNNING AGGREGATOR WITH CONTINUOUS PROBABILITIES\n")
cat("======================================================================\n\n")

# Find completed scenarios
rds_files <- list.files(output_dir, pattern = "^scenario_\\d{3}\\.rds$", full.names = TRUE)
rds_files <- sort(rds_files)

if (length(rds_files) == 0) {
  stop("No completed scenario .rds files found in ", output_dir)
}

cat(sprintf("Found %d completed scenarios\n", length(rds_files)))

# Filter to requested range if specified
if (!is.null(scenario_range)) {
  rds_files <- rds_files[scenario_range[scenario_range <= length(rds_files)]]
  cat(sprintf("Filtering to scenarios %d-%d (%d files)\n",
              min(scenario_range), max(scenario_range), length(rds_files)))
}

# Re-run aggregator on each scenario
results <- list()
old_probs <- c()
new_probs <- c()

for (rds_file in rds_files) {
  scenario_id <- gsub(".*scenario_(\\d{3})\\.rds", "\\1", rds_file)
  cat(sprintf("\n--- Scenario %s ---\n", scenario_id))

  # Load saved state
  state <- readRDS(rds_file)

  # Get old probability
  old_prob <- if (!is.null(state$aggregator_assessments) && length(state$aggregator_assessments) > 0) {
    state$aggregator_assessments[[1]]$probability
  } else {
    NA
  }
  old_probs <- c(old_probs, old_prob)
  cat(sprintf("  Old probability: %.3f\n", old_prob))

  # Re-build context from saved state
  context <- prepare_aggregator_context(
    period = 1,
    events = if (!is.null(state$events_history) && length(state$events_history) > 0) state$events_history[[1]] else list(),
    interactions = if (!is.null(state$interaction_history) && length(state$interaction_history) > 0) state$interaction_history[[1]]$interactions else list(),
    previous_assessment = NULL,
    scenario_state = state$scenario_state,
    action_results = if (!is.null(state$action_results_history) && length(state$action_results_history) > 0) state$action_results_history[[1]] else list(),
    previous_state = NULL,
    full_history = NULL
  )

  # Re-run aggregator with updated prompt
  new_assessment <- assess_collapse_probability(context, api_key)
  new_assessment$period <- 1

  new_prob <- new_assessment$probability
  new_probs <- c(new_probs, new_prob)
  cat(sprintf("  New probability: %.3f (was %.3f, diff: %+.3f)\n",
              new_prob, old_prob, new_prob - old_prob))

  # Update the state with new assessment
  state$aggregator_assessments[[1]] <- new_assessment

  # Save updated state
  saveRDS(state, rds_file)

  results[[scenario_id]] <- list(
    scenario_id = sprintf("scenario_%s", scenario_id),
    old_probability = old_prob,
    new_probability = new_prob
  )

  # Small delay to avoid rate limiting
  Sys.sleep(1)
}

# Update ground_truth.csv
cat("\n======================================================================\n")
cat("UPDATING GROUND TRUTH\n")
cat("======================================================================\n\n")

ground_truth_file <- file.path(output_dir, "ground_truth.csv")
if (file.exists(ground_truth_file)) {
  gt <- read.csv(ground_truth_file, stringsAsFactors = FALSE)

  for (res in results) {
    idx <- which(gt$scenario_id == res$scenario_id)
    if (length(idx) > 0) {
      gt$collapse_probability[idx] <- res$new_probability
    }
  }

  write.csv(gt, ground_truth_file, row.names = FALSE)
  cat(sprintf("Updated %d entries in %s\n", length(results), ground_truth_file))
}

# Summary
cat("\n======================================================================\n")
cat("SUMMARY\n")
cat("======================================================================\n\n")

cat(sprintf("Scenarios re-assessed: %d\n", length(results)))
cat(sprintf("\nOld probabilities: min=%.3f, max=%.3f, mean=%.3f, unique=%d\n",
            min(old_probs, na.rm=TRUE), max(old_probs, na.rm=TRUE),
            mean(old_probs, na.rm=TRUE), length(unique(old_probs))))
cat(sprintf("New probabilities: min=%.3f, max=%.3f, mean=%.3f, unique=%d\n",
            min(new_probs, na.rm=TRUE), max(new_probs, na.rm=TRUE),
            mean(new_probs, na.rm=TRUE), length(unique(new_probs))))

cat("\nComparison:\n")
cat(sprintf("  %-12s  %8s  %8s  %8s\n", "Scenario", "Old", "New", "Diff"))
cat(paste(rep("-", 45), collapse=""), "\n")
for (res in results) {
  cat(sprintf("  %-12s  %8.3f  %8.3f  %+8.3f\n",
              res$scenario_id, res$old_probability, res$new_probability,
              res$new_probability - res$old_probability))
}

cat("\n[OK] Aggregator re-run complete!\n")
