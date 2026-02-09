# Enhanced Action Space with Cognitive Frameworks
# Simplified action system with worldviews, deception, and information asymmetry

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

#' Create agent with cognitive framework
#'
#' @param name Agent name
#' @param country Country name
#' @param worldview Worldview type (key from WORLDVIEWS)
#' @param deception_capacity Ability to deceive (0-1)
#' @param deception_willingness Willingness to use deception (0-1)
#' @param information_access Quality of information (0-1)
#' @param analytical_capability Ability to process information (0-1)
#' @param cognitive_rationality How rational/logical vs impulsive (0-1)
#' @param paranoia Tendency to see threats and conspiracies (0-1)
#' @param behavioral_consistency How predictable behavior is (0-1)
#' @param emotional_volatility How much emotions override logic (0-1)
#' @return Agent object with cognitive framework
create_cognitive_agent <- function(name, country, worldview,
                                  deception_capacity = 0.5,
                                  deception_willingness = 0.5,
                                  information_access = 0.7,
                                  analytical_capability = 0.7,
                                  cognitive_rationality = 0.7,
                                  paranoia = 0.5,
                                  behavioral_consistency = 0.7,
                                  emotional_volatility = 0.5) {

  wv <- WORLDVIEWS[[worldview]]

  agent <- list(
    name = name,
    country = country,
    worldview = worldview,
    worldview_details = wv,

    # Deception capabilities
    deception = list(
      capacity = deception_capacity,  # Technical ability to deceive
      willingness = deception_willingness,  # Moral/strategic willingness
      success_rate = deception_capacity * 0.8,  # Historical success
      detected_count = 0  # Times caught deceiving
    ),

    # Information asymmetry
    information = list(
      access = information_access,  # Quality of intelligence gathering
      accuracy = analytical_capability,  # Ability to interpret correctly
      known_to_others = 0.5,  # How much others know about this agent
      uncertainty = 1 - (information_access * analytical_capability)
    ),

    # Rationality components (NEW)
    rationality = list(
      cognitive = cognitive_rationality,      # Logical vs impulsive
      paranoia = paranoia,                    # Sees threats everywhere
      consistency = behavioral_consistency,    # Predictable vs erratic
      volatility = emotional_volatility       # Emotional override of logic
    ),

    # Cognitive biases from worldview
    cognitive_biases = wv$biases,
    decision_style = wv$decision_style,
    information_processing = wv$information_processing,
    base_trust = wv$trust_baseline,

    # Dynamic state
    trust_levels = list(),  # Trust in other agents (updated over time)
    perceived_threats = list(),  # Perceived threat from each agent
    action_history = list(),  # Past actions taken
    deception_history = list(),  # Past deceptions attempted
    information_received = list()  # Information gathered over time
  )

  class(agent) <- c("cognitive_agent", "list")
  return(agent)
}

#' Determine if agent attempts deception in an action
#'
#' @param agent Agent object
#' @param action_type Type of action being taken
#' @param target Target of the action
#' @param context Current situation context
#' @return List with deception decision and details
attempt_deception <- function(agent, action_type, target, context) {
  # Base probability from worldview
  base_prob <- agent$worldview_details$deception_tendency

  # Convert tendency to probability
  tendency_prob <- switch(base_prob,
    "very_high" = 0.8,
    "high" = 0.6,
    "moderate" = 0.4,
    "situational" = 0.3,
    "low" = 0.2,
    0.3  # default
  )

  # Modify by agent's willingness
  attempt_prob <- tendency_prob * agent$deception$willingness

  # Increase if desperate or under threat
  if (!is.null(context$under_threat) && context$under_threat) {
    attempt_prob <- attempt_prob * 1.5
  }

  # Decrease if recently caught
  if (agent$deception$detected_count > 0) {
    attempt_prob <- attempt_prob * (0.8 ^ agent$deception$detected_count)
  }

  attempt <- runif(1) < attempt_prob

  if (attempt) {
    # Success probability
    success_prob <- agent$deception$capacity

    # Modified by target's analytical capability
    if (!is.null(target)) {
      success_prob <- success_prob * (1 - target$information$accuracy * 0.5)
    }

    success <- runif(1) < success_prob

    return(list(
      attempted = TRUE,
      successful = success,
      probability = success_prob,
      type = ifelse(success, "undetected", "detected")
    ))
  }

  return(list(attempted = FALSE))
}

