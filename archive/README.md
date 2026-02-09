# Archive Directory

**This directory contains deprecated files preserved for historical reference.**

## ⚠️ Important Notice

**DO NOT use these files for active development.**

These files represent earlier versions of the simulation system that have been superseded by current implementations in the main directory.

---

## Quick Reference

### What's Archived Here

- **src/** - Deprecated source code (action_space.R, agent_system.R, simulation.R)
- **run_scripts/** - Old entry points (run_simulation.R, run_enhanced_simulation.R)
- **documentation/** - Outdated documentation files (15 files)

### Why Archived

The project evolved through three major versions:
1. **v1.0** - Basic 11-agent system
2. **v2.0** - Added cognitive framework (worldviews, deception)
3. **v3.0** - **CURRENT** - Full action execution with 49 concrete actions

Files in this archive represent v1.0 and v2.0 implementations.

---

## Current Active System

**To run the current simulation:**
```bash
cd ..
Rscript run_simulation_with_actions.R
```

**For current documentation:**
- `../CURRENT_SYSTEM_GUIDE.md` - Authoritative guide
- `../ACTION_EXECUTION_GUIDE.md` - Complete action reference
- `../README.md` - Project overview

---

## What's In This Archive

### Source Code (3 files)
- `src/action_space.R` - 27-action taxonomy (replaced by enhanced_action_space.R)
- `src/agent_system.R` - Basic agents (replaced by integrated_agent_system.R)
- `src/simulation.R` - No-action loop (replaced by simulation_with_actions.R)

### Run Scripts (2 files)
- `run_scripts/run_simulation.R` - v1.0 basic mode
- `run_scripts/run_enhanced_simulation.R` - v2.0 intermediate (cognitive only, no actions)

### Documentation (15 files)
- Action system: ACTION_SPACE_GUIDE.md, ACTIONS_IMPLEMENTED.md
- Cognitive framework: ENHANCED_FEATURES_GUIDE.md, RATIONALITY_*.md, INTEGRATION_EXAMPLE.md
- Forecasting: FORECASTING_*.md (3 files)
- General: PROJECT_SUMMARY.md, SYSTEM_SUMMARY.md, ORIGINAL_FEATURES_PRESERVED.md, QUICKSTART.md
- Bug tracking: CHANGES.md, BUGFIX_*.md, FIXED_ISSUES.md, TROUBLESHOOTING.md

---

## When to Use These Files

### Valid Use Cases
✅ Research comparison (v1.0 vs v2.0 vs v3.0)
✅ Understanding project evolution
✅ Reproducing earlier results
✅ Ablation studies (testing without certain features)

### Invalid Use Cases
❌ Active development
❌ New simulations
❌ Documentation reference (use current docs instead)

---

## Full Index

**See `../ARCHIVE_INDEX.md` for complete documentation of:**
- What each file is
- Why it was archived
- What replaced it
- When to use it

---

**Last Updated:** January 2026
**Archive Created:** January 2026
