# v3.7 Scenario Rebalance - Implementation Summary

**Date:** 2026-01-31
**Objective:** Balance Novaris/Tethys power dynamics to enable diverse action usage across all categories

---

## Changes Made

### 1. Cross-Expertise Prompts (agent_decision.R)

**Lines 693-715:** Added "CRITICAL: CROSS-EXPERTISE DECISION MAKING" section
- "You can recommend ANY action that serves your faction's interests"
- "EXPERTISE DOES NOT MEAN CONSTRAINT"
- Examples: military→diplomacy, diplomat→covert ops, etc.
- "Recommend action that BEST SERVES your faction, regardless of job title"

**Lines 798-800:** Modified IMPORTANT RULES
- Changed: "Your role determines what actions are appropriate"
- To: "Your role provides EXPERTISE, not CONSTRAINTS"
- Added: "Consider actions outside your traditional domain"

### 2. Faction Objectives Rebalance (FACTION_OBJECTIVES.md)

**Novaris - Added Vulnerabilities:**
- Military mobilization only 40% complete (not finished)
- 30% export revenue flows through Tethys pipelines
- Cyber infrastructure exposed to attack
- 15% ethnic Tethyan population (internal opposition risk)
- Can achieve objectives through: military, cyber, economic, covert, or diplomatic means

**Tethys - Added Offensive Capabilities:**
- NOT helpless - precision strike capability
- Advanced cyber warfare units (can attack Novaris infrastructure)
- Economic leverage (pipeline shutdown = 30% Novaris revenue loss)
- Intelligence networks inside Novaris (ethnic Tethyan population)
- Can: preemptive strike, cyber attack, economic warfare, covert ops, rally allies

**Action Space Impact:**
- Novaris: 30+ viable actions across all categories
- Tethys: 30-35 viable actions (previously ~15 diplomatic-only)
- Both powers have offensive AND defensive options

### 3. Scenario Description Updates (fictionalized_scenarios.R)

**Initial Situation:**
- Changed from: "Novaris preparations complete, Tethys seeking help"
- To: "Multi-domain active conflict - cyber attacks daily, economic warfare begun, covert ops underway"
- Emphasizes: Both sides have escalation options across all domains

**Information Asymmetries:**
- Added Tethys knowledge of Novaris vulnerabilities (logistics, pipeline leverage, ethnic networks)
- Added Novaris knowledge of Tethys offensive plans (preemptive strike consideration)
- Added unknown capabilities (Tethys cyber kill switches in Novaris grid, sabotage pre-positioned)

**Escalation Paths:**
- Added: "escalation_path_tethys_initiated" (Tethys can start conflict via preemptive strike)
- Added: "deescalation_path_deterrence_succeeds" (Tethys demonstrates capability, deters invasion)
- Shows: Both sides can escalate or de-escalate

### 4. Config Updates (config.R)

**Pre-Invasion Scenario:**
- Name: "Multi-Domain Escalation Crisis"
- Increased sanctions_level: 0.1 → 0.2 (economic warfare begun)
- Situation text emphasizes:
  - 40% mobilization (not complete)
  - Both sides have vulnerabilities
  - Active conflict in cyber/economic/covert domains
  - Both can escalate: Novaris (invade/cyber/economic) vs Tethys (preemptive/economic/rally)
  - "30 Days to Decision Point"

---

## Expected Impact

**Before Rebalance:**
- Novaris: Many options
- Tethys: Mostly diplomatic, waiting for help
- Asymmetric action usage

**After Rebalance:**
- Novaris: 30+ actions (military, cyber, economic, covert, diplomatic)
- Tethys: 30-35 actions (offensive + defensive across all domains)
- Symmetric action space

**Action Categories Now Viable for BOTH Powers:**
1. **Military:** Buildup, strikes, incursions, fortifications
2. **Cyber:** Attacks, theft, counterintelligence
3. **Economic:** Sanctions, embargos, asset seizures
4. **Covert:** Regime destabilization, sabotage, assassinations, proxy support
5. **Intelligence:** Gathering, surveillance, disinformation
6. **Diplomatic:** Negotiations, coalitions, mediation

**Key Design Principle:**
Objectives guide WHAT to achieve, but don't predetermine HOW.
Both powers have genuine strategic choices across all action domains.

---

## Test Plan

**Run Configuration:**
- Scenario: pre_invasion (rebalanced)
- Periods: 3 (for quick test)
- Cross-expertise: ENABLED (agent_decision.R changes)

**Success Metrics:**
1. **Action diversity increased:** Target >10 unique actions (baseline was 5)
2. **Tethys uses offensive actions:** Cyber attacks, limited strikes, economic warfare (not just diplomacy)
3. **Novaris uses non-military actions:** Cyber, economic, covert (not just buildup→invade)
4. **Cross-expertise visible:** Military advisors suggesting diplomacy, diplomats suggesting strikes, etc.
5. **Multiple domain engagement:** Actions across military, cyber, economic, covert, diplomatic

**Comparison to Baseline:**
- Baseline (v3.6 Test 3): 5 unique actions, 50% proxy_support, 0% cross-expertise
- Target (v3.7): 15-20 unique actions, <30% any single action, visible cross-expertise

---

**Status:** Changes implemented, ready for test simulation.
