# External event generator - creates random geopolitical/economic events

#' Generate external events for a time period
#'
#' @param period Integer period number
#' @param event_types List of possible event types with probabilities
#' @param n_events Number of events to generate (default 1-2)
#' @return List of events that occurred
generate_external_events <- function(period, event_types, n_events = NULL) {
  if (is.null(n_events)) {
    # Randomly generate 0-2 events per period
    n_events <- sample(0:2, 1, prob = c(0.2, 0.5, 0.3))
  }

  if (n_events == 0) {
    return(list())
  }

  # Sample events based on probabilities
  event_probs <- sapply(event_types, function(e) e$probability)
  selected_indices <- sample(
    seq_along(event_types),
    size = min(n_events, length(event_types)),
    prob = event_probs,
    replace = FALSE
  )

  events <- lapply(selected_indices, function(idx) {
    event <- event_types[[idx]]

    # Create base event
    event_obj <- list(
      period = period,
      timestamp = Sys.time(),
      type = event$type,
      name = event$name,
      description = event$impact,
      severity = runif(1, 0.5, 1.0)  # Random severity multiplier
    )

    # Add directional impact_type for battlefield events
    if (event$type == "battlefield") {
      # Balanced direction (50-50 defender vs aggressor success)
      if (runif(1) < 0.5) {
        event_obj$impact_type <- "defender_success"
        event_obj$description <- "Smaller power successfully defends key positions"
      } else {
        event_obj$impact_type <- "aggressor_success"
        event_obj$description <- "Major power makes significant territorial gains"
      }
    }

    # Add directional impact_type for economic events
    if (event$type == "economic") {
      if (grepl("sanction", event$name, ignore.case = TRUE)) {
        event_obj$impact_type <- "sanctions_increase"
      }
    }

    event_obj
  })

  return(events)
}

#' Generate battlefield events based on current military balance
#'
#' @param period Integer period number
#' @param military_balance Numeric value indicating balance (-1 to 1, negative favors major power)
#' @return Battlefield event description
generate_battlefield_event <- function(period, military_balance = 0) {
  # Add some randomness to the outcome
  outcome <- military_balance + rnorm(1, 0, 0.3)

  # Balanced battlefield outcomes (50-50 instead of defender bias)
  if (outcome > 0.3) {
    description <- "Simulated tactical shift: Smaller power successfully defends key positions"
    impact <- "defender_success"
  } else if (outcome > 0) {
    description <- "Simulated frontline stabilizes with defensive advantages"
    impact <- "stalemate_favorable"
  } else if (outcome > -0.3) {
    description <- "Simulated frontline stabilizes with uncertain momentum"
    impact <- "stalemate_uncertain"
  } else if (outcome > -0.6) {
    description <- "Simulated territorial shift: Major power makes limited advances"
    impact <- "aggressor_advance"
  } else {
    description <- "Simulated breakthrough: Major power achieves significant operational objectives"
    impact <- "aggressor_success"
  }

  list(
    period = period,
    timestamp = Sys.time(),
    type = "battlefield",
    name = "Battlefield Development",
    description = description,
    impact_type = impact,
    severity = abs(outcome)
  )
}

#' Generate economic event affecting one or both powers
#'
#' @param period Integer period number
#' @param sanctions_level Current level of sanctions (0-1)
#' @return Economic event description
generate_economic_event <- function(period, sanctions_level = 0.5) {
  event_type <- sample(c("sanctions", "commodity", "gdp"), 1)

  if (event_type == "sanctions") {
    if (runif(1) < 0.7) {
      description <- sprintf(
        "New sanctions package targets major power's %s sector",
        sample(c("energy", "banking", "technology", "defense"), 1)
      )
      impact_type <- "sanctions_increase"
    } else {
      description <- "Some countries ease sanctions in exchange for partial withdrawal"
      impact_type <- "sanctions_decrease"
    }
  } else if (event_type == "commodity") {
    commodity <- sample(c("oil", "natural gas", "wheat", "metals"), 1)
    direction <- sample(c("surge", "decline"), 1, prob = c(0.6, 0.4))
    pct_change <- round(runif(1, 10, 40))

    description <- sprintf(
      "%s prices %s by %d%%, affecting both economies",
      tools::toTitleCase(commodity),
      direction,
      pct_change
    )
    impact_type <- paste0("commodity_", direction)
  } else {
    # GDP impact
    if (runif(1) < sanctions_level) {
      description <- "Major power's GDP contracts due to war costs and sanctions"
      impact_type <- "gdp_decline_major"
    } else {
      description <- "Smaller power's economy shows resilience despite ongoing conflict"
      impact_type <- "gdp_stable_small"
    }
  }

  list(
    period = period,
    timestamp = Sys.time(),
    type = "economic",
    name = "Economic Development",
    description = description,
    impact_type = impact_type,
    severity = runif(1, 0.4, 0.9)
  )
}

