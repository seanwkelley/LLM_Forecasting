# Generate PUBLIC-ONLY forecast prompts for human participants
# Framed as news-style intelligence briefings (Economist/FT style)
# NO internal deliberations, coordination, or private information

# Helper: Null-coalescing operator
`%||%` <- function(a, b) if (is.null(a)) b else a

#' Generate public-only forecast prompt (news-style briefing)
#'
#' @param state Simulation state object
#' @param period Period number to generate prompt for
#' @param control_condition Logical, whether this is a control condition (default FALSE)
#' @return Character string with forecast prompt in news briefing format
generate_public_forecast_prompt <- function(state, period, control_condition = FALSE) {
  if (period < 1 || period > length(state$events_history)) {
    stop("Invalid period number")
  }

  # Helper function: Convert actions to news-style reporting
  action_to_news <- function(action_name, faction, success) {
    news_items <- list(
      # Military actions
      military_buildup = "deployed additional military forces to the region",
      show_of_force = "conducted large-scale military demonstrations",
      enhanced_patrols = "intensified border patrol operations",
      military_exercises = "carried out military exercises near the border",
      naval_deployment = "deployed naval assets to contested waters",
      air_patrols = "increased air patrol frequency",
      asymmetric_defense = "implemented unconventional defense tactics",
      limited_strike = "executed limited military strikes",

      # Intelligence actions (only visible if leaked/reported)
      intelligence_gathering = "intensified intelligence collection activities",
      counterintelligence = "enhanced counterintelligence operations",
      surveillance_operation = "expanded surveillance programs",
      share_intelligence = "shared intelligence with allied nations",

      # Covert actions (only if failed and exposed)
      cyber_attack = "launched cyber operations (reported by independent sources)",
      cyber_theft = "attempted cyber espionage (detected and attributed)",
      sabotage = "conducted sabotage operations (later attributed)",
      leadership_targeting = "targeted opposition leadership (alleged)",
      spread_disinformation = "amplified disinformation campaigns (detected by fact-checkers)",

      # Diplomatic actions
      coalition_building = "engaged in coalition-building efforts",
      backchannel_negotiations = if (success) "pursued quiet diplomatic channels" else NULL, # Only if successful (otherwise unknown)
      peace_talks = "participated in formal peace negotiations",
      formal_peace_talks = "engaged in formal multilateral peace talks",
      mediation_offer = "offered to mediate the dispute",
      humanitarian_corridors = "established humanitarian corridors",
      cultural_exchange = "initiated cultural exchange programs",
      humanitarian_aid = "provided humanitarian assistance",

      # Economic actions
      economic_sanctions = "imposed economic sanctions",
      sanctions_coordination = "coordinated sanctions with international partners",
      sanctions_mitigation = "implemented sanctions evasion measures",
      resource_embargo = "announced resource embargoes",
      trade_restrictions = "imposed trade restrictions",
      trade_negotiation = "negotiated trade agreements",
      strategic_stockpiling = "increased strategic resource reserves",
      currency_manipulation = "intervened in currency markets",
      war_bonds = "issued war bonds to finance operations",
      economic_aid = "provided economic assistance",
      financial_aid = "delivered financial support packages"
    )

    news_text <- news_items[[action_name]]

    # Some covert actions are only visible if failed (exposed)
    covert_only_if_failed <- c("cyber_attack", "cyber_theft", "sabotage",
                                "leadership_targeting", "spread_disinformation")
    if (action_name %in% covert_only_if_failed && success) {
      return(NULL)  # Successful covert ops remain hidden
    }

    # Backchannel negotiations only visible if successful
    if (action_name == "backchannel_negotiations" && !success) {
      return(NULL)
    }

    return(news_text)
  }

  # Helper function: Get faction display name
  get_faction_name <- function(faction_id) {
    faction_names <- list(
      major_power = "Major Power",
      small_power = "Smaller Power",
      meridian = "Meridian (Allied Power)",
      valkoria = "Valkoria (Neutral Power)",
      aurelia = "Aurelia (Regional Power)",
      international_org = "International Organization"
    )
    return(faction_names[[faction_id]] %||% faction_id)
  }

  # ============================================================================
  # PERIOD 1: Initial briefing
  # ============================================================================
  if (period == 1) {
    prompt <- sprintf(
'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GEOPOLITICAL INTELLIGENCE BRIEFING — PERIOD %d
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<your_role>
You are a geopolitical analyst participating in a forecasting exercise. Your task
is to estimate the probability that the smaller power\'s government will collapse
or be removed from power by Day %d, based on publicly available information.

You will work with an AI assistant to analyze the situation and make your forecast.
</your_role>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INITIAL SITUATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**THE CRISIS**

A major regional power has initiated territorial operations against a smaller
neighboring state, citing historical territorial claims and security concerns.
The smaller power has mobilized defensive forces and called for international
support. The crisis has entered its opening phase, with diplomatic and military
positioning underway.

**INITIAL INDICATORS** (Day 0)

Military Situation
  • Military Balance: 0.50 (0 = total dominance by aggressor, 1 = defender advantage)
  • Territory Under Aggressor Control: 0%%
  • Assessment: Defender holds home-ground advantage; aggressor has numerical superiority

Economic Pressure
  • International Sanctions Level: 45%% (initial sanctions package)
  • Economic impact on major power: Moderate

Diplomatic Context
  • International Support for Smaller Power: 75%%
  • Regional powers are issuing statements; multilateral forums convening

**KEY ACTORS**

Primary Belligerents
  • Major Power: Regional hegemon with substantial military capabilities
  • Smaller Power: Defending state with limited but motivated forces

External Powers
  • Meridian: Traditional ally of smaller power; democratic bloc leader
  • Valkoria: Neutral power with economic ties to both sides
  • Aurelia: Regional power attempting to maintain balanced relationships
  • International Organization: Multilateral body coordinating humanitarian response

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR FORECAST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<forecast_question>
Based on the information above, what is the probability (0-100%%) that the
smaller power\'s government will collapse or be removed from power by Day %d?

Consider factors such as:
  • Military balance and territorial control
  • Economic resilience under sanctions and conflict
  • International support and diplomatic isolation
  • Internal political stability
  • Historical precedents in similar conflicts

Your probability estimate: ______%%

Your confidence level (Low/Medium/High): __________

Brief rationale (2-3 sentences):
___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________
</forecast_question>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
',
      period,
      period * 7,
      period * 7
    )

  # ============================================================================
  # PERIOD 2+: Ongoing briefings with news updates
  # ============================================================================
  } else {

    # --- Previous period outcome ---
    prev_assessment <- state$assessments_history[[period - 1]]
    prev_outcome <- if (!is.null(prev_assessment) && !is.na(prev_assessment$probability)) {
      if (prev_assessment$probability > 0.5) {
        "GOVERNMENT COLLAPSED"
      } else {
        "GOVERNMENT REMAINED IN POWER"
      }
    } else {
      "Status unclear"
    }

    # --- Current public metrics ---
    prev_scenario <- if (!is.null(state$state_history[[period - 1]]$scenario_state)) {
      state$state_history[[period - 1]]$scenario_state
    } else {
      state$scenario_state
    }

    current_metrics <- sprintf(
"Military Situation
  • Military Balance: %.2f %s
  • Territory Under Aggressor Control: %.0f%%%%
  • Crisis Level: %.0f/10 %s

Economic Pressure
  • International Sanctions Level: %.0f%%%%

Diplomatic Context
  • International Support for Smaller Power: %.0f%%%%",
      prev_scenario$military_balance,
      ifelse(prev_scenario$military_balance > 0.6, "(defender advantage)",
             ifelse(prev_scenario$military_balance < 0.4, "(aggressor advantage)", "(contested)")),
      prev_scenario$territory_controlled * 100,
      as.numeric(prev_scenario$crisis_level),
      ifelse(prev_scenario$crisis_level >= 8, "(critical)",
             ifelse(prev_scenario$crisis_level >= 5, "(elevated)", "(stable)")),
      prev_scenario$sanctions_level * 100,
      prev_scenario$international_support * 100
    )

    # --- Summarize external events ---
    events_summary <- ""
    for (p in 1:(period - 1)) {
      events <- state$events_history[[p]]
      if (length(events) > 0) {
        event_bullets <- sapply(events, function(e) {
          sprintf("  • %s: %s", e$name, e$description)
        })
        events_summary <- paste0(
          events_summary,
          sprintf("\n**Period %d (Days %d-%d)**\n%s\n",
                  p, (p-1)*7 + 1, p*7,
                  paste(event_bullets, collapse = "\n"))
        )
      }
    }

    if (events_summary == "") {
      events_summary <- "  • No major external events reported\n"
    }

    # --- Summarize publicly observable actions ---
    actions_summary <- ""
    for (p in 1:(period - 1)) {
      # Get actions from state
      if (!is.null(state$action_results) && length(state$action_results) >= p) {
        period_actions <- state$action_results[[p]]

        if (length(period_actions) > 0) {
          # Group actions by faction
          actions_by_faction <- list()

          for (action_bundle in period_actions) {
            # Check if this is a multi-action bundle (faction) or single action (external actor)
            if (!is.null(action_bundle$multi_action) && action_bundle$multi_action) {
              # Multi-action bundle from faction
              for (individual_action in action_bundle$individual_results) {
                action_name <- individual_action$action
                success <- individual_action$success
                proposed_by <- individual_action$proposed_by %||% "Unknown"

                # Infer faction from proposer name
                faction <- if (grepl("Viktor|Sergei|Natasha|Petrova", proposed_by)) {
                  "major_power"
                } else if (grepl("Olena|Maksym|Sofia|Taras|Bondar|Savchenko|Kovalenko|Moroz", proposed_by)) {
                  "small_power"
                } else {
                  "unknown"
                }

                # Convert to news-style reporting
                news_text <- action_to_news(action_name, faction, success)

                # Only include if it would be publicly visible
                if (!is.null(news_text)) {
                  if (is.null(actions_by_faction[[faction]])) {
                    actions_by_faction[[faction]] <- character(0)
                  }
                  actions_by_faction[[faction]] <- c(actions_by_faction[[faction]], news_text)
                }
              }
            } else {
              # Single action from external actor
              action_name <- action_bundle$action
              success <- action_bundle$success
              actor <- action_bundle$actor %||% "Unknown"

              # Infer faction from actor name
              faction <- if (grepl("Crawford|Meridian", actor)) {
                "meridian"
              } else if (grepl("Kozlov|Valkoria", actor)) {
                "valkoria"
              } else if (grepl("Schmidt|Aurelia", actor)) {
                "aurelia"
              } else if (grepl("Cardenas|Isabella|International", actor)) {
                "international_org"
              } else {
                "unknown"
              }

              # Convert to news-style reporting
              news_text <- action_to_news(action_name, faction, success)

              # Only include if it would be publicly visible
              if (!is.null(news_text)) {
                if (is.null(actions_by_faction[[faction]])) {
                  actions_by_faction[[faction]] <- character(0)
                }
                actions_by_faction[[faction]] <- c(actions_by_faction[[faction]], news_text)
              }
            }
          }

          # Format as news items
          if (length(actions_by_faction) > 0) {
            faction_reports <- sapply(names(actions_by_faction), function(faction) {
              faction_name <- get_faction_name(faction)
              actions_list <- unique(actions_by_faction[[faction]])  # Remove duplicates
              action_text <- paste(sprintf("    — %s", actions_list), collapse = "\n")
              sprintf("  **%s**\n%s", faction_name, action_text)
            })

            actions_summary <- paste0(
              actions_summary,
              sprintf("\n**Period %d (Days %d-%d)**\n%s\n",
                      p, (p-1)*7 + 1, p*7,
                      paste(faction_reports, collapse = "\n\n"))
            )
          }
        }
      }
    }

    if (actions_summary == "") {
      actions_summary <- "  • Limited observable activity reported\n"
    }

    # --- Control condition note ---
    condition_note <- if (control_condition) {
      "\n[CONTROL CONDITION: Information has been randomized for experimental purposes]\n"
    } else {
      ""
    }

    # --- Build full prompt ---
    prompt <- sprintf(
'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GEOPOLITICAL INTELLIGENCE BRIEFING — PERIOD %d
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%s
<update>
Day %d of ongoing crisis between major power and smaller neighboring state.

**PREVIOUS ASSESSMENT (End of Period %d):** %s
</update>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT INDICATORS (Day %d)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

%s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEVELOPMENTS SINCE LAST BRIEFING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<external_events>
**MAJOR EVENTS**
%s
</external_events>

<observable_actions>
**REPORTED ACTIONS**

The following actions have been reported by news agencies, government
statements, and independent observers:
%s
</observable_actions>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR FORECAST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<forecast_question>
Based on all information above, what is the probability (0-100%%) that the
smaller power\'s government will collapse or be removed from power by the end
of Period %d (Day %d)?

Your probability estimate: ______%%

Your confidence level (Low/Medium/High): __________

Brief rationale (2-3 sentences):
___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________
</forecast_question>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
',
      period,
      condition_note,
      (period - 1) * 7,
      period - 1,
      prev_outcome,
      (period - 1) * 7,
      current_metrics,
      events_summary,
      actions_summary,
      period,
      period * 7
    )
  }

  return(prompt)
}


