# ============================================================================
# LME Regression Analysis for Structural Grounding
#
# Model A: |Delta| ~ Importance_z + Model + (Importance_z | Question)
# Model B: |Delta| ~ PathRelevance_z + Model + (PathRelevance_z | Question)
# Scrambled Placebo: compare grounding coefficient (original vs scrambled 70B)
#
# Reads pre-built CSVs from Python (lme_analysis.py).
# Outputs: lme_results.json, LaTeX tables.
#
# Usage:
#   Rscript forecast_bench/lme_analysis.R
# ============================================================================

library(lme4)
library(lmerTest)   # Satterthwaite p-values
library(jsonlite)

# ── Paths ──────────────────────────────────────────────────────────────────
causal_dir <- file.path("outputs", "sensitivity", "causal")
figures_dir <- file.path("paper", "figures")

node_csv       <- file.path(causal_dir, "lme_node_data.csv")
path_rel_csv   <- file.path(causal_dir, "lme_path_relevance_data.csv")
edge_betw_csv  <- file.path(causal_dir, "lme_edge_betweenness_data.csv")
scrambled_csv  <- file.path(causal_dir, "lme_scrambled_data.csv")
orig70b_csv    <- file.path(causal_dir, "lme_original_70b_data.csv")
ablation_csv   <- file.path(causal_dir, "lme_ablation_data.csv")
direct_csv     <- file.path(causal_dir, "lme_direct_indirect_data.csv")
ext_node_csv   <- file.path(causal_dir, "lme_extended_node_data.csv")
ext_edge_csv   <- file.path(causal_dir, "lme_extended_edge_data.csv")
net_size_csv   <- file.path(causal_dir, "lme_network_size_data.csv")

ref_model <- "Llama-3.3-70B"

# ── Helper: extract results into a list ────────────────────────────────────
extract_results <- function(fit, label, formula_str, re_formula_str, df) {
  s <- summary(fit)
  fe <- as.data.frame(s$coefficients)

  # Build fixed effects list
  fe_list <- list()
  for (param in rownames(fe)) {
    fe_list[[param]] <- list(
      coef     = round(fe[param, "Estimate"], 6),
      se       = round(fe[param, "Std. Error"], 6),
      t        = round(fe[param, "t value"], 4),
      df_satt  = if ("df" %in% colnames(fe)) round(fe[param, "df"], 2) else NA,
      p        = round(fe[param, "Pr(>|t|)"], 6)
    )
    # Confidence intervals
    ci <- confint(fit, parm = "beta_", method = "Wald", quiet = TRUE)
    if (param %in% rownames(ci)) {
      fe_list[[param]]$ci_lower <- round(ci[param, 1], 6)
      fe_list[[param]]$ci_upper <- round(ci[param, 2], 6)
    }
  }

  # Random effects variance
  vc <- as.data.frame(VarCorr(fit))
  re_var <- list()
  for (i in seq_len(nrow(vc))) {
    key <- paste0(vc$var1[i], ifelse(is.na(vc$var2[i]), "", paste0(":", vc$var2[i])))
    if (vc$grp[i] == "Residual") key <- "Residual"
    re_var[[key]] <- round(vc$vcov[i], 6)
  }

  # R-squared (Nakagawa & Schielzeth)
  var_fe    <- var(predict(fit, re.form = NA))
  var_re    <- sum(vc$vcov[vc$grp != "Residual"])
  var_resid <- vc$vcov[vc$grp == "Residual"]
  r2m <- var_fe / (var_fe + var_re + var_resid)
  r2c <- (var_fe + var_re) / (var_fe + var_re + var_resid)

  # Per-model slopes (for interaction models)
  # Detect the predictor variable (importance_z, path_relevance_z, edge_betweenness_z)
  all_params <- rownames(fe)
  pred_var <- NULL
  for (candidate in c("importance_z", "path_relevance_z", "edge_betweenness_z", "betweenness_z",
                       "rating", "uncertainty_numeric", "initial_logit", "is_structuralStructural")) {
    if (candidate %in% all_params) { pred_var <- candidate; break }
  }

  per_model_slopes <- list()
  if (!is.null(pred_var) && "model" %in% names(df)) {
    V <- vcov(fit)
    b1 <- fixef(fit)[[pred_var]]
    models <- levels(df$model)
    for (mod in models) {
      int_name <- paste0(pred_var, ":model", mod)
      intercept_name <- paste0("model", mod)
      if (mod == levels(df$model)[1]) {
        # Reference model
        slope <- b1
        se_slope <- sqrt(V[pred_var, pred_var])
        intercept_val <- fixef(fit)[["(Intercept)"]]
        se_int <- sqrt(V["(Intercept)", "(Intercept)"])
      } else if (int_name %in% all_params) {
        # Model with interaction term
        slope <- b1 + fixef(fit)[[int_name]]
        se_slope <- sqrt(V[pred_var, pred_var] + V[int_name, int_name] +
                         2 * V[pred_var, int_name])
        intercept_val <- fixef(fit)[["(Intercept)"]] +
                         ifelse(intercept_name %in% all_params, fixef(fit)[[intercept_name]], 0)
        se_int <- sqrt(V["(Intercept)", "(Intercept)"] +
                       ifelse(intercept_name %in% all_params, V[intercept_name, intercept_name] +
                              2 * V["(Intercept)", intercept_name], 0))
      } else {
        # No interaction — shared slope
        slope <- b1
        se_slope <- sqrt(V[pred_var, pred_var])
        intercept_val <- fixef(fit)[["(Intercept)"]] +
                         ifelse(intercept_name %in% all_params, fixef(fit)[[intercept_name]], 0)
        se_int <- sqrt(V["(Intercept)", "(Intercept)"])
      }
      # Test slope against zero
      t_vs_zero <- slope / se_slope
      p_vs_zero <- 2 * pt(abs(t_vs_zero), df = nobs(fit) - length(fixef(fit)), lower.tail = FALSE)

      # Test slope difference from reference (for non-reference models)
      if (mod == levels(df$model)[1]) {
        t_vs_ref <- NA
        p_vs_ref <- NA
      } else if (int_name %in% all_params) {
        int_coef <- fixef(fit)[[int_name]]
        int_se   <- sqrt(V[int_name, int_name])
        t_vs_ref <- int_coef / int_se
        p_vs_ref <- 2 * pt(abs(t_vs_ref), df = nobs(fit) - length(fixef(fit)), lower.tail = FALSE)
      } else {
        t_vs_ref <- NA
        p_vs_ref <- NA
      }

      per_model_slopes[[mod]] <- list(
        slope     = round(slope, 6),
        slope_se  = round(se_slope, 6),
        slope_ci_lower = round(slope - 1.96 * se_slope, 6),
        slope_ci_upper = round(slope + 1.96 * se_slope, 6),
        t_vs_zero = round(t_vs_zero, 4),
        p_vs_zero = round(p_vs_zero, 6),
        t_vs_ref  = if (!is.na(t_vs_ref)) round(t_vs_ref, 4) else NA,
        p_vs_ref  = if (!is.na(p_vs_ref)) round(p_vs_ref, 6) else NA,
        intercept = round(intercept_val, 6),
        intercept_se = round(se_int, 6)
      )
    }
  }

  list(
    label            = label,
    formula          = formula_str,
    re_formula       = re_formula_str,
    n_obs            = nobs(fit),
    n_groups         = length(unique(df$question_id)),
    converged        = is.null(fit@optinfo$conv$lme4$messages),
    log_likelihood   = round(as.numeric(logLik(fit)), 4),
    aic              = round(AIC(fit), 4),
    bic              = round(BIC(fit), 4),
    r2_marginal      = round(r2m, 4),
    r2_conditional   = round(r2c, 4),
    fixed_effects    = fe_list,
    per_model_slopes = per_model_slopes,
    random_effects_variance = re_var,
    scale            = round(var_resid, 6)
  )
}

