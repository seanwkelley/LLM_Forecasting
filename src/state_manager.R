# State manager and logging system

library(jsonlite)
library(uuid)

#' Initialize simulation state
#'
#' @param config Configuration list
#' @return Simulation state object
initialize_simulation <- function(config) {
  # Load scenario preset
  preset_name <- if (!is.null(SCENARIO_PRESET)) SCENARIO_PRESET else "medium_intensity"
  preset <- SCENARIO_PRESETS[[preset_name]]

  if (is.null(preset)) {
    cat(sprintf("WARNING: Scenario preset '%s' not found. Using medium_intensity.\n", preset_name))
    preset <- SCENARIO_PRESETS[["medium_intensity"]]
  }

  cat(sprintf("\n=== SCENARIO: %s ===\n", preset$name))
  cat(sprintf("Territory: %.0f-%.0f%% | Crisis: %.0f/10 | Sanctions: %.0f%%\n\n",
              preset$territory_controlled[1] * 100,
              preset$territory_controlled[2] * 100,
              preset$crisis_level,
              preset$sanctions_level * 100))

  state <- list(
    simulation_id = UUIDgenerate(),
    start_time = Sys.time(),
    config = config,
    current_period = 0,
    scenario_preset = preset_name,
    agents = lapply(config$agents, create_agent),
    events_history = list(),
    interactions_history = list(),
    assessments_history = list(),
    scenario_state = list(
      current_day = 0,
      situation_summary = paste(preset$situation, "This is an academic research simulation."),
      recent_events = c(
        "Major power launched military operations with ground forces",
        "Smaller power activated defense protocols and mobilized reserves",
        "International community imposed sanctions on major power",
        "Allied nations announced support for smaller power"
      ),
      military_balance = runif(1, preset$military_balance[1], preset$military_balance[2]),
      sanctions_level = preset$sanctions_level,
      international_support = preset$international_support,
      crisis_level = preset$crisis_level,
      territory_controlled = runif(1, preset$territory_controlled[1], preset$territory_controlled[2]),
      nuclear_used = FALSE,
      momentum = preset$momentum,
      consecutive_wins_defender = 0,
      consecutive_wins_aggressor = preset$consecutive_wins_aggressor
    )
  )

  class(state) <- c("simulation_state", "list")
  return(state)
}

