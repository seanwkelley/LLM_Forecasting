# Run ONLY scenario 050 to reach 50 total
# =========================================

library(jsonlite)
library(uuid)

# Load configuration and simulation code
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

cat(rep("=", 70), "\n", sep="")
cat("RUNNING SCENARIO 050 (to reach 50 total)\n")
cat(rep("=", 70), "\n\n")

# Check API key
api_key <- Sys.getenv("OPENROUTER_API_KEY")
if (api_key == "") {
  stop("OPENROUTER_API_KEY environment variable not set")
}

output_dir <- "outputs/multiscenario"
dir.create(file.path(output_dir, "temp"), recursive = TRUE, showWarnings = FALSE)

# Check if scenario 050 already exists
scenario_dir <- file.path(output_dir, "scenario_050")
state_file <- file.path(output_dir, "scenario_050.rds")
if (file.exists(state_file) && dir.exists(scenario_dir)) {
  interaction_files <- list.files(scenario_dir, pattern = "\\.csv$")
  if (length(interaction_files) >= 3) {
    cat("Scenario 050 already completed! Nothing to do.\n")
    q(save = "no")
  }
}

# Load scenario parameters (already generated with seed=42)
scenarios <- read.csv(file.path(output_dir, "scenarios.csv"), stringsAsFactors = FALSE)
scenario_row <- scenarios[scenarios$scenario_id == "scenario_050", ]

if (nrow(scenario_row) == 0) {
  stop("scenario_050 not found in scenarios.csv")
}

cat(sprintf("Scenario 050 parameters:\n"))
cat(sprintf("  Territory: %.1f%% | Balance: %.2f | Sanctions: %.1f%% | Support: %.1f%%\n",
            scenario_row$territory_controlled * 100,
            scenario_row$military_balance,
            scenario_row$sanctions_level * 100,
            scenario_row$international_support * 100))
cat(sprintf("  Crisis level: %d | Novaris GDP: %.1f | Tethys GDP: %.1f | Momentum: %.1f\n\n",
            scenario_row$crisis_level,
            scenario_row$novaris_gdp,
            scenario_row$tethys_gdp,
            scenario_row$momentum))

# Create enhanced agents
cat("Creating enhanced cognitive agents...\n")
enhanced_agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(
    major_power = "Novaris",
    small_power = "Tethys",
    external = "External"
  )
)

# Create custom initial state from parameters
state <- list(
  simulation_id = "scenario_050",
  start_time = Sys.time(),
  current_period = 0,
  scenario_preset = "custom",
  agents = enhanced_agents,
  events_history = list(),
  interactions_history = list(),
  assessments_history = list(),
  scenario_state = list(
    current_day = 0,
    situation_summary = SCENARIO_PRESETS$pre_invasion$situation,
    recent_events = c(
      "Major power has mobilized forces along border",
      "Smaller power activated defense protocols",
      "International sanctions implemented",
      "Allied nations monitoring situation"
    ),
    military_balance = scenario_row$military_balance,
    sanctions_level = scenario_row$sanctions_level,
    international_support = scenario_row$international_support,
    crisis_level = scenario_row$crisis_level,
    territory_controlled = scenario_row$territory_controlled,
    nuclear_used = FALSE,
    momentum = scenario_row$momentum,
    consecutive_wins_defender = 0,
    consecutive_wins_aggressor = ifelse(scenario_row$territory_controlled > 0.1, 1, 0)
  ),
  faction_capabilities = list(
    major_power_military = 1.0,
    small_power_military = 0.6,
    major_power_gdp = scenario_row$novaris_gdp,
    small_power_gdp = scenario_row$tethys_gdp
  ),
  action_decisions = list(),
  action_results = list(),
  pre_action_coordination = list()
)

class(state) <- c("simulation_state", "list")

# Run simulation for period 1
cat("\n--- Simulating scenario_050 ---\n")
tryCatch({
  final_state <- run_simulation_period_with_actions(
    state = state,
    period = 1,
    api_key = api_key,
    data_dir = "data",
    output_dir = "outputs/multiscenario/temp"
  )

  # Save state
  saveRDS(final_state, state_file)

  # Copy interaction files
  dir.create(scenario_dir, recursive = TRUE, showWarnings = FALSE)
  interaction_files <- list.files("outputs/interactions", pattern = "^period_01_", full.names = TRUE)
  if (length(interaction_files) > 0) {
    file.copy(interaction_files, scenario_dir, overwrite = TRUE)
  }
  assessment_file <- file.path(output_dir, "temp", "assessments.csv")
  if (file.exists(assessment_file)) {
    file.copy(assessment_file, scenario_dir, overwrite = TRUE)
  }

  # Extract ground truth
  assessment <- final_state$assessments_history[[1]]
  collapse_prob <- if (!is.null(assessment$probability)) assessment$probability else NA

  novaris_actions <- c()
  tethys_actions <- c()
  if (!is.null(final_state$action_decisions[[1]])) {
    if (!is.null(final_state$action_decisions[[1]]$major_power)) {
      decision <- final_state$action_decisions[[1]]$major_power
      if (!is.null(decision$approved_actions)) {
        novaris_actions <- sapply(decision$approved_actions, function(a) a$action)
      }
    }
    if (!is.null(final_state$action_decisions[[1]]$small_power)) {
      decision <- final_state$action_decisions[[1]]$small_power
      if (!is.null(decision$approved_actions)) {
        tethys_actions <- sapply(decision$approved_actions, function(a) a$action)
      }
    }
  }

  cat(sprintf("\n=== SCENARIO 050 COMPLETE ===\n"))
  cat(sprintf("  Collapse probability: %.3f\n", collapse_prob))
  cat(sprintf("  Novaris actions (%d): %s\n", length(novaris_actions), paste(novaris_actions, collapse=", ")))
  cat(sprintf("  Tethys actions (%d): %s\n", length(tethys_actions), paste(tethys_actions, collapse=", ")))
  cat(sprintf("  Final territory: %.3f\n", final_state$scenario_state$territory_controlled))
  cat(sprintf("  Final military balance: %.3f\n", final_state$scenario_state$military_balance))
  cat(sprintf("  Final crisis level: %.1f\n", final_state$scenario_state$crisis_level))

  # Update ground_truth.csv
  gt <- read.csv(file.path(output_dir, "ground_truth.csv"), stringsAsFactors = FALSE)
  new_row <- data.frame(
    scenario_id = "scenario_050",
    period = 1,
    collapse_probability = collapse_prob,
    novaris_actions = paste(novaris_actions, collapse = "|"),
    tethys_actions = paste(tethys_actions, collapse = "|"),
    n_novaris_actions = length(novaris_actions),
    n_tethys_actions = length(tethys_actions),
    final_territory = final_state$scenario_state$territory_controlled,
    final_military_balance = final_state$scenario_state$military_balance,
    final_crisis_level = final_state$scenario_state$crisis_level,
    final_sanctions = final_state$scenario_state$sanctions_level,
    final_support = final_state$scenario_state$international_support,
    stringsAsFactors = FALSE
  )
  gt <- rbind(gt, new_row)
  write.csv(gt, file.path(output_dir, "ground_truth.csv"), row.names = FALSE)
  cat(sprintf("\nUpdated ground_truth.csv (now %d rows)\n", nrow(gt)))

  cat(sprintf("\nSaved %d interaction files + assessment to %s\n",
              length(interaction_files), scenario_dir))

}, error = function(e) {
  cat(sprintf("\nERROR: Simulation failed: %s\n", e$message))
  cat(sprintf("Traceback:\n"))
  traceback()
})

cat("\nDone.\n")
