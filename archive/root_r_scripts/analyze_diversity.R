gt <- read.csv("outputs/multiscenario/ground_truth.csv", stringsAsFactors=FALSE)
cat("=== MULTISCENARIO DIVERSITY ANALYSIS ===\n")
cat(sprintf("Total completed scenarios: %d\n\n", nrow(gt)))

# Collapse probability distribution
cat("--- COLLAPSE PROBABILITY ---\n")
probs <- gt$collapse_probability[!is.na(gt$collapse_probability)]
cat(sprintf("  N with valid probability: %d\n", length(probs)))
cat(sprintf("  Range: %.3f - %.3f\n", min(probs), max(probs)))
cat(sprintf("  Mean: %.3f, Median: %.3f, SD: %.3f\n", mean(probs), median(probs), sd(probs)))
cat(sprintf("  Quartiles: Q1=%.3f Q2=%.3f Q3=%.3f\n", quantile(probs, 0.25), quantile(probs, 0.5), quantile(probs, 0.75)))
cat("\n  Histogram:\n")
breaks <- seq(0.35, 0.85, by=0.05)
h <- hist(probs, breaks=breaks, plot=FALSE)
for (j in seq_along(h$counts)) {
  bar <- paste(rep("#", h$counts[j]), collapse="")
  cat(sprintf("    [%.2f-%.2f): %2d %s\n", h$breaks[j], h$breaks[j+1], h$counts[j], bar))
}

# Actions analysis - Novaris
cat("\n--- NOVARIS (MAJOR POWER) ACTIONS ---\n")
has_actions <- gt$novaris_actions != ""
novaris_all <- unlist(strsplit(gt$novaris_actions[has_actions], "\\|"))
cat(sprintf("  Scenarios with actions: %d/%d\n", sum(has_actions), nrow(gt)))
cat(sprintf("  Total action instances: %d\n", length(novaris_all)))
cat(sprintf("  Unique action types: %d\n", length(unique(novaris_all))))
cat(sprintf("  Actions per scenario: mean=%.1f, range=%d-%d\n",
    mean(gt$n_novaris_actions[gt$n_novaris_actions > 0]),
    min(gt$n_novaris_actions[gt$n_novaris_actions > 0]),
    max(gt$n_novaris_actions[gt$n_novaris_actions > 0])))
cat("\n  Action frequency:\n")
nov_tab <- sort(table(novaris_all), decreasing=TRUE)
n_with <- sum(has_actions)
for (nm in names(nov_tab)) {
  pct <- round(100 * nov_tab[nm] / n_with, 1)
  cat(sprintf("    %-35s %2d (%5.1f%%)\n", nm, nov_tab[nm], pct))
}

# Actions analysis - Tethys
cat("\n--- TETHYS (SMALL POWER) ACTIONS ---\n")
tethys_all <- unlist(strsplit(gt$tethys_actions[has_actions], "\\|"))
cat(sprintf("  Scenarios with actions: %d/%d\n", sum(gt$tethys_actions != ""), nrow(gt)))
cat(sprintf("  Total action instances: %d\n", length(tethys_all)))
cat(sprintf("  Unique action types: %d\n", length(unique(tethys_all))))
cat(sprintf("  Actions per scenario: mean=%.1f, range=%d-%d\n",
    mean(gt$n_tethys_actions[gt$n_tethys_actions > 0]),
    min(gt$n_tethys_actions[gt$n_tethys_actions > 0]),
    max(gt$n_tethys_actions[gt$n_tethys_actions > 0])))
cat("\n  Action frequency:\n")
teth_tab <- sort(table(tethys_all), decreasing=TRUE)
for (nm in names(teth_tab)) {
  pct <- round(100 * teth_tab[nm] / n_with, 1)
  cat(sprintf("    %-35s %2d (%5.1f%%)\n", nm, teth_tab[nm], pct))
}

# Unique action combos
cat("\n--- ACTION COMBINATION DIVERSITY ---\n")
with_actions <- gt[has_actions,]
cat(sprintf("  Unique Novaris action sets: %d out of %d scenarios\n",
    length(unique(with_actions$novaris_actions)), nrow(with_actions)))
cat(sprintf("  Unique Tethys action sets: %d out of %d scenarios\n",
    length(unique(with_actions$tethys_actions)), nrow(with_actions)))
combo <- paste(with_actions$novaris_actions, "||", with_actions$tethys_actions)
cat(sprintf("  Unique (Novaris,Tethys) combos: %d out of %d scenarios\n",
    length(unique(combo)), nrow(with_actions)))

# Final state diversity
cat("\n--- FINAL STATE DIVERSITY ---\n")
cat(sprintf("  Territory:   %.3f - %.3f (SD=%.3f)\n", min(gt$final_territory), max(gt$final_territory), sd(gt$final_territory)))
cat(sprintf("  Mil balance: %.3f - %.3f (SD=%.3f)\n", min(gt$final_military_balance), max(gt$final_military_balance), sd(gt$final_military_balance)))
cat(sprintf("  Crisis lvl:  %.1f - %.1f (SD=%.1f)\n", min(gt$final_crisis_level), max(gt$final_crisis_level), sd(gt$final_crisis_level)))
cat(sprintf("  Sanctions:   %.3f - %.3f (SD=%.3f)\n", min(gt$final_sanctions), max(gt$final_sanctions), sd(gt$final_sanctions)))
cat(sprintf("  Support:     %.3f - %.3f (SD=%.3f)\n", min(gt$final_support), max(gt$final_support), sd(gt$final_support)))

# Scenarios WITHOUT actions
cat("\n--- SCENARIOS WITHOUT ACTIONS ---\n")
no_actions <- gt[!has_actions,]
cat(sprintf("  %d scenarios have no actions\n", nrow(no_actions)))
cat(sprintf("  IDs: %s\n", paste(no_actions$scenario_id, collapse=", ")))
valid_probs <- no_actions$collapse_probability[!is.na(no_actions$collapse_probability)]
if (length(valid_probs) > 0) {
  cat(sprintf("  Collapse probs (valid): %s\n", paste(round(valid_probs, 3), collapse=", ")))
}
na_probs <- sum(is.na(no_actions$collapse_probability))
if (na_probs > 0) {
  cat(sprintf("  Scenarios with NA probability: %d\n", na_probs))
}
