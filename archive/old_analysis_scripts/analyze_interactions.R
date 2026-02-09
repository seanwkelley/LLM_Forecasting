# Analyze interaction quality from simulation

setwd("D:/Northeastern/LLM_Forecasting")

state <- readRDS("outputs/simulation_state.rds")

cat("=== INTERACTION QUALITY ANALYSIS ===\n\n")

# 1. Interaction counts
cat("--- Interaction Counts by Period ---\n")
for (i in 1:length(state$interactions_history)) {
  period_ints <- state$interactions_history[[i]]
  cat(sprintf("Period %d: %d interaction scenarios\n", i, length(period_ints)))
}

cat("\n--- Interaction Types ---\n")
all_types <- c()
for (period in state$interactions_history) {
  for (int in period) {
    all_types <- c(all_types, int$type)
  }
}
print(table(all_types))

cat("\n--- Sample Interactions (Period 5) ---\n")
p5 <- state$interactions_history[[5]]
for (i in 1:min(3, length(p5))) {
  int <- p5[[i]]
  cat(sprintf("\n[%d] Type: %s\n", i, int$type))
  cat(sprintf("    Topic: %s\n", int$topic))
  cat(sprintf("    Participants: %s\n", paste(int$participants, collapse=", ")))
  cat(sprintf("    Messages: %d\n", length(int$messages)))

  # Show first message snippet
  if (length(int$messages) > 0) {
    msg <- int$messages[[1]]
    content_preview <- substr(gsub("\\s+", " ", msg$content), 1, 200)
    cat(sprintf("    First msg (%s): %s...\n", msg$sender_name, content_preview))
  }
}

cat("\n\n--- Pre-Action Coordination Quality ---\n")
for (i in c(1, 5, 10)) {
  cat(sprintf("\nPeriod %d:\n", i))
  coord <- state$pre_action_coordination[[i]]
  for (faction_name in names(coord)) {
    fc <- coord[[faction_name]]
    cat(sprintf("  %s: %d participants, %d messages\n",
                toupper(faction_name),
                length(fc$participants),
                length(fc$messages)))
  }
}

cat("\n\n--- Action Decision Quality ---\n")
for (i in c(1, 5, 10)) {
  cat(sprintf("\nPeriod %d decisions:\n", i))
  decisions <- state$action_decisions[[i]]
  for (d in decisions) {
    cat(sprintf("  %s (%s): %s -> %s\n",
                d$agent_name, d$faction, d$action,
                ifelse(is.null(d$target) || d$target == "none", "N/A", d$target)))
    # Show reasoning snippet
    if (!is.null(d$reasoning)) {
      reason_preview <- substr(gsub("\\s+", " ", d$reasoning), 1, 150)
      cat(sprintf("    Reasoning: %s...\n", reason_preview))
    }
  }
}

cat("\n\nDone!\n")
