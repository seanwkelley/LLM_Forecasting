# ============================================================================
# Difficulty-ELO Regression Analysis
#
# Tests whether LLM-judged question difficulty (ELO) predicts belief
# sensitivity metrics after controlling for |p - 0.5|.
#
# Usage:
#   Rscript forecast_bench/difficulty_regression.R
# ============================================================================

library(lme4)
library(lmerTest)  # p-values for lmer via Satterthwaite
library(car)       # vif()
# ── Load data ────────────────────────────────────────────────────────────────
data_path <- file.path("outputs", "sensitivity", "causal",
                        "difficulty_regression_data.csv")
if (!file.exists(data_path)) {
  stop("Data file not found. Run prep_difficulty_regression.py first.")
}

df <- read.csv(data_path, stringsAsFactors = FALSE)
cat(sprintf("Loaded %d rows (%d questions × %d models)\n",
            nrow(df), length(unique(df$question_id)), length(unique(df$model))))

# ── Preprocessing ────────────────────────────────────────────────────────────
df$model <- as.factor(df$model)

# Standardize ELO for interpretable coefficients
df$elo_z <- scale(df$elo)[, 1]
df$dist50_z <- scale(df$abs_dist_from_50)[, 1]

cat("\nELO summary:\n")
print(summary(df$elo))
cat(sprintf("\nCorrelation ELO vs |p-0.5|: r = %.3f\n",
            cor(df$elo, df$abs_dist_from_50, use = "complete.obs")))

# ── Helper: fit mixed model and print summary ────────────────────────────────
fit_and_report <- function(formula_str, dv_name, data) {
  cat(sprintf("\n%s\n%s\n", paste(rep("=", 70), collapse = ""),
              paste("DV:", dv_name)))

  # Drop rows with NA in the DV
  dv_col <- all.vars(as.formula(formula_str))[1]
  sub <- data[!is.na(data[[dv_col]]), ]
  n_obs <- nrow(sub)
  n_q <- length(unique(sub$question_id))
  cat(sprintf("  N = %d obs, %d questions\n", n_obs, n_q))

  if (n_obs < 20 || n_q < 10) {
    cat("  Skipping: too few observations\n")
    return(NULL)
  }

  # Fit mixed model: random intercept for model
  m <- lmer(as.formula(formula_str), data = sub, REML = TRUE)

  cat("\nFixed effects:\n")
  print(summary(m)$coefficients, digits = 4)

  # Marginal & conditional R² (Nakagawa & Schielzeth, manual)
  vc <- as.data.frame(VarCorr(m))
  var_re <- sum(vc$vcov[vc$grp != "Residual"])
  var_resid <- vc$vcov[vc$grp == "Residual"]
  var_fe <- var(predict(m, re.form = NA))  # variance of fixed-effect predictions
  r2m <- var_fe / (var_fe + var_re + var_resid)
  r2c <- (var_fe + var_re) / (var_fe + var_re + var_resid)
  cat(sprintf("\nMarginal R² = %.4f  (fixed effects only)\n", r2m))
  cat(sprintf("Conditional R² = %.4f  (fixed + random)\n", r2c))

  # VIF check
  v <- tryCatch(vif(m), error = function(e) NULL)
  if (!is.null(v)) {
    cat("\nVIF:\n")
    print(v, digits = 3)
  }

  # Compare: ELO-only vs dist50-only vs both (likelihood ratio)
  cat("\n--- Model comparison (ML for LRT) ---\n")
  m_both <- lmer(as.formula(formula_str), data = sub, REML = FALSE)
  f_elo <- gsub("\\+ dist50_z", "", formula_str)
  f_dist <- gsub("elo_z \\+\\s*", "", formula_str)
  m_elo <- lmer(as.formula(f_elo), data = sub, REML = FALSE)
  m_dist <- lmer(as.formula(f_dist), data = sub, REML = FALSE)

  cat(sprintf("  AIC(elo_only)  = %.1f\n", AIC(m_elo)))
  cat(sprintf("  AIC(dist_only) = %.1f\n", AIC(m_dist)))
  cat(sprintf("  AIC(both)      = %.1f\n", AIC(m_both)))

  # LRT: does adding ELO to dist50-only improve fit?
  lr <- anova(m_dist, m_both)
  cat(sprintf("\n  LRT adding ELO to dist50 model: χ²(1) = %.3f, p = %.4f\n",
              lr$Chisq[2], lr$`Pr(>Chisq)`[2]))

  return(m)
}

# ============================================================================
# 1. Mean absolute shift ~ difficulty + distance from 50%
# ============================================================================
m1 <- fit_and_report(
  "mean_shift ~ elo_z + dist50_z + (1|model)",
  "Mean absolute shift (overall responsiveness)",
  df
)

