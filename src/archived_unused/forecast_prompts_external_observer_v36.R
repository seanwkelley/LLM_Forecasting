# Generate forecast prompts for human participants (v3.6 - External Observer Perspective)
# Humans should only see what would be visible in the news/public sources
# NOT internal deliberations, agent positions, or classified information

#' Filter actions to externally observable ones
#'
#' Some actions are visible (military strikes, sanctions), others are covert (sabotage, assassination)
#'
#' @param action_name Name of the action
#' @param success Logical, whether action succeeded
#' @param detected Logical, whether covert action was detected
#' @return Logical, whether action is publicly observable
is_action_publicly_observable <- function(action_name, success = TRUE, detected = FALSE) {

  # Always observable (public actions)
  public_actions <- c(
    "diplomatic_visit", "peace_talks", "trade_negotiation", "cultural_exchange",
    "humanitarian_aid", "mediation_offer", "economic_sanctions", "financial_aid",
    "resource_embargo", "military_buildup", "naval_deployment", "air_patrols",
    "troop_movements", "joint_exercises", "arms_development", "border_incursion",
    "limited_strike", "full_scale_attack", "occupation", "blockade", "siege_warfare",
    "nuclear_development", "chemical_weapons", "biological_program",
    "tactical_nuclear_use", "strategic_nuclear_strike", "trade_agreement",
    "propaganda_campaign"
  )

  # Covert actions - only visible if detected or failed spectacularly
  covert_actions <- c(
    "intelligence_gathering", "surveillance_operation", "counterintelligence",
    "spread_disinformation", "sabotage", "assassination_attempt",
    "regime_destabilization", "proxy_support", "false_flag_operation",
    "cyber_attack", "cyber_theft", "currency_manipulation"
  )

  if (action_name %in% public_actions) {
    return(TRUE)
  } else if (action_name %in% covert_actions) {
    # Covert actions only visible if detected or failed
    return(detected || (!success && runif(1) > 0.3))  # Failed ops sometimes leak
  }

  # Unknown actions - assume not observable
  return(FALSE)
}

#' Convert action to external observer description
#'
#' Translates internal action execution into what external observer would see
#'
#' @param action_record Action record from simulation state
#' @return Character string describing observable action
describe_action_externally <- function(action_record) {

  if (is.null(action_record$detected)) {
    detected <- FALSE
  } else {
    detected <- action_record$detected
  }

  if (!is_action_publicly_observable(action_record$action, action_record$success, detected)) {
    return(NULL)  # Not observable
  }

  faction_label <- switch(action_record$faction,
    major_power = "Novaris",
    small_power = "Tethys",
    meridian = "Meridian Alliance",
    valkoria = "Valkoria",
    aurelia = "Aurelia",
    international_org = "International Organizations",
    action_record$faction
  )

  # Map action to external description
  external_desc <- switch(action_record$action,
    # Diplomatic
    peace_talks = sprintf("%s initiated peace negotiations", faction_label),
    mediation_offer = sprintf("%s offered to mediate the conflict", faction_label),
    diplomatic_visit = sprintf("%s conducted high-level diplomatic visit", faction_label),
    humanitarian_aid = sprintf("%s provided humanitarian assistance", faction_label),

    # Economic
    economic_sanctions = sprintf("%s imposed economic sanctions", faction_label),
    financial_aid = sprintf("%s provided financial aid package", faction_label),
    resource_embargo = sprintf("%s announced resource embargo", faction_label),

    # Military posture
    military_buildup = sprintf("%s increased military readiness and force levels", faction_label),
    troop_movements = sprintf("%s repositioned military forces", faction_label),
    naval_deployment = sprintf("%s deployed naval forces to the region", faction_label),
    joint_exercises = sprintf("%s conducted military exercises", faction_label),

    # Open conflict
    limited_strike = sprintf("%s conducted precision military strikes", faction_label),
    full_scale_attack = sprintf("%s launched major military offensive", faction_label),
    border_incursion = sprintf("%s forces crossed the border", faction_label),
    blockade = sprintf("%s imposed naval/economic blockade", faction_label),
    siege_warfare = sprintf("%s besieged urban areas", faction_label),

    # Covert (only if detected)
    cyber_attack = if (detected) sprintf("%s implicated in cyber attack", faction_label) else NULL,
    sabotage = if (detected) sprintf("%s accused of sabotage operations", faction_label) else NULL,
    assassination_attempt = if (detected) sprintf("Assassination attempt attributed to %s", faction_label) else NULL,

    # WMD
    nuclear_development = sprintf("%s announced nuclear weapons program", faction_label),
    tactical_nuclear_use = sprintf("%s USED TACTICAL NUCLEAR WEAPON", faction_label),

    # Default
    sprintf("%s took action", faction_label)
  )

  # Add outcome if relevant
  if (!is.null(external_desc)) {
    if (action_record$action %in% c("peace_talks", "mediation_offer")) {
      outcome_desc <- if (action_record$success) " - talks ongoing" else " - negotiations stalled"
      external_desc <- paste0(external_desc, outcome_desc)
    } else if (action_record$action %in% c("limited_strike", "full_scale_attack", "border_incursion")) {
      # Don't reveal exact military outcomes, but major changes are observable
      if (!is.null(action_record$territory_change) && abs(action_record$territory_change) > 0.03) {
        outcome_desc <- if (action_record$success) " - territorial gains reported" else " - offensive repelled"
        external_desc <- paste0(external_desc, outcome_desc)
      }
    }
  }

  return(external_desc)
}

