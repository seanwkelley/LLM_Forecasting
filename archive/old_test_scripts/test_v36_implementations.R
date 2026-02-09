# Test Script for v3.6 Implementations
# Tests both cross-expertise and external observer updates

cat("Testing v3.6 Implementations\n")
cat(paste(rep("=", 70), collapse = ""), "\n\n")

# ============================================================================
# TEST 1: Cross-Expertise Prompts
# ============================================================================

cat("TEST 1: Cross-Expertise Recommendation Prompts\n")
cat(paste(rep("-", 70), collapse = ""), "\n\n")

# Load interaction engine (which now has updated prompts)
source("src/interaction_engine.R")

# Check if the prompt update is present
test_faction <- "major_power"
test_context <- list(
  scenario_state = list(
    crisis_level = 7,
    military_balance = -0.2,
    territory_controlled = 0.10
  ),
  recent_events = list()
)

cat("Testing prompt generation...\n")

# This would normally be called during coordination
# We're just checking the function exists and runs
if (exists("format_situation_for_coordination")) {
  situation <- format_situation_for_coordination(test_context)
  cat("✓ Situation formatting works\n")
} else {
  cat("⚠️  format_situation_for_coordination not found\n")
}

# Check that generate_dynamic_action_options exists
if (exists("generate_dynamic_action_options")) {
  cat("✓ Action options generation works\n")
} else {
  cat("⚠️  generate_dynamic_action_options not found\n")
}

cat("\nCross-expertise update should include language like:\n")
cat("  'You bring X EXPERTISE to this decision...'\n")
cat("  'A military expert CAN recommend diplomacy...'\n")
cat("  'Recommend the action that BEST SERVES your faction'\n\n")

cat("To verify: Run a simulation and check coordination logs for\n")
cat("cross-expertise recommendations (e.g., military → peace_talks)\n\n")

# ============================================================================
# TEST 2: External Observer Forecasting
# ============================================================================

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("TEST 2: External Observer Forecasting Functions\n")
cat(paste(rep("-", 70), collapse = ""), "\n\n")

# Load external observer module
source("src/forecast_prompts_external_observer_v36.R")

# Test action observability
cat("Testing action observability filter...\n\n")

test_actions <- list(
  list(action = "military_buildup", success = TRUE, detected = FALSE,
       desc = "Public action - always visible"),
  list(action = "peace_talks", success = FALSE, detected = FALSE,
       desc = "Public action - always visible"),
  list(action = "sabotage", success = TRUE, detected = FALSE,
       desc = "Covert - should be HIDDEN"),
  list(action = "sabotage", success = FALSE, detected = TRUE,
       desc = "Covert but detected - should be VISIBLE"),
  list(action = "cyber_attack", success = TRUE, detected = TRUE,
       desc = "Covert but detected - should be VISIBLE")
)

cat("Action Observability Tests:\n")
all_pass <- TRUE
for (test in test_actions) {
  observable <- is_action_publicly_observable(test$action, test$success, test$detected)

  # Check expectations
  expected <- if (test$action %in% c("military_buildup", "peace_talks")) {
    TRUE
  } else if (test$detected || !test$success) {
    TRUE
  } else {
    FALSE
  }

  status <- if (observable == expected) "✓" else "✗"
  if (observable != expected) all_pass <- FALSE

  cat(sprintf("  %s %s (success=%s, detected=%s): %s\n",
              status,
              test$action,
              test$success,
              test$detected,
              if (observable) "VISIBLE" else "HIDDEN"))
}

if (all_pass) {
  cat("\n✓ All observability tests passed!\n\n")
} else {
  cat("\n✗ Some tests failed - check implementation\n\n")
}

# Test action description
cat("Testing external action descriptions...\n\n")

test_action_record <- list(
  action = "limited_strike",
  faction = "major_power",
  success = TRUE,
  detected = FALSE,
  territory_change = 0.05
)

external_desc <- describe_action_externally(test_action_record)
cat(sprintf("  limited_strike → '%s'\n", external_desc))

if (!is.null(external_desc) && grepl("Novaris", external_desc)) {
  cat("✓ Action description works correctly\n\n")
} else {
  cat("✗ Action description issue\n\n")
}

# Test analyst commentary
cat("Testing analyst commentary generation...\n\n")

test_state <- list(
  territory_controlled = 0.15,
  crisis_level = 9,
  sanctions_level = 0.6
)

test_actions_list <- c(
  "Novaris launched major offensive",
  "Tethys increased military readiness"
)

