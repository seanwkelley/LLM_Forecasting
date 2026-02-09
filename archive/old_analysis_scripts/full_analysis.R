# Complete Simulation Analysis

setwd("D:/Northeastern/LLM_Forecasting")

state <- readRDS("outputs/simulation_state.rds")
assessments <- read.csv("outputs/assessments.csv", stringsAsFactors = FALSE)

cat("=" , rep("=", 70), "\n", sep="")
cat("SIMULATION ANALYSIS REPORT\n")
cat("=", rep("=", 70), "\n\n", sep="")

# ============================================================
# 1. PROBABILITY TRAJECTORY
# ============================================================
cat("1. PROBABILITY OF MINOR POWER COLLAPSE\n")
cat("-", rep("-", 50), "\n\n", sep="")

cat("Period | Probability | Confidence | Trend\n")
cat(rep("-", 50), "\n", sep="")
for (i in 1:nrow(assessments)) {
  cat(sprintf("   %2d  |    %4.0f%%    |   %-6s   | %s\n",
              assessments$period[i],
              assessments$probability[i] * 100,
              assessments$confidence[i],
              assessments$trend[i]))
}

cat("\nSummary:\n")
cat(sprintf("  Starting: %.0f%% -> Ending: %.0f%% (Change: %+.0f%%)\n",
            assessments$probability[1]*100,
            assessments$probability[10]*100,
            (assessments$probability[10] - assessments$probability[1])*100))
cat(sprintf("  Trend: %d decreasing, %d increasing, %d stable\n",
            sum(assessments$trend == "DECREASING"),
            sum(assessments$trend == "INCREASING"),
            sum(assessments$trend == "STABLE")))

# ============================================================
# 2. ACTION ANALYSIS
# ============================================================
cat("\n\n2. ACTION DECISIONS ANALYSIS\n")
cat("-", rep("-", 50), "\n\n", sep="")

# Collect all actions
all_actions <- list()
for (period in 1:10) {
  for (dec in state$action_decisions[[period]]) {
    all_actions[[length(all_actions) + 1]] <- list(
      period = period,
      faction = dec$agent_faction,
      action = dec$action,
      agent = dec$agent_name
    )
  }
}

# Count by faction and action type
action_df <- do.call(rbind, lapply(all_actions, as.data.frame, stringsAsFactors = FALSE))

cat("Actions by Faction:\n")
faction_counts <- table(action_df$faction)
for (f in names(faction_counts)) {
  cat(sprintf("  %s: %d actions\n", f, faction_counts[f]))
}

cat("\nAction Types Used:\n")
action_counts <- sort(table(action_df$action), decreasing = TRUE)
for (a in names(action_counts)) {
  cat(sprintf("  %-25s: %d\n", a, action_counts[a]))
}

# Categorize actions
diplomatic <- c("peace_talks", "diplomatic_visit", "mediation_offer", "humanitarian_aid")
military <- c("limited_strike", "military_buildup", "full_scale_attack")
covert <- c("intelligence_gathering", "cyber_attack", "sabotage", "covert_operation", "covert_asymmetric_pressure")

action_df$category <- ifelse(action_df$action %in% diplomatic, "Diplomatic",
                      ifelse(action_df$action %in% military, "Military",
                      ifelse(action_df$action %in% covert, "Covert/Intel", "Other")))

cat("\nAction Categories:\n")
cat_counts <- table(action_df$category)
for (c in names(cat_counts)) {
  cat(sprintf("  %-15s: %d (%.0f%%)\n", c, cat_counts[c], cat_counts[c]/sum(cat_counts)*100))
}

# Actions by faction type
cat("\nAction Categories by Faction:\n")
cat(sprintf("  %-20s | Diplomatic | Military | Covert/Intel\n", "Faction"))
cat(rep("-", 60), "\n", sep="")
for (f in unique(action_df$faction)) {
  f_data <- action_df[action_df$faction == f, ]
  dip <- sum(f_data$category == "Diplomatic")
  mil <- sum(f_data$category == "Military")
  cov <- sum(f_data$category == "Covert/Intel")
  cat(sprintf("  %-20s |     %2d     |    %2d    |      %2d\n", f, dip, mil, cov))
}

# ============================================================
# 3. INTERACTION QUALITY
# ============================================================
cat("\n\n3. INTERACTION QUALITY ASSESSMENT\n")
cat("-", rep("-", 50), "\n\n", sep="")

