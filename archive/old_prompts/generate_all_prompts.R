# Generate ALL forecasting prompts (TRUE + CONTROL conditions)

source("src/forecast_prompts_public.R")

# Load simulation
state <- readRDS("outputs/simulation_state.rds")

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("GENERATING ALL FORECASTING PROMPTS\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

cat(sprintf("Simulation has %d periods\n\n", state$current_period))

# ============================================================================
# 1. TRUE CONDITION (10 periods)
# ============================================================================

cat("1. Generating TRUE condition prompts...\n")

prompts_true <- generate_all_public_forecast_prompts(
  state,
  output_file = "outputs/human_forecasting/forecasting_prompts_TRUE.txt",
  control_condition = FALSE
)

cat(sprintf("   [OK] Generated %d prompts for TRUE condition\n", length(prompts_true)))
cat("   [OK] Saved to: outputs/human_forecasting/forecasting_prompts_TRUE.txt\n\n")

# ============================================================================
# 2. CONTROL CONDITION (10 periods)
# ============================================================================

cat("2. Generating CONTROL condition prompts...\n")

# Check if control_condition.R exists
if (file.exists("src/control_condition.R")) {
  tryCatch({
    prompts_control <- generate_all_public_forecast_prompts(
      state,
      output_file = "outputs/human_forecasting/forecasting_prompts_CONTROL.txt",
      control_condition = TRUE
    )

    cat(sprintf("   [OK] Generated %d prompts for CONTROL condition\n", length(prompts_control)))
    cat("   [OK] Saved to: outputs/human_forecasting/forecasting_prompts_CONTROL.txt\n\n")

  }, error = function(e) {
    cat("   [FAIL] Error generating control condition:\n")
    cat(sprintf("   %s\n", e$message))
    cat("   Control condition prompts NOT generated\n\n")
  })
} else {
  cat("   [FAIL] control_condition.R not found - skipping control condition\n\n")
}

# ============================================================================
# SUMMARY
# ============================================================================

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("SUMMARY\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

cat("Generated files in outputs/human_forecasting/:\n")
cat("  • forecasting_prompts_TRUE.txt - Real simulation dynamics (10 periods)\n")
if (file.exists("outputs/human_forecasting/forecasting_prompts_CONTROL.txt")) {
  cat("  • forecasting_prompts_CONTROL.txt - Randomized for overfitting detection (10 periods)\n")
}
cat("\n")

# Quick validation
cat("Validation:\n")
for (p in 1:min(3, length(prompts_true))) {
  cat(sprintf("  Period %d: %d characters\n", p, nchar(prompts_true[[p]])))
}
cat("\n")

cat("[OK] All prompts generated successfully!\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
