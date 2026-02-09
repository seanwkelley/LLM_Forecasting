# Strategic Direction Functions for Two-Stage Decision Process
# v3.6 - Add to interaction_engine.R or source separately
#
# These functions implement the strategic direction filtering system
# to reduce cognitive overload and improve action diversity

#' Extract strategic direction from agent response
#'
#' Parses agent's Round 1 response to identify their strategic preference
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

  # Try pattern matching first (most reliable)
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

  # Final fallback: Try to infer from recommended action
  # Requires STRATEGIC_DIRECTIONS to be loaded
  if (exists("STRATEGIC_DIRECTIONS")) {
    for (dir_name in names(STRATEGIC_DIRECTIONS)) {
      dir_actions <- STRATEGIC_DIRECTIONS[[dir_name]]$actions
      for (action in dir_actions) {
        if (grepl(toupper(action), response_upper)) {
          cat(sprintf("    Note: Inferred %s from action '%s'\n", dir_name, action))
          return(dir_name)
        }
      }
    }
  }

  return(NA)
}

#' Tally strategic direction votes from Round 1
#'
#' Analyzes all Round 1 responses to count votes for each strategic direction
#'
#' @param round_1_responses List of agent response objects from Round 1
#'   Each response should have $content and optionally $sender_name
#' @return Named vector of vote counts by direction, or empty vector if no votes
tally_strategic_votes <- function(round_1_responses) {
  votes <- c()

  for (i in seq_along(round_1_responses)) {
    response <- round_1_responses[[i]]

    # Get agent name from response object or list names
    agent_name <- if (!is.null(response$sender_name)) {
      response$sender_name
    } else if (!is.null(names(round_1_responses)[i])) {
      names(round_1_responses)[i]
    } else {
      sprintf("Agent_%d", i)
    }

    # Extract strategic direction from response content
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
#' Selects subset of actions based on strategic consensus:
#' - Majority direction: Include all actions from this category
#' - Minority direction: Include top actions for accommodation
#'
#' @param vote_counts Named vector of vote counts from tally_strategic_votes
#' @param primary_count Number of actions from majority direction (default 6)
#' @param secondary_count Number of actions from minority direction (default 2)
#' @param min_threshold Minimum votes to be considered as secondary (default 1)
#' @return Character vector of action names
build_filtered_action_set <- function(vote_counts,
                                       primary_count = 6,
                                       secondary_count = 2,
                                       min_threshold = 1) {

  # Check if STRATEGIC_DIRECTIONS is available
  if (!exists("STRATEGIC_DIRECTIONS")) {
    warning("STRATEGIC_DIRECTIONS not found. Please source enhanced_action_space.R first.")
    return(c())
  }

  # Fallback if no votes
  if (length(vote_counts) == 0) {
    cat("    No clear strategic votes - including diverse action set\n")
    filtered_actions <- c()
    for (dir_name in names(STRATEGIC_DIRECTIONS)) {
      dir_actions <- STRATEGIC_DIRECTIONS[[dir_name]]$actions
      # Take first 2 from each direction for diversity
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

  # Get actions from primary direction
  primary_actions <- STRATEGIC_DIRECTIONS[[primary_direction]]$actions
  # Take up to primary_count actions, or all if fewer available
  filtered_actions <- head(primary_actions, min(primary_count, length(primary_actions)))

  # Add secondary direction if there's meaningful minority
  if (length(vote_counts_sorted) > 1) {
    secondary_direction <- names(vote_counts_sorted)[2]
    secondary_votes <- vote_counts_sorted[2]

    if (secondary_votes >= min_threshold) {
      cat(sprintf("    Secondary direction: %s (%d votes) - minority view accommodated\n",
                  secondary_direction, secondary_votes))

      secondary_actions <- STRATEGIC_DIRECTIONS[[secondary_direction]]$actions
      # Add top secondary_count actions from minority direction
      filtered_actions <- c(filtered_actions,
                           head(secondary_actions, min(secondary_count, length(secondary_actions))))
    }
  }

  cat(sprintf("    Filtered action set: %d actions (from 49 total)\n\n",
              length(filtered_actions)))

  return(filtered_actions)
}

#' Format filtered action set for display in prompts
#'
#' Creates a formatted string describing the filtered actions,
#' organized by strategic direction for clarity
#'
#' @param action_list Vector of action names to include
#' @param state Current simulation state for contextual information (optional)
#' @return Formatted string with action details
format_filtered_actions_for_prompt <- function(action_list, state = NULL) {
  if (length(action_list) == 0) {
    return("ERROR: No actions available")
  }

  # Group by strategic direction for clarity
  by_direction <- list()
  for (action_name in action_list) {
    direction <- get_action_strategic_direction(action_name)
    if (is.null(by_direction[[direction]])) {
      by_direction[[direction]] <- c()
    }
    by_direction[[direction]] <- c(by_direction[[direction]], action_name)
  }

  actions_text <- sprintf("=== AVAILABLE ACTIONS (%d options based on strategic consensus) ===\n\n",
                         length(action_list))

  for (direction in names(by_direction)) {
    if (direction == "UNKNOWN") next

    dir_info <- STRATEGIC_DIRECTIONS[[direction]]
    actions_text <- paste0(actions_text,
                          sprintf("--- %s ---\n", dir_info$label))

    for (action in by_direction[[direction]]) {
      # Get action details if ACTION_DEFINITIONS exists
      action_desc <- action  # Fallback
      if (exists("ACTION_DEFINITIONS") && action %in% names(ACTION_DEFINITIONS)) {
        def <- ACTION_DEFINITIONS[[action]]
        action_desc <- sprintf("  • %s - %s\n    Cost: $%.1fB | Effects: %s",
                              action,
                              def$description,
                              def$cost_billions,
                              def$primary_effect)
      } else {
        action_desc <- sprintf("  • %s", action)
      }
      actions_text <- paste0(actions_text, action_desc, "\n")
    }
    actions_text <- paste0(actions_text, "\n")
  }

  return(actions_text)
}

#' Save strategic votes to CSV for analysis
#'
#' Logs strategic direction votes from all factions to CSV file
#'
#' @param period Current period number
#' @param coordination_records List of coordination records from all factions
#' @param output_dir Output directory (default: "outputs/interactions")
#' @return Path to CSV file, or NULL if no votes to save
save_strategic_votes_to_csv <- function(period, coordination_records,
                                        output_dir = "outputs/interactions") {

  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  # Collect all strategic votes from all factions
  votes_data <- list()

  for (coord in coordination_records) {
    if (!is.null(coord$strategic_votes) && length(coord$strategic_votes) > 0) {
      for (direction in names(coord$strategic_votes)) {
        votes_data[[length(votes_data) + 1]] <- data.frame(
          period = period,
          faction = coord$faction,
          direction = direction,
          vote_count = as.numeric(coord$strategic_votes[direction]),
          filtered_actions = if (!is.null(coord$filtered_actions)) {
            paste(coord$filtered_actions, collapse = "; ")
          } else {
            ""
          },
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

cat("Strategic direction functions loaded (v3.6)\n")
cat("  - extract_strategic_direction()\n")
cat("  - tally_strategic_votes()\n")
cat("  - build_filtered_action_set()\n")
cat("  - format_filtered_actions_for_prompt()\n")
cat("  - save_strategic_votes_to_csv()\n")
