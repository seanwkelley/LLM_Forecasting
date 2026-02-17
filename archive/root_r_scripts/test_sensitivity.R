# Test Parameter Sensitivity After Prompt Changes
# ================================================
# Runs 3 contrasting 1-period scenarios to check if agents
# now produce different actions for different parameter values.

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
cat("PARAMETER SENSITIVITY TEST\n")
cat("Testing 3 contrasting scenarios to check agent sensitivity\n")
cat(rep("=", 70), "\n\n")

# Check API key
api_key <- Sys.getenv("OPENROUTER_API_KEY")
if (api_key == "") {
  stop("OPENROUTER_API_KEY environment variable not set")
}

# Define 3 contrasting scenarios
test_scenarios <- list(
  low_threat = list(
    scenario_id = "test_low",
    territory_controlled = 0.02,    # Almost no territory lost
    military_balance = 0.08,        # Slightly favors Tethys
    sanctions_level = 0.10,         # Minimal sanctions
    international_support = 0.85,   # Strong support
    crisis_level = 3,               # Low crisis
    novaris_gdp = 340,
    tethys_gdp = 45,
    momentum = -0.1                 # Slightly favors defender
  ),
  medium_threat = list(
    scenario_id = "test_medium",
    territory_controlled = 0.20,    # 20% territory lost
    military_balance = -0.10,       # Slightly favors Novaris
    sanctions_level = 0.40,         # Moderate sanctions
    international_support = 0.55,   # Moderate support
    crisis_level = 6,               # Medium crisis
    novaris_gdp = 340,
    tethys_gdp = 45,
    momentum = 0.1                  # Slightly favors aggressor
  ),
  high_threat = list(
    scenario_id = "test_high",
    territory_controlled = 0.38,    # Major territory lost
    military_balance = -0.28,       # Strongly favors Novaris
    sanctions_level = 0.75,         # Severe sanctions
    international_support = 0.35,   # Weak support
    crisis_level = 9,               # High crisis
    novaris_gdp = 340,
    tethys_gdp = 45,
    momentum = 0.4                  # Strong aggressor momentum
  )
)

# Create agents once (shared across scenarios)
cat("Creating enhanced cognitive agents...\n\n")
enhanced_agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(
    major_power = "Novaris",
    small_power = "Tethys",
    external = "External"
  )
)

# Output directory
test_dir <- "outputs/sensitivity_test"
dir.create(file.path(test_dir, "temp"), recursive = TRUE, showWarnings = FALSE)

# Run each scenario
results <- list()

for (scenario_name in names(test_scenarios)) {
  params <- test_scenarios[[scenario_name]]

  cat(rep("-", 60), "\n", sep="")
  cat(sprintf("SCENARIO: %s\n", toupper(scenario_name)))
  cat(sprintf("  Territory lost: %.0f%% | Military balance: %+.2f | Sanctions: %.0f%%\n",
              params$territory_controlled * 100,
              params$military_balance,
              params$sanctions_level * 100))
  cat(sprintf("  Int'l support: %.0f%% | Crisis level: %d/10 | Momentum: %+.1f\n",
              params$international_support * 100,
              params$crisis_level,
              params$momentum))
  cat(rep("-", 60), "\n")

  # Create state
  state <- list(
    simulation_id = params$scenario_id,
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
      military_balance = params$military_balance,
      sanctions_level = params$sanctions_level,
      international_support = params$international_support,
      crisis_level = params$crisis_level,
      territory_controlled = params$territory_controlled,
      nuclear_used = FALSE,
      momentum = params$momentum,
      consecutive_wins_defender = 0,
      consecutive_wins_aggressor = ifelse(params$territory_controlled > 0.1, 1, 0)
    ),
    faction_capabilities = list(
      major_power_military = 1.0,
      small_power_military = 0.6,
      major_power_gdp = params$novaris_gdp,
      small_power_gdp = params$tethys_gdp
    ),
    action_decisions = list(),
    action_results = list(),
    pre_action_coordination = list()
  )
  class(state) <- c("simulation_state", "list")

  # Run 1 period
  tryCatch({
    final_state <- run_simulation_period_with_actions(
      state = state,
      period = 1,
      api_key = api_key,
      data_dir = "data",
      output_dir = file.path(test_dir, "temp")
    )

    # Extract results
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

    collapse_prob <- NA
    if (length(final_state$assessments_history) > 0) {
      assessment <- final_state$assessments_history[[1]]
      collapse_prob <- if (!is.null(assessment$probability)) assessment$probability else NA
    }

    results[[scenario_name]] <- list(
      novaris = novaris_actions,
      tethys = tethys_actions,
      collapse_prob = collapse_prob,
      final_crisis = final_state$scenario_state$crisis_level,
      final_territory = final_state$scenario_state$territory_controlled,
      final_balance = final_state$scenario_state$military_balance
    )

    # Save interaction files
    scenario_out <- file.path(test_dir, params$scenario_id)
    dir.create(scenario_out, recursive = TRUE, showWarnings = FALSE)
    interaction_files <- list.files("outputs/interactions", pattern = "^period_01_", full.names = TRUE)
    if (length(interaction_files) > 0) {
      file.copy(interaction_files, scenario_out, overwrite = TRUE)
    }

    cat(sprintf("\n  RESULT: %s\n", toupper(scenario_name)))
    cat(sprintf("    Collapse probability: %.3f\n", collapse_prob))
    cat(sprintf("    Novaris actions (%d): %s\n", length(novaris_actions), paste(novaris_actions, collapse=", ")))
    cat(sprintf("    Tethys actions (%d): %s\n", length(tethys_actions), paste(tethys_actions, collapse=", ")))
    cat(sprintf("    Final territory: %.3f | Final balance: %.3f | Final crisis: %.1f\n\n",
                final_state$scenario_state$territory_controlled,
                final_state$scenario_state$military_balance,
                final_state$scenario_state$crisis_level))

  }, error = function(e) {
    cat(sprintf("\n  ERROR: %s\n\n", e$message))
    results[[scenario_name]] <<- list(error = e$message)
  })
}

