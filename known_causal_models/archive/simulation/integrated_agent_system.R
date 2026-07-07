# Integrated Agent System
# Combines intra-country actors with worldviews, deception, and information asymmetry

source("src/enhanced_action_space.R")

#' Map original roles to worldviews and capabilities
ROLE_PROFILES <- list(
  # Military roles - tend toward realism
  military = list(
    default_worldview = "realist",
    deception_capacity = 0.7,  # Military intelligence training
    deception_willingness = 0.5,  # Varies by individual hawk_dove
    information_access = 0.8,  # Good tactical/operational intelligence
    analytical_capability = 0.7,
    typical_biases = c("overweight military solutions", "threat-focused", "zero-sum thinking"),
    # Rationality components
    cognitive_rationality = 0.75,    # Generally rational, trained
    paranoia = 0.60,                 # Professional paranoia
    behavioral_consistency = 0.80,   # Follow doctrine
    emotional_volatility = 0.40      # Disciplined
  ),

  # Government/political roles - varies widely
  government = list(
    default_worldview = "pragmatic_technocrat",
    deception_capacity = 0.6,  # Political experience
    deception_willingness = 0.6,  # Politics involves spin
    information_access = 0.75,  # Access to intelligence briefings
    analytical_capability = 0.65,
    typical_biases = c("domestic politics focus", "short-term thinking", "electoral concerns"),
    # Rationality components
    cognitive_rationality = 0.70,    # Political calculation
    paranoia = 0.50,                 # Moderate
    behavioral_consistency = 0.60,   # Shift with polls
    emotional_volatility = 0.50      # Balanced
  ),

  # Economic advisors - technocratic
  economic = list(
    default_worldview = "pragmatic_technocrat",
    deception_capacity = 0.4,  # Less skilled at deception
    deception_willingness = 0.3,  # Prefer honesty for credibility
    information_access = 0.6,  # Economic data access
    analytical_capability = 0.8,  # Strong analytical skills
    typical_biases = c("overweight economic costs", "quantifiable metrics focus", "efficiency emphasis"),
    # Rationality components
    cognitive_rationality = 0.85,    # Data-driven
    paranoia = 0.30,                 # Optimistic bias
    behavioral_consistency = 0.75,   # Economic models
    emotional_volatility = 0.25      # Calm analysis
  ),

  # Intelligence roles - vary by faction
  intelligence = list(
    default_worldview = "realist",
    deception_capacity = 0.9,  # Expert deceivers
    deception_willingness = 0.7,  # Part of the job
    information_access = 0.95,  # Best intelligence access
    analytical_capability = 0.85,  # Trained analysts
    typical_biases = c("worst-case scenarios", "trust no one", "conspiracy thinking"),
    # Rationality components
    cognitive_rationality = 0.80,    # Analytical
    paranoia = 0.85,                 # Professional paranoia!
    behavioral_consistency = 0.70,   # Methodical
    emotional_volatility = 0.35      # Controlled
  ),

  # Diplomatic roles - institutionalist
  diplomatic = list(
    default_worldview = "liberal_institutionalist",
    deception_capacity = 0.5,  # Some diplomatic doublespeak
    deception_willingness = 0.4,  # Prefer honesty for credibility
    information_access = 0.65,  # International contacts
    analytical_capability = 0.7,
    typical_biases = c("overweight negotiated solutions", "international norms focus", "reputation concerns"),
    # Rationality components
    cognitive_rationality = 0.75,    # Negotiation skills
    paranoia = 0.40,                 # Trusting demeanor
    behavioral_consistency = 0.65,   # Flexible
    emotional_volatility = 0.40      # Measured
  ),

  # Political opposition - varies
  political = list(
    default_worldview = "nationalist_populist",
    deception_capacity = 0.6,  # Political rhetoric
    deception_willingness = 0.7,  # Opposition tactics
    information_access = 0.4,  # Limited access to classified info
    analytical_capability = 0.5,
    typical_biases = c("domestic audience focus", "government criticism", "populist appeals"),
    # Rationality components
    cognitive_rationality = 0.55,    # Populism over logic
    paranoia = 0.65,                 # See plots everywhere
    behavioral_consistency = 0.45,   # Opportunistic
    emotional_volatility = 0.70      # Emotional appeals
  ),

  # Foreign government representatives
  foreign_government = list(
    default_worldview = "pragmatic_technocrat",
    deception_capacity = 0.7,
    deception_willingness = 0.6,
    information_access = 0.7,
    analytical_capability = 0.75,
    typical_biases = c("national interest focus", "alliance management", "credibility concerns"),
    # Rationality components
    cognitive_rationality = 0.75,    # Diplomatic calculation
    paranoia = 0.45,                 # Moderate caution
    behavioral_consistency = 0.70,   # Policy continuity
    emotional_volatility = 0.35      # Professional composure
  ),

  # International organizations
  international_org = list(
    default_worldview = "liberal_institutionalist",
    deception_capacity = 0.2,  # Transparency norms
    deception_willingness = 0.1,  # Institutional credibility
    information_access = 0.5,  # Limited intelligence
    analytical_capability = 0.7,
    typical_biases = c("humanitarian focus", "international law emphasis", "consensus seeking"),
    # Rationality components
    cognitive_rationality = 0.80,    # Bureaucratic
    paranoia = 0.25,                 # Institutional trust
    behavioral_consistency = 0.85,   # Rule-based
    emotional_volatility = 0.20      # Diplomatic calm
  )
)

