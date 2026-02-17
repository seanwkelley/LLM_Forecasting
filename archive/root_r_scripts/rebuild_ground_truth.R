# Rebuild ground_truth.csv from RDS state files
# ================================================
# Uses correct field names: action_decisions (not action_history),
# and falls back from aggregator_assessments to assessments_history.

output_dir <- "outputs/multiscenario"
scenarios <- read.csv(file.path(output_dir, "scenarios.csv"), stringsAsFactors = FALSE)

cat("Rebuilding ground_truth.csv from RDS files...\n\n")

all_rows <- list()

for (i in 1:nrow(scenarios)) {
  state_file <- file.path(output_dir, sprintf("scenario_%03d.rds", i))
  if (!file.exists(state_file)) next

  s <- readRDS(state_file)
  sid <- scenarios$scenario_id[i]

  # Collapse probability - check both field names
  collapse_prob <- NA
  if (!is.null(s$aggregator_assessments) && length(s$aggregator_assessments) > 0) {
    if (!is.null(s$aggregator_assessments[[1]]$probability)) {
      collapse_prob <- s$aggregator_assessments[[1]]$probability
    }
  } else if (!is.null(s$assessments_history) && length(s$assessments_history) > 0) {
    if (!is.null(s$assessments_history[[1]]$probability)) {
      collapse_prob <- s$assessments_history[[1]]$probability
    }
  }

  # Actions from action_decisions
  novaris_actions <- character(0)
  tethys_actions <- character(0)
  if (!is.null(s$action_decisions) && length(s$action_decisions) > 0) {
    if (!is.null(s$action_decisions[[1]]$major_power$approved_actions)) {
      novaris_actions <- sapply(s$action_decisions[[1]]$major_power$approved_actions, function(a) a$action)
    }
    if (!is.null(s$action_decisions[[1]]$small_power$approved_actions)) {
      tethys_actions <- sapply(s$action_decisions[[1]]$small_power$approved_actions, function(a) a$action)
    }
  }

  all_rows[[length(all_rows) + 1]] <- data.frame(
    scenario_id = sid,
    period = 1,
    collapse_probability = collapse_prob,
    novaris_actions = paste(novaris_actions, collapse = "|"),
    tethys_actions = paste(tethys_actions, collapse = "|"),
    n_novaris_actions = length(novaris_actions),
    n_tethys_actions = length(tethys_actions),
    final_territory = s$scenario_state$territory_controlled,
    final_military_balance = s$scenario_state$military_balance,
    final_crisis_level = s$scenario_state$crisis_level,
    final_sanctions = s$scenario_state$sanctions_level,
    final_support = s$scenario_state$international_support,
    stringsAsFactors = FALSE
  )

  cat(sprintf("  %s: prob=%.3f, novaris=%d actions, tethys=%d actions\n",
              sid, collapse_prob, length(novaris_actions), length(tethys_actions)))
}

gt <- do.call(rbind, all_rows)

# Back up old file
old_file <- file.path(output_dir, "ground_truth.csv")
if (file.exists(old_file)) {
  backup <- file.path(output_dir, "ground_truth_backup.csv")
  file.copy(old_file, backup, overwrite = TRUE)
  cat(sprintf("\nBacked up old ground_truth.csv to %s\n", backup))
}

write.csv(gt, old_file, row.names = FALSE)
cat(sprintf("\nRebuilt ground_truth.csv: %d scenarios\n", nrow(gt)))

# Summary
cat(sprintf("\nAll scenarios have actions: %s\n", all(gt$n_novaris_actions > 0)))
cat(sprintf("All scenarios have probability: %s\n", all(!is.na(gt$collapse_probability))))
cat(sprintf("Probability range: %.3f - %.3f\n", min(gt$collapse_probability, na.rm=TRUE), max(gt$collapse_probability, na.rm=TRUE)))
