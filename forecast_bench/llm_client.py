"""
LLM Client — Generic OpenRouter client for belief sensitivity experiments.

Supports both single-shot and multi-turn (conversational) API calls.
Generalized from market/llm_agent.py API call pattern.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

import requests


@dataclass
class CallStats:
    """Track API call statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    parse_failures: int = 0
    total_tokens: int = 0

    @property
    def success_rate(self) -> float:
        return self.successful_calls / self.total_calls if self.total_calls > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "parse_failures": self.parse_failures,
            "success_rate": f"{self.success_rate:.1%}",
            "total_tokens": self.total_tokens,
        }


class LLMClient:
    """Generic OpenRouter API client with retry logic.

    Parameters
    ----------
    api_key : str
        OpenRouter API key.
    model : str
        Model identifier (e.g. "meta-llama/llama-3.1-8b-instruct").
    temperature : float
        Sampling temperature.
    max_tokens : int
        Maximum tokens per response.
    timeout : int
        HTTP timeout in seconds.
    max_retries : int
        Number of retry attempts on failure.
    retry_delay : float
        Base delay between retries (exponential backoff on 429).
    rate_limit_delay : float
        Delay between successive calls.
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-3.1-8b-instruct",
        temperature: float = 0.7,
        max_tokens: int = 800,
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        rate_limit_delay: float = 0.5,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit_delay = rate_limit_delay
        self.stats = CallStats()

    def call(self, messages: list[dict], json_mode: bool = True) -> tuple[str, bool]:
        """Make a multi-turn API call.

        Parameters
        ----------
        messages : list[dict]
            OpenAI-format messages: [{"role": ..., "content": ...}, ...]
        json_mode : bool
            If True, request JSON output mode.

        Returns
        -------
        (response_text, success) tuple.
        """
        self.stats.total_calls += 1

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    usage = result.get("usage", {})
                    self.stats.total_tokens += usage.get("total_tokens", 0)
                    self.stats.successful_calls += 1
                    return content, True

                elif response.status_code == 429:
                    wait = self.retry_delay * (2 ** attempt)
                    print(f"  [RATE LIMIT] waiting {wait:.0f}s")
                    time.sleep(wait)
                    continue

                else:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    self.stats.failed_calls += 1
                    print(f"  [ERROR] HTTP {response.status_code}: {response.text[:200]}")
                    return "", False

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                self.stats.failed_calls += 1
                print("  [TIMEOUT]")
                return "", False

            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                self.stats.failed_calls += 1
                print(f"  [ERROR] {e}")
                return "", False

        self.stats.failed_calls += 1
        return "", False

    def call_single(self, system: str, user: str, json_mode: bool = True) -> tuple[str, bool]:
        """Convenience method for a single system+user call.

        Parameters
        ----------
        system : str
            System prompt.
        user : str
            User prompt.
        json_mode : bool
            If True, request JSON output mode.

        Returns
        -------
        (response_text, success) tuple.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.call(messages, json_mode=json_mode)

    def rate_limit_wait(self):
        """Wait between successive calls to respect rate limits."""
        if self.rate_limit_delay > 0:
            time.sleep(self.rate_limit_delay)


def _llm_json_repair(text: str) -> dict | None:
    """Last-resort: ask GPT-4o-mini to extract/repair JSON from malformed text."""
    import os
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        try:
            from forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    if not api_key:
        try:
            from archive.wargame_forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    if not api_key:
        return None

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Extract the JSON object from the following text. Return ONLY valid JSON, no other text."},
                    {"role": "user", "content": text[:4000]},
                ],
                "max_tokens": 2000,
                "temperature": 0,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            repaired = resp.json()["choices"][0]["message"]["content"].strip()
            return json.loads(repaired)
    except Exception:
        pass
    return None


def parse_json_response(text: str) -> dict | None:
    """Parse JSON from an LLM response, with fallback strategies.

    Tries:
    1. Direct JSON parse
    2. Extract from markdown code block
    3. Regex extraction (nested-JSON-aware: matches outermost braces)
    4. LLM repair via GPT-4o-mini (last resort)

    Returns
    -------
    Parsed dict, or None if all strategies fail.
    """
    if text is None:
        return None

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 2: markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: outermost braces (handles nested JSON)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4: LLM repair (cheap, last resort)
    repaired = _llm_json_repair(text)
    if repaired is not None:
        return repaired

    return None
