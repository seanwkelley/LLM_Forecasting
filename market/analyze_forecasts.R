# =============================================================================
# Linear Mixed Model Analysis -- Market Forecasting Experiment
#
#   sq_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
#
# Design:
#   - Demographic personas only (+/- ToM)
#   - Two models: llama and qwen (fixed effect)
#   - Period-within-scenario random intercept absorbs shared difficulty
#     across forecasters predicting the same ground truth
#   - Satterthwaite degrees of freedom (fast; KR too slow with 240 nested groups)
#
# Usage:
#   cd D:/Northeastern/LLM_Forecasting
#   Rscript market/analyze_forecasts.R
# =============================================================================

library(lme4)
library(lmerTest)
library(dplyr)

cat(strrep("=", 70), "\n")
cat("MARKET FORECASTING -- LMM ANALYSIS\n")
cat(strrep("=", 70), "\n")

# ---------------------------------------------------------------------------
# Load demographic conditions (llama + qwen)
# ---------------------------------------------------------------------------

base_dir <- file.path("outputs", "market_sim_llama_10s30p_persona")

conditions <- list(
  list(path = file.path(base_dir, "forecasting_demographic", "forecast_results.csv"),
       model = "llama", tom = 0),
  list(path = file.path(base_dir, "forecasting_demographic_tom", "forecast_results.csv"),
       model = "llama", tom = 1),
  list(path = file.path(base_dir, "forecasting_qwen_demographic", "forecast_results.csv"),
       model = "qwen", tom = 0),
  list(path = file.path(base_dir, "forecasting_qwen_demographic_tom", "forecast_results.csv"),
       model = "qwen", tom = 1)
)

frames <- list()
for (cond in conditions) {
  if (!file.exists(cond$path)) {
    cat("[WARN] Missing:", cond$path, "\n")
    next
  }
  df <- read.csv(cond$path, stringsAsFactors = FALSE)
  df$model <- cond$model
  df$tom <- cond$tom
  frames[[length(frames) + 1]] <- df
}

if (length(frames) == 0) {
  stop("No data files found. Run market forecasting first.")
}

dat <- bind_rows(frames)
dat$price_error <- as.numeric(dat$price_error)
dat$sq_error <- dat$price_error^2
dat$scenario_id <- as.factor(dat$scenario_id)
dat$forecaster_id <- as.factor(dat$forecaster_id)
dat$period <- as.factor(dat$period)
dat$model <- factor(dat$model, levels = c("llama", "qwen"))

# Drop rows with missing price predictions
dat <- dat[!is.na(dat$sq_error), ]

cat("\nTotal observations:", nrow(dat), "\n")
cat("Scenarios:", nlevels(dat$scenario_id), "\n")
cat("Periods:", nlevels(dat$period), "\n")
cat("Forecasters:", nlevels(dat$forecaster_id), "\n")
cat("Models:", paste(levels(dat$model), collapse = ", "), "\n")
cat("Scenario-period clusters:", nrow(unique(dat[, c("scenario_id", "period")])), "\n")

# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("DESCRIPTIVE STATISTICS\n")
cat(strrep("=", 70), "\n")

desc <- dat %>%
  group_by(model, tom) %>%
  summarise(
    N = n(),
    accuracy = mean(correct) * 100,
    mae = mean(abs(price_error), na.rm = TRUE),
    mse = mean(sq_error, na.rm = TRUE),
    rmse = sqrt(mean(sq_error, na.rm = TRUE)),
    .groups = "drop"
  )
print(as.data.frame(desc))

cat("\nClass distribution:\n")
print(table(dat$actual))

# ---------------------------------------------------------------------------
# LMM: Squared price error -- interaction model (test tom:model first)
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("LMM: SQUARED PRICE ERROR -- INTERACTION TEST\n")
cat(strrep("=", 70), "\n")

cat("\n--- Interaction model ---\n")
cat("sq_error ~ tom * model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)\n\n")

m_int <- lmer(sq_error ~ tom * model +
                (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id),
              data = dat, REML = TRUE)
print(summary(m_int, ddf = "Satterthwaite"))

