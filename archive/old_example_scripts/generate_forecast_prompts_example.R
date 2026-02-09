# Example: Generate Human Forecasting Prompts (TRUE + CONTROL Conditions)
#
# This script demonstrates how to generate forecasting prompts for human
# participants in both TRUE and CONTROL conditions after running a simulation.

# Load required functions
source("src/forecast_prompts.R")
source("src/control_condition.R")

# Load completed simulation state
# (Replace with your actual simulation output path)
state <- readRDS("outputs/simulation_state.rds")

cat("Loaded simulation with", state$current_period, "periods\n\n")

# ============================================================================
# OPTION 1: Generate Both Conditions Automatically
# ============================================================================

cat("OPTION 1: Generate both TRUE and CONTROL conditions\n")
cat(paste(rep("=", 60), collapse = ""), "\n")

files <- create_forecasting_worksheet(
  state,
  output_dir = "outputs",
  generate_control = TRUE  # Set FALSE to skip control condition
)

cat("\nGenerated files:\n")
cat("- TRUE condition:", files$prompts_true, "\n")
cat("- CONTROL condition:", files$prompts_control, "\n")
cat("- Answer key:", files$answers, "\n")
cat("- CSV template:", files$template, "\n\n")

# ============================================================================
# OPTION 2: Generate Control Condition Manually (for inspection)
# ============================================================================

cat("OPTION 2: Generate control condition manually\n")
cat(paste(rep("=", 60), collapse = ""), "\n")

# Create control condition state
control_state <- generate_control_condition(state)

# Show what changed
summary <- summarize_control_changes(state, control_state)
cat(summary)
cat("\n")

# Generate prompts from control state
control_prompts <- list()
for (p in 1:control_state$current_period) {
  control_prompts[[p]] <- generate_forecast_prompt(
    control_state,
    p,
    control_condition = TRUE
  )
}

cat("Generated", length(control_prompts), "control condition prompts\n\n")

# ============================================================================
# OPTION 3: Side-by-Side Comparison of Period 2 Prompts
# ============================================================================

cat("OPTION 3: Compare TRUE vs CONTROL for Period 2\n")
cat(paste(rep("=", 60), collapse = ""), "\n")

period <- 2

# TRUE condition
true_prompt <- generate_forecast_prompt(state, period, control_condition = FALSE)

# CONTROL condition
control_prompt <- generate_forecast_prompt(control_state, period, control_condition = TRUE)

cat("\n--- TRUE CONDITION (Period", period, ") ---\n")
cat(substr(true_prompt, 1, 800))  # Show first 800 characters
cat("\n...\n\n")

cat("--- CONTROL CONDITION (Period", period, ") ---\n")
cat(substr(control_prompt, 1, 800))  # Show first 800 characters
cat("\n...\n\n")

# ============================================================================
# OPTION 4: Analyze Control Randomization Effects
# ============================================================================

cat("OPTION 4: Analyze randomization effects\n")
cat(paste(rep("=", 60), collapse = ""), "\n")

# Compare metrics across conditions
cat("\nTERRITORY CONTROLLED:\n")
for (p in 1:min(5, state$current_period)) {
  true_terr <- if (!is.null(state$scenario_state_history[[p]])) {
    state$scenario_state_history[[p]]$territory_controlled
  } else {
    state$scenario_state$territory_controlled
  }

  control_terr <- if (!is.null(control_state$scenario_state_history[[p]])) {
    control_state$scenario_state_history[[p]]$territory_controlled
  } else {
    control_state$scenario_state$territory_controlled
  }

  cat(sprintf("Period %d: TRUE=%.1f%%, CONTROL=%.1f%% (diff=%.1f%%)\n",
              p, true_terr * 100, control_terr * 100,
              abs(true_terr - control_terr) * 100))
}

cat("\nCRISIS LEVEL:\n")
for (p in 1:min(5, state$current_period)) {
  true_crisis <- if (!is.null(state$scenario_state_history[[p]])) {
    state$scenario_state_history[[p]]$crisis_level
  } else {
    state$scenario_state$crisis_level
  }

  control_crisis <- if (!is.null(control_state$scenario_state_history[[p]])) {
    control_state$scenario_state_history[[p]]$crisis_level
  } else {
    control_state$scenario_state$crisis_level
  }

  cat(sprintf("Period %d: TRUE=%d/10, CONTROL=%d/10 (diff=%d)\n",
              p, true_crisis, control_crisis,
              abs(true_crisis - control_crisis)))
}

# ============================================================================
# OPTION 5: Mock Analysis of Human Forecaster Performance
# ============================================================================

cat("\n", paste(rep("=", 60), collapse = ""), "\n")
cat("OPTION 5: Mock analysis of forecaster performance\n")
cat(paste(rep("=", 60), collapse = ""), "\n")

# Simulate human forecasts (replace with actual human data)
set.seed(123)
n_periods <- state$current_period

# Good forecaster: tracks TRUE, clusters around base rate on CONTROL
human_true_good <- c(0.25, 0.30, 0.35, 0.32, 0.38)[1:min(5, n_periods)]
human_control_good <- c(0.36, 0.38, 0.37, 0.35, 0.36)[1:min(5, n_periods)]

# Bad forecaster: tracks patterns in both conditions (overfitting)
human_true_bad <- c(0.25, 0.30, 0.35, 0.32, 0.38)[1:min(5, n_periods)]
human_control_bad <- c(0.22, 0.45, 0.31, 0.39, 0.28)[1:min(5, n_periods)]

# LLM forecasts
llm_forecasts <- sapply(1:min(5, n_periods), function(p) {
  state$assessments_history[[p]]$probability
})

cat("\nGOOD FORECASTER (distinguishes signal from noise):\n")
cat("TRUE condition variance:", round(var(human_true_good), 4), "\n")
cat("CONTROL condition variance:", round(var(human_control_good), 4), "\n")
cat("Control mean:", round(mean(human_control_good), 2),
    "(close to base rate ~0.35)\n\n")

cat("BAD FORECASTER (overfits to both conditions):\n")
cat("TRUE condition variance:", round(var(human_true_bad), 4), "\n")
cat("CONTROL condition variance:", round(var(human_control_bad), 4), "\n")
cat("Control mean:", round(mean(human_control_bad), 2),
    "(not anchored to base rate)\n\n")

cat("Interpretation: Good forecaster shows LOW variance on CONTROL,\n")
cat("indicating they don't overfit to random patterns.\n\n")

# ============================================================================
# Summary
# ============================================================================

cat(paste(rep("=", 60), collapse = ""), "\n")
cat("SUMMARY\n")
cat(paste(rep("=", 60), collapse = ""), "\n\n")

cat("Files generated in outputs/:\n")
cat("1. forecasting_prompts_true.txt - Give to human forecasters\n")
cat("2. forecasting_prompts_control.txt - Give to same/different forecasters\n")
cat("3. forecasting_answer_key.txt - LLM aggregator answers\n")
cat("4. forecasting_template.csv - Data entry spreadsheet\n\n")

cat("Next steps:\n")
cat("1. Recruit human forecasters\n")
cat("2. Assign to TRUE or CONTROL condition (or both)\n")
cat("3. Collect forecasts using CSV template\n")
cat("4. Compare performance using compare_forecasts()\n")
cat("5. Test if CONTROL forecasts cluster around base rate\n\n")

cat("For methodology details, see CONTROL_CONDITION_GUIDE.md\n")
