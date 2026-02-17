# Run Simulation with Full Action Execution
#
# This script runs the complete simulation where agents:
# 1. Analyze the situation through their worldview
# 2. Choose concrete actions (military, economic, diplomatic, etc.)
# 3. Execute those actions with real consequences
# 4. Discuss the results with other agents
# 5. Aggregator assesses probability of government collapse

# ============================================================
# AUTO-ARCHIVE PREVIOUS RUNS (v3.3)
# ============================================================
# Check if outputs directory exists with previous simulation data
# If so, archive it before starting new run

archive_previous_run <- function() {
  outputs_dir <- "outputs"

  # Check if outputs directory exists and has simulation data
  if (dir.exists(outputs_dir)) {
    state_file <- file.path(outputs_dir, "simulation_state.rds")

    if (file.exists(state_file)) {
      # Get timestamp from the previous simulation if possible
      tryCatch({
        old_state <- readRDS(state_file)
        if (!is.null(old_state$start_time)) {
          archive_timestamp <- format(old_state$start_time, "%Y%m%d_%H%M%S")
        } else {
          # Fall back to file modification time
          archive_timestamp <- format(file.info(state_file)$mtime, "%Y%m%d_%H%M%S")
        }
      }, error = function(e) {
        # Fall back to current time if can't read state
        archive_timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
      })

      # Create archive directory name
      archive_base <- "archive/old_simulation_runs"
      dir.create(archive_base, recursive = TRUE, showWarnings = FALSE)
      archive_dir <- file.path(archive_base, sprintf("simulation_%s", archive_timestamp))

      # Rename outputs to archive
      cat("\n", rep("=", 60), "\n", sep = "")
      cat("ARCHIVING PREVIOUS SIMULATION RUN\n")
      cat(rep("=", 60), "\n", sep = "")
      cat(sprintf("Moving previous outputs to: %s/\n", archive_dir))

      # Rename the directory
      success <- file.rename(outputs_dir, archive_dir)

      if (success) {
        cat("✓ Previous run archived successfully\n\n")
      } else {
        # If rename fails, try copy and delete
        cat("Direct rename failed, attempting copy...\n")
        dir.create(archive_dir, recursive = TRUE)

        # Copy all files
        files_to_copy <- list.files(outputs_dir, full.names = TRUE, recursive = TRUE)
        for (f in files_to_copy) {
          rel_path <- sub(paste0("^", outputs_dir, "/?"), "", f)
          dest_path <- file.path(archive_dir, rel_path)
          dest_dir <- dirname(dest_path)
          if (!dir.exists(dest_dir)) dir.create(dest_dir, recursive = TRUE)
          file.copy(f, dest_path)
        }

        # Remove old outputs directory
        unlink(outputs_dir, recursive = TRUE)
        cat("✓ Previous run archived via copy\n\n")
      }
    } else {
      cat("\nNo previous simulation_state.rds found - starting fresh\n\n")
    }
  } else {
    cat("\nNo previous outputs directory found - starting fresh\n\n")
  }

  # Ensure outputs directory exists for new run
  if (!dir.exists(outputs_dir)) {
    dir.create(outputs_dir, recursive = TRUE)
  }
}

# Run the archive function
archive_previous_run()

# ============================================================
# AUTO-CLEANUP STALE RSCRIPT PROCESSES
# ============================================================
# Kill any lingering Rscript processes from previous interrupted runs
# This prevents issues with multiple simulations running concurrently

