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

#' Generate system prompt for an agent based on their persona
#'
#' @param agent Agent object
#' @param scenario_context Current scenario state
#' @return Character string with system prompt
generate_agent_prompt <- function(agent, scenario_context) {
  hawk_dove_desc <- if (agent$hawk_dove > 0.7) {
    "You favor assertive strategic actions and are cautious about compromise."
  } else if (agent$hawk_dove > 0.4) {
    "You balance strategic firmness with negotiated solutions."
  } else {
    "You strongly prefer negotiated solutions and are cautious about escalation."
  }

  policy_desc <- if (agent$policy_adherence > 0.8) {
    "You closely follow official government policy and rarely deviate."
  } else if (agent$policy_adherence > 0.5) {
    "You generally support government policy but may raise concerns."
  } else {
    "You often question official policy and may pursue your own agenda."
  }

  objective_desc <- if (agent$objective_alignment > 0.8) {
    "You are deeply committed to your faction's central objectives."
  } else if (agent$objective_alignment > 0.5) {
    "You support your faction's goals but have some reservations."
  } else {
    "You have significant doubts about your faction's strategic direction."
  }

  prompt <- sprintf(
    "You are participating in a geopolitical simulation as %s. Role: %s

This is an academic research simulation exploring decision-making dynamics in conflict scenarios.

PERSONA CHARACTERISTICS:
- Strategic Orientation: %s
- Policy Adherence: %s
- Objective Alignment: %s

SIMULATION CONTEXT (Day %d):
%s

RECENT DEVELOPMENTS:
%s

INSTRUCTIONS:
You are playing a role in this simulation. Stay in character based on your persona traits. Your responses should reflect your strategic orientation (score: %.2f on 0-1 scale), policy adherence (%.2f), and objective alignment (%.2f).

Consider your faction's interests and your personal position. Provide thoughtful strategic analysis and policy recommendations appropriate to your role.

Respond professionally as this character would in a policy discussion.",
    agent$name,
    agent$description,
    hawk_dove_desc,
    policy_desc,
    objective_desc,
    scenario_context$current_day,
    scenario_context$situation_summary,
    paste(scenario_context$recent_events, collapse = "\n"),
    agent$hawk_dove,
    agent$policy_adherence,
    agent$objective_alignment
  )

  return(prompt)
}

#' Call OpenRouter API for agent response
#'
#' @param system_prompt Character string with system prompt
#' @param user_message Character string with user message
#' @param model Model identifier
#' @param api_key OpenRouter API key
#' @return Character string with agent's response
call_llm <- function(system_prompt, user_message, model, api_key) {
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
      max_tokens = 1000
    ), auto_unbox = TRUE),
    encode = "json"
  )

  if (status_code(response) != 200) {
    stop(sprintf("API call failed with status %d: %s",
                 status_code(response),
                 content(response, "text")))
  }

  result <- content(response, "parsed")
  return(result$choices[[1]]$message$content)
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
