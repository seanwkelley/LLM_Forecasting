#!/usr/bin/env Rscript
# Simple extraction from .rds files

extract_ground_truth_from_state <- function(state, scenario_id) {
  period <- 1

  # Extract collapse probability from aggregator assessment
  assessment <- state$assessments_history[[period]]
  collapse_prob <- if (!is.null(assessment$probability)) {
    assessment$probability
  } else {
    NA
  }

  # Extract actions
  novaris_actions <- c()
  tethys_actions <- c()

  if (!is.null(state$action_decisions[[period]])) {
    # Novaris (major_power)
    if (!is.null(state$action_decisions[[period]]$major_power)) {
      decision <- state$action_decisions[[period]]$major_power
      if (!is.null(decision$approved_actions)) {
        novaris_actions <- sapply(decision$approved_actions, function(a) a$action)
      } else if (!is.null(decision$action)) {
        novaris_actions <- decision$action
      }
    }

    # Tethys (small_power)
    if (!is.null(state$action_decisions[[period]]$small_power)) {
      decision <- state$action_decisions[[period]]$small_power
      if (!is.null(decision$approved_actions)) {
        tethys_actions <- sapply(decision$approved_actions, function(a) a$action)
      } else if (!is.null(decision$action)) {
        tethys_actions <- decision$action
      }
    }
  }

  # Extract final state
  final_state <- state$scenario_state

  return(list(
    scenario_id = scenario_id,
    period = period,
    collapse_probability = collapse_prob,
    novaris_actions = novaris_actions,
    tethys_actions = tethys_actions,
    n_novaris_actions = length(novaris_actions),
    n_tethys_actions = length(tethys_actions),
    final_territory = final_state$territory_controlled,
    final_military_balance = final_state$military_balance,
    final_crisis_level = final_state$crisis_level,
    final_sanctions = final_state$sanctions_level,
    final_support = final_state$international_support
  ))
}

output_dir <- "outputs/multiscenario"

# Find all scenario .rds files
rds_files <- list.files(output_dir, pattern = "^scenario_\\d{3}\\.rds$", full.names = TRUE)

cat(sprintf("Found %d scenario files\n", length(rds_files)))

all_ground_truth <- list()

for (rds_file in rds_files) {
  scenario_id <- sub("\\.rds$", "", basename(rds_file))
  cat(sprintf("Extracting %s...\n", scenario_id))

  state <- readRDS(rds_file)
  gt <- extract_ground_truth_from_state(state, scenario_id)

  cat(sprintf("  Collapse prob: %.3f\n", gt$collapse_probability))
  cat(sprintf("  Novaris: %d actions\n", gt$n_novaris_actions))
  cat(sprintf("  Tethys: %d actions\n", gt$n_tethys_actions))

  all_ground_truth[[scenario_id]] <- gt
}

# Convert to data frame
ground_truth_df <- do.call(rbind, lapply(all_ground_truth, function(gt) {
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

# Save
ground_truth_file <- file.path(output_dir, "ground_truth.csv")
write.csv(ground_truth_df, ground_truth_file, row.names = FALSE)

cat(sprintf("\nSaved ground truth: %s\n", ground_truth_file))
print(ground_truth_df)
