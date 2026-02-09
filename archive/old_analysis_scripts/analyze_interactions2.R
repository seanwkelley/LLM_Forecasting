# Analyze interaction quality from simulation - debug version

setwd("D:/Northeastern/LLM_Forecasting")

state <- readRDS("outputs/simulation_state.rds")

cat("=== INTERACTION QUALITY ANALYSIS ===\n\n")

# Debug structure
cat("--- Debug: Period 1 interactions structure ---\n")
p1 <- state$interactions_history[[1]]
cat("Length:", length(p1), "\n")
cat("Class:", class(p1), "\n")
cat("Names:", paste(names(p1), collapse=", "), "\n\n")

# Check first element
cat("First element class:", class(p1[[1]]), "\n")
if (is.list(p1[[1]])) {
  cat("First element names:", paste(names(p1[[1]]), collapse=", "), "\n")
}

# Try to access correctly
cat("\n--- Sample Interaction Details ---\n")
int1 <- p1[[1]]
if (is.list(int1) && "type" %in% names(int1)) {
  cat("Type:", int1$type, "\n")
  cat("Topic:", int1$topic, "\n")
  cat("Participants:", paste(int1$participants, collapse=", "), "\n")
  cat("N messages:", length(int1$messages), "\n")
} else {
  cat("Structure differs from expected. Dumping:\n")
  str(int1, max.level = 2)
}

cat("\n--- Pre-Action Coordination Structure ---\n")
coord1 <- state$pre_action_coordination[[1]]
cat("Class:", class(coord1), "\n")
cat("Names:", paste(names(coord1), collapse=", "), "\n")

# Get faction coordination
if ("major_power" %in% names(coord1)) {
  mp <- coord1$major_power
  cat("\nMajor Power coordination:\n")
  cat("  Participants:", paste(mp$participants, collapse=", "), "\n")
  cat("  N messages:", length(mp$messages), "\n")

  if (length(mp$messages) > 0) {
    msg1 <- mp$messages[[1]]
    cat("\n  First message from:", msg1$sender_name, "\n")
    cat("  Content preview:\n")
    cat("  ", substr(gsub("\\s+", " ", msg1$content), 1, 300), "...\n")
  }
}

cat("\n--- Action Decisions Structure ---\n")
dec1 <- state$action_decisions[[1]]
cat("Class:", class(dec1), "\n")
cat("Length:", length(dec1), "\n")
if (length(dec1) > 0) {
  d <- dec1[[1]]
  cat("First decision names:", paste(names(d), collapse=", "), "\n")
  cat("Agent:", d$agent_name, "\n")
  cat("Action:", d$action, "\n")
  cat("Target:", d$target, "\n")
  cat("Reasoning preview:", substr(gsub("\\s+", " ", d$reasoning), 1, 200), "...\n")
}

cat("\nDone!\n")