# ── Helper: fit with fallback ──────────────────────────────────────────────
fit_lme <- function(formula_str, re_formula_str, df, label) {
  cat(sprintf("\n%s\n%s\n", paste(rep("=", 70), collapse = ""), label))
  cat(sprintf("  N = %d obs, %d questions\n", nrow(df), length(unique(df$question_id))))

  if (nrow(df) < 20) {
    cat("  Skipping: too few observations\n")
    return(NULL)
  }

  # Try random slope first
  fit <- tryCatch({
    m <- lmer(as.formula(formula_str), data = df, REML = TRUE,
              control = lmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 50000)))
    if (isSingular(m)) {
      cat("  Random slope model is singular. Falling back to random intercept.\n")
      stop("singular")
    }
    m
  }, error = function(e) {
    cat(sprintf("  Random slope failed (%s). Falling back to random intercept.\n", e$message))
    # Replace random slope with random intercept
    fallback <- gsub("\\(.*\\|", "(1 |", formula_str)
    re_formula_str <<- "~1"
    lmer(as.formula(fallback), data = df, REML = TRUE,
         control = lmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 50000)))
  })

  cat("\nFixed effects:\n")
  print(summary(fit)$coefficients, digits = 4)

  vc <- as.data.frame(VarCorr(fit))
  cat("\nRandom effects:\n")
  print(vc[, c("grp", "var1", "var2", "vcov")], digits = 4)

  # R-squared
  var_fe    <- var(predict(fit, re.form = NA))
  var_re    <- sum(vc$vcov[vc$grp != "Residual"])
  var_resid <- vc$vcov[vc$grp == "Residual"]
  r2m <- var_fe / (var_fe + var_re + var_resid)
  r2c <- (var_fe + var_re) / (var_fe + var_re + var_resid)
  cat(sprintf("\nMarginal R2 = %.4f  Conditional R2 = %.4f\n", r2m, r2c))

  extract_results(fit, label, formula_str, re_formula_str, df)
}

