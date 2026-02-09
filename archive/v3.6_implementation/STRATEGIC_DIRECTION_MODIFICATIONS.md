# Strategic Direction Implementation Guide (v3.6)
## Two-Stage Decision Process Modifications

This document details all code changes needed to implement the two-stage decision process with strategic direction filtering.

---

## File 1: src/enhanced_action_space.R

**STATUS:** ✅ Complete new version created as `enhanced_action_space_v36.R`

**Action:** Rename `enhanced_action_space_v36.R` to `enhanced_action_space.R` (backup original first)

**Key additions:**
- `STRATEGIC_DIRECTIONS` list mapping actions to strategic categories
- `get_action_strategic_direction(action_name)` function
- `format_strategic_directions()` function for prompts
- `format_filtered_actions(action_list, state)` function for filtered action display

---

## File 2: src/interaction_engine.R

### Modification 1: Add Strategic Direction Utility Functions

**Location:** After line 417 (before `generate_dynamic_action_options`)

**Add these functions:**

```r
#' Extract strategic direction from agent response
#'
#' @param response Agent's Round 1 response text
#' @return Strategic direction code (DIPLOMATIC, ECONOMIC, etc.) or NA
extract_strategic_direction <- function(response) {
  response_upper <- toupper(response)

  # Look for explicit direction codes (A, B, C, D, E, F)
  patterns <- list(
    "\\[A\\]|OPTION A|DIRECTION A|\\bA\\b.*DIPLOMATIC|STRATEGIC DIRECTION.*A" = "DIPLOMATIC",
    "\\[B\\]|OPTION B|DIRECTION B|\\bB\\b.*ECONOMIC|STRATEGIC DIRECTION.*B" = "ECONOMIC",
    "\\[C\\]|OPTION C|DIRECTION C|\\bC\\b.*MILITARY POSTURE|STRATEGIC DIRECTION.*C" = "MILITARY_POSTURE",
    "\\[D\\]|OPTION D|DIRECTION D|\\bD\\b.*COVERT|STRATEGIC DIRECTION.*D" = "COVERT",
    "\\[E\\]|OPTION E|DIRECTION E|\\bE\\b.*OPEN CONFLICT|\\bE\\b.*CONFLICT|STRATEGIC DIRECTION.*E" = "OPEN_CONFLICT",
    "\\[F\\]|OPTION F|DIRECTION F|\\bF\\b.*WMD|\\bF\\b.*ESCALATION|STRATEGIC DIRECTION.*F" = "WMD"
  )

  # Try pattern matching
  for (pattern in names(patterns)) {
    if (grepl(pattern, response_upper)) {
      return(patterns[[pattern]])
    }
  }

  # Fallback: Look for direction names directly
  direction_keywords <- list(
    "DIPLOMATIC PATH|DIPLOMACY|NEGOTIATION" = "DIPLOMATIC",
    "ECONOMIC PRESSURE|SANCTIONS|ECONOMIC WARFARE" = "ECONOMIC",
    "MILITARY POSTURE|BUILDUP|READINESS" = "MILITARY_POSTURE",
    "COVERT OPERATION|INTELLIGENCE|CLANDESTINE" = "COVERT",
    "OPEN CONFLICT|KINETIC|DIRECT ATTACK|MILITARY ACTION" = "OPEN_CONFLICT",
    "WMD|NUCLEAR|EXTREME" = "WMD"
  )

  for (keyword in names(direction_keywords)) {
    if (grepl(keyword, response_upper)) {
      return(direction_keywords[[keyword]])
    }
  }

  # If no direction found, try to infer from recommended action
  for (dir_name in names(STRATEGIC_DIRECTIONS)) {
    dir_actions <- STRATEGIC_DIRECTIONS[[dir_name]]$actions
    for (action in dir_actions) {
      if (grepl(toupper(action), response_upper)) {
        cat(sprintf("    Note: Inferred %s from action '%s'\n", dir_name, action))
        return(dir_name)
      }
    }
  }

  return(NA)
}

#' Tally strategic direction votes from Round 1
#'
#' @param round_1_responses List of agent responses from Round 1
#' @return Named vector of vote counts by direction
tally_strategic_votes <- function(round_1_responses) {
  votes <- c()

  for (i in seq_along(round_1_responses)) {
    response <- round_1_responses[[i]]
    agent_name <- if (!is.null(response$sender_name)) response$sender_name else names(round_1_responses)[i]

    direction <- extract_strategic_direction(response$content)

    if (!is.na(direction)) {
      votes <- c(votes, direction)
      cat(sprintf("    %s → %s\n", agent_name, direction))
    } else {
      cat(sprintf("    %s → UNCLEAR (will include diverse options)\n", agent_name))
    }
  }

  # Count votes
  if (length(votes) > 0) {
    vote_counts <- table(votes)
    return(vote_counts)
  } else {
    return(c())
  }
}

#' Build filtered action set based on strategic votes
#'
#' @param vote_counts Named vector of vote counts from tally_strategic_votes
#' @param primary_count Number of actions from majority direction (default 6)
#' @param secondary_count Number of actions from minority direction (default 2)
#' @param min_threshold Minimum votes to be considered (default 1)
#' @return Character vector of action names
build_filtered_action_set <- function(vote_counts,
                                       primary_count = 6,
                                       secondary_count = 2,
                                       min_threshold = 1) {

  if (length(vote_counts) == 0) {
    # Fallback: if no clear votes, include diverse sample from all directions
    cat("    No clear strategic votes - including diverse action set\n")
    filtered_actions <- c()
    for (dir_name in names(STRATEGIC_DIRECTIONS)) {
      dir_actions <- STRATEGIC_DIRECTIONS[[dir_name]]$actions
      filtered_actions <- c(filtered_actions, head(dir_actions, 2))
    }
    return(filtered_actions)
  }

  # Sort by vote count
  vote_counts_sorted <- sort(vote_counts, decreasing = TRUE)

  # Get primary direction (most votes)
  primary_direction <- names(vote_counts_sorted)[1]
  primary_votes <- vote_counts_sorted[1]

  cat(sprintf("\n    Primary direction: %s (%d votes)\n", primary_direction, primary_votes))

  # Get all actions from primary direction
  primary_actions <- STRATEGIC_DIRECTIONS[[primary_direction]]$actions
  filtered_actions <- head(primary_actions, min(primary_count, length(primary_actions)))

  # Add secondary direction if there's meaningful minority
  if (length(vote_counts_sorted) > 1) {
    secondary_direction <- names(vote_counts_sorted)[2]
    secondary_votes <- vote_counts_sorted[2]

    if (secondary_votes >= min_threshold) {
      cat(sprintf("    Secondary direction: %s (%d votes)\n", secondary_direction, secondary_votes))

      secondary_actions <- STRATEGIC_DIRECTIONS[[secondary_direction]]$actions
      filtered_actions <- c(filtered_actions, head(secondary_actions, min(secondary_count, length(secondary_actions))))
    }
  }

  cat(sprintf("    Filtered action set: %d actions (from 49 total)\n\n", length(filtered_actions)))

  return(filtered_actions)
}
```