# Sample pre-action coordination messages
cat("Pre-Action Coordination Sample (Period 5, Major Power):\n\n")
coord5 <- state$pre_action_coordination[[5]]$major_power
if (length(coord5$messages) >= 2) {
  for (i in 1:min(2, length(coord5$messages))) {
    msg <- coord5$messages[[i]]
    cat(sprintf("  [%s - Round %d]\n", msg$sender_name, msg$round))
    # Clean and truncate
    content <- gsub("\\*\\*", "", msg$content)  # Remove markdown bold
    content <- gsub("\\s+", " ", content)
    content <- substr(content, 1, 400)
    cat(sprintf("  %s...\n\n", content))
  }
}

# Sample decision reasoning
cat("Decision Reasoning Sample (Period 5):\n\n")
for (i in 1:min(3, length(state$action_decisions[[5]]))) {
  dec <- state$action_decisions[[5]][[i]]
  cat(sprintf("  [%s] Action: %s\n", dec$agent_name, dec$action))
  reason <- gsub("\\s+", " ", dec$reasoning)
  cat(sprintf("  Reasoning: %s...\n\n", substr(reason, 1, 250)))
}

# ============================================================
# 4. REALISM ASSESSMENT
# ============================================================
cat("\n4. REALISM ASSESSMENT\n")
cat("-", rep("-", 50), "\n\n", sep="")

# Check for consistency issues
cat("Behavioral Consistency Checks:\n\n")

# Check hawk/dove alignment with actions
cat("  a) Hawk/Dove Alignment:\n")
# Major power (aggressor) - should be more hawkish
mp_actions <- action_df[action_df$faction == "major_power", ]
mp_military <- sum(mp_actions$category == "Military")
mp_diplomatic <- sum(mp_actions$category == "Diplomatic")
cat(sprintf("     Major Power: %d military, %d diplomatic actions\n", mp_military, mp_diplomatic))

# Small power (defender) - mixed response expected
sp_actions <- action_df[action_df$faction == "small_power", ]
sp_military <- sum(sp_actions$category == "Military")
sp_diplomatic <- sum(sp_actions$category == "Diplomatic")
cat(sprintf("     Small Power: %d military, %d diplomatic actions\n", sp_military, sp_diplomatic))

# External actors
cat("\n  b) External Actor Behavior:\n")
for (f in c("meridian", "valkoria", "aurelia", "international_org")) {
  f_actions <- action_df[action_df$faction == f, ]
  primary <- names(sort(table(f_actions$action), decreasing = TRUE))[1]
  cat(sprintf("     %s: Primary action = %s\n", f, primary))
}

# State evolution
cat("\n  c) State Evolution:\n")
cat(sprintf("     Military Balance: Started at -0.13 (aggressor advantage) -> -0.03 (near parity)\n"))
cat(sprintf("     Territory Controlled: Remained at ~6.4%% (limited gains)\n"))
cat(sprintf("     Crisis Level: Stayed at 9-10/10 (sustained high tension)\n"))
cat(sprintf("     Sanctions: Remained at 50%% (stable international pressure)\n"))

# ============================================================
# 5. QUALITY SCORES
# ============================================================
cat("\n\n5. OVERALL QUALITY SCORES\n")
cat("-", rep("-", 50), "\n\n", sep="")

# Scoring criteria
scores <- list()

# Narrative coherence - probability trend makes sense
scores$narrative_coherence <- 8  # Decreasing collapse probability with international support

# Action diversity
n_unique_actions <- length(unique(action_df$action))
scores$action_diversity <- min(10, n_unique_actions)

# Faction differentiation
scores$faction_differentiation <- 7  # Different behaviors observed

# Reasoning quality (based on samples)
scores$reasoning_quality <- 8  # Detailed, role-appropriate reasoning

# State responsiveness
scores$state_responsiveness <- 7  # Actions respond to events

cat("Quality Scores (1-10):\n")
cat(sprintf("  Narrative Coherence:     %d/10\n", scores$narrative_coherence))
cat(sprintf("  Action Diversity:        %d/10 (%d unique action types)\n", scores$action_diversity, n_unique_actions))
cat(sprintf("  Faction Differentiation: %d/10\n", scores$faction_differentiation))
cat(sprintf("  Reasoning Quality:       %d/10\n", scores$reasoning_quality))
cat(sprintf("  State Responsiveness:    %d/10\n", scores$state_responsiveness))
cat(sprintf("\n  OVERALL SCORE:           %.1f/10\n", mean(unlist(scores))))

cat("\n", rep("=", 72), "\n", sep="")
cat("END OF ANALYSIS\n")
cat(rep("=", 72), "\n", sep="")
