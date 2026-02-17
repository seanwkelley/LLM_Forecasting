# Generate Multi-Scenario Dataset for Forecasting Experiment
# ===========================================================
#
# Creates 100 parametrically varied scenarios and runs simulation for 1 period each.
# Outputs ground truth data for forecasting experiments.
#
# Usage:
#   Rscript generate_multiscenario_dataset.R
#
# Outputs:
#   - outputs/multiscenario/scenarios.csv (100 scenarios with initial parameters)
#   - outputs/multiscenario/ground_truth.csv (actions, outcomes per scenario)
#   - outputs/multiscenario/scenario_*.rds (detailed simulation state per scenario)

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
cat("MULTI-SCENARIO DATASET GENERATION\n")
cat(rep("=", 70), "\n\n", sep="")

# ============================================================
# SCENARIO GENERATION
# ============================================================

#' Generate N scenarios with parametric variation
#'
#' Varies key parameters while keeping Tethys-Novaris backstory constant.
#' Uses Latin Hypercube Sampling for good coverage.
#'
#' @param n_scenarios Number of scenarios to generate
#' @param seed Random seed for reproducibility
#' @return Data frame with scenario parameters
generate_scenario_parameters <- function(n_scenarios = 100, seed = 42) {
  set.seed(seed)

  cat(sprintf("Generating %d scenario parameter sets (stratified by preset)...\n", n_scenarios))

  # Stratified sampling: divide scenarios evenly across 5 narrative presets,
  # with LHS within each stratum for space-filling coverage.
  # Each preset has parameter sub-ranges that produce coherent scenarios.

  preset_ranges <- list(
    pre_invasion = list(
      territory = c(0.00, 0.03),    # No territory captured yet
      balance   = c(-0.20, 0.10),   # Could favor either side
      sanctions = c(0.00, 0.30),    # Initial or no sanctions
      support   = c(0.30, 0.70),    # Uncertain international response
      crisis    = c(3, 8)           # Tension building, could be high
    ),
    low_intensity = list(
      territory = c(0.03, 0.10),    # Small territorial gains
      balance   = c(-0.20, 0.05),   # Slight aggressor advantage
      sanctions = c(0.10, 0.50),    # Targeted sanctions
      support   = c(0.40, 0.80),    # Growing support for defender
      crisis    = c(3, 7)           # Low-moderate crisis
    ),
    medium_intensity = list(
      territory = c(0.10, 0.30),    # Significant territory taken
      balance   = c(-0.35, -0.05),  # Aggressor has advantage
      sanctions = c(0.30, 0.70),    # Substantial sanctions
      support   = c(0.50, 0.85),    # Moderate-strong support
      crisis    = c(5, 9)           # Elevated crisis
    ),
    high_intensity = list(
      territory = c(0.25, 0.45),    # Major territory captured
      balance   = c(-0.40, -0.10),  # Strong aggressor advantage
      sanctions = c(0.50, 0.85),    # Heavy sanctions
      support   = c(0.60, 0.90),    # Strong international response
      crisis    = c(8, 10)          # Extreme crisis
    ),
    stalemate = list(
      territory = c(0.05, 0.25),    # Moderate territory held
      balance   = c(-0.15, 0.15),   # Roughly balanced
      sanctions = c(0.30, 0.70),    # Sustained sanctions
      support   = c(0.40, 0.80),    # Variable support
      crisis    = c(3, 7)           # Moderate — grinding not escalating
    )
  )

  preset_names <- names(preset_ranges)
  n_presets <- length(preset_names)
  per_preset <- ceiling(n_scenarios / n_presets)

  all_scenarios <- list()
  idx <- 1

  for (preset_name in preset_names) {
    pr <- preset_ranges[[preset_name]]
    n_this <- min(per_preset, n_scenarios - idx + 1)
    if (n_this <= 0) break

    if (requireNamespace("lhs", quietly = TRUE)) {
      lhs_design <- lhs::randomLHS(n_this, 7)
    } else {
      lhs_design <- matrix(runif(n_this * 7), ncol = 7)
    }

    stratum <- data.frame(
      scenario_id = sprintf("scenario_%03d", idx:(idx + n_this - 1)),
      territory_controlled = lhs_design[, 1] * (pr$territory[2] - pr$territory[1]) + pr$territory[1],
      military_balance     = lhs_design[, 2] * (pr$balance[2] - pr$balance[1]) + pr$balance[1],
      sanctions_level      = lhs_design[, 3] * (pr$sanctions[2] - pr$sanctions[1]) + pr$sanctions[1],
      international_support = lhs_design[, 4] * (pr$support[2] - pr$support[1]) + pr$support[1],
      crisis_level         = round(lhs_design[, 5] * (pr$crisis[2] - pr$crisis[1]) + pr$crisis[1]),
      novaris_gdp          = lhs_design[, 6] * 30 + 70,   # 70-100B (same across presets)
      tethys_gdp           = lhs_design[, 7] * 15 + 15,   # 15-30B  (same across presets)
      preset               = preset_name,
      stringsAsFactors = FALSE
    )

    all_scenarios[[preset_name]] <- stratum
    idx <- idx + n_this
  }

  scenarios <- do.call(rbind, all_scenarios)
  rownames(scenarios) <- NULL

  # Shuffle order so presets are interleaved (avoids running all of one type first)
  scenarios <- scenarios[sample(nrow(scenarios)), ]
  scenarios$scenario_id <- sprintf("scenario_%03d", 1:nrow(scenarios))

  # Add derived parameters
  scenarios$gdp_ratio <- scenarios$tethys_gdp / scenarios$novaris_gdp
  scenarios$momentum <- ifelse(scenarios$territory_controlled < 0.1, 0,
                               ifelse(scenarios$territory_controlled > 0.25, 0.2, 0.1))

  cat(sprintf("Generated %d scenarios across %d presets\n", nrow(scenarios), n_presets))
  cat("  Preset distribution:\n")
  print(table(scenarios$preset))
  cat(sprintf("  Territory range: %.1f%% - %.1f%%\n",
              min(scenarios$territory_controlled)*100,
              max(scenarios$territory_controlled)*100))
  cat(sprintf("  Military balance range: %.2f - %+.2f\n",
              min(scenarios$military_balance),
              max(scenarios$military_balance)))
  cat(sprintf("  Sanctions range: %.1f%% - %.1f%%\n",
              min(scenarios$sanctions_level)*100,
              max(scenarios$sanctions_level)*100))
  cat(sprintf("  Support range: %.1f%% - %.1f%%\n",
              min(scenarios$international_support)*100,
              max(scenarios$international_support)*100))
  cat(sprintf("  Crisis range: %d - %d\n\n",
              min(scenarios$crisis_level),
              max(scenarios$crisis_level)))

  return(scenarios)
}