# ── Helper: generate LaTeX table ───────────────────────────────────────────
generate_latex_table <- function(results, filename, caption) {
  if (is.null(results)) return(invisible(NULL))

  fe <- results$fixed_effects
  lines <- c(
    "\\begin{table}[htbp]",
    "\\centering",
    "\\small",
    sprintf("\\caption{%s}", caption),
    sprintf("\\label{tab:%s}", tools::file_path_sans_ext(filename)),
    "\\begin{tabular}{lccccc}",
    "\\toprule",
    "Parameter & Coef. & SE & $t$ & $p$ & 95\\% CI \\\\",
    "\\midrule"
  )

  for (param in names(fe)) {
    vals <- fe[[param]]
    # Clean parameter name for LaTeX
    display <- param
    display <- gsub("^model", "", display)
    display <- gsub("_", "\\\\_", display)

    p <- vals$p
    p_str <- if (p < 0.001) "$<$0.001" else sprintf("%.3f", p)
    stars <- if (p < 0.001) "***" else if (p < 0.01) "**" else if (p < 0.05) "*" else ""

    ci_str <- sprintf("[%.3f, %.3f]", vals$ci_lower, vals$ci_upper)
    lines <- c(lines, sprintf("  %s & %.4f%s & %.4f & %.2f & %s & %s \\\\",
                               display, vals$coef, stars, vals$se, vals$t, p_str, ci_str))
  }

  lines <- c(lines,
    "\\midrule",
    sprintf("  N observations & \\multicolumn{5}{c}{%d} \\\\", results$n_obs),
    sprintf("  N groups (questions) & \\multicolumn{5}{c}{%d} \\\\", results$n_groups),
    sprintf("  Log-likelihood & \\multicolumn{5}{c}{%.2f} \\\\", results$log_likelihood),
    sprintf("  AIC / BIC & \\multicolumn{5}{c}{%.1f / %.1f} \\\\", results$aic, results$bic),
    sprintf("  Marginal $R^2$ & \\multicolumn{5}{c}{%.4f} \\\\", results$r2_marginal),
    sprintf("  Conditional $R^2$ & \\multicolumn{5}{c}{%.4f} \\\\", results$r2_conditional)
  )

  # Random effects
  for (nm in names(results$random_effects_variance)) {
    val <- results$random_effects_variance[[nm]]
    nm_clean <- gsub("_", "\\\\_", nm)
    lines <- c(lines, sprintf("  RE var (%s) & \\multicolumn{5}{c}{%.4f} \\\\", nm_clean, val))
  }

  lines <- c(lines, "\\bottomrule", "\\end{tabular}", "\\end{table}")

  out_path <- file.path(figures_dir, filename)
  writeLines(lines, out_path)
  cat(sprintf("  Saved LaTeX table: %s\n", out_path))
}

# ============================================================================
# LOAD DATA
# ============================================================================
cat("Loading prepared CSVs...\n")

df_node      <- read.csv(node_csv, stringsAsFactors = FALSE)
df_path_rel  <- read.csv(path_rel_csv, stringsAsFactors = FALSE)
df_edge_betw <- read.csv(edge_betw_csv, stringsAsFactors = FALSE)
df_scrambled <- read.csv(scrambled_csv, stringsAsFactors = FALSE)
df_orig70b   <- read.csv(orig70b_csv, stringsAsFactors = FALSE)

cat(sprintf("  Nodes: %d rows\n", nrow(df_node)))
cat(sprintf("  Path Relevance: %d rows\n", nrow(df_path_rel)))
cat(sprintf("  Edge Betweenness: %d rows\n", nrow(df_edge_betw)))
cat(sprintf("  Scrambled: %d rows\n", nrow(df_scrambled)))
cat(sprintf("  Original 70B: %d rows\n", nrow(df_orig70b)))

# Set reference level for model factor
df_node$model      <- relevel(factor(df_node$model), ref = ref_model)
df_path_rel$model  <- relevel(factor(df_path_rel$model), ref = ref_model)
df_edge_betw$model <- relevel(factor(df_edge_betw$model), ref = ref_model)

# ============================================================================
# MODEL A: Node Importance — shared slope (primary)
# ============================================================================
result_a_shared <- fit_lme(
  "absolute_shift ~ importance_z + model + (importance_z | question_id)",
  "~importance_z", df_node,
  "Model A: Node Importance — shared slope"
)

# ============================================================================
# MODEL A: Node Importance — interaction (model-specific slopes)
# ============================================================================
result_a <- fit_lme(
  "absolute_shift ~ importance_z * model + (importance_z | question_id)",
  "~importance_z", df_node,
  "Model A: Node Importance — interaction"
)

