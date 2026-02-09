# Run simulation with enhanced cognitive agents
#
# This script integrates the cognitive framework (worldviews, deception, information asymmetry)
# with the original simulation structure (periods, events, interactions, predictions)

# Load configuration
source("config.R")

# Load integrated agent system (adds cognitive features)
source("src/integrated_agent_system.R")

# Create enhanced agents from config
cat("Creating enhanced cognitive agents...\n")
enhanced_agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(
    major_power = "Novaris",
    small_power = "Tethys",
    external = "External"
  )
)

# Print agent worldviews
cat("\nAgent Worldview Assignments:\n")
for (agent_id in names(enhanced_agents)) {
  agent <- enhanced_agents[[agent_id]]
  cat(sprintf("  %s: %s (hawk/dove=%.2f, deception_capacity=%.2f)\n",
              agent$name, agent$worldview, agent$hawk_dove,
              agent$deception$capacity))
}

# Replace AGENTS in config with enhanced agents
# This allows simulation.R to use the enhanced agents
AGENTS <- lapply(enhanced_agents, function(agent) {
  list(
    name = agent$name,
    faction = agent$faction,
    role = agent$role,
    hawk_dove = agent$hawk_dove,
    policy_adherence = agent$policy_adherence,
    objective_alignment = agent$objective_alignment,
    description = agent$description,
    # Enhanced attributes
    worldview = agent$worldview,
    worldview_details = agent$worldview_details,
    deception = agent$deception,
    information = agent$information,
    cognitive = agent$cognitive,
    cognitive_biases = agent$cognitive_biases,
    decision_style = agent$decision_style,
    information_processing = agent$information_processing,
    base_trust = agent$base_trust,
    trust_levels = agent$trust_levels,
    has_access_to = agent$has_access_to,
    agent_id = agent$agent_id,
    country = agent$country
  )
})

# Now run the simulation with enhanced agents
cat("\n========================================\n")
cat("Starting simulation with enhanced agents\n")
cat("========================================\n\n")

source("src/simulation.R")
final_state <- run_simulation()

cat("\n========================================\n")
cat("Simulation complete!\n")
cat("========================================\n")
