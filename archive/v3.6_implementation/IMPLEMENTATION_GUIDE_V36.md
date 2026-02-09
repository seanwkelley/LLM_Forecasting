# Implementation Guide: Two-Stage Decision Process (v3.6)
## Step-by-Step Integration Instructions

This guide provides complete step-by-step instructions for implementing the two-stage decision process with strategic direction filtering.

---

## Quick Start (Automated)

If you want to integrate everything at once:

1. **Backup your current files:**
   ```bash
   cd /d/Northeastern/LLM_Forecasting
   cp src/enhanced_action_space.R src/enhanced_action_space_backup.R
   cp src/interaction_engine.R src/interaction_engine_backup.R
   cp src/agent_decision.R src/agent_decision_backup.R
   ```

2. **Replace enhanced_action_space.R:**
   ```bash
   mv src/enhanced_action_space_v36.R src/enhanced_action_space.R
   ```

3. **Source strategic direction functions in interaction_engine.R:**

   Add at the top of `src/interaction_engine.R` (after line 3):
   ```r
   source("src/strategic_direction_functions.R")
   ```

4. **Follow the step-by-step modifications below**

---

## Step 1: Update enhanced_action_space.R

**Option A: Use the pre-built version**
```bash
mv src/enhanced_action_space_v36.R src/enhanced_action_space.R
```

**Option B: Manual addition**
Add the STRATEGIC_DIRECTIONS list and functions to your existing enhanced_action_space.R using the code from `enhanced_action_space_v36.R`.

**Verify:**
```r
source("src/enhanced_action_space.R")
names(STRATEGIC_DIRECTIONS)
# Should show: [1] "DIPLOMATIC" "ECONOMIC" "MILITARY_POSTURE" "COVERT" "OPEN_CONFLICT" "WMD"
```

---

## Step 2: Load Strategic Direction Functions

**In src/interaction_engine.R**, add after the library statements (around line 3):

```r
# Load strategic direction functions for two-stage decision process (v3.6)
source("src/strategic_direction_functions.R")
```

**Verify:**
```r
source("src/interaction_engine.R")
exists("extract_strategic_direction")
# Should return: TRUE
```

---

## Step 3: Modify Round 1 Prompt

**Location:** `src/interaction_engine.R`, function `run_pre_action_coordination`, Round 1 prompt

**Find this section** (around line 796):
```r
        prompt <- sprintf(
"INTERNAL STRATEGY MEETING - %s FACTION
...
```

**BEFORE the prompt, add:**
```r
        # Get strategic directions text for the prompt (v3.6)
        strategic_directions_text <- format_strategic_directions()
```

**UPDATE the prompt** to include strategic direction request:

Replace:
```r
=== YOUR TASK ===
Based on your CHARACTER, ROLE, and WORLDVIEW, recommend ONE specific action.
```

With:
```r
=== YOUR TASK ===

This is a TWO-PART recommendation:

**PART 1 - STRATEGIC DIRECTION:**
First, recommend the broad strategic approach your faction should take:

%s

Which strategic direction [A/B/C/D/E/F] do you recommend and why?

**PART 2 - SPECIFIC ACTION:**
Based on your strategic direction, recommend a SPECIFIC action from that category.
```

**ADD strategic_directions_text to sprintf parameters:**

Change the last line of sprintf from:
```r
          worldview_label
        )
```

To:
```r
          worldview_label,
          strategic_directions_text
        )
```

---

## Step 4: Add Strategic Vote Tallying Between Rounds

**Location:** `src/interaction_engine.R`, function `run_pre_action_coordination`

**Find the end of Round 1 loop** (around line 992):
```r
      messages <- c(messages, list(message))
      ...
    }
  } # End of for round in 1:n_rounds
```

**REPLACE that closing brace with:**
```r
      messages <- c(messages, list(message))
      ...
    }

    # === Strategic vote tallying after Round 1 (v3.6) ===
    if (round == 1) {
      cat("\n  Tallying strategic direction votes...\n")
      strategic_votes <- tally_strategic_votes(messages)

      cat("\n  Building filtered action set based on strategic consensus...\n")
      filtered_actions <- build_filtered_action_set(
        strategic_votes,
        primary_count = 6,
        secondary_count = 2
      )

      # Generate filtered action options text for final decision
      action_options_filtered <- format_filtered_actions_for_prompt(
        filtered_actions,
        context$scenario_state
      )
    }
  } # End of for round in 1:n_rounds
```

---