### Modification 2: Update Round 1 Prompt in run_pre_action_coordination

**Location:** Lines 796-854 (Round 1 prompt construction)

**Replace the existing Round 1 prompt with:**

```r
        # Get strategic directions text for the prompt
        strategic_directions_text <- format_strategic_directions()

        prompt <- sprintf(
"INTERNAL STRATEGY MEETING - %s FACTION

=== WHO YOU ARE ===
You are %s (%s, %s worldview).

%s

%s

%s

%s

%s

=== CURRENT SITUATION ===
%s

=== RECENT EVENTS ===
%s

=== YOUR FACTION'S PERSPECTIVE ===
%s

=== YOUR TASK ===

This is a TWO-PART recommendation:

**PART 1 - STRATEGIC DIRECTION:**
First, recommend the broad strategic approach your faction should take:

%s

Which strategic direction [A/B/C/D/E/F] do you recommend and why?

**PART 2 - SPECIFIC ACTION:**
Based on your strategic direction, recommend a SPECIFIC action from that category.

FORMAT YOUR RESPONSE AS:

STRATEGIC DIRECTION: [A/B/C/D/E/F] - [Direction name]
REASONING: [1-2 sentences on why this strategic approach is appropriate given the situation]

RECOMMENDED ACTION: [exact action name - e.g., 'military_buildup', 'peace_talks']
RATIONALE: [2-3 sentences in YOUR voice, explaining why this specific action within your strategic direction]
RISKS: [1-2 key risks from your perspective]
ALTERNATIVE CONSIDERED: [What other action did you consider? Why did you reject it?]

Remember:
- Choose strategic direction FIRST based on the overall situation
- Then select the best tactical action within that direction
- Stay in character - argue from your worldview and role
- Be specific about risks and tradeoffs
- Consider your covert capabilities when evaluating covert options
- Consider YOUR PERSONAL INTERESTS - they may not perfectly align with faction objectives

Speak IN CHARACTER. A hawk should sound like a hawk. A dove should sound like a dove.",
          toupper(gsub("_", " ", faction)),
          agent$name,
          hawk_dove_label,
          worldview_label,
          agent_description,
          agent_speech_style,
          agent_typical_args,
          covert_desc,
          interpersonal_desc,
          situation_summary,
          events_summary,
          faction_perspective,
          strategic_directions_text
        )
```

