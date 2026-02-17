"""
Base Forecaster Class - Core LLM API interaction and response parsing

Handles OpenRouter API calls, response parsing, and retry logic.
"""

import json
import time
import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import requests

from forecasting.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    DEFAULT_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    API_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY
)


@dataclass
class ForecastResponse:
    """Structured forecast response from LLM"""
    probability: float          # 0.0 to 1.0
    confidence: str             # "low", "medium", or "high"
    reasoning: str              # Brief explanation
    raw_response: str           # Full LLM response
    timestamp: str              # ISO format timestamp
    success: bool = True        # Whether parsing succeeded
    error: Optional[str] = None # Error message if failed


class BaseLLMForecaster:
    """
    Base class for LLM-based forecasters

    Handles API calls, response parsing, and error handling.
    Can be subclassed for different forecasting conditions.
    """

    def __init__(
        self,
        model: str = None,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
        system_prompt: str = None
    ):
        """
        Initialize forecaster

        Args:
            model: Model name (default from config)
            temperature: Sampling temperature
            max_tokens: Max response tokens
            system_prompt: System prompt (can be overridden per call)
        """
        self.model = model or DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.default_system_prompt = system_prompt

        # API configuration
        self.api_key = OPENROUTER_API_KEY
        self.base_url = OPENROUTER_BASE_URL
        self.timeout = API_TIMEOUT

        # Statistics
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0

    def call_llm(
        self,
        user_prompt: str,
        system_prompt: str = None,
        response_format: str = "text"
    ) -> Tuple[str, bool]:
        """
        Call LLM API with retry logic

        Args:
            user_prompt: User message
            system_prompt: System prompt (overrides default)
            response_format: "text" or "json" (for structured output)

        Returns:
            Tuple of (response_text, success)
        """
        self.total_calls += 1

        # Use provided system prompt or default
        sys_prompt = system_prompt or self.default_system_prompt

        # Build messages
        messages = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_prompt})

        # Build request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        # Add response format if JSON mode requested
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        # Retry loop
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )

                # Check for HTTP errors
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    self.successful_calls += 1
                    return content, True

                elif response.status_code == 429:  # Rate limit
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"[WARNING] Rate limit hit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    print(f"[ERROR] API call failed: {error_msg}")

                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        self.failed_calls += 1
                        return error_msg, False

            except requests.exceptions.Timeout:
                print(f"[ERROR] Request timeout (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    self.failed_calls += 1
                    return "Request timeout", False

            except Exception as e:
                print(f"[ERROR] API call exception: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    self.failed_calls += 1
                    return str(e), False

        self.failed_calls += 1
        return "Max retries exceeded", False

    def parse_forecast_response(self, response_text: str) -> ForecastResponse:
        """
        Parse LLM response to extract probability, confidence, and reasoning

        Handles multiple response formats:
        - JSON format: {"probability": 0.45, "confidence": "medium", ...}
        - Natural language: "probability: 45%", "confidence: medium"

        Args:
            response_text: Raw LLM response

        Returns:
            ForecastResponse object
        """
        timestamp = datetime.now().isoformat()

        # Try JSON parsing first
        try:
            data = json.loads(response_text)
            probability = self._extract_probability_value(data.get("probability"))
            confidence = self._normalize_confidence(data.get("confidence", "medium"))
            reasoning = data.get("reasoning", data.get("rationale", ""))

            if probability is not None:
                return ForecastResponse(
                    probability=probability,
                    confidence=confidence,
                    reasoning=reasoning,
                    raw_response=response_text,
                    timestamp=timestamp,
                    success=True
                )
        except json.JSONDecodeError:
            pass  # Fall through to regex parsing

        # Regex parsing for natural language responses
        probability = self._extract_probability_from_text(response_text)
        confidence = self._extract_confidence_from_text(response_text)
        reasoning = self._extract_reasoning_from_text(response_text)

        if probability is not None:
            return ForecastResponse(
                probability=probability,
                confidence=confidence,
                reasoning=reasoning,
                raw_response=response_text,
                timestamp=timestamp,
                success=True
            )

        # Parsing failed
        return ForecastResponse(
            probability=0.5,  # Default to 50% if parsing fails
            confidence="low",
            reasoning="Failed to parse response",
            raw_response=response_text,
            timestamp=timestamp,
            success=False,
            error="Could not extract probability from response"
        )

    def _extract_probability_value(self, value) -> Optional[float]:
        """Convert various probability formats to float 0.0-1.0"""
        if value is None:
            return None

        # Handle string formats
        if isinstance(value, str):
            # Remove % sign
            value = value.replace('%', '').strip()
            try:
                value = float(value)
            except ValueError:
                return None

        # Convert to float
        value = float(value)

        # Normalize to 0.0-1.0 range
        if value > 1.0:
            value = value / 100.0

        # Clip to valid range
        value = max(0.0, min(1.0, value))

        return value

    def _extract_probability_from_text(self, text: str) -> Optional[float]:
        """Extract probability from natural language text"""

        # Pattern 1: "probability: 0.45" or "probability: 45%"
        patterns = [
            r'probability[:\s]+([0-9.]+)%?',
            r'estimate[:\s]+([0-9.]+)%?',
            r'([0-9.]+)%?\s*probability',
            r'([0-9]{1,3})%\s*chance',
            r'p\s*=\s*([0-9.]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_probability_value(match.group(1))

        return None

    def _normalize_confidence(self, confidence: str) -> str:
        """Normalize confidence level to low/medium/high"""
        if not confidence:
            return "medium"

        confidence = confidence.lower().strip()

        if any(word in confidence for word in ["low", "weak", "uncertain"]):
            return "low"
        elif any(word in confidence for word in ["high", "strong", "confident", "very"]):
            return "high"
        else:
            return "medium"

    def _extract_confidence_from_text(self, text: str) -> str:
        """Extract confidence level from text"""

        # Look for confidence indicators
        patterns = [
            r'confidence[:\s]+(low|medium|high)',
            r'confidence[:\s]+(weak|moderate|strong)',
            r'(low|medium|high)\s+confidence',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._normalize_confidence(match.group(1))

        return "medium"  # Default

    def _extract_reasoning_from_text(self, text: str) -> str:
        """Extract reasoning/rationale from text"""

        # Look for reasoning sections
        patterns = [
            r'reasoning[:\s]+(.+?)(?:\n\n|\Z)',
            r'rationale[:\s]+(.+?)(?:\n\n|\Z)',
            r'explanation[:\s]+(.+?)(?:\n\n|\Z)',
            r'because[:\s]+(.+?)(?:\n\n|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                reasoning = match.group(1).strip()
                # Limit length
                if len(reasoning) > 500:
                    reasoning = reasoning[:500] + "..."
                return reasoning

        # If no explicit reasoning section, take first paragraph
        paragraphs = text.split('\n\n')
        if paragraphs:
            reasoning = paragraphs[0].strip()
            if len(reasoning) > 500:
                reasoning = reasoning[:500] + "..."
            return reasoning

        return "No reasoning provided"

    def generate_forecast(
        self,
        prompt: str,
        system_prompt: str = None
    ) -> ForecastResponse:
        """
        Generate a forecast for a given prompt

        Args:
            prompt: Forecasting prompt (intelligence briefing)
            system_prompt: Optional system prompt override

        Returns:
            ForecastResponse object
        """

        # Add structured output instruction to prompt
        enhanced_prompt = prompt + "\n\n" + """
Please provide your forecast in the following format:

Probability: [your estimate as a decimal 0.0 to 1.0 or percentage 0-100%]
Confidence: [low/medium/high]
Reasoning: [2-3 sentences explaining your assessment]
"""

        # Call LLM
        response_text, success = self.call_llm(enhanced_prompt, system_prompt)

        if not success:
            return ForecastResponse(
                probability=0.5,
                confidence="low",
                reasoning="API call failed",
                raw_response=response_text,
                timestamp=datetime.now().isoformat(),
                success=False,
                error=response_text
            )

        # Parse response
        forecast = self.parse_forecast_response(response_text)

        return forecast

    def get_statistics(self) -> Dict[str, int]:
        """Get API call statistics"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": self.successful_calls / self.total_calls if self.total_calls > 0 else 0
        }


if __name__ == "__main__":
    """Test the base forecaster"""

    print("=" * 80)
    print("BASE FORECASTER TEST")
    print("=" * 80)
    print()

    # Initialize forecaster
    from forecasting.config import GENERIC_SYSTEM_PROMPT
    forecaster = BaseLLMForecaster(system_prompt=GENERIC_SYSTEM_PROMPT)

    print(f"Model: {forecaster.model}")
    print(f"Temperature: {forecaster.temperature}")
    print()

    # Test with a simple prompt
    test_prompt = """
Based on the following scenario, estimate the probability that a small nation's
government will collapse within 30 days:

- Major power has mobilized 40% of military forces on border
- Small nation has strong international support (70%)
- Economic sanctions at 50% level
- No territory has been seized yet
- Crisis level: 7/10

What is the probability of government collapse?
"""

    print("Testing forecast generation...")
    print("-" * 80)

    forecast = forecaster.generate_forecast(test_prompt)

    print(f"Success: {forecast.success}")
    print(f"Probability: {forecast.probability:.2f} ({forecast.probability*100:.1f}%)")
    print(f"Confidence: {forecast.confidence}")
    print(f"Reasoning: {forecast.reasoning}")
    print()

    if not forecast.success:
        print(f"Error: {forecast.error}")
        print(f"Raw response: {forecast.raw_response}")

    print()
    print("=" * 80)
    print("API STATISTICS")
    print("=" * 80)
    stats = forecaster.get_statistics()
    print(f"Total calls: {stats['total_calls']}")
    print(f"Successful: {stats['successful_calls']}")
    print(f"Failed: {stats['failed_calls']}")
    print(f"Success rate: {stats['success_rate']*100:.1f}%")
    print()
    print("[OK] Base forecaster test complete!")
