# Inference layer for the hidden-confounder world (design doc 16.3).
# House rules: all statistics in R; the SCENARIO (seed) is the replication
# unit -> scenario random intercepts throughout. Every test is a
# two-condition comparison on stacked data — never a one-sample test
# against zero.
#
# Input: conf_master.csv from analyze_confounder.py (one row per
# scenario x checkpoint: p_see_A, p_do_A, p_do_C, star_do_A,
# spurious_do_A, star_do_C, confound_gap).
# Usage: Rscript analyze_confounder.R <run_dir>

suppressPackageStartupMessages({ library(nlme) })

args <- commandArgs(trailingOnly = TRUE)
run_dir <- if (length(args) >= 1) args[1] else "outputs/confounder_gptoss"
d <- read.csv(file.path(run_dir, "conf_master.csv"))
d$scenario <- factor(d$scenario)
d <- d[!is.na(d$p_see_A) & !is.na(d$p_do_A), ]
cat(sprintf("scenario-checkpoints: %d | scenarios: %d\n",
            nrow(d), nlevels(droplevels(d$scenario))))

## 1. Trap vs truth on the set-X1 question.
##    Stack the two distances per item; a negative `targetspurious`
##    coefficient means the answers sit closer to the spurious
##    (observational) value than to the correct interventional one.
long1 <- rbind(
  data.frame(scenario = d$scenario, ck = d$checkpoint,
             err = abs(d$p_do_A - d$star_do_A),     target = "truth"),
  data.frame(scenario = d$scenario, ck = d$checkpoint,
             err = abs(d$p_do_A - d$spurious_do_A), target = "spurious"))
long1$target <- factor(long1$target, levels = c("truth", "spurious"))
m1 <- lme(err ~ target, random = ~1 | scenario, data = long1,
          method = "REML")
cat("\n--- [1] |p(do_A) - target| ~ target, (1|scenario) ---\n")
cat("targetspurious < 0 = answers land closer to the confounded value\n")
print(summary(m1)$tTable)

## 2. Does the model separate seeing from setting as much as the truth
##    requires? Stack the model's see/do divergence against the true
##    divergence on the same items; `sourcemodel` near -(true divergence)
##    means no separation at all, near 0 means full separation.
long2 <- rbind(
  data.frame(scenario = d$scenario, ck = d$checkpoint,
             div = abs(d$p_see_A - d$p_do_A),       source = "model"),
  data.frame(scenario = d$scenario, ck = d$checkpoint,
             div = abs(d$star_do_A - d$spurious_do_A), source = "true"))
long2$source <- factor(long2$source, levels = c("true", "model"))
m2 <- lme(div ~ source, random = ~1 | scenario, data = long2,
          method = "REML")
cat("\n--- [2] see/do divergence ~ source (true vs model), (1|scenario) ---\n")
cat("sourcemodel = model divergence minus required divergence\n")
print(summary(m2)$tTable)

## 3. Necessity control: is failure specific to the confounded question?
##    Compare error on set-X1 (must ignore the value) with error on set-X3
##    (must use it) within the same scenario-checkpoints.
dc <- d[!is.na(d$p_do_C) & d$p_do_C != "", ]
if (nrow(dc) > 0) {
  dc$p_do_C <- as.numeric(dc$p_do_C)
  dc$star_do_C <- as.numeric(dc$star_do_C)
  long3 <- rbind(
    data.frame(scenario = dc$scenario, ck = dc$checkpoint,
               err = abs(dc$p_do_A - dc$star_do_A), query = "set_X1"),
    data.frame(scenario = dc$scenario, ck = dc$checkpoint,
               err = abs(dc$p_do_C - dc$star_do_C), query = "set_X3"))
  long3$query <- factor(long3$query, levels = c("set_X3", "set_X1"))
  m3 <- lme(err ~ query, random = ~1 | scenario, data = long3,
            method = "REML")
  cat("\n--- [3] |p - p*| ~ query (set_X3 vs set_X1), (1|scenario) ---\n")
  cat("queryset_X1 > 0 = failure is specific to confounding, not to\n")
  cat("interventions in general\n")
  print(summary(m3)$tTable)
}

cat("\ndescriptives\n")
cat(sprintf("  mean certified gap:        %.3f\n", mean(d$confound_gap)))
cat(sprintf("  mean model see/do div:     %.3f\n",
            mean(abs(d$p_see_A - d$p_do_A))))
cat(sprintf("  mean |p(do_A) - truth|:    %.3f\n",
            mean(abs(d$p_do_A - d$star_do_A))))
cat(sprintf("  mean |p(do_A) - spurious|: %.3f\n",
            mean(abs(d$p_do_A - d$spurious_do_A))))
