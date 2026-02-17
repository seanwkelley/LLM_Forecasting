"""
Configuration for LLM Forecasting System

Contains API keys, model selection, and experimental parameters.
"""

import os
from pathlib import Path

# =============================================================================
# API CONFIGURATION
# =============================================================================

# OpenRouter API key - loaded from environment variable
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "") or "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# =============================================================================
# MODEL SELECTION
# =============================================================================

# Primary model for forecasting
DEFAULT_MODEL = "deepseek/deepseek-v3.2"

# Alternative models (for testing/comparison)
ALTERNATIVE_MODELS = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "claude": "anthropic/claude-sonnet-4",
    "gpt4": "openai/gpt-4-turbo",
    "gemini": "google/gemini-2.0-flash-exp:free"
}

# =============================================================================
# EXPERIMENTAL PARAMETERS
# =============================================================================

# Number of agents per condition
# Generic conditions (low variance, smaller N)
N_AGENTS_GENERIC_INDEPENDENT = 10      # Condition 1
N_AGENTS_GENERIC_DEBATE = 50           # Condition 2 (10 groups × 5)
N_GROUPS_GENERIC_DEBATE = 10

# Personalized conditions (high variance expected, larger N)
N_AGENTS_PERSONALIZED_INDEPENDENT = 100  # Condition 3
N_AGENTS_PERSONALIZED_DEBATE = 100       # Condition 4 (20 groups × 5)
N_GROUPS_PERSONALIZED_DEBATE = 20

# Debate configuration
DEBATE_GROUP_SIZE = 5       # Agents per debate group
N_DEBATE_ROUNDS = 2         # Deliberation rounds (1=independent, 2=revision)

# Persona sampling
N_PERSONA_SAMPLE = 100      # Number of personas to sample from 500-persona pool
PERSONA_POOL_SIZE = 500     # Total personas available
RANDOM_SEED = 42            # For reproducible persona sampling

# =============================================================================
# FILE PATHS
# =============================================================================

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Prompts
PROMPTS_DIR = OUTPUTS_DIR / "human_forecasting" / "TRUE"

# Forecasting outputs
FORECASTING_RESULTS_DIR = OUTPUTS_DIR / "forecasting_results"

# Personas
PERSONA_FILE = PROJECT_ROOT / "forecasting" / "persona_profiles.json"

# =============================================================================
# OUTPUT FORMATS
# =============================================================================

# Forecast response format
FORECAST_FIELDS = [
    "period",
    "agent_id",
    "persona_id",  # null for generic agents
    "probability",
    "confidence",
    "reasoning",
    "timestamp"
]

# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

# Generic system prompt (for Conditions 1 and 2)
GENERIC_SYSTEM_PROMPT = """You are an expert geopolitical analyst with broad knowledge of international relations, military strategy, economic factors, and statistical reasoning.

Your task is to forecast the probability of specific geopolitical outcomes based on intelligence briefings. Provide probability estimates as decimals (0.0 to 1.0), confidence levels (low/medium/high), and brief reasoning for your assessments.

Be analytical, consider multiple perspectives, and avoid extreme predictions without strong evidence. Focus on base rates, precedents, and the balance of observable factors."""

# Persona system prompt prefix (for Conditions 3 and 4)
# Will be combined with persona.to_natural_language()
PERSONA_SYSTEM_PROMPT_PREFIX = """You are a geopolitical forecasting analyst participating in a forecasting exercise.

"""

PERSONA_SYSTEM_PROMPT_SUFFIX = """

Your task is to forecast the probability of specific geopolitical outcomes based on intelligence briefings. Consider your own expertise, cognitive strengths, and analytical style when forming your assessment. Provide probability estimates as decimals (0.0 to 1.0), confidence levels (low/medium/high), and brief reasoning."""

# =============================================================================
# API PARAMETERS
# =============================================================================

# Default temperature for forecasting
TEMPERATURE = 0.7

# Max tokens for responses
MAX_TOKENS = 500

# Timeout for API calls (seconds)
API_TIMEOUT = 60

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# =============================================================================
# VALIDATION
# =============================================================================

# Validate debate configuration
assert N_AGENTS_GENERIC_DEBATE == DEBATE_GROUP_SIZE * N_GROUPS_GENERIC_DEBATE, \
    f"N_AGENTS_GENERIC_DEBATE ({N_AGENTS_GENERIC_DEBATE}) must equal DEBATE_GROUP_SIZE ({DEBATE_GROUP_SIZE}) × N_GROUPS_GENERIC_DEBATE ({N_GROUPS_GENERIC_DEBATE})"

assert N_AGENTS_PERSONALIZED_DEBATE == DEBATE_GROUP_SIZE * N_GROUPS_PERSONALIZED_DEBATE, \
    f"N_AGENTS_PERSONALIZED_DEBATE ({N_AGENTS_PERSONALIZED_DEBATE}) must equal DEBATE_GROUP_SIZE ({DEBATE_GROUP_SIZE}) × N_GROUPS_PERSONALIZED_DEBATE ({N_GROUPS_PERSONALIZED_DEBATE})"

assert N_AGENTS_PERSONALIZED_INDEPENDENT <= PERSONA_POOL_SIZE, \
    f"Cannot sample {N_AGENTS_PERSONALIZED_INDEPENDENT} personas from pool of {PERSONA_POOL_SIZE}"

assert N_AGENTS_PERSONALIZED_DEBATE <= PERSONA_POOL_SIZE, \
    f"Cannot sample {N_AGENTS_PERSONALIZED_DEBATE} personas from pool of {PERSONA_POOL_SIZE}"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_model_name(model_alias: str = None) -> str:
    """
    Get full model name from alias or return default

    Args:
        model_alias: Short name like "llama", "claude", or None for default

    Returns:
        Full model name for API call
    """
    if model_alias is None:
        return DEFAULT_MODEL
    return ALTERNATIVE_MODELS.get(model_alias, DEFAULT_MODEL)


def get_output_dir(condition_name: str) -> Path:
    """
    Get output directory for a specific condition

    Args:
        condition_name: e.g., "condition_1_generic_independent"

    Returns:
        Path to output directory (created if doesn't exist)
    """
    output_dir = FORECASTING_RESULTS_DIR / condition_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


if __name__ == "__main__":
    # Test configuration
    print("=" * 80)
    print("CONFIGURATION TEST")
    print("=" * 80)
    print(f"Default model: {DEFAULT_MODEL}")
    print()
    print("GENERIC CONDITIONS:")
    print(f"  Condition 1 (Independent): N={N_AGENTS_GENERIC_INDEPENDENT}")
    print(f"  Condition 2 (Debate): N={N_AGENTS_GENERIC_DEBATE} ({N_GROUPS_GENERIC_DEBATE} groups × {DEBATE_GROUP_SIZE})")
    print()
    print("PERSONALIZED CONDITIONS:")
    print(f"  Condition 3 (Independent): N={N_AGENTS_PERSONALIZED_INDEPENDENT}")
    print(f"  Condition 4 (Debate): N={N_AGENTS_PERSONALIZED_DEBATE} ({N_GROUPS_PERSONALIZED_DEBATE} groups × {DEBATE_GROUP_SIZE})")
    print()
    print(f"Persona pool: {PERSONA_POOL_SIZE}")
    print(f"Prompts directory: {PROMPTS_DIR}")
    print(f"Results directory: {FORECASTING_RESULTS_DIR}")
    print("=" * 80)
