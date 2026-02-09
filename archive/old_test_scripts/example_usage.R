# Example usage of the wargame simulation

# Make sure you've set your API key first:
# Sys.setenv(OPENROUTER_API_KEY = "your-key-here")

# ============================================================================
# Example 1: Quick Start - Run a simple simulation
# ============================================================================

# Load the simulation
source("src/simulation.R")

# Run with default settings (10 periods, ~5-10 minutes depending on API speed)
cat("Running simulation with default settings...\n")
state <- start_simulation()

# The simulation will output progress and save results automatically

# ============================================================================
# Example 2: Custom Configuration
# ============================================================================

# Modify configuration before running
source("config.R")
source("src/simulation.R")

# Run shorter simulation for testing
cat("\nRunning shorter test simulation (3 periods)...\n")
state <- run_simulation(n_periods = 3)

# ============================================================================
# Example 3: Analyze Results
# ============================================================================

source("src/analysis.R")

# Print summary report
cat("\n=== SUMMARY REPORT ===\n")
print_summary_report(state)

# Generate visualizations
cat("\nGenerating plots...\n")
plot_probability_timeline(state, "outputs/my_timeline.png")

# Analyze interaction network from period 1
if (state$current_period >= 1) {
  plot_interaction_network(state, period = 1, "outputs/network_period_1.png")
}

# Export transcripts for qualitative analysis
export_interaction_transcripts(state, "outputs/my_transcripts.txt")

# ============================================================================
# Example 4: Extract Specific Data
# ============================================================================

# Get probability data
probabilities <- sapply(state$assessments_history, function(a) a$probability)
cat("\nProbability trajectory:\n")
print(probabilities)

# Get all events that occurred
all_events <- unlist(state$events_history, recursive = FALSE)
cat(sprintf("\nTotal events: %d\n", length(all_events)))

# Count event types
event_types <- table(sapply(all_events, function(e) e$type))
cat("\nEvents by type:\n")
print(event_types)

# Get interaction count by period
interaction_counts <- sapply(state$interactions_history, function(s) s$interaction_count)
cat("\nInteractions per period:\n")
print(interaction_counts)

# ============================================================================
# Example 5: Access Agent States
# ============================================================================

# Look at a specific agent's characteristics
agent <- state$agents$small_president
cat("\n=== Smaller Power President ===\n")
cat(sprintf("Name: %s\n", agent$name))
cat(sprintf("Hawk/Dove: %.2f\n", agent$hawk_dove))
cat(sprintf("Policy Adherence: %.2f\n", agent$policy_adherence))
cat(sprintf("Objective Alignment: %.2f\n", agent$objective_alignment))
cat(sprintf("Recent interactions: %d\n", length(agent$state$recent_interactions)))

# ============================================================================
# Example 6: Load Previously Saved Simulation
# ============================================================================

# Load a previously run simulation
saved_state <- load_simulation_state("outputs")

# Continue analysis on saved state
cat("\n=== ANALYZING SAVED SIMULATION ===\n")
stats <- generate_summary_stats(saved_state)
cat(sprintf("Simulation ran for %d periods\n", stats$periods_simulated))
cat(sprintf("Final collapse probability: %.1f%%\n", stats$final_probability * 100))

# ============================================================================
# Example 7: Examine Specific Interactions
# ============================================================================

# Look at interactions from a specific period
period_num <- 1
if (period_num <= state$current_period) {
  session <- state$interactions_history[[period_num]]

  cat(sprintf("\n=== Period %d Interactions ===\n", period_num))
  for (int in session$interactions) {
    cat(sprintf("\nTopic: %s\n", int$topic))
    cat(sprintf("Type: %s\n", int$type))
    cat(sprintf("Participants: %s\n", paste(int$participants, collapse = ", ")))
    cat(sprintf("Messages exchanged: %d\n", length(int$messages)))

    # Print first message as example
    if (length(int$messages) > 0) {
      msg <- int$messages[[1]]
      cat(sprintf("\nFirst message from %s:\n", msg$sender_name))
      cat(substr(msg$content, 1, 200), "...\n")
    }
  }
}

# ============================================================================
# Example 8: Custom Analysis - Track Probability Changes
# ============================================================================

# Calculate period-over-period changes
if (length(state$assessments_history) >= 2) {
  cat("\n=== Probability Changes ===\n")
  for (i in 2:length(state$assessments_history)) {
    prev_prob <- state$assessments_history[[i-1]]$probability
    curr_prob <- state$assessments_history[[i]]$probability
    change <- (curr_prob - prev_prob) * 100

    cat(sprintf("Period %d -> %d: %+.1f%% (%.1f%% -> %.1f%%)\n",
                i-1, i, change, prev_prob * 100, curr_prob * 100))
  }
}

# ============================================================================
# Example 9: Network Analysis
# ============================================================================

library(igraph)

# Build cumulative interaction network
cat("\n=== Network Centrality Analysis ===\n")

