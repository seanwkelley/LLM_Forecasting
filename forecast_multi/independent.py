"""
IndependentEnsemble — N forecasters with different personas, no communication.

Each makes 1 independent LLM call. Post-hoc ensemble: average probabilities.
"""

from __future__ import annotations

from forecast_multi.evaluation import ensemble_forecasts
from forecast_multi.llm_client import LLMClient, parse_forecast_response


class IndependentEnsemble:
    """Independent ensemble: N parallel forecasters, averaged post-hoc."""

    name = "independent"

    def __init__(self, client: LLMClient, personas: list[dict]):
        self.client = client
        self.personas = personas

    def forecast(
        self,
        domain,
        system_prompt_template: str,
        user_prompt: str,
    ) -> dict:
        """Run N independent forecasts and ensemble them.

        Parameters
        ----------
        domain : MarketDomain or ConflictDomain
        system_prompt_template : str
            The system prompt with {persona_prompt} placeholder, or a base
            that gets the persona prepended.
        user_prompt : str
            The shared user prompt.

        Returns
        -------
        dict with:
            forecasts: list of N individual forecast dicts
            ensemble: averaged ensemble forecast dict
        """
        individual_forecasts = []

        for persona in self.personas:
            sys_prompt = domain.get_system_prompt(persona["prompt"])

            response, success = self.client.call_single(sys_prompt, user_prompt)
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
                "forecaster_id": persona["id"],
                "round": "final",
                "source": source,
            }
            individual_forecasts.append(forecast)

        # Ensemble: average probabilities
        ens = ensemble_forecasts(individual_forecasts)
        ens["forecaster_id"] = "ensemble"
        ens["round"] = "final"
        ens["source"] = "ensemble"

        return {
            "forecasts": individual_forecasts,
            "ensemble": ens,
        }
