# Generate External Observer Forecasting Prompts (v3.6)
#
# This script generates realistic forecasting prompts where humans see only
# what external observers would see (news, analysis) without internal deliberations.

# Load required functions
source("src/forecast_prompts.R")                      # Original (full info)
source("src/forecast_prompts_external_observer_v36.R") # New (external observer)

# Load completed simulation state
state <- readRDS("outputs/simulation_state.rds")

cat("Loaded simulation with", state$current_period, "periods\n\n")

# ============================================================================
# GENERATE BOTH VERSIONS FOR COMPARISON
# ============================================================================

cat("Generating BOTH forecasting prompt versions...\n")
cat(paste(rep("=", 70), collapse = ""), "\n\n")

# Version 1: Full Information (original system)
cat("1. FULL INFORMATION version (original)...\n")
prompts_full <- generate_all_forecast_prompts(
  state,
  output_file = "outputs/forecasting_prompts_FULL_INFO.txt",
  control_condition = FALSE
)
cat("   ✓ Saved to: outputs/forecasting_prompts_FULL_INFO.txt\n\n")

# Version 2: External Observer (realistic)
cat("2. EXTERNAL OBSERVER version (realistic)...\n")
prompts_external <- generate_all_forecast_prompts_external(
  state,
  output_file = "outputs/forecasting_prompts_EXTERNAL_OBSERVER.txt",
  control_condition = FALSE
)
cat("   ✓ Saved to: outputs/forecasting_prompts_EXTERNAL_OBSERVER.txt\n\n")

# ============================================================================
# COMPARE THE TWO VERSIONS
# ============================================================================

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("COMPARISON: Period 2 Prompts\n")
cat(paste(rep("=", 70), collapse = ""), "\n\n")

period <- 2

cat("--- FULL INFORMATION VERSION ---\n")
cat(substr(prompts_full[[period]], 1, 600))
cat("\n...\n\n")

cat("--- EXTERNAL OBSERVER VERSION ---\n")
cat(substr(prompts_external[[period]], 1, 600))
cat("\n...\n\n")

# ============================================================================
# CHECK FOR INFORMATION LEAKAGE
# ============================================================================

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("VALIDATION: Checking for internal information leakage\n")
cat(paste(rep("=", 70), collapse = ""), "\n\n")

# Check if external observer prompts contain internal keywords
leaked_keywords <- c("internal", "coordination", "deliberation", "meeting",
                     "debate", "recommends", "agent")

leaks_found <- FALSE
for (p in 1:length(prompts_external)) {
  prompt_text <- tolower(prompts_external[[p]])
  for (keyword in leaked_keywords) {
    if (grepl(keyword, prompt_text) &&
        !grepl("international|coordination on military aid", prompt_text)) {  # Allow these contexts
      cat(sprintf("⚠️  Period %d contains '%s'\n", p, keyword))
      leaks_found <- TRUE
    }
  }
}

if (!leaks_found) {
  cat("✓ No internal information leakage detected\n\n")
} else {
  cat("\n⚠️  Review flagged prompts to ensure no internal info is visible\n\n")
}

# ============================================================================
# CONTENT COMPARISON
# ============================================================================

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("CONTENT ANALYSIS\n")
cat(paste(rep("=", 70), collapse = ""), "\n\n")

cat("Prompt lengths (characters):\n")
for (p in 1:min(3, length(prompts_full))) {
  cat(sprintf("Period %d: Full=%d, External=%d (%.0f%% of full)\n",
              p,
              nchar(prompts_full[[p]]),
              nchar(prompts_external[[p]]),
              nchar(prompts_external[[p]]) / nchar(prompts_full[[p]]) * 100))
}

cat("\nExternal observer prompts should be 40-60% of full info length.\n")
cat("Shorter = less information = more realistic constraint.\n\n")

# ============================================================================
# GENERATE CONTROL CONDITIONS (OPTIONAL)
# ============================================================================

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("OPTIONAL: Generate Control Conditions\n")
cat(paste(rep("=", 70), collapse = ""), "\n\n")

cat("Generating control conditions for both versions...\n\n")

# Full info control
prompts_full_control <- generate_all_forecast_prompts(
  state,
  output_file = "outputs/forecasting_prompts_FULL_INFO_CONTROL.txt",
  control_condition = TRUE
)
cat("✓ Full info control: outputs/forecasting_prompts_FULL_INFO_CONTROL.txt\n")

# External observer control
prompts_external_control <- generate_all_forecast_prompts_external(
  state,
  output_file = "outputs/forecasting_prompts_EXTERNAL_OBSERVER_CONTROL.txt",
  control_condition = TRUE
)
cat("✓ External observer control: outputs/forecasting_prompts_EXTERNAL_OBSERVER_CONTROL.txt\n\n")

# ============================================================================
# SUMMARY & NEXT STEPS
# ============================================================================

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("SUMMARY\n")
cat(paste(rep("=", 70), collapse = ""), "\n\n")

cat("Generated 4 forecasting prompt files:\n\n")

cat("RECOMMENDED FOR HUMAN FORECASTERS:\n")
cat("  ✓ forecasting_prompts_EXTERNAL_OBSERVER.txt (TRUE condition)\n")
cat("  ✓ forecasting_prompts_EXTERNAL_OBSERVER_CONTROL.txt (CONTROL condition)\n")
cat("    → Humans see only publicly observable information (realistic)\n\n")

cat("FOR COMPARISON/RESEARCH:\n")
cat("  • forecasting_prompts_FULL_INFO.txt (TRUE condition)\n")
cat("  • forecasting_prompts_FULL_INFO_CONTROL.txt (CONTROL condition)\n")
cat("    → Shows internal deliberations (unrealistic but interesting)\n\n")

cat("RESEARCH QUESTIONS:\n")
cat("1. Do humans with external observer constraint still forecast accurately?\n")
cat("2. How much does full info improve human performance?\n")
cat("3. Do LLMs (with full info) outperform external observer humans?\n")
cat("4. Does external observer version match real-world tournament accuracy?\n\n")

cat("NEXT STEPS:\n")
cat("1. Recruit human forecasters\n")
cat("2. RECOMMENDED: Use EXTERNAL_OBSERVER version for ecological validity\n")
cat("3. Optional: Run comparison study with FULL_INFO version\n")
cat("4. Collect forecasts and compare using compare_forecasts() function\n\n")

cat("For details on external observer methodology:\n")
cat("See: HUMAN_FORECASTING_REALISM_UPDATE.md\n\n")

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("✓ External observer forecasting prompts ready!\n")
cat(paste(rep("=", 70), collapse = ""), "\n")