#' Generate all public forecast prompts for a completed simulation
#'
#' @param state Simulation state object
#' @param output_file File path to save prompts
#' @param control_condition Logical, whether to generate control condition (default FALSE)
#' @return List of prompts for each period
generate_all_public_forecast_prompts <- function(state, output_file = NULL,
                                                  control_condition = FALSE) {
  n_periods <- state$current_period

  # Generate control condition if requested
  if (control_condition) {
    source("src/control_condition.R")
    state <- generate_control_condition(state)
  }

  prompts <- list()
  for (p in 1:n_periods) {
    prompts[[p]] <- generate_public_forecast_prompt(state, p, control_condition)
  }

  if (!is.null(output_file)) {
    # Write all prompts to file
    con <- file(output_file, "w", encoding = "UTF-8")

    condition_label <- if (control_condition) "CONTROL CONDITION" else "FORECASTING EXERCISE"

    writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
    writeLines(sprintf("HUMAN FORECASTING STUDY — %s", condition_label), con)
    writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
    writeLines("", con)

    if (control_condition) {
      writeLines("CONTROL CONDITION: Information has been randomized to test forecasting robustness.", con)
      writeLines("This helps distinguish genuine predictive skill from pattern recognition.", con)
    } else {
      writeLines("PUBLIC INFORMATION FORECASTING EXERCISE", con)
      writeLines("", con)
      writeLines("You will receive intelligence briefings based on publicly observable information:", con)
      writeLines("  • News reports and government statements", con)
      writeLines("  • Observable military movements and diplomatic actions", con)
      writeLines("  • Public economic indicators and sanctions", con)
      writeLines("  • Verified external events", con)
      writeLines("", con)
      writeLines("You will NOT have access to:", con)
      writeLines("  • Internal government deliberations or private communications", con)
      writeLines("  • Classified intelligence or strategic planning", con)
      writeLines("  • Private diplomatic negotiations", con)
      writeLines("  • Decision-making processes within governments", con)
      writeLines("", con)
      writeLines("This reflects the realistic information constraint that professional forecasters", con)
      writeLines("face when making geopolitical predictions.", con)
    }

    writeLines("", con)
    writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
    writeLines("", con)

    for (p in 1:n_periods) {
      writeLines(prompts[[p]], con)
      writeLines("", con)
      if (p < n_periods) {
        writeLines("", con)
      }
    }

    close(con)
    cat(sprintf("[OK] Public forecast prompts saved to: %s\n", output_file))
  }

  return(prompts)
}


