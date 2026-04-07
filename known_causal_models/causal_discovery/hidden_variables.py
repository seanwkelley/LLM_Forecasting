"""
Hidden Variable Detection — Test whether agents recognize incomplete variable sets.

Runs the full graph recovery pipeline (run_single_agent) but with some variables
removed from the agent's view. The simulation still runs with all variables
internally — only the agent's variable list and system prompt are modified.

Which variables are hidden is determined by random sampling: k variables are
drawn uniformly at random from the full variable set, repeated for n_draws
independent conditions. This avoids experimenter bias in selecting which
variables to hide. Degenerate draws (where the reduced GT has 0 edges) are
filtered out. Each condition records structural metadata (number of collapsed-
edge candidates, in/out-degree of hidden nodes) for post-hoc analysis of which
structural roles predict performance degradation.

Scoring: strict subset (NOT transitive closure). When A→B→C and B is hidden,
A→C is INCORRECT. The reduced GT is the submatrix of the full GT restricted to
visible variable indices. Agent declaring A→C is a collapsed-edge false positive.

Usage:
    python -m causal_discovery.hidden_variables --domain market --dry-run
    python -m causal_discovery.hidden_variables --domain conflict --dry-run
    python -m causal_discovery.hidden_variables --domain market --k 3 --n-draws 5
    python -m causal_discovery.hidden_variables --domain conflict --budget 15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.ground_truth import (
    MARKET_VARIABLES, CONFLICT_VARIABLES,
    get_market_ground_truth, get_conflict_ground_truth,
    precision_recall, per_edge_analysis, edges_to_matrix,
)
from causal_discovery.multi_agent.agent import (
    setup_domain, run_single_agent, AgentResult,
)
from causal_discovery.prompts_tests import build_hidden_variable_system_prompt


# =============================================================================
# Random hidden variable condition generation
# =============================================================================

def generate_hidden_conditions(
    domain: str,
    k: int = 3,
    n_draws: int = 5,
    seed: int = 42,
) -> list[dict]:
    """Generate random hidden variable conditions by sampling k variables to hide.

    Filters out degenerate draws where the reduced ground truth has 0 edges.
    Each condition includes structural metadata (n_collapsed_candidates,
    hidden_in_degree, hidden_out_degree) for post-hoc analysis.
    """
    if domain == "market":
        full_gt = get_market_ground_truth()
        full_variables = MARKET_VARIABLES
    else:
        full_gt = get_conflict_ground_truth()
        full_variables = CONFLICT_VARIABLES

    rng = np.random.default_rng(seed)
    conditions = []
    attempts = 0
    max_attempts = n_draws * 20

    while len(conditions) < n_draws and attempts < max_attempts:
        attempts += 1
        hidden = [str(v) for v in rng.choice(full_variables, size=k, replace=False)]

        # Filter degenerate: reduced GT must have at least 1 edge
        reduced_gt, visible_vars = compute_reduced_ground_truth(
            full_gt, full_variables, hidden,
        )
        n_edges = int(np.sum(reduced_gt))
        if n_edges == 0:
            continue

        # Check for duplicate draws
        hidden_sorted = tuple(sorted(hidden))
        if any(tuple(sorted(c["hidden"])) == hidden_sorted for c in conditions):
            continue

        # Compute structural metadata
        collapsed = find_collapsed_edges(full_gt, full_variables, hidden)
        var_idx = {v: i for i, v in enumerate(full_variables)}
        hidden_in = sum(int(np.sum(full_gt[:, var_idx[h]])) for h in hidden)
        hidden_out = sum(int(np.sum(full_gt[var_idx[h], :])) for h in hidden)

        name = "hide_" + "_".join(sorted(hidden))
        conditions.append({
            "name": name,
            "hidden": hidden,
            "metadata": {
                "reduced_gt_edges": n_edges,
                "n_collapsed_candidates": len(collapsed),
                "hidden_in_degree": hidden_in,
                "hidden_out_degree": hidden_out,
            },
        })

    return conditions


# =============================================================================
# Core functions
# =============================================================================

def compute_reduced_ground_truth(
    full_gt: np.ndarray,
    full_variables: list[str],
    hidden_variables: list[str],
) -> tuple[np.ndarray, list[str]]:
    """Subset of full GT edges where BOTH endpoints are visible.

    Returns (reduced_matrix, visible_variable_list).
    """
    visible_indices = [
        i for i, v in enumerate(full_variables) if v not in hidden_variables
    ]
    visible_vars = [full_variables[i] for i in visible_indices]

    n = len(visible_indices)
    reduced = np.zeros((n, n), dtype=int)
    for ri, fi in enumerate(visible_indices):
        for rj, fj in enumerate(visible_indices):
            reduced[ri, rj] = full_gt[fi, fj]

    return reduced, visible_vars


def find_collapsed_edges(
    full_gt: np.ndarray,
    full_variables: list[str],
    hidden_variables: list[str],
) -> list[tuple[str, str, list[str]]]:
    """Find (A, C, [hidden mediators]) where A→H→C exists but A→C does not.

    These are edges the agent might incorrectly declare due to missing mediators.
    Returns list of (source, target, [mediator_names]).
    """
    hidden_set = set(hidden_variables)
    var_idx = {v: i for i, v in enumerate(full_variables)}
    visible_vars = [v for v in full_variables if v not in hidden_set]

    collapsed = []
    for a in visible_vars:
        for c in visible_vars:
            if a == c:
                continue
            ai, ci = var_idx[a], var_idx[c]
            # Skip if direct edge exists in full GT
            if full_gt[ai, ci] == 1:
                continue
            # Check for paths A -> H -> C where H is hidden
            mediators = []
            for h in hidden_variables:
                hi = var_idx[h]
                if full_gt[ai, hi] == 1 and full_gt[hi, ci] == 1:
                    mediators.append(h)
            if mediators:
                collapsed.append((a, c, mediators))

    return collapsed


def setup_hidden_domain(
    domain: str,
    hidden_variables: list[str],
    n_warmup: int = 10,
    seed: int = 42,
    budget: int = 30,
) -> dict:
    """Set up domain then replace variables/system_prompt with visible-only versions.

    The simulation still runs with all variables internally — only the agent's
    view is restricted.
    """
    domain_setup = setup_domain(domain, n_warmup=n_warmup, seed=seed, budget=budget)

    full_variables = domain_setup["variables"]
    visible_variables = [v for v in full_variables if v not in hidden_variables]

    # Replace variables and system prompt with visible-only versions
    domain_setup["variables"] = visible_variables
    domain_setup["system_prompt"] = build_hidden_variable_system_prompt(
        domain, visible_variables,
    )

    return domain_setup


def _detect_hidden_variable_awareness(
    declaration: dict, conversation: list[dict],
) -> dict:
    """Scan agent output for signs it recognized unexplained effects.

    Keyword search over the agent's conversation for mentions of hidden,
    latent, unobserved, or missing variables.
    """
    keywords = [
        "hidden", "latent", "unobserved", "unexplained", "missing variable",
        "confound", "unmeasured", "mediator", "omitted", "unaccounted",
        "not included", "not in our variable set", "not among the variables",
    ]

    relevant_quotes = []
    agent_flagged_unexplained = False
    agent_hypothesized_hidden = False

    # Scan conversation for agent messages
    for msg in conversation:
        if msg["role"] != "assistant":
            continue
        content = msg["content"].lower()
        for kw in keywords:
            if kw in content:
                agent_flagged_unexplained = True
                # Extract surrounding context (find the sentence)
                idx = content.find(kw)
                start = max(0, idx - 80)
                end = min(len(content), idx + len(kw) + 80)
                quote = msg["content"][start:end].strip()
                if quote not in relevant_quotes:
                    relevant_quotes.append(quote)

    # Check specifically for hypothesizing hidden variables
    hypothesis_keywords = ["hidden variable", "latent variable", "unobserved variable",
                          "missing variable", "omitted variable", "unmeasured"]
    for msg in conversation:
        if msg["role"] != "assistant":
            continue
        content = msg["content"].lower()
        for kw in hypothesis_keywords:
            if kw in content:
                agent_hypothesized_hidden = True
                break
        if agent_hypothesized_hidden:
            break

    return {
        "agent_flagged_unexplained": agent_flagged_unexplained,
        "agent_hypothesized_hidden": agent_hypothesized_hidden,
        "relevant_quotes": relevant_quotes[:5],  # limit to top 5
    }


def score_hidden_condition(
    agent_result: AgentResult,
    full_gt: np.ndarray,
    full_variables: list[str],
    hidden_variables: list[str],
) -> dict:
    """Score agent's graph recovery under hidden variable conditions.

    Returns:
        standard_scores: precision, recall, F1, SHD against reduced GT
        collapsed_edge_analysis: which collapsed edges were declared
        hidden_variable_detection: did the agent notice unexplained effects
    """
    reduced_gt, visible_vars = compute_reduced_ground_truth(
        full_gt, full_variables, hidden_variables,
    )

    # Build agent's estimated matrix over visible variables only
    estimated = edges_to_matrix(agent_result.declared_edges, visible_vars)

    # Standard scoring against reduced GT
    standard_scores = precision_recall(estimated, reduced_gt)
    edge_details = per_edge_analysis(estimated, reduced_gt, visible_vars)
    standard_scores["per_edge"] = edge_details

    # Collapsed edge analysis
    collapsed_candidates = find_collapsed_edges(full_gt, full_variables, hidden_variables)
    declared_set = set(agent_result.declared_edges)

    collapsed_declared = []
    collapsed_not_declared = []
    for src, dst, mediators in collapsed_candidates:
        if (src, dst) in declared_set:
            collapsed_declared.append({
                "from": src, "to": dst,
                "hidden_mediators": mediators,
                "declared": True,
            })
        else:
            collapsed_not_declared.append({
                "from": src, "to": dst,
                "hidden_mediators": mediators,
                "declared": False,
            })

    collapsed_analysis = {
        "total_collapsed_candidates": len(collapsed_candidates),
        "collapsed_declared": len(collapsed_declared),
        "collapsed_not_declared": len(collapsed_not_declared),
        "collapsed_rate": (
            len(collapsed_declared) / len(collapsed_candidates)
            if collapsed_candidates else 0.0
        ),
        "details": collapsed_declared + collapsed_not_declared,
    }

    # Hidden variable awareness
    awareness = _detect_hidden_variable_awareness(
        agent_result.declaration_raw, agent_result.conversation,
    )

    return {
        "standard_scores": standard_scores,
        "collapsed_edge_analysis": collapsed_analysis,
        "hidden_variable_detection": awareness,
    }


# =============================================================================
# Main pipeline
# =============================================================================

def run_hidden_variables(
    domain: str = "market",
    conditions: list[dict] | None = None,
    k: int = 3,
    n_draws: int = 5,
    budget: int = 30,
    n_warmup: int = 10,
    seed: int = 42,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    dry_run: bool = False,
    output_dir: str = "",
    verbose: bool = True,
) -> dict:
    """Run hidden variable detection across multiple conditions.

    For each condition: setup_hidden_domain → run_single_agent → score → save.

    If conditions is None, generates n_draws random conditions hiding k variables.
    """
    if conditions is None:
        conditions = generate_hidden_conditions(
            domain, k=k, n_draws=n_draws, seed=seed,
        )

    if domain == "market":
        full_gt = get_market_ground_truth()
        full_variables = MARKET_VARIABLES
    else:
        full_gt = get_conflict_ground_truth()
        full_variables = CONFLICT_VARIABLES

    # Output directory
    if not output_dir:
        model_short = model.split("/")[-1] if "/" in model else model
        output_dir = str(
            Path("outputs/causal_discovery/hidden_variables")
            / f"{domain}_{model_short}"
        )
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "per_condition").mkdir(exist_ok=True)
    (out_path / "conversation_logs").mkdir(exist_ok=True)

    all_results = {}
    summary_rows = []

    for cond in conditions:
        cond_name = cond["name"]
        hidden = cond["hidden"]
        if verbose:
            print(f"\n{'='*60}")
            print(f"Condition: {cond_name}")
            print(f"Hidden variables: {hidden}")
            print(f"{'='*60}")

        # Setup domain with hidden variables
        domain_setup = setup_hidden_domain(
            domain, hidden, n_warmup=n_warmup, seed=seed, budget=budget,
        )

        visible_vars = domain_setup["variables"]
        if verbose:
            print(f"Visible variables ({len(visible_vars)}): {visible_vars}")

        # Run single agent
        agent_result = run_single_agent(
            domain_setup=domain_setup,
            agent_id=f"hidden_{cond_name}",
            budget=budget,
            api_key=api_key,
            model=model,
            dry_run=dry_run,
            verbose=verbose,
        )

        # Score
        scores = score_hidden_condition(
            agent_result, full_gt, full_variables, hidden,
        )

        # Summary row
        std = scores["standard_scores"]
        col = scores["collapsed_edge_analysis"]
        awareness = scores["hidden_variable_detection"]
        row = {
            "condition": cond_name,
            "hidden_variables": hidden,
            "n_visible": len(visible_vars),
            "n_hidden": len(hidden),
            "precision": std["precision"],
            "recall": std["recall"],
            "f1": std["f1"],
            "shd": std["shd"],
            "n_declared_edges": len(agent_result.declared_edges),
            "collapsed_candidates": col["total_collapsed_candidates"],
            "collapsed_declared": col["collapsed_declared"],
            "collapsed_rate": round(col["collapsed_rate"], 3),
            "agent_flagged_unexplained": awareness["agent_flagged_unexplained"],
            "agent_hypothesized_hidden": awareness["agent_hypothesized_hidden"],
            "llm_calls": agent_result.llm_calls,
        }
        # Include structural metadata if present
        if "metadata" in cond:
            row["metadata"] = cond["metadata"]
        summary_rows.append(row)

        if verbose:
            print(f"\n  Results for {cond_name}:")
            print(f"    Precision={std['precision']:.3f}  Recall={std['recall']:.3f}  F1={std['f1']:.3f}  SHD={std['shd']}")
            print(f"    Collapsed edges: {col['collapsed_declared']}/{col['total_collapsed_candidates']} declared (rate={col['collapsed_rate']:.2f})")
            print(f"    Agent awareness: flagged={awareness['agent_flagged_unexplained']}, hypothesized={awareness['agent_hypothesized_hidden']}")

        # Save per-condition results
        condition_output = {
            "condition": cond_name,
            "hidden_variables": hidden,
            "visible_variables": visible_vars,
            "agent_declared_edges": [
                {"from": e[0], "to": e[1]} for e in agent_result.declared_edges
            ],
            "scores": {
                "standard": std,
                "collapsed_edges": col,
                "hidden_variable_detection": awareness,
            },
        }
        with open(out_path / "per_condition" / f"{cond_name}.json", "w") as f:
            json.dump(condition_output, f, indent=2, default=str)

        # Save conversation log
        with open(out_path / "conversation_logs" / f"{cond_name}_conversation.json", "w") as f:
            json.dump(agent_result.conversation, f, indent=2)

        all_results[cond_name] = condition_output

    # Save summary
    summary = {
        "domain": domain,
        "model": model,
        "k_hidden": k,
        "n_draws": n_draws,
        "budget": budget,
        "n_warmup": n_warmup,
        "seed": seed,
        "dry_run": dry_run,
        "n_conditions": len(conditions),
        "per_condition_summary": summary_rows,
        "aggregate": _compute_aggregate(summary_rows),
    }

    with open(out_path / "results.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if verbose:
        print(f"\n{'='*60}")
        print("AGGREGATE RESULTS")
        print(f"{'='*60}")
        agg = summary["aggregate"]
        print(f"  Mean F1: {agg['mean_f1']:.3f}")
        print(f"  Mean collapsed rate: {agg['mean_collapsed_rate']:.3f}")
        print(f"  Awareness rate: {agg['awareness_rate']:.3f}")
        print(f"\nResults saved to {out_path}")

    return summary


def _compute_aggregate(rows: list[dict]) -> dict:
    """Compute aggregate statistics across conditions."""
    if not rows:
        return {}
    return {
        "mean_precision": round(np.mean([r["precision"] for r in rows]), 4),
        "mean_recall": round(np.mean([r["recall"] for r in rows]), 4),
        "mean_f1": round(np.mean([r["f1"] for r in rows]), 4),
        "mean_shd": round(np.mean([r["shd"] for r in rows]), 2),
        "mean_collapsed_rate": round(np.mean([r["collapsed_rate"] for r in rows]), 4),
        "awareness_rate": round(
            np.mean([r["agent_flagged_unexplained"] for r in rows]), 4,
        ),
        "hypothesis_rate": round(
            np.mean([r["agent_hypothesized_hidden"] for r in rows]), 4,
        ),
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Hidden Variable Detection for Causal Discovery",
    )
    parser.add_argument("--domain", default="market", choices=["market", "conflict"])
    parser.add_argument("--k", type=int, default=3,
                       help="Number of variables to hide per condition")
    parser.add_argument("--n-draws", type=int, default=5,
                       help="Number of random conditions to generate")
    parser.add_argument("--budget", type=int, default=30)
    parser.add_argument("--n-warmup", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="meta-llama/llama-3.3-70b-instruct")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    # Load API key
    from causal_discovery.multi_agent.runner import _load_api_key
    api_key = args.dry_run and "dry-run" or _load_api_key()

    run_hidden_variables(
        domain=args.domain,
        k=args.k,
        n_draws=args.n_draws,
        budget=args.budget,
        n_warmup=args.n_warmup,
        seed=args.seed,
        api_key=api_key,
        model=args.model,
        dry_run=args.dry_run,
        output_dir=args.output_dir,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
