# Action Execution System
# Translates agent decisions into concrete state changes

#' Clamp military balance to valid range [-1, 1]
#'
#' @param value The military balance value to clamp
#' @return Clamped value within [-1, 1]
clamp_military_balance <- function(value) {
  max(-1, min(1, value))
}

#' Calculate diplomatic success probability based on context
#'
#' @param base_prob Base probability of success
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @param crisis_threshold Crisis level above which penalties apply
#' @param crisis_penalty Penalty per crisis level above threshold
#' @return Adjusted success probability (clamped to 0.05-0.95)
calculate_diplomatic_success_prob <- function(base_prob, actor, target, state,
                                               crisis_threshold = 5,
                                               crisis_penalty = 0.05) {
  prob <- base_prob
  crisis_level <- state$scenario_state$crisis_level
  military_balance <- state$scenario_state$military_balance

  # Crisis level penalty - harder to negotiate during active conflict

  if (crisis_level > crisis_threshold) {
    prob <- prob - (crisis_level - crisis_threshold) * crisis_penalty
  }

  # Military balance affects willingness - winning side less interested in talks
  # Negative balance = aggressor winning, positive = defender winning
  if (actor$faction == "major_power") {
    # If aggressor is winning (negative balance), less interested in diplomacy
    if (military_balance < -0.2) {
      prob <- prob - 0.10
    }
  } else if (actor$faction == "small_power") {
    # If defender is winning (positive balance), less need for desperate diplomacy
    if (military_balance > 0.2) {
      prob <- prob - 0.05  # Smaller penalty - defender still values peace
    }
  }

  # Allies are more receptive to each other
  if (!is.null(target)) {
    same_side <- (actor$faction == "small_power" && target$faction %in% c("small_power", "meridian")) ||
                 (actor$faction == "major_power" && target$faction %in% c("major_power", "valkoria")) ||
                 (actor$faction == "meridian" && target$faction == "small_power") ||
                 (actor$faction == "valkoria" && target$faction == "major_power")
    if (same_side) {
      prob <- prob + 0.15
    }
  }

  # Clamp to reasonable range - never impossible, never certain
  return(max(0.05, min(0.95, prob)))
}

#' Execute a diplomatic action
#'
#' @param action Action name
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @return List with results and updated state
execute_diplomatic_action <- function(action, actor, target, state) {
  result <- list(
    action = action,
    actor = actor$name,
    target = if(!is.null(target)) target$name else NA,
    success = TRUE,
    effects = list()
  )

  if (action == "diplomatic_visit") {
    # Base 50% - diplomatic visits often declined or produce nothing during conflict
    base_prob <- 0.50
    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 6,
                                                       crisis_penalty = 0.08)
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      result$effects$trust_change <- 0.05
      result$effects$diplomatic_relations <- "improved"
      result$effects$message <- "Diplomatic visit successful - relations improved"
    } else {
      result$success <- FALSE
      result$effects$trust_change <- 0
      result$effects$diplomatic_relations <- "unchanged"
      result$effects$message <- "Diplomatic visit declined or produced no results"
    }

  } else if (action == "peace_talks") {
    # Base 30% - most peace talks fail, especially during active conflict
    # Track peace talks count for diminishing returns
    if (is.null(state$peace_talks_count)) {
      state$peace_talks_count <- 0
    }
    state$peace_talks_count <- state$peace_talks_count + 1

    # Diminishing returns reduce base probability
    diminishing_factor <- max(0.1, 1 - (state$peace_talks_count - 1) * 0.15)
    base_prob <- 0.30 * diminishing_factor

    # Additional penalty if proposer is losing (desperate talks less credible)
    military_balance <- state$scenario_state$military_balance
    if ((actor$faction == "small_power" && military_balance < -0.2) ||
        (actor$faction == "major_power" && military_balance > 0.2)) {
      base_prob <- base_prob - 0.10  # Losing side penalty
    }

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 5,
                                                       crisis_penalty = 0.05)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$peace_talks_total <- state$peace_talks_count
    result$effects$diminishing_factor <- round(diminishing_factor * 100)

    if (runif(1) < success_prob) {
      # Successful peace talks reduce crisis
      base_reduction <- 1.5
      actual_reduction <- base_reduction * diminishing_factor

      state$scenario_state$crisis_level <- max(0, state$scenario_state$crisis_level - actual_reduction)
      result$effects$crisis_change <- -round(actual_reduction, 2)
      result$effects$message <- sprintf("Peace talks successful - crisis reduced by %.1f", actual_reduction)
    } else {
      result$success <- FALSE
      result$effects$crisis_change <- 0
      if (diminishing_factor < 0.5) {
        result$effects$message <- "Peace talks collapsed - parties too entrenched after repeated failures"
      } else {
        result$effects$message <- "Peace talks rejected - conditions not acceptable"
      }
    }

  } else if (action == "trade_negotiation") {
    # Base 40% between neutrals, much lower between adversaries
    # Check if negotiating with adversary
    is_adversary <- (actor$faction == "major_power" && !is.null(target) &&
                     target$faction %in% c("small_power", "meridian")) ||
                    (actor$faction == "small_power" && !is.null(target) &&
                     target$faction %in% c("major_power", "valkoria"))

    base_prob <- if (is_adversary) 0.10 else 0.40  # Very hard between enemies

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 6,
                                                       crisis_penalty = 0.06)
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      result$effects$economic_cooperation <- 0.1
      result$effects$message <- "Trade negotiations successful - economic ties strengthened"
    } else {
      result$success <- FALSE
      result$effects$economic_cooperation <- 0
      if (is_adversary) {
        result$effects$message <- "Trade negotiations failed - adversaries unwilling to engage economically"
      } else {
        result$effects$message <- "Trade negotiations stalled - terms unacceptable"
      }
    }

  } else if (action == "cultural_exchange") {
    # Base 60% - lower stakes, more likely to succeed
    base_prob <- 0.60
    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 7,
                                                       crisis_penalty = 0.10)
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      result$effects$soft_power <- 0.05
      result$effects$message <- "Cultural exchange successful - people-to-people ties strengthened"
    } else {
      result$success <- FALSE
      result$effects$soft_power <- 0
      result$effects$message <- "Cultural exchange cancelled due to tensions"
    }

  } else if (action == "humanitarian_aid") {
    # Base 55% - can be blocked, rejected, or diverted
    base_prob <- 0.55

    # Additional penalty if aid going to adversary territory (can be blocked)
    is_to_adversary <- (actor$faction == "major_power" && !is.null(target) &&
                        target$faction %in% c("small_power", "meridian")) ||
                       (actor$faction %in% c("small_power", "meridian", "international_org") &&
                        state$scenario_state$territory_controlled > 0.2)  # Aid to occupied areas

    if (is_to_adversary) {
      base_prob <- base_prob - 0.20  # Blockade/rejection risk
    }

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 7,
                                                       crisis_penalty = 0.08)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.5

    if (runif(1) < success_prob) {
      result$effects$international_support <- 0.1
      result$effects$message <- "Humanitarian aid delivered successfully"
    } else {
      result$success <- FALSE
      result$effects$international_support <- 0.02  # Still some credit for trying
      if (is_to_adversary) {
        result$effects$message <- "Humanitarian aid blocked or diverted"
      } else {
        result$effects$message <- "Humanitarian aid delivery faced logistical failures"
      }
    }

  } else if (action == "mediation_offer") {
    # Base 25% - mediation rarely accepted during active conflict
    base_prob <- 0.25

    # Neutral mediators more trusted
    is_neutral <- actor$faction %in% c("aurelia", "international_org")
    if (is_neutral) {
      base_prob <- base_prob + 0.10
    }

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 6,
                                                       crisis_penalty = 0.06)
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      state$scenario_state$crisis_level <- max(0, state$scenario_state$crisis_level - 2)
      result$effects$mediation_accepted <- TRUE
      result$effects$crisis_change <- -2
      result$effects$message <- "Mediation offer accepted - framework for talks established"
    } else {
      result$success <- FALSE
      result$effects$mediation_accepted <- FALSE
      result$effects$crisis_change <- 0
      result$effects$message <- "Mediation offer declined - parties not ready to negotiate"
    }

  } else if (action == "coalition_building") {
    # Building coalitions requires diplomatic skill and favorable conditions
    # Base 55% - coalition building is challenging
    base_prob <- 0.55

    # International support affects willingness of others to join
    if (!is.null(state$scenario_state$international_support)) {
      if (actor$faction == "small_power") {
        base_prob <- base_prob + (state$scenario_state$international_support - 0.5) * 0.3
      } else {
        base_prob <- base_prob - (state$scenario_state$international_support - 0.5) * 0.2
      }
    }

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 6,
                                                       crisis_penalty = 0.06)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 1.0

    if (runif(1) < success_prob) {
      result$effects$coalition_strength <- 0.15
      result$effects$diplomatic_leverage <- 0.1
      result$effects$message <- "Coalition building successful - new partners committed"
    } else {
      result$success <- FALSE
      result$effects$coalition_strength <- 0.03
      result$effects$message <- "Coalition building stalled - potential partners remain hesitant"
    }

  } else if (action == "backchannel_negotiations") {
    # Secret negotiations - can succeed even when public talks fail
    # Base 40% - backchannels are delicate
    base_prob <- 0.40

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 7,
                                                       crisis_penalty = 0.04)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.1

    if (runif(1) < success_prob) {
      result$effects$secret_understanding <- TRUE
      result$effects$future_leverage <- 0.1
      result$effects$message <- "Backchannel contact established - secret dialogue initiated"
    } else {
      result$success <- FALSE
      result$effects$secret_understanding <- FALSE
      result$effects$message <- "Backchannel approach rebuffed - no secret dialogue established"
    }

  } else if (action == "formal_peace_talks") {
    # More structured than regular peace_talks, higher stakes
    # Base 25% - formal talks often fail
    base_prob <- 0.25

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 5,
                                                       crisis_penalty = 0.05)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.3

    if (runif(1) < success_prob) {
      state$scenario_state$crisis_level <- max(0, state$scenario_state$crisis_level - 2)
      result$effects$crisis_change <- -2
      result$effects$formal_agreement <- TRUE
      result$effects$message <- "Formal peace talks achieved framework agreement"
    } else {
      result$success <- FALSE
      result$effects$crisis_change <- 0.5  # Failed formal talks slightly increase tension
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 0.5)
      result$effects$message <- "Formal peace talks collapsed - positions too far apart"
    }

  } else if (action == "prisoner_exchange") {
    # Humanitarian gesture that can build trust
    # Base 60% - usually doable if both sides willing
    base_prob <- 0.60

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 8,
                                                       crisis_penalty = 0.08)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.1

    if (runif(1) < success_prob) {
      result$effects$trust_building <- 0.1
      result$effects$humanitarian_credit <- 0.05
      result$effects$message <- "Prisoner exchange completed - humanitarian gesture appreciated"
    } else {
      result$success <- FALSE
      result$effects$message <- "Prisoner exchange negotiations failed - terms unacceptable"
    }

  } else if (action == "humanitarian_corridors") {
    # Establishing safe passage for civilians
    # Base 50% - requires cooperation from both sides
    base_prob <- 0.50

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 7,
                                                       crisis_penalty = 0.06)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.2

    if (runif(1) < success_prob) {
      result$effects$humanitarian_access <- TRUE
      result$effects$international_support <- 0.08
      result$effects$message <- "Humanitarian corridors established - civilians evacuated"
    } else {
      result$success <- FALSE
      result$effects$humanitarian_access <- FALSE
      result$effects$message <- "Humanitarian corridor negotiations failed - access denied"
    }

  } else if (action == "public_diplomatic_initiative") {
    # Public diplomacy campaign
    # Base 55% - public campaigns can succeed or backfire
    base_prob <- 0.55

    success_prob <- max(0.25, min(0.80, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.2

    if (runif(1) < success_prob) {
      result$effects$public_support <- 0.08
      result$effects$narrative_control <- TRUE
      result$effects$message <- "Public diplomatic initiative resonates - narrative shifting"
    } else {
      result$success <- FALSE
      result$effects$public_support <- -0.02
      result$effects$message <- "Public diplomatic initiative fell flat - message not received well"
    }

  } else if (action == "formal_multilateral_engagement") {
    # Engaging through international institutions
    # Base 45% - multilateral processes are slow and uncertain
    base_prob <- 0.45

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 6,
                                                       crisis_penalty = 0.05)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.5

    if (runif(1) < success_prob) {
      result$effects$institutional_support <- 0.1
      result$effects$legitimacy <- 0.08
      result$effects$message <- "Multilateral engagement successful - international backing secured"
    } else {
      result$success <- FALSE
      result$effects$institutional_support <- 0.02
      result$effects$message <- "Multilateral engagement stalled - consensus elusive"
    }

  } else if (action == "international_observers") {
    # Deploying international monitors
    # Base 50% - requires consent and cooperation
    base_prob <- 0.50

    success_prob <- calculate_diplomatic_success_prob(base_prob, actor, target, state,
                                                       crisis_threshold = 7,
                                                       crisis_penalty = 0.06)
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.3

    if (runif(1) < success_prob) {
      result$effects$transparency <- 0.1
      result$effects$violation_deterrence <- 0.08
      result$effects$message <- "International observers deployed - monitoring begins"
    } else {
      result$success <- FALSE
      result$effects$message <- "International observer deployment blocked - access denied"
    }
  }

  return(list(result = result, state = state))
}