#' Generate diplomatic event (balanced between favoring defender/aggressor)
#'
#' @param period Integer period number
#' @return Diplomatic event description
generate_diplomatic_event <- function(period) {
  # Balanced diplomatic events
  event_type <- sample(
    c("peace_talks", "alliance_defender", "alliance_aggressor",
      "condemnation", "mediation", "diplomatic_rift"),
    1,
    prob = c(0.2, 0.15, 0.15, 0.2, 0.15, 0.15)
  )

  if (event_type == "peace_talks") {
    description <- "Neutral power proposes new framework for peace negotiations"
    impact_type <- "peace_initiative"
    favors <- "neutral"
  } else if (event_type == "alliance_defender") {
    description <- "Allied coalition announces expanded military and economic cooperation with defender"
    impact_type <- "alliance_strengthening_defender"
    favors <- "defender"
  } else if (event_type == "alliance_aggressor") {
    description <- "Aggressor's ally announces increased diplomatic and economic support"
    impact_type <- "alliance_strengthening_aggressor"
    favors <- "aggressor"
  } else if (event_type == "condemnation") {
    description <- "International organization passes resolution condemning aggression"
    impact_type <- "diplomatic_pressure"
    favors <- "defender"
  } else if (event_type == "mediation") {
    description <- "Regional summit convened to discuss conflict de-escalation"
    impact_type <- "mediation_attempt"
    favors <- "neutral"
  } else {
    # diplomatic_rift - can go either way
    if (runif(1) < 0.5) {
      description <- "Defender's key ally faces domestic pressure to reduce involvement"
      impact_type <- "alliance_strain_defender"
      favors <- "aggressor"
    } else {
      description <- "Aggressor faces diplomatic isolation; key partner distances itself"
      impact_type <- "alliance_strain_aggressor"
      favors <- "defender"
    }
  }

  list(
    period = period,
    timestamp = Sys.time(),
    type = "diplomatic",
    name = "Diplomatic Development",
    description = description,
    impact_type = impact_type,
    favors = favors,
    severity = runif(1, 0.3, 0.8)
  )
}

#' Generate naval incident event
#'
#' @param period Integer period number
#' @return Naval event description
generate_naval_event <- function(period) {
  event_type <- sample(
    c("strait_incident", "naval_exercise", "fishing_dispute", "freedom_of_nav",
      "naval_buildup", "blockade_threat", "port_harassment"),
    1,
    prob = c(0.25, 0.15, 0.15, 0.2, 0.1, 0.1, 0.05)
  )

  if (event_type == "strait_incident") {
    incidents <- list(
      "Major power naval vessels shadow defender's cargo ships in Cerulean Strait",
      "Near-collision between major power destroyer and neutral tanker in contested waters",
      "Defender coast guard detains major power fishing vessels near Serpent Island",
      "Major power conducts live-fire naval exercise in disputed strait"
    )
    description <- sample(incidents, 1)
    impact_type <- "naval_tension_increase"
  } else if (event_type == "naval_exercise") {
    description <- "Defender conducts joint naval exercises with allied powers in regional waters"
    impact_type <- "naval_posturing_defender"
  } else if (event_type == "fishing_dispute") {
    description <- "Fishing vessels from both nations clash over territorial waters; coast guard called in"
    impact_type <- "maritime_dispute"
  } else if (event_type == "freedom_of_nav") {
    description <- "Neutral shipping companies complain of harassment in Cerulean Strait"
    impact_type <- "commercial_navigation_threat"
  } else if (event_type == "naval_buildup") {
    if (runif(1) < 0.5) {
      description <- "Major power deploys additional warships to Serpent Island naval base"
      impact_type <- "naval_escalation_major"
    } else {
      description <- "Defender strengthens coastal defense systems along strait approaches"
      impact_type <- "naval_defense_small"
    }
  } else if (event_type == "blockade_threat") {
    description <- "Major power announces 'enhanced inspections' of shipping entering defender ports"
    impact_type <- "quasi_blockade"
  } else {
    description <- "Defender naval forces increase port security and anti-access preparations"
    impact_type <- "port_security_increase"
  }

  list(
    period = period,
    timestamp = Sys.time(),
    type = "naval",
    name = "Naval Incident",
    description = description,
    impact_type = impact_type,
    severity = runif(1, 0.4, 0.85)
  )
}

