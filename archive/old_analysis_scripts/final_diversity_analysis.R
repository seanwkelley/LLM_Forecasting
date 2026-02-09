# Final comprehensive diversity analysis

setwd("D:/Northeastern/LLM_Forecasting")
state <- readRDS("outputs/simulation_state.rds")

cat("=", rep("=", 70), "\n", sep="")
cat("COMPREHENSIVE AGENT DIVERSITY ANALYSIS\n")
cat("=", rep("=", 70), "\n\n", sep="")

# Build complete traits dataframe
agents <- state$agents
agent_data <- list()

for (i in seq_along(agents)) {
  a <- agents[[i]]
  agent_data[[i]] <- data.frame(
    name = a$name,
    faction = a$faction,
    role = a$role,
    hawk_dove = a$hawk_dove,
    worldview = a$worldview,
    # Nested in rationality
    cognitive_rat = a$rationality$cognitive,
    paranoia = a$rationality$paranoia,
    consistency = a$rationality$consistency,
    volatility = a$rationality$volatility,
    # Nested in deception
    deception_cap = a$deception$capacity,
    deception_will = a$deception$willingness,
    # Nested in information
    info_access = a$information$access,
    info_accuracy = a$information$accuracy,
    stringsAsFactors = FALSE
  )
}
agent_df <- do.call(rbind, agent_data)

# ============================================================
# 1. TRAIT RANGES
# ============================================================
cat("1. TRAIT DIVERSITY METRICS\n")
cat("-", rep("-", 60), "\n\n", sep="")

cat(sprintf("%-18s | %5s | %5s | %5s | %5s | Interpretation\n",
            "Trait", "Min", "Max", "Range", "SD"))
cat(rep("-", 75), "\n", sep="")

traits_to_check <- c("hawk_dove", "cognitive_rat", "paranoia", "consistency",
                     "volatility", "deception_cap", "deception_will", "info_access")

for (trait in traits_to_check) {
  vals <- agent_df[[trait]]
  rng <- max(vals) - min(vals)
  s <- sd(vals)

  # Interpretation
  interp <- if (rng < 0.3) "LOW diversity" else if (rng < 0.5) "MODERATE" else "GOOD diversity"

  cat(sprintf("%-18s | %5.2f | %5.2f | %5.2f | %5.2f | %s\n",
              trait, min(vals), max(vals), rng, s, interp))
}

# ============================================================
# 2. WORLDVIEW DISTRIBUTION
# ============================================================
cat("\n\n2. WORLDVIEW DISTRIBUTION\n")
cat("-", rep("-", 60), "\n\n", sep="")

wv_table <- table(agent_df$worldview)
for (wv in names(sort(wv_table, decreasing = TRUE))) {
  pct <- wv_table[wv] / 12 * 100
  bar <- paste(rep("█", round(pct/5)), collapse="")
  cat(sprintf("%-25s: %d (%2.0f%%) %s\n", wv, wv_table[wv], pct, bar))
}

# ============================================================
# 3. COMPLETE AGENT PROFILES
# ============================================================
cat("\n\n3. COMPLETE AGENT PROFILES\n")
cat("-", rep("-", 60), "\n\n", sep="")

for (i in 1:nrow(agent_df)) {
  a <- agent_df[i, ]
  cat(sprintf("%s (%s)\n", a$name, a$faction))
  cat(sprintf("  Worldview: %s\n", a$worldview))
  cat(sprintf("  Hawk/Dove: %.0f%% hawk\n", a$hawk_dove * 100))
  cat(sprintf("  Cognitive: Rationality=%.0f%%, Paranoia=%.0f%%, Consistency=%.0f%%, Volatility=%.0f%%\n",
              a$cognitive_rat*100, a$paranoia*100, a$consistency*100, a$volatility*100))
  cat(sprintf("  Deception: Capacity=%.0f%%, Willingness=%.0f%%\n",
              a$deception_cap*100, a$deception_will*100))
  cat(sprintf("  Information: Access=%.0f%%, Accuracy=%.0f%%\n",
              a$info_access*100, a$info_accuracy*100))
  cat("\n")
}

# ============================================================
# 4. DECISION-MAKER ANALYSIS
# ============================================================
cat("\n4. DECISION-MAKER ANALYSIS (Faction Leaders)\n")
cat("-", rep("-", 60), "\n\n", sep="")

# Identify decision makers from action_decisions
dm_names <- c("Major Power Defense Minister", "Smaller Power President",
              "Meridian Representative", "Valkoria Representative",
              "Aurelia Representative", "International Organization Representative")