#' Update scenario state based on events and interactions
#'
#' @param state Simulation state
#' @param period Current period
#' @param events Events from this period
#' @param assessment Aggregator assessment
#' @return Updated state
update_scenario_state <- function(state, period, events, assessment) {
  state$scenario_state$current_day <- period * 7

  # Update military balance based on battlefield events with momentum
  for (event in events) {
    if (event$type == "battlefield") {
      # Check if impact_type exists before using it
      if (!is.null(event$impact_type) && length(event$impact_type) > 0) {
        if (event$impact_type == "defender_success") {
          # Track consecutive wins for momentum
          state$scenario_state$consecutive_wins_defender <-
            state$scenario_state$consecutive_wins_defender + 1
          state$scenario_state$consecutive_wins_aggressor <- 0

          # Momentum bonus: each consecutive win adds 0.05 to the effect
          momentum_bonus <- min(0.15, state$scenario_state$consecutive_wins_defender * 0.05)
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance + 0.1 + momentum_bonus))
          state$scenario_state$momentum <- state$scenario_state$momentum + 0.1

          # Territory recapture: defender recovers 2-5% of territory
          territory_loss <- runif(1, 0.02, 0.05)
          state$scenario_state$territory_controlled <-
            max(0, state$scenario_state$territory_controlled - territory_loss)

        } else if (event$impact_type == "aggressor_success") {
          # Track consecutive wins for momentum
          state$scenario_state$consecutive_wins_aggressor <-
            state$scenario_state$consecutive_wins_aggressor + 1
          state$scenario_state$consecutive_wins_defender <- 0

          # Momentum bonus: each consecutive win adds 0.05 to the effect
          momentum_bonus <- min(0.15, state$scenario_state$consecutive_wins_aggressor * 0.05)
          state$scenario_state$military_balance <-
            max(-1, min(1, state$scenario_state$military_balance - 0.1 - momentum_bonus))
          state$scenario_state$momentum <- state$scenario_state$momentum - 0.1

          # Territory capture: aggressor takes 3-8% of territory
          territory_gain <- runif(1, 0.03, 0.08)
          state$scenario_state$territory_controlled <-
            min(1.0, state$scenario_state$territory_controlled + territory_gain)

        } else if (grepl("aggressor_advance", event$impact_type)) {
          # Limited advance: aggressor takes 1-3% of territory
          territory_gain <- runif(1, 0.01, 0.03)
          state$scenario_state$territory_controlled <-
            min(1.0, state$scenario_state$territory_controlled + territory_gain)

          # Stalemate breaks momentum
          state$scenario_state$consecutive_wins_defender <- 0
          state$scenario_state$consecutive_wins_aggressor <- 0
          state$scenario_state$momentum <- state$scenario_state$momentum * 0.5

        } else {
          # Stalemate breaks momentum (no territory change)
          state$scenario_state$consecutive_wins_defender <- 0
          state$scenario_state$consecutive_wins_aggressor <- 0
          state$scenario_state$momentum <- state$scenario_state$momentum * 0.5
        }
      }
    } else if (event$type == "economic" && grepl("sanctions", event$description, ignore.case = TRUE)) {
      # Check if impact_type exists before using it
      if (!is.null(event$impact_type) && length(event$impact_type) > 0) {
        if (event$impact_type == "sanctions_increase") {
          state$scenario_state$sanctions_level <-
            min(1.0, state$scenario_state$sanctions_level + 0.1)
        } else if (event$impact_type == "sanctions_decrease") {
          state$scenario_state$sanctions_level <-
            max(0.0, state$scenario_state$sanctions_level - 0.1)
        }
      }
    } else if (event$type == "military_aid") {
      state$scenario_state$international_support <-
        min(1.0, state$scenario_state$international_support + 0.1)
    }

    # Handle shock events with special territory/crisis impacts
    if (!is.null(event$is_shock) && event$is_shock) {
      if (event$type == "military_disaster_small") {
        # Catastrophic defeat: aggressor seizes 10-15% territory
        state$scenario_state$territory_controlled <-
          min(1.0, state$scenario_state$territory_controlled + runif(1, 0.10, 0.15))
        state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 2)
      } else if (event$type == "coup_attempt") {
        # Coup attempt creates extreme crisis
        state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 3)
      } else if (event$type == "leadership_challenge_small") {
        # Political crisis
        state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 2)
      } else if (event$type == "domestic_crisis_small") {
        # Domestic unrest
        state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1)
      } else if (event$type == "escalation_spiral") {
        # Escalation threat (nuclear weapons)
        state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 2)
        # 5% chance major power actually uses nuclear weapons
        if (runif(1) < 0.05) {
          state$scenario_state$nuclear_used <- TRUE
          state$scenario_state$crisis_level <- 10
        }
      } else if (event$type == "diplomatic_breakthrough") {
        # De-escalation reduces crisis
        state$scenario_state$crisis_level <- max(0, state$scenario_state$crisis_level - 2)
      } else if (event$type == "military_disaster_major") {
        # Major power failure reduces crisis for smaller power
        state$scenario_state$crisis_level <- max(0, state$scenario_state$crisis_level - 1)
      }
    }
  }

  # Keep balances in reasonable range
  state$scenario_state$military_balance <-
    max(-1, min(1, state$scenario_state$military_balance))

  # Update situation summary based on assessment
  state$scenario_state$situation_summary <- sprintf(
    "Day %d: Conflict continues. Territory controlled by aggressor: %.1f%%. Crisis level: %d/10. Estimated probability of government collapse: %.1f%%. %s",
    state$scenario_state$current_day,
    state$scenario_state$territory_controlled * 100,
    state$scenario_state$crisis_level,
    assessment$probability * 100,
    assessment$key_factors
  )

  # Update recent events (keep last 3)
  event_descriptions <- sapply(events, function(e) e$description)
  state$scenario_state$recent_events <- c(
    event_descriptions,
    tail(state$scenario_state$recent_events, 2)
  )
  state$scenario_state$recent_events <-
    head(state$scenario_state$recent_events, 3)

  return(state)
}

#' Save interaction data to JSON file
#'
#' @param interaction Interaction object
#' @param period Period number
#' @param data_dir Data directory path
save_interaction <- function(interaction, period, data_dir) {
  period_dir <- file.path(data_dir, "interactions", sprintf("period_%d", period))
  dir.create(period_dir, recursive = TRUE, showWarnings = FALSE)

  filename <- file.path(
    period_dir,
    sprintf("interaction_%s.json", interaction$interaction_id)
  )

  write_json(interaction, filename, pretty = TRUE, auto_unbox = TRUE)
}

#' Save all interactions from a session
#'
#' @param session Interaction session
#' @param data_dir Data directory path
save_interaction_session <- function(session, data_dir) {
  for (interaction in session$interactions) {
    save_interaction(interaction, session$period, data_dir)
  }

  # Save session summary
  period_dir <- file.path(data_dir, "interactions", sprintf("period_%d", session$period))
  summary_file <- file.path(period_dir, "session_summary.json")

  session_summary <- list(
    period = session$period,
    session_id = session$session_id,
    start_time = session$start_time,
    end_time = session$end_time,
    interaction_count = session$interaction_count,
    interaction_ids = sapply(session$interactions, function(i) i$interaction_id)
  )

  write_json(session_summary, summary_file, pretty = TRUE, auto_unbox = TRUE)
}

