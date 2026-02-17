state_files <- list.files("outputs/multiscenario", pattern = "^scenario_\\d{3}\\.rds$", full.names = TRUE)
for (f in sort(state_files)) {
  s <- readRDS(f)
  id <- gsub(".*scenario_(\\d{3})\\.rds", "\\1", f)
  resp <- s$aggregator_assessments[[1]]$full_response
  # Extract just the PROBABILITY line
  prob_line <- regmatches(resp, regexpr("PROBABILITY:.*", resp))
  cat(sprintf("Scenario %s: %s\n", id, prob_line))
}