dm_df <- agent_df[agent_df$name %in% dm_names, ]

cat(sprintf("%-35s | H/D  | Rat  | Par  | Vol  | Worldview\n", "Decision Maker"))
cat(rep("-", 90), "\n", sep="")

for (i in 1:nrow(dm_df)) {
  a <- dm_df[i, ]
  cat(sprintf("%-35s | %.2f | %.2f | %.2f | %.2f | %s\n",
              a$name, a$hawk_dove, a$cognitive_rat, a$paranoia, a$volatility, a$worldview))
}

# ============================================================
# 5. KEY ISSUES
# ============================================================
cat("\n\n5. IDENTIFIED DIVERSITY ISSUES\n")
cat("-", rep("-", 60), "\n\n", sep="")

# Issue 1: Worldview homogeneity
pt_count <- sum(agent_df$worldview == "pragmatic_technocrat")
cat(sprintf("ISSUE 1: WORLDVIEW HOMOGENEITY\n"))
cat(sprintf("  - %d/12 (%.0f%%) agents are 'pragmatic_technocrat'\n", pt_count, pt_count/12*100))
cat(sprintf("  - Only %d/12 agents have 'nationalist_populist' worldview\n",
            sum(agent_df$worldview == "nationalist_populist")))
cat(sprintf("  - 0/12 agents have 'realist' worldview\n"))
cat("  IMPACT: Pragmatic technocrats favor data-driven, 'optimal' solutions\n")
cat("          like peace_talks over risky military actions.\n\n")

# Issue 2: Decision-maker worldviews even more concentrated
dm_wv <- table(dm_df$worldview)
cat(sprintf("ISSUE 2: DECISION-MAKER WORLDVIEW CONCENTRATION\n"))
cat(sprintf("  - 4/6 decision-makers are pragmatic_technocrat\n"))
cat(sprintf("  - 2/6 are liberal_institutionalist\n"))
cat(sprintf("  - 0/6 are nationalist_populist or realist\n"))
cat("  IMPACT: No hawkish worldviews among those who choose actions!\n\n")

# Issue 3: High rationality across the board
high_rat <- sum(agent_df$cognitive_rat >= 0.70)
cat(sprintf("ISSUE 3: UNIFORMLY HIGH RATIONALITY\n"))
cat(sprintf("  - %d/12 agents have rationality >= 70%%\n", high_rat))
cat(sprintf("  - Minimum rationality: %.0f%%\n", min(agent_df$cognitive_rat)*100))
cat("  IMPACT: All agents make 'sensible' choices; no irrational escalation.\n\n")

# Issue 4: Low volatility
low_vol <- sum(agent_df$volatility <= 0.50)
cat(sprintf("ISSUE 4: LOW EMOTIONAL VOLATILITY\n"))
cat(sprintf("  - %d/12 agents have volatility <= 50%%\n", low_vol))
cat(sprintf("  - Maximum volatility: %.0f%%\n", max(agent_df$volatility)*100))
cat("  IMPACT: Few emotion-driven decisions; steady, predictable behavior.\n\n")

# ============================================================
# 6. RECOMMENDATIONS
# ============================================================
cat("\n6. RECOMMENDATIONS FOR MORE DIVERSE BEHAVIOR\n")
cat("-", rep("-", 60), "\n\n", sep="")

cat("To get more varied action selection (less peace_talks convergence):\n\n")

cat("a) WORLDVIEW CHANGES:\n")
cat("   - Change 2-3 agents to 'realist' worldview (see threats, favor military)\n")
cat("   - Change Major Power Defense Minister to 'nationalist_populist'\n")
cat("   - Add a 'revolutionary' or 'ideological' worldview option\n\n")

cat("b) COGNITIVE TRAIT CHANGES:\n")
cat("   - Lower rationality for 2-3 agents to 0.40-0.55 range\n")
cat("   - Increase volatility for key decision-makers (0.60-0.80)\n")
cat("   - Increase paranoia for major_power agents (currently 0.27-0.86)\n\n")

cat("c) DECISION-MAKER SELECTION:\n")
cat("   - Consider letting Military Chief (0.90 hawk) make decisions instead\n")
cat("     of Defense Minister (0.70 hawk) for major_power\n")
cat("   - Let Military Commander (0.85 hawk) sometimes override President\n\n")

cat("d) STRUCTURAL CHANGES:\n")
cat("   - Weight action selection by hawk_dove score\n")
cat("   - Add 'pressure' mechanics that push toward military action\n")
cat("   - Reduce peace_talks success rate or add diminishing returns\n")
