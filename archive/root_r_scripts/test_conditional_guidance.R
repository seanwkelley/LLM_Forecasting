# Quick test: 2 contrasting scenarios to verify conditional guidance
# Scenario A: low crisis stalemate (should get cautious intelligence, economic stockpiling)
# Scenario B: high crisis total war (should get aggressive intelligence, economic warfare)
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

source_env <- new.env(parent = globalenv())
exprs <- parse("generate_multiscenario_dataset.R")
for (expr in exprs) {
  expr_text <- deparse(expr)
  if (any(grepl("<-\\s*function", expr_text)) || any(grepl("^library\\(", expr_text))) {
    eval(expr, envir = source_env)
  }
}
for (fn_name in c("generate_scenario_parameters", "run_single_scenario_simulation",
                   "extract_ground_truth_from_state", "map_scenario_to_preset", "get_preset_context")) {
  if (exists(fn_name, envir = source_env)) {
    assign(fn_name, get(fn_name, envir = source_env), envir = globalenv())
  }
}

Sys.setenv(SKIP_POST_ACTION_DISCUSSIONS = "1")

api_key <- Sys.getenv("OPENROUTER_API_KEY")
if (api_key == "") stop("OPENROUTER_API_KEY not set")

enhanced_agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(major_power = "Novaris", small_power = "Tethys", external = "External")
)

test_scenarios <- data.frame(
  scenario_id = c("test_calm_stalemate", "test_total_war"),
  territory_controlled = c(0.10, 0.40),
  military_balance = c(0.05, -0.35),
  sanctions_level = c(0.15, 0.75),
  international_support = c(0.45, 0.80),
  crisis_level = c(3, 10),
  novaris_gdp = c(85, 85),
  tethys_gdp = c(22, 22),
  preset = c("stalemate", "high_intensity"),
  stringsAsFactors = FALSE
)
test_scenarios$gdp_ratio <- test_scenarios$tethys_gdp / test_scenarios$novaris_gdp
test_scenarios$momentum <- ifelse(test_scenarios$territory_controlled < 0.1, 0,
                                   ifelse(test_scenarios$territory_controlled > 0.25, 0.2, 0.1))

output_dir <- "outputs/test_conditional"
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "temp"), recursive = TRUE, showWarnings = FALSE)

cat(rep("=", 70), "\n", sep = "")
cat("CONDITIONAL GUIDANCE TEST\n")
cat(rep("=", 70), "\n\n", sep = "")

for (i in 1:2) {
  scenario_row <- test_scenarios[i, ]
  cat(sprintf("\n%s\n", paste(rep("=", 60), collapse = "")))
  cat(sprintf("SCENARIO: %s [%s]\n", scenario_row$scenario_id, scenario_row$preset))
  cat(sprintf("  Territory: %.0f%% | Balance: %+.2f | Sanctions: %.0f%% | Support: %.0f%% | Crisis: %.1f\n",
              scenario_row$territory_controlled * 100,
              scenario_row$military_balance,
              scenario_row$sanctions_level * 100,
              scenario_row$international_support * 100,
              scenario_row$crisis_level))
  cat(sprintf("%s\n\n", paste(rep("=", 60), collapse = "")))

  temp_assessment <- file.path(output_dir, "temp", "assessments.csv")
  if (file.exists(temp_assessment)) file.remove(temp_assessment)

  result <- run_single_scenario_simulation(
    scenario_params = scenario_row,
    agents = enhanced_agents,
    api_key = api_key
  )

  if (result$success) {
    cat(sprintf("\n  Collapse probability: %.3f\n", result$ground_truth$collapse_probability))
  } else {
    cat(sprintf("\n  FAILED: %s\n", result$error))
  }
}

cat("\nDone.\n")