# ============================================================
# SCENARIO PRESET MAPPING
# ============================================================

#' Map scenario parameters to the most appropriate qualitative preset
#'
#' Uses crisis_level, territory_controlled, and military_balance to classify
#' each scenario into a narrative category. This ensures agents see a
#' qualitative description that matches the quantitative parameters.
#'
#' @param scenario_params Single row from scenario data frame
#' @return Name of the matching preset from SCENARIO_PRESETS
map_scenario_to_preset <- function(scenario_params) {
  # Use explicit preset column if available (from stratified generation)
  if (!is.null(scenario_params$preset) && !is.na(scenario_params$preset) &&
      nchar(as.character(scenario_params$preset)) > 0) {
    return(as.character(scenario_params$preset))
  }

  territory <- scenario_params$territory_controlled
  balance <- scenario_params$military_balance
  crisis <- scenario_params$crisis_level

  # Pre-invasion: very low territory (regardless of crisis — no invasion has occurred)
  if (territory < 0.03) {
    return("pre_invasion")
  }

  # Total war: high territory captured AND high crisis
  if (territory >= 0.20 && crisis >= 8) {
    return("high_intensity")
  }

  # Stalemate: moderate territory, balanced military, moderate crisis
  if (territory >= 0.05 && territory <= 0.20 && abs(balance) < 0.15 && crisis <= 7) {
    return("stalemate")
  }

  # Full-scale invasion: significant territory taken, aggressor advantage
  if (territory >= 0.08 && (balance < -0.10 || crisis >= 8)) {
    return("medium_intensity")
  }

  # Low intensity: some territory taken but limited conflict
  if (territory >= 0.03 && territory < 0.12) {
    return("low_intensity")
  }

  # High territory but moderate crisis — stalemate after major push
  if (territory >= 0.12 && crisis < 8) {
    return("stalemate")
  }

  # Default: medium intensity for ambiguous cases
  return("medium_intensity")
}

