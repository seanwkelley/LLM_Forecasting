# Test stratified scenario generation
library(jsonlite)
source("config.R")

source_env <- new.env(parent = globalenv())
exprs <- parse("generate_multiscenario_dataset.R")
for (expr in exprs) {
  expr_text <- deparse(expr)
  if (any(grepl("<-\\s*function", expr_text)) || any(grepl("^library\\(", expr_text))) {
    eval(expr, envir = source_env)
  }
}
for (fn_name in c("generate_scenario_parameters", "map_scenario_to_preset", "get_preset_context")) {
  if (exists(fn_name, envir = source_env)) {
    assign(fn_name, get(fn_name, envir = source_env), envir = globalenv())
  }
}

scenarios <- generate_scenario_parameters(n_scenarios = 50, seed = 42)
cat("\nFirst 10 scenarios:\n")
for (i in 1:min(10, nrow(scenarios))) {
  s <- scenarios[i, ]
  preset <- map_scenario_to_preset(s)
  cat(sprintf("  %s: preset=%-16s terr=%.2f bal=%+.2f crisis=%2.0f sanc=%.2f supp=%.2f\n",
    s$scenario_id, preset, s$territory_controlled, s$military_balance,
    s$crisis_level, s$sanctions_level, s$international_support))
}

cat("\nPreset column matches mapping?\n")
mismatches <- 0
for (i in 1:nrow(scenarios)) {
  mapped <- map_scenario_to_preset(scenarios[i, ])
  if (mapped != scenarios$preset[i]) {
    cat(sprintf("  MISMATCH: %s preset=%s mapped=%s\n", scenarios$scenario_id[i], scenarios$preset[i], mapped))
    mismatches <- mismatches + 1
  }
}
if (mismatches == 0) cat("  All match.\n")

cat("\nDone.\n")
