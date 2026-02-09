# Analyze simulation results and create probability plot

library(ggplot2)

setwd("D:/Northeastern/LLM_Forecasting")

# Read the assessments CSV
assessments <- read.csv("outputs/assessments.csv", stringsAsFactors = FALSE)

cat("=== SIMULATION ANALYSIS ===\n\n")

# 1. Probability trajectory
cat("--- Probability of Minor Power Collapse Over Time ---\n")
print(assessments[, c("period", "probability", "confidence", "trend")])

# 2. Create the plot
p <- ggplot(assessments, aes(x = period, y = probability)) +
  geom_line(color = "#2563eb", size = 1.2) +
  geom_point(aes(color = confidence), size = 3) +
  scale_color_manual(values = c("HIGH" = "#16a34a", "MEDIUM" = "#eab308", "LOW" = "#dc2626")) +
  scale_y_continuous(labels = scales::percent_format(), limits = c(0, 0.5)) +
  scale_x_continuous(breaks = 1:10) +
  labs(
    title = "Probability of Minor Power (Tethys) Government Collapse",
    subtitle = "10-Period Wargame Simulation Results",
    x = "Period",
    y = "Collapse Probability",
    color = "Confidence"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(face = "bold", size = 14),
    plot.subtitle = element_text(color = "gray50"),
    panel.grid.minor = element_blank()
  ) +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "gray70", alpha = 0.7) +
  annotate("text", x = 1.5, y = 0.48, label = "50% threshold", color = "gray50", size = 3)

# Save plot
ggsave("outputs/collapse_probability_plot.png", p, width = 10, height = 6, dpi = 150)
cat("\nPlot saved to: outputs/collapse_probability_plot.png\n")

# 3. Summary statistics
cat("\n--- Summary Statistics ---\n")
cat("Starting probability:", assessments$probability[1], "\n")
cat("Ending probability:", assessments$probability[nrow(assessments)], "\n")
cat("Change:", assessments$probability[nrow(assessments)] - assessments$probability[1], "\n")
cat("Min probability:", min(assessments$probability), "(Period", which.min(assessments$probability), ")\n")
cat("Max probability:", max(assessments$probability), "(Period", which.max(assessments$probability), ")\n")

# 4. Trend analysis
cat("\n--- Trend Analysis ---\n")
trend_table <- table(assessments$trend)
print(trend_table)

cat("\nDone!\n")