#' Get situation text and initial events for a preset, customized with params
#'
#' @param preset_name Name of the preset
#' @param scenario_params Scenario parameter row
#' @return List with situation_summary and recent_events
get_preset_context <- function(preset_name, scenario_params) {
  preset <- SCENARIO_PRESETS[[preset_name]]

  territory_pct <- round(scenario_params$territory_controlled * 100, 1)
  balance_desc <- if (scenario_params$military_balance > 0.05) {
    "Tethys holds a defensive advantage"
  } else if (scenario_params$military_balance < -0.15) {
    "Novaris holds significant military advantage"
  } else if (scenario_params$military_balance < -0.05) {
    "Novaris holds moderate military advantage"
  } else {
    "Military forces are roughly balanced"
  }

  sanctions_desc <- if (scenario_params$sanctions_level > 0.6) {
    "Comprehensive international sanctions in effect"
  } else if (scenario_params$sanctions_level > 0.3) {
    "Targeted sanctions imposed on key sectors"
  } else if (scenario_params$sanctions_level > 0.1) {
    "Limited initial sanctions in place"
  } else {
    "Minimal economic restrictions"
  }

  support_desc <- if (scenario_params$international_support > 0.7) {
    "Strong international coalition supporting Tethys"
  } else if (scenario_params$international_support > 0.5) {
    "Moderate international support for Tethys"
  } else {
    "Limited international backing for Tethys"
  }

  # Compose situation: preset narrative + parameter-specific context
  situation <- sprintf(
    "%s\n\nCURRENT CONDITIONS: %s controls %.1f%% of Tethyan territory. %s. %s. %s. Crisis intensity: %.0f/10.",
    preset$situation,
    "Novaris", territory_pct,
    balance_desc,
    sanctions_desc,
    support_desc,
    scenario_params$crisis_level
  )

  # Preset-appropriate initial events
  events <- switch(preset_name,
    pre_invasion = c(
      "Major power has mobilized forces along border",
      "Smaller power activated defense protocols",
      "Diplomatic channels remain open but strained",
      "International community monitoring situation"
    ),
    low_intensity = c(
      "Limited military operations along border regions",
      "Smaller power mobilizing defensive forces",
      "International sanctions being implemented",
      "Civilian displacement from border areas reported"
    ),
    medium_intensity = c(
      "Full-scale military operations underway across multiple fronts",
      "Smaller power mounting organized defensive campaign",
      "Emergency international sanctions imposed",
      "Significant civilian casualties and displacement"
    ),
    high_intensity = c(
      "Intense combat across all fronts with heavy casualties",
      "Major urban areas under siege or bombardment",
      "Maximum international sanctions and aid mobilization",
      "Humanitarian crisis escalating rapidly"
    ),
    stalemate = c(
      "Frontlines have stabilized after period of active combat",
      "Both sides consolidating positions and resupplying",
      "Diplomatic efforts underway but no breakthrough",
      "War of attrition affecting both economies"
    )
  )

  list(situation_summary = situation, recent_events = events)
}


# ============================================================
# SIMULATION RUNNER
# ============================================================