# ============================================================================
# MODEL B: Path Relevance — shared slope (primary)
# ============================================================================
result_b_shared <- fit_lme(
  "absolute_shift ~ path_relevance_z + model + (path_relevance_z | question_id)",
  "~path_relevance_z", df_path_rel,
  "Model B: Path Relevance — shared slope"
)

# ============================================================================
# MODEL B: Path Relevance — interaction (model-specific slopes)
# ============================================================================
result_b <- fit_lme(
  "absolute_shift ~ path_relevance_z * model + (path_relevance_z | question_id)",
  "~path_relevance_z", df_path_rel,
  "Model B: Path Relevance — interaction"
)

# Model C (Edge Betweenness) removed — edge-level predictors dropped from analysis.

# ============================================================================
# LOG-ODDS MODELS: absolute log-odds shift with direction covariate
# ============================================================================
cat("\n--- Log-odds models ---\n")

# Model A (log-odds): betweenness with direction covariate
result_a_logit_shared <- NULL
result_a_logit <- NULL
if ("abs_logit_shift" %in% names(df_node) && "direction" %in% names(df_node)) {
  df_node$direction <- factor(df_node$direction, levels = c("negate", "strengthen", "other"))

  result_a_logit_shared <- fit_lme(
    "abs_logit_shift ~ importance_z + direction + model + (importance_z | question_id)",
    "~importance_z", df_node,
    "Model A (log-odds): Node Importance + Direction — shared slope"
  )

  result_a_logit <- fit_lme(
    "abs_logit_shift ~ importance_z * model + direction + (importance_z | question_id)",
    "~importance_z", df_node,
    "Model A (log-odds): Node Importance + Direction — interaction"
  )
}

# Model B (log-odds): outcome mediation with direction covariate
result_b_logit_shared <- NULL
result_b_logit <- NULL
if ("abs_logit_shift" %in% names(df_path_rel) && "direction" %in% names(df_path_rel)) {
  df_path_rel$direction <- factor(df_path_rel$direction, levels = c("negate", "strengthen", "other"))

  result_b_logit_shared <- fit_lme(
    "abs_logit_shift ~ path_relevance_z + direction + model + (path_relevance_z | question_id)",
    "~path_relevance_z", df_path_rel,
    "Model B (log-odds): Outcome Mediation + Direction — shared slope"
  )

  result_b_logit <- fit_lme(
    "abs_logit_shift ~ path_relevance_z * model + direction + (path_relevance_z | question_id)",
    "~path_relevance_z", df_path_rel,
    "Model B (log-odds): Outcome Mediation + Direction — interaction"
  )
}

# ============================================================================
# ORIGINAL 70B (for placebo comparison)
# ============================================================================
re_orig <- "~importance_z"
result_orig70b <- fit_lme(
  "absolute_shift ~ importance_z + (importance_z | question_id)",
  re_orig,
  df_orig70b,
  "Original 70B (for placebo comparison)"
)

# ============================================================================
# SCRAMBLED PLACEBO
# ============================================================================
re_scram <- "~importance_z"
result_scrambled <- fit_lme(
  "absolute_shift ~ importance_z + (importance_z | question_id)",
  re_scram,
  df_scrambled,
  "Scrambled Placebo (70B)"
)

# ============================================================================
# PLACEBO COMPARISON
# ============================================================================
cat(sprintf("\n%s\nSCRAMBLED PLACEBO COMPARISON\n%s\n",
            paste(rep("=", 70), collapse = ""),
            paste(rep("=", 70), collapse = "")))

if (!is.null(result_orig70b) && !is.null(result_scrambled)) {
  orig_b1  <- result_orig70b$fixed_effects[["importance_z"]]
  scram_b1 <- result_scrambled$fixed_effects[["importance_z"]]

  if (!is.null(orig_b1) && !is.null(scram_b1)) {
    cat(sprintf("  Original 70B  beta1 = %.4f (p = %.4f, CI [%.3f, %.3f])\n",
                orig_b1$coef, orig_b1$p, orig_b1$ci_lower, orig_b1$ci_upper))
    cat(sprintf("  Scrambled 70B beta1 = %.4f (p = %.4f, CI [%.3f, %.3f])\n",
                scram_b1$coef, scram_b1$p, scram_b1$ci_lower, scram_b1$ci_upper))
    degraded <- scram_b1$coef < orig_b1$coef
    cat(sprintf("  beta1 degraded in scrambled: %s\n", ifelse(degraded, "YES", "NO")))
  }
}

# ============================================================================
# ABLATION: Node Removal LME (betweenness + path relevance)
# ============================================================================
result_ablation_node_betw <- NULL
result_ablation_node_pr   <- NULL
result_ablation_edge_betw <- NULL