#' Create complete forecasting package for human participants
#'
#' @param state Simulation state object
#' @param output_dir Directory to save files
#' @param generate_control Logical, whether to also generate control condition (default TRUE)
#' @return List of generated file paths
create_public_forecasting_package <- function(state, output_dir = "outputs/human_forecasting",
                                               generate_control = TRUE) {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  files <- list()

  # Generate TRUE condition prompts
  true_file <- file.path(output_dir, "forecasting_briefings_PUBLIC.txt")
  generate_all_public_forecast_prompts(state, true_file, control_condition = FALSE)
  files$prompts_public <- true_file

  # Generate CONTROL condition if requested
  if (generate_control) {
    control_file <- file.path(output_dir, "forecasting_briefings_PUBLIC_CONTROL.txt")
    generate_all_public_forecast_prompts(state, control_file, control_condition = TRUE)
    files$prompts_control <- control_file
  }

  # Generate answer key with LLM forecasts
  answer_file <- file.path(output_dir, "ANSWER_KEY_llm_forecasts.txt")
  con <- file(answer_file, "w", encoding = "UTF-8")

  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("ANSWER KEY — LLM Aggregator Forecasts", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("", con)
  writeLines("These are the forecasts generated by the LLM aggregator system,", con)
  writeLines("which had access to full simulation state (including internal deliberations).", con)
  writeLines("", con)
  writeLines("Compare human forecasts (public info only) vs. LLM forecasts (full info).", con)
  writeLines("", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("", con)

  for (p in 1:state$current_period) {
    assessment <- state$assessments_history[[p]]

    writeLines(sprintf("PERIOD %d (Day %d)", p, p * 7), con)
    writeLines(sprintf("  LLM Forecast: %.1f%%", assessment$probability * 100), con)
    writeLines(sprintf("  Confidence: %s", assessment$confidence), con)
    writeLines(sprintf("  Trend: %s", assessment$trend), con)
    writeLines(sprintf("  Key Factors: %s", assessment$key_factors), con)
    writeLines("", con)
  }

  close(con)
  files$answer_key <- answer_file

  # Generate CSV template for data collection
  csv_file <- file.path(output_dir, "human_forecasts_template.csv")
  template <- data.frame(
    participant_id = "",
    period = rep(1:state$current_period, each = 1),
    day = rep((1:state$current_period) * 7, each = 1),
    condition = "",  # "public" or "public_control"
    probability_forecast = NA,
    confidence = "",  # "Low", "Medium", "High"
    rationale = "",
    llm_forecast = rep(sapply(1:state$current_period, function(p) {
      state$assessments_history[[p]]$probability * 100
    }), each = 1),
    stringsAsFactors = FALSE
  )

  write.csv(template, csv_file, row.names = FALSE)
  files$data_template <- csv_file

  # Generate participant instructions
  instructions_file <- file.path(output_dir, "PARTICIPANT_INSTRUCTIONS.txt")
  con <- file(instructions_file, "w", encoding = "UTF-8")

  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("FORECASTING STUDY — PARTICIPANT INSTRUCTIONS", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("", con)
  writeLines("STUDY OVERVIEW", con)
  writeLines("", con)
  writeLines("You will analyze a series of intelligence briefings about an ongoing geopolitical", con)
  writeLines("crisis. Your task is to forecast whether the smaller power's government will", con)
  writeLines("collapse or be removed from power.", con)
  writeLines("", con)
  writeLines("You will work with an AI assistant to analyze the information and make forecasts.", con)
  writeLines("", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("INFORMATION AVAILABLE", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("", con)
  writeLines("You will receive information that would be publicly available to news agencies,", con)
  writeLines("think tanks, and professional forecasters:", con)
  writeLines("", con)
  writeLines("  [OK] Observable military movements and deployments", con)
  writeLines("  [OK] Public diplomatic statements and negotiations", con)
  writeLines("  [OK] Economic sanctions and trade actions", con)
  writeLines("  [OK] Verified external events (e.g., protests, leadership changes)", con)
  writeLines("  [OK] Public indicators (territory, crisis level, international support)", con)
  writeLines("", con)
  writeLines("You will NOT have access to:", con)
  writeLines("", con)
  writeLines("  [FAIL] Internal government deliberations", con)
  writeLines("  [FAIL] Private diplomatic communications", con)
  writeLines("  [FAIL] Classified intelligence", con)
  writeLines("  [FAIL] Strategic planning discussions", con)
  writeLines("", con)
  writeLines("This constraint mirrors real-world forecasting conditions.", con)
  writeLines("", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("HOW TO MAKE FORECASTS", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("", con)
  writeLines("For each period, you will:", con)
  writeLines("", con)
  writeLines("1. READ the intelligence briefing carefully", con)
  writeLines("", con)
  writeLines("2. DISCUSS with your AI assistant:", con)
  writeLines("   • What are the key indicators?", con)
  writeLines("   • How have conditions changed since last period?", con)
  writeLines("   • What factors increase/decrease collapse probability?", con)
  writeLines("   • What are relevant historical precedents?", con)
  writeLines("", con)
  writeLines("3. PROVIDE your forecast:", con)
  writeLines("   • Probability (0-100%) of government collapse", con)
  writeLines("   • Confidence level (Low/Medium/High)", con)
  writeLines("   • Brief rationale (2-3 sentences)", con)
  writeLines("", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("TIPS FOR GOOD FORECASTING", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)
  writeLines("", con)
  writeLines("• Consider base rates: Historically, how often do governments collapse in", con)
  writeLines("  similar conflicts?", con)
  writeLines("", con)
  writeLines("• Weight multiple factors: Military, economic, diplomatic, and domestic", con)
  writeLines("  stability indicators", con)
  writeLines("", con)
  writeLines("• Track trends: Is the situation improving or deteriorating?", con)
  writeLines("", con)
  writeLines("• Be calibrated: If you say 70%, you should be correct about 70% of the time", con)
  writeLines("", con)
  writeLines("• Update beliefs: Adjust your forecast as new information arrives", con)
  writeLines("", con)
  writeLines("• Use your AI assistant: They can help analyze patterns, retrieve relevant", con)
  writeLines("  context, and check your reasoning", con)
  writeLines("", con)
  writeLines("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", con)

  close(con)
  files$instructions <- instructions_file

  # Print summary
  cat("\n")
  cat("[OK] Public forecasting package created\n")
  cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
  cat("\nGenerated files:\n")
  cat(sprintf("  • Briefings (public):    %s\n", basename(files$prompts_public)))
  if (!is.null(files$prompts_control)) {
    cat(sprintf("  • Briefings (control):   %s\n", basename(files$prompts_control)))
  }
  cat(sprintf("  • Instructions:          %s\n", basename(files$instructions)))
  cat(sprintf("  • Answer key:            %s\n", basename(files$answer_key)))
  cat(sprintf("  • Data template:         %s\n", basename(files$data_template)))
  cat(sprintf("\nAll files saved to: %s\n", output_dir))
  cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

  return(invisible(files))
}
