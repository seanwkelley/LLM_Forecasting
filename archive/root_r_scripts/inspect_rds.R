# Inspect RDS state files to understand action storage differences
for (i in c(1,2,3,8,11,12,13)) {
  f <- sprintf("outputs/multiscenario/scenario_%03d.rds", i)
  s <- readRDS(f)
  cat(sprintf("=== scenario_%03d ===\n", i))

  # What top-level fields exist?
  cat(sprintf("  Top-level fields: %s\n", paste(names(s), collapse=", ")))

  # Check action_decisions (used by extract_ground_truth_from_state)
  if (!is.null(s$action_decisions) && length(s$action_decisions) > 0) {
    cat(sprintf("  action_decisions: length=%d\n", length(s$action_decisions)))
    if (length(s$action_decisions) >= 1 && !is.null(s$action_decisions[[1]])) {
      cat(sprintf("    [[1]] names: %s\n", paste(names(s$action_decisions[[1]]), collapse=", ")))
      if (!is.null(s$action_decisions[[1]]$major_power)) {
        d <- s$action_decisions[[1]]$major_power
        cat(sprintf("    major_power fields: %s\n", paste(names(d), collapse=", ")))
        if (!is.null(d$approved_actions)) {
          acts <- sapply(d$approved_actions, function(a) a$action)
          cat(sprintf("    Novaris approved_actions: %s\n", paste(acts, collapse=", ")))
        } else {
          cat("    Novaris: no approved_actions field\n")
        }
      } else {
        cat("    No major_power key\n")
      }
    } else {
      cat("    action_decisions[[1]] is NULL\n")
    }
  } else {
    cat("  No action_decisions (NULL or length 0)\n")
  }

  # Check action_history (used by resume loader)
  if (!is.null(s$action_history)) {
    cat(sprintf("  action_history: %d rows\n", nrow(s$action_history)))
    nov <- s$action_history[s$action_history$faction == "major_power", "action"]
    teth <- s$action_history[s$action_history$faction == "small_power", "action"]
    cat(sprintf("    Novaris: %s\n", paste(nov, collapse=", ")))
    cat(sprintf("    Tethys: %s\n", paste(teth, collapse=", ")))
  } else {
    cat("  No action_history\n")
  }

  # Check aggregator
  if (!is.null(s$aggregator_assessments) && length(s$aggregator_assessments) > 0) {
    cat(sprintf("  aggregator_assessments prob: %.3f\n", s$aggregator_assessments[[1]]$probability))
  } else {
    cat("  No aggregator_assessments\n")
  }
  if (!is.null(s$assessments_history) && length(s$assessments_history) > 0) {
    cat(sprintf("  assessments_history prob: %.3f\n", s$assessments_history[[1]]$probability))
  } else {
    cat("  No assessments_history\n")
  }

  cat("\n")
}
