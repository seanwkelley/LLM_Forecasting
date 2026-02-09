setwd("D:/Northeastern/LLM_Forecasting")
state <- readRDS("outputs/simulation_state.rds")
a <- state$agents[[1]]

cat("Agent 1 name:", a$name, "\n\n")

cat("Checking nested structures:\n\n")

cat("rationality field:\n")
str(a$rationality)

cat("\ncognitive field:\n")
str(a$cognitive)

cat("\ndeception field:\n")
str(a$deception)

cat("\ninformation field:\n")
str(a$information)