#' Assign worldview based on role and hawk_dove score
#'
#' @param role Agent role
#' @param hawk_dove Hawk-dove score (0-1)
#' @param faction Faction membership
#' @return Worldview type
assign_worldview <- function(role, hawk_dove, faction) {
  # MAJOR POWER agents - an invading power is more likely realist/nationalist
  if (faction == "major_power") {
    if (role == "military") {
      if (hawk_dove > 0.8) {
        return("nationalist_populist")  # Ultra-hawks
      } else {
        return("realist")  # Military realism - default for aggressors
      }
    }
    if (role == "government") {
      if (hawk_dove > 0.6) {
        return("realist")  # Leadership launching invasion = realist
      } else {
        return("pragmatic_technocrat")  # Moderate government officials
      }
    }
    if (role == "intelligence") {
      return("realist")  # Intelligence services are inherently realist
    }
    if (role == "economic") {
      # Even economic advisors in aggressive regime lean realist
      if (hawk_dove > 0.4) {
        return("pragmatic_technocrat")
      } else {
        return("pragmatic_technocrat")  # Still technocratic but regime-aligned
      }
    }
  }

  # SMALL POWER agents - defending nation, seeks international support
  if (faction == "small_power") {
    if (role == "military") {
      if (hawk_dove > 0.8) {
        return("nationalist_populist")  # Defensive nationalism
      } else if (hawk_dove > 0.5) {
        return("realist")  # Pragmatic defense
      } else {
        return("liberal_institutionalist")  # Seeks international backing
      }
    }
    if (role == "government") {
      return("liberal_institutionalist")  # Seeking international support
    }
    if (role == "diplomatic") {
      return("liberal_institutionalist")
    }
    if (role == "political") {
      if (hawk_dove > 0.6) {
        return("nationalist_populist")  # Rally around flag
      } else {
        return("constructivist")  # Relationship-focused opposition
      }
    }
  }

  # VALKORIA (allied to aggressor) - supports major power
  if (faction == "valkoria") {
    if (hawk_dove > 0.6) {
      return("realist")  # Power politics
    } else {
      return("pragmatic_technocrat")
    }
  }

  # MERIDIAN (allied to defender) - supports small power
  if (faction == "meridian") {
    if (hawk_dove > 0.5) {
      return("realist")  # Security-focused ally
    } else {
      return("liberal_institutionalist")  # Rules-based order
    }
  }

  # AURELIA (neutral mediator)
  if (faction == "aurelia") {
    return("liberal_institutionalist")  # Believes in diplomacy
  }

  # INTERNATIONAL ORG
  if (faction == "international_org") {
    return("liberal_institutionalist")
  }

  # Fallback by role for any remaining cases
  if (role == "military") {
    return("realist")
  }
  if (role == "diplomatic") {
    return("liberal_institutionalist")
  }
  if (role == "economic") {
    return("pragmatic_technocrat")
  }

  # Default
  return("pragmatic_technocrat")
}

