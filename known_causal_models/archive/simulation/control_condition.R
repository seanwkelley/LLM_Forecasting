# Control Condition Generation for Forecasting Experiments
#
# Implements constrained randomization to break information→outcome connection
# while maintaining local plausibility

#' Generate control condition from true simulation state
#'
#' Creates a control condition by randomizing three layers:
#' 1. State metrics: Permute across periods with constraints
#' 2. Event narratives: Permute and flip beneficiaries
#' 3. Outcome: Keep same final outcome (government survived/collapsed)
#'
#' @param state True simulation state object
#' @return Control condition state object with randomized information
generate_control_condition <- function(state) {
  control_state <- state

  n_periods <- state$current_period

  # Layer 1: Permute state metrics across periods (with constraints)
  control_state <- permute_state_metrics(control_state, n_periods)

  # Layer 2: Permute and flip event narratives
  control_state <- permute_event_narratives(control_state, n_periods)

  # Layer 3: Keep same final outcome
  # (assessments_history outcome remains the same, but intermediate probabilities randomized)
  control_state <- randomize_intermediate_probabilities(control_state, n_periods)

  return(control_state)
}

#' Permute state metrics across periods with local coherence constraints
#'
#' @param state State object
#' @param n_periods Number of periods
#' @return State with permuted metrics
permute_state_metrics <- function(state, n_periods) {
  # Extract metric time series from state_history
  territory <- sapply(1:n_periods, function(p) {
    if (!is.null(state$state_history[[p]]$scenario_state$territory_controlled)) {
      state$state_history[[p]]$scenario_state$territory_controlled
    } else {
      state$scenario_state$territory_controlled
    }
  })

  crisis <- sapply(1:n_periods, function(p) {
    if (!is.null(state$state_history[[p]]$scenario_state$crisis_level)) {
      state$state_history[[p]]$scenario_state$crisis_level
    } else {
      state$scenario_state$crisis_level
    }
  })

  sanctions <- sapply(1:n_periods, function(p) {
    if (!is.null(state$state_history[[p]]$scenario_state$sanctions_level)) {
      state$state_history[[p]]$scenario_state$sanctions_level
    } else {
      state$scenario_state$sanctions_level
    }
  })

  military_balance <- sapply(1:n_periods, function(p) {
    if (!is.null(state$state_history[[p]]$scenario_state$military_balance)) {
      state$state_history[[p]]$scenario_state$military_balance
    } else {
      state$scenario_state$military_balance
    }
  })

  # Constrained permutation: allow small local jumps, prevent nonsensical sequences
  # Strategy: shuffle with constraints on maximum period-to-period change
  territory_perm <- constrained_shuffle(territory, max_jump = 0.15)
  crisis_perm <- constrained_shuffle(crisis, max_jump = 3)
  sanctions_perm <- constrained_shuffle(sanctions, max_jump = 0.20)
  military_perm <- constrained_shuffle(military_balance, max_jump = 0.3)

  # Apply permuted values back to state_history
  for (p in 1:n_periods) {
    if (is.null(state$state_history[[p]]$scenario_state)) {
      state$state_history[[p]]$scenario_state <- state$scenario_state
    }

    state$state_history[[p]]$scenario_state$territory_controlled <- territory_perm[p]
    state$state_history[[p]]$scenario_state$crisis_level <- crisis_perm[p]
    state$state_history[[p]]$scenario_state$sanctions_level <- sanctions_perm[p]
    state$state_history[[p]]$scenario_state$military_balance <- military_perm[p]
  }

  # Update current state to last period values
  state$scenario_state$territory_controlled <- territory_perm[n_periods]
  state$scenario_state$crisis_level <- crisis_perm[n_periods]
  state$scenario_state$sanctions_level <- sanctions_perm[n_periods]
  state$scenario_state$military_balance <- military_perm[n_periods]

  return(state)
}