if (file.exists(ablation_csv)) {
  df_ablation <- read.csv(ablation_csv, stringsAsFactors = FALSE)
  df_abl_nodes <- df_ablation[df_ablation$ablation_type == "node", ]
  df_abl_edges <- df_ablation[df_ablation$ablation_type == "edge", ]
  cat(sprintf("  Ablation: %d node, %d edge rows\n", nrow(df_abl_nodes), nrow(df_abl_edges)))

  # Node ablation: betweenness
  if (nrow(df_abl_nodes) >= 20) {
    result_ablation_node_betw <- fit_lme(
      "absolute_shift ~ betweenness_z + (betweenness_z | question_id)",
      "~betweenness_z", df_abl_nodes,
      "Ablation: Node Betweenness (70B)"
    )
  }

  # Node ablation: path relevance
  if (nrow(df_abl_nodes) >= 20 && sd(df_abl_nodes$path_relevance_z, na.rm = TRUE) > 0) {
    result_ablation_node_pr <- fit_lme(
      "absolute_shift ~ path_relevance_z + (path_relevance_z | question_id)",
      "~path_relevance_z", df_abl_nodes,
      "Ablation: Node Path Relevance (70B)"
    )
  }

  # Edge ablation removed — edge-level predictors dropped from analysis.
} else {
  cat("  [SKIP] No ablation data CSV\n")
}

# ============================================================================
# DIRECT vs INDIRECT: Does proximity to outcome predict shift beyond betweenness?
# ============================================================================
result_direct_main <- NULL
result_direct_interaction <- NULL

if (file.exists(direct_csv)) {
  df_direct <- read.csv(direct_csv, stringsAsFactors = FALSE)
  df_direct$model <- relevel(factor(df_direct$model), ref = ref_model)
  df_direct$is_direct <- factor(df_direct$is_direct, levels = c(0, 1),
                                 labels = c("Indirect", "Direct"))
  cat(sprintf("  Direct/Indirect: %d rows (%d direct, %d indirect)\n",
              nrow(df_direct),
              sum(df_direct$is_direct == "Direct"),
              sum(df_direct$is_direct == "Indirect")))

  # Model: is_direct + betweenness_z + model + (1 | question)
  result_direct_main <- fit_lme(
    "absolute_shift ~ is_direct + betweenness_z + model + (1 | question_id)",
    "~1", df_direct,
    "Direct vs Indirect: Main Effects"
  )

  # Model with interaction: is_direct × betweenness_z
  result_direct_interaction <- fit_lme(
    "absolute_shift ~ is_direct * betweenness_z + model + (1 | question_id)",
    "~1", df_direct,
    "Direct vs Indirect: Interaction (directness x betweenness)"
  )
} else {
  cat("  [SKIP] No direct/indirect data CSV\n")
}

# ============================================================================
# EXTENDED NODE METRICS: causal depth, n_paths, degree
# ============================================================================
result_causal_depth <- NULL
result_n_paths      <- NULL
result_degree       <- NULL

if (file.exists(ext_node_csv)) {
  df_ext_node <- read.csv(ext_node_csv, stringsAsFactors = FALSE)
  df_ext_node$model <- relevel(factor(df_ext_node$model), ref = ref_model)
  cat(sprintf("  Extended node data: %d rows\n", nrow(df_ext_node)))

  # Causal depth (distance to outcome) — expect NEGATIVE: closer = larger shift
  result_causal_depth <- fit_lme(
    "absolute_shift ~ causal_depth_z + model + (1 | question_id)",
    "~1", df_ext_node,
    "Extended: Causal Depth (shared slope)"
  )

  # Number of paths to outcome — expect POSITIVE: more paths = more ways to matter
  result_n_paths <- fit_lme(
    "absolute_shift ~ n_paths_to_outcome_z + model + (1 | question_id)",
    "~1", df_ext_node,
    "Extended: N Paths to Outcome (shared slope)"
  )

  # Node degree — expect POSITIVE: more connected = more important
  result_degree <- fit_lme(
    "absolute_shift ~ degree_z + model + (1 | question_id)",
    "~1", df_ext_node,
    "Extended: Node Degree (shared slope)"
  )
} else {
  cat("  [SKIP] No extended node data\n")
}

# ============================================================================
# COMBINED NODE MODEL: which predictors survive when controlling for each other?
# ============================================================================
result_node_combined <- NULL

if (file.exists(ext_node_csv)) {
  result_node_combined <- fit_lme(
    "absolute_shift ~ betweenness_z + path_relevance_z + causal_depth_z + degree_z + is_direct + model + (1 | question_id)",
    "~1", df_ext_node,
    "Combined Node Model (all predictors)"
  )
}

# ============================================================================
# EXTENDED EDGE METRICS: on_shortest_path, sp_count, direct_to_outcome
# ============================================================================
result_edge_on_sp      <- NULL
result_edge_sp_count   <- NULL
result_edge_direct_out <- NULL