cat("\nANOVA (Type III, Kenward-Roger):\n")
print(anova(m_int, ddf = "Satterthwaite"))

# Check if interaction is significant
int_anova <- anova(m_int, ddf = "Satterthwaite")
int_p <- int_anova["tom:model", "Pr(>F)"]
cat(sprintf("\ntom:model interaction p = %.4f", int_p))
if (int_p < 0.05) {
  cat(" --> SIGNIFICANT, retaining interaction\n")
} else {
  cat(" --> not significant, dropping interaction\n")
}

# ---------------------------------------------------------------------------
# LMM: Squared price error -- main effects model
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("LMM: SQUARED PRICE ERROR -- MAIN EFFECTS\n")
cat(strrep("=", 70), "\n")

cat("\n--- Model ---\n")
cat("sq_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)\n\n")

m1 <- lmer(sq_error ~ tom + model +
             (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id),
           data = dat, REML = TRUE)
print(summary(m1, ddf = "Satterthwaite"))

cat("\nANOVA (Type III, Kenward-Roger):\n")
print(anova(m1, ddf = "Satterthwaite"))

# ---------------------------------------------------------------------------
# Model comparison: with vs without period clustering
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("MODEL COMPARISON: PERIOD CLUSTERING\n")
cat(strrep("=", 70), "\n")

cat("\nFitting model WITHOUT period-within-scenario intercept...\n")
m_no_period <- lmer(sq_error ~ tom + model +
                      (1|scenario_id) + (1|forecaster_id),
                    data = dat, REML = FALSE)

m_with_period <- lmer(sq_error ~ tom + model +
                        (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id),
                      data = dat, REML = FALSE)

cat("\nLikelihood ratio test:\n")
print(anova(m_no_period, m_with_period))

# ---------------------------------------------------------------------------
# Random effects decomposition
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("RANDOM EFFECTS DECOMPOSITION\n")
cat(strrep("=", 70), "\n")

vc <- as.data.frame(VarCorr(m1))
resid_var <- sigma(m1)^2
total_var <- sum(vc$vcov) + resid_var

cat("\nWith period-within-scenario clustering:\n")
for (i in 1:nrow(vc)) {
  pct <- vc$vcov[i] / total_var * 100
  cat(sprintf("  %-25s  Var=%12.2f  SD=%10.2f  (%5.1f%%)\n",
              vc$grp[i], vc$vcov[i], vc$sdcor[i], pct))
}
cat(sprintf("  %-25s  Var=%12.2f  SD=%10.2f  (%5.1f%%)\n",
            "Residual", resid_var, sigma(m1), resid_var/total_var*100))

cat(sprintf("\nEffective clustering: %d scenario-period clusters, each with ~%d obs\n",
            nrow(unique(dat[, c("scenario_id", "period")])),
            round(nrow(dat) / nrow(unique(dat[, c("scenario_id", "period")])))))

# Compare to model without period clustering
vc_old <- as.data.frame(VarCorr(m_no_period))
resid_old <- sigma(m_no_period)^2
total_old <- sum(vc_old$vcov) + resid_old
cat(sprintf("\nWithout period clustering: residual = %.1f%% of variance\n",
            resid_old / total_old * 100))
cat(sprintf("With period clustering:    residual = %.1f%% of variance\n",
            resid_var / total_var * 100))

# ---------------------------------------------------------------------------
# LMM: Absolute price error (supplementary)
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("LMM: ABSOLUTE PRICE ERROR (supplementary)\n")
cat(strrep("=", 70), "\n")

dat$abs_error <- abs(dat$price_error)

cat("\n--- Model ---\n")
cat("abs_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)\n\n")

m_abs <- lmer(abs_error ~ tom + model +
                (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id),
              data = dat, REML = TRUE)
print(summary(m_abs, ddf = "Satterthwaite"))

cat("\nANOVA (Type III, Kenward-Roger):\n")
print(anova(m_abs, ddf = "Satterthwaite"))

# ---------------------------------------------------------------------------
# LMM: Percentage price error (supplementary)
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("LMM: SQUARED PERCENTAGE ERROR (supplementary)\n")
cat(strrep("=", 70), "\n")

