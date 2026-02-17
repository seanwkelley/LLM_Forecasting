"""
Information Sharding for Multi-Agent Forecasting

Randomly samples portions of context to create information asymmetry across agents.
Tests whether ensemble can reconstruct full picture from partial views.
"""

import re
import random
from typing import List, Tuple


def _is_separator_line(line: str) -> bool:
    """Check if a line is a visual separator (===, ---, ***, etc.)."""
    stripped = line.strip()
    if not stripped:
        return True
    # Lines made entirely of separator characters
    if re.match(r'^[=\-_*~━─]+$', stripped):
        return True
    return False


def _split_prose_into_sentences(text: str) -> List[str]:
    """Split a prose paragraph into sentences using punctuation boundaries."""
    # Split on period, exclamation, or question mark followed by space/newline
    # But NOT on decimal numbers (e.g., 85.0) or abbreviations (e.g., U.S.)
    sentences = re.split(r'([.!?](?:\s+|\n+|$))', text)

    result = []
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i] + sentences[i + 1]
        sentence = sentence.strip()
        if sentence:
            result.append(sentence)

    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())

    return result


def _is_structured_line(line: str) -> bool:
    """Check if a line is structured data (bullet point, numbered item, key:value)."""
    stripped = line.strip()
    # Bullet points: - item, * item, bullet char
    if re.match(r'^[-*\u2022\u2023\u25E6]\s', stripped):
        return True
    # Numbered items: 1. item, 2) item
    if re.match(r'^\d+[.)]\s', stripped):
        return True
    # Key: value pairs (e.g., "Territory Remaining: 95.0%")
    if re.match(r'^[A-Z][\w\s]+:', stripped):
        return True
    return False


