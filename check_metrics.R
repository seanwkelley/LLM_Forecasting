# Check actual simulation metric values across all periods
state <- readRDS("outputs/simulation_state.rds")

cat("Period | Mil.Balance | Territory | Crisis | Sanctions | Intl.Support\n")
cat("-------|-------------|-----------|--------|-----------|-------------\n")

for (p in 1:state$current_period) {
  s <- state$state_history[[p]]$scenario_state
  cat(sprintf("  %2d   |   %6.3f    |   %5.3f   | %5.1f  |   %5.3f   |   %5.3f\n",
    p, s$military_balance, s$territory_controlled, s$crisis_level, s$sanctions_level, s$international_support))
}
