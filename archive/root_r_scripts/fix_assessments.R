# Fix accumulated assessments.csv files in multiscenario outputs
# ================================================================
# Each scenario's assessments.csv incorrectly contains rows from all
# prior scenarios due to append-mode writing to a shared temp file.
# The correct assessment for each scenario is the LAST row in the file.

output_dir <- "outputs/multiscenario"

scenario_dirs <- list.dirs(output_dir, recursive = FALSE)
scenario_dirs <- scenario_dirs[grepl("scenario_\\d{3}$", scenario_dirs)]
scenario_dirs <- sort(scenario_dirs)

cat(sprintf("Found %d scenario directories\n\n", length(scenario_dirs)))

fixed <- 0
skipped <- 0

for (d in scenario_dirs) {
  afile <- file.path(d, "assessments.csv")
  scenario_name <- basename(d)

  if (!file.exists(afile)) {
    cat(sprintf("  %s: no assessments.csv, skipping\n", scenario_name))
    skipped <- skipped + 1
    next
  }

  df <- read.csv(afile, stringsAsFactors = FALSE)
  n_rows <- nrow(df)

  if (n_rows == 1) {
    cat(sprintf("  %s: already 1 row, OK\n", scenario_name))
    skipped <- skipped + 1
    next
  }

  # Keep only the last row (the actual assessment for this scenario)
  correct_row <- df[n_rows, , drop = FALSE]
  write.csv(correct_row, afile, row.names = FALSE)
  cat(sprintf("  %s: had %d rows, kept last row (prob=%.3f)\n",
              scenario_name, n_rows, correct_row$probability))
  fixed <- fixed + 1
}

cat(sprintf("\nDone: fixed %d, skipped %d (already correct or missing)\n", fixed, skipped))