#' Generate air warfare incident event
#'
#' @param period Integer period number
#' @return Air warfare event description
generate_air_event <- function(period) {
  event_type <- sample(
    c("airspace_violation", "drone_incident", "fighter_scramble", "air_defense",
      "no_fly_zone_proposal", "civilian_air_threat"),
    1,
    prob = c(0.25, 0.2, 0.2, 0.15, 0.1, 0.1)
  )

  if (event_type == "airspace_violation") {
    incidents <- list(
      "Major power bombers conduct 'training mission' near defender airspace; fighters scrambled",
      "Defender aircraft conduct reconnaissance flight along border; major power protests",
      "Major power military aircraft violate neutral airspace during patrol mission",
      "Both nations' fighters conduct aggressive maneuvering in disputed airspace"
    )
    description <- sample(incidents, 1)
    impact_type <- "airspace_tension"
  } else if (event_type == "drone_incident") {
    if (runif(1) < 0.6) {
      description <- "Defender shoots down major power reconnaissance drone over disputed territory"
      impact_type <- "drone_shootdown"
    } else {
      description <- "Major power claims to have destroyed defender surveillance drone"
      impact_type <- "drone_escalation"
    }
  } else if (event_type == "fighter_scramble") {
    description <- sprintf(
      "Air forces scrambled %d times this week as tensions increase",
      sample(12:25, 1)
    )
    impact_type <- "air_readiness_high"
  } else if (event_type == "air_defense") {
    if (runif(1) < 0.5) {
      description <- "Major power activates air defense systems along border; defender calls it 'threatening'"
      impact_type <- "air_defense_major"
    } else {
      description <- "Defender deploys mobile surface-to-air missile batteries to forward positions"
      impact_type <- "air_defense_small"
    }
  } else if (event_type == "no_fly_zone_proposal") {
    description <- "International community debates no-fly zone proposal to prevent escalation"
    impact_type <- "no_fly_zone_discussion"
  } else {
    description <- "Civilian airlines reroute flights due to air defense incidents; airspace increasingly dangerous"
    impact_type <- "civilian_air_disruption"
  }

  list(
    period = period,
    timestamp = Sys.time(),
    type = "air",
    name = "Air Incident",
    description = description,
    impact_type = impact_type,
    severity = runif(1, 0.3, 0.8)
  )
}

#' Generate cyber warfare incident event
#'
#' @param period Integer period number
#' @return Cyber event description
generate_cyber_event <- function(period) {
  event_type <- sample(
    c("infrastructure_attack", "cyber_espionage", "financial_cyber",
      "military_network", "attribution_dispute", "cyber_defense"),
    1,
    prob = c(0.25, 0.2, 0.15, 0.15, 0.15, 0.1)
  )

  if (event_type == "infrastructure_attack") {
    targets <- list(
      list(
        target = "Defender power grid experiences widespread outages; cyber attack suspected",
        attribution = "defender"
      ),
      list(
        target = "Major power pipeline control systems targeted by sophisticated malware",
        attribution = "major"
      ),
      list(
        target = "Banking system disruption affects major power financial sector",
        attribution = "major"
      ),
      list(
        target = "Defender telecommunications infrastructure suffers distributed attack",
        attribution = "defender"
      )
    )
    selected <- sample(targets, 1)[[1]]
    description <- selected$target
    impact_type <- paste0("cyber_infrastructure_", selected$attribution)
  } else if (event_type == "cyber_espionage") {
    if (runif(1) < 0.5) {
      description <- "Major intelligence leak: Defender military plans exposed via cyber breach"
      impact_type <- "cyber_espionage_defender"
    } else {
      description <- "Major power accuses defender's allies of cyber espionage campaign"
      impact_type <- "cyber_espionage_major"
    }
  } else if (event_type == "financial_cyber") {
    description <- "Coordinated cyberattack on major power banks attributed to state-sponsored actors"
    impact_type <- "financial_cyberattack"
  } else if (event_type == "military_network") {
    if (runif(1) < 0.5) {
      description <- "Defender military command and control networks experience disruption"
      impact_type <- "military_cyber_defender"
    } else {
      description <- "Major power satellite communications briefly go offline; cyber attack suspected"
      impact_type <- "military_cyber_major"
    }
  } else if (event_type == "attribution_dispute") {
    description <- "Both nations accuse each other of cyber attacks; attribution remains unclear"
    impact_type <- "cyber_attribution_crisis"
  } else {
    description <- "Defender strengthens cyber defenses with allied technical assistance"
    impact_type <- "cyber_defense_upgrade"
  }

  list(
    period = period,
    timestamp = Sys.time(),
    type = "cyber",
    name = "Cyber Incident",
    description = description,
    impact_type = impact_type,
    severity = runif(1, 0.4, 0.9)
  )
}

