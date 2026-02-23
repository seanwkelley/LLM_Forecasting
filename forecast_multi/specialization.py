"""
SpecializationForecaster — 3 domain specialists + 1 aggregator.

Each specialist focuses on a subgraph of the causal model and sees only
their relevant variables. The aggregator integrates all specialist analyses.

Total: 3-4 LLM calls per period (3 specialists + optional LLM aggregator).
"""

from __future__ import annotations

import numpy as np

from forecast_multi.causal_text import get_graph_text
from forecast_multi.evaluation import ensemble_forecasts
from forecast_multi.llm_client import LLMClient, parse_forecast_response


class SpecializationForecaster:
    """Specialization forecaster: 3 specialists + 1 aggregator."""

    name = "specialization"

    def __init__(
        self,
        client: LLMClient,
        subgraphs: dict[str, dict],
        mechanistic_aggregator: bool = False,
    ):
        self.client = client
        self.subgraphs = subgraphs
        self.mechanistic_aggregator = mechanistic_aggregator

    def forecast(
        self,
        domain,
        system_prompt_base: str,
        user_prompt: str,
        expanded_vars: dict[str, float] | None = None,
    ) -> dict:
        """Run specialist + aggregator pipeline.

        Parameters
        ----------
        domain : MarketDomain or ConflictDomain
        system_prompt_base : str
            Base system prompt (unused directly; specialists get their own).
        user_prompt : str
            The base user prompt with time-series data.
        expanded_vars : dict
            All expanded variables for this period (specialists filter to their subgraph).

        Returns
        -------
        dict with:
            forecasts: list of all specialist + aggregator forecasts
            ensemble: the aggregator's final forecast
        """
        all_forecasts = []
        specialist_analyses = []

        if expanded_vars is None:
            expanded_vars = {}

        # --- Specialist phase ---
        for name, spec in self.subgraphs.items():
            # Build specialist-specific prompt with their subgraph variables
            spec_vars = {
                k: v for k, v in expanded_vars.items()
                if k in spec["variables"] and isinstance(v, (int, float))
            }

            spec_section = f"\n## Your Domain: {name.title()} Analysis\n"
            if spec_vars:
                spec_section += "Relevant variables for your analysis:\n"
                for var in sorted(spec_vars.keys()):
                    val = spec_vars[var]
                    label = var.replace("_", " ").title()
                    if isinstance(val, float):
                        spec_section += f"- {label}: {val:.4f}\n"
                    else:
                        spec_section += f"- {label}: {val}\n"

            full_user_prompt = user_prompt + spec_section

            sys_prompt = domain.get_system_prompt(spec["prompt"])

            response, success = self.client.call_single(sys_prompt, full_user_prompt)
            self.client.rate_limit_wait()

            if success:
                parsed = parse_forecast_response(response)
            else:
                parsed = None

            if parsed is None:
                parsed = {
                    "prob_up": 0.333,
                    "prob_down": 0.333,
                    "prob_flat": 0.334,
                    "reasoning": "FALLBACK",
                }
                source = "fallback"
            else:
                source = "llm"

            forecast = {
                **parsed,
                "forecaster_id": f"specialist_{name}",
                "round": "specialist",
                "source": source,
            }
            all_forecasts.append(forecast)

            specialist_analyses.append({
                "name": name,
                "forecast": forecast,
                "reasoning": parsed.get("reasoning", ""),
            })

        # --- Aggregation phase ---
        if self.mechanistic_aggregator:
            # Simple average (or could be confidence-weighted)
            specialist_forecasts = [sa["forecast"] for sa in specialist_analyses]
            agg = ensemble_forecasts(specialist_forecasts)
            agg["forecaster_id"] = "aggregator_mechanistic"
            agg["round"] = "final"
            agg["source"] = "mechanistic"
            all_forecasts.append(agg)
        else:
            # LLM aggregator
            agg = self._llm_aggregation(
                domain, user_prompt, specialist_analyses, expanded_vars,
            )
            all_forecasts.append(agg)

        return {
            "forecasts": all_forecasts,
            "ensemble": agg,
        }

    def _llm_aggregation(
        self,
        domain,
        user_prompt: str,
        specialist_analyses: list[dict],
        expanded_vars: dict,
    ) -> dict:
        """Use an LLM to integrate specialist analyses."""
        # Build aggregator prompt
        agg_system = domain.get_system_prompt(
            "You are a chief analyst integrating assessments from domain specialists. "
            "Weigh each specialist's input based on the relevance and confidence of "
            "their analysis. Form a balanced final prediction."
        )

        analyses_text = "\n## Specialist Analyses\n"
        for sa in specialist_analyses:
            f = sa["forecast"]
            analyses_text += (
                f"\n**{sa['name'].title()} Specialist:**\n"
                f"- Prediction: prob_up={f['prob_up']:.3f}, "
                f"prob_down={f['prob_down']:.3f}, prob_flat={f['prob_flat']:.3f}\n"
            )
            # Include point estimate if available
            for key in ("predicted_price", "predicted_ei"):
                if key in f and f[key] is not None:
                    analyses_text += f"- Point estimate: {f[key]:.2f}\n"
            analyses_text += f"- Analysis: {sa['reasoning']}\n"

        # Include causal graph context for the aggregator
        graph_text = get_graph_text(domain.name)
        agg_user = user_prompt + f"\n{graph_text}" + analyses_text

        response, success = self.client.call_single(agg_system, agg_user)
        self.client.rate_limit_wait()

        if success:
            parsed = parse_forecast_response(response)
        else:
            parsed = None

        if parsed is None:
            # Fall back to mechanical average of specialists
            specialist_forecasts = [sa["forecast"] for sa in specialist_analyses]
            parsed = ensemble_forecasts(specialist_forecasts)
            parsed["reasoning"] = "FALLBACK (averaged specialists)"
            source = "fallback"
        else:
            source = "llm"

        return {
            **parsed,
            "forecaster_id": "aggregator",
            "round": "final",
            "source": source,
        }