cleanup_stale_processes <- function() {
  tryCatch({
    # Get current process ID
    current_pid <- Sys.getpid()

    # Find all Rscript processes
    if (Sys.info()["sysname"] == "Windows") {
      # Windows: Use tasklist and findstr
      result <- system("tasklist /FI \"IMAGENAME eq Rscript.exe\" /FO CSV /NH", intern = TRUE)

      if (length(result) > 0 && !grepl("INFO: No tasks", result[1])) {
        cat("\n", rep("=", 60), "\n", sep = "")
        cat("CLEANING UP STALE RSCRIPT PROCESSES\n")
        cat(rep("=", 60), "\n", sep = "")

        # Parse CSV output and extract PIDs
        pids <- character()
        for (line in result) {
          # CSV format: "Image Name","PID","Session Name","Session#","Mem Usage"
          parts <- strsplit(gsub("\"", "", line), ",")[[1]]
          if (length(parts) >= 2) {
            pid <- parts[2]
            if (pid != current_pid) {
              pids <- c(pids, pid)
            }
          }
        }

        if (length(pids) > 0) {
          cat(sprintf("Found %d other Rscript process(es): %s\n", length(pids), paste(pids, collapse = ", ")))
          cat("Terminating stale processes...\n")

          for (pid in pids) {
            system(sprintf("taskkill /PID %s /F >nul 2>&1", pid), intern = FALSE, ignore.stderr = TRUE)
          }

          Sys.sleep(2)
          cat("✓ Stale processes cleaned up\n\n")
        } else {
          cat("No other Rscript processes found - starting fresh\n\n")
        }
      }
    } else {
      # Unix/Linux/Mac: Use ps and grep
      cmd <- sprintf("ps aux | grep -i '[R]script' | grep -v '%d' | awk '{print $2}'", current_pid)
      pids <- system(cmd, intern = TRUE)

      if (length(pids) > 0 && nchar(pids[1]) > 0) {
        cat("\n", rep("=", 60), "\n", sep = "")
        cat("CLEANING UP STALE RSCRIPT PROCESSES\n")
        cat(rep("=", 60), "\n", sep = "")
        cat(sprintf("Found %d other Rscript process(es): %s\n", length(pids), paste(pids, collapse = ", ")))
        cat("Terminating stale processes...\n")

        for (pid in pids) {
          system(sprintf("kill %s 2>/dev/null", pid), ignore.stderr = TRUE)
        }

        Sys.sleep(2)
        cat("✓ Stale processes cleaned up\n\n")
      } else {
        cat("\nNo other Rscript processes found - starting fresh\n\n")
      }
    }
  }, error = function(e) {
    cat("\nNote: Could not check for stale processes (this is OK)\n")
    cat("Error:", e$message, "\n\n")
  })
}

# Run the cleanup function
cleanup_stale_processes()

# ============================================================
# MAIN SIMULATION
# ============================================================

# CRITICAL: Force clean environment to avoid R caching issues
# Remove any previously loaded functions that might be cached
if (exists("run_pre_action_coordination")) {
  cat("Clearing cached functions...\n")
  rm(run_pre_action_coordination, envir = .GlobalEnv)
}
if (exists("run_simulation_with_actions")) {
  rm(run_simulation_with_actions, envir = .GlobalEnv)
}
if (exists("run_simulation_period_with_actions")) {
  rm(run_simulation_period_with_actions, envir = .GlobalEnv)
}

# Check for jsonlite package (required for JSON parsing in multi-action system)
if (!requireNamespace("jsonlite", quietly = TRUE)) {
  cat("\n⚠ Warning: jsonlite package not found. Installing...\n")
  install.packages("jsonlite", repos = "https://cloud.r-project.org/")
}
library(jsonlite)

cat("Force-reloading all source files with clean environment...\n\n")

# Load configuration
source("config.R")

# Load integrated agent system (cognitive features)
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

# Print agent worldviews and capabilities
cat("\n=== AGENT ROSTER ===\n")
for (agent_id in names(enhanced_agents)) {
  agent <- enhanced_agents[[agent_id]]
  cat(sprintf("\n%s (%s):\n", agent$name, agent$country))
  cat(sprintf("  Role: %s | Faction: %s\n", agent$role, agent$faction))
  cat(sprintf("  Worldview: %s\n", agent$worldview))
  cat(sprintf("  Hawk/Dove: %.0f%% / %.0f%%\n",
              agent$hawk_dove * 100, (1 - agent$hawk_dove) * 100))
  cat(sprintf("  Rationality: %.0f%% | Paranoia: %.0f%% | Consistency: %.0f%% | Volatility: %.0f%%\n",
              agent$rationality$cognitive * 100,
              agent$rationality$paranoia * 100,
              agent$rationality$consistency * 100,
              agent$rationality$volatility * 100))
  cat(sprintf("  Deception Capacity: %.0f%% | Willingness: %.0f%%\n",
              agent$deception$capacity * 100, agent$deception$willingness * 100))
  cat(sprintf("  Information Access: %.0f%% | Analytical: %.0f%%\n",
              agent$information$access * 100, agent$information$accuracy * 100))
}