all_edges <- list()
for (session in state$interactions_history) {
  for (int in session$interactions) {
    if (length(int$participant_ids) >= 2) {
      for (i in 1:(length(int$participant_ids) - 1)) {
        for (j in (i + 1):length(int$participant_ids)) {
          all_edges <- c(all_edges, list(c(
            int$participant_ids[i],
            int$participant_ids[j]
          )))
        }
      }
    }
  }
}

if (length(all_edges) > 0) {
  g <- graph_from_edgelist(do.call(rbind, all_edges), directed = FALSE)
  g <- simplify(g)

  # Calculate centrality measures
  degree_cent <- degree(g)
  betweenness_cent <- betweenness(g)

  # Show most central agents
  cat("\nMost connected agents (by degree):\n")
  top_degree <- head(sort(degree_cent, decreasing = TRUE), 5)
  for (i in seq_along(top_degree)) {
    agent_name <- state$agents[[names(top_degree)[i]]]$name
    cat(sprintf("  %d. %s (degree: %d)\n", i, agent_name, top_degree[i]))
  }

  cat("\nMost influential agents (by betweenness):\n")
  top_between <- head(sort(betweenness_cent, decreasing = TRUE), 5)
  for (i in seq_along(top_between)) {
    agent_name <- state$agents[[names(top_between)[i]]]$name
    cat(sprintf("  %d. %s (betweenness: %.2f)\n", i, agent_name, top_between[i]))
  }
}

cat("\n=== Examples Complete ===\n")
cat("Check the 'outputs' directory for saved files.\n")

# ============================================================================
# Example 10: Generate Human Forecasting Prompts
# ============================================================================

# After running a simulation, generate forecasting materials for humans
source("src/forecast_prompts.R")

cat("\n=== Generating Forecasting Materials ===\n")
files <- create_forecasting_worksheet(state, "outputs")

cat("\nGenerated files:\n")
cat(sprintf("  Prompts: %s\n", files$prompts))
cat(sprintf("  Answers: %s\n", files$answers))
cat(sprintf("  Template: %s\n", files$template))

# ============================================================================
# Example 11: Generate Single Period Forecast Prompt
# ============================================================================

# Generate prompt for a specific period
cat("\n=== Period 1 Forecast Prompt ===\n")
prompt_p1 <- generate_forecast_prompt(state, period = 1)
cat(substr(prompt_p1, 1, 500), "...\n")  # Show first 500 chars

# ============================================================================
# Example 12: Compare Human vs LLM Forecasts
# ============================================================================

# Simulate some human forecasts (0-1 scale)
# In real use, these would come from actual human participants
human_forecasts <- c(0.28, 0.32, 0.36, 0.39, 0.41, 0.43, 0.46, 0.48, 0.51, 0.54)

cat("\n=== Comparing Human vs LLM Forecasts ===\n")
comparison <- compare_forecasts(state, human_forecasts)
print(comparison)

# Calculate metrics
cat("\nAccuracy Metrics:\n")
cat(sprintf("  Mean Absolute Error: %.3f\n", mean(comparison$abs_difference)))
cat(sprintf("  Correlation: %.3f\n",
            cor(comparison$llm_forecast, comparison$human_forecast)))

# ============================================================================
# Example 13: Visualize Forecast Comparison
# ============================================================================

library(ggplot2)

cat("\n=== Creating Forecast Comparison Plot ===\n")

# Reshape data for plotting
plot_data <- rbind(
  data.frame(
    period = comparison$period,
    probability = comparison$llm_forecast,
    forecaster = "LLM Aggregator"
  ),
  data.frame(
    period = comparison$period,
    probability = comparison$human_forecast,
    forecaster = "Human Forecaster"
  )
)

# Create comparison plot
forecast_plot <- ggplot(plot_data, aes(x = period, y = probability,
                                       color = forecaster, shape = forecaster)) +
  geom_line(size = 1) +
  geom_point(size = 3) +
  scale_color_manual(values = c("LLM Aggregator" = "#3498db",
                                 "Human Forecaster" = "#e74c3c")) +
  scale_shape_manual(values = c("LLM Aggregator" = 16,
                                 "Human Forecaster" = 17)) +
  labs(
    title = "LLM vs Human Probability Forecasts",
    subtitle = "Government Collapse Probability Over Time",
    x = "Period",
    y = "Probability of Government Collapse",
    color = "Forecaster",
    shape = "Forecaster"
  ) +
  theme_minimal() +
  theme(legend.position = "bottom")

# Save plot
ggsave("outputs/forecast_comparison.png", forecast_plot, width = 10, height = 6)
cat("Forecast comparison plot saved to outputs/forecast_comparison.png\n")

# ============================================================================
# Example 14: Period Summary for Quick Review
# ============================================================================

cat("\n=== Period-by-Period Summary ===\n")
for (p in 1:min(3, state$current_period)) {
  summary <- generate_period_summary(state, p)
  cat(summary, "\n")
}

cat("\n=== Forecasting Examples Complete ===\n")
cat("Check the 'outputs' directory for all generated forecasting materials.\n")
