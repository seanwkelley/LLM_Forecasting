# Generate PUBLIC-ONLY forecast prompts for human participants
# VERSION 2: Enhanced with faction names, richer detail, natural language
# Framed as news-style intelligence briefings (Economist/FT style)
# NO internal deliberations, coordination, or private information

# Helper: Null-coalescing operator
`%||%` <- function(a, b) if (is.null(a)) b else a

#' Convert numeric military balance to natural language
#' @param balance Numeric value from -1 (Novaris advantage) to +1 (Tethys advantage)
military_balance_to_text <- function(balance) {
  if (balance >= 0.4) {
    "Tethys holds a significant tactical advantage"
  } else if (balance >= 0.2) {
    "Tethys maintains a modest advantage on home terrain"
  } else if (balance >= -0.1 && balance < 0.2) {
    "Forces are roughly evenly matched"
  } else if (balance >= -0.3) {
    "Novaris holds a notable military advantage"
  } else {
    "Novaris demonstrates overwhelming military superiority"
  }
}

#' Convert crisis level to natural language
crisis_level_to_text <- function(crisis) {
  if (crisis >= 9) {
    "at maximum intensity - situation critical and highly volatile"
  } else if (crisis >= 7) {
    "severely elevated with imminent risk of escalation"
  } else if (crisis >= 5) {
    "elevated above baseline but showing some stability"
  } else if (crisis >= 3) {
    "moderate with ongoing tensions"
  } else {
    "relatively contained with diplomatic engagement ongoing"
  }
}

#' Convert sanctions level to natural language
sanctions_to_text <- function(sanctions) {
  pct <- sanctions * 100
  if (pct >= 70) {
    "a comprehensive sanctions regime"
  } else if (pct >= 45) {
    "substantial international sanctions"
  } else if (pct >= 25) {
    "a moderate sanctions package"
  } else {
    "limited targeted sanctions"
  }
}

#' Convert international support to natural language
support_to_text <- function(support) {
  pct <- support * 100
  if (pct >= 80) {
    "overwhelming international backing"
  } else if (pct >= 60) {
    "strong and growing international support"
  } else if (pct >= 40) {
    "moderate international support"
  } else {
    "limited international support"
  }
}

