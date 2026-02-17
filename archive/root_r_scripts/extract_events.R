# Extract actual external events from each scenario's RDS file
# Output: JSON file that Python can read

library(jsonlite)

output_dir <- "outputs/multiscenario"
all_events <- list()

for (i in 1:50) {
  f <- sprintf("%s/scenario_%03d.rds", output_dir, i)
  if (!file.exists(f)) next

  s <- readRDS(f)
  sid <- sprintf("scenario_%03d", i)

  # Extract events from events_history
  events <- list()
  if (!is.null(s$events_history) && length(s$events_history) > 0) {
    period_events <- s$events_history[[1]]  # Period 1
    if (is.list(period_events)) {
      for (evt in period_events) {
        if (is.list(evt)) {
          events[[length(events) + 1]] <- list(
            type = if (!is.null(evt$type)) as.character(evt$type) else "unknown",
            name = if (!is.null(evt$name)) as.character(evt$name) else "",
            description = if (!is.null(evt$description)) as.character(evt$description) else
                          if (!is.null(evt$impact)) as.character(evt$impact) else ""
          )
        }
      }
    }
  }

  # Extract actions from action_decisions
  novaris_actions <- character(0)
  tethys_actions <- character(0)
  if (!is.null(s$action_decisions) && length(s$action_decisions) > 0) {
    if (!is.null(s$action_decisions[[1]]$major_power$approved_actions)) {
      novaris_actions <- sapply(s$action_decisions[[1]]$major_power$approved_actions, function(a) a$action)
    }
    if (!is.null(s$action_decisions[[1]]$small_power$approved_actions)) {
      tethys_actions <- sapply(s$action_decisions[[1]]$small_power$approved_actions, function(a) a$action)
    }
  }

  # Extract external actor actions safely
  external_actions <- list()
  for (faction in c("meridian", "valkoria", "aurelia", "international_org")) {
    tryCatch({
      dec <- s$action_decisions[[1]][[faction]]
      if (!is.null(dec)) {
        action_name <- ""
        if (!is.null(dec$action)) {
          action_name <- as.character(dec$action)
        } else if (!is.null(dec$approved_actions) && length(dec$approved_actions) > 0) {
          action_name <- as.character(dec$approved_actions[[1]]$action)
        }
        if (nchar(action_name) > 0) {
          external_actions[[length(external_actions) + 1]] <- list(
            faction = faction,
            action = action_name
          )
        }
      }
    }, error = function(e) {})
  }

  all_events[[sid]] <- list(
    scenario_id = sid,
    external_events = events,
    novaris_actions = as.list(novaris_actions),
    tethys_actions = as.list(tethys_actions),
    external_actor_actions = external_actions
  )

  cat(sprintf("  %s: %d events, %d novaris, %d tethys, %d external\n",
              sid, length(events), length(novaris_actions), length(tethys_actions), length(external_actions)))
}

# Write as JSON
json_file <- file.path(output_dir, "scenario_events.json")
write(toJSON(all_events, auto_unbox = TRUE, pretty = TRUE), json_file)
cat(sprintf("\nWrote %d scenarios to %s\n", length(all_events), json_file))