#' Modify agent capabilities based on hawk_dove, role, and faction
#'
#' @param base_profile Base role profile
#' @param hawk_dove Hawk-dove score
#' @param policy_adherence Policy adherence score
#' @param faction Agent's faction (for faction-specific modifications)
#' @param role Agent's role
#' @return Modified capability scores
modify_capabilities <- function(base_profile, hawk_dove, policy_adherence,
                                faction = NULL, role = NULL) {
  # Hawks are more willing to deceive
  deception_willingness <- base_profile$deception_willingness + (hawk_dove - 0.5) * 0.3
  deception_willingness <- max(0, min(1, deception_willingness))

  # Low policy adherence = higher deception willingness
  deception_willingness <- deception_willingness + (1 - policy_adherence) * 0.2
  deception_willingness <- max(0, min(1, deception_willingness))

  # Hawks may have slightly worse analytical capability (emotion-driven)
  analytical_capability <- base_profile$analytical_capability - (hawk_dove - 0.5) * 0.1
  analytical_capability <- max(0.3, min(1, analytical_capability))

  # Rationality modifications
  # Hawks have higher emotional volatility
  emotional_volatility <- base_profile$emotional_volatility + (hawk_dove - 0.5) * 0.2
  emotional_volatility <- max(0, min(1, emotional_volatility))

  # High hawks + low rationality = higher paranoia
  paranoia <- base_profile$paranoia + (hawk_dove - 0.5) * 0.15
  paranoia <- max(0, min(1, paranoia))

  # Low policy adherence = lower consistency
  behavioral_consistency <- base_profile$behavioral_consistency * policy_adherence
  behavioral_consistency <- max(0.2, min(1, behavioral_consistency))

  # Start with base cognitive rationality
  cognitive_rationality <- base_profile$cognitive_rationality

  # LOWER RATIONALITY for certain agent types to create more diverse behavior
  # Ultra-hawks (>0.85) are more emotion-driven
  if (hawk_dove > 0.85) {
    cognitive_rationality <- cognitive_rationality - 0.20
    emotional_volatility <- emotional_volatility + 0.15
  }

  # Major power government launching invasion - ideologically driven, not purely rational
  if (!is.null(faction) && faction == "major_power" && !is.null(role) && role == "government") {
    cognitive_rationality <- cognitive_rationality - 0.15  # Ideology over pure rationality
    paranoia <- paranoia + 0.10  # More threat-focused
  }

  # Political opposition is less consistent and more emotional
  if (!is.null(role) && role == "political") {
    cognitive_rationality <- cognitive_rationality - 0.15
    emotional_volatility <- emotional_volatility + 0.20
    behavioral_consistency <- behavioral_consistency - 0.30
  }

  # Clamp values
  cognitive_rationality <- max(0.35, min(1, cognitive_rationality))
  emotional_volatility <- max(0, min(0.85, emotional_volatility))
  paranoia <- max(0, min(0.95, paranoia))
  behavioral_consistency <- max(0.15, min(1, behavioral_consistency))

  return(list(
    deception_capacity = base_profile$deception_capacity,
    deception_willingness = deception_willingness,
    information_access = base_profile$information_access,
    analytical_capability = analytical_capability,
    # Rationality components
    cognitive_rationality = cognitive_rationality,
    paranoia = paranoia,
    behavioral_consistency = behavioral_consistency,
    emotional_volatility = emotional_volatility
  ))
}

#' Create integrated agent from config
#'
#' @param agent_id Agent identifier from config
#' @param agent_config Agent configuration list
#' @param country_name Fictionalized country name
#' @return Integrated cognitive agent
create_integrated_agent <- function(agent_id, agent_config, country_name = NULL) {
  role <- agent_config$role
  faction <- agent_config$faction
  hawk_dove <- agent_config$hawk_dove
  policy_adherence <- agent_config$policy_adherence

  # Get base profile for role
  role_profile <- ROLE_PROFILES[[role]]
  if (is.null(role_profile)) {
    role_profile <- ROLE_PROFILES$government  # Default
  }

  # Assign worldview
  worldview <- assign_worldview(role, hawk_dove, faction)

  # Modify capabilities based on personality, faction, and role
  capabilities <- modify_capabilities(role_profile, hawk_dove, policy_adherence, faction, role)

  # Determine country name
  if (is.null(country_name)) {
    country_name <- switch(faction,
      "major_power" = "Novaris",
      "small_power" = "Tethys",
      "external" = "External Actor",
      faction
    )
  }

  # Create cognitive agent
  agent <- create_cognitive_agent(
    name = agent_config$name,
    country = country_name,
    worldview = worldview,
    deception_capacity = capabilities$deception_capacity,
    deception_willingness = capabilities$deception_willingness,
    information_access = capabilities$information_access,
    analytical_capability = capabilities$analytical_capability,
    # Rationality components
    cognitive_rationality = capabilities$cognitive_rationality,
    paranoia = capabilities$paranoia,
    behavioral_consistency = capabilities$behavioral_consistency,
    emotional_volatility = capabilities$emotional_volatility
  )

  # Add original attributes
  agent$agent_id <- agent_id
  agent$faction <- faction
  agent$role <- role
  agent$hawk_dove <- hawk_dove
  agent$policy_adherence <- policy_adherence
  agent$objective_alignment <- agent_config$objective_alignment
  agent$description <- agent_config$description

  # Role-specific information access
  agent <- set_role_information_access(agent, role, faction)

  return(agent)
}

