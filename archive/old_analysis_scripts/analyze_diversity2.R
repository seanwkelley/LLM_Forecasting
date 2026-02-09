# Analyze agent cognitive diversity - fixed version

setwd("D:/Northeastern/LLM_Forecasting")
state <- readRDS("outputs/simulation_state.rds")

cat("=", rep("=", 70), "\n", sep="")
cat("AGENT COGNITIVE DIVERSITY ANALYSIS\n")
cat("=", rep("=", 70), "\n\n", sep="")

# ============================================================
# 1. EXTRACT AGENT TRAITS
# ============================================================
cat("1. AGENT COGNITIVE CHARACTERISTICS\n")
cat("-", rep("-", 60), "\n\n", sep="")

agents <- state$agents

# First, check what fields are available
cat("Available fields in first agent:\n")
cat(paste(" ", names(agents[[1]]), collapse="\n"), "\n\n")

# Build traits dataframe safely
agent_traits <- list()
for (i in seq_along(agents)) {
  a <- agents[[i]]
  agent_traits[[i]] <- list(
    name = ifelse(is.null(a$name), NA, a$name),
    faction = ifelse(is.null(a$faction), NA, a$faction),
    role = ifelse(is.null(a$role), NA, a$role),
    hawk_dove = ifelse(is.null(a$hawk_dove), NA, a$hawk_dove),
    worldview = ifelse(is.null(a$worldview), NA, a$worldview),
    rationality = ifelse(is.null(a$cognitive_rationality), NA, a$cognitive_rationality),
    paranoia = ifelse(is.null(a$paranoia), NA, a$paranoia),
    consistency = ifelse(is.null(a$behavioral_consistency), NA, a$behavioral_consistency),
    volatility = ifelse(is.null(a$emotional_volatility), NA, a$emotional_volatility),
    deception_cap = ifelse(is.null(a$deception_capacity), NA, a$deception_capacity),
    deception_will = ifelse(is.null(a$deception_willingness), NA, a$deception_willingness),
    info_access = ifelse(is.null(a$information_access), NA, a$information_access),
    analytical = ifelse(is.null(a$analytical_capability), NA, a$analytical_capability),
    policy_adherence = ifelse(is.null(a$policy_adherence), NA, a$policy_adherence),
    objective_alignment = ifelse(is.null(a$objective_alignment), NA, a$objective_alignment)
  )
}
agent_df <- do.call(rbind, lapply(agent_traits, as.data.frame, stringsAsFactors = FALSE))

cat("Trait Ranges Across All 12 Agents:\n\n")
cat(sprintf("%-22s | %5s | %5s | %5s | %5s\n", "Trait", "Min", "Max", "Range", "SD"))
cat(rep("-", 55), "\n", sep="")

numeric_cols <- c("hawk_dove", "rationality", "paranoia", "consistency",
                  "volatility", "deception_cap", "deception_will",
                  "info_access", "analytical", "policy_adherence", "objective_alignment")

for (col in numeric_cols) {
  vals <- agent_df[[col]]
  vals <- vals[!is.na(vals)]
  if (length(vals) > 0) {
    cat(sprintf("%-22s | %5.2f | %5.2f | %5.2f | %5.2f\n",
                col, min(vals), max(vals), max(vals)-min(vals), sd(vals)))
  }
}

cat("\n\nWorldview Distribution:\n")
print(table(agent_df$worldview))

# ============================================================
# 2. DETAILED PROFILES
# ============================================================
cat("\n\n2. DETAILED AGENT PROFILES\n")
cat("-", rep("-", 60), "\n\n", sep="")

cat(sprintf("%-32s | %-12s | H/D  | Rat  | Par  | Vol  | Worldview\n", "Agent", "Faction"))
cat(rep("-", 95), "\n", sep="")

for (i in 1:nrow(agent_df)) {
  a <- agent_df[i, ]
  cat(sprintf("%-32s | %-12s | %.2f | %.2f | %.2f | %.2f | %s\n",
              substr(a$name, 1, 32),
              substr(a$faction, 1, 12),
              a$hawk_dove,
              a$rationality,
              a$paranoia,
              a$volatility,
              a$worldview))
}

# ============================================================
# 3. DIVERSITY ISSUES
# ============================================================
cat("\n\n3. DIVERSITY ANALYSIS\n")
cat("-", rep("-", 60), "\n\n", sep="")

# Worldview concentration
wv_table <- table(agent_df$worldview)
cat("a) WORLDVIEW CONCENTRATION:\n")
for (wv in names(sort(wv_table, decreasing = TRUE))) {
  cat(sprintf("   %-25s: %d agents (%.0f%%)\n", wv, wv_table[wv], wv_table[wv]/12*100))
}

# Rationality clustering
cat("\nb) RATIONALITY CLUSTERING:\n")
cat(sprintf("   High rationality (>=0.75): %d agents\n", sum(agent_df$rationality >= 0.75, na.rm=TRUE)))
cat(sprintf("   Medium (0.50-0.74):        %d agents\n", sum(agent_df$rationality >= 0.50 & agent_df$rationality < 0.75, na.rm=TRUE)))
cat(sprintf("   Low (<0.50):               %d agents\n", sum(agent_df$rationality < 0.50, na.rm=TRUE)))