#' Generate information warfare event
#'
#' @param period Integer period number
#' @return Information warfare event description
generate_information_event <- function(period) {
  event_type <- sample(
    c("disinformation_campaign", "public_opinion_shift", "international_narrative",
      "media_leak", "propaganda_victory", "diaspora_division"),
    1,
    prob = c(0.25, 0.2, 0.2, 0.15, 0.1, 0.1)
  )

  if (event_type == "disinformation_campaign") {
    campaigns <- list(
      "Social media campaign falsely claims defender preparing chemical weapons",
      "Coordinated bot network spreads false narratives about major power intentions",
      "Deepfake video of defender leader causes international controversy",
      "Major power state media launches coordinated propaganda offensive"
    )
    description <- sample(campaigns, 1)
    impact_type <- "information_warfare_active"
  } else if (event_type == "public_opinion_shift") {
    if (runif(1) < 0.5) {
      shifts <- list(
        "War-weariness grows in defender population; protests demand negotiations",
        "Major power domestic opposition to conflict increases; economic costs mount",
        "Defender public rallies around flag after major power aggression"
      )
      description <- sample(shifts, 1)
      impact_type <- "domestic_opinion_shift"
    } else {
      description <- "International public opinion increasingly sympathetic to defender's position"
      impact_type <- "international_opinion_defender"
    }
  } else if (event_type == "international_narrative") {
    if (runif(1) < 0.5) {
      description <- "Major power narrative gains traction in neutral countries; legitimacy contest intensifies"
      impact_type <- "narrative_victory_major"
    } else {
      description <- "Defender successfully frames conflict as defensive; international support increases"
      impact_type <- "narrative_victory_defender"
    }
  } else if (event_type == "media_leak") {
    leaks <- list(
      "Leaked documents reveal major power war plans; international scandal",
      "Defender intelligence shared with media exposes major power violations",
      "Internal military communications leak embarrasses both sides"
    )
    description <- sample(leaks, 1)
    impact_type <- "information_leak"
  } else if (event_type == "propaganda_victory") {
    if (runif(1) < 0.5) {
      description <- "Major power propaganda campaign backfires; credibility damaged"
      impact_type <- "propaganda_failure_major"
    } else {
      description <- "Defender information campaign effectively counters major power narratives"
      impact_type <- "information_defense_success"
    }
  } else {
    description <- "Diaspora communities split over conflict; social divisions intensify in multiple countries"
    impact_type <- "diaspora_polarization"
  }

  list(
    period = period,
    timestamp = Sys.time(),
    type = "information",
    name = "Information Warfare",
    description = description,
    impact_type = impact_type,
    severity = runif(1, 0.3, 0.75)
  )
}

#' Create formatted event summary for agents
#'
#' @param events List of event objects
#' @return Character string with formatted summary
format_events_for_agents <- function(events) {
  if (length(events) == 0) {
    return("No major external events this period.")
  }

  summaries <- sapply(events, function(e) {
    sprintf("- %s: %s", e$name, e$description)
  })

  paste(summaries, collapse = "\n")
}

