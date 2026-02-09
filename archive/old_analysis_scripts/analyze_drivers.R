# Analyze what's driving the steady probability decline

setwd("D:/Northeastern/LLM_Forecasting")

state <- readRDS("outputs/simulation_state.rds")
assessments <- read.csv("outputs/assessments.csv", stringsAsFactors = FALSE)

cat("=== DRIVERS OF PROBABILITY CHANGE ===\n\n")

# 1. Check if state variables are actually changing
cat("1. STATE VARIABLE EVOLUTION\n")
cat("-", rep("-", 50), "\n\n", sep="")

cat("The simulation state at end of Period 10:\n")
cat(sprintf("  Military Balance:    %.3f (negative = aggressor advantage)\n", state$scenario_state$military_balance))
cat(sprintf("  Territory Controlled: %.1f%%\n", state$scenario_state$territory_controlled * 100))
cat(sprintf("  Crisis Level:        %.0f/10\n", state$scenario_state$crisis_level))
cat(sprintf("  Sanctions Level:     %.0f%%\n", state$scenario_state$sanctions_level * 100))
cat(sprintf("  International Support: %.0f%%\n", state$scenario_state$international_support * 100))
cat(sprintf("  Momentum:            %.2f\n", state$scenario_state$momentum))

cat("\nPROBLEM: These are only final values. Let me check action results for changes...\n\n")

# 2. Look at action results to see state changes
cat("2. ACTION RESULTS & STATE CHANGES BY PERIOD\n")
cat("-", rep("-", 50), "\n\n", sep="")

for (p in 1:10) {
  cat(sprintf("--- Period %d (Prob: %.0f%% -> ", p,
              ifelse(p==1, 35, assessments$probability[p-1]*100)))
  cat(sprintf("%.0f%%) ---\n", assessments$probability[p]*100))

  results <- state$action_results[[p]]
  for (r in results) {
    if (!is.null(r$effects) && length(r$effects) > 0) {
      effects_str <- paste(names(r$effects), "=", unlist(r$effects), collapse=", ")
      cat(sprintf("  %s by %s: %s -> Effects: %s\n",
                  r$action, r$faction,
                  ifelse(r$success, "SUCCESS", "FAILED"),
                  effects_str))
    } else {
      cat(sprintf("  %s by %s: %s (no state effects)\n",
                  r$action, r$faction,
                  ifelse(r$success, "SUCCESS", "FAILED")))
    }
  }
  cat("\n")
}

# 3. Check what the aggregator is actually seeing
cat("\n3. KEY FACTORS FROM AGGREGATOR ASSESSMENTS\n")
cat("-", rep("-", 50), "\n\n", sep="")

for (p in 1:10) {
  cat(sprintf("Period %d (%.0f%%): ", p, assessments$probability[p]*100))

  # Extract key themes from key_factors
  kf <- assessments$key_factors[p]
  if (!is.na(kf) && nchar(kf) > 0) {
    # Look for key phrases
    has_support <- grepl("international support|70%|strong.*support", kf, ignore.case=TRUE)
    has_sanctions <- grepl("sanction", kf, ignore.case=TRUE)
    has_military <- grepl("military advantage|territorial", kf, ignore.case=TRUE)
    has_diplomacy <- grepl("peace|negotiat|mediat|diplomatic", kf, ignore.case=TRUE)
    has_resilience <- grepl("resilien|stable|cohesion", kf, ignore.case=TRUE)

    themes <- c()
    if (has_support) themes <- c(themes, "int'l support")
    if (has_sanctions) themes <- c(themes, "sanctions pressure")
    if (has_military) themes <- c(themes, "military factors")
    if (has_diplomacy) themes <- c(themes, "diplomatic progress")
    if (has_resilience) themes <- c(themes, "regime resilience")

    cat(paste(themes, collapse=", "), "\n")
  } else {
    cat("(no key factors recorded)\n")
  }
}

# 4. The real issue - static inputs?
cat("\n\n4. POTENTIAL ISSUE: STATIC CONTEXT TO AGGREGATOR\n")
cat("-", rep("-", 50), "\n\n", sep="")

cat("Checking what context the aggregator receives...\n\n")

# Look at assessment history structure
a1 <- state$assessments_history[[1]]
cat("Assessment input fields:\n")
cat(paste(" ", names(a1), collapse="\n"), "\n")

cat("\nThe aggregator likely sees:\n")
cat("  - scenario_state (but is it updated each period?)\n")
cat("  - recent actions and results\n")
cat("  - interaction summaries\n")
cat("\nIf scenario_state values don't change much, the aggregator\n")
cat("may be making incremental adjustments based on similar inputs.\n")
