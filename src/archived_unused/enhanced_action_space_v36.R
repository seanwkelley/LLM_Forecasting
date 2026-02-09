# Enhanced Action Space with Cognitive Frameworks
# v3.6 - Added Strategic Direction Mappings for Two-Stage Decision Process

# Core action categories (simplified from paper's scoring)
ACTION_TYPES <- list(
  diplomatic = c(
    "diplomatic_visit", "peace_talks", "trade_negotiation",
    "cultural_exchange", "humanitarian_aid", "mediation_offer"
  ),
  intelligence = c(
    "share_intelligence", "intelligence_gathering", "surveillance_operation",
    "counterintelligence", "spread_disinformation", "propaganda_campaign"
  ),
  economic = c(
    "trade_agreement", "economic_sanctions", "financial_aid",
    "resource_embargo", "currency_manipulation", "cyber_theft"
  ),
  military_posture = c(
    "military_buildup", "naval_deployment", "air_patrols",
    "troop_movements", "joint_exercises", "arms_development"
  ),
  covert_operations = c(
    "sabotage", "assassination_attempt", "regime_destabilization",
    "proxy_support", "false_flag_operation", "cyber_attack"
  ),
  open_conflict = c(
    "border_incursion", "limited_strike", "full_scale_attack",
    "occupation", "blockade", "siege_warfare"
  ),
  wmd = c(
    "nuclear_development", "chemical_weapons", "biological_program",
    "tactical_nuclear_use", "strategic_nuclear_strike"
  )
)

# ============================================================================
# STRATEGIC DIRECTION CATEGORIES (NEW v3.6)
# Maps actions to high-level strategic approaches for cognitive load reduction
# ============================================================================

STRATEGIC_DIRECTIONS <- list(
  DIPLOMATIC = list(
    code = "A",
    label = "A. DIPLOMATIC PATH",
    description = "Pursue negotiation, de-escalation, relationship building",
    focus = "Reduce tensions through dialogue and cooperation",
    actions = c("diplomatic_visit", "peace_talks", "trade_negotiation",
                "cultural_exchange", "humanitarian_aid", "mediation_offer"),
    examples = c("peace_talks", "mediation_offer", "humanitarian_aid")
  ),

  ECONOMIC = list(
    code = "B",
    label = "B. ECONOMIC PRESSURE",
    description = "Financial warfare, sanctions, trade manipulation",
    focus = "Use economic tools to punish or support",
    actions = c("trade_agreement", "economic_sanctions", "financial_aid",
                "resource_embargo", "currency_manipulation", "cyber_theft"),
    examples = c("economic_sanctions", "resource_embargo", "financial_aid")
  ),

  MILITARY_POSTURE = list(
    code = "C",
    label = "C. MILITARY POSTURE",
    description = "Build capabilities, signal resolve, prepare for conflict",
    focus = "Strengthen military position without open combat",
    actions = c("military_buildup", "naval_deployment", "air_patrols",
                "troop_movements", "joint_exercises", "arms_development"),
    examples = c("military_buildup", "troop_movements", "joint_exercises")
  ),

  COVERT = list(
    code = "D",
    label = "D. COVERT OPERATIONS",
    description = "Deniable actions, destabilization, intelligence",
    focus = "Achieve objectives through clandestine means",
    actions = c("sabotage", "assassination_attempt", "regime_destabilization",
                "proxy_support", "false_flag_operation", "cyber_attack",
                "intelligence_gathering", "surveillance_operation",
                "counterintelligence", "spread_disinformation", "propaganda_campaign"),
    examples = c("cyber_attack", "sabotage", "regime_destabilization")
  ),

  OPEN_CONFLICT = list(
    code = "E",
    label = "E. OPEN CONFLICT",
    description = "Direct kinetic action, immediate military force",
    focus = "Use open military force to achieve objectives",
    actions = c("border_incursion", "limited_strike", "full_scale_attack",
                "occupation", "blockade", "siege_warfare"),
    examples = c("limited_strike", "full_scale_attack", "occupation")
  ),

  WMD = list(
    code = "F",
    label = "F. WMD/EXTREME ESCALATION",
    description = "Nuclear/chemical/biological options",
    focus = "Ultimate escalation - fundamentally changes conflict",
    actions = c("nuclear_development", "chemical_weapons", "biological_program",
                "tactical_nuclear_use", "strategic_nuclear_strike"),
    examples = c("nuclear_development", "tactical_nuclear_use")
  )
)

#' Get strategic direction for an action
#'
#' @param action_name Name of the action
#' @return Strategic direction category name (e.g., "DIPLOMATIC")
get_action_strategic_direction <- function(action_name) {
  for (direction_name in names(STRATEGIC_DIRECTIONS)) {
    if (action_name %in% STRATEGIC_DIRECTIONS[[direction_name]]$actions) {
      return(direction_name)
    }
  }
  return("UNKNOWN")
}