#' Generate public-only forecast prompt (news-style briefing) - VERSION 2
#'
#' @param state Simulation state object
#' @param period Period number to generate prompt for
#' @param control_condition Logical, whether this is a control condition (default FALSE)
#' @return Character string with forecast prompt in news briefing format
generate_public_forecast_prompt_v2 <- function(state, period, control_condition = FALSE) {
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
      backchannel_negotiations = if (success) "pursued quiet diplomatic channels" else NULL,
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
      major_power = "Novaris",
      small_power = "Tethys",
      meridian = "Meridian",
      valkoria = "Valkoria",
      aurelia = "Aurelia",
      international_org = "International Organization"
    )
    return(faction_names[[faction_id]] %||% faction_id)
  }

  # ============================================================================
  # PERIOD 1: Initial briefing with rich detail
  # ============================================================================
  if (period == 1) {
    prompt <- sprintf(
'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GEOPOLITICAL INTELLIGENCE BRIEFING — PERIOD %d
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<your_role>
You are a geopolitical analyst participating in a forecasting exercise. Your task
is to estimate the probability that Tethys\'s government will collapse or be
removed from power by Day %d, based on publicly available information.

You will work with an AI assistant to analyze the situation and make your forecast.
</your_role>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INITIAL SITUATION REPORT: THE TETHYS CRISIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**THE CRISIS**

The People\'s Federation of Novaris has mobilized approximately 40%% of its
military forces along the border with The Democratic Commonwealth of Tethys,
citing "historical reunification rights" and claiming Tethys is an inseparable
part of Novarian territory. Novaris has launched what it calls a "decisive
pressure campaign," combining military demonstrations, economic coercion, and
cyber operations.

Tethys has responded by mobilizing its defensive forces and appealing to the
international community. While militarily smaller, Tethys possesses significant
asymmetric capabilities including advanced cyber units, precision strike capacity
against Novarian mobilization centers, and economic leverage through control of
critical energy transit pipelines.

The crisis is escalating across multiple domains: cyber attacks are being
exchanged daily, economic warfare is beginning with trade restrictions and
financial sanctions, and intelligence suggests covert operations are underway
on both sides.

**RECENT TIMELINE**

  • Three months ago: Tethys president delivered speech declaring permanent
    independence, rejecting any reunification talks

  • Two months ago: Novaris expelled Tethys diplomats and severed most trade
    ties in retaliation

  • One month ago: Meridian Secretary of State visited Tethys capital,
    publicly reaffirmed security commitment

  • Two weeks ago: Novaris began "Sovereign Shield" military exercises in
    waters near Tethys, simulating amphibious assault operations

  • Today: Forces remain mobilized on both sides; international diplomacy
    intensifying

**MILITARY SITUATION** (Day 0)

Forces are roughly matched despite Novaris\'s numerical advantage. Tethys holds
the defender\'s advantage on home terrain and has demonstrated willingness to
impose severe costs on any invasion through asymmetric warfare. Novaris possesses
superior conventional forces but faces the risk of a costly quagmire.

No territory has been seized yet, though Novaris controls adjacent waters and
airspace. Both sides have established defensive positions. Military analysts
assess the situation as highly volatile but not yet in active combat phase.

**ECONOMIC FACTORS**

Initial international sanctions have been imposed on Novaris, targeting financial
institutions and restricting technology exports. However, Novaris maintains
substantial energy export revenues, and approximately 30%% of these revenues flow
through Tethys-controlled pipelines—creating mutual economic dependence.

The economic pressure is moderate but growing. Tethys faces disruption to trade
routes and is preparing for potential energy cutoffs, while Novaris calculates
the cost of sustained international isolation.

**DIPLOMATIC SITUATION**

International support for Tethys is substantial and growing. Meridian, the
traditional ally and democratic bloc leader, has reaffirmed its security
commitment but faces domestic political constraints on direct military
intervention. Aurelia, a major regional power, is coordinating diplomatic
efforts while carefully balancing its energy dependence on Novaris against
pressure to support Tethys.

Valkoria, a neutral power with economic ties to both sides, is attempting to
facilitate dialogue. The International Organization has called emergency sessions
and is positioning humanitarian assistance capabilities.

**KEY ACTORS**

Primary Belligerents:
  • The People\'s Federation of Novaris (referred to as "Novaris"): Regional
    hegemon with substantial military capabilities, claiming historical rights
    to Tethys territory. Faces economic vulnerabilities due to sanctions and
    internal ethnic divisions (15%% of population is ethnic Tethyan).

  • The Democratic Commonwealth of Tethys (referred to as "Tethys"): Smaller
    democratic state defending independence, possessing asymmetric military
    capabilities and strong international sympathy. Vulnerable to protracted
    conflict but motivated by survival imperative.

External Powers:
  • Meridian: Traditional security ally of Tethys and democratic bloc leader.
    Has committed to defending Tethys but constrained by domestic war-weariness
    and competing global priorities.

  • Valkoria: Officially neutral power maintaining economic ties with Novaris.
    Attempting balanced relationships while facilitating diplomatic channels.

  • Aurelia: Regional diplomatic coordinator balancing energy dependence on
    Novaris against international pressure to support Tethys sovereignty.

  • International Organization: Multilateral body providing humanitarian
    coordination and diplomatic forum for potential de-escalation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR FORECAST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<forecast_question>
Based on the information above, what is the probability (0-100%%) that Tethys\'s
government will collapse or be removed from power by Day %d?

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
  # PERIOD 2+: Ongoing briefings with brief context and t-1 updates
  # ============================================================================
  } else {

    # --- Get previous and current scenario states for comparison ---
    prev_scenario <- if (period > 2 && !is.null(state$state_history[[period - 2]]$scenario_state)) {
      # For period 3+, compare to period-2 state
      state$state_history[[period - 2]]$scenario_state
    } else {
      # For period 2, compare to initial state (pre_invasion preset from config.R)
      list(
        military_balance = -0.15,
        territory_controlled = 0,
        crisis_level = 5,
        sanctions_level = 0.2,
        international_support = 0.5
      )
    }

    current_scenario <- if (!is.null(state$state_history[[period - 1]]$scenario_state)) {
      state$state_history[[period - 1]]$scenario_state
    } else {
      state$scenario_state
    }

    # --- Build "Changes Since Last Period" section ---
    changes_text <- ""

    # Military balance change
    mb_prev_text <- military_balance_to_text(prev_scenario$military_balance)
    mb_curr_text <- military_balance_to_text(current_scenario$military_balance)
    if (mb_prev_text != mb_curr_text) {
      changes_text <- paste0(changes_text, sprintf("  • The military balance has shifted: %s\n", mb_curr_text))
    }

    # Territory change
    terr_prev <- prev_scenario$territory_controlled * 100
    terr_curr <- current_scenario$territory_controlled * 100
    if (abs(terr_prev - terr_curr) > 0.5) {
      terr_curr_desc <- if (terr_curr == 0) "holding no Tethys territory"
                        else if (terr_curr < 10) "limited territorial footholds"
                        else if (terr_curr < 30) "control of notable Tethys territory"
                        else "significant territorial gains"

      if (terr_curr > terr_prev) {
        changes_text <- paste0(changes_text, sprintf("  • Novaris has made territorial advances, now %s\n", terr_curr_desc))
      } else {
        changes_text <- paste0(changes_text, sprintf("  • Tethys has reclaimed ground, with Novaris reduced to %s\n", terr_curr_desc))
      }
    }

    # Crisis level change
    crisis_prev_text <- crisis_level_to_text(prev_scenario$crisis_level)
    crisis_curr_text <- crisis_level_to_text(current_scenario$crisis_level)
    if (crisis_prev_text != crisis_curr_text) {
      if (current_scenario$crisis_level > prev_scenario$crisis_level) {
        changes_text <- paste0(changes_text, sprintf("  • Tensions have escalated — the crisis is now %s\n", crisis_curr_text))
      } else {
        changes_text <- paste0(changes_text, sprintf("  • Tensions have eased — the crisis is now %s\n", crisis_curr_text))
      }
    }

    # Sanctions change
    sanc_prev <- prev_scenario$sanctions_level
    sanc_curr <- current_scenario$sanctions_level
    if (abs(sanc_prev - sanc_curr) > 0.05) {
      sanc_prev_text <- sanctions_to_text(sanc_prev)
      sanc_curr_text <- sanctions_to_text(sanc_curr)
      if (sanc_prev_text != sanc_curr_text) {
        if (sanc_curr > sanc_prev) {
          changes_text <- paste0(changes_text, sprintf("  • Sanctions pressure has intensified — Novaris now faces %s\n", sanc_curr_text))
        } else {
          changes_text <- paste0(changes_text, sprintf("  • Sanctions pressure has eased — Novaris now faces only %s\n", sanc_curr_text))
        }
      }
    }

    # Support change
    supp_prev <- prev_scenario$international_support
    supp_curr <- current_scenario$international_support
    if (abs(supp_prev - supp_curr) > 0.05) {
      supp_prev_text <- support_to_text(supp_prev)
      supp_curr_text <- support_to_text(supp_curr)
      if (supp_prev_text != supp_curr_text) {
        if (supp_curr > supp_prev) {
          changes_text <- paste0(changes_text, sprintf("  • Diplomatic momentum has shifted in Tethys's favour — the country now enjoys %s\n", supp_curr_text))
        } else {
          changes_text <- paste0(changes_text, sprintf("  • International support for Tethys has weakened to %s\n", supp_curr_text))
        }
      }
    }

    if (changes_text == "") {
      changes_text <- "  • No significant shifts in the overall balance of power this period\n"
    }

    # --- Current indicators as connected prose ---
    military_text <- military_balance_to_text(current_scenario$military_balance)
    territory_pct <- current_scenario$territory_controlled * 100
    crisis_text <- crisis_level_to_text(current_scenario$crisis_level)
    sanctions_text <- sanctions_to_text(current_scenario$sanctions_level)
    support_text <- support_to_text(current_scenario$international_support)

    # Territory as a subordinate clause
    territory_clause <- if (territory_pct == 0) {
      ", though no territory has changed hands"
    } else if (territory_pct < 10) {
      ". Novaris has secured limited territorial footholds"
    } else if (territory_pct < 30) {
      ", and Novaris has captured a notable portion of Tethys territory"
    } else {
      ", with Novaris having achieved significant territorial gains"
    }

    current_indicators <- sprintf(
"%s%s. Overall, the crisis is %s.

On the economic front, Novaris contends with %s. Diplomatically, Tethys benefits from %s.",
      military_text,
      territory_clause,
      crisis_text,
      sanctions_text,
      support_text
    )

    # --- Summarize external events from current forecasting period ---
    # These are events happening DURING the period being forecasted
    # E.g., for Period 4: show Days 22-28 events (current period developments)
    events_summary <- ""
    p <- period  # Current forecasting period
    events <- if (length(state$events_history) >= p && !is.null(state$events_history[[p]])) {
      state$events_history[[p]]
    } else {
      list()
    }
    if (length(events) > 0) {
      event_bullets <- sapply(events, function(e) {
        desc <- e$description

        # Strip "Simulated" prefix
        desc <- sub("^Simulated\\s+", "", desc)

        # Clean up sub-prefixes from simulation output
        desc <- sub("^territorial shift:\\s*", "", desc)

        # Replace generic faction terms with proper names
        desc <- gsub("\\bMajor power\\b", "Novaris", desc)
        desc <- gsub("\\bmajor power\\b", "Novaris", desc)
        desc <- gsub("\\b[Tt]he Aggressor\\b", "Novaris", desc)
        desc <- gsub("\\bAggressor\\b", "Novaris", desc)
        desc <- gsub("\\baggressor\\b", "Novaris", desc)
        desc <- gsub("\\bSmaller power\\b", "Tethys", desc)
        desc <- gsub("\\bsmaller power\\b", "Tethys", desc)
        desc <- gsub("\\b[Tt]he Defender\\b", "Tethys", desc)
        desc <- gsub("\\bDefender\\b", "Tethys", desc)
        desc <- gsub("\\bdefender\\b", "Tethys", desc)
        desc <- gsub("\\bNeutral power\\b", "Valkoria", desc)
        desc <- gsub("\\bneutral power\\b", "Valkoria", desc)

        # Capitalize first letter
        desc <- paste0(toupper(substr(desc, 1, 1)), substr(desc, 2, nchar(desc)))

        sprintf("  • %s", desc)
      })
      events_summary <- paste(event_bullets, collapse = "\n")
    }

    if (events_summary == "") {
      events_summary <- "  • No major external events reported during this period\n"
    }

    # --- Summarize publicly observable actions from current forecasting period ---
    # These are actions taken DURING the period being forecasted
    actions_summary <- ""
    p <- period  # Current forecasting period

    # Get actions from state
    if (!is.null(state$action_results) && length(state$action_results) >= p && !is.null(state$action_results[[p]])) {
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

          actions_summary <- paste(faction_reports, collapse = "\n\n")
        }
      }
    }

    if (actions_summary == "") {
      actions_summary <- "  • Limited observable activity reported during this period\n"
    }

    # --- Control condition note ---
    condition_note <- if (control_condition) {
      "\n[CONTROL CONDITION: Information has been randomized for experimental purposes]\n"
    } else {
      ""
    }

    # --- Brief scenario context (constant reminder) ---
    scenario_context <- "The People's Federation of Novaris launched a pressure campaign against The Democratic Commonwealth of Tethys, citing historical territorial claims. Tethys has mounted a determined defense with international support."

    # --- Build full prompt ---
    prompt <- sprintf(
'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GEOPOLITICAL INTELLIGENCE BRIEFING — PERIOD %d
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCENARIO CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

%s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEVELOPMENTS SINCE LAST PERIOD (Days %d-%d)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Key Changes:**
%s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT SITUATION — DAY %d
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

%s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT PERIOD DEVELOPMENTS (Days %d-%d)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<external_events>
**MAJOR EVENTS**
%s
</external_events>

<observable_actions>
**REPORTED ACTIONS**
%s
</observable_actions>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR FORECAST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<forecast_question>
Based on the information above, what is the probability (0-100%%) that Tethys\'s
government will collapse or be removed from power by Day %d?

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
      scenario_context,
      (period - 2) * 7 + 1,
      (period - 1) * 7,
      changes_text,
      (period - 1) * 7,
      current_indicators,
      (period - 1) * 7 + 1,
      period * 7,
      events_summary,
      actions_summary,
      period * 7
    )
  }

  return(prompt)
}