#' Save agent state timeline
#'
#' @param agent Agent object
#' @param agent_id Agent identifier
#' @param period Current period
#' @param data_dir Data directory path
save_agent_state <- function(agent, agent_id, period, data_dir) {
  agent_dir <- file.path(data_dir, "agent_states")
  dir.create(agent_dir, recursive = TRUE, showWarnings = FALSE)

  filename <- file.path(agent_dir, sprintf("%s_timeline.csv", agent_id))

  # Create data frame for this period
  state_data <- data.frame(
    period = period,
    timestamp = as.character(Sys.time()),
    hawk_dove_score = agent$hawk_dove,
    policy_adherence = agent$policy_adherence,
    objective_alignment = agent$objective_alignment,
    n_interactions = length(agent$state$recent_interactions),
    stringsAsFactors = FALSE
  )

  # Append to existing file or create new
  if (file.exists(filename)) {
    existing <- read.csv(filename)
    state_data <- rbind(existing, state_data)
  }

  write.csv(state_data, filename, row.names = FALSE)
}

#' Save all agent states
#'
#' @param agents List of agent objects
#' @param period Current period
#' @param data_dir Data directory path
save_all_agent_states <- function(agents, period, data_dir) {
  for (agent_id in names(agents)) {
    save_agent_state(agents[[agent_id]], agent_id, period, data_dir)
  }
}

#' Build interaction network for a period
#'
#' @param interactions List of interactions
#' @param period Period number
#' @return Data frame with network edges
build_interaction_network <- function(interactions, period) {
  if (length(interactions) == 0) {
    return(data.frame())
  }

  # Create edge list from interactions
  edges <- list()

  for (int in interactions) {
    if (length(int$participant_ids) < 2) next

    # Create edges between all pairs of participants
    for (i in 1:(length(int$participant_ids) - 1)) {
      for (j in (i + 1):length(int$participant_ids)) {
        edge <- list(
          period = period,
          agent_A = int$participant_ids[i],
          agent_B = int$participant_ids[j],
          interaction_type = int$type,
          interaction_id = int$interaction_id
        )
        edges <- c(edges, list(edge))
      }
    }
  }

  if (length(edges) == 0) {
    return(data.frame())
  }

  # Convert to data frame and aggregate
  edge_df <- do.call(rbind, lapply(edges, as.data.frame))

  # Count interactions between pairs
  network <- aggregate(
    interaction_id ~ period + agent_A + agent_B + interaction_type,
    data = edge_df,
    FUN = length
  )
  names(network)[5] <- "interaction_count"

  return(network)
}

#' Save network data
#'
#' @param interactions List of interactions
#' @param period Period number
#' @param data_dir Data directory path
save_network_data <- function(interactions, period, data_dir) {
  network_dir <- file.path(data_dir, "networks")
  dir.create(network_dir, recursive = TRUE, showWarnings = FALSE)

  network <- build_interaction_network(interactions, period)

  if (nrow(network) > 0) {
    filename <- file.path(network_dir, sprintf("period_%d_network.csv", period))
    write.csv(network, filename, row.names = FALSE)
  }
}

#' Save assessment to file
#'
#' @param assessment Assessment object
#' @param period Period number
#' @param output_dir Output directory path
save_assessment <- function(assessment, period, output_dir) {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  filename <- file.path(output_dir, "assessments.csv")

  assessment_data <- data.frame(
    period = period,
    timestamp = as.character(assessment$timestamp),
    probability = assessment$probability,
    confidence = assessment$confidence,
    trend = assessment$trend,
    key_factors = assessment$key_factors,
    stringsAsFactors = FALSE
  )

  if (file.exists(filename)) {
    existing <- read.csv(filename, stringsAsFactors = FALSE)
    assessment_data <- rbind(existing, assessment_data)
  }

  write.csv(assessment_data, filename, row.names = FALSE)

  # Also save full response
  full_file <- file.path(output_dir, sprintf("assessment_period_%d.txt", period))
  writeLines(assessment$full_response, full_file)
}

#' Save complete simulation state
#'
#' @param state Simulation state object
#' @param output_dir Output directory path
save_simulation_state <- function(state, output_dir) {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  filename <- file.path(output_dir, "simulation_state.rds")
  saveRDS(state, filename)

  cat(sprintf("Simulation state saved to %s\n", filename))
}

#' Load simulation state
#'
#' @param output_dir Output directory path
#' @return Simulation state object
load_simulation_state <- function(output_dir) {
  filename <- file.path(output_dir, "simulation_state.rds")

  if (!file.exists(filename)) {
    stop("Simulation state file not found")
  }

  state <- readRDS(filename)
  return(state)
}
