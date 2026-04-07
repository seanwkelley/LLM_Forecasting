# Generate forecast prompts for human participants

#' Generate forecast prompt for a period
#'
#' @param state Simulation state object
#' @param period Period number to generate prompt for
#' @param control_condition Logical, whether this is a control condition (default FALSE)
#' @return Character string with forecast prompt
generate_forecast_prompt <- function(state, period, control_condition = FALSE) {
  if (period < 1 || period > length(state$events_history)) {
    stop("Invalid period number")
  }

  # Get information available at the START of this period
  # (i.e., everything that happened up to period - 1)

  if (period == 1) {
    # Period 1: Only initial scenario information
    prompt <- sprintf(
"<forecasting_task>
FORECASTING TASK - PERIOD %d

<task_description>
You are participating in a geopolitical forecasting exercise. Based on the information below, please estimate the probability (0-100%%) that the smaller power's government will collapse or be removed from power by the end of Period %d (Day %d).
</task_description>

<initial_scenario>
INITIAL SCENARIO:
A major power has initiated territorial operations against a smaller power. The smaller power is mounting defensive resistance. International reactions are developing.

INITIAL CONDITIONS:
- Military Balance: Slight advantage to defender (home territory advantage)
- International Sanctions: Initial sanctions package in place against major power
- External Support: Moderate international support for smaller power
- Day: 0 (start of conflict)

AGENT COMPOSITION:
Major Power: 4 decision-makers (military, government, economic, intelligence)
Smaller Power: 4 decision-makers (president, military, diplomat, opposition)
External Actors: 3 representatives (allied power, neutral power, international org)
</initial_scenario>

<forecast_question>
QUESTION:
What is the probability (0-100%%) that the smaller power's government will be removed from power by Day %d?

Your forecast: ___%%

Confidence (Low/Medium/High): _______

Brief reasoning:
</forecast_question>
</forecasting_task>
",
      period,
      period,
      period * 7,
      period * 7
    )
  } else {
    # Periods 2+: Include summary of what happened in previous periods

    # Summarize previous events
    prev_events_summary <- ""
    for (p in 1:(period - 1)) {
      events <- state$events_history[[p]]
      if (length(events) > 0) {
        event_list <- sapply(events, function(e) {
          sprintf("  - %s: %s", e$name, e$description)
        })
        prev_events_summary <- paste0(
          prev_events_summary,
          sprintf("\nPeriod %d (Days %d-%d):\n%s\n",
                  p, (p-1)*7 + 1, p*7,
                  paste(event_list, collapse = "\n"))
        )
      }
    }

    # Get previous outcome (binary: government survived or collapsed)
    prev_assessment <- state$assessments_history[[period - 1]]
    prev_outcome <- if (!is.null(prev_assessment) && !is.na(prev_assessment$probability)) {
      if (prev_assessment$probability > 0.5) {
        "Government COLLAPSED or removed from power"
      } else {
        "Government REMAINED IN POWER"
      }
    } else {
      "Not available"
    }

    # Get public knowledge metrics from previous period
    prev_scenario <- if (!is.null(state$scenario_state_history[[period - 1]])) {
      state$scenario_state_history[[period - 1]]
    } else {
      state$scenario_state
    }

    prev_metrics <- sprintf(
      "- Territory controlled by aggressor: %.1f%%
- Crisis level: %d/10
- Sanctions level: %.1f%%
- International support for smaller power: %.1f%%",
      prev_scenario$territory_controlled * 100,
      prev_scenario$crisis_level,
      prev_scenario$sanctions_level * 100,
      prev_scenario$international_support * 100
    )

    # Summarize key interaction themes (without full transcripts)
    interaction_summary <- ""
    for (p in 1:(period - 1)) {
      session <- state$interactions_history[[p]]
      if (!is.null(session) && length(session$interactions) > 0) {
        interaction_topics <- sapply(session$interactions, function(int) {
          sprintf("  - %s (%s)", int$topic, int$type)
        })
        interaction_summary <- paste0(
          interaction_summary,
          sprintf("\nPeriod %d Key Discussions:\n%s\n",
                  p,
                  paste(interaction_topics, collapse = "\n"))
        )
      }
    }

    # Add control condition note if applicable
    condition_note <- if (control_condition) {
      "\n[NOTE: This is a CONTROL CONDITION with randomized information for experimental purposes.]\n"
    } else {
      ""
    }

    prompt <- sprintf(
"<forecasting_task>
%sFORECASTING TASK - PERIOD %d

<task_description>
You are participating in a geopolitical forecasting exercise. Based on the information below, please estimate the probability (0-100%%) that the smaller power's government will collapse or be removed from power by the end of Period %d (Day %d).
</task_description>

<scenario_update>
SCENARIO UPDATE:
Day %d of simulated conflict between major power and smaller power.

PREVIOUS PERIOD OUTCOME:
End of Period %d: %s

PUBLICLY OBSERVABLE METRICS (End of Period %d):
%s
</scenario_update>

<historical_context>
EVENTS THAT HAVE OCCURRED:
%s

KEY INTERACTIONS AND DISCUSSIONS:
%s
</historical_context>

<current_situation>
CURRENT SITUATION (Start of Period %d):
%s
</current_situation>

<forecast_question>
QUESTION:
Based on all information above, what is the probability (0-100%%) that the smaller power's government will be removed from power by the end of Period %d (Day %d)?

Your forecast: ___%%

Confidence (Low/Medium/High): _______

Brief reasoning (2-3 sentences):
</forecast_question>
</forecasting_task>
",
      condition_note,
      period,
      period,
      period * 7,
      (period - 1) * 7,
      period - 1,
      prev_outcome,
      period - 1,
      prev_metrics,
      prev_events_summary,
      interaction_summary,
      period,
      state$scenario_state$situation_summary,
      period,
      period * 7
    )
  }

  return(prompt)
}

