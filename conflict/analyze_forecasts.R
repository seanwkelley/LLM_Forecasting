# =============================================================================
# Linear Mixed Model Analysis -- Conflict Forecasting Experiment
#
#   sq_ei_error ~ tom + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
#
# Design:
#   - Demographic personas only (+/- ToM)
#   - Single model (llama) -- no model fixed effect
#   - Period-within-scenario random intercept absorbs shared difficulty
#     across forecasters predicting the same ground truth
#   - Satterthwaite degrees of freedom (fast; KR too slow with 240 nested groups)
#
# Usage:
#   cd D:/Northeastern/LLM_Forecasting
#   Rscript conflict/analyze_forecasts.R
# =============================================================================

library(lme4)
library(lmerTest)
library(dplyr)

cat(strrep("=", 70), "\n")
cat("CONFLICT FORECASTING -- LMM ANALYSIS\n")
cat(strrep("=", 70), "\n")

# ---------------------------------------------------------------------------
# Load demographic conditions only
# ---------------------------------------------------------------------------

base_dir <- file.path("outputs", "conflict_llama_persona")

conditions <- list(
  list(path = file.path(base_dir, "forecasting_demographic", "forecast_results.csv"),
       tom = 0),
  list(path = file.path(base_dir, "forecasting_demographic_tom", "forecast_results.csv"),
       tom = 1)
)

frames <- list()
for (cond in conditions) {
  if (!file.exists(cond$path)) {
    cat("[WARN] Missing:", cond$path, "\n")
    next
  }
  df <- read.csv(cond$path, stringsAsFactors = FALSE)
  df$tom <- cond$tom
  frames[[length(frames) + 1]] <- df
}

if (length(frames) == 0) {
  stop("No data files found. Run conflict forecasting first.")
}

dat <- bind_rows(frames)
dat$ei_error <- as.numeric(dat$ei_error)
dat$sq_ei_error <- dat$ei_error^2
dat$scenario_id <- as.factor(dat$scenario_id)
dat$forecaster_id <- as.factor(dat$forecaster_id)
dat$period <- as.factor(dat$period)

# Drop rows with missing EI predictions
dat <- dat[!is.na(dat$sq_ei_error), ]

cat("\nTotal observations:", nrow(dat), "\n")
cat("Scenarios:", nlevels(dat$scenario_id), "\n")
cat("Periods:", nlevels(dat$period), "\n")
cat("Forecasters:", nlevels(dat$forecaster_id), "\n")
cat("Scenario-period clusters:", nrow(unique(dat[, c("scenario_id", "period")])), "\n")

# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("DESCRIPTIVE STATISTICS\n")
cat(strrep("=", 70), "\n")

desc <- dat %>%
  group_by(tom) %>%
  summarise(
    N = n(),
    accuracy = mean(correct) * 100,
    ei_mae = mean(abs(ei_error), na.rm = TRUE),
    ei_mse = mean(sq_ei_error, na.rm = TRUE),
    ei_rmse = sqrt(mean(sq_ei_error, na.rm = TRUE)),
    .groups = "drop"
  )
print(as.data.frame(desc))

cat("\nClass distribution:\n")
print(table(dat$actual))

# ---------------------------------------------------------------------------
# LMM: Squared EI error (main analysis)
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("LMM: SQUARED EI ERROR\n")
cat(strrep("=", 70), "\n")

cat("\n--- Model ---\n")
cat("sq_ei_error ~ tom + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)\n\n")