#' Process information through agent's worldview filter
#'
#' @param agent Agent object
#' @param information Raw information
#' @param source Source of information
#' @return Processed/interpreted information
filter_information <- function(agent, information, source) {
  # Information quality depends on access level
  info_quality <- agent$information$access

  # Add noise based on uncertainty
  noise_level <- agent$information$uncertainty

  # Apply worldview biases
  processed <- information

  if (agent$information_processing == "threat_focused") {
    # Realists amplify threats
    if (!is.null(information$threat_level)) {
      processed$threat_level <- min(1.0, information$threat_level * 1.3)
    }
  } else if (agent$information_processing == "opportunity_focused") {
    # Liberals see more opportunities for cooperation
    if (!is.null(information$cooperation_potential)) {
      processed$cooperation_potential <- min(1.0, information$cooperation_potential * 1.2)
    }
  } else if (agent$information_processing == "identity_focused") {
    # Nationalists weight in-group/out-group heavily
    if (!is.null(information$cultural_similarity)) {
      processed$salience_multiplier <- information$cultural_similarity
    }
  }

  # Add uncertainty
  if (noise_level > 0.3) {
    processed$confidence <- "low"
  } else if (noise_level > 0.1) {
    processed$confidence <- "medium"
  } else {
    processed$confidence <- "high"
  }

  # Track information received
  processed$source <- source
  processed$timestamp <- Sys.time()
  processed$filtered_by_worldview <- agent$worldview

  return(processed)
}

#' Update agent's trust in another agent
#'
#' @param agent Agent whose trust is being updated
#' @param target Agent being evaluated
#' @param interaction Type of interaction that occurred
#' @param deception_detected Whether deception was detected
#' @return Updated agent object
update_trust <- function(agent, target, interaction, deception_detected = FALSE) {
  target_name <- target$name

  # Initialize trust if first interaction
  if (is.null(agent$trust_levels[[target_name]])) {
    agent$trust_levels[[target_name]] <- agent$base_trust
  }

  current_trust <- agent$trust_levels[[target_name]]

  # Deception severely damages trust
  if (deception_detected) {
    new_trust <- current_trust * 0.3  # Major trust loss
  } else {
    # Positive interactions build trust slowly
    if (interaction %in% c("diplomatic_visit", "trade_agreement", "peace_talks")) {
      new_trust <- current_trust + (1 - current_trust) * 0.1
    } else if (interaction %in% c("military_buildup", "sanctions")) {
      new_trust <- current_trust * 0.9  # Slight decrease
    } else if (interaction %in% c("border_incursion", "cyber_attack")) {
      new_trust <- current_trust * 0.5  # Major decrease
    } else {
      new_trust <- current_trust  # No change
    }
  }

  agent$trust_levels[[target_name]] <- max(0, min(1, new_trust))

  return(agent)
}

#' Generate action with cognitive framework
#'
#' @param agent Agent making decision
#' @param situation Current situation
#' @param available_actions Actions available
#' @return List with action, reasoning, and deception info
generate_cognitive_action <- function(agent, situation, available_actions) {
  # Filter information through worldview
  processed_situation <- filter_information(agent, situation, "situation_report")

  # Decision style influences action selection
  if (agent$decision_style == "rational_calculator") {
    reasoning <- "Calculating optimal outcome based on power dynamics"
  } else if (agent$decision_style == "norm_follower") {
    reasoning <- "Considering international norms and institutional frameworks"
  } else if (agent$decision_style == "emotion_driven") {
    reasoning <- "Responding to perceived threats to national identity"
  } else if (agent$decision_style == "opportunistic") {
    reasoning <- "Seeking opportunities to reshape the balance of power"
  } else if (agent$decision_style == "analytical") {
    reasoning <- "Analyzing data to optimize outcomes"
  } else {
    reasoning <- "Evaluating options based on relationships and shared values"
  }

  # Select action (simplified - would integrate with LLM in full implementation)
  action_category <- sample(names(ACTION_TYPES), 1)
  action <- sample(ACTION_TYPES[[action_category]], 1)

  # Check for deception
  deception_info <- attempt_deception(
    agent,
    action,
    NULL,  # Would specify target
    processed_situation
  )

  return(list(
    action = action,
    category = action_category,
    reasoning = reasoning,
    worldview_influence = agent$worldview,
    deception = deception_info,
    information_confidence = processed_situation$confidence
  ))
}

#' Get agent description for prompt
#'
#' @param agent Agent object
#' @return Formatted description string
get_agent_description <- function(agent) {
  sprintf(
    "%s (%s) - Worldview: %s
Decision Style: %s
Information Processing: %s
Deception Tendency: %s
Trust Baseline: %.2f
Information Access: %.1f%%
Analytical Capability: %.1f%%

Cognitive Biases:
%s",
    agent$name,
    agent$country,
    agent$worldview_details$name,
    agent$decision_style,
    agent$information_processing,
    agent$worldview_details$deception_tendency,
    agent$base_trust,
    agent$information$access * 100,
    agent$information$accuracy * 100,
    paste("-", agent$cognitive_biases, collapse = "\n")
  )
}