#' Set role-specific information access patterns
#'
#' @param agent Agent object
#' @param role Role type
#' @param faction Faction
#' @return Agent with updated information access
set_role_information_access <- function(agent, role, faction) {
  # What does this role have access to?
  if (role == "intelligence") {
    agent$has_access_to <- c(
      "signals_intelligence",
      "human_intelligence",
      "satellite_imagery",
      "intercepted_communications",
      "foreign_agents_reports"
    )
  } else if (role == "military") {
    agent$has_access_to <- c(
      "battlefield_reports",
      "tactical_intelligence",
      "troop_movements",
      "logistics_data",
      "weapons_inventory"
    )
  } else if (role == "government") {
    agent$has_access_to <- c(
      "intelligence_briefings",
      "diplomatic_cables",
      "economic_reports",
      "public_opinion_polls",
      "media_reports"
    )
  } else if (role == "economic") {
    agent$has_access_to <- c(
      "economic_statistics",
      "trade_data",
      "sanctions_impact",
      "budget_reports",
      "market_intelligence"
    )
  } else if (role == "diplomatic") {
    agent$has_access_to <- c(
      "diplomatic_cables",
      "foreign_ministry_reports",
      "international_media",
      "embassy_reports",
      "track_two_dialogues"
    )
  } else if (role == "political") {
    agent$has_access_to <- c(
      "public_information",
      "media_reports",
      "leaked_documents",
      "opposition_intelligence",
      "public_opinion"
    )
  } else if (role %in% c("foreign_government", "international_org")) {
    agent$has_access_to <- c(
      "public_information",
      "diplomatic_reports",
      "international_media",
      "intelligence_sharing",
      "open_source_intelligence"
    )
  }

  # Faction determines what information is available
  if (faction == "small_power") {
    # Smaller power has less resources
    agent$information$access <- agent$information$access * 0.85
  } else if (faction == "external") {
    # External actors depend on sharing
    agent$information$access <- agent$information$access * 0.90
  }

  return(agent)
}

#' Determine what information an agent can share
#'
#' @param agent Agent object
#' @param information_type Type of information
#' @return TRUE if agent has access to this information type
can_access_information <- function(agent, information_type) {
  return(information_type %in% agent$has_access_to)
}

#' Share information between agents (with potential deception)
#'
#' @param sender Sending agent
#' @param receiver Receiving agent
#' @param information Information to share
#' @param context Current context
#' @return Information received (potentially false or filtered)
share_information <- function(sender, receiver, information, context) {
  # Check if sender has access to this information
  if (!can_access_information(sender, information$type)) {
    return(list(
      received = FALSE,
      reason = "Sender lacks access to this information"
    ))
  }

  # Check for deception attempt
  deception <- attempt_deception(sender, "intelligence_sharing", receiver, context)

  if (deception$attempted && deception$successful) {
    # Sender successfully deceives - alter information
    false_information <- information
    false_information$content <- paste0("[DECEPTION] ", information$content)
    false_information$source_reliability <- "compromised"
    false_information$is_deception <- TRUE

    return(list(
      received = TRUE,
      information = false_information,
      deception_successful = TRUE
    ))
  } else if (deception$attempted && !deception$successful) {
    # Deception detected
    receiver <- update_trust(receiver, sender, "intelligence_sharing",
                           deception_detected = TRUE)

    return(list(
      received = TRUE,
      information = information,
      deception_detected = TRUE,
      trust_damaged = TRUE,
      new_trust = receiver$trust_levels[[sender$name]]
    ))
  } else {
    # Honest sharing
    filtered_info <- filter_information(receiver, information, sender$name)

    return(list(
      received = TRUE,
      information = filtered_info,
      honest_exchange = TRUE
    ))
  }
}