def split_into_chunks(text: str) -> List[str]:
    """
    Split text into atomic information chunks using a hybrid approach.

    For structured data (bullet points, numbered lists, key:value):
        Split on newlines - each line is one chunk.
    For prose paragraphs:
        Split on sentence boundaries.

    Filters out empty lines and visual separators (===, ---).
    """
    lines = text.split('\n')
    chunks = []
    prose_buffer = []

    def flush_prose():
        """Process accumulated prose lines as a paragraph."""
        if prose_buffer:
            paragraph = ' '.join(prose_buffer)
            sentences = _split_prose_into_sentences(paragraph)
            chunks.extend(sentences)
            prose_buffer.clear()

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and separators
        if _is_separator_line(line):
            flush_prose()
            continue

        # Structured lines get their own chunk
        if _is_structured_line(stripped):
            flush_prose()
            chunks.append(stripped)
        # Section headers (ALL CAPS or short lines without punctuation)
        elif re.match(r'^[A-Z][A-Z\s\d():/]+$', stripped) and len(stripped) < 80:
            flush_prose()
            chunks.append(stripped)
        else:
            # Accumulate prose for sentence splitting
            prose_buffer.append(stripped)

    flush_prose()
    return chunks


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into atomic information chunks.

    Uses hybrid approach: line-based for structured data,
    sentence-based for prose paragraphs.
    """
    return split_into_chunks(text)


def extract_sections(prompt: str) -> Tuple[str, str, str]:
    """
    Extract prompt into three sections:
    1. Header/Instructions (keep always)
    2. Context (state, events, actions - shard this)
    3. Output format/Footer (keep always)

    Returns:
        (header, context, footer)
    """
    # Find key markers
    # Typically prompts have:
    # - Opening instruction (header)
    # - Context section starting with a situation marker
    # - Footer starting with task/output instructions

    lines = prompt.split('\n')

    header_end = 0
    context_start = 0
    context_end = len(lines)
    footer_start = len(lines)
    found_context = False

    context_markers = ['STRATEGIC SITUATION', 'INITIAL SITUATION', 'SITUATION UPDATE', 'SITUATION REPORT']
    footer_markers = ['YOUR FORECASTING TASK', 'OUTPUT FORMAT', 'GUIDANCE', 'CRITICAL INSTRUCTIONS']

    for i, line in enumerate(lines):
        # Context section: match FIRST occurrence only
        if not found_context and any(marker in line for marker in context_markers):
            context_start = i
            header_end = i
            found_context = True

        # Footer: match first occurrence after context
        if found_context and any(marker in line for marker in footer_markers):
            context_end = i
            footer_start = i
            break

    header = '\n'.join(lines[:header_end])
    context = '\n'.join(lines[context_start:context_end])
    footer = '\n'.join(lines[footer_start:])

    return header, context, footer


def shard_information(prompt: str, information_fraction: float, seed: int = None) -> str:
    """
    Randomly sample a fraction of information from the prompt.

    Keeps header and footer intact, only shards the middle context section.

    Args:
        prompt: Full prompt text
        information_fraction: Fraction of context to keep (0.0 to 1.0)
        seed: Random seed for reproducibility

    Returns:
        Sharded prompt with partial information
    """
    if information_fraction >= 0.99:
        return prompt  # Near-full information, no sharding needed

    if information_fraction <= 0.0:
        raise ValueError("information_fraction must be > 0.0")

    # Set random seed if provided
    if seed is not None:
        random.seed(seed)

    # Extract sections
    header, context, footer = extract_sections(prompt)

    # Split context into sentences
    sentences = split_into_sentences(context)

    if not sentences:
        return prompt  # No context to shard

    # Calculate how many sentences to keep
    n_keep = max(1, int(len(sentences) * information_fraction))

    # Randomly sample sentences (preserve order)
    indices = sorted(random.sample(range(len(sentences)), n_keep))
    sampled_sentences = [sentences[i] for i in indices]

    # Reconstruct prompt
    sharded_context = '\n'.join(sampled_sentences)
    sharded_prompt = f"{header}\n\n{sharded_context}\n\n{footer}"

    return sharded_prompt


def create_information_distribution(n_agents: int, min_frac: float = 0.05, max_frac: float = 0.95, seed: int = None) -> List[float]:
    """
    Create information level distribution for N agents.

    Each agent receives a random fraction of information drawn from
    Uniform(min_frac, max_frac). No agent gets all information (baseline)
    or near-zero information (useless).

    Args:
        n_agents: Total number of agents
        min_frac: Minimum information fraction (default 0.05 = 5%)
        max_frac: Maximum information fraction (default 0.95 = 95%)
        seed: Random seed for reproducibility

    Returns:
        List of information fractions, one per agent
    """
    rng = random.Random(seed)
    distribution = [rng.uniform(min_frac, max_frac) for _ in range(n_agents)]
    return distribution


def create_uniform_information_distribution(n_agents: int, fraction: float) -> List[float]:
    """
    Create a uniform information distribution where all agents get the same fraction.

    Each agent sees a different random subset (via per-agent seed), but the
    proportion of information is held constant. This isolates the effect of
    subset diversity from quantity variation.

    Args:
        n_agents: Total number of agents
        fraction: Information fraction for all agents (0.0-1.0)

    Returns:
        List of identical information fractions, one per agent
    """
    if not (0.0 < fraction <= 1.0):
        raise ValueError(f"fraction must be in (0.0, 1.0], got {fraction}")
    return [fraction] * n_agents


def analyze_sharding(original: str, sharded: str) -> dict:
    """
    Analyze how much information was retained in sharded prompt.

    Returns:
        Statistics about information retention
    """
    orig_sentences = split_into_sentences(original)
    shard_sentences = split_into_sentences(sharded)

    return {
        'original_sentences': len(orig_sentences),
        'sharded_sentences': len(shard_sentences),
        'retention_rate': len(shard_sentences) / len(orig_sentences) if orig_sentences else 0.0,
        'original_chars': len(original),
        'sharded_chars': len(sharded),
        'char_retention_rate': len(sharded) / len(original) if original else 0.0
    }


if __name__ == "__main__":
    # Test sharding
    print("Testing information sharding...\n")

    test_prompt = """You are a strategic analyst.

