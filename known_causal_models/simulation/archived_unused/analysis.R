# Analysis and visualization functions

library(ggplot2)
library(dplyr)
library(tidyr)
library(igraph)

#' Plot probability timeline
#'
#' @param state Simulation state object
#' @param output_file Optional file path to save plot
#' @return ggplot object
plot_probability_timeline <- function(state, output_file = NULL) {
  # Extract assessments
  assessments_df <- do.call(rbind, lapply(seq_along(state$assessments_history), function(i) {
    assessment <- state$assessments_history[[i]]
    data.frame(
      period = i,
      day = i * PERIOD_DURATION_DAYS,
      probability = assessment$probability,
      confidence = assessment$confidence,
      trend = assessment$trend,
      stringsAsFactors = FALSE
    )
  }))

  # Create plot
  p <- ggplot(assessments_df, aes(x = day, y = probability * 100)) +
    geom_line(color = "#2c3e50", size = 1.2) +
    geom_point(aes(color = confidence), size = 3) +
    scale_color_manual(
      values = c("LOW" = "#e74c3c", "MEDIUM" = "#f39c12", "HIGH" = "#27ae60"),
      name = "Confidence"
    ) +
    labs(
      title = "Probability of Government Collapse Over Time",
      subtitle = sprintf("Simulation ID: %s", substr(state$simulation_id, 1, 8)),
      x = "Days Since Invasion",
      y = "Probability of Collapse (%)"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 14, face = "bold"),
      plot.subtitle = element_text(size = 10, color = "gray50"),
      legend.position = "bottom"
    ) +
    ylim(0, 100)

  if (!is.null(output_file)) {
    ggsave(output_file, p, width = 10, height = 6)
    cat(sprintf("Plot saved to %s\n", output_file))
  }

  return(p)
}

#' Plot interaction network for a specific period
#'
#' @param state Simulation state object
#' @param period Period number to visualize
#' @param output_file Optional file path to save plot
#' @return igraph plot
plot_interaction_network <- function(state, period, output_file = NULL) {
  session <- state$interactions_history[[period]]

  if (length(session$interactions) == 0) {
    cat("No interactions to plot for this period.\n")
    return(NULL)
  }

  # Build edge list
  edges <- list()
  for (int in session$interactions) {
    if (length(int$participant_ids) >= 2) {
      for (i in 1:(length(int$participant_ids) - 1)) {
        for (j in (i + 1):length(int$participant_ids)) {
          edges <- c(edges, list(c(
            int$participant_ids[i],
            int$participant_ids[j]
          )))
        }
      }
    }
  }

  if (length(edges) == 0) {
    cat("No network edges to plot.\n")
    return(NULL)
  }

  # Create graph
  g <- graph_from_edgelist(do.call(rbind, edges), directed = FALSE)

  # Simplify (combine multiple edges)
  g <- simplify(g, edge.attr.comb = "sum")

  # Set node attributes based on faction
  node_colors <- sapply(V(g)$name, function(agent_id) {
    agent <- state$agents[[agent_id]]
    if (agent$faction == "major_power") {
      "#e74c3c"  # Red
    } else if (agent$faction == "small_power") {
      "#3498db"  # Blue
    } else {
      "#95a5a6"  # Gray
    }
  })

  V(g)$color <- node_colors

  # Set labels
  V(g)$label <- sapply(V(g)$name, function(agent_id) {
    agent <- state$agents[[agent_id]]
    # Shorten name
    gsub("Power ", "", gsub("Smaller ", "S.", gsub("Major ", "M.", agent$name)))
  })

  if (!is.null(output_file)) {
    png(output_file, width = 800, height = 800)
  }

  # Plot
  plot(g,
       vertex.size = 20,
       vertex.label.cex = 0.7,
       vertex.label.color = "black",
       edge.width = E(g)$weight * 2,
       layout = layout_with_fr(g),
       main = sprintf("Interaction Network - Period %d", period))

  legend("bottomleft",
         legend = c("Major Power", "Smaller Power", "External"),
         col = c("#e74c3c", "#3498db", "#95a5a6"),
         pch = 19,
         pt.cex = 2,
         cex = 0.8)

  if (!is.null(output_file)) {
    dev.off()
    cat(sprintf("Network plot saved to %s\n", output_file))
  }

  return(g)
}

#' Generate summary statistics
#'
#' @param state Simulation state object
#' @return List with summary statistics
generate_summary_stats <- function(state) {
  # Probability statistics
  probs <- sapply(state$assessments_history, function(a) a$probability)

  # Interaction statistics
  total_interactions <- sum(sapply(state$interactions_history, function(s) s$interaction_count))
  interactions_by_period <- sapply(state$interactions_history, function(s) s$interaction_count)

  # Event statistics
  total_events <- sum(sapply(state$events_history, length))
  events_by_type <- table(unlist(sapply(state$events_history, function(events) {
    sapply(events, function(e) e$type)
  })))

  stats <- list(
    simulation_id = state$simulation_id,
    periods_simulated = state$current_period,
    total_days = state$current_period * PERIOD_DURATION_DAYS,
    runtime_minutes = as.numeric(difftime(state$end_time, state$start_time, units = "mins")),

    # Probability stats
    initial_probability = probs[1],
    final_probability = tail(probs, 1),
    mean_probability = mean(probs, na.rm = TRUE),
    max_probability = max(probs, na.rm = TRUE),
    min_probability = min(probs, na.rm = TRUE),

    # Interaction stats
    total_interactions = total_interactions,
    mean_interactions_per_period = mean(interactions_by_period),

    # Event stats
    total_events = total_events,
    events_by_type = events_by_type,

    # Agent stats
    n_agents = length(state$agents),
    n_major_power = sum(sapply(state$agents, function(a) a$faction == "major_power")),
    n_small_power = sum(sapply(state$agents, function(a) a$faction == "small_power")),
    n_external = sum(sapply(state$agents, function(a) a$faction == "external"))
  )

  return(stats)
}

