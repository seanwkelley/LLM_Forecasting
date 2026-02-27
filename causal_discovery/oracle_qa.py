"""
Oracle QA — Can an agent answer targeted causal questions by designing experiments?

A programmatic oracle generates causal questions from the ground truth adjacency
matrix. The agent receives one question at a time, a small configurable
intervention budget (default 3), runs experiments, and answers. Each question
is a standalone mini-test.

Question types (3 each, 12 total by default):
- Counterfactual: "If X were fixed at 0, would Y change?"
- Mechanism: "What mediates the effect of X on Y?"
- Robustness: "Would the effect of X on Y vanish if M were held constant?"
- Direction: "Does X cause Y, or does Y cause X?"

Usage:
    python -m causal_discovery.oracle_qa --domain market --dry-run
    python -m causal_discovery.oracle_qa --domain conflict --n-per-type 4
    python -m causal_discovery.oracle_qa --domain market --budget 3 --model meta-llama/llama-3.1-8b-instruct
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.ground_truth import (
    MARKET_VARIABLES, CONFLICT_VARIABLES,
    get_market_ground_truth, get_conflict_ground_truth,
)
from causal_discovery.multi_agent.agent import (
    setup_domain, call_llm, parse_json_response, mock_llm_response,
    AgentResult, _summarize_effect,
)
from causal_discovery.intervention import (
    Intervention, run_market_intervention, run_conflict_intervention,
    format_result_for_agent,
)
from causal_discovery.prompts_tests import (
    generate_question_battery,
    build_qa_system_prompt,
    build_qa_observation_prompt,
    build_qa_intervention_prompt,
    build_qa_answer_prompt,
    mock_qa_response,
)


# =============================================================================
# Single question pipeline
# =============================================================================

def _run_qa_agent(
    domain_setup: dict,
    question: dict,
    budget: int,
    api_key: str,
    model: str,
    dry_run: bool,
    verbose: bool,
) -> dict:
    """Run one question through the mini Q&A pipeline.

    Flow: present question → budget interventions → request answer

    Returns dict with:
        question_id, question_type, question_text, agent_answer,
        score, interventions_run, conversation, llm_calls
    """
    domain = domain_setup["domain"]
    variables = domain_setup["variables"]
    intervention_types = domain_setup["intervention_types"]
    qid = question["id"]
    qtype = question["type"]
    qtext = question["question"]

    # Build system prompt
    system_prompt = build_qa_system_prompt(domain, variables)
    conversation = [{"role": "system", "content": system_prompt}]
    llm_calls = 0

    # --- Phase 1: Present question with history ---
    if verbose:
        print(f"    [{qid}] Presenting question: {qtext[:80]}...")

    obs_prompt = build_qa_observation_prompt(
        domain=domain,
        history_summary=domain_setup["history_summary"],
        variables=variables,
        question=qtext,
    )
    conversation.append({"role": "user", "content": obs_prompt})

    if dry_run:
        obs_response = mock_qa_response("observation", qtype, 0, domain)
        obs_raw = json.dumps(obs_response)
    else:
        obs_raw = call_llm(conversation, api_key, model)
        obs_response = parse_json_response(obs_raw)
        llm_calls += 1

    conversation.append({"role": "assistant", "content": obs_raw})

    # --- Phase 2: Interventions ---
    interventions_run = []
    all_results = []
    past_results_summary = ""

    for step in range(budget):
        if verbose:
            print(f"    [{qid}] Intervention {step+1}/{budget}")

        int_prompt = build_qa_intervention_prompt(
            domain=domain,
            variables=variables,
            question=qtext,
            budget_remaining=budget - step,
            intervention_types=intervention_types,
            past_results_summary=past_results_summary,
        )
        conversation.append({"role": "user", "content": int_prompt})

        if dry_run:
            proposal = mock_qa_response("intervention", qtype, step, domain)
            proposal_raw = json.dumps(proposal)
        else:
            proposal_raw = call_llm(conversation, api_key, model)
            proposal = parse_json_response(proposal_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": proposal_raw})

        # Parse and execute intervention
        int_spec = proposal.get("intervention", proposal)
        target = int_spec.get("target", {})
        int_type = int_spec.get("type", "event")

        # Validate type
        if int_type not in ("action", "trait", "event"):
            if verbose:
                print(f"    [{qid}] Invalid type '{int_type}', skipping")
            conversation.append({"role": "user", "content":
                f"Invalid intervention type '{int_type}'. Must be action, trait, or event."})
            conversation.append({"role": "assistant", "content":
                json.dumps({"acknowledged": "Will use a valid type next time."})})
            continue

        # Normalize event targets
        if int_type == "event" and "shock_type" not in target:
            for alt_key in ("event", "shock", "type", "event_type"):
                if alt_key in target:
                    target["shock_type"] = target.pop(alt_key)
                    break

        # Normalize action targets
        if int_type == "action" and "value" not in target:
            for alt_key in ("action", "recommendation", "action_name"):
                if alt_key in target:
                    target["value"] = target.pop(alt_key)
                    break
        if int_type == "action" and "agent_id" not in target:
            for alt_key in ("agent", "agent_name"):
                if alt_key in target:
                    target["agent_id"] = target.pop(alt_key)
                    break

        intervention = Intervention(
            type=int_type,
            target=target,
            run_periods=int_spec.get("run_periods", 3),
            description=int_spec.get("description", f"QA intervention {step+1}"),
        )

        # Execute
        result = None
        try:
            if domain == "market":
                result = run_market_intervention(
                    state_snapshot=domain_setup["state_snapshot"],
                    agents_snapshot=domain_setup["agents_snapshot"],
                    base_params=domain_setup["base_params"],
                    shocks=domain_setup["shocks"],
                    start_period=domain_setup["start_period"],
                    intervention=intervention,
                    rule_based=True,
                )
            else:
                result = run_conflict_intervention(
                    state_snapshot=domain_setup["state_snapshot"],
                    agents_config=domain_setup["agents_snapshot"],
                    faction_agents=domain_setup["faction_agents"],
                    shocks=domain_setup["shocks"],
                    start_period=domain_setup["start_period"],
                    intervention=intervention,
                    rule_based=True,
                )
            result_text = format_result_for_agent(result)
            all_results.append(result)
        except Exception as e:
            result_text = f"INTERVENTION FAILED: {e}"
            if verbose:
                print(f"    [{qid}] Error: {e}")

        if verbose and result:
            effect = _summarize_effect(result)
            print(f"    [{qid}] Result: {effect[:80]}")

        # Feed result back
        conversation.append({"role": "user", "content":
            f"EXPERIMENT RESULT:\n{result_text}\n\nNote this result for when you answer the question."})
        conversation.append({"role": "assistant", "content":
            json.dumps({"noted": "Will incorporate this evidence into my answer."})})

        interventions_run.append({
            "step": step + 1,
            "type": int_type,
            "target": target,
            "description": intervention.description,
            "effect": _summarize_effect(result) if result else "FAILED",
        })

        # Update past results summary for next prompt
        lines = []
        for inv in interventions_run:
            lines.append(f"  {inv['step']}. [{inv['type']}] {inv['description']} => {inv['effect']}")
        past_results_summary = "\n".join(lines)

    # --- Phase 3: Request answer ---
    if verbose:
        print(f"    [{qid}] Requesting final answer...")

    # Build evidence summary from results
    if all_results:
        from causal_discovery.prompts import build_evidence_summary
        evidence = build_evidence_summary(all_results, variables)
    else:
        evidence = "No successful experiments were run."

    answer_prompt = build_qa_answer_prompt(qtext, evidence)
    # Use a fresh conversation for the answer (avoid context overflow)
    answer_conversation = [
        {"role": "system", "content": build_qa_system_prompt(domain, variables)},
        {"role": "user", "content": answer_prompt},
    ]

    if dry_run:
        answer_response = mock_qa_response("answer", qtype, 0, domain)
        answer_raw = json.dumps(answer_response)
    else:
        answer_raw = call_llm(answer_conversation, api_key, model)
        answer_response = parse_json_response(answer_raw)
        llm_calls += 1

    conversation.append({"role": "user", "content": answer_prompt})
    conversation.append({"role": "assistant", "content": answer_raw})

    # Score the answer
    score = score_qa_answer(answer_response, question["scoring_key"], qtype)

    return {
        "question_id": qid,
        "question_type": qtype,
        "question_text": qtext,
        "expected_answer": question["expected_answer"],
        "agent_answer": answer_response,
        "score": score,
        "interventions_run": interventions_run,
        "conversation": conversation,
        "llm_calls": llm_calls,
    }


# =============================================================================
# Scoring
# =============================================================================

def score_qa_answer(
    agent_response: dict, scoring_key: dict, question_type: str,
) -> dict:
    """Score one answer. Returns {correct, partial_credit, explanation}."""
    answer = agent_response.get("answer", "").lower()
    reasoning = agent_response.get("reasoning", "").lower()
    full_text = f"{answer} {reasoning}"

    if question_type == "counterfactual":
        correct_answer = scoring_key.get("correct_answer", "yes").lower()
        # Check if agent said yes or no
        agent_says_yes = any(w in answer for w in ["yes", "would change", "would be affected"])
        agent_says_no = any(w in answer for w in ["no", "would not change", "wouldn't change", "no effect"])

        if correct_answer == "yes":
            correct = agent_says_yes and not agent_says_no
        else:
            correct = agent_says_no and not agent_says_yes

        return {
            "correct": correct,
            "partial_credit": 1.0 if correct else 0.0,
            "explanation": f"Expected '{correct_answer}', agent answered: {answer[:100]}",
        }

    elif question_type == "mechanism":
        mediator = scoring_key.get("mediator", "").lower()
        has_direct = scoring_key.get("has_direct_edge", False)
        partial = 0.0

        # Check if agent identified the mediator
        if mediator in full_text:
            partial += 0.5

        # Check if agent correctly identified direct/indirect
        says_both = any(w in full_text for w in ["both", "direct and indirect"])
        says_indirect_only = any(w in full_text for w in ["indirect only", "indirectly", "no direct"])

        if has_direct and says_both:
            partial += 0.5
        elif not has_direct and says_indirect_only:
            partial += 0.5

        return {
            "correct": partial >= 0.75,
            "partial_credit": partial,
            "explanation": f"Mediator={mediator} (found={mediator in full_text}), direct={has_direct}",
        }

    elif question_type == "robustness":
        correct_answer = scoring_key.get("correct_answer", "yes").lower()
        vanishes = scoring_key.get("vanishes", True)

        agent_says_yes = any(w in answer for w in ["yes", "vanish", "would vanish", "disappear", "eliminated"])
        agent_says_no = any(w in answer for w in ["no", "would not vanish", "persist", "wouldn't vanish", "still"])

        if vanishes:
            correct = agent_says_yes and not agent_says_no
        else:
            correct = agent_says_no and not agent_says_yes

        return {
            "correct": correct,
            "partial_credit": 1.0 if correct else 0.0,
            "explanation": f"Expected vanishes={vanishes}, agent answer: {answer[:100]}",
        }

    elif question_type == "direction":
        correct_dir = scoring_key.get("correct_direction", ("", ""))
        wrong_dir = scoring_key.get("wrong_direction", ("", ""))

        a, b = correct_dir
        # Check if agent stated correct direction
        correct_pattern = f"{a.lower()} cause" in full_text or f"{a.lower()} → {b.lower()}" in full_text or f"{a.lower()} -> {b.lower()}" in full_text
        wrong_pattern = f"{b.lower()} cause" in full_text or f"{b.lower()} → {a.lower()}" in full_text or f"{b.lower()} -> {a.lower()}" in full_text

        # Also check "the first" / "the second" patterns
        if "first" in answer and "causes" in answer:
            correct_pattern = True
        if "second" in answer and "causes" in answer and "first" not in answer:
            wrong_pattern = True

        correct = correct_pattern and not wrong_pattern

        return {
            "correct": correct,
            "partial_credit": 1.0 if correct else 0.0,
            "explanation": f"Correct direction: {a}->{b}, agent answer: {answer[:100]}",
        }

    return {"correct": False, "partial_credit": 0.0, "explanation": "Unknown question type"}


# =============================================================================
# Main pipeline
# =============================================================================

def run_oracle_qa(
    domain: str = "market",
    budget_per_question: int = 3,
    n_per_type: int = 3,
    n_warmup: int = 10,
    seed: int = 42,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    dry_run: bool = False,
    output_dir: str = "",
    verbose: bool = True,
) -> dict:
    """Main entry point. Setup domain, generate questions, run each, score, save."""

    # Get ground truth
    if domain == "market":
        gt = get_market_ground_truth()
        variables = MARKET_VARIABLES
    else:
        gt = get_conflict_ground_truth()
        variables = CONFLICT_VARIABLES

    # Generate questions
    questions = generate_question_battery(
        domain=domain,
        gt_matrix=gt,
        variables=variables,
        n_per_type=n_per_type,
        seed=seed,
    )

    if verbose:
        print(f"Generated {len(questions)} questions for {domain} domain")
        for q in questions:
            print(f"  [{q['id']}] {q['type']}: {q['question'][:70]}...")

    # Setup domain once
    if verbose:
        print(f"\nSetting up {domain} domain (warmup={n_warmup})...")
    domain_setup = setup_domain(domain, n_warmup=n_warmup, seed=seed, budget=budget_per_question * 3)

    # Output directory
    if not output_dir:
        model_short = model.split("/")[-1] if "/" in model else model
        output_dir = str(
            Path("outputs/causal_discovery/oracle_qa")
            / f"{domain}_{model_short}"
        )
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "per_question").mkdir(exist_ok=True)

    # Run each question
    per_question_results = []
    for q in questions:
        if verbose:
            print(f"\n  Question {q['id']} ({q['type']}):")

        result = _run_qa_agent(
            domain_setup=domain_setup,
            question=q,
            budget=budget_per_question,
            api_key=api_key,
            model=model,
            dry_run=dry_run,
            verbose=verbose,
        )
        per_question_results.append(result)

        if verbose:
            s = result["score"]
            print(f"    Score: correct={s['correct']}, partial={s['partial_credit']:.2f}")
            print(f"    Explanation: {s['explanation'][:80]}")

        # Save per-question result
        save_result = {k: v for k, v in result.items() if k != "conversation"}
        with open(out_path / "per_question" / f"{q['id']}.json", "w") as f:
            json.dump(save_result, f, indent=2, default=str)

        # Save conversation separately (can be large)
        with open(out_path / "per_question" / f"{q['id']}_conversation.json", "w") as f:
            json.dump(result["conversation"], f, indent=2)

    # Aggregate scores
    by_type = {}
    for r in per_question_results:
        qtype = r["question_type"]
        if qtype not in by_type:
            by_type[qtype] = {"correct": 0, "total": 0, "partial_sum": 0.0}
        by_type[qtype]["total"] += 1
        by_type[qtype]["correct"] += int(r["score"]["correct"])
        by_type[qtype]["partial_sum"] += r["score"]["partial_credit"]

    type_summaries = {}
    for qtype, stats in by_type.items():
        type_summaries[qtype] = {
            "accuracy": round(stats["correct"] / stats["total"], 3) if stats["total"] > 0 else 0.0,
            "mean_partial_credit": round(stats["partial_sum"] / stats["total"], 3) if stats["total"] > 0 else 0.0,
            "correct": stats["correct"],
            "total": stats["total"],
        }

    total_correct = sum(s["correct"] for s in by_type.values())
    total_questions = sum(s["total"] for s in by_type.values())
    total_partial = sum(s["partial_sum"] for s in by_type.values())

    summary = {
        "domain": domain,
        "model": model,
        "budget_per_question": budget_per_question,
        "n_per_type": n_per_type,
        "seed": seed,
        "dry_run": dry_run,
        "total_questions": total_questions,
        "overall_accuracy": round(total_correct / total_questions, 3) if total_questions > 0 else 0.0,
        "overall_mean_partial_credit": round(total_partial / total_questions, 3) if total_questions > 0 else 0.0,
        "by_type": type_summaries,
        "per_question": [
            {
                "id": r["question_id"],
                "type": r["question_type"],
                "question": r["question_text"],
                "expected": r["expected_answer"],
                "agent_answer": r["agent_answer"].get("answer", ""),
                "correct": r["score"]["correct"],
                "partial_credit": r["score"]["partial_credit"],
                "explanation": r["score"]["explanation"],
                "n_interventions": len(r["interventions_run"]),
                "llm_calls": r["llm_calls"],
            }
            for r in per_question_results
        ],
    }

    # Save summary
    with open(out_path / "results.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if verbose:
        print(f"\n{'='*60}")
        print("ORACLE QA RESULTS")
        print(f"{'='*60}")
        print(f"  Overall accuracy: {summary['overall_accuracy']:.3f} ({total_correct}/{total_questions})")
        print(f"  Mean partial credit: {summary['overall_mean_partial_credit']:.3f}")
        print(f"\n  By type:")
        for qtype, stats in type_summaries.items():
            print(f"    {qtype}: {stats['accuracy']:.3f} ({stats['correct']}/{stats['total']})")
        print(f"\nResults saved to {out_path}")

    return summary


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Oracle QA for Causal Discovery",
    )
    parser.add_argument("--domain", default="market", choices=["market", "conflict"])
    parser.add_argument("--budget", type=int, default=3,
                       help="Intervention budget per question")
    parser.add_argument("--n-per-type", type=int, default=3,
                       help="Number of questions per type")
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

    run_oracle_qa(
        domain=args.domain,
        budget_per_question=args.budget,
        n_per_type=args.n_per_type,
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