#' Run simulation for a single scenario (1 period only)
#'
#' @param scenario_params Single row from scenario data frame
#' @param agents Agent list from config
#' @param api_key OpenRouter API key
#' @return List with simulation results
run_single_scenario_simulation <- function(scenario_params, agents, api_key) {
  scenario_id <- scenario_params$scenario_id

  cat(sprintf("\n--- Simulating %s ---\n", scenario_id))
  cat(sprintf("  Territory: %.1f%% | Balance: %.2f | Sanctions: %.1f%% | Support: %.1f%%\n",
              scenario_params$territory_controlled * 100,
              scenario_params$military_balance,
              scenario_params$sanctions_level * 100,
              scenario_params$international_support * 100))

  # Map scenario to appropriate qualitative preset
  preset_name <- map_scenario_to_preset(scenario_params)
  preset_ctx <- get_preset_context(preset_name, scenario_params)
  cat(sprintf("  Preset: %s\n", preset_name))

  # Create custom initial state from parameters
  state <- list(
    simulation_id = scenario_id,
    start_time = Sys.time(),
    current_period = 0,
    scenario_preset = preset_name,
    agents = agents,
    events_history = list(),
    interactions_history = list(),
    assessments_history = list(),
    scenario_state = list(
      current_day = 0,
      situation_summary = preset_ctx$situation_summary,
      recent_events = preset_ctx$recent_events,
      military_balance = scenario_params$military_balance,
      sanctions_level = scenario_params$sanctions_level,
      international_support = scenario_params$international_support,
      crisis_level = scenario_params$crisis_level,
      territory_controlled = scenario_params$territory_controlled,
      nuclear_used = FALSE,
      momentum = scenario_params$momentum,
      consecutive_wins_defender = 0,
      consecutive_wins_aggressor = ifelse(scenario_params$territory_controlled > 0.1, 1, 0)
    ),
    faction_capabilities = list(
      major_power_military = 1.0,
      small_power_military = 0.6,
      major_power_gdp = scenario_params$novaris_gdp,
      small_power_gdp = scenario_params$tethys_gdp
    ),
    action_decisions = list(),
    action_results = list(),
    pre_action_coordination = list()
  )

  class(state) <- c("simulation_state", "list")

  # Run simulation for PERIOD 1 ONLY
  tryCatch({
    final_state <- run_simulation_period_with_actions(
      state = state,
      period = 1,
      api_key = api_key,
      data_dir = "data",
      output_dir = "outputs/multiscenario/temp"
    )

    # Extract ground truth data
    ground_truth <- extract_ground_truth_from_state(final_state, scenario_id)

    cat(sprintf("  ✓ Simulation complete\n"))
    cat(sprintf("    Collapse prob: %.3f\n", ground_truth$collapse_probability))
    cat(sprintf("    Novaris actions: %s\n", paste(ground_truth$novaris_actions, collapse=", ")))
    cat(sprintf("    Tethys actions: %s\n", paste(ground_truth$tethys_actions, collapse=", ")))

    return(list(
      success = TRUE,
      state = final_state,
      ground_truth = ground_truth
    ))

  }, error = function(e) {
    cat(sprintf("  ✗ Simulation failed: %s\n", e$message))
    return(list(
      success = FALSE,
      error = e$message,
      ground_truth = NULL
    ))
  })
}


#' Extract ground truth data from simulation state
#'
#' @param state Final simulation state
#' @param scenario_id Scenario identifier
#' @return Ground truth data frame row
extract_ground_truth_from_state <- function(state, scenario_id) {
  period <- 1

  # Extract collapse probability from aggregator assessment
  assessment <- state$assessments_history[[period]]
  collapse_prob <- if (!is.null(assessment$probability)) {
    assessment$probability
  } else {
    NA
  }

  # Extract actions
  novaris_actions <- c()
  tethys_actions <- c()

  if (!is.null(state$action_decisions[[period]])) {
    # Novaris (major_power)
    if (!is.null(state$action_decisions[[period]]$major_power)) {
      decision <- state$action_decisions[[period]]$major_power
      if (!is.null(decision$approved_actions)) {
        novaris_actions <- sapply(decision$approved_actions, function(a) a$action)
      } else if (!is.null(decision$action)) {
        novaris_actions <- decision$action
      }
    }

    # Tethys (small_power)
    if (!is.null(state$action_decisions[[period]]$small_power)) {
      decision <- state$action_decisions[[period]]$small_power
      if (!is.null(decision$approved_actions)) {
        tethys_actions <- sapply(decision$approved_actions, function(a) a$action)
      } else if (!is.null(decision$action)) {
        tethys_actions <- decision$action
      }
    }
  }

  # Extract final state
  final_state <- state$scenario_state

  return(list(
    scenario_id = scenario_id,
    period = period,
    collapse_probability = collapse_prob,
    novaris_actions = novaris_actions,
    tethys_actions = tethys_actions,
    n_novaris_actions = length(novaris_actions),
    n_tethys_actions = length(tethys_actions),
    final_territory = final_state$territory_controlled,
    final_military_balance = final_state$military_balance,
    final_crisis_level = final_state$crisis_level,
    final_sanctions = final_state$sanctions_level,
    final_support = final_state$international_support
  ))
}


# ============================================================
# MAIN EXECUTION
# ============================================================