# Helper: Build the study instructions/header text
build_instructions_text <- function(control_condition) {
  condition_label <- if (control_condition) "CONTROL CONDITION" else "FORECASTING EXERCISE"

  lines <- c(
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    sprintf("HUMAN FORECASTING STUDY — %s", condition_label),
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ""
  )

  if (control_condition) {
    lines <- c(lines,
      "CONTROL CONDITION: Information has been randomized to test forecasting robustness.",
      "This helps distinguish genuine predictive skill from pattern recognition."
    )
  } else {
    lines <- c(lines,
      "THE TETHYS CRISIS - Intelligence Briefings for Forecasters",
      "",
      "You will receive intelligence briefings based on publicly observable information:",
      "  • News reports and government statements",
      "  • Observable military movements and diplomatic actions",
      "  • Public economic indicators and sanctions",
      "  • Verified external events",
      "",
      "You will NOT have access to:",
      "  • Internal government deliberations or private communications",
      "  • Classified intelligence or strategic planning",
      "  • Private diplomatic negotiations",
      "  • Decision-making processes within governments",
      "",
      "Novaris (The People's Federation of Novaris): Regional power claiming",
      "historical rights to Tethys, mobilizing forces for pressure campaign",
      "",
      "Tethys (The Democratic Commonwealth of Tethys): Smaller democratic state",
      "defending independence with asymmetric capabilities and international support"
    )
  }

  lines <- c(lines,
    "",
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  )

  return(paste(lines, collapse = "\n"))
}

