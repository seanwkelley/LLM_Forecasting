library(tidyverse)

df <- read_csv("outputs/sensitivity/causal/persuasiveness_ratings_gpt-oss.csv",
               show_col_types = FALSE)

df <- df %>%
  mutate(
    importance_bin = ifelse(importance == "high", 1, 0),
    direction = ifelse(grepl("negate", probe_type), "negate", "strengthen")
  )

cat("\n=== Persuasiveness by importance level ===\n")
df %>%
  group_by(importance) %>%
  summarise(mean = mean(persuasiveness), sd = sd(persuasiveness), n = n()) %>%
  print()

cat("\n=== Persuasiveness by probe_type ===\n")
df %>%
  group_by(probe_type) %>%
  summarise(mean = mean(persuasiveness), sd = sd(persuasiveness), n = n()) %>%
  print()

cat("\n=== Persuasiveness by direction ===\n")
df %>%
  group_by(direction) %>%
  summarise(mean = mean(persuasiveness), sd = sd(persuasiveness), n = n()) %>%
  print()

cat("\n=== Mann-Whitney U: persuasiveness ~ importance ===\n")
wt <- wilcox.test(persuasiveness ~ importance, data = df)
print(wt)

cat("\n=== OLS: absolute_shift ~ importance + persuasiveness ===\n")
m1 <- lm(absolute_shift ~ importance_bin + persuasiveness, data = df)
summary(m1)

cat("\n=== OLS: absolute_shift ~ importance + persuasiveness + direction ===\n")
m2 <- lm(absolute_shift ~ importance_bin + persuasiveness + direction, data = df)
summary(m2)

cat("\n=== Persuasiveness by importance x direction ===\n")
df %>%
  group_by(importance, direction) %>%
  summarise(mean = mean(persuasiveness), sd = sd(persuasiveness), n = n(), .groups = "drop") %>%
  print()
