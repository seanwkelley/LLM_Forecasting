state <- readRDS("outputs/simulation_state.rds")

cat("=== CHECKING ACTOR NAMES IN ACTION RESULTS ===\n\n")

# Check which actions are being labeled as "unknown"
for (p in 1:min(3, length(state$action_results))) {
  cat(sprintf("Period %d:\n", p))
  period_actions <- state$action_results[[p]]

  for (i in seq_along(period_actions)) {
    action_bundle <- period_actions[[i]]

    # Check if single action (external actor)
    if (!is.null(action_bundle$actor)) {
      cat(sprintf("  [%d] Actor: %s\n", i, action_bundle$actor))
      cat(sprintf("      Action: %s\n", action_bundle$action))
      cat(sprintf("      Success: %s\n\n", action_bundle$success))
    }
  }
}

cat("\n=== CHECKING AGENTS CONFIGURATION ===\n\n")
if (!is.null(state$agents)) {
  cat("External actors in state$agents:\n")
  for (agent_name in names(state$agents)) {
    agent <- state$agents[[agent_name]]
    if (!is.null(agent$faction)) {
      cat(sprintf("  %s -> faction: %s, name: %s\n",
                  agent_name,
                  agent$faction,
                  agent$name %||% "N/A"))
    }
  }
}