#' Generate all forecast prompts for a completed simulation
#'
#' @param state Simulation state object
#' @param output_file File path to save prompts
#' @param control_condition Logical, whether to generate control condition (default FALSE)
#' @return List of prompts for each period
generate_all_forecast_prompts <- function(state, output_file = NULL, control_condition = FALSE) {
  n_periods <- state$current_period

  # Generate control condition if requested
  if (control_condition) {
    source("src/control_condition.R")
    state <- generate_control_condition(state)
  }

  prompts <- list()
  for (p in 1:n_periods) {
    prompts[[p]] <- generate_forecast_prompt(state, p, control_condition)
  }

  if (!is.null(output_file)) {
    # Write all prompts to file
    con <- file(output_file, "w")

    condition_label <- if (control_condition) "CONTROL CONDITION" else "TRUE CONDITION"

    writeLines(sprintf("HUMAN FORECASTING PROMPTS - %s", condition_label), con)
    writeLines(paste(rep("=", 80), collapse = ""), con)
    writeLines("", con)
    if (control_condition) {
      writeLines("CONTROL CONDITION: Information has been randomized to break predictability.", con)
      writeLines("This tests whether forecasters can overfit to random patterns.", con)
    } else {
      writeLines("TRUE CONDITION: These prompts reflect actual simulation dynamics.", con)
      writeLines("Compare human predictions with the LLM aggregator's assessments.", con)
    }
    writeLines("", con)
    writeLines(paste(rep("=", 80), collapse = ""), con)
    writeLines("", con)

    for (p in 1:n_periods) {
      writeLines(prompts[[p]], con)
      writeLines("", con)
      writeLines(paste(rep("-", 80), collapse = ""), con)
      writeLines("", con)
    }

    close(con)
    cat(sprintf("Forecast prompts saved to %s\n", output_file))
  }

  return(prompts)
}

#' Generate comparison table of LLM vs human forecasts
#'
#' @param state Simulation state object
#' @param human_forecasts Numeric vector of human probability forecasts (0-1 scale)
#' @param human_names Optional vector of forecaster names
#' @return Data frame with comparison
compare_forecasts <- function(state, human_forecasts, human_names = NULL) {
  n_periods <- length(human_forecasts)

  if (n_periods > state$current_period) {
    warning("More human forecasts than simulation periods. Truncating.")
    n_periods <- state$current_period
    human_forecasts <- human_forecasts[1:n_periods]
  }

  llm_forecasts <- sapply(1:n_periods, function(p) {
    state$assessments_history[[p]]$probability
  })

  comparison <- data.frame(
    period = 1:n_periods,
    day = (1:n_periods) * 7,
    llm_forecast = llm_forecasts,
    human_forecast = human_forecasts,
    difference = human_forecasts - llm_forecasts,
    abs_difference = abs(human_forecasts - llm_forecasts)
  )

  if (!is.null(human_names)) {
    comparison$forecaster <- human_names[1:n_periods]
  }

  return(comparison)
}