#' Generate high-impact shock events (political crises, escalations)
#' SYMMETRIC DESIGN: 50% help defender, 50% help aggressor
#'
#' @param period Integer period number
#' @param scenario_state Current scenario state
#' @return Shock event or NULL
generate_shock_event <- function(period, scenario_state) {
  # 20% chance of shock event per period
  if (runif(1) > 0.2) {
    return(NULL)
  }

  # SYMMETRIC shock events - balanced between helping defender vs aggressor
  # Negative impact_on_collapse = helps defender (reduces collapse probability)
  # Positive impact_on_collapse = helps aggressor (increases collapse probability)

  # Events that HELP THE DEFENDER (reduce collapse probability)
  defender_favorable <- list(
    list(
      type = "domestic_crisis_major",
      name = "Aggressor Internal Crisis",
      description = "Major anti-war protests erupt in aggressor nation; political opposition gains momentum",
      impact_on_collapse = -0.18,
      severity = 0.85
    ),
    list(
      type = "military_disaster_major",
      name = "Aggressor Military Failure",
      description = "Aggressor offensive stalls with heavy casualties; strategic positions lost",
      impact_on_collapse = -0.22,
      severity = 0.9
    ),
    list(
      type = "diplomatic_breakthrough",
      name = "Diplomatic Breakthrough",
      description = "Major diplomatic initiative gains international support; ceasefire framework emerging",
      impact_on_collapse = -0.15,
      severity = 0.7
    ),
    list(
      type = "allied_surge_defender",
      name = "Allied Support Surge",
      description = "Allied coalition announces major new military aid package for defender",
      impact_on_collapse = -0.20,
      severity = 0.85
    ),
    list(
      type = "defender_counteroffensive",
      name = "Defender Counteroffensive Success",
      description = "Defender forces achieve breakthrough; recapture strategic territory",
      impact_on_collapse = -0.25,
      severity = 0.95
    ),
    list(
      type = "aggressor_economic_crisis",
      name = "Aggressor Economic Crisis",
      description = "Sanctions bite hard; aggressor faces currency collapse and supply shortages",
      impact_on_collapse = -0.18,
      severity = 0.8
    ),
    list(
      type = "international_condemnation",
      name = "International Condemnation",
      description = "UN passes binding resolution; new coalition forms to support defender",
      impact_on_collapse = -0.12,
      severity = 0.65
    ),
    list(
      type = "aggressor_ally_wavering",
      name = "Aggressor Alliance Fractures",
      description = "Key ally of aggressor distances itself; reduces economic and diplomatic support",
      impact_on_collapse = -0.15,
      severity = 0.75
    )
  )

  # Events that HELP THE AGGRESSOR (increase collapse probability)
  aggressor_favorable <- list(
    list(
      type = "domestic_crisis_small",
      name = "Defender Internal Crisis",
      description = "Political infighting erupts in defender nation; war-weariness spreads",
      impact_on_collapse = 0.18,
      severity = 0.85
    ),
    list(
      type = "leadership_challenge_small",
      name = "Defender Leadership Challenge",
      description = "Opposition leader demands negotiations; threatens no-confidence vote",
      impact_on_collapse = 0.22,
      severity = 0.9
    ),
    list(
      type = "military_disaster_small",
      name = "Defender Military Setback",
      description = "Defender forces suffer major defeat; critical defensive lines breached",
      impact_on_collapse = 0.25,
      severity = 0.95
    ),
    list(
      type = "escalation_threat",
      name = "Escalation Threat",
      description = "Aggressor signals willingness to use unconventional weapons; international panic",
      impact_on_collapse = 0.15,
      severity = 0.9
    ),
    list(
      type = "allied_abandonment",
      name = "Allied Support Wavers",
      description = "Key ally signals reduced military aid commitment; domestic politics intervene",
      impact_on_collapse = 0.18,
      severity = 0.8
    ),
    list(
      type = "coup_attempt",
      name = "Coup Attempt",
      description = "Military faction in defender nation attempts power seizure; chaos ensues",
      impact_on_collapse = 0.30,
      severity = 1.0
    ),
    list(
      type = "economic_collapse_defender",
      name = "Defender Economic Crisis",
      description = "Defender economy buckles under war strain; critical shortages emerge",
      impact_on_collapse = 0.20,
      severity = 0.85
    ),
    list(
      type = "aggressor_breakthrough",
      name = "Aggressor Breakthrough",
      description = "Aggressor forces achieve major operational success; encircle key city",
      impact_on_collapse = 0.25,
      severity = 0.95
    )
  )

  # 50-50 split: randomly select from defender-favorable or aggressor-favorable
  if (runif(1) < 0.5) {
    selected_shock <- sample(defender_favorable, 1)[[1]]
  } else {
    selected_shock <- sample(aggressor_favorable, 1)[[1]]
  }

  list(
    period = period,
    timestamp = Sys.time(),
    type = selected_shock$type,
    name = selected_shock$name,
    description = selected_shock$description,
    impact_on_collapse = selected_shock$impact_on_collapse,
    severity = selected_shock$severity,
    is_shock = TRUE
  )
}
