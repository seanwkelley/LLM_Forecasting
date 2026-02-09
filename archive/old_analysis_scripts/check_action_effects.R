# Deep dive into action results structure

setwd("D:/Northeastern/LLM_Forecasting")
state <- readRDS("outputs/simulation_state.rds")

cat("=== ACTION RESULTS DEEP DIVE ===\n\n")

# Check structure of action_results
cat("1. Action Results Structure\n")
cat("-", rep("-", 40), "\n\n", sep="")

ar1 <- state$action_results[[1]]
cat("Period 1 action_results length:", length(ar1), "\n")
cat("Class:", class(ar1), "\n\n")

if (length(ar1) > 0) {
  cat("First action result structure:\n")
  str(ar1[[1]], max.level = 2)
}

cat("\n\n2. Sample Action Results (All Periods)\n")
cat("-", rep("-", 40), "\n\n", sep="")

for (p in 1:10) {
  cat(sprintf("--- Period %d ---\n", p))
  results <- state$action_results[[p]]

  if (length(results) == 0) {
    cat("  (empty)\n")
    next
  }

  for (i in seq_along(results)) {
    r <- results[[i]]
    cat(sprintf("  [%d] ", i))

    if (is.list(r)) {
      # Check what fields exist
      cat(sprintf("Fields: %s\n", paste(names(r), collapse=", ")))

      if ("action" %in% names(r)) {
        cat(sprintf("      Action: %s, Success: %s\n",
                    r$action,
                    ifelse(is.null(r$success), "NULL", as.character(r$success))))
      }

      if ("effects" %in% names(r) && !is.null(r$effects)) {
        cat(sprintf("      Effects: %s\n", paste(names(r$effects), "=", r$effects, collapse=", ")))
      }

      if ("narrative" %in% names(r)) {
        cat(sprintf("      Narrative: %s...\n", substr(r$narrative, 1, 80)))
      }
    } else {
      cat(sprintf("Not a list: %s\n", class(r)))
    }
  }
  cat("\n")
}

# 3. Check if state is being tracked over time
cat("\n3. Is State History Being Tracked?\n")
cat("-", rep("-", 40), "\n\n", sep="")

cat("Fields in simulation state:\n")
cat(paste(" ", names(state), collapse="\n"), "\n\n")

# Check if there's period-by-period state
if ("state_history" %in% names(state)) {
  cat("state_history found!\n")
  str(state$state_history, max.level = 1)
} else {
  cat("No state_history field - only final state is stored\n")
  cat("This means actions may be executing but state changes aren't tracked over time\n")
}