#' Generate external analyst commentary
#'
#' Simulates what independent analysts might say based on observable events
#'
#' @param scenario_state Current scenario state
#' @param recent_actions Recent observable actions
#' @return Character string with analyst commentary
generate_analyst_commentary <- function(scenario_state, recent_actions) {

  commentary <- c()

  # Territory analysis
  if (!is.null(scenario_state$territory_controlled)) {
    if (scenario_state$territory_controlled > 0.20) {
      commentary <- c(commentary, "Independent analysts assess that the aggressor has achieved significant territorial control, raising questions about the defender's military sustainability.")
    } else if (scenario_state$territory_controlled > 0.10) {
      commentary <- c(commentary, "Military analysts note that while the aggressor has made gains, the defender's resistance remains stronger than initially predicted.")
    } else if (scenario_state$territory_controlled < 0.05) {
      commentary <- c(commentary, "Defense experts observe that territorial changes remain limited, suggesting either strategic restraint or effective defensive operations.")
    }
  }

  # Crisis level analysis
  if (!is.null(scenario_state$crisis_level)) {
    if (scenario_state$crisis_level >= 9) {
      commentary <- c(commentary, "International observers warn that the crisis has reached critical levels, with risk of catastrophic escalation.")
    } else if (scenario_state$crisis_level <= 4) {
      commentary <- c(commentary, "Regional experts suggest that diplomatic channels may be creating opportunities for de-escalation.")
    }
  }

  # Sanctions analysis
  if (!is.null(scenario_state$sanctions_level) && scenario_state$sanctions_level > 0.5) {
    commentary <- c(commentary, "Economic analysts note that comprehensive sanctions are placing significant pressure on the aggressor's economy, though effects may take time to materialize.")
  }

  # Action-based analysis
  if (length(recent_actions) > 0) {
    peace_talks_count <- sum(grepl("peace negotiations|mediation", recent_actions))
    if (peace_talks_count >= 2) {
      commentary <- c(commentary, "Diplomatic observers note repeated negotiation attempts, though skepticism remains about willingness to make necessary concessions.")
    }

    military_actions <- sum(grepl("strikes|offensive|attack|besieged", recent_actions))
    if (military_actions >= 2) {
      commentary <- c(commentary, "Security analysts point to sustained military operations as evidence that neither side sees a military resolution as impossible.")
    }
  }

  if (length(commentary) == 0) {
    commentary <- c("Analysts continue to monitor the situation closely.")
  }

  # Return 1-2 pieces of commentary
  return(paste(sample(commentary, min(2, length(commentary))), collapse = "\n\n"))
}

