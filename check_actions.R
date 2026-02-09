state <- readRDS("outputs/simulation_state.rds")

cat("=== ACTION RESULTS STRUCTURE ===\n\n")
cat("Length of action_results:", length(state$action_results), "\n\n")

if (length(state$action_results) > 0) {
  cat("Period 1 actions:\n")
  p1_actions <- state$action_results[[1]]
  cat("Number of actions:", length(p1_actions), "\n")
  cat("Class:", class(p1_actions), "\n\n")

  if (length(p1_actions) > 0) {
    cat("First action structure:\n")
    print(str(p1_actions[[1]]))
    cat("\nFirst 3 actions:\n")
    for (i in 1:min(3, length(p1_actions))) {
      cat(sprintf("\nAction %d:\n", i))
      print(p1_actions[[i]])
    }
  }
}