#' Constrained shuffle that prevents extreme jumps
#'
#' @param values Numeric vector to shuffle
#' @param max_jump Maximum allowed period-to-period change
#' @return Shuffled vector with constraints
constrained_shuffle <- function(values, max_jump) {
  n <- length(values)
  if (n <= 1) return(values)

  # Start with a random permutation
  shuffled <- sample(values)

  # Iteratively swap elements to reduce violations of max_jump constraint
  max_iterations <- 100
  for (iter in 1:max_iterations) {
    violations <- 0

    for (i in 1:(n-1)) {
      if (abs(shuffled[i+1] - shuffled[i]) > max_jump) {
        violations <- violations + 1

        # Try to find a better swap
        candidates <- which(abs(shuffled - shuffled[i]) <= max_jump)
        candidates <- candidates[candidates > i & candidates <= min(i+3, n)]

        if (length(candidates) > 0) {
          swap_idx <- sample(candidates, 1)
          temp <- shuffled[i+1]
          shuffled[i+1] <- shuffled[swap_idx]
          shuffled[swap_idx] <- temp
        }
      }
    }

    if (violations == 0) break
  }

  return(shuffled)
}

#' Permute event narratives and flip beneficiaries
#'
#' @param state State object
#' @param n_periods Number of periods
#' @return State with permuted and flipped events
permute_event_narratives <- function(state, n_periods) {
  # Extract all events
  all_events <- list()
  for (p in 1:n_periods) {
    if (length(state$events_history[[p]]) > 0) {
      all_events <- c(all_events, state$events_history[[p]])
    }
  }

  if (length(all_events) == 0) return(state)

  # Shuffle events
  shuffled_events <- sample(all_events)

  # Flip beneficiaries with 50% probability per event
  flipped_events <- lapply(shuffled_events, function(event) {
    if (runif(1) < 0.5) {
      flip_event_beneficiary(event)
    } else {
      event
    }
  })

  # Randomize magnitudes
  randomized_events <- lapply(flipped_events, randomize_event_magnitude)

  # Redistribute events across periods
  events_per_period <- sapply(1:n_periods, function(p) length(state$events_history[[p]]))

  event_idx <- 1
  for (p in 1:n_periods) {
    n_events <- events_per_period[p]
    if (n_events > 0 && event_idx <= length(randomized_events)) {
      state$events_history[[p]] <- randomized_events[event_idx:min(event_idx + n_events - 1, length(randomized_events))]
      event_idx <- event_idx + n_events
    } else {
      state$events_history[[p]] <- list()
    }
  }

  return(state)
}

#' Flip event beneficiary (aggressor ↔ defender)
#'
#' @param event Event object
#' @return Event with flipped beneficiary
flip_event_beneficiary <- function(event) {
  flipped_event <- event

  # Flip description text
  flipped_event$description <- swap_actors(event$description)

  # Flip name if it contains actor names
  flipped_event$name <- swap_actors(event$name)

  # Reverse numeric effects if present
  if (!is.null(event$military_impact)) {
    flipped_event$military_impact <- -event$military_impact
  }
  if (!is.null(event$economic_impact)) {
    flipped_event$economic_impact <- -event$economic_impact
  }
  if (!is.null(event$territorial_impact)) {
    flipped_event$territorial_impact <- -event$territorial_impact
  }

  return(flipped_event)
}

#' Swap actor names in text (aggressor ↔ defender)
#'
#' @param text Text string
#' @return Text with swapped actors
swap_actors <- function(text) {
  # Define actor name mappings
  mappings <- list(
    c("Novaris", "__TEMP_NOVARIS__"),
    c("Tethys", "Novaris"),
    c("__TEMP_NOVARIS__", "Tethys"),
    c("major power", "__TEMP_MAJOR__"),
    c("smaller power", "major power"),
    c("__TEMP_MAJOR__", "smaller power"),
    c("aggressor", "__TEMP_AGG__"),
    c("defender", "aggressor"),
    c("__TEMP_AGG__", "defender"),
    c("offensive", "__TEMP_OFF__"),
    c("defensive", "offensive"),
    c("__TEMP_OFF__", "defensive")
  )

  result <- text
  for (mapping in mappings) {
    result <- gsub(mapping[1], mapping[2], result, ignore.case = TRUE)
  }

  return(result)
}

