# Test multi-target parsing
source("config.R")

# Simulate the agents list
agents <- AGENTS

# Test the old logic (would fail)
target_name_old <- "Meridian,Aurelia"
target_agent_old <- NULL
for (a in agents) {
  if (!is.null(a$country) && grepl(target_name_old, a$country, ignore.case = TRUE)) {
    target_agent_old <- a
    break
  }
}
cat("OLD LOGIC:\n")
cat("  Target string:", target_name_old, "\n")
cat("  Found agent:", if(is.null(target_agent_old)) "NULL" else target_agent_old$name, "\n\n")

# Test the new logic (should work)
target_name_new <- "Meridian,Aurelia"
target_agent_new <- NULL
target_names <- trimws(strsplit(target_name_new, ",")[[1]])
for (tname in target_names) {
  for (a in agents) {
    if (!is.null(a$country) && grepl(tname, a$country, ignore.case = TRUE)) {
      target_agent_new <- a
      break
    }
  }
  if (!is.null(target_agent_new)) break
}
cat("NEW LOGIC:\n")
cat("  Target string:", target_name_new, "\n")
cat("  Parsed into:", paste(target_names, collapse=", "), "\n")
cat("  Found agent:", if(is.null(target_agent_new)) "NULL" else target_agent_new$name, "\n")
cat("  Agent country:", if(is.null(target_agent_new)) "NULL" else target_agent_new$country, "\n")
