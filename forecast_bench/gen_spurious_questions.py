"""
Generate spurious (irrelevant) background contexts for all 100 ForecastBench questions.

For each question, uses GPT-4o-mini to generate a factual but completely irrelevant
background paragraph, then verifies no semantic overlap with the question topic.

Usage:
    python -m forecast_bench.gen_spurious_questions
    python -m forecast_bench.gen_spurious_questions --verify-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.questions import load_forecastbench_questions

OUTPUT_PATH = Path(__file__).parent / "spurious_conditioned_questions.json"

# Pool of maximally irrelevant topic domains to draw from
BACKGROUND_TOPICS = [
    "deep-sea hydrothermal vent biology",
    "medieval Scandinavian runestone inscriptions",
    "the history of Venetian glassblowing on Murano island",
    "competitive speed-cubing (Rubik's cube solving)",
    "the biochemistry of bioluminescence in deep-sea organisms",
    "the construction techniques of Roman aqueducts",
    "the migratory patterns of Arctic terns",
    "the fermentation chemistry of Korean kimchi",
    "the geology of Iceland's volcanic rift zones",
    "traditional Japanese lacquerware (urushi) craftsmanship",
    "the physics of auroral phenomena (northern lights)",
    "the history of Polynesian celestial navigation",
    "competitive pigeon racing in Belgium",
    "the acoustics of medieval Gothic cathedrals",
    "the botany of carnivorous pitcher plants (Nepenthes)",
    "the history of cuneiform writing in ancient Mesopotamia",
    "the metallurgy of Damascus steel production",
    "the ecology of mangrove forests in Southeast Asia",
    "the mathematics of origami fold patterns",
    "the history of lighthouse engineering on the Scottish coast",
    "the chemistry of natural indigo dye production",
    "the biomechanics of woodpecker skull shock absorption",
    "the archaeology of Nabataean water management at Petra",
    "the physics of sand dune formation in the Namib Desert",
    "the history of silk production along the ancient Silk Road",
    "the neuroscience of echolocation in bats",
    "competitive cheese rolling at Cooper's Hill, Gloucestershire",
    "the architecture of traditional Bhutanese dzong fortresses",
    "the oceanography of thermohaline circulation patterns",
    "the history of tuning systems in Baroque keyboard instruments",
    "the entomology of leafcutter ant agriculture",
    "the geology of New Zealand's geothermal systems",
    "the history of Persian carpet weaving techniques",
    "the physics of soap bubble formation and stability",
    "the marine biology of chambered nautilus shell growth",
    "the archaeology of Minoan palace complexes on Crete",
    "the history of Ethiopian coffee cultivation ceremonies",
    "the aerodynamics of peregrine falcon hunting dives",
    "the engineering of traditional Dutch windmill mechanisms",
    "the mycology of truffle symbiosis with oak tree roots",
    "the history of Hawaiian quilting traditions",
    "the crystallography of snowflake formation patterns",
    "the engineering of ancient Chinese crossbow trigger mechanisms",
    "the marine ecology of kelp forest ecosystems off California",
    "the history of Inuit snow goggles and UV protection",
    "the biochemistry of spider silk protein structure",
    "the geology of the Chicxulub impact crater in Yucatan",
    "the history of Aboriginal Australian boomerang aerodynamics",
    "the ecology of flamingo filter feeding in alkaline lakes",
    "the engineering of medieval trebuchet siege weapons",
    "the botany of baobab tree water storage adaptations",
    "the history of Tibetan sand mandala construction",
    "the acoustics of whale song frequency modulation",
    "the archaeology of Roman mosaic tessellation techniques",
    "the physics of lava lamp convection currents",
    "the history of Venetian carnival mask traditions",
    "the marine biology of sea cucumber respiratory systems",
    "the engineering of Inca suspension bridge construction",
    "the ecology of coral spawning synchronization events",
    "the history of Turkish shadow puppet theater (Karagöz)",
    "the biochemistry of firefly luciferin light production",
    "the geology of cave stalactite growth rates",
    "the history of Scottish Highland Games stone put events",
    "the physics of gyroscopic precession in spinning tops",
    "the archaeology of Angkor Wat hydraulic engineering",
    "the botany of Venus flytrap trigger hair mechanisms",
    "the history of Fabergé egg jeweled mechanism craftsmanship",
    "the marine biology of giant squid deep-sea adaptations",
    "the engineering of Swiss mechanical watchmaking escapements",
    "the ecology of desert tortoise burrow microhabitats",
    "the history of Maori ta moko facial tattoo traditions",
    "the physics of acoustic levitation experiments",
    "the archaeology of Göbekli Tepe megalithic construction",
    "the chemistry of volcanic glass (obsidian) formation",
    "the history of competitive kite fighting in Afghanistan",
    "the marine ecology of sea otter kelp forest keystone effects",
    "the engineering of ancient Egyptian obelisk quarrying and transport",
    "the botany of giant sequoia fire adaptation strategies",
    "the history of Mongolian throat singing (khoomei) harmonics",
    "the physics of murmuration patterns in starling flocks",
    "the archaeology of Pompeii fresco painting techniques",
    "the ecology of axolotl regeneration in Lake Xochimilco",
    "the history of traditional Samoan tatau ceremonies",
    "the crystallography of bismuth crystal staircase structures",
    "the engineering of Japanese pagoda earthquake resistance",
    "the marine biology of mantis shrimp polarized vision",
    "the history of Flemish oil painting glazing techniques",
    "the ecology of pistol shrimp cavitation bubble generation",
    "the archaeology of Stonehenge bluestone transport theories",
    "the physics of Prince Rupert's drop glass tempering",
    "the botany of rafflesia parasitic flowering mechanisms",
    "the history of Georgian polyphonic singing traditions",
    "the engineering of Viking longship clinker construction",
    "the marine ecology of Christmas Island red crab migration",
    "the chemistry of ancient Roman concrete seawater resistance",
    "the ecology of bombardier beetle chemical defense sprays",
    "the history of Azerbaijani mugham modal music systems",
    "the physics of ball lightning formation hypotheses",
    "the archaeology of Moai statue transportation on Easter Island",
    "the botany of strangler fig germination and growth strategies",
]

GENERATE_SYSTEM = """You generate factual background paragraphs about specific topics. The paragraph must:
1. Be 3-4 sentences with specific numerical facts and measurements
2. Be entirely about the assigned topic
3. Contain NO connection whatsoever to the forecasting question shown
4. Sound like an encyclopedia excerpt

