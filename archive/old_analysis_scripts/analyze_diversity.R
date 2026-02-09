# Analyze action selection patterns and agent cognitive diversity

setwd("D:/Northeastern/LLM_Forecasting")
state <- readRDS("outputs/simulation_state.rds")

cat("=", rep("=", 70), "\n", sep="")
cat("ACTION SELECTION & AGENT DIVERSITY ANALYSIS\n")
cat("=", rep("=", 70), "\n\n", sep="")

# ============================================================
# 1. ACTION SELECTION BY AGENT
# ============================================================
cat("1. ACTION SELECTION PATTERNS BY AGENT\n")
cat("-", rep("-", 60), "\n\n", sep="")

# Collect all decisions with agent info
decisions <- list()
for (p in 1:10) {
  for (d in state$action_decisions[[p]]) {
    decisions[[length(decisions) + 1]] <- list(
      period = p,
      agent = d$agent_name,
      faction = d$agent_faction,
      action = d$action
    )
  }
}
dec_df <- do.call(rbind, lapply(decisions, as.data.frame, stringsAsFactors = FALSE))

# Actions by specific agent
cat("Actions chosen by each decision-maker:\n\n")
for (agent in unique(dec_df$agent)) {
  agent_actions <- dec_df[dec_df$agent == agent, "action"]
  action_counts <- table(agent_actions)
  cat(sprintf("  %s:\n", agent))
  for (a in names(sort(action_counts, decreasing = TRUE))) {
    cat(sprintf("    %-30s: %d times\n", a, action_counts[a]))
  }
  cat("\n")
}

# Peace talks specifically
cat("\nPeace Talks Analysis:\n")
peace_talks_count <- sum(dec_df$action == "peace_talks")
total_actions <- nrow(dec_df)
cat(sprintf("  Total peace_talks: %d / %d actions (%.0f%%)\n",
            peace_talks_count, total_actions, peace_talks_count/total_actions*100))

cat("\n  Peace talks by period:\n")
for (p in 1:10) {
  period_actions <- dec_df[dec_df$period == p, ]
  pt_count <- sum(period_actions$action == "peace_talks")
  cat(sprintf("    Period %2d: %d/6 factions chose peace_talks\n", p, pt_count))
}

# ============================================================
# 2. AGENT COGNITIVE CHARACTERISTICS
# ============================================================
cat("\n\n2. AGENT COGNITIVE CHARACTERISTICS\n")
cat("-", rep("-", 60), "\n\n", sep="")

# Extract agent traits
agents <- state$agents
agent_traits <- data.frame(
  name = character(),
  faction = character(),
  role = character(),
  hawk_dove = numeric(),
  worldview = character(),
  rationality = numeric(),
  paranoia = numeric(),
  consistency = numeric(),
  volatility = numeric(),
  deception_capacity = numeric(),
  deception_willingness = numeric(),
  info_access = numeric(),
  analytical = numeric(),
  stringsAsFactors = FALSE
)

for (a in agents) {
  agent_traits <- rbind(agent_traits, data.frame(
    name = a$name,
    faction = a$faction,
    role = a$role,
    hawk_dove = a$hawk_dove,
    worldview = a$worldview,
    rationality = a$cognitive_rationality,
    paranoia = a$paranoia,
    consistency = a$behavioral_consistency,
    volatility = a$emotional_volatility,
    deception_capacity = a$deception_capacity,
    deception_willingness = a$deception_willingness,
    info_access = a$information_access,
    analytical = a$analytical_capability,
    stringsAsFactors = FALSE
  ))
}

cat("Trait Ranges Across All Agents:\n\n")
numeric_cols <- c("hawk_dove", "rationality", "paranoia", "consistency",
                  "volatility", "deception_capacity", "deception_willingness",
                  "info_access", "analytical")

for (col in numeric_cols) {
  vals <- agent_traits[[col]]
  cat(sprintf("  %-22s: min=%.2f, max=%.2f, range=%.2f, sd=%.2f\n",
              col, min(vals), max(vals), max(vals)-min(vals), sd(vals)))
}

cat("\n\nWorldview Distribution:\n")
print(table(agent_traits$worldview))