if (file.exists(ext_edge_csv)) {
  df_ext_edge <- read.csv(ext_edge_csv, stringsAsFactors = FALSE)
  df_ext_edge$model <- relevel(factor(df_ext_edge$model), ref = ref_model)
  cat(sprintf("  Extended edge data: %d rows\n", nrow(df_ext_edge)))

  # Edge on any shortest path to outcome (binary)
  result_edge_on_sp <- fit_lme(
    "absolute_shift ~ on_shortest_path + model + (1 | question_id)",
    "~1", df_ext_edge,
    "Extended: Edge on Shortest Path (binary)"
  )

  # Shortest path count through this edge
  if (sd(df_ext_edge$sp_count_z, na.rm = TRUE) > 0) {
    result_edge_sp_count <- fit_lme(
      "absolute_shift ~ sp_count_z + model + (1 | question_id)",
      "~1", df_ext_edge,
      "Extended: Edge Shortest Path Count"
    )
  }

  # Edge directly connects to outcome (binary)
  result_edge_direct_out <- fit_lme(
    "absolute_shift ~ is_direct_to_outcome + model + (1 | question_id)",
    "~1", df_ext_edge,
    "Extended: Edge Direct to Outcome (binary)"
  )
} else {
  cat("  [SKIP] No extended edge data\n")
}

# ============================================================================
# COMBINED EDGE MODEL: which edge predictors survive?
# ============================================================================
result_edge_combined <- NULL

if (file.exists(ext_edge_csv)) {
  result_edge_combined <- fit_lme(
    "absolute_shift ~ edge_betweenness_z + on_shortest_path + is_direct_to_outcome + model + (1 | question_id)",
    "~1", df_ext_edge,
    "Combined Edge Model (all predictors)"
  )
}

# ============================================================================
# NETWORK SIZE: Separate LME per size condition (70B only)
# ============================================================================
result_net_small  <- NULL
result_net_medium <- NULL
result_net_large  <- NULL
result_net_xl     <- NULL

if (file.exists(net_size_csv)) {
  df_net <- read.csv(net_size_csv, stringsAsFactors = FALSE)
  cat(sprintf("  Network size data: %d rows\n", nrow(df_net)))

  sizes <- list(
    "Small (3-5)"  = "net_small",
    "Medium (4-8)" = "net_medium",
    "Large (6-10)" = "net_large",
    "XL (12-16)"   = "net_xl"
  )

  for (sz_label in names(sizes)) {
    df_sz <- df_net[df_net$network_size == sz_label, ]
    if (nrow(df_sz) >= 20) {
      res <- fit_lme(
        "absolute_shift ~ importance_z + (importance_z | question_id)",
        "~importance_z", df_sz,
        paste0("Network Size: ", sz_label, " (70B)")
      )
      assign(paste0("result_", sizes[[sz_label]]), res)
    }
  }
} else {
  cat("  [SKIP] No network size data CSV\n")
}

# ============================================================================
# COHERENCE: Stated-Impact Rating → |Logit Shift|
# ============================================================================
coherence_reasoning_csv <- file.path(causal_dir, "lme_coherence_reasoning.csv")
result_coherence_reasoning <- NULL
result_coherence_reasoning_interaction <- NULL

if (file.exists(coherence_reasoning_csv)) {
  df_coh_reason <- read.csv(coherence_reasoning_csv, stringsAsFactors = FALSE)
  df_coh_reason$model <- factor(df_coh_reason$model)
  cat(sprintf("  Coherence Reasoning: %d rows\n", nrow(df_coh_reason)))

  if (nrow(df_coh_reason) >= 20) {
    result_coherence_reasoning <- fit_lme(
      "abs_logit_shift ~ rating + model + (1 | question_id)",
      "~1", df_coh_reason,
      "Coherence: Stated-Impact Rating (1-5) → |Logit Shift|"
    )
  }
  # Interaction model: per-model slopes
  result_coherence_reasoning_interaction <- NULL
  if (nrow(df_coh_reason) >= 20) {
    result_coherence_reasoning_interaction <- fit_lme(
      "abs_logit_shift ~ rating * model + (1 | question_id)",
      "~1", df_coh_reason,
      "Coherence: Stated-Impact Rating — interaction (per-model slopes)"
    )
  }
} else {
  cat("  [SKIP] No coherence reasoning CSV\n")
}

# ============================================================================
# COHERENCE: Uncertainty Rating → |Logit Shift|
# ============================================================================
coherence_uncertainty_csv <- file.path(causal_dir, "lme_coherence_uncertainty.csv")
result_coherence_uncertainty <- NULL
result_coherence_uncertainty_interaction <- NULL

