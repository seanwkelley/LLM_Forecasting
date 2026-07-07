# Inference layer for the dynamic (regime-shift) arm.
# House rules: all statistics in R; the SCENARIO (seed x change_type) is the
# replication unit -> scenario random intercepts throughout. The pilot has 12
# scenarios; treat p-values as provisional until a scale-up.
#
# Input: dyn_master.csv + dyn_structure.csv from analyze_dynamic.py.
# Usage: Rscript analyze_dynamic.R <run_dir>

suppressPackageStartupMessages({ library(nlme) })

args <- commandArgs(trailingOnly = TRUE)
run_dir <- if (length(args) >= 1) args[1] else "outputs/dynamic_gptoss"
d <- read.csv(file.path(run_dir, "dyn_master.csv"))
s <- read.csv(file.path(run_dir, "dyn_structure.csv"))

d$abs_err <- abs(d$p - d$p_star)
d$scenario <- factor(d$scenario)
d$affected <- d$affected %in% c("True", "TRUE", "true")
d$phase <- factor(d$phase, levels = c("pre", "post"))
s$scenario <- factor(s$scenario)

cat(sprintf("forecast rows: %d | structure rows: %d | scenarios: %d\n",
            nrow(d), nrow(s), nlevels(d$scenario)))

## 1. Disruption test: does error jump after the change, and ONLY on the
##    affected node? (phase x affected interaction is the certified signature)
m1 <- lme(abs_err ~ phase * affected, random = ~1 | scenario,
          data = d, method = "REML")
cat("\n--- [1] abs error ~ phase * affected, (1|scenario) ---\n")
cat("phasepost:affectedTRUE > 0 = change disrupts affected node specifically\n")
print(round(summary(m1)$tTable, 4))

## 2. Perseveration: post-change affected items with a detectable gap.
##    DV: persev = d(truth) - d(stale); positive = closer to the STALE model.
##    rel_time slope < 0 = letting go of the old world with more evidence.
pv <- droplevels(subset(d, affected & phase == "post" & regime_gap >= 0.5))
if (nrow(pv) > 10) {
  pv$persev <- abs(pv$p - pv$p_star) - abs(pv$p - pv$p_stale)
  m2 <- lme(persev ~ rel_time, random = ~1 | scenario, data = pv,
            method = "REML")
  cat("\n--- [2] perseveration ~ rel_time (post, affected, gap>=0.5) ---\n")
  cat("intercept > 0 = answers sit closer to the stale mechanism than truth\n")
  print(round(summary(m2)$tTable, 4))
} else cat("\n[2] perseveration model skipped: n too small\n")

## 3. Model vs the recency baseline: excess error over the 20-period
##    sliding-window refit, post-change affected items.
ex <- droplevels(subset(d, affected & phase == "post" & !is.na(p_window)))
if (nrow(ex) > 10) {
  ex$excess <- abs(ex$p - ex$p_star) - abs(ex$p_window - ex$p_star)
  tryCatch({
    m3 <- lme(excess ~ 1, random = ~1 | scenario, data = ex, method = "REML")
    cat("\n--- [3] model error minus sliding-window-refit error (post, affected) ---\n")
    print(round(summary(m3)$tTable, 4))
  }, error = function(e) cat("\n[3] failed (degenerate DV?):",
                             conditionMessage(e), "\n"))
}

## 4. Structure tracking: does the reported graph move toward the NEW regime?
##    DV: track = F1(new) - F1(old); positive post-change = updated beliefs.
if (nrow(s) > 10) {
  s$track <- s$f1_r2 - s$f1_r1
  s$post <- as.integer(s$rel_time >= 0)
  tryCatch({
    m4 <- lme(track ~ post, random = ~1 | scenario, data = s, method = "REML")
    cat("\n--- [4] (F1 new - F1 old) ~ post, (1|scenario) ---\n")
    cat("post > 0 = stated structure tracks the change at all\n")
    print(round(summary(m4)$tTable, 4))
  }, error = function(e) cat("\n[4] failed (degenerate DV?):",
                             conditionMessage(e), "\n"))
  ## 4c. the sharp metric: the changed SLOT itself (whole-graph F1 is
  ##     dominated by the ~17 shared edges; this isolates the one that moved)
  if ("changed_state" %in% names(s)) {
    s$new_state <- as.integer(s$changed_state == "new")
    tryCatch({
      m4c <- lme(new_state ~ post, random = ~1 | scenario, data = s,
                 method = "REML")
      cat("\n--- [4c] P(changed slot stated as in the NEW graph) ~ post ---\n")
      print(round(summary(m4c)$tTable, 4))
    }, error = function(e) cat("\n[4c] failed (degenerate DV?):",
                               conditionMessage(e), "\n"))
  }
  ## 4b. latency: among post rows only, does tracking grow with distance?
  sp <- droplevels(subset(s, rel_time >= 0))
  if (nrow(sp) > 10) {
    tryCatch({
      m4b <- lme(track ~ rel_time, random = ~1 | scenario, data = sp,
                 method = "REML")
      cat("\n--- [4b] tracking ~ rel_time (post only): latency slope ---\n")
      print(round(summary(m4b)$tTable, 4))
    }, error = function(e) cat("\n[4b] failed (degenerate DV?):",
                               conditionMessage(e), "\n"))
  }
}

cat("\nNOTE: pilot scenario count is small -> all of the above is PROVISIONAL.\n")
