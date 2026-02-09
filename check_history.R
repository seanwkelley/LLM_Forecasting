state <- readRDS("outputs/simulation_state.rds")

cat("Checking state history structure:\n\n")

cat("scenario_state_history exists:", !is.null(state$scenario_state_history), "\n")

if (!is.null(state$scenario_state_history)) {
  cat("Length of scenario_state_history:", length(state$scenario_state_history), "\n")
} else {
  cat("scenario_state_history is NULL\n")
}

cat("Current period:", state$current_period, "\n")

cat("\nChecking state_history (alternative):\n")
cat("state_history exists:", !is.null(state$state_history), "\n")

if (!is.null(state$state_history)) {
  cat("Length of state_history:", length(state$state_history), "\n")
  cat("First element keys:", paste(names(state$state_history[[1]]), collapse=", "), "\n")
}

cat("\nChecking current scenario_state:\n")
cat("Keys:", paste(names(state$scenario_state), collapse=", "), "\n")