### Modification 3: Add Strategic Vote Tallying Between Rounds

**Location:** After line 992 (after Round 1 completes, before Round 2 begins)

**Add this code block:**

```r
  } # End of round 1

  # === NEW: Tally strategic votes and filter actions ===
  if (round == 1) {
    cat("\n  Tallying strategic direction votes...\n")
    strategic_votes <- tally_strategic_votes(messages)

    cat("\n  Building filtered action set based on strategic consensus...\n")
    filtered_actions <- build_filtered_action_set(
      strategic_votes,
      primary_count = 6,
      secondary_count = 2
    )

    # Generate filtered action options text for Round 2 and final decision
    action_options_filtered <- format_filtered_actions(filtered_actions, context$scenario_state)
  } else {
    # Round 2 - use filtered actions
```

### Modification 4: Update Round 2 to Use Filtered Actions

**Location:** Line 822 in the action_options reference (inside Round 1 prompt)

**Change:** The Round 2 prompt doesn't explicitly show action options, but the filtered set should be available for the final decision. Round 2 focuses on debate, not action selection.

**No changes needed to Round 2 prompt itself.**

### Modification 5: Return Strategic Votes in Coordination Record

**Location:** Lines 994-1003 (return statement of run_pre_action_coordination)

**Replace with:**

```r
  # Return coordination record with all input INCLUDING strategic votes
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

## File 3: src/agent_decision.R

### Modification 1: Add Decision Synthesis Requirement

**Location:** Search for where the final action decision prompt is constructed (likely in `agent_decide_action` function)

**Find the section that builds the decision prompt when coordination input exists**

**Add this synthesis requirement:**

```r
# If coordination input exists, require explicit synthesis
if (!is.null(coordination_input) && !is.null(coordination_input$round_2_responses)) {

  # Format Round 2 positions for review
  round_2_summary <- paste(sapply(coordination_input$round_2_responses, function(r) {
    sprintf("[%s]: %s", r$sender_name, substr(r$content, 1, 400))
  }), collapse = "\n\n")

  # Format strategic votes if available
  strategic_summary <- ""
  if (!is.null(coordination_input$strategic_votes)) {
    vote_text <- paste(names(coordination_input$strategic_votes),
                      coordination_input$strategic_votes, sep = " (", collapse = " votes), ")
    strategic_summary <- sprintf("\nStrategic direction votes: %s votes)", vote_text)
  }

  synthesis_requirement <- sprintf("

=== TEAM INPUT RECEIVED ===

Your team has debated the strategic approach and specific options.%s

Round 2 positions:
%s

=== YOUR DECISION PROCESS (REQUIRED) ===

Before making your final decision, you must synthesize the team input:

1. POSITIONS SUMMARY: What are the main options being debated?
   - Strategic directions proposed: %s
   - Specific actions recommended: [list 2-3 key action recommendations]

2. CRITICAL CONCERNS: What are the most serious warnings raised?
   - [Agent name]'s concern about [specific risk]
   - [Agent name]'s point about [consequence]

3. YOUR REASONING:
   - Which arguments are most compelling given the current situation?
   - Why are you prioritizing [value/goal X] over [value/goal Y]?
   - What's the strongest case AGAINST your choice, and why do you proceed anyway?

4. FINAL DECISION: [action_name]
   Justification: [How this choice balances competing concerns from the debate]

Your decision will be evaluated on whether it shows genuine integration of team perspectives, not just confirmation of your priors.
Be specific about which colleagues' arguments influenced you and how.
",
    strategic_summary,
    round_2_summary,
    if (!is.null(coordination_input$strategic_votes)) {
      paste(names(coordination_input$strategic_votes), collapse = ", ")
    } else {
      "Not clearly specified"
    }
  )

  decision_prompt <- paste0(decision_prompt, synthesis_requirement)
}
```

### Modification 2: Use Filtered Actions in Final Decision

**Location:** Where available actions are presented to decision-maker

**Add logic to use filtered actions if available:**

```r
# Use filtered action set if available from coordination, otherwise use all actions
available_actions <- if (!is.null(coordination_input$filtered_actions)) {
  cat("  Using filtered action set from strategic consensus\n")
  coordination_input$action_options_filtered
} else {
  cat("  Using full action set (no pre-coordination)\n")
  generate_dynamic_action_options(agent$faction, context, NULL)
}

