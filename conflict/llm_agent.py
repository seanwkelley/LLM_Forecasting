"""
LLM Conflict Agent -- Wraps LLM API calls to produce action recommendations.

Each agent receives a persona-specific system prompt and a per-period user
prompt with conflict state. Returns a validated action recommendation.

Uses OpenRouter API with JSON output mode (same pattern as market/llm_agent.py).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from conflict.engine import ACTION_SPACE, ConflictState
from conflict.prompts import get_system_prompt, get_system_prompt_no_persona, build_user_prompt


@dataclass
class LLMAgentConfig:
    """Configuration for LLM conflict agents."""
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "meta-llama/llama-3.1-8b-instruct"
    temperature: float = 0.7
    max_tokens: int = 300
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 2.0
    rate_limit_delay: float = 0.5
    use_persona: bool = True


@dataclass
class LLMCallStats:
    """Track API call statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    parse_failures: int = 0
    total_tokens: int = 0

    @property
    def success_rate(self) -> float:
        return self.successful_calls / self.total_calls if self.total_calls > 0 else 0.0


class LLMConflictAgent:
    """Wraps a single LLM agent that recommends actions in the conflict sim.

    One instance per agent per simulation. Each period is independent.
    """

    def __init__(self, agent_template: dict, config: LLMAgentConfig):
        self.agent_id = agent_template["agent_id"]
        self.agent_template = agent_template
        self.faction = agent_template["faction"]
        self.role = agent_template["role"]
        self.config = config
        if config.use_persona:
            self.system_prompt = get_system_prompt(agent_template)
        else:
            self.system_prompt = get_system_prompt_no_persona(agent_template)
        self.stats = LLMCallStats()

    def get_recommendation(
        self,
        state: ConflictState,
        shock_description: str = "",
    ) -> Optional[dict]:
        """Query the LLM for an action recommendation.

        Returns
        -------
        dict with keys: agent_id, agent_role, faction, action, reasoning
        or None on failure.
        """
        user_prompt = build_user_prompt(
            agent=self.agent_template,
            state=state,
            shock_description=shock_description,
        )

        response_text, success = self._call_llm(user_prompt)

        if not success:
            return None

        return self._parse_recommendation(response_text, state)

    def _call_llm(self, user_prompt: str) -> tuple[str, bool]:
        """Make the API call with retry logic."""
        self.stats.total_calls += 1

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout,
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    usage = result.get("usage", {})
                    self.stats.total_tokens += usage.get("total_tokens", 0)
                    self.stats.successful_calls += 1
                    return content, True

                elif response.status_code == 429:
                    wait = self.config.retry_delay * (2 ** attempt)
                    print(f"  [RATE LIMIT] {self.agent_id} -- waiting {wait:.0f}s")
                    time.sleep(wait)
                    continue

                else:
                    if attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay)
                        continue
                    self.stats.failed_calls += 1
                    print(f"  [ERROR] {self.agent_id} HTTP {response.status_code}")
                    return "", False

            except requests.exceptions.Timeout:
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                self.stats.failed_calls += 1
                print(f"  [TIMEOUT] {self.agent_id}")
                return "", False

            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                self.stats.failed_calls += 1
                print(f"  [ERROR] {self.agent_id}: {e}")
                return "", False

        self.stats.failed_calls += 1
        return "", False

    def _parse_recommendation(
        self,
        response_text: str,
        state: ConflictState,
    ) -> Optional[dict]:
        """Parse LLM JSON response into a validated recommendation."""
        # Strip thinking tags (e.g., Qwen3)
        response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()

        # Try direct JSON parse
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    self.stats.parse_failures += 1
                    return None
            else:
                match = re.search(r"\{[^{}]*\}", response_text)
                if match:
                    try:
                        data = json.loads(match.group(0))
                    except json.JSONDecodeError:
                        self.stats.parse_failures += 1
                        return None
                else:
                    self.stats.parse_failures += 1
                    return None

        action_name = str(data.get("action", "")).lower().strip().replace(" ", "_")
        reasoning = str(data.get("reasoning", ""))

        # Validate action name
        if action_name not in ACTION_SPACE:
            # Try fuzzy match
            for valid_name in ACTION_SPACE:
                if valid_name in action_name or action_name in valid_name:
                    action_name = valid_name
                    break
            else:
                self.stats.parse_failures += 1
                return None

        # Check affordability
        own_faction = state.factions[self.faction]
        if ACTION_SPACE[action_name]["cost"] > own_faction.resources:
            # Pick the most escalatory affordable action matching the agent's intent
            affordable = [
                (n, s) for n, s in ACTION_SPACE.items()
                if s["cost"] <= own_faction.resources
            ]
            if not affordable:
                action_name = "intelligence_gathering"
            else:
                target_delta = ACTION_SPACE[action_name]["escalation_delta"]
                action_name = min(affordable,
                    key=lambda ns: abs(ns[1]["escalation_delta"] - target_delta)
                )[0]

        return {
            "agent_id": self.agent_id,
            "agent_role": self.role,
            "faction": self.faction,
            "action": action_name,
            "reasoning": reasoning,
        }


class LLMAgentPool:
    """Manages all LLM agents for a conflict simulation.

    Creates one LLMConflictAgent per agent, handles rate limiting.
    """

    def __init__(self, config: LLMAgentConfig):
        self.config = config
        self.agents: dict[str, LLMConflictAgent] = {}

    def register_agent(self, agent_template: dict):
        """Register an agent with the pool."""
        self.agents[agent_template["agent_id"]] = LLMConflictAgent(
            agent_template, self.config
        )

    def register_all(self, agent_templates: list[dict]):
        """Register all agents."""
        for tmpl in agent_templates:
            self.register_agent(tmpl)

    def collect_recommendations(
        self,
        state: ConflictState,
        shock_description: str = "",
        verbose: bool = True,
    ) -> list[dict]:
        """Collect action recommendations from all agents for one period.

        Returns
        -------
        List of recommendation dicts (agents that failed are excluded).
        """
        recommendations = []

        for aid, llm_agent in self.agents.items():
            rec = llm_agent.get_recommendation(
                state=state,
                shock_description=shock_description,
            )

            if rec is not None:
                recommendations.append(rec)
                if verbose:
                    print(f"    {aid:15s} ({rec['faction']:7s}) | "
                          f"{rec['action']:20s} | {rec['reasoning'][:60]}")
            else:
                if verbose:
                    print(f"    {aid:15s} | NO RECOMMENDATION")

            # Rate limit between calls
            if self.config.rate_limit_delay > 0:
                time.sleep(self.config.rate_limit_delay)

        return recommendations

    def get_aggregate_stats(self) -> dict:
        """Aggregate statistics across all agents."""
        total = LLMCallStats()
        for agent in self.agents.values():
            total.total_calls += agent.stats.total_calls
            total.successful_calls += agent.stats.successful_calls
            total.failed_calls += agent.stats.failed_calls
            total.parse_failures += agent.stats.parse_failures
            total.total_tokens += agent.stats.total_tokens

        return {
            "total_calls": total.total_calls,
            "successful_calls": total.successful_calls,
            "failed_calls": total.failed_calls,
            "parse_failures": total.parse_failures,
            "success_rate": f"{total.success_rate:.1%}",
            "total_tokens": total.total_tokens,
        }