# ============================================================================
# 2. SSR ~ difficulty + distance from 50%
# ============================================================================
m2 <- fit_and_report(
  "ssr ~ elo_z + dist50_z + (1|model)",
  "Structural Sensitivity Ratio (SSR)",
  df
)

# ============================================================================
# 3. Within-question Kendall τ ~ difficulty + distance from 50%
# ============================================================================
m3 <- fit_and_report(
  "within_tau ~ elo_z + dist50_z + (1|model)",
  "Within-question Kendall τ (structural faithfulness)",
  df
)

# ============================================================================
# 4. SPP ~ difficulty + distance from 50%
# ============================================================================
m4 <- fit_and_report(
  "spp ~ elo_z + dist50_z + (1|model)",
  "Shortest-Path Premium (SPP)",
  df
)

# ============================================================================
# 5. Asymmetry index ~ difficulty + distance from 50%
# ============================================================================
m5 <- fit_and_report(
  "asymmetry_index ~ elo_z + dist50_z + (1|model)",
  "Asymmetry index (negate/strengthen ratio)",
  df
)

# ============================================================================
# 6. Reasoning coherence (judge rating) ~ difficulty + distance from 50%
# ============================================================================
m6 <- fit_and_report(
  "mean_judge_rating ~ elo_z + dist50_z + (1|model)",
  "Mean reasoning judge rating (1-5)",
  df
)

# ============================================================================
# 7. Expressed uncertainty (uncertainty judge) ~ difficulty + distance from 50%
# ============================================================================
m7 <- fit_and_report(
  "mean_uncertainty_rating ~ elo_z + dist50_z + (1|model)",
  "Mean uncertainty judge rating (1-5, expressed hedging)",
  df
)

# ============================================================================
# 8. Validation: does ELO predict inter-model disagreement?
# ============================================================================
cat(sprintf("\n%s\nValidation: ELO vs inter-model SD of initial prob\n",
            paste(rep("=", 70), collapse = "")))

# Use question-level data (one row per question, averaged across models)
q_level <- aggregate(
  cbind(elo, inter_model_sd, abs_dist_from_50) ~ question_id,
  data = df, FUN = mean, na.rm = TRUE
)
q_level <- q_level[!is.na(q_level$inter_model_sd), ]
cat(sprintf("  N = %d questions\n", nrow(q_level)))

if (nrow(q_level) >= 10) {
  r_elo_sd <- cor.test(q_level$elo, q_level$inter_model_sd, method = "spearman")
  cat(sprintf("  Spearman ρ(ELO, inter-model SD): %.3f (p = %.4f)\n",
              r_elo_sd$estimate, r_elo_sd$p.value))

  # Partial correlation: ELO → inter-model SD controlling for |p-0.5|
  m_val <- lm(inter_model_sd ~ scale(elo) + scale(abs_dist_from_50),
              data = q_level)
  cat("\n  Linear model: inter_model_sd ~ elo + |p-0.5|\n")
  print(summary(m_val)$coefficients, digits = 4)
  cat(sprintf("  R² = %.4f\n", summary(m_val)$r.squared))
}

# ============================================================================
# 9. Brier score ~ difficulty (does difficulty predict accuracy?)
# ============================================================================
cat(sprintf("\n%s\nBrier score ~ difficulty\n",
            paste(rep("=", 70), collapse = "")))

df_brier <- df[!is.na(df$brier), ]
if (nrow(df_brier) >= 20) {
  m_brier <- fit_and_report(
    "brier ~ elo_z + dist50_z + (1|model)",
    "Brier score (forecasting accuracy)",
    df_brier
  )
}

# ============================================================================
# Summary table
# ============================================================================
cat(sprintf("\n\n%s\nSUMMARY: ELO coefficient across all DVs\n%s\n",
            paste(rep("=", 70), collapse = ""),
            paste(rep("=", 70), collapse = "")))
cat(sprintf("%-35s %8s %8s %8s\n", "Outcome", "β(ELO_z)", "SE", "p"))
cat(paste(rep("-", 65), collapse = ""), "\n")

models_list <- list(
  "Mean absolute shift" = m1,
  "SSR" = m2,
  "Within-question τ" = m3,
  "Shortest-path premium" = m4,
  "Asymmetry index" = m5,
  "Reasoning judge rating" = m6,
  "Uncertainty judge rating" = m7
)

for (nm in names(models_list)) {
  m <- models_list[[nm]]
  if (is.null(m)) {
    cat(sprintf("%-35s %8s\n", nm, "skipped"))
    next
  }
  coefs <- summary(m)$coefficients
  if ("elo_z" %in% rownames(coefs)) {
    cat(sprintf("%-35s %8.4f %8.4f %8.4f\n",
                nm, coefs["elo_z", "Estimate"],
                coefs["elo_z", "Std. Error"],
                coefs["elo_z", "Pr(>|t|)"]))
  }
}

cat("\nDone.\n")