#' Randomize numeric magnitudes in event descriptions
#'
#' @param event Event object
#' @return Event with randomized magnitudes
randomize_event_magnitude <- function(event) {
  randomized_event <- event

  # Find numbers in description and randomize them (±30%)
  desc <- event$description

  # Pattern to match numbers (including decimals and percentages)
  numbers <- gregexpr("[0-9]+\\.?[0-9]*", desc, perl = TRUE)
  matches <- regmatches(desc, numbers)[[1]]

  if (length(matches) > 0) {
    for (match in matches) {
      original <- as.numeric(match)
      # Randomize by ±30%
      randomized <- original * runif(1, 0.7, 1.3)
      # Round appropriately
      if (original >= 10) {
        randomized <- round(randomized)
      } else {
        randomized <- round(randomized, 1)
      }

      desc <- sub(match, as.character(randomized), desc, fixed = TRUE)
    }

    randomized_event$description <- desc
  }

  return(randomized_event)
}

#' Randomize intermediate probability assessments while keeping final outcome
#'
#' @param state State object
#' @param n_periods Number of periods
#' @return State with randomized intermediate probabilities
randomize_intermediate_probabilities <- function(state, n_periods) {
  if (n_periods < 2) return(state)

  # Keep final outcome the same
  final_prob <- state$assessments_history[[n_periods]]$probability
  final_outcome_collapsed <- final_prob > 0.5

  # Generate random walk for intermediate periods
  # Start from random initial value, trend toward final outcome
  initial_prob <- runif(1, 0.2, 0.8)

  for (p in 1:(n_periods-1)) {
    # Random walk with trend toward final outcome
    trend <- (final_prob - initial_prob) / n_periods
    noise <- rnorm(1, 0, 0.1)

    prob <- initial_prob + trend * p + noise
    prob <- max(0, min(1, prob))  # Constrain to [0,1]

    state$assessments_history[[p]]$probability <- prob
  }

  # Final period keeps true outcome
  state$assessments_history[[n_periods]]$probability <- final_prob

  return(state)
}

#' Generate human-readable summary of control condition changes
#'
#' @param true_state Original state
#' @param control_state Control condition state
#' @return Character string with summary
summarize_control_changes <- function(true_state, control_state) {
  n_periods <- true_state$current_period

  summary <- "CONTROL CONDITION RANDOMIZATION SUMMARY\n"
  summary <- paste0(summary, paste(rep("=", 60), collapse = ""), "\n\n")

  # Metric changes
  summary <- paste0(summary, "STATE METRIC CHANGES:\n")
  for (p in 1:n_periods) {
    true_terr <- true_state$state_history[[p]]$scenario_state$territory_controlled
    ctrl_terr <- control_state$state_history[[p]]$scenario_state$territory_controlled

    summary <- paste0(summary, sprintf(
      "Period %d: Territory %.1f%% → %.1f%%\n",
      p, true_terr * 100, ctrl_terr * 100
    ))
  }

  summary <- paste0(summary, "\n")

  # Event flips
  n_events_flipped <- 0
  for (p in 1:n_periods) {
    true_events <- true_state$events_history[[p]]
    ctrl_events <- control_state$events_history[[p]]

    if (length(true_events) > 0 && length(ctrl_events) > 0) {
      for (i in seq_along(ctrl_events)) {
        if (grepl("Tethys", ctrl_events[[i]]$description) != grepl("Tethys", true_events[[i]]$description)) {
          n_events_flipped <- n_events_flipped + 1
        }
      }
    }
  }

  summary <- paste0(summary, sprintf(
    "NARRATIVE CHANGES:\n%d events had beneficiaries flipped\n",
    n_events_flipped
  ))

  summary <- paste0(summary, "\n")

  # Final outcome
  final_true <- true_state$assessments_history[[n_periods]]$probability
  final_ctrl <- control_state$assessments_history[[n_periods]]$probability

  summary <- paste0(summary, sprintf(
    "FINAL OUTCOME:\nTrue: %.1f%% | Control: %.1f%% (same outcome preserved)\n",
    final_true * 100, final_ctrl * 100
  ))

  return(summary)
}