if (file.exists(coherence_uncertainty_csv)) {
  df_coh_uncert <- read.csv(coherence_uncertainty_csv, stringsAsFactors = FALSE)
  df_coh_uncert$model <- factor(df_coh_uncert$model)
  # Treat uncertainty as ordered factor (2=Confident, 3=Mixed, 4=Hedging)
  df_coh_uncert$uncertainty <- factor(df_coh_uncert$uncertainty, levels = c(2, 3, 4),
                                       labels = c("Confident", "Mixed", "Hedging"))
  cat(sprintf("  Coherence Uncertainty: %d rows\n", nrow(df_coh_uncert)))

  if (nrow(df_coh_uncert) >= 20) {
    result_coherence_uncertainty <- fit_lme(
      "abs_logit_shift ~ uncertainty + model + (1 | question_id)",
      "~1", df_coh_uncert,
      "Coherence: Uncertainty (Confident/Mixed/Hedging) → |Logit Shift|"
    )
  }

  # Interaction model: uncertainty_numeric (continuous 0-2) × model for per-model slopes
  result_coherence_uncertainty_interaction <- NULL
  if ("uncertainty_numeric" %in% names(df_coh_uncert) && nrow(df_coh_uncert) >= 20) {
    result_coherence_uncertainty_interaction <- fit_lme(
      "abs_logit_shift ~ uncertainty_numeric * model + (1 | question_id)",
      "~1", df_coh_uncert,
      "Coherence: Uncertainty (numeric) — interaction (per-model slopes)"
    )
  }
} else {
  cat("  [SKIP] No coherence uncertainty CSV\n")
}

# ============================================================================
# COHERENCE: Bayesian — Initial Logit → Signed Logit Shift
# ============================================================================
coherence_bayesian_csv <- file.path(causal_dir, "lme_coherence_bayesian.csv")
result_coherence_bayesian <- NULL
result_coherence_bayesian_interaction <- NULL

if (file.exists(coherence_bayesian_csv)) {
  df_coh_bayes <- read.csv(coherence_bayesian_csv, stringsAsFactors = FALSE)
  df_coh_bayes$model <- factor(df_coh_bayes$model)
  cat(sprintf("  Coherence Bayesian: %d rows\n", nrow(df_coh_bayes)))

  if (nrow(df_coh_bayes) >= 20) {
    result_coherence_bayesian <- fit_lme(
      "logit_shift ~ initial_logit + model + (1 | question_id)",
      "~1", df_coh_bayes,
      "Coherence: Bayesian (Initial Logit → Signed Logit Shift)"
    )
  }

  # Interaction model: per-model initial_logit slopes
  result_coherence_bayesian_interaction <- NULL
  if (nrow(df_coh_bayes) >= 20) {
    result_coherence_bayesian_interaction <- fit_lme(
      "logit_shift ~ initial_logit * model + (1 | question_id)",
      "~1", df_coh_bayes,
      "Coherence: Bayesian — interaction (per-model slopes)"
    )
  }
} else {
  cat("  [SKIP] No coherence Bayesian CSV\n")
}

# ============================================================================
# COHERENCE: Embedding — Structural vs Control Cosine Similarity
# ============================================================================
coherence_embedding_csv <- file.path(causal_dir, "lme_coherence_embedding.csv")
result_coherence_embedding <- NULL
result_coherence_embedding_interaction <- NULL

if (file.exists(coherence_embedding_csv)) {
  df_coh_emb <- read.csv(coherence_embedding_csv, stringsAsFactors = FALSE)
  df_coh_emb$model <- factor(df_coh_emb$model)
  df_coh_emb$is_structural <- factor(df_coh_emb$is_structural, levels = c(0, 1),
                                      labels = c("Control", "Structural"))
  cat(sprintf("  Coherence Embedding: %d rows\n", nrow(df_coh_emb)))

  if (nrow(df_coh_emb) >= 20) {
    result_coherence_embedding <- fit_lme(
      "mean_cosine_sim ~ is_structural + model + (1 | question_id)",
      "~1", df_coh_emb,
      "Coherence: Embedding Similarity (Structural vs Control)"
    )
  }

  # Interaction model: per-model structural effect
  result_coherence_embedding_interaction <- NULL
  if (nrow(df_coh_emb) >= 20) {
    result_coherence_embedding_interaction <- fit_lme(
      "mean_cosine_sim ~ is_structural * model + (1 | question_id)",
      "~1", df_coh_emb,
      "Coherence: Embedding — interaction (per-model structural effect)"
    )
  }
} else {
  cat("  [SKIP] No coherence embedding CSV\n")
}

