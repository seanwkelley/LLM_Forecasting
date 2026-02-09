#!/usr/bin/env Rscript
# Main entry point for wargame simulation

# Load simulation
source("src/simulation.R")

# Set up environment
if (Sys.getenv("OPENROUTER_API_KEY") == "") {
  cat("ERROR: OPENROUTER_API_KEY environment variable not set.\n")
  cat("Please set it before running:\n")
  cat("  export OPENROUTER_API_KEY='your-key-here'\n")
  cat("Or in R:\n")
  cat("  Sys.setenv(OPENROUTER_API_KEY = 'your-key-here')\n")
  quit(status = 1)
}

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)

if (length(args) == 0) {
  # Default: run new simulation
  cat("Starting new simulation with default parameters...\n")
  state <- start_simulation()
} else if (args[1] == "resume") {
  # Resume from saved state
  if (length(args) < 2) {
    cat("ERROR: Please specify period to resume from\n")
    cat("Usage: Rscript run_simulation.R resume <period>\n")
    quit(status = 1)
  }
  period <- as.integer(args[2])
  cat(sprintf("Resuming simulation from period %d...\n", period))
  state <- run_simulation(resume_from_period = period)
} else if (args[1] == "analyze") {
  # Analyze existing simulation
  cat("Analyzing completed simulation...\n")
  source("src/analysis.R")
  state <- analyze_simulation()
} else {
  cat("Unknown command. Available commands:\n")
  cat("  Rscript run_simulation.R              # Run new simulation\n")
  cat("  Rscript run_simulation.R resume <N>   # Resume from period N\n")
  cat("  Rscript run_simulation.R analyze      # Analyze results\n")
  quit(status = 1)
}

cat("\nDone!\n")