dat$price_pct_error <- as.numeric(dat$price_pct_error)
dat$sq_pct_error <- dat$price_pct_error^2

cat("\n--- Model ---\n")
cat("sq_pct_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)\n\n")

m_pct <- lmer(sq_pct_error ~ tom + model +
                (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id),
              data = dat, REML = TRUE)
print(summary(m_pct, ddf = "Satterthwaite"))

cat("\nANOVA (Type III, Kenward-Roger):\n")
print(anova(m_pct, ddf = "Satterthwaite"))

# ---------------------------------------------------------------------------
# ToM effect sizes
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("ToM EFFECT SIZES\n")
cat(strrep("=", 70), "\n")

for (mod_name in c("llama", "qwen")) {
  sub <- dat[dat$model == mod_name, ]
  notom <- sub$sq_error[sub$tom == 0]
  tom_vals <- sub$sq_error[sub$tom == 1]
  diff <- mean(tom_vals, na.rm = TRUE) - mean(notom, na.rm = TRUE)
  pooled_sd <- sqrt((var(notom, na.rm = TRUE) + var(tom_vals, na.rm = TRUE)) / 2)
  d <- diff / pooled_sd

  wins <- 0
  for (sid in unique(sub$scenario_id)) {
    s0 <- mean(sub$sq_error[sub$tom == 0 & sub$scenario_id == sid], na.rm = TRUE)
    s1 <- mean(sub$sq_error[sub$tom == 1 & sub$scenario_id == sid], na.rm = TRUE)
    if (s1 < s0) wins <- wins + 1
  }

  cat(sprintf("\n%s (sq_error):\n", mod_name))
  cat(sprintf("  no-ToM: %.2f | ToM: %.2f | diff: %+.2f | d=%.3f | ToM wins %d/%d scenarios\n",
              mean(notom, na.rm=TRUE), mean(tom_vals, na.rm=TRUE), diff, d, wins,
              length(unique(sub$scenario_id))))
}

# Overall (across models)
notom_all <- dat$sq_error[dat$tom == 0]
tom_all <- dat$sq_error[dat$tom == 1]
diff_all <- mean(tom_all, na.rm=TRUE) - mean(notom_all, na.rm=TRUE)
sd_all <- sqrt((var(notom_all, na.rm=TRUE) + var(tom_all, na.rm=TRUE)) / 2)
d_all <- diff_all / sd_all
cat(sprintf("\nOverall (sq_error):\n"))
cat(sprintf("  no-ToM: %.2f | ToM: %.2f | diff: %+.2f | d=%.3f\n",
            mean(notom_all, na.rm=TRUE), mean(tom_all, na.rm=TRUE), diff_all, d_all))

# ---------------------------------------------------------------------------
# Per-forecaster breakdown
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("PER-FORECASTER PERFORMANCE\n")
cat(strrep("=", 70), "\n")

cat(sprintf("\n%-25s | %-6s | %5s | %8s | %8s | %4s\n",
            "Forecaster", "Model", "ToM", "MSE", "MAE", "N"))
cat(sprintf("%-25s | %-6s | %5s | %8s | %8s | %4s\n",
            strrep("-", 25), strrep("-", 6), strrep("-", 5),
            strrep("-", 8), strrep("-", 8), strrep("-", 4)))

for (fid in levels(dat$forecaster_id)) {
  for (mod_name in levels(dat$model)) {
    for (t in c(0, 1)) {
      sub <- dat[dat$forecaster_id == fid & dat$model == mod_name & dat$tom == t, ]
      if (nrow(sub) == 0) next
      cat(sprintf("%-25s | %-6s | %5s | %8.2f | %8.2f | %4d\n",
                  fid, mod_name, ifelse(t, "yes", "no"),
                  mean(sub$sq_error, na.rm=TRUE),
                  mean(abs(sub$price_error), na.rm=TRUE),
                  nrow(sub)))
    }
  }
}

cat("\n", strrep("=", 70), "\n", sep = "")
cat("ANALYSIS COMPLETE\n")
cat(strrep("=", 70), "\n")
