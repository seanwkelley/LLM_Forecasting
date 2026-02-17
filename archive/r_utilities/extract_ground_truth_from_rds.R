#!/usr/bin/env Rscript
# Extract ground truth from saved .rds scenario files

source("generate_multiscenario_dataset.R")

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