# ============================================================================
# SAVE JSON RESULTS
# ============================================================================
all_results <- list(
  model_a_shared         = result_a_shared,
  model_a                = result_a,
  model_b_shared         = result_b_shared,
  model_b                = result_b,
  original_70b           = result_orig70b,
  scrambled_placebo      = result_scrambled,
  direct_main            = result_direct_main,
  direct_interaction     = result_direct_interaction,
  ext_causal_depth       = result_causal_depth,
  ext_n_paths            = result_n_paths,
  ext_degree             = result_degree,
  ext_edge_on_sp         = result_edge_on_sp,
  ext_edge_sp_count      = result_edge_sp_count,
  ext_edge_direct_out    = result_edge_direct_out,
  node_combined          = result_node_combined,
  edge_combined          = result_edge_combined,
  ablation_node_betw     = result_ablation_node_betw,
  ablation_node_path_rel = result_ablation_node_pr,
  net_small              = result_net_small,
  net_medium             = result_net_medium,
  net_large              = result_net_large,
  net_xl                 = result_net_xl,
  model_a_logit_shared   = result_a_logit_shared,
  model_a_logit          = result_a_logit,
  model_b_logit_shared   = result_b_logit_shared,
  model_b_logit          = result_b_logit,
  coherence_reasoning              = result_coherence_reasoning,
  coherence_reasoning_interaction  = result_coherence_reasoning_interaction,
  coherence_uncertainty            = result_coherence_uncertainty,
  coherence_uncertainty_interaction = result_coherence_uncertainty_interaction,
  coherence_bayesian               = result_coherence_bayesian,
  coherence_bayesian_interaction   = result_coherence_bayesian_interaction,
  coherence_embedding              = result_coherence_embedding,
  coherence_embedding_interaction  = result_coherence_embedding_interaction
)

json_path <- file.path(causal_dir, "lme_results.json")
write_json(all_results, json_path, pretty = TRUE, auto_unbox = TRUE, null = "null")
cat(sprintf("\nSaved JSON results: %s\n", json_path))

# ============================================================================
# GENERATE LATEX TABLES
# ============================================================================
generate_latex_table(result_a_shared, "lme_model_a_shared_table.tex",
                     "Model A: Node Importance --- Shared Slope")
generate_latex_table(result_a, "lme_model_a_table.tex",
                     "Model A: Node Importance --- Model-Specific Slopes")
generate_latex_table(result_b_shared, "lme_model_b_shared_table.tex",
                     "Model B: Path Relevance --- Shared Slope")
generate_latex_table(result_b, "lme_model_b_table.tex",
                     "Model B: Path Relevance --- Model-Specific Slopes")
generate_latex_table(result_direct_main, "lme_direct_main_table.tex",
                     "Direct vs Indirect Causes --- Main Effects")
generate_latex_table(result_direct_interaction, "lme_direct_interaction_table.tex",
                     "Direct vs Indirect Causes --- Interaction")
generate_latex_table(result_ablation_node_betw, "lme_ablation_node_betw_table.tex",
                     "Ablation: Node Removal --- Betweenness Predicts Shift")
generate_latex_table(result_ablation_node_pr, "lme_ablation_node_pr_table.tex",
                     "Ablation: Node Removal --- Path Relevance Predicts Shift")

# Scrambled comparison table
if (!is.null(result_orig70b) && !is.null(result_scrambled)) {
  orig_b1  <- result_orig70b$fixed_effects[["importance_z"]]
  scram_b1 <- result_scrambled$fixed_effects[["importance_z"]]

  if (!is.null(orig_b1) && !is.null(scram_b1)) {
    lines <- c(
      "\\begin{table}[htbp]",
      "\\centering",
      "\\small",
      "\\caption{Scrambled Edge Placebo: Grounding Coefficient Comparison}",
      "\\label{tab:lme_scrambled_comparison}",
      "\\begin{tabular}{lccccc}",
      "\\toprule",
      "Condition & $\\beta_1$ & SE & $t$ & $p$ & 95\\% CI \\\\",
      "\\midrule"
    )

    for (lbl_beta in list(
      list(lbl = "Original 70B", b = orig_b1),
      list(lbl = "Scrambled 70B", b = scram_b1)
    )) {
      b <- lbl_beta$b
      p_str <- if (b$p < 0.001) "$<$0.001" else sprintf("%.3f", b$p)
      stars <- if (b$p < 0.001) "***" else if (b$p < 0.01) "**" else if (b$p < 0.05) "*" else ""
      ci <- sprintf("[%.3f, %.3f]", b$ci_lower, b$ci_upper)
      lines <- c(lines, sprintf("  %s & %.4f%s & %.4f & %.2f & %s & %s \\\\",
                                 lbl_beta$lbl, b$coef, stars, b$se, b$t, p_str, ci))
    }

    lines <- c(lines,
      "\\midrule",
      sprintf("  Original N & \\multicolumn{5}{c}{%d} \\\\", result_orig70b$n_obs),
      sprintf("  Scrambled N & \\multicolumn{5}{c}{%d} \\\\", result_scrambled$n_obs),
      "\\bottomrule",
      "\\end{tabular}",
      "\\end{table}"
    )

    writeLines(lines, file.path(figures_dir, "lme_scrambled_table.tex"))
    cat("  Saved LaTeX table: lme_scrambled_table.tex\n")
  }
}

cat("\nDone.\n")