STRATEGIC SITUATION (Period 1 Final State)

TETHYS POSITION:
- Territory Remaining: 95.0%
- Military Balance: -0.05
- GDP: $29.5B (started at $30B)
- International Support: 55%
- Crisis Level: 6.0/10

NOVARIS POSITION:
- Territory Controlled: 5.0%
- GDP: $98.0B (started at $100B)
- Sanctions Level: 15%

EXTERNAL EVENTS THIS PERIOD
1. Battlefield: Initial skirmishes along border
2. Economic: International sanctions imposed on Novaris
3. Diplomatic: Meridian reaffirms security commitment

ACTIONS TAKEN THIS PERIOD
NOVARIS ACTIONS:
- military_buildup
- naval_deployment
- strategic_stockpiling

TETHYS ACTIONS:
- show_of_force
- coalition_building
- humanitarian_aid

YOUR FORECASTING TASK

Predict which actions Tethys will take in Period 2.

OUTPUT FORMAT (JSON):
{
  "predicted_actions": ["action1", "action2", ...],
  "rationale": "explanation"
}

IMPORTANT: Output ONLY valid JSON.
"""

    # Show how chunks are split
    _, context, _ = extract_sections(test_prompt)
    chunks = split_into_chunks(context)
    print(f"Context split into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        label = "STRUCT" if _is_structured_line(chunk.strip()) else "PROSE "
        print(f"  [{i:2d}] {label}: {chunk[:80]}{'...' if len(chunk) > 80 else ''}")

    print(f"\nOriginal prompt:")
    print(f"  Length: {len(test_prompt)} chars")
    print(f"  Chunks: {len(split_into_sentences(test_prompt))}")

    # Test different information levels
    for frac in [0.25, 0.50, 0.75, 1.00]:
        sharded = shard_information(test_prompt, frac, seed=42)
        stats = analyze_sharding(test_prompt, sharded)

        print(f"\nSharding at {frac*100:.0f}%:")
        print(f"  Retained: {stats['sharded_sentences']}/{stats['original_sentences']} chunks ({stats['retention_rate']*100:.0f}%)")
        print(f"  Chars: {stats['sharded_chars']}/{stats['original_chars']} ({stats['char_retention_rate']*100:.0f}%)")

    # Test with prose-heavy text to show sentence splitting still works
    print(f"\n\n--- Prose splitting test ---")
    prose_text = """The crisis is escalating across multiple domains. Cyber attacks are being
exchanged daily. Economic warfare is beginning with trade restrictions. Intelligence
suggests covert operations are underway on both sides. Both sides have established
defensive positions. Military analysts assess the situation as highly volatile."""
    prose_chunks = split_into_chunks(prose_text)
    print(f"Prose split into {len(prose_chunks)} sentences:")
    for i, chunk in enumerate(prose_chunks):
        print(f"  [{i}]: {chunk[:80]}{'...' if len(chunk) > 80 else ''}")

    # Test distribution
    print(f"\n\nInformation distribution for N=10 (random, 5%-95%):")
    dist = create_information_distribution(10, seed=42)
    for i, frac in enumerate(dist):
        print(f"  Agent {i}: {frac*100:.1f}%")
    print(f"  Min: {min(dist)*100:.1f}%, Max: {max(dist)*100:.1f}%, Mean: {sum(dist)/len(dist)*100:.1f}%")

    print(f"\nInformation distribution for N=100 (random, 5%-95%):")
    dist = create_information_distribution(100, seed=42)
    print(f"  Min: {min(dist)*100:.1f}%, Max: {max(dist)*100:.1f}%, Mean: {sum(dist)/len(dist)*100:.1f}%")
    bins = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    for lo, hi in bins:
        count = sum(1 for f in dist if lo/100 <= f < hi/100)
        print(f"  {lo}-{hi}%: {count} agents")

    print("\n[OK] Information sharding test complete!")
