# START HERE - Quick Reference

**Version 3.8.5** | **Last Updated:** February 9, 2026

---

## To Run the Simulation

```bash
Rscript run_simulation_with_actions.R
```

That's it! This runs the **complete current system** with:
- **Multi-action proposal system** - Domain experts propose, president approves
- **XML-tagged prompts** - Structured prompts with 100% parsing success rate
- **Mixed LLM strategy** - Qwen (proposals), Claude Sonnet 4 (decisions), Gemini (aggregation)
- **Multi-domain warfare** - Naval, cyber, air, information warfare alongside traditional combat
- 11 agents with cognitive frameworks
- Pre-action coordination (agents discuss before deciding)
- 3-6 concurrent actions per major faction per period (vs single-action for external actors)
- 68 executable actions with effect resolution (cumulative, contradictions, synergies)
- Independent external actors (4 separate factions)
- Dynamic state tracking
- Full logging and analysis

---

## Documentation (Read in This Order)

### 1. Overview
**`README.md`** - Project overview, installation, basic usage

### 2. Multi-Action System Guide
**`docs/guides/MULTI_ACTION_SYSTEM_GUIDE.md`** - v3.8 multi-action system
- How domain experts propose actions
- Presidential approval process
- Effect resolution (cumulative, contradictions, synergies)
- Configuration options
- Expected impact on action diversity

### 3. Faction Capabilities
**`docs/guides/FACTION_OBJECTIVES.md`** - Strategic capabilities and goals
- Novaris (major power) capabilities and vulnerabilities
- Tethys (small power) offensive and defensive options
- External actor interests

### 4. Version Comparison
**`docs/guides/COMPREHENSIVE_COMPARISON.md`** - Performance across versions
- Action diversity metrics
- Version improvements

### 5. Archived Documentation
**`docs/archive/`** - Older system guides (reference only)
- ACTION_EXECUTION_GUIDE.md, CURRENT_SYSTEM_GUIDE.md, etc.

---

## File Structure

### Current Active Files
```
run_simulation_with_actions.R     ✅ Main entry point
config.R                           ✅ Configuration
src/integrated_agent_system.R     ✅ Cognitive framework
src/enhanced_action_space.R       ✅ 49-action system
src/simulation_with_actions.R     ✅ Main loop
[+ 7 other current source files]
```

### Documentation
```
CURRENT_SYSTEM_GUIDE.md           ✅ START HERE for system docs
ACTION_EXECUTION_GUIDE.md         ✅ Action reference
SCENARIO_CONFIGURATION.md         ✅ Scenario setup
README.md                          ✅ Overview
CLAUDE.md                          ✅ AI context
```

### Archive (Reference Only)
```
archive/                           📦 Deprecated files
├── src/                             3 old source files
├── run_scripts/                     2 old entry points
└── documentation/                   16 archived docs

ARCHIVE_INDEX.md                   📦 Complete archive documentation
```

---

## Common Tasks

### Change Scenario Intensity
Edit `config.R` line 17:
```r
SCENARIO_PRESET <- "high_intensity"  # Options: pre_invasion, low_intensity, medium_intensity, high_intensity, stalemate
```

### Analyze Results
```r
source("src/analysis.R")
analyze_simulation("outputs")
```

### Compare to Human Forecasts
```r
source("src/forecast_prompts.R")
state <- load_simulation_state("outputs")
human_probs <- c(0.25, 0.30, 0.35, ...)
comparison <- compare_forecasts(state, human_probs)
```

---

## What's New (v3.8.5)

**Latest Improvements (February 8-9, 2026):**
- ✅ **State threading** - Multi-action factions execute sequentially, preserving ~30 direct state mutations
- ✅ **Probabilistic external events** - All 15 event types have state handlers with 50-85% effectiveness
- ✅ **GDP effect application** - GDP changes correctly applied for multi-action factions
- ✅ **Symmetric thresholds** - Early termination at <5% or >95% collapse probability
- ✅ **Multi-target resolution** - Diplomatic actions to "Meridian,Aurelia" correctly parsed and receive alliance bonus
- ✅ **Mixed LLM strategy** - Qwen (proposals), Claude Sonnet 4 (decisions), Gemini (aggregation)

**v3.8.2 Improvements (February 2, 2026):**
- ✅ **Discussion memory** - Agents see previous period discussions with smart summarization
- ✅ **LLM message summarization** - Long messages (>150 chars) summarized via Gemini 2.5 Flash
- ✅ **Conversational continuity** - Agents can reference what they and colleagues previously said

**v3.8.1 Improvements (February 1, 2026):**
- ✅ **XML-tagged prompts** - Semantic structure with `<meeting_context>`, `<task>`, `<format_requirements>` tags
- ✅ **100% parsing success** - Zero failures across extensive testing with DeepSeek approval decisions
- ✅ **Multi-domain events** - Naval Incidents, Cyber Incidents, Air Incidents, Information Warfare
- ✅ **Enhanced actions** - Naval deployments, cyber_theft, share_intelligence, coalition_building, prisoner_exchange
- ✅ **Mixed LLM strategy** - Qwen (proposals), DeepSeek (decisions), Gemini (aggregation)
- ✅ **Robust formatting** - Strict requirements with examples, warnings, and explicit rules

**v3.8 Core Features:**
- ✅ **Domain experts propose** - Military, Intelligence, Diplomatic, Economic experts each propose 1-3 actions
- ✅ **Presidential approval** - Government leader reviews all proposals, approves/vetoes based on strategic judgment
- ✅ **Parallel execution** - Multiple approved actions execute concurrently (3-6 per faction)
- ✅ **Effect resolution** - Cumulative effects, diminishing returns, contradictions (peace + sabotage), synergies (intel + sabotage)
- ✅ **Cross-expertise** - Agents can recommend actions outside their domain

**Established Features:**
- ✅ 68 executable actions across 7 categories
- ✅ Pre-action coordination - agents discuss and debate before decisions
- ✅ Independent external actors - 4 separate factions with distinct interests
- ✅ Balanced scenario - Both powers have offensive and defensive capabilities
- ✅ Dynamic state tracking (GDP, military, territory, crisis)
- ✅ Probabilistic outcomes based on capabilities
- ✅ Cascading effects (combat attrition, economic costs)
- ✅ Configurable scenario presets

---

## Need Help?

1. **System overview:** Read `CURRENT_SYSTEM_GUIDE.md`
2. **Action details:** Read `ACTION_EXECUTION_GUIDE.md`
3. **Archived files:** See `ARCHIVE_INDEX.md`
4. **Cleanup details:** See `CLEANUP_SUMMARY.md`

---

## Quick Facts

**11 Agents:**
- 4 from Major Power (Novaris)
- 4 from Smaller Power (Tethys)
- 4 Independent External Actors (Meridian, Valkoria, Aurelia, International Org)

**68 Actions:**
- 14 Diplomatic
- 9 Intelligence
- 11 Economic
- 14 Military Posture
- 9 Covert Operations
- 6 Open Conflict
- 5 WMD

**Research Question:**
What is the probability that Tethys's government will be toppled?

---

**Ready to start? Run:** `Rscript run_simulation_with_actions.R`
