# Quick test: Run 2 scenarios with very different parameters to verify
# domain experts respond differently to events and parameters.
#
# Scenario A: Low crisis, strong defender, no sanctions (dovish conditions)
# Scenario B: High crisis, weak defender, heavy sanctions (hawkish conditions)
#
# Usage: Rscript test_event_differentiation.R

library(jsonlite)
library(uuid)

source("config.R")
source("src/integrated_agent_system.R")
source("src/agent_system.R")
source("src/event_generator.R")
source("src/interaction_engine.R")
source("src/aggregator.R")
source("src/state_manager.R")
source("src/agent_decision.R")
source("src/action_execution.R")
source("src/multi_action_system.R")
source("src/multi_action_effects.R")
source("src/simulation_with_actions.R")

# Source generation functions
source_env <- new.env(parent = globalenv())
exprs <- parse("generate_multiscenario_dataset.R")
for (expr in exprs) {
  expr_text <- deparse(expr)
  if (any(grepl("<-\\s*function", expr_text)) || any(grepl("^library\\(", expr_text))) {
    eval(expr, envir = source_env)
  }
}
for (fn_name in c("generate_scenario_parameters", "run_single_scenario_simulation", "extract_ground_truth_from_state")) {
  if (exists(fn_name, envir = source_env)) {
    assign(fn_name, get(fn_name, envir = source_env), envir = globalenv())
  }
}

api_key <- Sys.getenv("OPENROUTER_API_KEY")
if (api_key == "") stop("OPENROUTER_API_KEY not set")

# Create agents
enhanced_agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(
    major_power = "Novaris",
    small_power = "Tethys",
    external = "External"
  )
)

# Define two contrasting scenarios manually
test_scenarios <- data.frame(
  scenario_id = c("test_dovish", "test_hawkish"),
  territory_controlled = c(0.05, 0.35),        # 5% vs 35% territory lost
  military_balance = c(0.08, -0.28),            # strong defender vs weak defender
  sanctions_level = c(0.05, 0.70),              # minimal vs heavy sanctions
  international_support = c(0.85, 0.35),        # strong vs weak support
  crisis_level = c(3.0, 9.5),                   # low vs high crisis
  major_gdp = c(1800, 1800),
  small_gdp = c(350, 350),
  stringsAsFactors = FALSE
)

output_dir <- "outputs/test_differentiation"
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "temp"), recursive = TRUE, showWarnings = FALSE)

cat(rep("=", 70), "\n", sep = "")
cat("EVENT DIFFERENTIATION TEST\n")
cat("Scenario A: DOVISH (low crisis, strong position)\n")
cat("Scenario B: HAWKISH (high crisis, weak position)\n")
cat(rep("=", 70), "\n\n", sep = "")

for (i in 1:2) {
  scenario_row <- test_scenarios[i, ]
  cat(sprintf("\n%s\n", paste(rep("=", 60), collapse = "")))
  cat(sprintf("SCENARIO: %s\n", scenario_row$scenario_id))
  cat(sprintf("  Territory: %.0f%% | Balance: %+.2f | Sanctions: %.0f%% | Support: %.0f%% | Crisis: %.1f\n",
              scenario_row$territory_controlled * 100,
              scenario_row$military_balance,
              scenario_row$sanctions_level * 100,
              scenario_row$international_support * 100,
              scenario_row$crisis_level))
  cat(sprintf("%s\n\n", paste(rep("=", 60), collapse = "")))

  # Clean temp
  temp_assessment <- file.path(output_dir, "temp", "assessments.csv")
  if (file.exists(temp_assessment)) file.remove(temp_assessment)

  result <- run_single_scenario_simulation(
    scenario_params = scenario_row,
    agents = enhanced_agents,
    api_key = api_key
  )

  if (result$success) {
    cat(sprintf("\n  Collapse probability: %.3f\n", result$ground_truth$collapse_probability))

    # Save state
    state_file <- file.path(output_dir, sprintf("%s.rds", scenario_row$scenario_id))
    saveRDS(result$state, state_file)

    # Copy interaction CSVs
    scenario_dir <- file.path(output_dir, scenario_row$scenario_id)
    dir.create(scenario_dir, recursive = TRUE, showWarnings = FALSE)
    interaction_files <- list.files("outputs/interactions", pattern = "^period_01_", full.names = TRUE)
    if (length(interaction_files) > 0) {
      file.copy(interaction_files, scenario_dir, overwrite = TRUE)
    }
  } else {
    cat(sprintf("\n  FAILED: %s\n", result$error))
  }
}

# Compare proposals side by side
cat("\n\n")
cat(rep("=", 70), "\n", sep = "")
cat("COMPARISON OF PROPOSALS\n")
cat(rep("=", 70), "\n\n", sep = "")

for (sc_id in test_scenarios$scenario_id) {
  pf <- file.path(output_dir, sc_id, "period_01_proposals.csv")
  if (file.exists(pf)) {
    props <- read.csv(pf)
    cat(sprintf("\n--- %s ---\n", toupper(sc_id)))
    for (faction in unique(props$faction_name)) {
      cat(sprintf("  %s:\n", faction))
      fp <- props[props$faction_name == faction & props$priority == "primary", ]
      for (j in 1:nrow(fp)) {
        cat(sprintf("    %s: %s\n", fp$domain[j], fp$proposed_action[j]))
      }
    }
  }
}

cat("\nDone.\n")
