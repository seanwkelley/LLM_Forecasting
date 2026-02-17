# Quick test of preset mapping - no API calls needed
library(jsonlite)

# Source config for SCENARIO_PRESETS
source("config.R")

# Source the mapping functions from generate_multiscenario_dataset.R
source_env <- new.env(parent = globalenv())
exprs <- parse("generate_multiscenario_dataset.R")
for (expr in exprs) {
  expr_text <- deparse(expr)
  if (any(grepl("<-\\s*function", expr_text)) || any(grepl("^library\\(", expr_text))) {
    eval(expr, envir = source_env)
  }
}
for (fn_name in c("map_scenario_to_preset", "get_preset_context", "generate_scenario_parameters")) {
  if (exists(fn_name, envir = source_env)) {
    assign(fn_name, get(fn_name, envir = source_env), envir = globalenv())
  }
}

cat("Testing preset mapping...\n\n")

# Test with specific parameter combinations
test_cases <- list(
  list(territory_controlled=0.01, military_balance=-0.22, crisis_level=5, sanctions_level=0.1, international_support=0.5),
  list(territory_controlled=0.35, military_balance=-0.25, crisis_level=9, sanctions_level=0.7, international_support=0.8),
  list(territory_controlled=0.15, military_balance=0.0, crisis_level=5, sanctions_level=0.4, international_support=0.6),
  list(territory_controlled=0.00, military_balance=-0.10, crisis_level=9, sanctions_level=0.3, international_support=0.4),
  list(territory_controlled=0.07, military_balance=-0.20, crisis_level=3, sanctions_level=0.2, international_support=0.7)
)

for (tc in test_cases) {
  preset <- map_scenario_to_preset(tc)
  ctx <- get_preset_context(preset, tc)
  cat(sprintf("Params: terr=%.2f bal=%+.2f crisis=%.0f sanc=%.1f supp=%.1f\n",
    tc[["territory_controlled"]], tc[["military_balance"]], tc[["crisis_level"]],
    tc[["sanctions_level"]], tc[["international_support"]]))
  cat(sprintf("Preset: %s\n", preset))
  cat(sprintf("Situation:\n  %s\n", substr(ctx$situation_summary, 1, 300)))
  cat(sprintf("Events: %s\n\n", paste(ctx$recent_events, collapse=" | ")))
}

cat("Done.\n")