Respond with ONLY valid JSON:
{"background": "the paragraph text", "keywords": ["keyword1", "keyword2", ...]}

The keywords should be 5-8 distinctive terms from your paragraph that could be used to detect if a model incorporates this background into its reasoning."""

VERIFY_SYSTEM = """You are checking whether a background paragraph could be considered relevant to a forecasting question. Be strict: flag ANY possible connection, even indirect or metaphorical.

Consider these types of relevance:
- Direct topical overlap (same domain, entities, or concepts)
- Indirect relevance (background topic could plausibly inform the forecast)
- Metaphorical or analogical connection a model might exploit
- Geographic overlap (same country/region mentioned in both)
- Temporal overlap (same time period referenced)

Respond with ONLY valid JSON:
{"relevant": true or false, "reason": "explanation of any connection found"}"""


def _get_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
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
    return api_key


def _extract_question_keywords(question: str) -> list[str]:
    """Extract rough topic keywords from a question for topic avoidance."""
    import re
    # Remove common forecasting boilerplate
    q = question.lower()
    for phrase in ["will ", "what is the probability that ", "according to wikipedia, ",
                   "by 2025", "by 2026", "before 2025", "before 2026",
                   "2025-12-28", "2025-12-21", "higher than", "increased by",
                   "compared to", "more than"]:
        q = q.replace(phrase, " ")
    # Extract meaningful words (>3 chars)
    words = re.findall(r'[a-z]{4,}', q)
    return list(set(words))


def generate_backgrounds(args):
    """Generate irrelevant backgrounds for all 100 questions."""
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    # Load 116 high-complexity questions
    hc_path = Path(__file__).parent / "high_complexity_questions.json"
    questions = json.loads(hc_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(questions)} high-complexity questions")

    # Load existing if resuming
    existing = {}
    if args.resume and OUTPUT_PATH.exists():
        existing_list = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        existing = {e["id"]: e for e in existing_list}
        print(f"Loaded {len(existing)} existing entries")

    client = LLMClient(
        api_key=api_key,
        model="openai/gpt-4o-mini",
        temperature=0.7,
        max_tokens=600,
    )

    verify_client = LLMClient(
        api_key=api_key,
        model="openai/gpt-4o-mini",
        temperature=0.0,
        max_tokens=300,
    )

    import random
    rng = random.Random(42)
    # Shuffle topics so assignment is random but reproducible
    topics = list(BACKGROUND_TOPICS)
    rng.shuffle(topics)

    results = []
    for i, q in enumerate(questions):
        qid = q["id"]

        # Skip if already done
        if qid in existing:
            results.append(existing[qid])
            print(f"  [{i+1}/{len(questions)}] {qid[:30]} -- cached")
            continue

        question_text = q["question"]
        # Pick a topic that cycles through the pool
        topic = topics[i % len(topics)]

        print(f"  [{i+1}/{len(questions)}] {qid[:30]}...", end=" ")

        # Generate background
        gen_prompt = (
            f"TOPIC TO WRITE ABOUT: {topic}\n\n"
            f"FORECASTING QUESTION (write about the topic above, NOT about this question): "
            f"{question_text}"
        )

        max_attempts = 3
        background = None
        keywords = []

        for attempt in range(max_attempts):
            text, ok = client.call_single(GENERATE_SYSTEM, gen_prompt)
            client.rate_limit_wait()
            if not ok:
                continue

            data = parse_json_response(text)
            if data and "background" in data:
                candidate_bg = data["background"]
                keywords = data.get("keywords", [])

                # Verify irrelevance
                verify_prompt = (
                    f"FORECASTING QUESTION:\n{question_text}\n\n"
                    f"BACKGROUND PARAGRAPH:\n{candidate_bg}"
                )
                vtext, vok = verify_client.call_single(VERIFY_SYSTEM, verify_prompt)
                verify_client.rate_limit_wait()

                if vok:
                    vdata = parse_json_response(vtext)
                    if vdata and not vdata.get("relevant", True):
                        background = candidate_bg
                        break
                    else:
                        reason = vdata.get("reason", "unknown") if vdata else "parse fail"
                        print(f"[relevance detected: {reason[:50]}] ", end="")
                        # Try a different topic
                        topic = topics[(i + attempt + 1) % len(topics)]
                        gen_prompt = (
                            f"TOPIC TO WRITE ABOUT: {topic}\n\n"
                            f"FORECASTING QUESTION (write about the topic above, NOT about this question): "
                            f"{question_text}"
                        )
                else:
                    background = candidate_bg  # fallback: use it
                    break

        if background is None:
            print("FAILED")
            continue

        entry = {
            "id": qid,
            "original": question_text,
            "background": background,
            "spurious_keywords": keywords,
            "assigned_topic": topic,
        }
        results.append(entry)
        print(f"OK ({topic[:40]})")

    # Sort by ID for consistency
    results.sort(key=lambda x: x["id"])

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(results)} questions to {OUTPUT_PATH}")
    print(f"Gen stats: {json.dumps(client.stats.__dict__)}")
    print(f"Verify stats: {json.dumps(verify_client.stats.__dict__)}")


def verify_only(args):
    """Re-verify all existing backgrounds for relevance."""
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    entries = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    print(f"Verifying {len(entries)} entries")

    verify_client = LLMClient(
        api_key=api_key,
        model="openai/gpt-4o-mini",
        temperature=0.0,
        max_tokens=300,
    )

    flagged = []
    for i, e in enumerate(entries):
        verify_prompt = (
            f"FORECASTING QUESTION:\n{e['original']}\n\n"
            f"BACKGROUND PARAGRAPH:\n{e['background']}"
        )
        text, ok = verify_client.call_single(VERIFY_SYSTEM, verify_prompt)
        verify_client.rate_limit_wait()

        if ok:
            data = parse_json_response(text)
            if data and data.get("relevant", False):
                flagged.append((e["id"], data.get("reason", "")))
                print(f"  FLAGGED: {e['id'][:30]} -- {data.get('reason', '')[:60]}")

    print(f"\nFlagged {len(flagged)}/{len(entries)} as potentially relevant")
    for qid, reason in flagged:
        print(f"  {qid[:30]}: {reason[:80]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if args.verify_only:
        verify_only(args)
    else:
        generate_backgrounds(args)


if __name__ == "__main__":
    main()