# Add available_actions to decision prompt
decision_prompt <- paste0(decision_prompt, "\n\n", available_actions)
```

---

## File 4: src/state_manager.R (or create new file)

### Add Strategic Vote Logging Function

**Create new function:**

```r
#' Save strategic votes to CSV for analysis
#'
#' @param period Current period number
#' @param coordination_records List of coordination records from all factions
#' @param output_dir Output directory (default: "outputs/interactions")
save_strategic_votes_to_csv <- function(period, coordination_records, output_dir = "outputs/interactions") {

  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  # Collect all strategic votes from all factions
  votes_data <- list()

  for (coord in coordination_records) {
    if (!is.null(coord$strategic_votes)) {
      for (direction in names(coord$strategic_votes)) {
        votes_data[[length(votes_data) + 1]] <- data.frame(
          period = period,
          faction = coord$faction,
          direction = direction,
          vote_count = as.numeric(coord$strategic_votes[direction]),
          filtered_actions = paste(coord$filtered_actions, collapse = "; "),
          timestamp = Sys.time(),
          stringsAsFactors = FALSE
        )
      }
    }
  }

  if (length(votes_data) > 0) {
    votes_df <- do.call(rbind, votes_data)

    csv_file <- file.path(output_dir, sprintf("period_%02d_strategic_votes.csv", period))
    write.csv(votes_df, csv_file, row.names = FALSE)

    cat(sprintf("  Saved strategic votes to: %s\n", csv_file))
    return(csv_file)
  }

  return(NULL)
}
```

---

## Testing & Validation

After implementing these changes:

1. **Run a test simulation:**
   ```bash
   Rscript run_simulation_with_actions.R
   ```

2. **Check console output for:**
   - "Tallying strategic direction votes..."
   - Agent names → Strategic directions
   - "Primary direction: X (N votes)"
   - "Filtered action set: N actions"

3. **Verify output files:**
   ```r
   # Check strategic votes were logged
   votes <- read.csv("outputs/interactions/period_01_strategic_votes.csv")
   print(votes)

   # Check action diversity improved
   actions <- read.csv("outputs/all_actions.csv")
   cat("Unique actions used:", length(unique(actions$action)), "/ 49\n")
   ```

4. **Compare to baseline:**
   - Pre-implementation: ~15-20 unique actions, top-10 = 70-80%
   - Expected post-implementation: ~25-35 unique actions, top-10 = 50-60%

---

## Summary of Changes

- **enhanced_action_space.R**: Added strategic direction mappings and utility functions
- **interaction_engine.R**:
  - Added strategic direction extraction and tallying functions
  - Modified Round 1 prompt to request strategic direction
  - Added vote tallying between rounds
  - Modified coordination return to include votes and filtered actions
- **agent_decision.R**:
  - Added decision synthesis requirement
  - Uses filtered actions when available
- **state_manager.R**: Added strategic vote CSV logging

**Total new code:** ~300 lines
**Modified sections:** ~50 lines
**Expected result:** Better action diversity, clearer deliberation, reduced cognitive overload