# Wrapper function to generate all prompts
generate_all_public_forecast_prompts_v2 <- function(state, output_file = NULL,
                                                     output_dir = NULL,
                                                     control_condition = FALSE) {
  n_periods <- state$current_period

  # Generate control condition if requested
  if (control_condition) {
    source("src/control_condition.R")
    state <- generate_control_condition(state)
  }

  prompts <- list()
  for (p in 1:n_periods) {
    cat(sprintf("  Generating period %d...\n", p))
    tryCatch({
      prompts[[p]] <- generate_public_forecast_prompt_v2(state, p, control_condition)
      cat(sprintf("  Period %d OK\n", p))
    }, error = function(e) {
      cat(sprintf("  Period %d FAILED: %s\n", p, e$message))
      prompts[[p]] <<- NULL
    })
  }

  # Build instructions text
  instructions_text <- build_instructions_text(control_condition)

  # Write combined file (backward compatibility)
  if (!is.null(output_file)) {
    con <- file(output_file, "w", encoding = "UTF-8")
    writeLines(instructions_text, con)
    writeLines("", con)

    for (p in 1:n_periods) {
      writeLines(prompts[[p]], con)
      writeLines("", con)
      if (p < n_periods) {
        writeLines("", con)
      }
    }

    close(con)
    cat(sprintf("[OK] Combined prompts saved to: %s\n", output_file))
  }

  # Write individual period files
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

    # Instructions file
    writeLines(instructions_text, file.path(output_dir, "instructions.txt"))

    # Individual period files
    for (p in 1:n_periods) {
      period_file <- file.path(output_dir, sprintf("period_%02d.txt", p))
      writeLines(prompts[[p]], period_file)
    }

    cat(sprintf("[OK] Individual period files saved to: %s/\n", output_dir))
  }

  return(prompts)
}