# Replace AGENTS in config with enhanced agents
# This allows simulation to use the enhanced agents
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
    rationality = agent$rationality,  # NEW: Rationality components
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

# Now run the simulation with action execution
cat("\n" , rep("=", 60), "\n")
cat("STARTING SIMULATION WITH ACTION EXECUTION\n")
cat(rep("=", 60), "\n\n")

cat("Features enabled:\n")
cat("  ✓ 11 intra-country actors\n")
cat("  ✓ Worldview-driven decision making\n")
cat("  ✓ Deception mechanics\n")
cat("  ✓ Information asymmetry\n")
cat("  ✓ ** CONCRETE ACTION EXECUTION **\n")
cat("  ✓ Diplomatic, Economic, Military, Covert, WMD actions\n")
cat("  ✓ Action consequences on state (GDP, military strength, territory)\n")
cat("  ✓ Periodic summaries and probability predictions\n")
cat("  ✓ ** v3.6: CROSS-EXPERTISE RECOMMENDATIONS **\n\n")

# Load simulation engine (which loads interaction_engine.R)
source("src/simulation_with_actions.R")

# Run simulation
final_state <- run_simulation_with_actions()

cat("\n", rep("=", 60), "\n")
cat("SIMULATION COMPLETE\n")
cat(rep("=", 60), "\n")

# Print detailed action log
cat("\n=== DETAILED ACTION LOG ===\n")
for (period in 1:length(final_state$action_decisions)) {
  if (!is.null(final_state$action_decisions[[period]])) {
    cat(sprintf("\n--- Period %d ---\n", period))

    for (faction in names(final_state$action_decisions[[period]])) {
      decision <- final_state$action_decisions[[period]][[faction]]
      result <- final_state$action_results[[period]][[faction]]

      # Check if this is a multi-action decision
      if (!is.null(decision$approved_actions)) {
        # Multi-action system
        cat(sprintf("\n%s (%s):\n",
                   toupper(faction), decision$agent_name))
        cat(sprintf("  Multi-action system: %d actions approved\n",
                   length(decision$approved_actions)))

        for (i in seq_along(decision$approved_actions)) {
          action_item <- decision$approved_actions[[i]]
          cat(sprintf("\n  Action %d/%d: %s",
                     i, length(decision$approved_actions), action_item$action))

          # Show if counter-proposal
          if (!is.null(action_item$is_counter) && action_item$is_counter) {
            cat(sprintf(" (↻ counter from: %s)", action_item$original_action))
          }

          # Show priority if available
          if (!is.null(action_item$priority)) {
            cat(sprintf(" [%s priority]", action_item$priority))
          }
          cat("\n")

          if (!is.null(action_item$target) && !is.na(action_item$target)) {
            cat(sprintf("    Target: %s\n", action_item$target))
          }
          if (!is.null(action_item$rationale)) {
            cat(sprintf("    Rationale: %s\n", action_item$rationale))
          }
        }

        # Show overall result
        cat(sprintf("  Overall Result: %s\n",
                   if (result$success) "✓ SUCCESS" else "✗ FAILED"))

        if (!is.null(result$effects)) {
          cat("  Combined Effects:\n")
          for (effect_name in names(result$effects)) {
            effect_value <- result$effects[[effect_name]]
            if (effect_name == "message") {
              cat(sprintf("    - %s\n", effect_value))
            } else {
              cat(sprintf("    - %s: %s\n", effect_name, effect_value))
            }
          }
        }

      } else {
        # Single-action system (traditional)
        cat(sprintf("\n%s (%s):\n",
                   toupper(faction), decision$agent_name))
        cat(sprintf("  Action: %s\n", decision$action))
        if (!is.null(decision$target) && !is.na(decision$target)) {
          cat(sprintf("  Target: %s\n", decision$target))
        }
        cat(sprintf("  Reasoning: %s\n", decision$reasoning))
        cat(sprintf("  Expected: %s\n", decision$expected_outcome))
        cat(sprintf("  Result: %s\n",
                   if (result$success) "✓ SUCCESS" else "✗ FAILED"))

        if (!is.null(result$effects)) {
          cat("  Effects:\n")
          for (effect_name in names(result$effects)) {
            effect_value <- result$effects[[effect_name]]
            if (effect_name == "message") {
              cat(sprintf("    - %s\n", effect_value))
            } else {
              cat(sprintf("    - %s: %s\n", effect_name, effect_value))
            }
          }
        }
      }
    }
  }
}

