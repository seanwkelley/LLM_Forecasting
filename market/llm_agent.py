"""
LLM Market Agent — Wraps LLM API calls to produce trading orders.

Each agent receives a role-specific system prompt and a per-period user
prompt with market state + private signals. Returns a validated Order.

Uses OpenRouter API (same as forecaster_base.py) with JSON output mode.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from market.engine import AgentState, MarketState, Order
from market.prompts import get_system_prompt, build_user_prompt, generate_price_ticks


@dataclass
class LLMAgentConfig:
    """Configuration for LLM market agents."""
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "meta-llama/llama-3.1-8b-instruct"
    temperature: float = 0.7
    max_tokens: int = 300
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 2.0
    rate_limit_delay: float = 0.5  # seconds between calls


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


class LLMMarketAgent:
    """Wraps a single LLM agent that trades in the market.

    One instance per agent per simulation. Maintains conversation-free
    interaction (each period is independent — no message history).
    """

    def __init__(self, agent_id: str, role: str, config: LLMAgentConfig):
        self.agent_id = agent_id
        self.role = role
        self.config = config
        self.system_prompt = get_system_prompt(agent_id, role)
        self.stats = LLMCallStats()

    def get_order(
        self,
        agent_state: AgentState,
        market_state: MarketState,
        price_ticks: list[float],
        shock_description: str = "",
    ) -> Optional[Order]:
        """Query the LLM for a trading order.

        Parameters
        ----------
        agent_state : AgentState
            This agent's current state.
        market_state : MarketState
            Public market state.
        price_ticks : list[float]
            Available price levels.
        shock_description : str
            Public shock announcements.

        Returns
        -------
        Order or None if the agent chooses not to trade.
        """
        user_prompt = build_user_prompt(
            agent=agent_state,
            state=market_state,
            price_ticks=price_ticks,
            shock_description=shock_description,
        )

        response_text, success = self._call_llm(user_prompt)

        if not success:
            return None

        return self._parse_order(response_text, agent_state, price_ticks)

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
                    # Track token usage
                    usage = result.get("usage", {})
                    self.stats.total_tokens += usage.get("total_tokens", 0)
                    self.stats.successful_calls += 1
                    return content, True

                elif response.status_code == 429:
                    wait = self.config.retry_delay * (2 ** attempt)
                    print(f"  [RATE LIMIT] {self.agent_id} — waiting {wait:.0f}s")
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

    def _parse_order(
        self,
        response_text: str,
        agent_state: AgentState,
        price_ticks: list[float],
    ) -> Optional[Order]:
        """Parse LLM JSON response into a validated Order."""
        # Try direct JSON parse
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code block
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    self.stats.parse_failures += 1
                    return None
            else:
                # Last resort: find anything that looks like JSON
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

        # Extract fields with defaults
        side = str(data.get("side", "")).lower().strip()
        quantity = data.get("quantity", 0)
        limit_price = data.get("limit_price", 0)
        reasoning = str(data.get("reasoning", ""))

        # Validate side
        if side not in ("buy", "sell"):
            self.stats.parse_failures += 1
            return None

        # Enforce role constraints
        if agent_state.role == "producer" and side != "sell":
            side = "sell"  # producers can only sell
        if agent_state.role == "consumer" and side != "buy":
            side = "buy"  # consumers can only buy

        # Validate quantity
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 0

        if quantity <= 0:
            return None  # agent chose not to trade

        # Validate and snap price to nearest tick
        try:
            limit_price = float(limit_price)
        except (ValueError, TypeError):
            self.stats.parse_failures += 1
            return None

        if price_ticks:
            limit_price = min(price_ticks, key=lambda t: abs(t - limit_price))

        return Order(
            agent_id=agent_state.agent_id,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            reasoning=reasoning,
        )


class LLMAgentPool:
    """Manages all LLM agents for a market simulation.

    Creates one LLMMarketAgent per agent_id, sharing the same API config.
    Handles rate limiting between calls.
    """

    def __init__(self, config: LLMAgentConfig):
        self.config = config
        self.agents: dict[str, LLMMarketAgent] = {}

    def register_agent(self, agent_id: str, role: str):
        """Register an agent with the pool."""
        self.agents[agent_id] = LLMMarketAgent(agent_id, role, self.config)

    def register_all(self, agent_states: dict[str, AgentState]):
        """Register all agents from market state."""
        for aid, astate in agent_states.items():
            self.register_agent(aid, astate.role)

    def collect_orders(
        self,
        agent_states: dict[str, AgentState],
        market_state: MarketState,
        price_ticks: list[float],
        shock_description: str = "",
        verbose: bool = True,
    ) -> list[Order]:
        """Collect orders from all LLM agents for one period.

        Handles rate limiting between API calls.

        Returns
        -------
        List of validated orders (agents that chose not to trade are excluded).
        """
        orders = []

        for aid, llm_agent in self.agents.items():
            if aid not in agent_states:
                continue

            order = llm_agent.get_order(
                agent_state=agent_states[aid],
                market_state=market_state,
                price_ticks=price_ticks,
                shock_description=shock_description,
            )

            if order is not None:
                orders.append(order)
                if verbose:
                    print(f"    {aid:15s} | {order.side:4s} {order.quantity:3d} @ "
                          f"${order.limit_price:.2f} | {order.reasoning[:60]}")
            else:
                if verbose:
                    print(f"    {aid:15s} | NO ORDER")

            # Rate limit between calls
            if self.config.rate_limit_delay > 0:
                time.sleep(self.config.rate_limit_delay)

        return orders

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