# Volatility clustering
cat("\nc) EMOTIONAL VOLATILITY:\n")
cat(sprintf("   High volatility (>=0.50):  %d agents\n", sum(agent_df$volatility >= 0.50, na.rm=TRUE)))
cat(sprintf("   Medium (0.30-0.49):        %d agents\n", sum(agent_df$volatility >= 0.30 & agent_df$volatility < 0.50, na.rm=TRUE)))
cat(sprintf("   Low (<0.30):               %d agents\n", sum(agent_df$volatility < 0.30, na.rm=TRUE)))

# Hawk/Dove distribution
cat("\nd) HAWK/DOVE DISTRIBUTION:\n")
cat(sprintf("   Strong hawks (>=0.70):     %d agents\n", sum(agent_df$hawk_dove >= 0.70, na.rm=TRUE)))
cat(sprintf("   Moderate (0.30-0.69):      %d agents\n", sum(agent_df$hawk_dove >= 0.30 & agent_df$hawk_dove < 0.70, na.rm=TRUE)))
cat(sprintf("   Doves (<0.30):             %d agents\n", sum(agent_df$hawk_dove < 0.30, na.rm=TRUE)))

# ============================================================
# 4. DECISION-MAKER SPECIFIC ANALYSIS
# ============================================================
cat("\n\n4. DECISION-MAKER TRAITS (agents who make action choices)\n")
cat("-", rep("-", 60), "\n\n", sep="")

# The decision makers based on faction leaders
decision_makers <- c("Major Power Defense Minister", "Smaller Power President",
                     "Meridian Representative", "Valkoria Representative",
                     "Aurelia Representative", "International Organization Representative")

dm_df <- agent_df[agent_df$name %in% decision_makers, ]

cat(sprintf("%-35s | H/D  | Rat  | Par  | Worldview\n", "Decision Maker"))
cat(rep("-", 75), "\n", sep="")

for (i in 1:nrow(dm_df)) {
  a <- dm_df[i, ]
  cat(sprintf("%-35s | %.2f | %.2f | %.2f | %s\n",
              a$name, a$hawk_dove, a$rationality, a$paranoia, a$worldview))
}

cat("\nDecision-maker trait ranges:\n")
cat(sprintf("  Hawk/Dove:   %.2f - %.2f (range: %.2f)\n",
            min(dm_df$hawk_dove), max(dm_df$hawk_dove), max(dm_df$hawk_dove) - min(dm_df$hawk_dove)))
cat(sprintf("  Rationality: %.2f - %.2f (range: %.2f)\n",
            min(dm_df$rationality), max(dm_df$rationality), max(dm_df$rationality) - min(dm_df$rationality)))
cat(sprintf("  Paranoia:    %.2f - %.2f (range: %.2f)\n",
            min(dm_df$paranoia), max(dm_df$paranoia), max(dm_df$paranoia) - min(dm_df$paranoia)))

cat("\nDecision-maker worldviews:\n")
print(table(dm_df$worldview))

cat("\n\n5. KEY FINDINGS\n")
cat("-", rep("-", 60), "\n\n", sep="")

cat("ISSUES IDENTIFIED:\n\n")

# Check pragmatic_technocrat dominance
pt_count <- sum(agent_df$worldview == "pragmatic_technocrat", na.rm=TRUE)
if (pt_count >= 6) {
  cat(sprintf("1. WORLDVIEW HOMOGENEITY: %d/12 agents are 'pragmatic_technocrat'\n", pt_count))
  cat("   This creates convergent thinking toward rational, data-driven solutions\n")
  cat("   like peace_talks, which appear 'optimal' to technocratic worldviews.\n\n")
}

# Check high rationality
high_rat <- sum(agent_df$rationality >= 0.70, na.rm=TRUE)
if (high_rat >= 8) {
  cat(sprintf("2. RATIONALITY CLUSTERING: %d/12 agents have rationality >= 0.70\n", high_rat))
  cat("   High rationality agents converge on similar 'optimal' choices.\n")
  cat("   Fewer impulsive or emotionally-driven decisions.\n\n")
}

# Check low volatility
low_vol <- sum(agent_df$volatility <= 0.40, na.rm=TRUE)
if (low_vol >= 8) {
  cat(sprintf("3. LOW EMOTIONAL VOLATILITY: %d/12 agents have volatility <= 0.40\n", low_vol))
  cat("   Agents rarely make dramatic, emotion-driven choices.\n")
  cat("   This suppresses escalatory spirals and erratic behavior.\n\n")
}

cat("RECOMMENDATION:\n")
cat("To increase action diversity, consider:\n")
cat("  - Adding more nationalist_populist or realist worldviews\n")
cat("  - Lowering rationality for some agents (impulsive decision-makers)\n")
cat("  - Increasing emotional volatility for key actors\n")
cat("  - Adding agents with high paranoia + low rationality combinations\n")