# Save summary
cat("\n\nSaving simulation summary...\n")
summary_file <- sprintf("outputs/simulation_summary_%s.txt",
                       format(Sys.time(), "%Y%m%d_%H%M%S"))
sink(summary_file)

cat("SIMULATION SUMMARY\n")
cat(rep("=", 60), "\n\n")
cat(sprintf("Simulation ID: %s\n", final_state$simulation_id))
cat(sprintf("Periods Simulated: %d\n", final_state$current_period))
cat(sprintf("End Reason: %s\n",
           if (!is.null(final_state$end_reason)) final_state$end_reason else "completed"))
cat(sprintf("Runtime: %.1f minutes\n",
           as.numeric(difftime(final_state$end_time, final_state$start_time, units = "mins"))))

cat("\n--- Final State ---\n")
cat(sprintf("Crisis Level: %.1f/10\n", final_state$scenario_state$crisis_level))
cat(sprintf("Military Balance: %.2f\n", final_state$scenario_state$military_balance))
cat(sprintf("Sanctions Level: %.2f\n", final_state$scenario_state$sanctions_level))
if (!is.null(final_state$faction_capabilities$territory_controlled)) {
  cat(sprintf("Territory Controlled: %.1f%%\n",
             final_state$scenario_state$territory_controlled * 100))
}

cat("\n--- Final Assessment ---\n")
final_assessment <- final_state$assessments_history[[final_state$current_period]]
if (!is.null(final_assessment)) {
  cat(sprintf("Probability of Collapse: %.1f%%\n",
             final_assessment$probability * 100))
  cat(sprintf("Confidence: %s\n", final_assessment$confidence))
  cat(sprintf("Trend: %s\n", final_assessment$trend))
  cat(sprintf("Key Factors: %s\n", final_assessment$key_factors))
}

cat("\n--- Actions Taken ---\n")
for (period in 1:length(final_state$action_results)) {
  if (!is.null(final_state$action_results[[period]])) {
    cat(sprintf("\nPeriod %d:\n", period))
    for (faction in names(final_state$action_results[[period]])) {
      result <- final_state$action_results[[period]][[faction]]

      # Handle multi-action results differently (v3.8.2 fix)
      if (!is.null(result$multi_action) && result$multi_action) {
        # Multi-action system: show each individual action result
        if (!is.null(result$individual_results) && length(result$individual_results) > 0) {
          for (i in seq_along(result$individual_results)) {
            ind_result <- result$individual_results[[i]]
            action_name <- if (!is.null(result$actions[i])) result$actions[i] else "unknown"
            success_str <- if (isTRUE(ind_result$success)) "success" else "failed"
            cat(sprintf("  %s: %s (%s)\n", faction, action_name, success_str))
          }
        } else {
          # Fallback: show summary
          cat(sprintf("  %s: %d actions (%d succeeded, %d failed)\n",
                     faction,
                     length(result$actions),
                     result$success_count,
                     result$failure_count))
        }
      } else {
        # Single-action system: original behavior
        cat(sprintf("  %s: %s (%s)\n",
                   faction,
                   result$action,
                   if (result$success) "success" else "failed"))
      }
    }
  }
}

sink()

cat(sprintf("\nSummary saved to: %s\n", summary_file))
cat("\nAll outputs saved in: outputs/\n")