#' Generate forecast prompt with external observer perspective
#'
#' @param state Simulation state object
#' @param period Period number to generate prompt for
#' @param control_condition Logical, whether this is a control condition (default FALSE)
#' @return Character string with forecast prompt
generate_forecast_prompt_external <- function(state, period, control_condition = FALSE) {
  if (period < 1 || period > length(state$events_history)) {
    stop("Invalid period number")
  }

  if (period == 1) {
    # Period 1: Only initial scenario information
    prompt <- sprintf(
"FORECASTING TASK - PERIOD %d

You are participating in a geopolitical forecasting exercise. You are an EXTERNAL OBSERVER with access only to publicly available information (similar to what you would see in news media and open-source analysis).

Based on the information below, please estimate the probability (0-100%%) that Tethys's government will collapse or be removed from power by the end of Period %d (Day %d).

INITIAL SCENARIO:
The major power Novaris has initiated military operations against the smaller power Tethys. Tethys is mounting defensive resistance. International reactions are developing.

INITIAL CONDITIONS (Day 0):
- Military situation: Novaris forces positioned on border, initial operations beginning
- International response: Initial sanctions package announced against Novaris
- External support: Moderate international support pledged to Tethys
- Estimated force balance: Slight defender advantage (home territory, motivated defenders)

NOTE: You do NOT have access to:
- Internal government deliberations or decision-making processes
- Classified intelligence assessments
- Private diplomatic communications
- Undisclosed military plans

You can only see what would be reported in news media and independent analysis.

QUESTION:
Based on publicly available information, what is the probability (0-100%%) that Tethys's government will be removed from power by Day %d?

Your forecast: ___%%

Confidence (Low/Medium/High): _______

Brief reasoning (2-3 sentences):
",
      period,
      period,
      period * 7,
      period * 7
    )
  } else {
    # Periods 2+: Include only externally observable events and actions

    # Filter to observable actions only
    observable_actions <- c()
    for (p in 1:(period - 1)) {
      if (!is.null(state$faction_actions)) {
        period_actions <- Filter(function(a) a$period == p, state$faction_actions)
        for (action_record in period_actions) {
          external_desc <- describe_action_externally(action_record)
          if (!is.null(external_desc)) {
            observable_actions <- c(observable_actions,
              sprintf("Day %d: %s", (p-1)*7 + sample(1:7, 1), external_desc))
          }
        }
      }
    }

    # External events (these are observable)
    external_events <- ""
    for (p in 1:(period - 1)) {
      events <- state$events_history[[p]]
      if (length(events) > 0) {
        event_list <- sapply(events, function(e) {
          sprintf("  Day %d: %s - %s", (p-1)*7 + sample(1:7, 1), e$name, e$description)
        })
        external_events <- paste0(
          external_events,
          paste(event_list, collapse = "\n"), "\n"
        )
      }
    }

    # Get observable metrics (these would be estimated by external analysts)
    prev_scenario <- if (!is.null(state$scenario_state_history[[period - 1]])) {
      state$scenario_state_history[[period - 1]]
    } else {
      state$scenario_state
    }

    observable_metrics <- sprintf(
      "- Estimated territory under Novaris control: ~%.0f%% (based on front-line reports)
- Conflict intensity assessment: %s (based on reported military activity)
- International sanctions: %s
- External aid to Tethys: %s",
      prev_scenario$territory_controlled * 100,
      if (prev_scenario$crisis_level >= 8) "Very High" else if (prev_scenario$crisis_level >= 6) "High" else if (prev_scenario$crisis_level >= 4) "Moderate" else "Low",
      if (prev_scenario$sanctions_level > 0.6) "Comprehensive" else if (prev_scenario$sanctions_level > 0.3) "Significant" else "Limited",
      if (!is.null(prev_scenario$international_support) && prev_scenario$international_support > 0.6) "Substantial" else "Moderate"
    )

    # Generate analyst commentary
    analyst_commentary <- generate_analyst_commentary(prev_scenario, observable_actions)

    # Previous LLM forecast (as if it were another analyst)
    prev_assessment <- state$assessments_history[[period - 1]]
    llm_forecast_note <- if (!is.null(prev_assessment) && !is.na(prev_assessment$probability)) {
      sprintf("\nOTHER FORECASTER ASSESSMENT (Period %d):
One forecasting model estimated %.0f%% probability of government collapse by end of Period %d.
(You may use this as additional data point, but are not required to agree with it.)",
        period - 1,
        prev_assessment$probability * 100,
        period - 1)
    } else {
      ""
    }

    # Add control condition note if applicable
    condition_note <- if (control_condition) {
      "\n[NOTE: This is a CONTROL CONDITION with randomized information for experimental purposes.]\n"
    } else {
      ""
    }

    prompt <- sprintf(
"%sFORECASTING TASK - PERIOD %d

You are an EXTERNAL OBSERVER with access only to publicly available information.

SCENARIO UPDATE:
Day %d of conflict between Novaris (aggressor) and Tethys (defender).

OBSERVABLE METRICS (as of end of Period %d):
%s

REPORTED EVENTS AND ACTIONS:
%s

%s

INDEPENDENT ANALYST COMMENTARY:
%s%s

REMINDER - Information Limits:
You do NOT have access to:
- Internal deliberations within either government
- Classified intelligence or military plans
- Private diplomatic communications
- Undisclosed covert operations

QUESTION:
Based ONLY on publicly observable information and independent analysis, what is the probability (0-100%%) that Tethys's government will be removed from power by the end of Period %d (Day %d)?

Your forecast: ___%%

Confidence (Low/Medium/High): _______

Brief reasoning (2-3 sentences):
What publicly observable factors most influence your forecast?
",
      condition_note,
      period,
      (period - 1) * 7,
      period - 1,
      observable_metrics,
      if (length(observable_actions) > 0) paste(observable_actions, collapse = "\n") else "No major actions publicly reported",
      if (nchar(external_events) > 10) paste0("\n", external_events) else "",
      analyst_commentary,
      llm_forecast_note,
      period,
      period * 7
    )
  }

  return(prompt)
}

