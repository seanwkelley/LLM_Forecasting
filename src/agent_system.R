# Agent system - handles agent state and LLM interactions

library(httr)
library(jsonlite)

#' Create an agent object with full persona
#'
#' @param agent_config List containing agent configuration
#' @return Agent object with state tracking
create_agent <- function(agent_config) {
  agent <- agent_config
  agent$state <- list(
    current_position = list(),
    memory = list(),
    recent_interactions = list()
  )
  class(agent) <- c("wargame_agent", "list")
  return(agent)
}

#' Generate system prompt for an agent based on their full persona
#'
#' @param agent Agent object
#' @param scenario_context Current scenario state
#' @return Character string with system prompt
generate_agent_prompt <- function(agent, scenario_context) {
  # Strategic orientation description
  hawk_dove_desc <- if (agent$hawk_dove > 0.8) {
    "ULTRA-HAWK: You strongly favor military solutions and view compromise as weakness. You push for aggressive action."
  } else if (agent$hawk_dove > 0.6) {
    "HAWK: You prefer assertive actions and are skeptical of negotiations. Military strength is paramount."
  } else if (agent$hawk_dove > 0.4) {
    "MODERATE: You balance military readiness with diplomatic options. Context determines approach."
  } else if (agent$hawk_dove > 0.2) {
    "DOVE: You prefer diplomatic solutions and warn against escalation risks. Negotiation first."
  } else {
    "ULTRA-DOVE: You strongly oppose military action and push hard for immediate negotiations, even with concessions."
  }

  # Policy adherence description
  policy_desc <- if (agent$policy_adherence > 0.8) {
    "LOYALIST: You closely follow official policy and defend leadership decisions."
  } else if (agent$policy_adherence > 0.5) {
    "PRAGMATIST: You support policy but raise concerns when you see risks."
  } else {
    "INDEPENDENT: You frequently challenge official policy and advocate for alternative approaches."
  }

  # Objective alignment description
  objective_desc <- if (agent$objective_alignment > 0.8) {
    "TRUE BELIEVER: Deeply committed to faction's objectives - victory or survival at high cost."
  } else if (agent$objective_alignment > 0.5) {
    "CONDITIONAL SUPPORTER: Supports goals but questions whether current strategy achieves them."
  } else {
    "SKEPTIC: Has serious doubts about the strategic direction and may advocate for major changes."
  }

  # Worldview description (from integrated system)
  worldview <- if (!is.null(agent$worldview)) agent$worldview else "pragmatic_technocrat"
  worldview_desc <- switch(worldview,
    "realist" = "REALIST WORLDVIEW: You see international politics as zero-sum power competition. States act in self-interest. Military strength and credible threats matter most. Institutions are tools of the powerful.",
    "liberal_institutionalist" = "LIBERAL INSTITUTIONALIST WORLDVIEW: You believe in international cooperation, rules-based order, and institutions. Diplomacy and economic interdependence can prevent conflict. Reputation and norms matter.",
    "nationalist_populist" = "NATIONALIST WORLDVIEW: National honor, sovereignty, and strength above all. Foreign threats are existential. Compromise is betrayal. The people demand resolve.",
    "pragmatic_technocrat" = "TECHNOCRATIC WORLDVIEW: You focus on costs, benefits, and feasibility. Data and analysis over ideology. What works matters more than what sounds good.",
    "constructivist" = "CONSTRUCTIVIST WORLDVIEW: Identities and relationships shape interests. How we frame the conflict matters. Narratives can change outcomes. Dialogue builds understanding.",
    "revolutionary_revisionist" = "REVISIONIST WORLDVIEW: The current order is unjust and must be challenged. Bold action changes facts on the ground. History favors the decisive.",
    "PRAGMATIC WORLDVIEW: You assess situations based on practical outcomes and available options."
  )

  # Rationality and cognitive style (check both naming conventions for backward compatibility)
  cog_rat <- if (!is.null(agent$rationality$cognitive)) {
    agent$rationality$cognitive
  } else if (!is.null(agent$rationality$cognitive_rationality)) {
    agent$rationality$cognitive_rationality
  } else 0.7

  paranoia <- if (!is.null(agent$rationality$paranoia)) agent$rationality$paranoia else 0.5

  consistency <- if (!is.null(agent$rationality$consistency)) {
    agent$rationality$consistency
  } else if (!is.null(agent$rationality$behavioral_consistency)) {
    agent$rationality$behavioral_consistency
  } else 0.7

  volatility <- if (!is.null(agent$rationality$volatility)) {
    agent$rationality$volatility
  } else if (!is.null(agent$rationality$emotional_volatility)) {
    agent$rationality$emotional_volatility
  } else 0.4

  cognitive_desc <- ""
  if (cog_rat < 0.5) {
    cognitive_desc <- paste0(cognitive_desc, "You often make decisions based on gut instinct rather than careful analysis. ")
  } else if (cog_rat > 0.8) {
    cognitive_desc <- paste0(cognitive_desc, "You are highly analytical and data-driven in your assessments. ")
  }

  if (paranoia > 0.7) {
    cognitive_desc <- paste0(cognitive_desc, "You see threats everywhere and assume the worst about adversaries' intentions. ")
  } else if (paranoia < 0.3) {
    cognitive_desc <- paste0(cognitive_desc, "You tend to be optimistic and may underestimate threats. ")
  }

  if (volatility > 0.6) {
    cognitive_desc <- paste0(cognitive_desc, "Your positions can shift strongly based on recent events. ")
  }

  if (consistency < 0.5) {
    cognitive_desc <- paste0(cognitive_desc, "You are unpredictable and may take positions that surprise others. ")
  }

  # Role-specific expertise and biases
  role <- if (!is.null(agent$role)) agent$role else "government"
  role_desc <- switch(role,
    "military" = "MILITARY EXPERTISE: You focus on operational feasibility, force ratios, logistics, and tactical outcomes. You may overweight military solutions.",
    "economic" = "ECONOMIC EXPERTISE: You focus on costs, sanctions impact, trade, and resource constraints. You warn about economic sustainability.",
    "intelligence" = "INTELLIGENCE EXPERTISE: You have the best information but see threats everywhere. You warn about what the enemy might do.",
    "diplomatic" = "DIPLOMATIC EXPERTISE: You focus on negotiations, international support, and reputation. You see paths to de-escalation others miss.",
    "government" = "LEADERSHIP ROLE: You balance competing advice and make final decisions. You think about domestic politics and coalition management.",
    "political" = "OPPOSITION PERSPECTIVE: You critique government policy and amplify public concerns. You may propose alternatives or demand accountability.",
    "foreign_government" = "EXTERNAL ALLY: You represent allied interests and coordinate support or pressure.",
    "international_org" = "INTERNATIONAL INSTITUTION: You advocate for humanitarian concerns, international law, and multilateral solutions.",
    "Your role shapes your perspective on this crisis."
  )

  prompt <- sprintf(
    "<agent_response>
You are %s in a geopolitical crisis simulation. %s

<worldview>
%s
</worldview>

<role_context>
%s
</role_context>

<agent_disposition>
=== YOUR DISPOSITION ===
%s
%s
%s
%s
</agent_disposition>

<situation_context>
=== CURRENT SITUATION (Day %d) ===
%s

=== RECENT DEVELOPMENTS ===
%s
</situation_context>

<response_requirements>
=== RESPONSE REQUIREMENTS ===
1. BE SPECIFIC AND CONCRETE: Give specific policy recommendations, not vague principles. Name actions, timelines, conditions.
2. STAY IN CHARACTER: Your hawk/dove orientation (%.2f) and worldview MUST shape your position. Hawks push for strength; doves push for talks.
3. BE BRIEF: 2-4 paragraphs maximum. Policy meetings are not poetry readings.
4. DISAGREE WHEN APPROPRIATE: If someone proposes something that conflicts with your worldview or orientation, you MUST push back. A hawk should challenge dovish proposals. A dove should warn about escalation risks.
5. ACKNOWLEDGE TRADEOFFS: Note the costs and risks of your preferred approach, but argue it's still the best option.

Your response should read like a policy advisor speaking in a crisis meeting - direct, substantive, and shaped by your specific perspective.
</response_requirements>
</agent_response>",
    agent$name,
    agent$description,
    worldview_desc,
    role_desc,
    hawk_dove_desc,
    policy_desc,
    objective_desc,
    cognitive_desc,
    scenario_context$current_day,
    scenario_context$situation_summary,
    paste(scenario_context$recent_events, collapse = "\n"),
    agent$hawk_dove
  )

  return(prompt)
}