m1 <- lmer(sq_ei_error ~ tom +
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
m_no_period <- lmer(sq_ei_error ~ tom +
                      (1|scenario_id) + (1|forecaster_id),
                    data = dat, REML = FALSE)

m_with_period <- lmer(sq_ei_error ~ tom +
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
  cat(sprintf("  %-25s  Var=%10.4f  SD=%8.4f  (%5.1f%%)\n",
              vc$grp[i], vc$vcov[i], vc$sdcor[i], pct))
}
cat(sprintf("  %-25s  Var=%10.4f  SD=%8.4f  (%5.1f%%)\n",
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
# LMM: Absolute EI error (supplementary)
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("LMM: ABSOLUTE EI ERROR (supplementary)\n")
cat(strrep("=", 70), "\n")

dat$abs_ei_error <- abs(dat$ei_error)

cat("\n--- Model ---\n")
cat("abs_ei_error ~ tom + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)\n\n")

m_abs <- lmer(abs_ei_error ~ tom +
                (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id),
              data = dat, REML = TRUE)
print(summary(m_abs, ddf = "Satterthwaite"))

cat("\nANOVA (Type III, Kenward-Roger):\n")
print(anova(m_abs, ddf = "Satterthwaite"))

# ---------------------------------------------------------------------------
# ToM effect sizes
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("ToM EFFECT SIZES\n")
cat(strrep("=", 70), "\n")

notom <- dat$sq_ei_error[dat$tom == 0]
tom_vals <- dat$sq_ei_error[dat$tom == 1]
diff <- mean(tom_vals, na.rm = TRUE) - mean(notom, na.rm = TRUE)
pooled_sd <- sqrt((var(notom, na.rm = TRUE) + var(tom_vals, na.rm = TRUE)) / 2)
d <- diff / pooled_sd

wins <- 0
for (sid in unique(dat$scenario_id)) {
  s0 <- mean(dat$sq_ei_error[dat$tom == 0 & dat$scenario_id == sid], na.rm = TRUE)
  s1 <- mean(dat$sq_ei_error[dat$tom == 1 & dat$scenario_id == sid], na.rm = TRUE)
  if (s1 < s0) wins <- wins + 1
}

cat(sprintf("\nSq EI error:\n"))
cat(sprintf("  no-ToM: %.4f | ToM: %.4f | diff: %+.4f | d=%.3f | ToM wins %d/%d scenarios\n",
            mean(notom, na.rm=TRUE), mean(tom_vals, na.rm=TRUE), diff, d, wins,
            length(unique(dat$scenario_id))))

# Absolute error effect size
notom_abs <- dat$abs_ei_error[dat$tom == 0]
tom_abs <- dat$abs_ei_error[dat$tom == 1]
diff_abs <- mean(tom_abs, na.rm=TRUE) - mean(notom_abs, na.rm=TRUE)
sd_abs <- sqrt((var(notom_abs, na.rm=TRUE) + var(tom_abs, na.rm=TRUE)) / 2)
d_abs <- diff_abs / sd_abs

cat(sprintf("\nAbs EI error:\n"))
cat(sprintf("  no-ToM: %.4f | ToM: %.4f | diff: %+.4f | d=%.3f\n",
            mean(notom_abs, na.rm=TRUE), mean(tom_abs, na.rm=TRUE), diff_abs, d_abs))

# ---------------------------------------------------------------------------
# Per-forecaster breakdown
# ---------------------------------------------------------------------------

cat("\n", strrep("=", 70), "\n", sep = "")
cat("PER-FORECASTER PERFORMANCE\n")
cat(strrep("=", 70), "\n")

cat(sprintf("\n%-25s | %5s | %10s | %10s | %4s\n",
            "Forecaster", "ToM", "MSE", "MAE", "N"))
cat(sprintf("%-25s | %5s | %10s | %10s | %4s\n",
            strrep("-", 25), strrep("-", 5),
            strrep("-", 10), strrep("-", 10), strrep("-", 4)))

for (fid in levels(dat$forecaster_id)) {
  for (t in c(0, 1)) {
    sub <- dat[dat$forecaster_id == fid & dat$tom == t, ]
    if (nrow(sub) == 0) next
    cat(sprintf("%-25s | %5s | %10.4f | %10.4f | %4d\n",
                fid, ifelse(t, "yes", "no"),
                mean(sub$sq_ei_error, na.rm=TRUE),
                mean(sub$abs_ei_error, na.rm=TRUE),
                nrow(sub)))
  }
}

cat("\n", strrep("=", 70), "\n", sep = "")
cat("ANALYSIS COMPLETE\n")
cat(strrep("=", 70), "\n")