## Step 5: Update Coordination Return Value

**Location:** `src/interaction_engine.R`, end of `run_pre_action_coordination` function (around line 994)

**Find:**
```r
  # Return coordination record with all input
  coordination <- list(
    faction = faction,
    topic = coordination_topic,
    participants = sapply(faction_agents, function(a) a$name),
    messages = messages,
    context = context
  )

  return(coordination)
```

**REPLACE with:**
```r
  # Return coordination record with all input (v3.6: includes strategic votes)
  coordination <- list(
    faction = faction,
    topic = coordination_topic,
    participants = sapply(faction_agents, function(a) a$name),
    messages = messages,
    context = context,
    strategic_votes = if (exists("strategic_votes")) strategic_votes else NULL,
    filtered_actions = if (exists("filtered_actions")) filtered_actions else NULL,
    action_options_filtered = if (exists("action_options_filtered")) action_options_filtered else action_options
  )

  return(coordination)
```

---

## Step 6: Update agent_decision.R

**Location:** `src/agent_decision.R`, function that handles final action decisions

**Find where the decision prompt is built when coordination input exists**

This will look something like:
```r
if (!is.null(coordination_input)) {
  # Add team input to prompt
  ...
}
```

**ADD the decision synthesis requirement:**

```r
# === Enhanced decision synthesis (v3.6) ===
if (!is.null(coordination_input) && length(coordination_input$messages) > 0) {

  # Format Round 2 positions (last round of coordination)
  round_2_messages <- Filter(function(m) m$round == 2, coordination_input$messages)

  if (length(round_2_messages) > 0) {
    round_2_summary <- paste(sapply(round_2_messages, function(r) {
      sprintf("[%s]: %s", r$sender_name, substr(r$content, 1, 400))
    }), collapse = "\n\n")

    # Format strategic votes if available
    strategic_summary <- ""
    if (!is.null(coordination_input$strategic_votes)) {
      vote_text <- paste(names(coordination_input$strategic_votes),
                        " (", coordination_input$strategic_votes, " votes)", sep = "", collapse = ", ")
      strategic_summary <- sprintf("\n\nStrategic direction votes: %s", vote_text)
    }

    synthesis_requirement <- sprintf("

=== TEAM INPUT RECEIVED ===

Your team has debated the strategic approach and specific options.%s

Round 2 debate positions:
%s

=== YOUR DECISION PROCESS (REQUIRED) ===

Before selecting your action, synthesize the team input:

1. POSITIONS SUMMARY:
   - What are the 2-3 main options being debated?
   - Which strategic directions were recommended?

2. CRITICAL CONCERNS:
   - List specific warnings raised by team members
   - Note which colleague raised each concern

3. YOUR REASONING:
   - Which arguments are most compelling given the situation?
   - Why are you prioritizing certain goals over others?
   - What's the strongest case AGAINST your choice? Why proceed anyway?

4. FINAL DECISION: [action_name]
   - How does this balance the competing concerns from the debate?
   - Which colleagues' arguments most influenced you?

Your decision shows genuine integration when it references specific team member arguments and explains how you weighed them.
",
      strategic_summary,
      round_2_summary
    )

    decision_prompt <- paste0(decision_prompt, synthesis_requirement)
  }
}
```

**Also add filtered actions to prompt:**

```r
# Use filtered action set if available from coordination
available_actions_text <- if (!is.null(coordination_input$action_options_filtered)) {
  cat("  Using filtered action set from strategic consensus\n")
  coordination_input$action_options_filtered
} else {
  cat("  Using full action set (no pre-coordination)\n")
  generate_dynamic_action_options(agent$faction, context, NULL)
}

# Add to decision prompt
decision_prompt <- paste0(decision_prompt, "\n\n", available_actions_text)
```

---

## Step 7: Add Strategic Vote Logging

**Location:** In your main simulation file (`run_simulation_with_actions.R` or `src/simulation_with_actions.R`)

**After each period's coordination phase, add:**

```r
# Log strategic votes for analysis (v3.6)
if (exists("save_strategic_votes_to_csv")) {
  save_strategic_votes_to_csv(
    period = period,
    coordination_records = list(
      major_power_coordination,
      small_power_coordination,
      # Add other faction coordinations as needed
    ),
    output_dir = "outputs/interactions"
  )
}
```

---

## Step 8: Test the Implementation

### Basic Functionality Test

