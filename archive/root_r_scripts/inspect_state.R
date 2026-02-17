state <- readRDS("outputs/multiscenario/scenario_001.rds")
cat("Names in state:\n")
cat(paste(names(state), collapse=", "), "\n\n")

cat("Assessment structure:\n")
if (!is.null(state$aggregator_assessments)) {
  cat("aggregator_assessments exists, length:", length(state$aggregator_assessments), "\n")
  a <- state$aggregator_assessments[[1]]
  cat("Names:", paste(names(a), collapse=", "), "\n")
  cat("Probability:", a$probability, "\n")
  cat("\nFull response (first 500 chars):\n")
  cat(substr(a$full_response, 1, 500), "\n")
} else {
  cat("No aggregator_assessments field!\n")
  # Check other field names that might contain it
  for (n in names(state)) {
    if (grepl("assess|prob|aggregat", n, ignore.case=TRUE)) {
      cat(sprintf("  Found related field: %s\n", n))
    }
  }
}
