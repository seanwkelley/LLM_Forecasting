"""
DebateForecaster — 2 agents, 3 rounds of deliberation.

Round 1: Independent initial predictions
Round 2: Each sees the other's Round 1 forecast + reasoning, revises
Round 3: Each sees the other's Round 2 revision, provides final forecast

Ensemble: average of the two Round 3 forecasts.
Total: 6 LLM calls per period.
"""

from __future__ import annotations

from forecast_multi.evaluation import ensemble_forecasts
from forecast_multi.llm_client import LLMClient, parse_forecast_response


class DebateForecaster:
    """Debate forecaster: 2 agents × 3 rounds."""

    name = "debate"

    def __init__(self, client: LLMClient, agent_a: dict, agent_b: dict):
        self.client = client
        self.agent_a = agent_a
        self.agent_b = agent_b

    def forecast(
        self,
        domain,
        system_prompt_base: str,
        user_prompt: str,
    ) -> dict:
        """Run 3-round debate between two agents.

        Returns
        -------
        dict with:
            forecasts: list of all 6 forecasts (3 rounds × 2 agents)
            ensemble: averaged final (Round 3) forecasts
        """
        all_forecasts = []

        # Build agent-specific system prompts
        sys_a = domain.get_system_prompt(self.agent_a["prompt"])
        sys_b = domain.get_system_prompt(self.agent_b["prompt"])

        # Maintain conversation histories for multi-turn
        history_a = [
            {"role": "system", "content": sys_a},
            {"role": "user", "content": user_prompt},
        ]
        history_b = [
            {"role": "system", "content": sys_b},
            {"role": "user", "content": user_prompt},
        ]

        # --- Round 1: Independent initial predictions ---
        resp_a, ok_a = self.client.call(history_a)
        self.client.rate_limit_wait()
        forecast_a1 = self._parse_or_fallback(resp_a, ok_a)
        forecast_a1.update({
            "forecaster_id": self.agent_a["id"],
            "round": "round_1",
        })
        all_forecasts.append(forecast_a1)

        resp_b, ok_b = self.client.call(history_b)
        self.client.rate_limit_wait()
        forecast_b1 = self._parse_or_fallback(resp_b, ok_b)
        forecast_b1.update({
            "forecaster_id": self.agent_b["id"],
            "round": "round_1",
        })
        all_forecasts.append(forecast_b1)

        # Add assistant responses to histories
        history_a.append({"role": "assistant", "content": resp_a if ok_a else "{}"})
        history_b.append({"role": "assistant", "content": resp_b if ok_b else "{}"})

        # --- Round 2: Critique and revision ---
        critique_for_a = self._build_critique_prompt(
            self.agent_b["name"], forecast_b1, round_num=2,
        )
        critique_for_b = self._build_critique_prompt(
            self.agent_a["name"], forecast_a1, round_num=2,
        )

        history_a.append({"role": "user", "content": critique_for_a})
        history_b.append({"role": "user", "content": critique_for_b})

        resp_a2, ok_a2 = self.client.call(history_a)
        self.client.rate_limit_wait()
        forecast_a2 = self._parse_or_fallback(resp_a2, ok_a2)
        forecast_a2.update({
            "forecaster_id": self.agent_a["id"],
            "round": "round_2",
        })
        all_forecasts.append(forecast_a2)

        resp_b2, ok_b2 = self.client.call(history_b)
        self.client.rate_limit_wait()
        forecast_b2 = self._parse_or_fallback(resp_b2, ok_b2)
        forecast_b2.update({
            "forecaster_id": self.agent_b["id"],
            "round": "round_2",
        })
        all_forecasts.append(forecast_b2)

        history_a.append({"role": "assistant", "content": resp_a2 if ok_a2 else "{}"})
        history_b.append({"role": "assistant", "content": resp_b2 if ok_b2 else "{}"})

        # --- Round 3: Final forecast ---
        final_for_a = self._build_critique_prompt(
            self.agent_b["name"], forecast_b2, round_num=3,
        )
        final_for_b = self._build_critique_prompt(
            self.agent_a["name"], forecast_a2, round_num=3,
        )

        history_a.append({"role": "user", "content": final_for_a})
        history_b.append({"role": "user", "content": final_for_b})

        resp_a3, ok_a3 = self.client.call(history_a)
        self.client.rate_limit_wait()
        forecast_a3 = self._parse_or_fallback(resp_a3, ok_a3)
        forecast_a3.update({
            "forecaster_id": self.agent_a["id"],
            "round": "final",
        })
        all_forecasts.append(forecast_a3)

        resp_b3, ok_b3 = self.client.call(history_b)
        self.client.rate_limit_wait()
        forecast_b3 = self._parse_or_fallback(resp_b3, ok_b3)
        forecast_b3.update({
            "forecaster_id": self.agent_b["id"],
            "round": "final",
        })
        all_forecasts.append(forecast_b3)

        # Ensemble: average of final round forecasts
        ens = ensemble_forecasts([forecast_a3, forecast_b3])
        ens["forecaster_id"] = "ensemble"
        ens["round"] = "final"
        ens["source"] = "ensemble"

        return {
            "forecasts": all_forecasts,
            "ensemble": ens,
        }

    def _build_critique_prompt(
        self, other_name: str, other_forecast: dict, round_num: int,
    ) -> str:
        """Build the prompt showing the other agent's forecast."""
        reasoning = other_forecast.get("reasoning", "No reasoning provided")
        prob_up = other_forecast.get("prob_up", 0.33)
        prob_down = other_forecast.get("prob_down", 0.33)
        prob_flat = other_forecast.get("prob_flat", 0.34)

        # Include point estimate if available
        point_parts = []
        for key in ("predicted_price", "predicted_ei"):
            if key in other_forecast and other_forecast[key] is not None:
                point_parts.append(f"Point estimate: {other_forecast[key]:.2f}")

        point_str = f"\n{'; '.join(point_parts)}" if point_parts else ""

        if round_num == 2:
            return (
                f"Another analyst ({other_name}) predicted:\n"
                f"- prob_up: {prob_up:.3f}, prob_down: {prob_down:.3f}, "
                f"prob_flat: {prob_flat:.3f}{point_str}\n"
                f"- Reasoning: {reasoning}\n\n"
                f"Consider their perspective. Where do you agree or disagree? "
                f"Provide your revised forecast as the same JSON format."
            )
        else:  # round 3
            return (
                f"After revision, the other analyst ({other_name}) now predicts:\n"
                f"- prob_up: {prob_up:.3f}, prob_down: {prob_down:.3f}, "
                f"prob_flat: {prob_flat:.3f}{point_str}\n"
                f"- Reasoning: {reasoning}\n\n"
                f"After deliberation, provide your FINAL forecast as the same JSON format."
            )

    @staticmethod
    def _parse_or_fallback(response: str, success: bool) -> dict:
        """Parse response or return uniform fallback."""
        if success:
            parsed = parse_forecast_response(response)
            if parsed is not None:
                parsed["source"] = "llm"
                return parsed

        return {
            "prob_up": 0.333,
            "prob_down": 0.333,
            "prob_flat": 0.334,
            "reasoning": "FALLBACK",
            "source": "fallback",
        }
