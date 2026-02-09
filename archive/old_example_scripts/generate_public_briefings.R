# Generate Public Forecasting Briefings for Human-AI Study
#
# This script generates news-style intelligence briefings with PUBLIC information only
# (no internal deliberations, coordination, or private negotiations)

# Load required functions
source("src/forecast_prompts_public.R")

# Load completed simulation state
state <- readRDS("outputs/simulation_state.rds")

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("PUBLIC FORECASTING BRIEFING GENERATOR\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

cat("Loaded simulation with", state$current_period, "periods\n\n")

# ============================================================================
# GENERATE COMPLETE FORECASTING PACKAGE
# ============================================================================

cat("Generating complete forecasting package for human participants...\n\n")

files <- create_public_forecasting_package(
  state,
  output_dir = "outputs/human_forecasting",
  generate_control = TRUE  # Set FALSE to skip control condition
)

# ============================================================================
# PREVIEW: Show Period 1 and Period 2 briefings
# ============================================================================

cat("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("PREVIEW: Period 1 Briefing (First 1000 characters)\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

prompt_p1 <- generate_public_forecast_prompt(state, 1, control_condition = FALSE)
cat(substr(prompt_p1, 1, 1000))
cat("\n\n... (truncated) ...\n\n")

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("PREVIEW: Period 2 Briefing (First 1200 characters)\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

prompt_p2 <- generate_public_forecast_prompt(state, 2, control_condition = FALSE)
cat(substr(prompt_p2, 1, 1200))
cat("\n\n... (truncated) ...\n\n")

# ============================================================================
# VALIDATION: Check for information leakage
# ============================================================================

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("VALIDATION: Checking for internal information leakage\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

# Keywords that indicate internal information
leaked_keywords <- c(
  "internal deliberation", "coordination meeting", "recommends", "agent",
  "strategic planning", "faction", "internal discussion", "decides to",
  "coordination between", "internal debate"
)

prompts_to_check <- lapply(1:state$current_period, function(p) {
  generate_public_forecast_prompt(state, p, control_condition = FALSE)
})

leaks_found <- FALSE
for (p in 1:length(prompts_to_check)) {
  prompt_text <- tolower(prompts_to_check[[p]])
  for (keyword in leaked_keywords) {
    if (grepl(keyword, prompt_text, fixed = TRUE)) {
      cat(sprintf("[FAIL] Period %d contains '%s'\n", p, keyword))
      leaks_found <- TRUE
    }
  }
}

if (!leaks_found) {
  cat("[OK] No internal information leakage detected\n")
  cat("    All prompts contain only publicly observable information\n\n")
} else {
  cat("\n[FAIL] Internal information detected - review prompts\n\n")
}

# ============================================================================
# COMPARISON: Public vs. Original prompts
# ============================================================================

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("COMPARISON: Information Filtering\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

# Load original forecast prompts function for comparison
source("src/forecast_prompts.R")

cat("Content comparison for Period 2:\n\n")

original_prompt <- generate_forecast_prompt(state, 2, control_condition = FALSE)
public_prompt <- generate_public_forecast_prompt(state, 2, control_condition = FALSE)

cat(sprintf("Original prompt length: %d characters\n", nchar(original_prompt)))
cat(sprintf("Public prompt length:   %d characters\n", nchar(public_prompt)))
cat(sprintf("Public is %.0f%% of original length\n",
            nchar(public_prompt) / nchar(original_prompt) * 100))
cat("\n")

# Check what's removed
has_interactions_original <- grepl("interaction", tolower(original_prompt))
has_interactions_public <- grepl("interaction", tolower(public_prompt))

cat("Information filtering:\n")
cat(sprintf("  Original includes interactions: %s\n",
            ifelse(has_interactions_original, "[YES]", "[NO]")))
cat(sprintf("  Public includes interactions:   %s\n",
            ifelse(has_interactions_public, "[YES]", "[NO]")))

if (has_interactions_original && !has_interactions_public) {
  cat("\n[OK] Internal interactions successfully filtered out\n")
}

# ============================================================================
# SUMMARY & NEXT STEPS
# ============================================================================

cat("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("SUMMARY\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

cat("Generated files in outputs/human_forecasting/:\n\n")
cat("FOR PARTICIPANTS:\n")
cat("  • PARTICIPANT_INSTRUCTIONS.txt - Study overview and guidelines\n")
cat("  • forecasting_briefings_PUBLIC.txt - Intelligence briefings (TRUE)\n")
cat("  • forecasting_briefings_PUBLIC_CONTROL.txt - Randomized version (CONTROL)\n\n")

cat("FOR RESEARCHERS:\n")
cat("  • human_forecasts_template.csv - Data collection spreadsheet\n")
cat("  • ANSWER_KEY_llm_forecasts.txt - LLM aggregator forecasts\n\n")

cat("STUDY DESIGN:\n\n")
cat("This creates a human-AI forecasting study to test whether humans\n")
cat("with personalized AI assistants can predict geopolitical outcomes\n")
cat("using only publicly available information.\n\n")

cat("Key features:\n")
cat("  [OK] News-style intelligence briefings (Economist/FT format)\n")
cat("  [OK] Public information only (no internal deliberations)\n")
cat("  [OK] Observable actions and events\n")
cat("  [OK] Realistic information constraint\n")
cat("  [OK] Control condition for overfitting detection\n\n")

cat("NEXT STEPS:\n\n")
cat("1. Review generated briefings for quality and realism\n")
cat("2. Recruit human participants (e.g., forecasters, analysts, students)\n")
cat("3. Pair participants with AI assistants (e.g., Claude, GPT-4)\n")
cat("4. Collect forecasts using the CSV template\n")
cat("5. Compare performance:\n")
cat("   • Human+AI (public info) vs. LLM aggregator (full info)\n")
cat("   • Performance on TRUE vs. CONTROL condition\n")
cat("   • Calibration and Brier scores\n\n")

cat("RESEARCH QUESTIONS:\n\n")
cat("• Can humans with AI assistants forecast accurately using only public info?\n")
cat("• How does performance compare to LLM systems with full information?\n")
cat("• Do AI assistants improve human forecasting accuracy?\n")
cat("• Can forecasters distinguish signal (TRUE) from noise (CONTROL)?\n\n")

cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("[OK] Public forecasting briefings ready for human-AI study!\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