#' Generate all forecast prompts for a completed simulation (external observer version)
#'
#' @param state Simulation state object
#' @param output_file File path to save prompts
#' @param control_condition Logical, whether to generate control condition (default FALSE)
#' @return List of prompts for each period
generate_all_forecast_prompts_external <- function(state, output_file = NULL, control_condition = FALSE) {
  n_periods <- state$current_period

  # Generate control condition if requested
  if (control_condition) {
    source("src/control_condition.R")
    state <- generate_control_condition(state)
  }

  prompts <- list()
  for (p in 1:n_periods) {
    prompts[[p]] <- generate_forecast_prompt_external(state, p, control_condition)
  }

  if (!is.null(output_file)) {
    # Write all prompts to file
    con <- file(output_file, "w")

    condition_label <- if (control_condition) "CONTROL CONDITION" else "TRUE CONDITION"

    writeLines(sprintf("HUMAN FORECASTING PROMPTS - %s (EXTERNAL OBSERVER PERSPECTIVE)", condition_label), con)
    writeLines(paste(rep("=", 80), collapse = ""), con)
    writeLines("", con)
    if (control_condition) {
      writeLines("CONTROL CONDITION: Information has been randomized to break predictability.", con)
      writeLines("This tests whether forecasters can overfit to random patterns.", con)
    } else {
      writeLines("TRUE CONDITION: Prompts reflect publicly observable simulation dynamics.", con)
      writeLines("Forecasters see only what external observers would see (news, analysis).", con)
      writeLines("Internal deliberations and classified information are NOT included.", con)
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
    cat(sprintf("Forecast prompts (external observer) saved to %s\n", output_file))
  }

  return(prompts)
}

cat("Forecast prompts (External Observer v3.6) loaded\n")
cat("  - is_action_publicly_observable()\n")
cat("  - describe_action_externally()\n")
cat("  - generate_analyst_commentary()\n")
cat("  - generate_forecast_prompt_external()\n")
cat("  - generate_all_forecast_prompts_external()\n")
