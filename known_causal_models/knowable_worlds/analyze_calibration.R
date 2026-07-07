# Inference layer for the Knowable Worlds study (audit item C1/C6).
# House rules: all statistics in R; the SCM is the replication unit, so every
# model carries an SCM random intercept (with only 5 clusters in the pilot,
# treat p-values as provisional until the scale-up run).
#
# Input: master_long.csv from analyze_calibration.py.
# Usage: Rscript analyze_calibration.R <run_dir>

suppressPackageStartupMessages({ library(nlme) })

args <- commandArgs(trailingOnly = TRUE)
run_dir <- if (length(args) >= 1) args[1] else "outputs/pilot_gptoss"
d <- read.csv(file.path(run_dir, "master_long.csv"))

d$abs_err <- abs(d$p - d$p_star)
d$rung <- factor(d$rung)
d$kind <- factor(d$kind)
d$scm  <- factor(d$scm_seed)
d$confounded <- d$confounded %in% c("True", "TRUE", "true")

cat(sprintf("rows: %d | SCM clusters: %d (pilot: inference is provisional)\n",
            nrow(d), nlevels(d$scm)))

## 1. Quantity ladder, interventional items: does mechanism knowledge reduce error?
q <- droplevels(subset(d, kind == "interventional" &
                          rung %in% c("L0", "L1", "L2", "L3")))
q$rung <- relevel(q$rung, ref = "L0")
m1 <- lme(abs_err ~ rung, random = ~1 | scm, data = q, method = "REML")
cat("\n--- [1] abs error ~ rung (interventional, ref L0), (1|scm) ---\n")
print(round(summary(m1)$tTable, 4))

## 2. Trap-attraction: on confounded items, does the given TRUE graph (L1/L2)
##    pull answers toward the conditioning trap relative to L0?
##    DV: trap_pull = d(truth) - d(trap); positive = closer to the trap.
tr <- droplevels(subset(d, confounded & kind == "interventional" &
                           rung %in% c("L0", "L1", "L2", "L3") &
                           !is.na(p_cond)))
tr$trap_pull <- abs(tr$p - tr$p_star) - abs(tr$p - tr$p_cond)
tr$rung <- relevel(tr$rung, ref = "L0")
if (nrow(tr) > 12) {
  m2 <- lme(trap_pull ~ rung, random = ~1 | scm, data = tr, method = "REML")
  cat("\n--- [2] trap_pull ~ rung (confounded do items, ref L0), (1|scm) ---\n")
  cat("positive coefficient = the rung pulls answers TOWARD the trap\n")
  print(round(summary(m2)$tTable, 4))
} else cat("\n[2] trap model skipped: n too small (need scale-up)\n")

## 3. Counterfactuals: rung effect on |error| (truth is deterministic 0/1)
cf <- droplevels(subset(d, kind == "counterfactual" &
                           rung %in% c("L0", "L1", "L2", "L3")))
cf$rung <- relevel(cf$rung, ref = "L0")
if (nrow(cf) > 12) {
  m3 <- lme(abs_err ~ rung, random = ~1 | scm, data = cf, method = "REML")
  cat("\n--- [3] abs error ~ rung (counterfactual, ref L0), (1|scm) ---\n")
  print(round(summary(m3)$tTable, 4))
}

## 4. Model vs oracle: is the model's L1 error above the OLS floor?
ol <- droplevels(subset(d, kind == "interventional" & rung == "L1" &
                           !is.na(p_ols)))
if (nrow(ol) > 8) {
  ol$excess <- abs(ol$p - ol$p_star) - abs(ol$p_ols - ol$p_star)
  m4 <- lme(excess ~ 1, random = ~1 | scm, data = ol, method = "REML")
  cat("\n--- [4] model error minus OLS-floor error at L1 (intercept test) ---\n")
  print(round(summary(m4)$tTable, 4))
}

## 5. Wrong-graph obedience: at L1w, is the model closer to the wrong-model
##    oracle than to the truth? DV: d(wrong) - d(truth); negative = obeys wrong map.
wr <- droplevels(subset(d, rung == "L1w" & kind == "interventional" &
                           !is.na(p_wrong)))
if (nrow(wr) > 8) {
  wr$obey <- abs(wr$p - wr$p_wrong) - abs(wr$p - wr$p_star)
  m5 <- lme(obey ~ 1, random = ~1 | scm, data = wr, method = "REML")
  cat("\n--- [5] L1w obedience: d(wrong-model) - d(truth); negative = follows the wrong map ---\n")
  print(round(summary(m5)$tTable, 4))
} else cat("\n[5] L1w model skipped: n too small\n")

cat("\nNOTE: 5 SCM clusters -> all of the above is PROVISIONAL; rerun after scale-up.\n")