#' Generate period summary for forecasting (condensed version)
#'
#' @param state Simulation state object
#' @param period Period number
#' @return Character string with condensed summary
generate_period_summary <- function(state, period) {
  if (period < 1 || period > state$current_period) {
    stop("Invalid period number")
  }

  # Events summary
  events <- state$events_history[[period]]
  event_text <- if (length(events) > 0) {
    paste(sapply(events, function(e) e$description), collapse = "; ")
  } else {
    "No major events"
  }

  # Interaction count
  session <- state$interactions_history[[period]]
  n_interactions <- if (!is.null(session)) session$interaction_count else 0

  # Assessment
  assessment <- state$assessments_history[[period]]
  prob_text <- if (!is.na(assessment$probability)) {
    sprintf("%.1f%%", assessment$probability * 100)
  } else {
    "N/A"
  }

  summary <- sprintf(
    "Period %d (Day %d): Events: %s | Interactions: %d | LLM Forecast: %s | Confidence: %s",
    period,
    period * 7,
    substr(event_text, 1, 100),
    n_interactions,
    prob_text,
    assessment$confidence
  )

  return(summary)
}

#' Create forecasting worksheet with answer key
#'
#' @param state Simulation state object
#' @param output_dir Directory to save files
#' @param generate_control Logical, whether to also generate control condition (default TRUE)
#' @return Paths to generated files
create_forecasting_worksheet <- function(state, output_dir = "outputs", generate_control = TRUE) {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  files <- list()

  # Generate TRUE condition prompts (without answers)
  prompts_file <- file.path(output_dir, "forecasting_prompts_true.txt")
  generate_all_forecast_prompts(state, prompts_file, control_condition = FALSE)
  files$prompts_true <- prompts_file

  # Generate CONTROL condition prompts if requested
  if (generate_control) {
    control_prompts_file <- file.path(output_dir, "forecasting_prompts_control.txt")
    generate_all_forecast_prompts(state, control_prompts_file, control_condition = TRUE)
    files$prompts_control <- control_prompts_file
  }

  # Generate answer key (with LLM forecasts)
  answer_file <- file.path(output_dir, "forecasting_answer_key.txt")
  con <- file(answer_file, "w")

  writeLines("FORECASTING ANSWER KEY - LLM Aggregator Forecasts", con)
  writeLines(paste(rep("=", 80), collapse = ""), con)
  writeLines("", con)

  for (p in 1:state$current_period) {
    assessment <- state$assessments_history[[p]]

    writeLines(sprintf("PERIOD %d (Day %d)", p, p * 7), con)
    writeLines(sprintf("LLM Forecast: %.1f%%", assessment$probability * 100), con)
    writeLines(sprintf("Confidence: %s", assessment$confidence), con)
    writeLines(sprintf("Trend: %s", assessment$trend), con)
    writeLines(sprintf("Key Factors: %s", assessment$key_factors), con)
    writeLines("", con)
    writeLines(paste(rep("-", 80), collapse = ""), con)
    writeLines("", con)
  }

  close(con)
  cat(sprintf("Answer key saved to %s\n", answer_file))

  # Generate CSV for easy data entry
  csv_file <- file.path(output_dir, "forecasting_template.csv")
  template <- data.frame(
    period = 1:state$current_period,
    day = (1:state$current_period) * 7,
    condition = "",  # "true" or "control"
    forecaster_name = "",
    probability_forecast = NA,
    confidence = "",
    llm_forecast = sapply(1:state$current_period, function(p) {
      state$assessments_history[[p]]$probability * 100
    }),
    stringsAsFactors = FALSE
  )

  write.csv(template, csv_file, row.names = FALSE)
  cat(sprintf("CSV template saved to %s\n", csv_file))

  files$answers <- answer_file
  files$template <- csv_file

  return(files)
}
