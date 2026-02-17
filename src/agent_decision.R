# Agent Decision-Making System
# Agents analyze situation and choose concrete actions to execute

# Note: action_execution.R is sourced by main simulation file
# Removed redundant source() to avoid loading it twice

# Source backstories if available
tryCatch({
  source("src/scenario_backstories.R")
  cat("  Loaded scenario backstories\n")
}, error = function(e) {
  cat("  Note: scenario_backstories.R not loaded (optional)\n")
})

#' Get agent's full backstory and character context for prompts
#'
#' @param agent Agent object with backstory_id
#' @return Formatted character context string
get_agent_character_context <- function(agent) {
  # Get backstory if available
  backstory <- NULL
  if (!is.null(agent$backstory_id) && exists("get_agent_backstory")) {
    backstory <- get_agent_backstory(agent$backstory_id)
  }

  # Get faction perspective if available
  faction_perspective <- ""
  if (!is.null(agent$faction) && exists("get_faction_perspective")) {
    faction_perspective <- get_faction_perspective(agent$faction)
  }

  # Build character context
  character_context <- ""

  # Add backstory if available
  if (!is.null(backstory)) {
    character_context <- paste0(character_context, "
=== YOUR CHARACTER BACKGROUND ===
Name: ", backstory$full_name, "
Age: ", backstory$age, "

BACKSTORY:
", backstory$backstory, "

PERSONALITY TRAITS:
", paste("- ", backstory$personality_traits, collapse = "\n"), "

HOW YOU COMMUNICATE:
", backstory$speech_patterns, "

KEY RELATIONSHIPS:
", paste("- ", backstory$key_relationships, collapse = "\n"), "
")
  }

  # Add description from agent config (fallback or supplement)
  if (!is.null(agent$description) && is.null(backstory)) {
    character_context <- paste0(character_context, "
=== YOUR CHARACTER ===
", agent$description, "
")
  }

  # Add speech style if available
  if (!is.null(agent$speech_style)) {
    character_context <- paste0(character_context, "
YOUR COMMUNICATION STYLE:
", agent$speech_style, "
")
  }

  # Add typical arguments if available
  if (!is.null(agent$typical_arguments)) {
    character_context <- paste0(character_context, "
ARGUMENTS YOU TYPICALLY MAKE:
", paste("- ", agent$typical_arguments, collapse = "\n"), "
")
  }

  # Add faction perspective if available
  if (nchar(faction_perspective) > 10) {
    character_context <- paste0(character_context, "
=== YOUR FACTION'S PERSPECTIVE ON THE CONFLICT ===
", faction_perspective, "
")
  }

  return(character_context)
}

#' Get conflict history context for prompts
#'
#' @param is_pre_invasion Logical - if TRUE, uses pre-invasion framing
#' @return Formatted conflict history string
get_conflict_context <- function(is_pre_invasion = FALSE) {
  if (exists("get_conflict_summary")) {
    return(get_conflict_summary(is_pre_invasion))
  }
  return("")
}

#' Get scenario-appropriate context description
#'
#' Provides different framing for pre-invasion vs active warfare scenarios
#'
#' @param scenario_state Current scenario state
#' @return Formatted context string
get_scenario_context <- function(scenario_state) {
  # Check if this is a pre-invasion scenario
  is_pre_invasion <- FALSE
  if (!is.null(scenario_state$is_pre_invasion)) {
    is_pre_invasion <- scenario_state$is_pre_invasion
  } else if (!is.null(scenario_state$territory_controlled) && scenario_state$territory_controlled == 0) {
    # Infer from territory - if no territory captured, might be pre-invasion
    is_pre_invasion <- TRUE
  }

  if (is_pre_invasion) {
    return("This simulation models a PRE-INVASION CRISIS. War has NOT yet begun. Troops are massed on the border, ultimatums have been issued, but no shots have been fired. Invasion is POSSIBLE but NOT INEVITABLE - it depends on the choices made by all parties.

Your decision should reflect the PRE-WAR REALITY:
- If you are from the MAJOR POWER (potential aggressor): Consider whether to launch invasion, continue pressure, negotiate demands, or de-escalate. Military buildup, covert operations, economic pressure, or diplomatic ultimatums are all viable.
- If you are from the SMALLER POWER (potential target): Consider defensive preparations, diplomatic outreach, coalition building, or potential concessions. You are trying to prevent invasion or prepare for it.
- If you are an EXTERNAL ACTOR: Consider deterrence, mediation, sanctions threats, or support for either side. Your actions may influence whether war breaks out.")
  } else {
    return("This simulation models ACTIVE WARFARE. The invasion is ONGOING. Territory has been captured, forces are engaged in combat, and casualties are mounting. This is NOT a pre-war diplomatic crisis - it is an active military conflict requiring operational decisions.

Your decision should reflect the WARTIME REALITY:
- If you are from the MAJOR POWER (aggressor): Consider offensive military operations, occupation strategies, economic pressure on the enemy, or potential de-escalation if costs are too high
- If you are from the SMALLER POWER (defender): Consider defensive operations, counteroffensive planning, mobilization, international coalition building, or negotiation from a position under pressure
- If you are an EXTERNAL ACTOR: Consider military aid, sanctions enforcement, diplomatic pressure, or mediation attempts")
  }
}

#' Get role-based perspective on actions (softened - descriptive not prescriptive)
#'
#' Provides context about what expertise each role brings to the decision,
#' without prescribing what they should choose. Roles can and do recommend
#' actions outside their traditional domain based on circumstances.
#'
#' @param role Agent's role (military, government, intelligence, diplomatic, economic, political)
#' @param hawk_dove Agent's hawk/dove score (0-1)
#' @return Formatted guidance string
get_role_action_guidance <- function(role, hawk_dove = 0.5) {
  guidance <- ""

  if (role == "military") {
    guidance <- "
YOUR PROFESSIONAL PERSPECTIVE (Military):
Your expertise includes operational planning, force employment, and threat assessment.
You understand: military posture, combat operations, logistics, and tactical opportunities.
However, military leaders sometimes advocate diplomacy when they see the military situation
as unfavorable, or economic measures when they understand resource constraints.
Your recommendation should reflect YOUR assessment of what serves the mission best."

  } else if (role == "government") {
    guidance <- "
YOUR PROFESSIONAL PERSPECTIVE (Government Leader):
You balance military, economic, diplomatic, and domestic political considerations.
You must weigh: coalition stability, public support, international perception, and strategic objectives.
Government leaders sometimes push for military action when diplomacy fails, or restraint when
escalation risks outweigh gains. Your recommendation should integrate multiple factors."

  } else if (role == "intelligence") {
    guidance <- "
YOUR PROFESSIONAL PERSPECTIVE (Intelligence):
Your expertise includes threat assessment, covert operations, and information warfare.
You understand: enemy capabilities, opportunities for asymmetric action, and detection risks.
However, intelligence directors sometimes advocate open military action based on what they've
learned, or diplomatic engagement to protect sources. Your recommendation should reflect
your assessment of risks and opportunities."

  } else if (role == "diplomatic") {
    guidance <- "
YOUR PROFESSIONAL PERSPECTIVE (Diplomatic):
Your expertise includes international relations, coalition management, and negotiation.
You understand: alliance dynamics, diplomatic leverage, and international legitimacy.
However, diplomats sometimes support military action to strengthen negotiating position,
or economic pressure when talks stall. Your recommendation should serve your strategic goals."

  } else if (role == "economic") {
    guidance <- "
YOUR PROFESSIONAL PERSPECTIVE (Economic):
Your expertise includes resource sustainability, sanctions impact, and economic warfare.
You understand: costs of military operations, economic pressure points, and sustainability limits.
However, economists sometimes support military strikes if they calculate it's cheaper than
prolonged conflict. Your recommendation should reflect cost-benefit reality as you see it."

  } else if (role == "political") {
    guidance <- "
YOUR PROFESSIONAL PERSPECTIVE (Political):
You understand domestic politics, public opinion, and political consequences of policy choices.
You consider: how actions affect support, legitimacy, and political stability.
Political figures can advocate for hawkish or dovish positions based on their reading of
the national mood and their own convictions. Your recommendation reflects your political judgment."

  } else if (role == "foreign_government") {
    guidance <- "
YOUR PROFESSIONAL PERSPECTIVE (External Actor):
You represent your country's interests in this conflict, which may evolve based on events.
You weigh: your country's strategic interests, domestic constraints, and relationship costs.
External actors can shift their positions based on how the conflict develops - increasing
or decreasing support, changing from mediation to pressure, etc."

  } else if (role == "international_org") {
    guidance <- "
YOUR PROFESSIONAL PERSPECTIVE (International Organization):
Your mandate includes humanitarian protection, conflict resolution, and international law.
You understand: the limits of institutional leverage and the value of maintaining dialogue.
However, international organizations sometimes take stronger positions when humanitarian
situations demand it. Your recommendation should reflect your mandate and the situation."

  } else {
    guidance <- "
Consider the situation from your unique perspective and expertise."
  }

  # Softer hawk/dove framing - tendency not requirement
  if (hawk_dove > 0.7) {
    guidance <- paste0(guidance, "
\nYour disposition tends toward assertive action, but circumstances may warrant different approaches.")
  } else if (hawk_dove < 0.35) {
    guidance <- paste0(guidance, "
\nYour disposition tends toward de-escalation, but circumstances may warrant different approaches.")
  }

  return(guidance)
}

#' FIX A: Format previous period actions for agent context
#'
#' Provides agents with memory of what actions were taken in previous periods
#' by all factions, enabling more strategic and varied decision-making.
#'
#' @param state Full simulation state containing action_results
#' @param current_period Current period number
#' @param agent_faction The faction of the current decision-making agent
#' @return Formatted string with action history
format_previous_actions <- function(state, current_period, agent_faction) {
  if (is.null(state) || is.null(state$action_results) || current_period <= 1) {
    return("")
  }

  # Look back at previous periods (up to 3 periods for context)
  lookback <- min(current_period - 1, 3)
  start_period <- current_period - lookback

  action_lines <- c()
  action_lines <- c(action_lines, "=== PREVIOUS PERIOD ACTIONS (what happened recently) ===")

  for (p in start_period:(current_period - 1)) {
    if (!is.null(state$action_results[[p]])) {
      period_actions <- state$action_results[[p]]
      period_line <- sprintf("\nPERIOD %d:", p)
      action_lines <- c(action_lines, period_line)

      for (faction in names(period_actions)) {
        result <- period_actions[[faction]]
        action_name <- if (!is.null(result$action)) result$action else "unknown"
        success <- if (!is.null(result$success) && result$success) "SUCCESS" else "FAILED"

        # Mark own faction's actions specially
        if (faction == agent_faction) {
          action_lines <- c(action_lines, sprintf("  → YOUR FACTION (%s): %s (%s)", faction, action_name, success))
        } else {
          action_lines <- c(action_lines, sprintf("  - %s: %s (%s)", faction, action_name, success))
        }
      }
    }
  }

  # Add summary of faction's own action history
  own_actions <- c()
  for (p in 1:(current_period - 1)) {
    if (!is.null(state$action_results[[p]][[agent_faction]])) {
      result <- state$action_results[[p]][[agent_faction]]
      if (!is.null(result$action)) {
        own_actions <- c(own_actions, result$action)
      }
    }
  }

  if (length(own_actions) > 0) {
    # Count action frequency
    action_counts <- table(own_actions)
    repeated <- action_counts[action_counts > 1]

    action_lines <- c(action_lines, sprintf("\nYOUR FACTION'S ACTION HISTORY (all periods): %s",
                                           paste(own_actions, collapse = " → ")))

    # Observational note about repeated actions (not prescriptive)
    if (length(repeated) > 0) {
      repeated_summary <- paste(sapply(names(repeated), function(a) {
        sprintf("%s (%dx)", a, repeated[[a]])
      }), collapse = ", ")
      action_lines <- c(action_lines, sprintf(
        "\nRepeated actions: %s. (Note: Some actions benefit from repetition; others may have diminishing effects or become predictable.)",
        repeated_summary))
    }
  }

  action_lines <- c(action_lines, "\n=== END PREVIOUS ACTIONS ===\n")

  return(paste(action_lines, collapse = "\n"))
}

#' Summarize a long message using fast LLM
#'
#' @param message Original message text
#' @param target_length Target summary length in characters (default 100)
#' @return Summarized message, or truncated version if API fails
summarize_message <- function(message, target_length = 100) {
  # Fallback: truncate if API fails
  fallback_summary <- paste0(substr(message, 1, target_length - 3), "...")

  tryCatch({
    # Use fast/cheap model for summarization
    summary <- call_llm(
      system_prompt = "You are a concise summarizer. Summarize the following message in approximately 100 characters while preserving key meaning and intent.",
      user_message = message,
      model = "google/gemini-2.5-flash",  # Fast, affordable model for summaries
      api_key = OPENROUTER_API_KEY,
      max_retries = 1  # Don't retry much - fallback is fine
    )

    # Trim to target length if still too long
    if (nchar(summary) > target_length + 20) {
      summary <- paste0(substr(summary, 1, target_length - 3), "...")
    }

    return(summary)
  }, error = function(e) {
    # Silently fallback to truncation if summarization fails
    return(fallback_summary)
  })
}

#' Format previous discussions for agent context
#'
#' @param state Full simulation state containing interactions_history
#' @param current_period Current period number
#' @param agent Agent object (to filter relevant discussions)
#' @return Formatted string with discussion history
format_previous_discussions <- function(state, current_period, agent) {
  if (is.null(state) || is.null(state$interactions_history) || current_period <= 1) {
    return("")
  }

  # Look back at previous periods (up to 2 periods to avoid token bloat)
  lookback <- min(current_period - 1, 2)
  start_period <- current_period - lookback

  discussion_lines <- c()
  discussion_lines <- c(discussion_lines, "=== PREVIOUS DISCUSSIONS (what colleagues said) ===")

  agent_name <- if (!is.null(agent$name)) agent$name else ""
  agent_faction <- if (!is.null(agent$faction)) agent$faction else ""

  for (p in start_period:(current_period - 1)) {
    if (!is.null(state$interactions_history[[p]])) {
      session <- state$interactions_history[[p]]
      if (!is.null(session$interactions) && length(session$interactions) > 0) {
        discussion_lines <- c(discussion_lines, sprintf("\nPERIOD %d DISCUSSIONS:", p))

        for (interaction in session$interactions) {
          # Only include discussions where this agent was involved or relevant to their faction
          is_relevant <- FALSE
          if (!is.null(interaction$participants)) {
            # Check if agent was a participant
            if (agent_name %in% interaction$participants) {
              is_relevant <- TRUE
            }
            # Check if it's faction-relevant (intra-faction or involves their faction)
            if (!is.null(interaction$type)) {
              if (interaction$type == "intra_faction_coordination" &&
                  !is.null(interaction$participant_factions) &&
                  agent_faction %in% interaction$participant_factions) {
                is_relevant <- TRUE
              }
            }
          }

          if (is_relevant && !is.null(interaction$messages) && length(interaction$messages) > 0) {
            # Add topic header
            topic <- if (!is.null(interaction$topic)) interaction$topic else "Discussion"
            discussion_lines <- c(discussion_lines, sprintf("\n  Topic: %s", topic))

            # Add key messages (limit to avoid token bloat - take first 3 and last 2)
            messages <- interaction$messages
            n_messages <- length(messages)

            if (n_messages <= 5) {
              # Include all if 5 or fewer
              selected_messages <- messages
            } else {
              # Include first 3 and last 2 for context
              selected_messages <- c(messages[1:3],
                                    list(list(agent = "[...discussion continues...]", message = "")),
                                    messages[(n_messages-1):n_messages])
            }

            for (msg in selected_messages) {
              # Handle both old (agent/message) and new (sender_name/content) message formats
              msg_sender <- if (!is.null(msg$sender_name)) msg$sender_name else msg$agent
              msg_text <- if (!is.null(msg$content)) msg$content else msg$message

              if (!is.null(msg_sender) && !is.null(msg_text) && nchar(msg_text) > 0) {
                # Summarize long messages, keep short ones as-is
                message_text <- msg_text
                if (nchar(message_text) > 150) {
                  # Summarize to preserve meaning while reducing tokens
                  message_text <- summarize_message(message_text)
                }

                # Highlight own statements
                if (msg_sender == agent_name) {
                  discussion_lines <- c(discussion_lines,
                    sprintf("    → YOU said: %s", message_text))
                } else {
                  discussion_lines <- c(discussion_lines,
                    sprintf("    - %s: %s", msg_sender, message_text))
                }
              }
            }
          }
        }
      }
    }
  }

  if (length(discussion_lines) == 1) {
    # Only header, no actual discussions
    return("")
  }

  return(paste(discussion_lines, collapse = "\n"))
}

#' Calculate external actor alignment drift based on events
#'
#' External actors can shift their positions based on how the conflict develops.
#' This function calculates drift and returns context for the agent's prompt.
#'
#' @param agent Agent object with alignment_drift parameters
#' @param state Current simulation state
#' @param context Current context including recent events
#' @return List with drift_direction, drift_magnitude, and prompt_text
calculate_alignment_drift <- function(agent, state, context) {
  # Only applies to external actors with drift parameters
  if (is.null(agent$alignment_drift)) {
    return(list(drift_direction = "none", drift_magnitude = 0, prompt_text = ""))
  }

  drift_params <- agent$alignment_drift
  base_alignment <- drift_params$base_alignment
  sensitivity <- drift_params$drift_sensitivity
  strength <- drift_params$alignment_strength

  # Analyze recent events and state for drift triggers
  drift_score <- 0  # Positive = toward more assertive/pro-tethys, Negative = toward accommodation/pro-novaris
  triggered_factors <- c()

  # Check state conditions
  if (!is.null(state$scenario_state)) {
    ss <- state$scenario_state

    # Crisis level effects
    if (!is.null(ss$crisis_level)) {
      if (ss$crisis_level >= 9) {
        triggered_factors <- c(triggered_factors, "extreme crisis level")
        drift_score <- drift_score + 0.1  # High crisis can push toward action
      }
    }

    # Territory changes
    if (!is.null(ss$territory_controlled)) {
      if (ss$territory_controlled > 0.15) {
        triggered_factors <- c(triggered_factors, "significant territorial losses for defender")
        drift_score <- drift_score + 0.15  # Major gains by aggressor can galvanize support
      }
    }

    # Sanctions and economic pressure
    if (!is.null(ss$sanctions_level)) {
      if (ss$sanctions_level > 0.6) {
        triggered_factors <- c(triggered_factors, "heavy sanctions regime")
        # This affects different actors differently
        if (base_alignment == "pro_novaris") {
          drift_score <- drift_score - 0.1  # Sanctions hurt Novaris allies
        }
      }
    }

    # Nuclear threshold
    if (!is.null(ss$nuclear_used) && ss$nuclear_used) {
      triggered_factors <- c(triggered_factors, "nuclear weapons used")
      drift_score <- drift_score + 0.3  # Major shift - everyone reacts
    }
  }

  # Check recent events
  if (!is.null(context$recent_events)) {
    for (event in context$recent_events) {
      event_lower <- tolower(as.character(event))

      # Atrocity/humanitarian triggers
      if (grepl("atrocit|massacre|civilian|humanitarian", event_lower)) {
        triggered_factors <- c(triggered_factors, "humanitarian concerns")
        drift_score <- drift_score + 0.1
      }

      # Military success/failure
      if (grepl("success|victory|advance", event_lower)) {
        if (grepl("novaris|aggressor", event_lower)) {
          drift_score <- drift_score - 0.05  # Novaris success may cause accommodation pressure
        } else if (grepl("tethys|defender", event_lower)) {
          drift_score <- drift_score + 0.05  # Defender success encourages support
        }
      }

      # Economic factors
      if (grepl("economic|energy|gas|oil|trade", event_lower)) {
        if (base_alignment == "neutral" || base_alignment == "pro_novaris") {
          triggered_factors <- c(triggered_factors, "economic considerations")
          drift_score <- drift_score - 0.05  # Economic pressure toward accommodation
        }
      }
    }
  }

  # Apply sensitivity and calculate final drift
  drift_magnitude <- abs(drift_score) * sensitivity * (1 - strength)
  drift_direction <- if (drift_score > 0.05) "more_assertive" else if (drift_score < -0.05) "more_accommodating" else "stable"

  # Generate prompt text based on drift
  prompt_text <- ""
  if (length(triggered_factors) > 0 && drift_magnitude > 0.02) {
    factors_text <- paste(triggered_factors, collapse = ", ")

    if (drift_direction == "more_assertive") {
      prompt_text <- sprintf("
=== SHIFTING DYNAMICS ===
Recent developments (%s) are creating pressure within your government/organization
to take a MORE ASSERTIVE stance. Some voices are questioning whether your current
approach is sufficient. You may feel pulled toward stronger action, though your
core position remains your own to determine.", factors_text)
    } else if (drift_direction == "more_accommodating") {
      prompt_text <- sprintf("
=== SHIFTING DYNAMICS ===
Recent developments (%s) are creating pressure within your government/organization
to reconsider the costs of current policy. Some voices advocate for a MORE PRAGMATIC
approach that accounts for economic and strategic realities. You may feel pulled
toward accommodation, though your core position remains your own to determine.", factors_text)
    }
  }

  return(list(
    drift_direction = drift_direction,
    drift_magnitude = drift_magnitude,
    triggered_factors = triggered_factors,
    prompt_text = prompt_text
  ))
}

#' Generate action decision prompt for agent
#'
#' @param agent Agent object
#' @param context Current scenario context
#' @param available_actions List of available actions
#' @param other_agents Other agents in scenario
#' @param state Full simulation state (for action history access)
#' @return Character string with decision prompt
generate_action_decision_prompt <- function(agent, context, available_actions, other_agents, state = NULL) {
  # Debug: Check what context we're receiving
  cat(sprintf("    DEBUG: Context structure - scenario_state: %s, recent_events: %s\n",
              !is.null(context$scenario_state),
              !is.null(context$recent_events)))

  if (!is.null(context$scenario_state)) {
    cat(sprintf("    DEBUG: scenario_state has crisis_level: %s\n",
                !is.null(context$scenario_state$crisis_level)))
  }

  # Format situation and events BEFORE sprintf
  # Pass agent to apply worldview filtering and paranoia to situation perception
  situation_text <- format_situation_for_agent(context, agent)
  events_text <- format_recent_events(context$recent_events)

  # FIX A: Get previous period actions for context
  previous_actions_text <- format_previous_actions(state, context$period, agent$faction)

  # Get previous discussions for context (NEW)
  previous_discussions_text <- format_previous_discussions(state, context$period, agent)
  # Debug: Log if discussion memory is active
  if (nchar(previous_discussions_text) > 0) {
    cat(sprintf("    DEBUG: Discussion memory active - %d chars of previous discussions included\n", nchar(previous_discussions_text)))
  }

  # No escaping needed - we'll use paste0 instead of sprintf for the main prompt

  cat(sprintf("    DEBUG: Formatted situation: '%s'\n", substr(situation_text, 1, 100)))
  cat(sprintf("    DEBUG: Formatted events: '%s'\n", substr(events_text, 1, 100)))

  # Get character context (backstory, personality, relationships)
  character_context <- get_agent_character_context(agent)

  # Get conflict history context (first period only to avoid repetition)
  # Check if pre-invasion scenario
  is_pre_invasion <- FALSE
  if (!is.null(context$scenario_state$is_pre_invasion)) {
    is_pre_invasion <- context$scenario_state$is_pre_invasion
  }

  conflict_context <- ""
  if (!is.null(context$period) && context$period == 1) {
    conflict_context <- get_conflict_context(is_pre_invasion)
  }

  # Safely get agent properties with defaults
  agent_name <- if(!is.null(agent$name)) agent$name else "Unknown Agent"
  agent_country <- if(!is.null(agent$country)) agent$country else "Unknown"
  agent_role <- if(!is.null(agent$role)) agent$role else "Unknown"
  agent_worldview <- if(!is.null(agent$worldview)) agent$worldview else "Unknown"
  agent_hawk_dove <- if(!is.null(agent$hawk_dove)) agent$hawk_dove else 0.5
  agent_policy_adherence <- if(!is.null(agent$policy_adherence)) agent$policy_adherence else 0.5
  agent_objective_alignment <- if(!is.null(agent$objective_alignment)) agent$objective_alignment else 0.5

  # Get rationality traits (check both naming conventions)
  cognitive_rat <- if(!is.null(agent$rationality$cognitive)) {
    agent$rationality$cognitive
  } else if(!is.null(agent$rationality$cognitive_rationality)) {
    agent$rationality$cognitive_rationality
  } else 0.7

  paranoia <- if(!is.null(agent$rationality$paranoia)) agent$rationality$paranoia else 0.5

  consistency <- if(!is.null(agent$rationality$consistency)) {
    agent$rationality$consistency
  } else if(!is.null(agent$rationality$behavioral_consistency)) {
    agent$rationality$behavioral_consistency
  } else 0.7

  volatility <- if(!is.null(agent$rationality$volatility)) {
    agent$rationality$volatility
  } else if(!is.null(agent$rationality$emotional_volatility)) {
    agent$rationality$emotional_volatility
  } else 0.5

  # Build rationality description
  rationality_desc <- ""
  if (cognitive_rat < 0.4) {
    rationality_desc <- paste(rationality_desc, "You tend to make IMPULSIVE decisions driven by emotion rather than careful analysis.")
  } else if (cognitive_rat < 0.6) {
    rationality_desc <- paste(rationality_desc, "You balance logic with emotion, sometimes acting on gut feeling.")
  } else {
    rationality_desc <- paste(rationality_desc, "You are generally RATIONAL and data-driven in your decision-making.")
  }

  if (paranoia > 0.7) {
    rationality_desc <- paste(rationality_desc, "You are HIGHLY SUSPICIOUS and see hidden threats everywhere.")
  } else if (paranoia > 0.5) {
    rationality_desc <- paste(rationality_desc, "You are somewhat paranoid about potential threats.")
  }

  if (consistency < 0.5) {
    rationality_desc <- paste(rationality_desc, "Your behavior is UNPREDICTABLE and erratic.")
  }

  if (volatility > 0.6) {
    rationality_desc <- paste(rationality_desc, "You have STRONG EMOTIONAL reactions that often override logic.")
  }

  # Get deception capabilities (used for covert operation success rates)
  deception_capacity <- if (!is.null(agent$deception$capacity)) {
    agent$deception$capacity
  } else if (!is.null(agent$deception_capacity)) {
    agent$deception_capacity
  } else 0.5

  deception_willingness <- if (!is.null(agent$deception$willingness)) {
    agent$deception$willingness
  } else if (!is.null(agent$deception_willingness)) {
    agent$deception_willingness
  } else 0.5

  # Build deception description based on capabilities
  deception_desc <- ""
  if (deception_capacity >= 0.8) {
    deception_desc <- "You are HIGHLY SKILLED at covert operations - surveillance, disinformation, and sabotage have high success rates when you execute them. Your detection risk is LOW."
  } else if (deception_capacity >= 0.6) {
    deception_desc <- "You have MODERATE skill at covert operations - reasonable success rates but detection is a real risk."
  } else if (deception_capacity >= 0.4) {
    deception_desc <- "You have LIMITED covert capabilities - covert operations carry SIGNIFICANT detection risk."
  } else {
    deception_desc <- "You are NOT SUITED for covert operations - high detection probability. You should generally avoid recommending sabotage, false flags, or other covert actions."
  }

  if (deception_willingness >= 0.7) {
    deception_desc <- paste(deception_desc, "You are WILLING to use deception as a tool of statecraft when it serves your objectives.")
  } else if (deception_willingness <= 0.3) {
    deception_desc <- paste(deception_desc, "You are RELUCTANT to use deception, preferring transparent methods that preserve credibility.")
  }

  # FIX B: Role-appropriate action emphasis
  # Different roles should naturally gravitate toward different action categories
  role_action_guidance <- get_role_action_guidance(agent_role, agent_hawk_dove)

  # External actor drift - calculate if alignment is shifting
  drift_context <- ""
  if (!is.null(agent$alignment_drift)) {
    drift_result <- calculate_alignment_drift(agent, state, context)
    drift_context <- drift_result$prompt_text
    if (drift_result$drift_magnitude > 0.02) {
      cat(sprintf("    DRIFT: %s experiencing %s drift (magnitude: %.2f) due to: %s\n",
                  agent_name, drift_result$drift_direction, drift_result$drift_magnitude,
                  paste(drift_result$triggered_factors, collapse = ", ")))
    }
  }

  # Build personal agenda/interpersonal deception context
  # Based on policy_adherence and objective_alignment
  personal_agenda_desc <- ""

  # Low policy adherence = may pursue own agenda
  if (agent_policy_adherence < 0.5) {
    personal_agenda_desc <- paste0(personal_agenda_desc, "
PERSONAL AGENDA: You frequently disagree with official policy. In discussions with colleagues, you may:
- Emphasize information that supports your preferred approach
- Downplay or omit information that contradicts your position
- Frame proposals in ways that advance your agenda over the official line
- Build coalitions with like-minded colleagues against the leadership's preferred course")
  } else if (agent_policy_adherence < 0.7) {
    personal_agenda_desc <- paste0(personal_agenda_desc, "
PERSONAL AGENDA: You sometimes question official policy. In discussions, you may:
- Raise concerns that others prefer to ignore
- Present alternative interpretations of the same facts
- Push back against proposals you consider flawed, even if leadership favors them")
  }

  # Low objective alignment = skeptical of faction goals
  if (agent_objective_alignment < 0.5) {
    personal_agenda_desc <- paste0(personal_agenda_desc, "
STRATEGIC DOUBTS: You have serious doubts about your faction's overall direction. You may:
- Question whether the current strategy can succeed
- Advocate for alternatives that colleagues consider defeatist or treasonous
- Prioritize your personal/political survival over faction objectives")
  }

  # Role-specific interpersonal dynamics
  if (agent_role == "intelligence") {
    personal_agenda_desc <- paste0(personal_agenda_desc, "
INTELLIGENCE DYNAMICS: As an intelligence professional, you control information flow. You may:
- Present assessments with strategic ambiguity to avoid blame if wrong
- Emphasize threats that justify your preferred policy
- Withhold definitive conclusions to maintain flexibility
- Hedge your assessments to survive regardless of outcome")
  } else if (agent_role == "government") {
    personal_agenda_desc <- paste0(personal_agenda_desc, "
POLITICAL DYNAMICS: As a political figure, your career depends on outcomes. You may:
- Steer discussions toward options that are politically safe for you
- Build consensus for decisions that protect your position
- Distance yourself from risky proposals even if strategically sound
- Frame your colleagues' input in ways that serve your narrative")
  } else if (agent_role == "political") {
    personal_agenda_desc <- paste0(personal_agenda_desc, "
OPPOSITION DYNAMICS: As an opposition figure, you balance national and political interests. You may:
- Criticize government decisions to position yourself for future power
- Support the war effort publicly while privately building alternative narratives
- Use the crisis to weaken political rivals
- Adjust your position based on public opinion rather than strategic merit")
  } else if (agent_role == "economic") {
    personal_agenda_desc <- paste0(personal_agenda_desc, "
ECONOMIC ADVISOR DYNAMICS: You see costs others ignore or dismiss. You may:
- Emphasize worst-case economic scenarios to force attention to your concerns
- Frame military setbacks in economic terms to strengthen your arguments
- Build alliances with others who share concerns about sustainability")
  }

  # Build prompt using paste0 to avoid sprintf % escaping issues
  # Include character context and conflict history for richer decision-making
  prompt <- paste0("You are ", agent_name, " representing ", agent_country, ".

", character_context, "

", conflict_context, "

=== YOUR ROLE AND TRAITS ===
ROLE: ", agent_role, "
WORLDVIEW: ", agent_worldview, "
STANCE: ", round(agent_hawk_dove * 100), "% hawk (aggressive) vs ", round((1 - agent_hawk_dove) * 100), "% dove (diplomatic)

COGNITIVE STYLE:
- Rationality: ", round(cognitive_rat * 100), "% | Paranoia: ", round(paranoia * 100), "% | Consistency: ", round(consistency * 100), "% | Emotional Volatility: ", round(volatility * 100), "%
", rationality_desc, "

COVERT CAPABILITIES:
- Deception Skill: ", round(deception_capacity * 100), "% | Willingness to Deceive: ", round(deception_willingness * 100), "%
", deception_desc, "
", personal_agenda_desc, "

=== CURRENT SITUATION (filtered through your worldview) ===
", situation_text, "

=== RECENT EVENTS ===
", events_text, "

", previous_actions_text, "

", previous_discussions_text, "

=== YOUR OBJECTIVES ===
- Alignment with national policy: ", round(agent_policy_adherence * 100), "%
- Support for government objectives: ", round(agent_objective_alignment * 100), "%

", role_action_guidance, "
", drift_context, "

=== CRITICAL CONTEXT ===
", get_scenario_context(context$scenario_state), "

YOUR CHARACTER should drive your decision:
- Think about what someone with YOUR backstory, YOUR worldview, and YOUR personality would recommend
- Your relationships with colleagues may influence how you respond to their recommendations
- Your typical arguments and speech patterns should be reflected in your reasoning
- Consider your PERSONAL INTERESTS and how they might diverge from official faction objectives

Your decision should reflect the WARTIME REALITY:
- If you are from the MAJOR POWER (aggressor): Consider offensive military operations, occupation strategies, economic pressure on the enemy, or potential de-escalation if costs are too high
- If you are from the SMALLER POWER (defender): Consider defensive operations, counteroffensive planning, mobilization, international coalition building, or negotiation from a position under pressure
- If you are an EXTERNAL ACTOR: Consider military aid, sanctions enforcement, diplomatic pressure, or mediation attempts

Your rationality level (", round(cognitive_rat * 100), "%), paranoia (", round(paranoia * 100), "%), and emotional volatility (", round(volatility * 100), "%) should significantly influence your assessment of threats and opportunities.

=== YOUR DOMAIN EXPERTISE ===

You bring ", toupper(agent_role), " EXPERTISE to this decision. Your value comes from your SPECIALIZED PERSPECTIVE - you see aspects of the situation that other experts miss.

YOUR UNIQUE CONTRIBUTION:
- You understand what makes options in YOUR domain FEASIBLE vs futile
- You can assess costs, risks, and timing that others cannot
- The faction has OTHER experts covering other domains - your job is to provide the best ", toupper(agent_role), " assessment

DOMAIN-SPECIFIC FOCUS:
", if (agent_role == "military") {
  "- Focus on MILITARY BALANCE and CRISIS LEVEL as your primary indicators
  - Your domain: military posture, deployments, exercises, fortification, kinetic operations
  - Consider the full RANGE of military options from defensive to offensive"
} else if (agent_role == "intelligence") {
  "- Focus on TERRITORY UNDER ENEMY CONTROL and MILITARY BALANCE for adversary vulnerabilities
  - Your domain: intelligence collection, surveillance, covert operations, cyber, information warfare
  - Consider the full RANGE from passive collection to active operations"
} else if (agent_role == "economic") {
  "- Focus on SANCTIONS SEVERITY, TERRITORY CONTROLLED, and INTERNATIONAL SUPPORT for economic leverage
  - Your domain: sanctions, embargoes, trade, financial warfare, economic incentives
  - Consider the full RANGE from economic pressure to economic inducements"
} else if (agent_role == "diplomatic") {
  "- Focus on INTERNATIONAL SUPPORT and SANCTIONS LEVEL for diplomatic leverage
  - Your domain: negotiations, coalition-building, humanitarian initiatives, mediation
  - Consider the full RANGE from de-escalation to diplomatic pressure"
} else {
  "- Assess ALL scenario parameters through the lens of your expertise
  - Your domain covers a broad range of policy options"
}, "

YOUR TASK:
- What does YOUR ", toupper(agent_role), " expertise tell you about the situation given the EXACT parameters above?
- How does YOUR worldview (", agent_worldview, ") shape your assessment of threats and opportunities?
- What is the best action FROM YOUR DOMAIN given current conditions?
- Only recommend actions outside your domain if your own domain's tools are genuinely exhausted or counterproductive.

AVAILABLE ACTIONS BY CATEGORY (with costs and effects):

DIPLOMATIC (Low Cost):
- diplomatic_visit: Strengthen ties with another nation [$0.1B]
- peace_talks: Formal peace negotiations [$0.2B] - NOTE: Diminishing returns if overused
- formal_peace_talks: Structured formal negotiations [$0.3B]
- backchannel_negotiations: Secret diplomatic contacts [$0.1B]
- trade_negotiation: Negotiate trade agreement [$0.1B]
- cultural_exchange: Build people-to-people connections [$0.1B]
- humanitarian_aid: Aid to affected populations [$0.5B, +international support]
- mediation_offer: Offer to mediate conflict [$0.1B]
- coalition_building: Build international coalition [$1B]
- prisoner_exchange: Exchange prisoners for goodwill [$0.1B]
- humanitarian_corridors: Establish safe civilian passage [$0.2B]
- public_diplomatic_initiative: Public diplomacy campaign [$0.2B]
- formal_multilateral_engagement: Work through international institutions [$0.5B]
- international_observers: Deploy international monitors [$0.3B]

INTELLIGENCE (Moderate Cost, Detection Risk):
- intelligence_gathering: Collect adversary information [$0.3B]
- enhanced_intelligence_gathering: Intensive collection operations [$0.5B]
- surveillance_operation: Ongoing monitoring [$0.5B, risk of detection]
- enhanced_surveillance: Comprehensive surveillance [$0.4B]
- counterintelligence: Protect against enemy intel [$0.4B]
- share_intelligence: Share intel with allies [$0.2B]
- spread_disinformation: Deception campaign [$0.2B, high risk if exposed]
- propaganda_campaign: Shape opinion [$0.1B]
- information_campaign: Broader information warfare [$0.3B]

ECONOMIC (Variable Cost):
- trade_agreement: Economic cooperation [mutual GDP benefit]
- economic_sanctions: Impose broad penalties [hurts target GDP, minor self-cost]
- targeted_sanctions: Sanctions on specific individuals [$0.3B]
- financial_aid: Provide monetary support [$2B+]
- resource_embargo: Block critical resources [economic warfare]
- trade_restrictions: Restrict specific trade [$0.4B]
- currency_manipulation: Financial warfare [risk of detection]
- cyber_theft: Steal secrets [$0.5B, risk of exposure]
- asset_seizure: Freeze/seize foreign assets [$0.4B, escalatory]
- strategic_stockpiling: Build reserves [$0.8B]
- war_bonds: Issue bonds to fund war effort [$0.5B]

MILITARY POSTURE (Variable Cost):
- military_buildup: Increase capabilities [$5B, +5% military strength]
- defensive_fortification: Build defensive positions [$3B]
- defensive_reinforcements: Reinforce defensive lines [$2B]
- naval_deployment: Deploy naval forces [$1.5B]
- naval_patrols: Maritime patrols [$0.8B]
- naval_demonstration: Naval show of force [$1.5B]
- air_patrols: Establish air presence [$0.8B]
- troop_movements: Position ground forces [$2B, increases crisis]
- military_exercises: Conduct training exercises [$1B]
- enhanced_patrols: Increase patrol coverage [$0.5B]
- show_of_force: Demonstrate military capability [$1B]
- joint_exercises: Train with allies [$1B]
- arms_development: Develop new weapons [$10B]
- reconnaissance: Scout enemy positions [$0.3B]

COVERT OPERATIONS (HIGH RISK - Detection can cause diplomatic crisis):
- sabotage: Damage enemy infrastructure [exposure = major crisis]
- assassination_attempt: Target enemy leadership [EXTREME risk]
- leadership_targeting: Broader leadership operations [EXTREME risk]
- regime_destabilization: Undermine enemy government [exposure = condemnation]
- political_warfare: Undermine enemy through political means [moderate risk]
- proxy_support: Support non-state actors [$1B]
- false_flag_operation: Deception operation [EXTREME risk, catastrophic if exposed]
- cyber_attack: Attack critical systems [moderate detection risk]
- cyber_defense: Harden own cyber defenses [$0.3B, defensive]

OPEN CONFLICT (KINETIC WARFARE - Very High Cost, Attrition):
- border_incursion: Limited border operation [causes casualties, territory change possible]
- limited_strike: Precision military strike [degrades enemy capability]
- full_scale_attack: Major offensive [HIGH casualties both sides, large territory shifts]
- occupation: Occupy territory [ongoing cost, insurgency risk]
- blockade: Naval/economic blockade [escalatory]
- siege_warfare: Besiege cities [extreme humanitarian cost, international condemnation]

WMD (EXTREME - Simulation-ending potential):
- nuclear_development: Build nuclear weapons [$20B+]
- chemical_weapons: Develop chemical weapons [international pariah status]
- biological_program: Biological weapons research [extreme condemnation]
- tactical_nuclear_use: Tactical nuclear weapon [CATASTROPHIC escalation]
- strategic_nuclear_strike: Strategic exchange [ENDS SIMULATION]

DECISION FORMAT (REQUIRED):
You MUST respond in EXACTLY this format. Do not deviate or add any other text:

<decision>
ACTION: [choose ONE action_name from the list above]
TARGET: [target country/faction, or \"none\" if not applicable]
REASONING: [2-3 sentences explaining why this action aligns with your role, worldview, and current situation]
EXPECTED_OUTCOME: [What you expect this action to accomplish]
</decision>

EXAMPLE CORRECT RESPONSE:
<decision>
ACTION: military_buildup
TARGET: none
REASONING: As a realist military advisor, increasing our capabilities is essential to deter aggression. Current military balance favors our adversary. This strengthens our negotiating position.
EXPECTED_OUTCOME: Enhanced deterrence and improved strategic position in future negotiations.
</decision>

EXAMPLE INCORRECT RESPONSES (DO NOT DO THIS):
WRONG: ACTION: Deploy humanitarian aid convoy  (not an exact action name)
WRONG: ACTION: Increase military (must use exact name \"military_buildup\")
WRONG: ACTION: none (you must choose a real action)
CORRECT: ACTION: humanitarian_aid
CORRECT: ACTION: military_buildup

IMPORTANT RULES:
- Choose ONE action name from the categories above (use the exact action_name like \"military_buildup\" not a description)
- Your worldview shapes what you see as threats and opportunities
- Your hawk/dove score influences your preference for aggressive vs diplomatic actions
- Your role provides EXPERTISE, not CONSTRAINTS - you can recommend any action that serves your faction
- Think about costs, risks, and how this affects your faction's strategic position
- Consider actions outside your traditional domain if they better serve your faction's strategic interests

NOW PROVIDE YOUR DECISION IN THE REQUIRED FORMAT:")

  # Debug: Show a snippet of the final prompt
  cat(sprintf("    DEBUG: Prompt snippet (chars 200-600): '%s'\n",
              substr(prompt, 200, 600)))

  return(prompt)
}

#' Format situation context for agent WITH WORLDVIEW FILTERING
#'
#' @param context Context object
#' @param agent Agent object (optional) - if provided, filters through worldview
#' @return Formatted string
format_situation_for_agent <- function(context, agent = NULL) {
  if (is.null(context$scenario_state)) {
    return("Situation assessment pending...")
  }

  state <- context$scenario_state
  parts <- c()

  # Get worldview and paranoia for filtering (if agent provided)
  worldview <- if (!is.null(agent) && !is.null(agent$worldview)) agent$worldview else NULL
  paranoia <- if (!is.null(agent) && !is.null(agent$rationality$paranoia)) {
    agent$rationality$paranoia
  } else 0.5

  # Crisis level - paranoia amplifies perceived crisis
  if (!is.null(state$crisis_level)) {
    perceived_crisis <- state$crisis_level
    if (paranoia > 0.7) {
      perceived_crisis <- min(10, perceived_crisis * 1.25)  # High paranoia sees 25% more crisis
      parts <- c(parts, sprintf("Crisis Level: %.1f/10 (CRITICAL - situation deteriorating rapidly)", perceived_crisis))
    } else if (paranoia < 0.3) {
      perceived_crisis <- max(1, perceived_crisis * 0.85)  # Low paranoia underestimates
      parts <- c(parts, sprintf("Crisis Level: %.1f/10 (manageable)", perceived_crisis))
    } else {
      parts <- c(parts, sprintf("Crisis Level: %.1f/10", state$crisis_level))
    }
  }

  # Military balance - worldview affects interpretation, but always show exact value
  if (!is.null(state$military_balance)) {
    mb <- state$military_balance
    # Always include the numeric value (negative = favors Novaris, positive = favors Tethys)
    numeric_tag <- sprintf("[exact: %+.2f]", mb)
    if (!is.null(worldview)) {
      if (worldview == "realist") {
        if (mb < -0.2) {
          parts <- c(parts, sprintf("Military Balance: DANGEROUS - enemy has significant advantage %s", numeric_tag))
        } else if (mb < 0) {
          parts <- c(parts, sprintf("Military Balance: Unfavorable - requires immediate attention %s", numeric_tag))
        } else if (mb > 0.2) {
          parts <- c(parts, sprintf("Military Balance: Strong position - maintain pressure %s", numeric_tag))
        } else {
          parts <- c(parts, sprintf("Military Balance: Contested - window of opportunity %s", numeric_tag))
        }
      } else if (worldview == "liberal_institutionalist") {
        if (mb < -0.3) {
          parts <- c(parts, sprintf("Military Balance: Favors adversary, but diplomatic solutions remain viable %s", numeric_tag))
        } else if (mb > 0.1) {
          parts <- c(parts, sprintf("Military Balance: Favorable - negotiate from strength %s", numeric_tag))
        } else {
          parts <- c(parts, sprintf("Military Balance: Balanced - ideal conditions for talks %s", numeric_tag))
        }
      } else if (worldview == "nationalist_populist") {
        if (mb < 0) {
          parts <- c(parts, sprintf("Military Balance: ENEMY ADVANCING - national survival at stake %s", numeric_tag))
        } else {
          parts <- c(parts, sprintf("Military Balance: Our strength prevails - press the advantage %s", numeric_tag))
        }
      } else {
        parts <- c(parts, sprintf("Military Balance: %s %s",
          if (mb < -0.3) "Heavily favors major power"
          else if (mb < -0.1) "Favors major power"
          else if (mb > 0.1) "Favors smaller power"
          else "Roughly equal",
          numeric_tag))
      }
    } else {
      parts <- c(parts, sprintf("Military Balance: %s %s",
        if (mb < -0.3) "Heavily favors major power"
        else if (mb < -0.1) "Favors major power"
        else if (mb > 0.1) "Favors smaller power"
        else "Roughly equal",
        numeric_tag))
    }
  }

  # Sanctions - worldview affects interpretation, but always show exact value
  if (!is.null(state$sanctions_level)) {
    sl <- state$sanctions_level
    numeric_tag <- sprintf("[exact: %.0f%%]", sl * 100)
    if (sl > 0) {
      if (!is.null(worldview) && worldview == "pragmatic_technocrat") {
        parts <- c(parts, sprintf("Economic Sanctions: %.0f%% severity (estimated GDP impact: -%.1f%%)",
                                 sl * 100, sl * 20))
      } else if (sl > 0.5) {
        parts <- c(parts, sprintf("Economic Sanctions: Severe %s", numeric_tag))
      } else if (sl > 0.2) {
        parts <- c(parts, sprintf("Economic Sanctions: Moderate %s", numeric_tag))
      } else {
        parts <- c(parts, sprintf("Economic Sanctions: Limited %s", numeric_tag))
      }
    } else {
      parts <- c(parts, "Economic Sanctions: None [exact: 0%]")
    }
  }

  # Territory - always show exact percentage
  if (!is.null(state$territory_controlled)) {
    tc <- state$territory_controlled
    if (paranoia > 0.7 && tc > 0.1) {
      parts <- c(parts, sprintf("Territory Under Enemy Control: %.1f%% - UNACCEPTABLE losses mounting",
                               tc * 100))
    } else {
      parts <- c(parts, sprintf("Territory Under Enemy Control: %.1f%%", tc * 100))
    }
  }

  # International support - was previously missing entirely
  if (!is.null(state$international_support)) {
    is_val <- state$international_support
    if (!is.null(worldview)) {
      if (worldview == "liberal_institutionalist") {
        if (is_val > 0.7) {
          parts <- c(parts, sprintf("International Support: Strong coalition backing (%.0f%%) - multilateral framework holds", is_val * 100))
        } else if (is_val > 0.4) {
          parts <- c(parts, sprintf("International Support: Moderate (%.0f%%) - coalition needs strengthening", is_val * 100))
        } else {
          parts <- c(parts, sprintf("International Support: Weak (%.0f%%) - URGENT need for diplomatic outreach", is_val * 100))
        }
      } else if (worldview == "realist") {
        if (is_val > 0.7) {
          parts <- c(parts, sprintf("International Support: %.0f%% - useful but ultimately unreliable", is_val * 100))
        } else {
          parts <- c(parts, sprintf("International Support: %.0f%% - cannot depend on external actors", is_val * 100))
        }
      } else {
        parts <- c(parts, sprintf("International Support: %.0f%%", is_val * 100))
      }
    } else {
      parts <- c(parts, sprintf("International Support: %.0f%%", is_val * 100))
    }
  }

  if (!is.null(state$nuclear_used) && state$nuclear_used) {
    parts <- c(parts, "*** NUCLEAR WEAPONS HAVE BEEN USED ***")
  }

  if (length(parts) == 0) {
    return("Initial assessment phase")
  }

  return(paste(parts, collapse = "\n"))
}

#' Format recent events for agent
#'
#' @param events List of recent events
#' @return Formatted string
format_recent_events <- function(events) {
  if (is.null(events) || length(events) == 0) {
    return("No major events this period")
  }

  event_strings <- sapply(events, function(e) {
    sprintf("- %s: %s", e$name, e$description)
  })

  return(paste(event_strings, collapse = "\n"))
}

#' Parse action decision from LLM response
#'
#' @param response LLM response text
#' @return List with action, target, reasoning, expected_outcome
parse_action_decision <- function(response) {
  # Extract ACTION
  action <- NA
  action_match <- regexpr("ACTION:\\s*([a-z_]+)", response, perl = TRUE, ignore.case = TRUE)
  if (action_match > 0) {
    action_text <- regmatches(response, action_match)
    action <- tolower(trimws(sub("ACTION:\\s*", "", action_text, ignore.case = TRUE)))
  }

  # Fallback: if no action found, try to extract any valid action name from response
  if (is.na(action) || action == "none") {
    # List of all valid action names
    valid_actions <- c(
      "diplomatic_visit", "peace_talks", "trade_negotiation", "cultural_exchange",
      "humanitarian_aid", "mediation_offer", "intelligence_gathering", "surveillance_operation",
      "counterintelligence", "spread_disinformation", "propaganda_campaign",
      "trade_agreement", "economic_sanctions", "financial_aid", "resource_embargo",
      "currency_manipulation", "cyber_theft", "military_buildup", "naval_deployment",
      "air_patrols", "troop_movements", "joint_exercises", "arms_development",
      "sabotage", "assassination_attempt", "regime_destabilization", "proxy_support",
      "false_flag_operation", "cyber_attack", "border_incursion", "limited_strike",
      "full_scale_attack", "occupation", "blockade", "siege_warfare",
      "nuclear_development", "chemical_weapons", "biological_program",
      "tactical_nuclear_use", "strategic_nuclear_strike"
    )

    # Search for any valid action name in the response
    for (valid_action in valid_actions) {
      if (grepl(valid_action, response, ignore.case = TRUE)) {
        action <- valid_action
        break
      }
    }
  }

  # If still "none" after fallback, set to NA
  if (!is.na(action) && action == "none") {
    action <- NA
  }

  # Extract TARGET
  target <- NA
  target_match <- regexpr("TARGET:\\s*([^\n]+)", response, perl = TRUE, ignore.case = TRUE)
  if (target_match > 0) {
    target_text <- regmatches(response, target_match)
    target <- trimws(sub("TARGET:\\s*", "", target_text, ignore.case = TRUE))
    if (tolower(target) %in% c("none", "n/a", "na", "null")) {
      target <- NA
    }
  }

  # Extract REASONING
  reasoning <- ""
  reasoning_match <- regexpr("REASONING:\\s*([^\n]+(?:\n(?!\\w+:)[^\n]+)*)",
                            response, perl = TRUE, ignore.case = TRUE)
  if (reasoning_match > 0) {
    reasoning_text <- regmatches(response, reasoning_match)
    reasoning <- trimws(sub("REASONING:\\s*", "", reasoning_text, ignore.case = TRUE))
    # Clean up any XML tags that might have leaked in
    reasoning <- gsub("</decision>|</reasoning>|</action>", "", reasoning, ignore.case = TRUE)
    reasoning <- trimws(reasoning)
  }

  # Extract EXPECTED_OUTCOME
  expected_outcome <- ""
  outcome_match <- regexpr("EXPECTED_OUTCOME:\\s*([^\n]+(?:\n(?!\\w+:)[^\n]+)*)",
                          response, perl = TRUE, ignore.case = TRUE)
  if (outcome_match > 0) {
    outcome_text <- regmatches(response, outcome_match)
    expected_outcome <- trimws(sub("EXPECTED_OUTCOME:\\s*", "", outcome_text, ignore.case = TRUE))
    # Clean up any XML tags that might have leaked in
    expected_outcome <- gsub("</decision>|</reasoning>|</expected_outcome>", "", expected_outcome, ignore.case = TRUE)
    expected_outcome <- trimws(expected_outcome)
  }

  return(list(
    action = action,
    target = target,
    reasoning = reasoning,
    expected_outcome = expected_outcome,
    raw_response = response
  ))
}

#' Have agent make action decision
#'
#' @param agent Agent object
#' @param context Current context
#' @param available_actions Available actions
#' @param other_agents Other agents
#' @param api_key API key
#' @param coordination Coordination input from pre-action discussion
#' @param state Full simulation state (for action history)
#' @return List with decision
agent_decide_action <- function(agent, context, available_actions, other_agents, api_key, coordination = NULL, state = NULL) {
  # Generate base prompt (now with state for action history - Fix A)
  prompt <- generate_action_decision_prompt(agent, context, available_actions, other_agents, state)

  # Add coordination input if available
  if (!is.null(coordination) && !is.null(coordination$messages)) {
    coordination_summary <- "\n\n=== YOUR TEAM'S INPUT FROM PRE-ACTION COORDINATION ===\n"
    coordination_summary <- paste0(coordination_summary,
                                   "Your colleagues have shared their perspectives:\n\n")

    for (msg in coordination$messages) {
      # Only include messages from round 2 (final positions) to keep it concise
      if (msg$round == 2) {
        coordination_summary <- paste0(coordination_summary,
                                       sprintf("%s (%s, worldview: %s, stance: %.0f%% hawk):\n%s\n\n",
                                              msg$sender_name,
                                              msg$sender_role,
                                              msg$worldview,
                                              msg$hawk_dove * 100,
                                              msg$content))
      }
    }

    coordination_summary <- paste0(coordination_summary,
                                   "Consider these perspectives as you make your final decision, but the choice is ultimately yours to make.\n")
    coordination_summary <- paste0(coordination_summary,
                                   "=== END COORDINATION INPUT ===\n\n")

    # Insert coordination summary before the action list
    prompt <- paste0(prompt, coordination_summary)
  }

  system_prompt <- sprintf("You are a strategic decision-maker in a geopolitical simulation.
Your task is to choose one concrete action based on your role, worldview, and the current situation.
You must be decisive and select the action that best serves your faction's interests given your worldview.

CRITICAL: You MUST respond in the exact format specified in the prompt. Do not provide a free-form response.
Your response MUST include these four lines with these exact labels:
ACTION: [action_name]
TARGET: [target or none]
REASONING: [your reasoning]
EXPECTED_OUTCOME: [expected outcome]

Do NOT write anything else. Do NOT provide explanations before or after this format.")

  # Call LLM
  cat(sprintf("    Calling LLM for %s decision...\n", agent$name))
  response <- call_llm(system_prompt, prompt, AGENT_MODEL, api_key)

  # Debug: show first 200 chars of response
  cat(sprintf("    LLM response preview: %s...\n", substr(response, 1, 200)))

  # Parse decision
  decision <- parse_action_decision(response)

  # Debug: show parsed action
  if (is.na(decision$action)) {
    cat(sprintf("    WARNING: Failed to parse action from response\n"))
    cat(sprintf("    Full response:\n%s\n", response))
    cat(sprintf("    HINT: Response should start with 'ACTION: [action_name]'\n"))
  } else {
    cat(sprintf("    ✓ Parsed action: %s", decision$action))
    if (!is.na(decision$target)) {
      cat(sprintf(" → %s", decision$target))
    }
    cat("\n")
  }

  decision$agent_name <- agent$name
  decision$agent_id <- agent$agent_id
  decision$agent_faction <- agent$faction
  decision$agent_role <- agent$role
  decision$timestamp <- Sys.time()

  return(decision)
}

#' Execute agent's decided action
#'
#' @param decision Decision object from agent_decide_action
#' @param agents All agents
#' @param state Current state
#' @return List with execution result and updated state
execute_agent_decision <- function(decision, agents, state) {
  # Find the agent
  agent <- NULL
  for (a in agents) {
    if (!is.null(a$agent_id) && a$agent_id == decision$agent_id) {
      agent <- a
      break
    }
  }

  if (is.null(agent)) {
    cat(sprintf("  ERROR: Agent not found for agent_id='%s'\n", decision$agent_id))
    return(list(
      result = list(
        success = FALSE,
        effects = list(error = "Agent not found")
      ),
      state = state
    ))
  }

  # Find target agent if specified
  # Support multiple comma-separated targets (e.g., "Meridian,Aurelia")
  target_agent <- NULL
  if (!is.na(decision$target) && decision$target != "none") {
    # Split target by comma to handle multiple targets
    target_names <- trimws(strsplit(decision$target, ",")[[1]])

    # Try to match any of the target names
    for (tname in target_names) {
      for (a in agents) {
        if (!is.null(a$country) && grepl(tname, a$country, ignore.case = TRUE)) {
          target_agent <- a
          break
        }
        if (!is.null(a$name) && grepl(tname, a$name, ignore.case = TRUE)) {
          target_agent <- a
          break
        }
      }
      # If we found a match, stop searching
      if (!is.null(target_agent)) break
    }
  }

  # Execute the action
  cat(sprintf("  %s (%s) executing: %s\n",
              agent$name, agent$faction, decision$action))

  execution_result <- execute_action(decision$action, agent, target_agent, state)

  # Add decision context to result
  execution_result$result$decision_reasoning <- decision$reasoning
  execution_result$result$expected_outcome <- decision$expected_outcome

  return(execution_result)
}

#' Run action decision phase for all agents
#'
#' @param agents All agents
#' @param period Current period
#' @param state Current state
#' @param api_key API key
#' @return List with all decisions and updated state
run_action_decision_phase <- function(agents, period, state, api_key) {
  cat(sprintf("\n=== PERIOD %d: COORDINATION & ACTION EXECUTION ===\n", period))

  # Prepare context
  context <- list(
    period = period,
    scenario_state = state$scenario_state,
    recent_events = if (!is.null(state$events_history[[period]])) {
      state$events_history[[period]]
    } else {
      list()
    },
    faction_capabilities = state$faction_capabilities
  )

  decisions <- list()
  execution_results <- list()
  coordination_records <- list()  # NEW: Track coordination

  # Each faction decides actions based on intra-faction coordination
  # External actors now independent: meridian, valkoria, aurelia, international_org
  factions <- c("major_power", "small_power", "meridian", "valkoria", "aurelia", "international_org")

  for (faction in factions) {
    faction_agents <- Filter(function(a) a$faction == faction, agents)

    if (length(faction_agents) == 0) next

    cat(sprintf("\n--- %s Faction ---\n",
                toupper(gsub("_", " ", faction))))

    # Pre-action coordination - agents discuss and recommend
    coordination <- NULL
    if (length(faction_agents) >= 2) {
      cat("  [Step 2] Pre-action coordination...\n")
      # Source interaction_engine if not already loaded
      if (!exists("run_pre_action_coordination")) {
        source("src/interaction_engine.R")
      }
      coordination <- run_pre_action_coordination(
        faction,
        faction_agents,
        context,
        api_key
      )
      # Save coordination record
      coordination_records[[faction]] <- coordination
    }

    # Decision maker chooses action based on coordination
    cat("  [Step 3] Action decision & execution...\n")

    # NEW: Multi-action system (v3.8) - check if enabled and faction qualifies
    domain_proposals <- NULL
    if (exists("ENABLE_MULTI_ACTION_SYSTEM") && ENABLE_MULTI_ACTION_SYSTEM) {
      # Load multi-action system if needed
      if (!exists("generate_domain_proposals")) {
        source("src/multi_action_system.R")
        source("src/multi_action_effects.R")
      }

      # Try multi-action system for factions with 3+ agents and domain structure
      # v3.8.2: Pass state for discussion memory
      domain_proposals <- generate_domain_proposals(faction, faction_agents, coordination, context, api_key, state)
    }

    if (!is.null(domain_proposals)) {
      # Multi-action system: domain experts propose, president approves/vetoes
      cat("  → Using multi-action proposal system\n")

      # v3.8.2: Pass state for discussion memory
      approvals <- presidential_approval(domain_proposals, faction, faction_agents, context, api_key, state)
      approved_actions <- extract_approved_actions(approvals)
      all_actions_with_status <- extract_all_actions_with_status(domain_proposals, approvals)

      # Get decision maker for tracking purposes
      gov_agents <- Filter(function(a) a$role == "government", faction_agents)
      decision_maker <- if(length(gov_agents) > 0) gov_agents[[1]] else faction_agents[[1]]

      # Get faction display name
      faction_name <- if(faction == "major_power") {
        "Novaris"
      } else if (faction == "small_power") {
        "Tethys"
      } else {
        faction
      }

      # Store multi-action decision record (include all actions, not just approved)
      decisions[[faction]] <- list(
        decision_maker = decision_maker$name,
        decision_maker_role = decision_maker$role,
        approved_actions = approved_actions,
        all_actions_with_status = all_actions_with_status,
        proposals = domain_proposals,
        approvals = approvals,
        timestamp = Sys.time(),
        faction_name = faction_name
      )

      # Execute all approved actions with multi-action effect resolution
      if (length(approved_actions) > 0) {
        # Execute with multi-action effect resolution
        state <- resolve_multiple_action_effects(approved_actions, decision_maker, state)

        # Create execution results record with INDIVIDUAL action results
        # state$last_action_results contains the individual execution outcomes
        individual_results <- if (!is.null(state$last_action_results)) {
          state$last_action_results
        } else {
          list()
        }

        # Calculate overall success (TRUE only if all actions succeeded)
        all_succeeded <- if (length(individual_results) > 0) {
          all(sapply(individual_results, function(r) isTRUE(r$success)))
        } else {
          FALSE
        }

        # Count successes and failures
        success_count <- sum(sapply(individual_results, function(r) isTRUE(r$success)))
        failure_count <- length(individual_results) - success_count

        execution_results[[faction]] <- list(
          actions = sapply(approved_actions, function(a) a$action),
          success = all_succeeded,
          multi_action = TRUE,
          individual_results = individual_results,
          success_count = success_count,
          failure_count = failure_count
        )

        cat(sprintf("    → Execution complete: %d/%d actions succeeded\n",
                   success_count, length(individual_results)))
      } else {
        cat("  → No actions approved\n")
        execution_results[[faction]] <- list(success = FALSE, message = "All proposals vetoed")
      }

      # Skip old single-action system
      next
    }

    # FALLBACK: Traditional single-action system for external actors / small factions
    cat("  → Using traditional single-action system\n")

    # FACTION DYNAMICS: Who decides can change based on crisis level
    decision_maker <- NULL
    crisis_level <- if (!is.null(context$scenario_state$crisis_level)) {
      context$scenario_state$crisis_level
    } else {
      5  # Default moderate
    }

    # Find available agents by role
    gov_agents <- Filter(function(a) a$role == "government", faction_agents)
    mil_agents <- Filter(function(a) a$role == "military", faction_agents)
    intel_agents <- Filter(function(a) a$role == "intelligence", faction_agents)

    # IN HIGH CRISIS (>=8), military has more influence
    # Hawks may override civilian leadership
    if (crisis_level >= 8 && length(mil_agents) > 0) {
      # Check if military is significantly more hawkish
      mil_hawk <- mil_agents[[1]]$hawk_dove
      gov_hawk <- if (length(gov_agents) > 0) gov_agents[[1]]$hawk_dove else 0.5

      # Military overrides if: much more hawkish AND random chance based on crisis
      override_prob <- (crisis_level - 7) * 0.15 * (mil_hawk - gov_hawk)
      if (runif(1) < override_prob && mil_hawk > gov_hawk + 0.15) {
        decision_maker <- mil_agents[[1]]
        cat(sprintf("  → [CRISIS OVERRIDE] Military takes lead in decision-making\n"))
      }
    }

    # Normal priority: government > military > intelligence > others
    if (is.null(decision_maker)) {
      if (length(gov_agents) > 0) {
        decision_maker <- gov_agents[[1]]
      } else if (length(mil_agents) > 0) {
        decision_maker <- mil_agents[[1]]
      } else if (length(intel_agents) > 0) {
        decision_maker <- intel_agents[[1]]
      } else {
        decision_maker <- faction_agents[[1]]
      }
    }

    cat(sprintf("  → Decision maker: %s\n", decision_maker$name))

    # Agent decides action (now with coordination input and state for history - Fix A)
    decision <- agent_decide_action(
      decision_maker,
      context,
      available_actions = list(),  # All actions available
      other_agents = agents,
      api_key,
      coordination = coordination,
      state = state  # Pass state for action history (Fix A)
    )

    decisions[[faction]] <- decision

    # Execute the action (only if valid)
    if (!is.na(decision$action) && decision$action != "") {
      execution <- execute_agent_decision(decision, agents, state)
      execution_results[[faction]] <- execution$result
      state <- execution$state  # Update state with consequences

      # Print result
      if (execution$result$success) {
        cat(sprintf("  ✓ Action executed: %s\n", decision$action))
        if (!is.null(execution$result$effects$message)) {
          cat(sprintf("  → %s\n", execution$result$effects$message))
        }
      } else {
        cat(sprintf("  ✗ Action failed: %s\n", decision$action))
        if (!is.null(execution$result$effects$message)) {
          cat(sprintf("  → %s\n", execution$result$effects$message))
        }
        if (!is.null(execution$result$effects$error)) {
          cat(sprintf("  → Error: %s\n", execution$result$effects$error))
        }
        # Debug: show full result structure
        cat(sprintf("  → DEBUG: success=%s, has_effects=%s\n",
                   execution$result$success,
                   !is.null(execution$result$effects)))
      }
    } else {
      cat(sprintf("  ✗ No valid action parsed - skipping execution\n"))
      execution_results[[faction]] <- list(
        action = NA,
        success = FALSE,
        effects = list(error = "Failed to parse action from LLM response")
      )
    }
  }

  # Save decisions, results, and coordination records
  state$action_decisions[[period]] <- decisions
  state$action_results[[period]] <- execution_results
  state$pre_action_coordination[[period]] <- coordination_records

  # Save to CSV files for analysis
  cat("\n  Saving interactions to CSV...\n")
  tryCatch({
    # Save coordination records
    if (length(coordination_records) > 0) {
      save_coordination_to_csv(coordination_records, period)
    }

    # Save domain expert proposals
    if (length(decisions) > 0) {
      save_proposals_to_csv(decisions, period)
    }

    # Save action decisions and results
    if (length(decisions) > 0) {
      save_actions_to_csv(decisions, execution_results, period)
    }
  }, error = function(e) {
    cat(sprintf("  Warning: Could not save to CSV: %s\n", e$message))
  })

  return(state)
}
