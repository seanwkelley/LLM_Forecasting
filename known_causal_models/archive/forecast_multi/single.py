"""
SingleForecaster — one LLM call per period with a generic expert persona.

The simplest communication structure: no deliberation, no ensemble.
"""

from __future__ import annotations

from forecast_multi.llm_client import LLMClient, parse_forecast_response


SINGLE_PERSONA = (
    "You are a careful, well-calibrated analyst. Weigh all available evidence "
    "— trends, levels, structural factors — and form a balanced prediction. "
    "Avoid overconfidence; assign non-trivial probability to all outcomes "
    "unless the evidence is overwhelming."
)


class SingleForecaster:
    """Single forecaster: 1 LLM call per period."""

    name = "single"

    def __init__(self, client: LLMClient):
        self.client = client

    def forecast(
        self,
        domain,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """Run a single forecast.

        Returns
        -------
        dict with keys:
            forecasts: list of individual forecast dicts (length 1)
            ensemble: the single forecast (same as individual)
        """
        response, success = self.client.call_single(system_prompt, user_prompt)
        self.client.rate_limit_wait()

        if success:
            parsed = parse_forecast_response(response)
        else:
            parsed = None

        if parsed is None:
            # Fallback: uniform probabilities
            target_history_key = domain.target_key
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
            "forecaster_id": "single",
            "round": "final",
            "source": source,
        }

        return {
            "forecasts": [forecast],
            "ensemble": forecast,
        }

    @staticmethod
    def get_persona_prompt() -> str:
        return SINGLE_PERSONA