cat("\n\nDetailed Agent Profiles:\n\n")
cat(sprintf("%-35s | %-8s | H/D  | Rat  | Par  | Con  | Vol  | Worldview\n", "Agent", "Faction"))
cat(rep("-", 100), "\n", sep="")

for (i in 1:nrow(agent_traits)) {
  a <- agent_traits[i, ]
  cat(sprintf("%-35s | %-8s | %.2f | %.2f | %.2f | %.2f | %.2f | %s\n",
              substr(a$name, 1, 35),
              substr(a$faction, 1, 8),
              a$hawk_dove,
              a$rationality,
              a$paranoia,
              a$consistency,
              a$volatility,
              a$worldview))
}

# ============================================================
# 3. DOES HAWK/DOVE PREDICT ACTION CHOICE?
# ============================================================
cat("\n\n3. HAWK/DOVE vs ACTION CHOICE CORRELATION\n")
cat("-", rep("-", 60), "\n\n", sep="")

# Map agents to their hawk/dove scores
agent_hd <- setNames(agent_traits$hawk_dove, agent_traits$name)

# Categorize actions
military_actions <- c("limited_strike", "military_buildup", "full_scale_attack",
                      "border_incursion", "blockade")
diplomatic_actions <- c("peace_talks", "diplomatic_visit", "humanitarian_aid",
                        "mediation_offer", "trade_agreement")
covert_actions <- c("intelligence_gathering", "cyber_attack", "sabotage",
                    "covert_operation", "covert_asymmetric_pressure")

dec_df$action_type <- ifelse(dec_df$action %in% military_actions, "military",
                      ifelse(dec_df$action %in% diplomatic_actions, "diplomatic", "covert"))

# For each agent, calculate % military actions
cat("Agent Hawk/Dove Score vs % Military Actions:\n\n")
cat(sprintf("%-35s | H/D  | %%Mil | %%Dip | %%Cov | Actions\n", "Agent"))
cat(rep("-", 80), "\n", sep="")

for (agent in unique(dec_df$agent)) {
  agent_dec <- dec_df[dec_df$agent == agent, ]
  hd <- agent_hd[agent]
  pct_mil <- sum(agent_dec$action_type == "military") / nrow(agent_dec) * 100
  pct_dip <- sum(agent_dec$action_type == "diplomatic") / nrow(agent_dec) * 100
  pct_cov <- sum(agent_dec$action_type == "covert") / nrow(agent_dec) * 100

  cat(sprintf("%-35s | %.2f | %3.0f%% | %3.0f%% | %3.0f%% | %s\n",
              substr(agent, 1, 35),
              hd,
              pct_mil, pct_dip, pct_cov,
              paste(agent_dec$action, collapse=", ")))
}

# ============================================================
# 4. PROBLEM IDENTIFICATION
# ============================================================
cat("\n\n4. IDENTIFIED ISSUES\n")
cat("-", rep("-", 60), "\n\n", sep="")

# Check worldview clustering
wv_counts <- table(agent_traits$worldview)
dominant_wv <- names(wv_counts)[which.max(wv_counts)]
cat(sprintf("a) Worldview clustering: %d/%d agents are '%s'\n",
            max(wv_counts), nrow(agent_traits), dominant_wv))

# Check rationality clustering
high_rat <- sum(agent_traits$rationality >= 0.7)
cat(sprintf("b) Rationality clustering: %d/%d agents have rationality >= 0.70\n",
            high_rat, nrow(agent_traits)))

# Check hawk/dove range for decision makers
decision_makers <- unique(dec_df$agent)
dm_traits <- agent_traits[agent_traits$name %in% decision_makers, ]
cat(sprintf("c) Decision-maker hawk/dove range: %.2f to %.2f\n",
            min(dm_traits$hawk_dove), max(dm_traits$hawk_dove)))

# Volatility check
low_vol <- sum(agent_traits$volatility <= 0.4)
cat(sprintf("d) Emotional volatility: %d/%d agents have low volatility (<= 0.40)\n",
            low_vol, nrow(agent_traits)))

cat("\n")