#' Create all integrated agents from config
#'
#' @param config Configuration object with AGENTS
#' @param country_mapping Named list mapping factions to country names
#' @return List of integrated agents
create_all_integrated_agents <- function(config, country_mapping = NULL) {
  if (is.null(country_mapping)) {
    country_mapping <- list(
      major_power = "Novaris",
      small_power = "Tethys",
      external = "External"
    )
  }

  agents <- list()

  for (agent_id in names(config$AGENTS)) {
    agent_config <- config$AGENTS[[agent_id]]
    country_name <- country_mapping[[agent_config$faction]]

    # Special handling for external actors
    if (agent_config$faction == "external") {
      if (grepl("Allied Defender", agent_config$name)) {
        country_name <- "Meridian"
      } else if (grepl("Allied Aggressor", agent_config$name)) {
        country_name <- "Valkoria"
      } else if (grepl("Neutral", agent_config$name)) {
        country_name <- "Aurelia"
      } else {
        country_name <- "International Community"
      }
    }

    agent <- create_integrated_agent(agent_id, agent_config, country_name)
    agents[[agent_id]] <- agent
  }

  return(agents)
}

#' Get agents by faction
#'
#' @param agents List of all agents
#' @param faction Faction name
#' @return List of agents in that faction
get_agents_by_faction <- function(agents, faction) {
  Filter(function(a) a$faction == faction, agents)
}

#' Get agents by role
#'
#' @param agents List of all agents
#' @param role Role type
#' @return List of agents with that role
get_agents_by_role <- function(agents, role) {
  Filter(function(a) a$role == role, agents)
}

#' Determine which agents can communicate
#'
#' @param agent1 First agent
#' @param agent2 Second agent
#' @return TRUE if they can communicate
can_communicate <- function(agent1, agent2) {
  # Same faction - always can communicate
  if (agent1$faction == agent2$faction) {
    return(TRUE)
  }

  # Diplomatic roles can communicate across factions
  if (agent1$role == "diplomatic" || agent2$role == "diplomatic") {
    return(TRUE)
  }

  # Intelligence can communicate (covertly)
  if (agent1$role == "intelligence" && agent2$role == "intelligence") {
    return(TRUE)
  }

  # External actors can communicate with anyone
  if (agent1$faction == "external" || agent2$faction == "external") {
    return(TRUE)
  }

  # Government leaders can communicate
  if (agent1$role == "government" && agent2$role == "government") {
    return(TRUE)
  }

  # Otherwise no direct communication
  return(FALSE)
}

#' Generate intra-faction coordination action
#'
#' @param agents Agents in same faction
#' @param topic Discussion topic
#' @param context Current context
#' @return Coordination outcome
intra_faction_coordination <- function(agents, topic, context) {
  # Each agent provides input based on their worldview
  inputs <- list()

  for (agent in agents) {
    # Filter context through worldview
    perceived_situation <- filter_information(agent, context, "situation_update")

    # Generate recommendation
    recommendation <- generate_cognitive_action(
      agent,
      perceived_situation,
      ACTION_TYPES
    )

    inputs[[agent$name]] <- list(
      agent_id = agent$agent_id,
      role = agent$role,
      worldview = agent$worldview,
      hawk_dove = agent$hawk_dove,
      recommendation = recommendation$action,
      reasoning = recommendation$reasoning
    )
  }

  # Determine consensus (hawks vs doves)
  avg_hawk_dove <- mean(sapply(agents, function(a) a$hawk_dove))

  # Weighted by policy adherence and objective alignment
  weights <- sapply(agents, function(a) a$policy_adherence * a$objective_alignment)
  weighted_hawk <- sum(sapply(1:length(agents), function(i) {
    agents[[i]]$hawk_dove * weights[i]
  })) / sum(weights)

  return(list(
    inputs = inputs,
    avg_hawk_dove = avg_hawk_dove,
    weighted_position = weighted_hawk,
    consensus = if (weighted_hawk > 0.6) "aggressive" else if (weighted_hawk < 0.4) "cautious" else "moderate"
  ))
}