#' Call OpenRouter API for agent response with retry logic
#'
#' @param system_prompt Character string with system prompt
#' @param user_message Character string with user message
#' @param model Model identifier
#' @param api_key OpenRouter API key
#' @param max_retries Maximum number of retry attempts (default 3)
#' @param base_delay Base delay in seconds for exponential backoff (default 2)
#' @return Character string with agent's response
call_llm <- function(system_prompt, user_message, model, api_key,
                     max_retries = 3, base_delay = 2) {

  last_error <- NULL

  for (attempt in 1:(max_retries + 1)) {
    result <- tryCatch({
      response <- POST(
        url = paste0(OPENROUTER_BASE_URL, "/chat/completions"),
        add_headers(
          "Authorization" = paste("Bearer", api_key),
          "Content-Type" = "application/json"
        ),
        body = toJSON(list(
          model = model,
          messages = list(
            list(role = "system", content = system_prompt),
            list(role = "user", content = user_message)
          ),
          temperature = 0.7,
          max_tokens = 4000  # Increased for multi-agent coordination
        ), auto_unbox = TRUE),
        encode = "json",
        timeout(120)  # 2 minute timeout
      )

      if (status_code(response) != 200) {
        # Check for rate limiting (429) or server errors (5xx)
        status <- status_code(response)
        if (status == 429 || status >= 500) {
          stop(sprintf("Retryable API error (status %d)", status))
        }
        stop(sprintf("API call failed with status %d: %s",
                     status,
                     content(response, "text")))
      }

      parsed <- content(response, "parsed")
      return(parsed$choices[[1]]$message$content)

    }, error = function(e) {
      last_error <<- e
      return(NULL)
    })

    # If we got a result, return it
    if (!is.null(result)) {
      return(result)
    }

    # If this wasn't the last attempt, wait and retry
    if (attempt <= max_retries) {
      delay <- base_delay * (2 ^ (attempt - 1))  # Exponential backoff
      cat(sprintf("    [Retry %d/%d] Network error, waiting %.0fs: %s\n",
                  attempt, max_retries, delay, last_error$message))
      Sys.sleep(delay)
    }
  }

  # All retries exhausted
  stop(sprintf("API call failed after %d retries. Last error: %s",
               max_retries, last_error$message))
}

#' Get agent's response to a situation or message
#'
#' @param agent Agent object
#' @param context Scenario context
#' @param message Message or situation to respond to
#' @param api_key OpenRouter API key
#' @return Character string with response
get_agent_response <- function(agent, context, message, api_key) {
  system_prompt <- generate_agent_prompt(agent, context)
  response <- call_llm(system_prompt, message, AGENT_MODEL, api_key)

  # Update agent's memory
  agent$state$recent_interactions <- c(
    agent$state$recent_interactions,
    list(list(
      timestamp = Sys.time(),
      message = message,
      response = response
    ))
  )

  # Keep only last 10 interactions in memory
  if (length(agent$state$recent_interactions) > 10) {
    agent$state$recent_interactions <- tail(agent$state$recent_interactions, 10)
  }

  return(response)
}

#' Update agent's position based on interactions
#'
#' @param agent Agent object
#' @param interaction_summary Summary of recent interactions
#' @return Updated agent object
update_agent_position <- function(agent, interaction_summary) {
  # This could be more sophisticated - for now, we track positions qualitatively
  agent$state$current_position <- c(
    agent$state$current_position,
    list(list(
      timestamp = Sys.time(),
      summary = interaction_summary
    ))
  )
  return(agent)
}