main <- function() {
  # Check API key
  api_key <- Sys.getenv("OPENROUTER_API_KEY")
  if (api_key == "") {
    stop("OPENROUTER_API_KEY environment variable not set")
  }

  # Create output directory
  output_dir <- "outputs/multiscenario"
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(file.path(output_dir, "temp"), recursive = TRUE, showWarnings = FALSE)

  # Generate scenario parameters
  scenarios <- generate_scenario_parameters(n_scenarios = 100, seed = 42)

  # Save scenario parameters
  scenarios_file <- file.path(output_dir, "scenarios.csv")
  write.csv(scenarios, scenarios_file, row.names = FALSE)
  cat(sprintf("\n✓ Saved scenario parameters: %s\n\n", scenarios_file))

  # Create enhanced agents (do this once, reuse for all scenarios)
  cat("Creating enhanced cognitive agents...\n")
  enhanced_agents <- create_all_integrated_agents(
    config = list(AGENTS = AGENTS),
    country_mapping = list(
      major_power = "Novaris",
      small_power = "Tethys",
      external = "External"
    )
  )

  # Use the full enhanced_agents directly (don't strip out fields)
  # The simulation needs all agent attributes (description, deception, etc.)

  # Check for already-completed scenarios (resume support)
  completed_scenarios <- c()
  existing_ground_truth <- list()
  for (i in 1:nrow(scenarios)) {
    scenario_dir <- file.path(output_dir, sprintf("scenario_%03d", i))
    state_file <- file.path(output_dir, sprintf("scenario_%03d.rds", i))
    # A scenario is complete if both its .rds state file AND interaction directory exist
    if (file.exists(state_file) && dir.exists(scenario_dir)) {
      # Verify the directory has interaction files (not just an empty dir)
      interaction_files <- list.files(scenario_dir, pattern = "\\.csv$")
      if (length(interaction_files) >= 3) {
        completed_scenarios <- c(completed_scenarios, i)
        # Load ground truth from saved state
        saved_state <- readRDS(state_file)

        # Get collapse probability - check both field names (changed across versions)
        collapse_prob <- NA
        if (!is.null(saved_state$aggregator_assessments) && length(saved_state$aggregator_assessments) > 0) {
          assessment <- saved_state$aggregator_assessments[[1]]
          if (!is.null(assessment$probability)) collapse_prob <- assessment$probability
        } else if (!is.null(saved_state$assessments_history) && length(saved_state$assessments_history) > 0) {
          assessment <- saved_state$assessments_history[[1]]
          if (!is.null(assessment$probability)) collapse_prob <- assessment$probability
        }

        # Get actions from action_decisions (not action_history which doesn't exist)
        novaris_actions <- character(0)
        tethys_actions <- character(0)
        if (!is.null(saved_state$action_decisions) && length(saved_state$action_decisions) > 0) {
          if (!is.null(saved_state$action_decisions[[1]]$major_power$approved_actions)) {
            novaris_actions <- sapply(saved_state$action_decisions[[1]]$major_power$approved_actions, function(a) a$action)
          }
          if (!is.null(saved_state$action_decisions[[1]]$small_power$approved_actions)) {
            tethys_actions <- sapply(saved_state$action_decisions[[1]]$small_power$approved_actions, function(a) a$action)
          }
        }

        existing_ground_truth[[i]] <- list(
          scenario_id = scenarios$scenario_id[i],
          period = 1,
          collapse_probability = collapse_prob,
          novaris_actions = novaris_actions,
          tethys_actions = tethys_actions,
          n_novaris_actions = length(novaris_actions),
          n_tethys_actions = length(tethys_actions),
          final_territory = saved_state$scenario_state$territory_controlled,
          final_military_balance = saved_state$scenario_state$military_balance,
          final_crisis_level = saved_state$scenario_state$crisis_level,
          final_sanctions = saved_state$scenario_state$sanctions_level,
          final_support = saved_state$scenario_state$international_support
        )
      }
    }
  }

  # Run simulations for all scenarios
  cat("\n", rep("=", 70), "\n")
  cat("RUNNING SIMULATIONS\n")
  cat(rep("=", 70), "\n")

  if (length(completed_scenarios) > 0) {
    cat(sprintf("\n[RESUME] Found %d already-completed scenarios, skipping them.\n", length(completed_scenarios)))
    cat(sprintf("[RESUME] Completed: %s\n", paste(sprintf("%03d", completed_scenarios), collapse = ", ")))
    cat(sprintf("[RESUME] Remaining: %d scenarios to run\n\n", nrow(scenarios) - length(completed_scenarios)))
  }

  all_ground_truth <- existing_ground_truth  # Start with already-loaded results
  successful_count <- length(completed_scenarios)
  failed_count <- 0

  for (i in 1:nrow(scenarios)) {
    # Skip already-completed scenarios
    if (i %in% completed_scenarios) {
      next
    }

    scenario_row <- scenarios[i, ]

    # Clean temp directory before each scenario to prevent assessment accumulation
    temp_assessment <- file.path(output_dir, "temp", "assessments.csv")
    if (file.exists(temp_assessment)) file.remove(temp_assessment)

    result <- run_single_scenario_simulation(
      scenario_params = scenario_row,
      agents = enhanced_agents,
      api_key = api_key
    )

    if (result$success) {
      all_ground_truth[[i]] <- result$ground_truth
      successful_count <- successful_count + 1

      # Save detailed state
      state_file <- file.path(output_dir, sprintf("scenario_%03d.rds", i))
      saveRDS(result$state, state_file)

      # Copy interaction CSVs to scenario-specific directory before they get overwritten
      scenario_dir <- file.path(output_dir, sprintf("scenario_%03d", i))
      dir.create(scenario_dir, recursive = TRUE, showWarnings = FALSE)

      # Copy coordination, proposals, actions, and discussion CSVs
      interaction_files <- list.files("outputs/interactions", pattern = "^period_01_", full.names = TRUE)
      if (length(interaction_files) > 0) {
        file.copy(interaction_files, scenario_dir, overwrite = TRUE)
      }

      # Copy aggregator assessment
      assessment_file <- file.path(output_dir, "temp", "assessments.csv")
      if (file.exists(assessment_file)) {
        file.copy(assessment_file, scenario_dir, overwrite = TRUE)
      }

      cat(sprintf("  Saved %d interaction files + assessment to %s\n",
                  length(interaction_files), scenario_dir))

    } else {
      failed_count <- failed_count + 1
      all_ground_truth[[i]] <- list(
        scenario_id = scenario_row$scenario_id,
        success = FALSE,
        error = result$error
      )
    }

    # Save ground truth incrementally (after each scenario)
    ground_truth_df_partial <- do.call(rbind, lapply(all_ground_truth, function(gt) {
      if (is.null(gt) || is.null(gt$collapse_probability)) return(NULL)
      data.frame(
        scenario_id = gt$scenario_id,
        period = gt$period,
        collapse_probability = gt$collapse_probability,
        novaris_actions = paste(gt$novaris_actions, collapse = "|"),
        tethys_actions = paste(gt$tethys_actions, collapse = "|"),
        n_novaris_actions = gt$n_novaris_actions,
        n_tethys_actions = gt$n_tethys_actions,
        final_territory = gt$final_territory,
        final_military_balance = gt$final_military_balance,
        final_crisis_level = gt$final_crisis_level,
        final_sanctions = gt$final_sanctions,
        final_support = gt$final_support,
        stringsAsFactors = FALSE
      )
    }))
    ground_truth_file <- file.path(output_dir, "ground_truth.csv")
    write.csv(ground_truth_df_partial, ground_truth_file, row.names = FALSE)

    # Progress update
    if (i %% 10 == 0) {
      cat(sprintf("\nProgress: %d/%d scenarios completed (%d successful, %d failed)\n\n",
                  i, nrow(scenarios), successful_count, failed_count))
    }
  }

  # Final ground truth save (redundant but ensures completeness)
  ground_truth_df <- do.call(rbind, lapply(all_ground_truth, function(gt) {
    if (is.null(gt) || is.null(gt$collapse_probability)) return(NULL)
    data.frame(
      scenario_id = gt$scenario_id,
      period = gt$period,
      collapse_probability = gt$collapse_probability,
      novaris_actions = paste(gt$novaris_actions, collapse = "|"),
      tethys_actions = paste(gt$tethys_actions, collapse = "|"),
      n_novaris_actions = gt$n_novaris_actions,
      n_tethys_actions = gt$n_tethys_actions,
      final_territory = gt$final_territory,
      final_military_balance = gt$final_military_balance,
      final_crisis_level = gt$final_crisis_level,
      final_sanctions = gt$final_sanctions,
      final_support = gt$final_support,
      stringsAsFactors = FALSE
    )
  }))

  ground_truth_file <- file.path(output_dir, "ground_truth.csv")
  write.csv(ground_truth_df, ground_truth_file, row.names = FALSE)

  # Final summary
  cat("\n", rep("=", 70), "\n")
  cat("DATASET GENERATION COMPLETE\n")
  cat(rep("=", 70), "\n")
  cat(sprintf("Scenarios generated: %d\n", nrow(scenarios)))
  cat(sprintf("Simulations successful: %d\n", successful_count))
  cat(sprintf("Simulations failed: %d\n", failed_count))
  cat(sprintf("\nOutput files:\n"))
  cat(sprintf("  Scenarios: %s\n", scenarios_file))
  cat(sprintf("  Ground truth: %s\n", ground_truth_file))
  cat(sprintf("  Detailed states: %s/scenario_*.rds\n", output_dir))
  cat(rep("=", 70), "\n")
}

# Run if called as script
if (!interactive()) {
  main()
}
