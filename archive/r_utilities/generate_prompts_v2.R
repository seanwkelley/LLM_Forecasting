# Generate IMPROVED forecasting prompts (VERSION 2)
# With faction names, richer detail, and natural language

source("src/forecast_prompts_public_v2.R")

# Load simulation
state <- readRDS("outputs/simulation_state.rds")

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("GENERATING IMPROVED FORECASTING PROMPTS (VERSION 2)\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

cat(sprintf("Simulation: %d periods\n\n", state$current_period))

cat("Improvements:\n")
cat("  ✓ Faction names included (Novaris, Tethys)\n")
cat("  ✓ Richer initial scenario with backstory\n")
cat("  ✓ Natural language instead of raw numbers\n")
cat("  ✓ More intuitive descriptions\n\n")

# TRUE CONDITION
cat("1. Generating TRUE condition (natural language)...\n")
tryCatch({
  prompts_true <- generate_all_public_forecast_prompts_v2(
    state,
    output_file = "outputs/human_forecasting/forecasting_prompts_TRUE.txt",
    output_dir = "outputs/human_forecasting/TRUE",
    control_condition = FALSE
  )
  cat(sprintf("   [OK] Generated %d prompts\n", length(prompts_true)))
}, error = function(e) {
  cat("   [FAIL] Error in TRUE condition:\n")
  cat(sprintf("   %s\n\n", e$message))
  traceback()
})

# CONTROL CONDITION
cat("\n2. Generating CONTROL condition (natural language)...\n")
tryCatch({
  prompts_control <- generate_all_public_forecast_prompts_v2(
    state,
    output_file = "outputs/human_forecasting/forecasting_prompts_CONTROL.txt",
    output_dir = "outputs/human_forecasting/CONTROL",
    control_condition = TRUE
  )
  cat(sprintf("   [OK] Generated %d prompts\n", length(prompts_control)))
}, error = function(e) {
  cat("   [FAIL] Error:\n")
  cat(sprintf("   %s\n\n", e$message))
})

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("PREVIEW: Period 1 (first 1500 characters)\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

cat(substr(prompts_true[[1]], 1, 1500))
cat("\n\n... (truncated) ...\n\n")

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("[OK] Improved prompts generated successfully!\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