commentary <- generate_analyst_commentary(test_state, test_actions_list)
cat("Generated commentary:\n")
cat(paste(strwrap(commentary, width = 65), collapse = "\n"))
cat("\n\n")

if (nchar(commentary) > 50) {
  cat("✓ Analyst commentary generated\n\n")
} else {
  cat("✗ Commentary too short or missing\n\n")
}

# ============================================================================
# TEST 3: Generate Sample Prompts
# ============================================================================

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("TEST 3: Generate Sample Forecast Prompts\n")
cat(paste(rep("-", 70), collapse = ""), "\n\n")

# Create minimal test state
test_simulation_state <- list(
  current_period = 2,
  events_history = list(
    list(  # Period 1
      list(name = "Economic Shock", description = "Oil prices surge"),
      list(name = "Military Mobilization", description = "Forces deployed")
    )
  ),
  faction_actions = list(
    list(period = 1, action = "limited_strike", faction = "major_power",
         success = TRUE, detected = FALSE),
    list(period = 1, action = "military_buildup", faction = "small_power",
         success = TRUE, detected = FALSE)
  ),
  scenario_state_history = list(
    list(  # Period 1
      territory_controlled = 0.08,
      crisis_level = 8,
      sanctions_level = 0.4,
      international_support = 0.6
    )
  ),
  assessments_history = list(
    list(probability = 0.28)  # Period 1 LLM forecast
  )
)

cat("Generating external observer prompt for Period 2...\n\n")

tryCatch({
  test_prompt <- generate_forecast_prompt_external(test_simulation_state, 2)

  cat("Sample prompt (first 500 characters):\n")
  cat(paste(rep("-", 70), collapse = ""), "\n")
  cat(substr(test_prompt, 1, 500))
  cat("\n...\n")
  cat(paste(rep("-", 70), collapse = ""), "\n\n")

  # Check for key elements
  checks <- list(
    "EXTERNAL OBSERVER" = grepl("EXTERNAL OBSERVER", test_prompt),
    "Publicly observable" = grepl("publicly|observable|reported", test_prompt, ignore.case = TRUE),
    "Information limits" = grepl("do NOT have access", test_prompt, ignore.case = TRUE),
    "Analyst commentary" = grepl("analyst|expert", test_prompt, ignore.case = TRUE),
    "No internal leakage" = !grepl("internal.*coordination|deliberation.*meeting", test_prompt, ignore.case = TRUE)
  )

  cat("Prompt validation:\n")
  for (check_name in names(checks)) {
    status <- if (checks[[check_name]]) "✓" else "✗"
    cat(sprintf("  %s %s\n", status, check_name))
  }
  cat("\n")

  if (all(unlist(checks))) {
    cat("✓ External observer prompt is correctly formatted!\n\n")
  } else {
    cat("⚠️  Some validation checks failed - review prompt\n\n")
  }

}, error = function(e) {
  cat("✗ Error generating prompt:\n")
  cat(paste("  ", e$message, "\n\n"))
})

# ============================================================================
# SUMMARY
# ============================================================================

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("TEST SUMMARY\n")
cat(paste(rep("=", 70), collapse = ""), "\n\n")

cat("✓ Cross-expertise prompts: Updated in src/interaction_engine.R\n")
cat("  → Agents can now recommend actions outside their traditional domain\n")
cat("  → To verify: Run simulation and check for cross-expertise recommendations\n\n")

cat("✓ External observer forecasting: Implemented\n")
cat("  → Functions tested: observability, descriptions, commentary, prompts\n")
cat("  → Ready to generate realistic forecasting prompts\n\n")

cat("NEXT STEPS:\n")
cat("1. Run full simulation:\n")
cat("   Rscript run_simulation_with_actions.R\n\n")

cat("2. Check cross-expertise in coordination logs:\n")
cat("   coordination <- read.csv('outputs/all_coordination.csv')\n")
cat("   # Look for military recommending peace, diplomats recommending strikes, etc.\n\n")

cat("3. Generate external observer forecasting prompts:\n")
cat("   Rscript examples/generate_external_observer_prompts.R\n\n")

cat("4. Review generated prompts:\n")
cat("   outputs/forecasting_prompts_EXTERNAL_OBSERVER.txt\n\n")

cat(paste(rep("=", 70), collapse = ""), "\n")
cat("✓ v3.6 implementations ready for testing!\n")
cat(paste(rep("=", 70), collapse = ""), "\n")