#' Print summary report
#'
#' @param state Simulation state object
print_summary_report <- function(state) {
  stats <- generate_summary_stats(state)

  cat("\n")
  cat("="*60, "\n", sep = "")
  cat("           SIMULATION SUMMARY REPORT\n")
  cat("="*60, "\n", sep = "")
  cat(sprintf("Simulation ID: %s\n", stats$simulation_id))
  cat(sprintf("Runtime: %.1f minutes\n", stats$runtime_minutes))
  cat(sprintf("Periods Simulated: %d (%d days)\n",
              stats$periods_simulated, stats$total_days))
  cat("\n")

  cat("AGENTS:\n")
  cat(sprintf("  Total: %d\n", stats$n_agents))
  cat(sprintf("  Major Power: %d\n", stats$n_major_power))
  cat(sprintf("  Smaller Power: %d\n", stats$n_small_power))
  cat(sprintf("  External: %d\n", stats$n_external))
  cat("\n")

  cat("PROBABILITY ASSESSMENT:\n")
  cat(sprintf("  Initial: %.1f%%\n", stats$initial_probability * 100))
  cat(sprintf("  Final: %.1f%%\n", stats$final_probability * 100))
  cat(sprintf("  Mean: %.1f%%\n", stats$mean_probability * 100))
  cat(sprintf("  Range: %.1f%% - %.1f%%\n",
              stats$min_probability * 100, stats$max_probability * 100))
  cat("\n")

  cat("INTERACTIONS:\n")
  cat(sprintf("  Total: %d\n", stats$total_interactions))
  cat(sprintf("  Mean per period: %.1f\n", stats$mean_interactions_per_period))
  cat("\n")

  cat("EVENTS:\n")
  cat(sprintf("  Total: %d\n", stats$total_events))
  cat("  By type:\n")
  for (type in names(stats$events_by_type)) {
    cat(sprintf("    %s: %d\n", type, stats$events_by_type[type]))
  }

  cat("="*60, "\n", sep = "")
}

#' Export interaction transcripts to text file
#'
#' @param state Simulation state object
#' @param output_file Output file path
export_interaction_transcripts <- function(state, output_file) {
  con <- file(output_file, "w")

  writeLines("INTERACTION TRANSCRIPTS", con)
  writeLines(paste(rep("=", 80), collapse = ""), con)
  writeLines("", con)

  for (period in seq_along(state$interactions_history)) {
    session <- state$interactions_history[[period]]

    writeLines(sprintf("PERIOD %d (Day %d)", period, period * PERIOD_DURATION_DAYS), con)
    writeLines(paste(rep("-", 80), collapse = ""), con)
    writeLines("", con)

    for (int in session$interactions) {
      writeLines(sprintf("Interaction: %s", int$topic), con)
      writeLines(sprintf("Type: %s", int$type), con)
      writeLines(sprintf("Participants: %s", paste(int$participants, collapse = ", ")), con)
      writeLines("", con)

      for (msg in int$messages) {
        writeLines(sprintf("[%s]", msg$sender_name), con)
        writeLines(msg$content, con)
        writeLines("", con)
      }

      writeLines(paste(rep("-", 40), collapse = ""), con)
      writeLines("", con)
    }

    writeLines("", con)
  }

  close(con)
  cat(sprintf("Transcripts exported to %s\n", output_file))
}

#' Load and analyze completed simulation
#'
#' @param output_dir Output directory with saved simulation
#' @export
analyze_simulation <- function(output_dir = "outputs") {
  state <- load_simulation_state(output_dir)

  # Print summary
  print_summary_report(state)

  # Generate plots
  cat("\nGenerating visualizations...\n")
  plot_probability_timeline(state, file.path(output_dir, "probability_timeline.png"))

  # Network plots for first, middle, and last periods
  periods_to_plot <- c(1, ceiling(state$current_period / 2), state$current_period)
  for (p in periods_to_plot) {
    if (p <= state$current_period) {
      plot_interaction_network(
        state, p,
        file.path(output_dir, sprintf("network_period_%d.png", p))
      )
    }
  }

  # Export transcripts
  export_interaction_transcripts(state, file.path(output_dir, "transcripts.txt"))

  # Generate forecasting prompts for human participants
  cat("\nGenerating forecasting prompts for human participants...\n")
  source("src/forecast_prompts.R")
  create_forecasting_worksheet(state, output_dir)

  cat("\nAnalysis complete!\n")

  return(state)
}