#' Execute an intelligence action
#'
#' @param action Action name
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @return List with results and updated state
execute_intelligence_action <- function(action, actor, target, state) {
  result <- list(
    action = action,
    actor = actor$name,
    target = if(!is.null(target)) target$name else NA,
    success = TRUE,
    effects = list()
  )

  if (action == "intelligence_gathering") {
    # Intelligence gathering can fail due to counterintelligence, bad sources, or operational errors
    # Base 75% success, modified by actor's information access capability
    base_prob <- 0.75

    # Better information access = higher success
    if (!is.null(actor$information$access)) {
      base_prob <- base_prob + (actor$information$access - 0.5) * 0.2
    }

    # Target's counterintelligence capability reduces success
    if (!is.null(target) && !is.null(target$deception$capacity)) {
      base_prob <- base_prob - target$deception$capacity * 0.15
    }

    success_prob <- max(0.30, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      result$effects$information_gained <- TRUE
      result$effects$intelligence_quality <- actor$information$access
      result$effects$message <- sprintf("Gathered intelligence on %s",
                                       if(!is.null(target)) target$country else "situation")
    } else {
      result$success <- FALSE
      result$effects$information_gained <- FALSE
      # Partial failure - some low-quality intel obtained
      if (runif(1) < 0.5) {
        result$effects$intelligence_quality <- actor$information$access * 0.3
        result$effects$message <- "Intelligence gathering partially failed - only fragmentary information obtained"
      } else {
        result$effects$intelligence_quality <- 0
        result$effects$message <- "Intelligence gathering failed - sources unreliable or compromised"
      }
    }
  } else if (action == "surveillance_operation") {
    # Continuous monitoring
    success_prob <- actor$deception$capacity
    if (runif(1) < success_prob) {
      result$effects$surveillance_established <- TRUE
      result$effects$information_advantage <- 0.1
      result$effects$message <- "Surveillance operation successful"
    } else {
      result$success <- FALSE
      result$effects$detected <- TRUE
      result$effects$message <- "Surveillance operation detected - diplomatic incident"
      # Damages trust
      result$effects$trust_damage <- -0.3
    }
  } else if (action == "counterintelligence") {
    # Counterintelligence can fail to detect threats or implement effective measures
    # Base 70% effectiveness
    base_prob <- 0.70

    # Higher deception capacity = better counterintel
    if (!is.null(actor$deception$capacity)) {
      base_prob <- base_prob + actor$deception$capacity * 0.15
    }

    success_prob <- max(0.35, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      result$effects$defensive_capability <- 0.15
      result$effects$threats_detected <- TRUE
      result$effects$message <- "Counterintelligence measures enhanced - threats neutralized"
    } else {
      result$success <- FALSE
      result$effects$defensive_capability <- 0.05  # Minimal improvement
      result$effects$threats_detected <- FALSE
      result$effects$message <- "Counterintelligence efforts yielded limited results - some threats may persist"
    }
  } else if (action == "spread_disinformation") {
    # Attempt to deceive
    success_prob <- actor$deception$capacity * 0.7
    if (runif(1) < success_prob) {
      result$effects$disinformation_successful <- TRUE
      result$effects$enemy_confusion <- 0.2
      result$effects$message <- "Disinformation campaign successful"
    } else {
      result$success <- FALSE
      result$effects$exposed <- TRUE
      result$effects$trust_damage <- -0.5
      result$effects$international_reputation <- -0.2
      result$effects$message <- "Disinformation exposed - major credibility damage"
    }
  } else if (action == "propaganda_campaign") {
    # Propaganda campaigns can backfire or fail to gain traction
    # Base 65% effectiveness - messaging is hard
    base_prob <- 0.65

    # Crisis level affects receptiveness - people more skeptical during high crisis
    crisis_level <- if (!is.null(state$scenario_state$crisis_level)) {
      state$scenario_state$crisis_level
    } else {
      5
    }
    if (crisis_level > 7) {
      base_prob <- base_prob - (crisis_level - 7) * 0.08  # Harder to control narrative in crisis
    }

    success_prob <- max(0.25, min(0.85, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.1

    if (runif(1) < success_prob) {
      result$effects$domestic_support <- 0.05
      result$effects$international_narrative <- TRUE
      result$effects$message <- "Propaganda campaign shapes public opinion"
    } else {
      result$success <- FALSE
      result$effects$domestic_support <- 0.01  # Minimal effect
      result$effects$international_narrative <- FALSE
      # Check for backfire
      if (runif(1) < 0.3) {
        result$effects$domestic_support <- -0.02
        result$effects$credibility_damage <- 0.05
        result$effects$message <- "Propaganda campaign backfired - messaging seen as heavy-handed"
      } else {
        result$effects$message <- "Propaganda campaign failed to gain traction - audience skeptical"
      }
    }

  } else if (action == "share_intelligence") {
    # Sharing intel with allies - generally succeeds if allies trust you
    # Base 70% - depends on relationship
    base_prob <- 0.70

    # Check if sharing with ally
    is_ally <- (actor$faction == "small_power" && !is.null(target) &&
                target$faction %in% c("meridian")) ||
               (actor$faction == "major_power" && !is.null(target) &&
                target$faction == "valkoria")
    if (is_ally) {
      base_prob <- base_prob + 0.15
    }

    success_prob <- max(0.40, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.2

    if (runif(1) < success_prob) {
      result$effects$alliance_trust <- 0.1
      result$effects$coordination_improved <- TRUE
      result$effects$message <- "Intelligence shared successfully - ally coordination improved"
    } else {
      result$success <- FALSE
      result$effects$message <- "Intelligence sharing limited - trust issues or classification concerns"
    }

  } else if (action == "enhanced_intelligence_gathering") {
    # More intensive intel collection - higher reward, higher risk
    # Base 65% - more aggressive means more chance of problems
    base_prob <- 0.65

    if (!is.null(actor$information$access)) {
      base_prob <- base_prob + (actor$information$access - 0.5) * 0.25
    }

    success_prob <- max(0.30, min(0.85, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.5

    if (runif(1) < success_prob) {
      result$effects$intelligence_quality <- 0.15
      result$effects$strategic_insight <- TRUE
      result$effects$message <- "Enhanced intelligence gathering yields valuable insights"
    } else {
      result$success <- FALSE
      # Risk of detection on failure
      if (runif(1) < 0.4) {
        result$effects$detected <- TRUE
        result$effects$message <- "Enhanced intelligence gathering detected - diplomatic incident"
      } else {
        result$effects$message <- "Enhanced intelligence gathering produced limited results"
      }
    }

  } else if (action == "enhanced_surveillance") {
    # More comprehensive surveillance
    # Base 70% - technical challenges
    base_prob <- 0.70

    success_prob <- max(0.40, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.4

    if (runif(1) < success_prob) {
      result$effects$surveillance_coverage <- 0.12
      result$effects$early_warning <- TRUE
      result$effects$message <- "Enhanced surveillance established - monitoring improved"
    } else {
      result$success <- FALSE
      result$effects$surveillance_coverage <- 0.03
      result$effects$message <- "Enhanced surveillance faced technical difficulties"
    }

  } else if (action == "information_campaign") {
    # Broader information warfare
    # Base 60% - information space is contested
    base_prob <- 0.60

    success_prob <- max(0.30, min(0.85, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.3

    if (runif(1) < success_prob) {
      result$effects$narrative_influence <- 0.08
      result$effects$information_advantage <- TRUE
      result$effects$message <- "Information campaign reaches target audiences"
    } else {
      result$success <- FALSE
      result$effects$narrative_influence <- 0.01
      result$effects$message <- "Information campaign drowned out by competing narratives"
    }
  }

  return(list(result = result, state = state))
}

#' Execute an economic action
#'
#' @param action Action name
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @return List with results and updated state
execute_economic_action <- function(action, actor, target, state) {
  result <- list(
    action = action,
    actor = actor$name,
    target = if(!is.null(target)) target$name else NA,
    success = TRUE,
    effects = list()
  )

  crisis_level <- state$scenario_state$crisis_level

  if (action == "trade_agreement") {
    # Trade agreements between adversaries nearly impossible during war
    # Check relationship between parties
    is_adversary <- (actor$faction == "major_power" && !is.null(target) &&
                     target$faction %in% c("small_power", "meridian")) ||
                    (actor$faction == "small_power" && !is.null(target) &&
                     target$faction %in% c("major_power", "valkoria")) ||
                    (actor$faction %in% c("meridian", "small_power") && !is.null(target) &&
                     target$faction %in% c("major_power", "valkoria")) ||
                    (actor$faction %in% c("valkoria", "major_power") && !is.null(target) &&
                     target$faction %in% c("small_power", "meridian"))

    is_ally <- (actor$faction == "major_power" && !is.null(target) &&
                target$faction == "valkoria") ||
               (actor$faction == "small_power" && !is.null(target) &&
                target$faction == "meridian") ||
               (actor$faction == "valkoria" && !is.null(target) &&
                target$faction == "major_power") ||
               (actor$faction == "meridian" && !is.null(target) &&
                target$faction == "small_power")

    # Base probability depends heavily on relationship
    if (is_adversary) {
      base_prob <- 0.05  # Near impossible between enemies during conflict
    } else if (is_ally) {
      base_prob <- 0.70  # Allies usually cooperate
    } else {
      base_prob <- 0.35  # Neutral parties
    }

    # Crisis penalty
    if (crisis_level > 6) {
      base_prob <- base_prob - (crisis_level - 6) * 0.05
    }

    success_prob <- max(0.05, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      result$effects$gdp_growth_actor <- 0.02
      result$effects$gdp_growth_target <- 0.02
      result$effects$economic_interdependence <- 0.15
      result$effects$message <- "Trade agreement signed - economic ties strengthened"
    } else {
      result$success <- FALSE
      result$effects$gdp_growth_actor <- 0
      result$effects$gdp_growth_target <- 0
      if (is_adversary) {
        result$effects$message <- "Trade agreement impossible - parties are adversaries"
      } else {
        result$effects$message <- "Trade agreement negotiations collapsed - terms unacceptable"
      }
    }

  } else if (action == "economic_sanctions") {
    # Sanctions can be imposed but effectiveness varies
    # Base effectiveness by actor power
    if (actor$faction == "major_power") {
      base_severity <- 0.15
      effectiveness_prob <- 0.80  # Major power sanctions usually effective
    } else if (actor$faction %in% c("international_org", "meridian", "valkoria", "aurelia")) {
      base_severity <- 0.10
      effectiveness_prob <- 0.65  # External actors have moderate effectiveness
    } else {
      base_severity <- 0.02
      effectiveness_prob <- 0.40  # Small power sanctions often circumvented
    }

    # Target can mitigate through allies
    # If major power is target and has ally support, reduced effectiveness
    if (!is.null(target) && target$faction == "major_power") {
      effectiveness_prob <- effectiveness_prob - 0.15  # Harder to sanction major power
    }

    result$effects$success_probability <- round(effectiveness_prob * 100)

    if (runif(1) < effectiveness_prob) {
      severity <- base_severity
      state$scenario_state$sanctions_level <- min(1.0, state$scenario_state$sanctions_level + severity)

      result$effects$target_gdp_impact <- -severity
      result$effects$actor_cost <- -severity * 0.3  # Sanctions also hurt actor
      result$effects$sanctions_severity <- severity
      result$effects$message <- sprintf("Economic sanctions effective - target GDP -%.1f%%", severity * 100)
    } else {
      result$success <- FALSE
      # Partial effect even on failure
      severity <- base_severity * 0.3
      state$scenario_state$sanctions_level <- min(1.0, state$scenario_state$sanctions_level + severity * 0.5)

      result$effects$target_gdp_impact <- -severity
      result$effects$actor_cost <- -base_severity * 0.2
      result$effects$sanctions_severity <- severity
      result$effects$message <- "Sanctions imposed but largely circumvented through third parties"
    }

    # Increase crisis level regardless
    state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1)

  } else if (action == "financial_aid") {
    # Aid delivery can be blocked or fail to reach intended recipients
    # Base probability - usually succeeds but not guaranteed
    base_prob <- 0.65

    # Check if aid going through contested/occupied territory
    territory_controlled <- state$scenario_state$territory_controlled
    if (territory_controlled > 0.3) {
      base_prob <- base_prob - 0.20  # Harder to deliver aid in occupied areas
    }

    # High crisis makes logistics harder
    if (crisis_level > 7) {
      base_prob <- base_prob - (crisis_level - 7) * 0.08
    }

    # Allies more likely to successfully deliver aid to each other
    is_ally <- (actor$faction == "meridian" && !is.null(target) &&
                target$faction == "small_power") ||
               (actor$faction == "valkoria" && !is.null(target) &&
                target$faction == "major_power")
    if (is_ally) {
      base_prob <- base_prob + 0.15
    }

    success_prob <- max(0.15, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$actor_cost <- 2.0  # Cost incurred regardless

    if (runif(1) < success_prob) {
      result$effects$aid_amount_billions <- 2.0
      result$effects$target_stability <- 0.1
      result$effects$actor_influence <- 0.1
      result$effects$message <- "$2.0B financial aid delivered successfully"
    } else {
      result$success <- FALSE
      result$effects$aid_amount_billions <- 0.5  # Partial delivery
      result$effects$target_stability <- 0.02
      result$effects$actor_influence <- 0.03
      result$effects$message <- "Financial aid partially blocked or diverted - limited impact"
    }

  } else if (action == "resource_embargo") {
    # Embargoes require enforcement capability
    # Base effectiveness by actor
    if (actor$faction == "major_power") {
      base_prob <- 0.75
      base_severity <- 0.12
    } else if (actor$faction %in% c("international_org", "meridian", "valkoria")) {
      base_prob <- 0.55
      base_severity <- 0.08
    } else {
      base_prob <- 0.30  # Small powers struggle to enforce embargoes
      base_severity <- 0.04
    }

    # Naval/military capability affects enforcement
    if (actor$faction == "major_power" &&
        !is.null(state$faction_capabilities$major_power_military)) {
      if (state$faction_capabilities$major_power_military > 0.8) {
        base_prob <- base_prob + 0.10
      }
    }

    result$effects$success_probability <- round(base_prob * 100)

    if (runif(1) < base_prob) {
      result$effects$target_gdp_impact <- -base_severity
      result$effects$target_military_capability <- -0.05
      result$effects$message <- "Resource embargo enforced - supply lines disrupted"
    } else {
      result$success <- FALSE
      result$effects$target_gdp_impact <- -base_severity * 0.3
      result$effects$target_military_capability <- -0.01
      result$effects$message <- "Resource embargo porous - smuggling and third-party trade continue"
    }

    state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 2)

  } else if (action == "currency_manipulation") {
    # Economic warfare - requires financial sophistication
    base_prob <- 0.45  # Lowered from 0.6

    # Major financial powers more capable
    if (actor$faction == "major_power") {
      base_prob <- base_prob + 0.15
    }

    # Target's economic resilience matters
    if (!is.null(target) && target$faction == "major_power") {
      base_prob <- base_prob - 0.20  # Harder to manipulate major economy
    }

    success_prob <- max(0.10, min(0.70, base_prob))
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      result$effects$target_financial_instability <- 0.15
      result$effects$target_gdp_impact <- -0.08
      result$effects$message <- "Currency manipulation successful - financial turbulence"
    } else {
      result$success <- FALSE
      result$effects$target_financial_instability <- 0.02
      result$effects$target_gdp_impact <- -0.01
      result$effects$message <- "Currency manipulation failed - markets stabilized"
    }

  } else if (action == "cyber_theft") {
    # Steal economic/technical secrets - requires cyber capability
    base_prob <- actor$deception$capacity * 0.6  # Lowered from 0.8

    # Target's cyber defenses
    if (!is.null(target) && target$faction == "major_power") {
      base_prob <- base_prob - 0.15  # Better defenses
    }

    success_prob <- max(0.10, min(0.75, base_prob))
    result$effects$success_probability <- round(success_prob * 100)

    if (runif(1) < success_prob) {
      result$effects$economic_advantage <- 0.05
      result$effects$technology_stolen <- TRUE
      result$effects$message <- "Cyber theft successful - technological secrets obtained"
    } else {
      result$success <- FALSE
      # Detection risk on failure
      if (runif(1) < 0.6) {  # 60% chance of detection on failure
        result$effects$detected <- TRUE
        result$effects$diplomatic_crisis <- TRUE
        result$effects$trust_damage <- -0.2
        result$effects$message <- "Cyber theft detected - international incident"
      } else {
        result$effects$detected <- FALSE
        result$effects$message <- "Cyber theft failed - defenses held, operation undetected"
      }
    }

  } else if (action == "trade_restrictions") {
    # Imposing trade restrictions - can hurt both sides
    # Base 70% effectiveness
    base_prob <- 0.70

    success_prob <- max(0.40, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.4

    if (runif(1) < success_prob) {
      result$effects$target_trade_damage <- 0.08
      result$effects$actor_trade_cost <- 0.02
      result$effects$message <- "Trade restrictions implemented - target commerce disrupted"
    } else {
      result$success <- FALSE
      result$effects$target_trade_damage <- 0.02
      result$effects$message <- "Trade restrictions circumvented through third parties"
    }

  } else if (action == "targeted_sanctions") {
    # Sanctions against specific individuals/entities
    # Base 65% - targeted sanctions are precise but can be evaded
    base_prob <- 0.65

    success_prob <- max(0.35, min(0.85, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.3

    if (runif(1) < success_prob) {
      result$effects$elite_pressure <- 0.1
      result$effects$asset_freeze <- TRUE
      result$effects$message <- "Targeted sanctions imposed - key figures affected"
    } else {
      result$success <- FALSE
      result$effects$elite_pressure <- 0.02
      result$effects$message <- "Targeted sanctions evaded - assets moved offshore"
    }

  } else if (action == "asset_seizure") {
    # Seizing foreign assets - aggressive economic action
    # Base 75% if you have jurisdiction
    base_prob <- 0.75

    success_prob <- max(0.45, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.4

    if (runif(1) < success_prob) {
      result$effects$assets_seized_billions <- runif(1, 0.5, 3.0)
      result$effects$target_financial_damage <- 0.1
      result$effects$message <- sprintf("Asset seizure successful - $%.1fB frozen", result$effects$assets_seized_billions)
      # Increases crisis
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1.5)
    } else {
      result$success <- FALSE
      result$effects$message <- "Asset seizure blocked - legal challenges or assets relocated"
    }

  } else if (action == "strategic_stockpiling") {
    # Building reserves of critical materials
    # Base 80% - mostly internal action
    base_prob <- 0.80

    success_prob <- max(0.50, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.8

    if (runif(1) < success_prob) {
      result$effects$strategic_reserves <- 0.1
      result$effects$economic_resilience <- 0.05
      result$effects$message <- "Strategic stockpiling successful - reserves increased"
    } else {
      result$success <- FALSE
      result$effects$strategic_reserves <- 0.03
      result$effects$message <- "Stockpiling limited by supply constraints and high prices"
    }

  } else if (action == "war_bonds") {
    # Issuing war bonds to fund military efforts
    # Base 65% - depends on public confidence
    base_prob <- 0.65

    # Higher crisis can increase patriotic buying
    crisis_level <- if (!is.null(state$scenario_state$crisis_level)) {
      state$scenario_state$crisis_level
    } else {
      5
    }
    if (crisis_level > 7) {
      base_prob <- base_prob + 0.1  # Patriotic fervor
    }

    success_prob <- max(0.35, min(0.85, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.5

    if (runif(1) < success_prob) {
      result$effects$funds_raised_billions <- runif(1, 2, 8)
      result$effects$public_commitment <- 0.05
      result$effects$message <- sprintf("War bonds successful - $%.1fB raised", result$effects$funds_raised_billions)
    } else {
      result$success <- FALSE
      result$effects$funds_raised_billions <- runif(1, 0.5, 1.5)
      result$effects$message <- sprintf("War bond uptake weak - only $%.1fB raised", result$effects$funds_raised_billions)
    }
  }

  return(list(result = result, state = state))
}

#' Execute a military posture action
#'
#' @param action Action name
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @return List with results and updated state
execute_military_posture_action <- function(action, actor, target, state) {
  result <- list(
    action = action,
    actor = actor$name,
    target = if(!is.null(target)) target$name else NA,
    success = TRUE,
    effects = list()
  )

  # Get current GDP for resource constraints
  actor_gdp <- if (actor$faction == "major_power") {
    if (!is.null(state$faction_capabilities$major_power_gdp)) {
      state$faction_capabilities$major_power_gdp
    } else 100.0
  } else if (actor$faction == "small_power") {
    if (!is.null(state$faction_capabilities$small_power_gdp)) {
      state$faction_capabilities$small_power_gdp
    } else 30.0
  } else {
    50.0  # External actors
  }

  # Sanctions level affects military operations
  sanctions_penalty <- if (!is.null(state$scenario_state$sanctions_level)) {
    state$scenario_state$sanctions_level * 0.15
  } else {
    0
  }

  if (action == "military_buildup") {
    # Military buildup can fail due to supply chain issues, logistics, budget overruns
    # Base 80% success - major undertaking
    base_prob <- 0.80

    # Economic pressure reduces effectiveness
    base_prob <- base_prob - sanctions_penalty

    # Low GDP makes buildup harder
    if (actor_gdp < 40) {
      base_prob <- base_prob - 0.15
    }

    success_prob <- max(0.40, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 5.0

    if (runif(1) < success_prob) {
      buildup_amount <- 0.05

      # Update faction military strength
      if (actor$faction == "major_power") {
        if (is.null(state$faction_capabilities$major_power_military)) {
          state$faction_capabilities$major_power_military <- 1.0
        }
        state$faction_capabilities$major_power_military <-
          state$faction_capabilities$major_power_military + buildup_amount
      } else if (actor$faction == "small_power") {
        if (is.null(state$faction_capabilities$small_power_military)) {
          state$faction_capabilities$small_power_military <- 0.6
        }
        state$faction_capabilities$small_power_military <-
          state$faction_capabilities$small_power_military + buildup_amount
      }

      result$effects$military_strength_increase <- buildup_amount
      result$effects$message <- "Military buildup increases combat capability"

      # Increases tensions
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1)
    } else {
      result$success <- FALSE
      # Partial buildup on failure
      partial_amount <- 0.02
      if (actor$faction == "major_power") {
        if (is.null(state$faction_capabilities$major_power_military)) {
          state$faction_capabilities$major_power_military <- 1.0
        }
        state$faction_capabilities$major_power_military <-
          state$faction_capabilities$major_power_military + partial_amount
      } else if (actor$faction == "small_power") {
        if (is.null(state$faction_capabilities$small_power_military)) {
          state$faction_capabilities$small_power_military <- 0.6
        }
        state$faction_capabilities$small_power_military <-
          state$faction_capabilities$small_power_military + partial_amount
      }
      result$effects$military_strength_increase <- partial_amount
      result$effects$message <- "Military buildup hampered by supply chain issues - partial gains only"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 0.5)
    }

  } else if (action == "naval_deployment") {
    # Naval deployment can fail due to mechanical issues, weather, or operational problems
    # Base 85% success
    base_prob <- 0.85 - sanctions_penalty

    success_prob <- max(0.50, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 1.5

    if (runif(1) < success_prob) {
      result$effects$power_projection <- 0.1
      result$effects$message <- "Naval forces deployed to region"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1)
    } else {
      result$success <- FALSE
      result$effects$power_projection <- 0.03
      result$effects$message <- "Naval deployment delayed - mechanical issues and weather complications"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 0.3)
    }

  } else if (action == "air_patrols") {
    # Air patrols can fail due to weather, maintenance, or incidents
    # Base 85% success
    base_prob <- 0.85 - sanctions_penalty * 0.5

    success_prob <- max(0.55, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.8

    if (runif(1) < success_prob) {
      result$effects$air_superiority <- 0.05
      result$effects$message <- "Air patrols establish presence"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 0.5)
    } else {
      result$success <- FALSE
      result$effects$air_superiority <- 0.01
      # Check for incident
      if (runif(1) < 0.2) {
        result$effects$incident <- TRUE
        result$effects$message <- "Air patrol incident - aircraft lost to mechanical failure"
      } else {
        result$effects$message <- "Air patrols reduced due to maintenance and weather issues"
      }
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 0.2)
    }

  } else if (action == "troop_movements") {
    # Troop movements can fail due to logistics, detection, or coordination problems
    # Base 80% success
    base_prob <- 0.80 - sanctions_penalty

    success_prob <- max(0.45, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 2.0

    if (runif(1) < success_prob) {
      result$effects$readiness_increase <- 0.1
      result$effects$message <- "Troops moved to forward positions"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 2)
    } else {
      result$success <- FALSE
      result$effects$readiness_increase <- 0.03
      result$effects$message <- "Troop movements delayed by logistics problems - partial repositioning"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1)
    }

  } else if (action == "joint_exercises") {
    # Joint exercises can fail due to coordination issues or political problems
    # Base 75% success - requires multi-party coordination
    base_prob <- 0.75

    # International support affects ally willingness
    if (!is.null(state$scenario_state$international_support)) {
      if (actor$faction == "small_power") {
        # Defender benefits from high international support
        base_prob <- base_prob + (state$scenario_state$international_support - 0.5) * 0.2
      } else if (actor$faction == "major_power") {
        # Aggressor penalized by high international support (for defender)
        base_prob <- base_prob - (state$scenario_state$international_support - 0.5) * 0.15
      }
    }

    success_prob <- max(0.35, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 1.0

    if (runif(1) < success_prob) {
      result$effects$alliance_cohesion <- 0.1
      result$effects$military_coordination <- 0.05
      result$effects$message <- "Joint military exercises strengthen alliance"
    } else {
      result$success <- FALSE
      result$effects$alliance_cohesion <- 0.02
      result$effects$military_coordination <- 0.01
      result$effects$message <- "Joint exercises scaled back due to coordination difficulties"
    }

  } else if (action == "arms_development") {
    # Arms development can fail due to technical problems, budget issues
    # Base 60% success - R&D is inherently risky
    base_prob <- 0.60 - sanctions_penalty

    # Low GDP makes development harder
    if (actor_gdp < 50) {
      base_prob <- base_prob - 0.15
    }

    success_prob <- max(0.25, min(0.80, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 10.0

    if (runif(1) < success_prob) {
      result$effects$technological_edge <- 0.08
      result$effects$future_capability <- 0.15
      result$effects$message <- "Advanced weapons development achieves breakthrough"
    } else {
      result$success <- FALSE
      result$effects$technological_edge <- 0.02
      result$effects$future_capability <- 0.05
      result$effects$message <- "Arms development faces technical setbacks - progress slower than expected"
    }

  } else if (action == "defensive_fortification") {
    # Fortification can fail due to supply issues, terrain problems, or time constraints
    # Base 80% success
    base_prob <- 0.80 - sanctions_penalty

    success_prob <- max(0.45, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 3.0

    if (runif(1) < success_prob) {
      result$effects$defensive_strength <- 0.1
      result$effects$territory_hardened <- TRUE
      result$effects$message <- "Defensive fortifications completed - positions strengthened"
    } else {
      result$success <- FALSE
      result$effects$defensive_strength <- 0.03
      result$effects$territory_hardened <- FALSE
      result$effects$message <- "Fortification efforts delayed by supply shortages - partial progress only"
    }

  } else if (action == "defensive_reinforcements") {
    # Reinforcements can fail due to logistics or route interdiction
    # Base 75% success
    base_prob <- 0.75 - sanctions_penalty

    success_prob <- max(0.40, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 2.0

    if (runif(1) < success_prob) {
      result$effects$troop_increase <- 0.08
      result$effects$defensive_capability <- 0.1
      result$effects$message <- "Reinforcements arrived - defensive lines strengthened"
    } else {
      result$success <- FALSE
      result$effects$troop_increase <- 0.02
      result$effects$defensive_capability <- 0.03
      result$effects$message <- "Reinforcement convoy disrupted - only partial forces arrived"
    }

  } else if (action == "show_of_force") {
    # Show of force can fail if not impressive enough or goes wrong
    # Base 70% success - requires coordination
    base_prob <- 0.70

    success_prob <- max(0.40, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 1.0

    if (runif(1) < success_prob) {
      result$effects$deterrence <- 0.1
      result$effects$intimidation <- TRUE
      result$effects$message <- "Show of force demonstrates military capability"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1.5)
    } else {
      result$success <- FALSE
      result$effects$deterrence <- 0
      result$effects$intimidation <- FALSE
      # Check for embarrassing failure
      if (runif(1) < 0.3) {
        result$effects$embarrassment <- TRUE
        result$effects$message <- "Show of force backfired - equipment malfunction embarrasses military"
      } else {
        result$effects$message <- "Show of force underwhelming - failed to impress observers"
      }
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 0.5)
    }

  } else if (action == "military_exercises") {
    # Exercises can have accidents or go poorly
    # Base 80% success
    base_prob <- 0.80

    success_prob <- max(0.50, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 1.0

    if (runif(1) < success_prob) {
      result$effects$readiness <- 0.08
      result$effects$training_benefit <- TRUE
      result$effects$message <- "Military exercises improve readiness and coordination"
    } else {
      result$success <- FALSE
      result$effects$readiness <- 0.02
      result$effects$training_benefit <- FALSE
      # Check for accident
      if (runif(1) < 0.2) {
        result$effects$casualties <- rpois(1, 5)
        result$effects$message <- "Exercises marred by training accident - casualties sustained"
      } else {
        result$effects$message <- "Exercises revealed coordination problems - limited training value"
      }
    }

  } else if (action == "enhanced_patrols") {
    # Patrols can fail to cover territory or be ineffective
    # Base 80% success
    base_prob <- 0.80

    success_prob <- max(0.50, min(0.95, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.5

    if (runif(1) < success_prob) {
      result$effects$surveillance <- 0.1
      result$effects$border_security <- 0.08
      result$effects$message <- "Enhanced patrols increase area coverage and security"
    } else {
      result$success <- FALSE
      result$effects$surveillance <- 0.03
      result$effects$border_security <- 0.02
      result$effects$message <- "Patrol coverage gaps persist - insufficient resources"
    }

  } else if (action == "naval_patrols") {
    # Naval patrols can fail due to weather or mechanical issues
    # Base 80% success
    base_prob <- 0.80

    success_prob <- max(0.50, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.8

    if (runif(1) < success_prob) {
      result$effects$maritime_security <- 0.1
      result$effects$sea_control <- 0.05
      result$effects$message <- "Naval patrols establish maritime presence"
    } else {
      result$success <- FALSE
      result$effects$maritime_security <- 0.03
      result$effects$message <- "Naval patrols hampered by weather and mechanical problems"
    }

  } else if (action == "naval_demonstration") {
    # Naval demonstration can fail to impress or go wrong
    # Base 75% success
    base_prob <- 0.75

    success_prob <- max(0.45, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 1.5

    if (runif(1) < success_prob) {
      result$effects$naval_deterrence <- 0.1
      result$effects$power_projection <- 0.08
      result$effects$message <- "Naval demonstration projects power"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1)
    } else {
      result$success <- FALSE
      result$effects$naval_deterrence <- 0.02
      result$effects$message <- "Naval demonstration less impressive than planned"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 0.3)
    }

  } else if (action == "reconnaissance") {
    # Reconnaissance can fail to gather useful intel or be detected
    # Base 70% success
    base_prob <- 0.70

    # Actor's information access helps
    if (!is.null(actor$information$access)) {
      base_prob <- base_prob + (actor$information$access - 0.5) * 0.2
    }

    success_prob <- max(0.35, min(0.90, base_prob))
    result$effects$success_probability <- round(success_prob * 100)
    result$effects$cost_billions <- 0.3

    if (runif(1) < success_prob) {
      result$effects$intelligence_gained <- TRUE
      result$effects$tactical_awareness <- 0.1
      result$effects$message <- "Reconnaissance mission successful - enemy positions mapped"
    } else {
      result$success <- FALSE
      result$effects$intelligence_gained <- FALSE
      # Check if detected
      if (runif(1) < 0.4) {
        result$effects$detected <- TRUE
        result$effects$message <- "Reconnaissance detected - enemy alerted to our interest"
      } else {
        result$effects$message <- "Reconnaissance inconclusive - poor conditions obscured observation"
      }
    }
  }

  return(list(result = result, state = state))
}

#' Execute a covert operation
#'
#' @param action Action name
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @return List with results and updated state
execute_covert_action <- function(action, actor, target, state) {
  result <- list(
    action = action,
    actor = actor$name,
    target = if(!is.null(target)) target$name else NA,
    success = TRUE,
    effects = list(),
    covert = TRUE  # Mark as covert
  )

  # Covert operations have detection risk
  detection_prob <- 1 - actor$deception$capacity
  detected <- runif(1) < detection_prob

  if (action == "sabotage") {
    if (!detected) {
      result$effects$infrastructure_damage <- 0.15
      result$effects$economic_disruption <- 0.08
      result$effects$military_degradation <- 0.05
      result$effects$message <- "Sabotage operation successful - infrastructure damaged"
    } else {
      result$success <- FALSE
      result$effects$detected <- TRUE
      result$effects$diplomatic_crisis <- "major"
      result$effects$international_condemnation <- 0.3
      result$effects$message <- "Sabotage operation exposed - major diplomatic crisis"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 3)
    }
  } else if (action == "assassination_attempt") {
    # Extremely risky
    success_prob <- actor$deception$capacity * 0.3  # Low success rate

    if (runif(1) < success_prob && !detected) {
      result$effects$leadership_eliminated <- TRUE
      result$effects$target_chaos <- 0.5
      result$effects$government_instability <- 0.4
      result$effects$message <- "Assassination successful - target leadership eliminated"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 5)
    } else {
      result$success <- FALSE
      result$effects$detected <- TRUE
      result$effects$act_of_war <- TRUE
      result$effects$international_outrage <- 0.5
      result$effects$message <- "Assassination attempt failed and exposed - casus belli"
      state$scenario_state$crisis_level <- 10  # Maximum crisis
    }
  } else if (action == "regime_destabilization") {
    if (!detected) {
      result$effects$political_instability <- 0.2
      result$effects$opposition_strength <- 0.15
      result$effects$government_legitimacy <- -0.2
      result$effects$message <- "Destabilization campaign weakens regime"
    } else {
      result$success <- FALSE
      result$effects$detected <- TRUE
      result$effects$message <- "Destabilization efforts exposed"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 2)
    }
  } else if (action == "proxy_support") {
    # Supporting non-state actors
    result$effects$proxy_capability <- 0.2
    result$effects$indirect_pressure <- 0.15
    result$effects$cost_billions <- 1.0

    if (detected) {
      result$effects$plausible_deniability <- FALSE
      result$effects$message <- "Proxy support exposed - diplomatic fallout"
    } else {
      result$effects$plausible_deniability <- TRUE
      result$effects$message <- "Proxy forces strengthened"
    }
  } else if (action == "false_flag_operation") {
    # High risk, high reward
    if (!detected) {
      result$effects$enemy_blamed <- TRUE
      result$effects$international_support <- 0.2
      result$effects$justification_for_action <- TRUE
      result$effects$message <- "False flag operation successful - enemy blamed"
    } else {
      result$success <- FALSE
      result$effects$detected <- TRUE
      result$effects$credibility_destroyed <- TRUE
      result$effects$international_isolation <- 0.4
      result$effects$message <- "False flag exposed - catastrophic credibility loss"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 4)
    }
  } else if (action == "cyber_attack") {
    if (!detected) {
      result$effects$infrastructure_disruption <- 0.12
      result$effects$economic_damage <- 0.06
      result$effects$message <- "Cyber attack disrupts critical systems"
    } else {
      result$success <- FALSE
      result$effects$detected <- TRUE
      result$effects$attribution_confirmed <- TRUE
      result$effects$message <- "Cyber attack traced back - diplomatic incident"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 2)
    }

  } else if (action == "leadership_targeting") {
    # Targeting enemy leadership - extremely risky
    # Similar to assassination but broader (can include capture, compromise)
    success_prob <- actor$deception$capacity * 0.25  # Very low success rate

    if (runif(1) < success_prob && !detected) {
      result$effects$leadership_compromised <- TRUE
      result$effects$enemy_command_disruption <- 0.3
      result$effects$message <- "Leadership targeting operation successful - command structure disrupted"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 4)
    } else {
      result$success <- FALSE
      result$effects$detected <- TRUE
      result$effects$act_of_war <- TRUE
      result$effects$international_outrage <- 0.4
      result$effects$message <- "Leadership targeting attempt exposed - major diplomatic crisis"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 5)
    }

  } else if (action == "political_warfare") {
    # Undermining enemy through political means
    # Base success depends on deception capacity
    success_prob <- 0.4 + actor$deception$capacity * 0.3

    if (!detected && runif(1) < success_prob) {
      result$effects$political_instability <- 0.15
      result$effects$domestic_opposition <- 0.1
      result$effects$message <- "Political warfare campaign undermines enemy cohesion"
    } else if (detected) {
      result$success <- FALSE
      result$effects$detected <- TRUE
      result$effects$message <- "Political warfare operations exposed - credibility damaged"
      state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 1.5)
    } else {
      result$success <- FALSE
      result$effects$political_instability <- 0.03
      result$effects$message <- "Political warfare had limited effect - target society resilient"
    }

  } else if (action == "cyber_defense") {
    # Defensive cyber operations - protect own systems
    # Base 75% - defense is easier than offense
    base_prob <- 0.75

    if (!is.null(actor$deception$capacity)) {
      base_prob <- base_prob + actor$deception$capacity * 0.15
    }

    success_prob <- max(0.50, min(0.95, base_prob))
    # Note: cyber_defense doesn't use the detection mechanic the same way

    if (runif(1) < success_prob) {
      result$effects$cyber_resilience <- 0.15
      result$effects$threat_mitigation <- TRUE
      result$effects$message <- "Cyber defense strengthened - systems hardened"
    } else {
      result$success <- FALSE
      result$effects$cyber_resilience <- 0.05
      result$effects$message <- "Cyber defense improvements incomplete - vulnerabilities remain"
    }
    # Cyber defense doesn't trigger detection concerns
    detected <- FALSE
  }

  result$effects$detection_risk <- detection_prob
  result$effects$was_detected <- detected

  return(list(result = result, state = state))
}

#' Execute open conflict action (kinetic warfare)
#'
#' @param action Action name
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @return List with results and updated state
execute_conflict_action <- function(action, actor, target, state) {
  result <- list(
    action = action,
    actor = actor$name,
    target = if(!is.null(target)) target$name else NA,
    success = TRUE,
    effects = list(),
    warfare = TRUE
  )

  # Initialize military strengths if not present
  if (is.null(state$faction_capabilities$major_power_military)) {
    state$faction_capabilities$major_power_military <- 1.0
  }
  if (is.null(state$faction_capabilities$small_power_military)) {
    state$faction_capabilities$small_power_military <- 0.6
  }

  # Calculate force ratio AND incorporate military_balance
  if (actor$faction == "major_power") {
    attacker_strength <- state$faction_capabilities$major_power_military
    defender_strength <- state$faction_capabilities$small_power_military
  } else {
    attacker_strength <- state$faction_capabilities$small_power_military
    defender_strength <- state$faction_capabilities$major_power_military
  }

  force_ratio <- attacker_strength / defender_strength

  # REALISM: military_balance affects success probability

  # Negative = aggressor advantage, positive = defender advantage
  mil_balance <- state$scenario_state$military_balance
  balance_modifier <- if (actor$faction == "major_power") {
    -mil_balance * 0.15  # Aggressor benefits from negative balance
  } else {
    mil_balance * 0.15   # Defender benefits from positive balance
  }

  if (action == "border_incursion") {
    # Limited border operation - incorporate military balance
    base_prob <- force_ratio * 0.6
    success_prob <- min(0.85, max(0.15, base_prob + balance_modifier))

    if (runif(1) < success_prob) {
      territory_gain <- 0.02
      state$scenario_state$territory_controlled <-
        min(1.0, state$scenario_state$territory_controlled + territory_gain)

      result$effects$territory_seized <- territory_gain
      result$effects$casualties_attacker <- rpois(1, 50)
      result$effects$casualties_defender <- rpois(1, 120)
      result$effects$message <- sprintf("Border incursion successful - %.1f%% territory seized",
                                       territory_gain * 100)

      # ASYMMETRIC ATTRITION: Winner loses less
      attacker_attrition <- 0.98  # 2% loss on success
      defender_attrition <- 0.95  # 5% loss when defeated
    } else {
      result$success <- FALSE
      result$effects$repelled <- TRUE
      result$effects$casualties_attacker <- rpois(1, 200)
      result$effects$casualties_defender <- rpois(1, 80)
      result$effects$message <- "Border incursion repelled with losses"

      # ASYMMETRIC ATTRITION: Loser loses more
      attacker_attrition <- 0.94  # 6% loss on failure
      defender_attrition <- 0.98  # 2% loss when defending successfully
    }

    # Apply asymmetric attrition
    state$faction_capabilities[[paste0(actor$faction, "_military")]] <-
      state$faction_capabilities[[paste0(actor$faction, "_military")]] * attacker_attrition

    target_faction <- if (actor$faction == "major_power") "small_power" else "major_power"
    state$faction_capabilities[[paste0(target_faction, "_military")]] <-
      state$faction_capabilities[[paste0(target_faction, "_military")]] * defender_attrition

    state$scenario_state$crisis_level <- 10  # Full crisis

    # Update military_balance based on outcome (clamped to [-1, 1])
    if (result$success) {
      state$scenario_state$military_balance <-
        clamp_military_balance(state$scenario_state$military_balance - 0.08)
    } else {
      state$scenario_state$military_balance <-
        clamp_military_balance(state$scenario_state$military_balance + 0.05)
    }

  } else if (action == "limited_strike") {
    # Precision strike on military targets - uses intelligence access + military balance
    base_prob <- 0.5 + actor$information$access * 0.4
    success_prob <- min(0.9, max(0.2, base_prob + balance_modifier))

    if (runif(1) < success_prob) {
      result$effects$military_degradation <- 0.08
      result$effects$infrastructure_damage <- 0.05
      result$effects$casualties_military <- rpois(1, 80)
      result$effects$casualties_civilian <- rpois(1, 15)
      result$effects$message <- "Limited strike hits military targets"

      # Degrade defender capability
      if (actor$faction == "major_power") {
        state$faction_capabilities$small_power_military <-
          state$faction_capabilities$small_power_military * 0.92
      } else {
        state$faction_capabilities$major_power_military <-
          state$faction_capabilities$major_power_military * 0.95
      }

      # Successful strike shifts balance slightly (clamped to [-1, 1])
      state$scenario_state$military_balance <-
        clamp_military_balance(state$scenario_state$military_balance - 0.05)
    } else {
      result$success <- FALSE
      result$effects$missed_targets <- TRUE
      result$effects$casualties_civilian <- rpois(1, 50)
      result$effects$international_condemnation <- 0.3
      result$effects$message <- "Strike missed targets - civilian casualties"

      # Failed strike doesn't shift balance much but hurts international standing
      state$scenario_state$international_support <-
        max(0, state$scenario_state$international_support - 0.05)
    }

    state$scenario_state$crisis_level <- 10

  } else if (action == "full_scale_attack") {
    # Major military offensive - heavily influenced by force ratio AND military balance
    base_prob <- force_ratio * 0.5
    success_prob <- min(0.75, max(0.15, base_prob + balance_modifier * 1.5))

    if (runif(1) < success_prob) {
      # Territory gain scales with force ratio
      base_territory <- runif(1, 0.05, 0.15)
      territory_gain <- base_territory * min(1.5, force_ratio)
      state$scenario_state$territory_controlled <-
        min(1.0, state$scenario_state$territory_controlled + territory_gain)

      result$effects$territory_seized <- territory_gain
      result$effects$casualties_attacker <- rpois(1, 800)
      result$effects$casualties_defender <- rpois(1, 1500)
      result$effects$equipment_losses_attacker <- rpois(1, 50)
      result$effects$equipment_losses_defender <- rpois(1, 120)
      result$effects$message <- sprintf("Major offensive successful - %.1f%% territory captured",
                                       territory_gain * 100)

      # ASYMMETRIC ATTRITION: Winner loses less than the fixed 15%
      attacker_attrition <- 0.88  # 12% loss on success
      defender_attrition <- 0.70  # 30% loss when overwhelmed

      state$faction_capabilities[[paste0(actor$faction, "_military")]] <-
        state$faction_capabilities[[paste0(actor$faction, "_military")]] * attacker_attrition

      target_faction <- if (actor$faction == "major_power") "small_power" else "major_power"
      state$faction_capabilities[[paste0(target_faction, "_military")]] <-
        state$faction_capabilities[[paste0(target_faction, "_military")]] * defender_attrition

      state$scenario_state$military_balance <-
        clamp_military_balance(state$scenario_state$military_balance - 0.25)
    } else {
      result$success <- FALSE
      result$effects$offensive_stalled <- TRUE
      result$effects$casualties_attacker <- rpois(1, 1200)
      result$effects$casualties_defender <- rpois(1, 900)
      result$effects$message <- "Offensive stalled - heavy losses"

      # FAILED OFFENSIVE: Attacker loses heavily, defender holds
      state$faction_capabilities[[paste0(actor$faction, "_military")]] <-
        state$faction_capabilities[[paste0(actor$faction, "_military")]] * 0.75  # 25% loss

      target_faction <- if (actor$faction == "major_power") "small_power" else "major_power"
      state$faction_capabilities[[paste0(target_faction, "_military")]] <-
        state$faction_capabilities[[paste0(target_faction, "_military")]] * 0.92  # Only 8% loss

      # Failed offensive shifts balance toward defender (clamped to [-1, 1])
      state$scenario_state$military_balance <-
        clamp_military_balance(state$scenario_state$military_balance + 0.15)
    }

    state$scenario_state$crisis_level <- 10

  } else if (action == "occupation") {
    # Occupy captured territory
    occupation_cost <- 0.05  # Ongoing cost

    result$effects$occupation_established <- TRUE
    result$effects$ongoing_cost_billions_per_period <- 3.0
    result$effects$insurgency_risk <- 0.3
    result$effects$military_tied_down <- 0.2
    result$effects$message <- "Occupation forces deployed - ongoing costs"

    # Ties down military capacity
    state$faction_capabilities[[paste0(actor$faction, "_military")]] <-
      state$faction_capabilities[[paste0(actor$faction, "_military")]] * 0.90

  } else if (action == "blockade") {
    # Naval/economic blockade
    if (actor$faction == "major_power" || actor$faction == "external") {
      result$effects$blockade_effectiveness <- 0.7
      result$effects$target_economic_damage <- 0.20
      result$effects$target_resupply_blocked <- TRUE
      result$effects$cost_billions_per_period <- 1.5
      result$effects$message <- "Blockade established - strangling economy"

      # Degrades defender over time
      state$scenario_state$blockade_active <- TRUE
    } else {
      result$effects$blockade_effectiveness <- 0.3
      result$effects$message <- "Blockade attempted but limited effectiveness"
    }

    state$scenario_state$crisis_level <- 10

  } else if (action == "siege_warfare") {
    # Siege cities
    result$effects$city_besieged <- TRUE
    result$effects$humanitarian_crisis <- 0.5
    result$effects$international_condemnation <- 0.4
    result$effects$casualties_civilian <- rpois(1, 500)
    result$effects$message <- "Siege warfare - major humanitarian crisis"

    state$scenario_state$crisis_level <- 10
  }

  return(list(result = result, state = state))
}

#' Execute WMD action
#'
#' @param action Action name
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @return List with results and updated state
execute_wmd_action <- function(action, actor, target, state) {
  result <- list(
    action = action,
    actor = actor$name,
    target = if(!is.null(target)) target$name else NA,
    success = TRUE,
    effects = list(),
    wmd = TRUE
  )

  if (action == "nuclear_development") {
    # Develop nuclear capability
    result$effects$nuclear_capability <- 0.3  # Progress toward weapons
    result$effects$cost_billions <- 15.0
    result$effects$international_sanctions_risk <- 0.6
    result$effects$message <- "Nuclear weapons development program initiated"

    state$scenario_state$crisis_level <- min(10, state$scenario_state$crisis_level + 3)

  } else if (action == "chemical_weapons") {
    # Develop chemical weapons
    result$effects$chemical_capability <- 0.5
    result$effects$cost_billions <- 2.0
    result$effects$international_condemnation <- 0.4
    result$effects$message <- "Chemical weapons program active"

  } else if (action == "biological_program") {
    # Biological weapons
    result$effects$biological_capability <- 0.4
    result$effects$cost_billions <- 5.0
    result$effects$international_isolation_risk <- 0.5
    result$effects$message <- "Biological weapons research underway"

  } else if (action == "tactical_nuclear_use") {
    # Use tactical nuke - EXTREME
    result$effects$nuclear_threshold_crossed <- TRUE
    result$effects$casualties <- rpois(1, 5000)
    result$effects$territory_destroyed <- 0.02
    result$effects$radiation_contamination <- TRUE
    result$effects$international_isolation <- 1.0
    result$effects$retaliation_probability <- 0.8
    result$effects$message <- "TACTICAL NUCLEAR WEAPON USED - INTERNATIONAL CRISIS"

    state$scenario_state$nuclear_used <- TRUE
    state$scenario_state$crisis_level <- 10

    # Massive international response
    state$scenario_state$sanctions_level <- 1.0  # Maximum sanctions

  } else if (action == "strategic_nuclear_strike") {
    # Strategic nuclear exchange - CATASTROPHIC
    result$effects$nuclear_war <- TRUE
    result$effects$civilization_ending <- TRUE
    result$effects$casualties_millions <- runif(1, 50, 200)
    result$effects$message <- "STRATEGIC NUCLEAR EXCHANGE - SIMULATION ENDS"

    state$simulation_ended <- TRUE
    state$end_reason <- "nuclear_war"
  }

  return(list(result = result, state = state))
}

#' Main action execution dispatcher
#'
#' @param action Action name
#' @param actor Agent executing action
#' @param target Target agent (if applicable)
#' @param state Current simulation state
#' @return List with results and updated state
execute_action <- function(action, actor, target = NULL, state) {
  # Determine action category
  diplomatic_actions <- c("diplomatic_visit", "peace_talks", "trade_negotiation",
                         "cultural_exchange", "humanitarian_aid", "mediation_offer",
                         "coalition_building", "backchannel_negotiations", "formal_peace_talks",
                         "prisoner_exchange", "humanitarian_corridors", "public_diplomatic_initiative",
                         "formal_multilateral_engagement", "international_observers")

  intelligence_actions <- c("intelligence_gathering", "surveillance_operation",
                           "counterintelligence", "spread_disinformation", "propaganda_campaign",
                           "share_intelligence", "enhanced_intelligence_gathering",
                           "enhanced_surveillance", "information_campaign")

  economic_actions <- c("trade_agreement", "economic_sanctions", "financial_aid",
                       "resource_embargo", "currency_manipulation", "cyber_theft",
                       "trade_restrictions", "targeted_sanctions", "asset_seizure",
                       "strategic_stockpiling", "war_bonds")

  military_posture_actions <- c("military_buildup", "naval_deployment", "air_patrols",
                                "troop_movements", "joint_exercises", "arms_development",
                                "defensive_fortification", "defensive_reinforcements",
                                "show_of_force", "military_exercises", "enhanced_patrols",
                                "naval_patrols", "naval_demonstration", "reconnaissance")

  covert_actions <- c("sabotage", "assassination_attempt", "regime_destabilization",
                     "proxy_support", "false_flag_operation", "cyber_attack",
                     "leadership_targeting", "political_warfare", "cyber_defense")

  conflict_actions <- c("border_incursion", "limited_strike", "full_scale_attack",
                       "occupation", "blockade", "siege_warfare")

  wmd_actions <- c("nuclear_development", "chemical_weapons", "biological_program",
                  "tactical_nuclear_use", "strategic_nuclear_strike")

  # Dispatch to appropriate handler
  if (action %in% diplomatic_actions) {
    return(execute_diplomatic_action(action, actor, target, state))
  } else if (action %in% intelligence_actions) {
    return(execute_intelligence_action(action, actor, target, state))
  } else if (action %in% economic_actions) {
    return(execute_economic_action(action, actor, target, state))
  } else if (action %in% military_posture_actions) {
    return(execute_military_posture_action(action, actor, target, state))
  } else if (action %in% covert_actions) {
    return(execute_covert_action(action, actor, target, state))
  } else if (action %in% conflict_actions) {
    return(execute_conflict_action(action, actor, target, state))
  } else if (action %in% wmd_actions) {
    return(execute_wmd_action(action, actor, target, state))
  } else {
    # Unknown action
    return(list(
      result = list(
        action = action,
        actor = actor$name,
        success = FALSE,
        effects = list(error = "Unknown action type")
      ),
      state = state
    ))
  }
}