#' Format strategic directions for agent prompt
#'
#' @param context Current simulation context (optional, for future context-sensitive filtering)
#' @return Formatted string describing all strategic options
format_strategic_directions <- function(context = NULL) {
  directions_text <- ""

  for (direction_name in names(STRATEGIC_DIRECTIONS)) {
    dir <- STRATEGIC_DIRECTIONS[[direction_name]]
    directions_text <- paste0(directions_text,
      sprintf("%s - %s\n", dir$label, dir$description),
      sprintf("  Focus: %s\n", dir$focus),
      sprintf("  Examples: %s\n\n", paste(dir$examples, collapse = ", "))
    )
  }

  return(directions_text)
}

#' Format filtered action set for agent prompt
#'
#' @param action_list Vector of action names to include
#' @param state Current simulation state for contextual info
#' @return Formatted string with action details
format_filtered_actions <- function(action_list, state = NULL) {
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

  actions_text <- sprintf("=== AVAILABLE ACTIONS (%d options from your strategic consensus) ===\n\n",
                         length(action_list))

  for (direction in names(by_direction)) {
    if (direction == "UNKNOWN") next

    dir_info <- STRATEGIC_DIRECTIONS[[direction]]
    actions_text <- paste0(actions_text,
      sprintf("--- %s ---\n", dir_info$label))

    for (action in by_direction[[direction]]) {
      # Get action details from ACTION_DEFINITIONS if available
      action_desc <- action  # Fallback to just the name
      if (exists("ACTION_DEFINITIONS") && action %in% names(ACTION_DEFINITIONS)) {
        def <- ACTION_DEFINITIONS[[action]]
        action_desc <- sprintf("%s - %s\n  Cost: $%.1fB | Effects: %s",
                              action,
                              def$description,
                              def$cost_billions,
                              def$primary_effect)
      }
      actions_text <- paste0(actions_text, sprintf("  • %s\n", action_desc))
    }
    actions_text <- paste0(actions_text, "\n")
  }

  return(actions_text)
}

# Continue with existing worldviews and other definitions...
# (Rest of the file remains the same as original enhanced_action_space.R)

# Worldview frameworks - how agents process information and make decisions
WORLDVIEWS <- list(
  realist = list(
    name = "Realist",
    description = "Power-focused, zero-sum worldview. Prioritizes national strength and relative gains.",
    biases = c("overweight military threats", "underweight cooperation benefits",
               "assume worst intentions"),
    decision_style = "rational_calculator",
    information_processing = "threat_focused",
    deception_tendency = "moderate",
    trust_baseline = 0.2
  ),

  liberal_institutionalist = list(
    name = "Liberal Institutionalist",
    description = "Believes in international norms, institutions, and mutual benefit.",
    biases = c("overweight diplomatic solutions", "underweight military necessity",
               "assume good faith initially"),
    decision_style = "norm_follower",
    information_processing = "opportunity_focused",
    deception_tendency = "low",
    trust_baseline = 0.6
  ),

  constructivist = list(
    name = "Constructivist",
    description = "Emphasizes identity, culture, and social relationships between states.",
    biases = c("overweight historical relationships", "underweight material power",
               "assume shared identity matters"),
    decision_style = "relationship_oriented",
    information_processing = "pattern_focused",
    deception_tendency = "low",
    trust_baseline = 0.5
  ),

  nationalist_populist = list(
    name = "Nationalist Populist",
    description = "Prioritizes national sovereignty, cultural preservation, and domestic support.",
    biases = c("overweight sovereignty threats", "underweight international opinion",
               "assume foreigners are adversaries"),
    decision_style = "emotion_driven",
    information_processing = "identity_focused",
    deception_tendency = "high",
    trust_baseline = 0.1
  ),

  revolutionary_revisionist = list(
    name = "Revolutionary Revisionist",
    description = "Seeks to overturn existing international order and reshape power dynamics.",
    biases = c("overweight opportunities for change", "underweight stability costs",
               "assume system is rigged against them"),
    decision_style = "opportunistic",
    information_processing = "advantage_focused",
    deception_tendency = "very_high",
    trust_baseline = 0.05
  ),

  pragmatic_technocrat = list(
    name = "Pragmatic Technocrat",
    description = "Data-driven, efficiency-focused, seeks optimal outcomes based on analysis.",
    biases = c("overweight quantifiable metrics", "underweight intangibles",
               "assume rational actors"),
    decision_style = "analytical",
    information_processing = "data_focused",
    deception_tendency = "situational",
    trust_baseline = 0.4
  )
)

cat("Enhanced Action Space loaded (v3.6 with Strategic Directions)\n")