# Print comparison summary
cat(rep("=", 70), "\n", sep="")
cat("COMPARISON SUMMARY\n")
cat(rep("=", 70), "\n\n")

cat(sprintf("%-15s %-12s %-50s\n", "SCENARIO", "P(COLLAPSE)", "NOVARIS ACTIONS"))
cat(rep("-", 70), "\n", sep="")
for (name in names(results)) {
  r <- results[[name]]
  if (is.null(r$error)) {
    cat(sprintf("%-15s %-12.3f %s\n", name, r$collapse_prob, paste(r$novaris, collapse=", ")))
  } else {
    cat(sprintf("%-15s ERROR: %s\n", name, r$error))
  }
}

cat("\n")
cat(sprintf("%-15s %-12s %-50s\n", "SCENARIO", "P(COLLAPSE)", "TETHYS ACTIONS"))
cat(rep("-", 70), "\n", sep="")
for (name in names(results)) {
  r <- results[[name]]
  if (is.null(r$error)) {
    cat(sprintf("%-15s %-12.3f %s\n", name, r$collapse_prob, paste(r$tethys, collapse=", ")))
  } else {
    cat(sprintf("%-15s ERROR: %s\n", name, r$error))
  }
}

# Check if actions differ across scenarios
cat("\n")
if (length(results) == 3 && all(sapply(results, function(r) is.null(r$error)))) {
  nov_low <- sort(results$low_threat$novaris)
  nov_high <- sort(results$high_threat$novaris)
  teth_low <- sort(results$low_threat$tethys)
  teth_high <- sort(results$high_threat$tethys)

  nov_overlap <- length(intersect(nov_low, nov_high)) / max(length(union(nov_low, nov_high)), 1)
  teth_overlap <- length(intersect(teth_low, teth_high)) / max(length(union(teth_low, teth_high)), 1)

  cat(sprintf("Novaris action overlap (low vs high): %.0f%% (%d shared of %d unique)\n",
              nov_overlap * 100,
              length(intersect(nov_low, nov_high)),
              length(union(nov_low, nov_high))))
  cat(sprintf("Tethys action overlap (low vs high):  %.0f%% (%d shared of %d unique)\n",
              teth_overlap * 100,
              length(intersect(teth_low, teth_high)),
              length(union(teth_low, teth_high))))

  prob_range <- results$high_threat$collapse_prob - results$low_threat$collapse_prob
  cat(sprintf("Collapse probability range: %.3f (low=%.3f, high=%.3f)\n", prob_range,
              results$low_threat$collapse_prob, results$high_threat$collapse_prob))

  if (nov_overlap < 0.5 && teth_overlap < 0.5) {
    cat("\n>>> GOOD: Actions are substantially different across scenarios!\n")
  } else if (nov_overlap < 0.75 || teth_overlap < 0.75) {
    cat("\n>>> MODERATE: Some differentiation but still significant overlap.\n")
  } else {
    cat("\n>>> POOR: Actions are still very similar across scenarios.\n")
  }
}

cat("\nDone.\n")