```r
# Test strategic direction extraction
test_response <- list(content = "STRATEGIC DIRECTION: A - DIPLOMATIC PATH\nRECOMMENDED ACTION: peace_talks")
direction <- extract_strategic_direction(test_response$content)
print(direction)  # Should print: "DIPLOMATIC"

# Test vote tallying
test_responses <- list(
  list(sender_name = "Agent1", content = "STRATEGIC DIRECTION: A"),
  list(sender_name = "Agent2", content = "STRATEGIC DIRECTION: A"),
  list(sender_name = "Agent3", content = "STRATEGIC DIRECTION: E")
)
votes <- tally_strategic_votes(test_responses)
print(votes)  # Should show: DIPLOMATIC: 2, OPEN_CONFLICT: 1

# Test action filtering
filtered <- build_filtered_action_set(votes, primary_count = 6, secondary_count = 2)
print(filtered)  # Should show diplomatic actions + some conflict actions
```

### Full Simulation Test

```bash
cd /d/Northeastern/LLM_Forecasting
Rscript run_simulation_with_actions.R
```

**Watch console output for:**
- "Tallying strategic direction votes..."
- "[Agent Name] → [DIRECTION]"
- "Primary direction: X (N votes)"
- "Secondary direction: Y (M votes)"
- "Filtered action set: N actions (from 49 total)"

### Verify Output Files

```r
# Check strategic votes CSV
votes_df <- read.csv("outputs/interactions/period_01_strategic_votes.csv")
print(votes_df)

# Analyze action diversity
actions_df <- read.csv("outputs/all_actions.csv")
unique_actions <- length(unique(actions_df$action))
cat("Unique actions used:", unique_actions, "out of 49\n")

# Calculate top-10 concentration
action_freq <- table(actions_df$action)
top_10_pct <- sum(head(sort(action_freq, decreasing = TRUE), 10)) / sum(action_freq) * 100
cat("Top 10 actions represent:", round(top_10_pct, 1), "% of all decisions\n")
```

**Expected improvements:**
- Unique actions: 25-35 (was 15-20)
- Top-10 concentration: 50-60% (was 70-80%)
- More even distribution across action categories

---

## Troubleshooting

### Issue: "function not found" errors

**Solution:** Make sure you sourced the files in correct order:
```r
source("src/enhanced_action_space.R")  # Defines STRATEGIC_DIRECTIONS
source("src/strategic_direction_functions.R")  # Uses STRATEGIC_DIRECTIONS
source("src/interaction_engine.R")  # Uses strategic direction functions
```

### Issue: Agents not providing strategic direction

**Problem:** LLM might not follow the two-part format consistently

**Solutions:**
1. Check the prompt includes clear PART 1 / PART 2 headers
2. Add more explicit instructions: "You MUST first choose A, B, C, D, E, or F"
3. The fallback logic in `extract_strategic_direction` should handle this

### Issue: All actions filtered out

**Problem:** Vote tallying or filtering failed

**Check:**
```r
# Debug vote extraction
test_msg <- list(content = "[Your actual agent message here]")
dir <- extract_strategic_direction(test_msg$content)
print(paste("Detected:", dir))
```

If returns NA, the pattern matching needs adjustment for your LLM's output format.

### Issue: No improvement in action diversity

**Possible causes:**
1. Filtered actions not being used in final decision
2. Decision-maker ignoring team input
3. Need to adjust primary_count/secondary_count parameters

**Check decision prompts include:**
- "AVAILABLE ACTIONS (X options from your strategic consensus)"
- Should see fewer than 49 actions listed

---

## Rollback Plan

If issues arise, rollback is simple:

```bash
cd /d/Northeastern/LLM_Forecasting
mv src/enhanced_action_space_backup.R src/enhanced_action_space.R
mv src/interaction_engine_backup.R src/interaction_engine.R
mv src/agent_decision_backup.R src/agent_decision.R
```

---

## Success Criteria

✅ **Implementation successful if:**

1. Console shows strategic vote tallying each period
2. Action options show "X actions from strategic consensus" (< 49)
3. Decision synthesis explicitly mentions team members
4. CSV file created: `period_XX_strategic_votes.csv`
5. Action diversity increases (unique actions > 25)
6. Top-10 concentration decreases (< 65%)

---

## Support

If you encounter issues:

1. Check the detailed modification guide: `STRATEGIC_DIRECTION_MODIFICATIONS.md`
2. Review function documentation in `strategic_direction_functions.R`
3. Test individual functions as shown in Step 8
4. Compare your modifications to the specification

---

**Implementation ready! Proceed with Step 1.**
