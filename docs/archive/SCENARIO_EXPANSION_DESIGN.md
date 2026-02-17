# Scenario Expansion Design

## Current Limitations

### 1. **Single Domain Focus**
Current scenario is primarily **land-based** conventional conflict:
- Limited naval dimension (ports mentioned but no naval actions)
- No explicit air warfare
- Cyber mentioned but not central
- Space/satellite domain absent

### 2. **Short Time Horizon**
- 5 periods × 7 days = 35 days total
- Too short for:
  - Arms development programs
  - Long-term economic strategies
  - Diplomatic relationship building
  - Public opinion shifts

### 3. **Binary Actors**
- Primarily Novaris vs. Tethys
- External actors (Meridian, Valkoria, etc.) are supporting cast
- No complex triangular dynamics

### 4. **Linear Escalation**
- Conflict starts at moderate level (5/10)
- Escalates somewhat predictably
- No sudden shocks or wildcards (beyond event generator)

---

## Proposed Expansions

### Option 1: **Multi-Domain Crisis** ⭐⭐⭐⭐⭐

**Concept:** Add explicit naval, air, cyber, and information warfare dimensions

**Implementation:**

#### A. Naval Dimension
Add to scenario backstory:
```
Disputed Waters: The Cerulean Strait between Novaris and Tethys
is a critical shipping lane carrying 30% of global energy exports.
Both nations claim territorial waters. Novaris maintains a naval
base on contested Serpent Island.

Recent incidents:
- Tethys coast guard detained Novaris fishing vessels
- Novaris destroyer conducted "freedom of navigation" exercise
- Neutral shipping complains of harassment
```

**Triggers naval actions:** naval_deployment, blockade, freedom_of_navigation_ops

#### B. Air Warfare Dimension
Add to scenario:
```
Air Space Tensions: Novaris claims Tethys air defense systems
threaten civilian air traffic. Tethys claims Novaris bombers
regularly violate airspace on "training missions."

Recent incidents:
- Tethys shot down reconnaissance drone
- Novaris scrambled fighters 15x this month
- No-fly zone proposals under international discussion
```

**Triggers:** air_patrols, air_defense_systems, no_fly_zone, air_strikes

#### C. Cyber Warfare Expansion
Current: Cyber mentioned but generic
Better: Specific cyber domains

```
Cyber Infrastructure at Risk:
- Tethys power grid (40% controlled by foreign tech)
- Novaris banking system (vulnerable to sanctions)
- Both nations' satellite networks
- Energy pipeline control systems
- Military command and control networks

Cyber Capabilities:
- Novaris: Tier 1 offensive, Tier 2 defensive
- Tethys: Tier 2 offensive, Tier 3 defensive (relies on allies)
```

**Enables:** targeted_cyber_ops, infrastructure_sabotage, cyber_espionage, cyber_defense

#### D. Information/Cognitive Warfare
Current: spread_disinformation exists
Better: Multi-layered information ops

```
Information Battlespace:
- Domestic public opinion (war support varies)
- International perception (legitimacy contest)
- Diaspora communities (divided loyalties)
- Social media narratives
- Traditional media control

Tools:
- State propaganda (legal, overt)
- Covert disinformation
- Influence operations
- Narrative warfare
```

**Enables:** propaganda_campaign, narrative_ops, influence_campaigns, truth_commissions

---

### Option 2: **Extended Time Horizons** ⭐⭐⭐⭐

**Concept:** Multiple simulation modes with different timescales

#### A. Tactical Mode (Current)
- 5-10 periods × 7 days
- Focus: Crisis management, escalation control
- Actions: Immediate tactical moves

#### B. Strategic Mode (NEW)
- 10-20 periods × 30 days (10-20 months)
- Focus: Long-term strategy, resource management
- Enables:
  - arms_development (takes 3-6 periods)
  - alliance_building (gradual trust building)
  - economic_transformation
  - public_opinion_shifts
  - military_modernization

#### C. Campaign Mode (NEW)
- 3 phases across 1-2 years
  - Phase 1: Pre-war posturing (6 months)
  - Phase 2: Active conflict (6 months)
  - Phase 3: Resolution/frozen conflict (6 months)

**Implementation:**
```r
# In config.R
SIMULATION_MODE <- "strategic"  # tactical, strategic, campaign

TIME_SCALES <- list(
  tactical = list(period_days = 7, n_periods = 5),
  strategic = list(period_days = 30, n_periods = 15),
  campaign = list(period_days = 60, n_periods = 12)
)
```

---

### Option 3: **Complex Multi-Actor Scenarios** ⭐⭐⭐⭐

**Concept:** Move beyond bilateral conflict

#### A. Triangular Dynamics
**Scenario:** Azurian Nuclear Crisis (already exists!)
- Azuria develops nukes
- Palmyra provides tech
- Meridian pressures for action
- Aurelia opposes military strikes
- Creates complex alliance dilemmas

**Triggers:**
- Nuclear inspection demands
- Sanctions coordination
- Intelligence sharing
- Preventive strike debates

#### B. Proxy War Scenario
**New Scenario:** Resource Competition in Ashanti
```
Ashanti Federation discovers massive rare earth deposits.
- Novaris-backed faction vs. Meridian-backed faction
- Both major powers fight through proxies
- Ashanti government trying to maintain neutrality
- Regional powers (Azuria, Palmyra) picking sides

Actions enabled:
- proxy_support (already exists!)
- arms_transfers
- economic_inducements
- covert_operations
- deniable_escalation
```

#### C. Alliance Crisis
**New Scenario:** Valkoria-Novaris Alliance Strain
```
Valkoria increasingly skeptical of supporting Novaris:
- Economic costs mounting
- Western sanctions hurting
- Domestic opposition growing
- Fear of being dragged into war

Dynamics:
- Novaris must balance aggression vs. ally retention
- Tethys can try to split the alliance
- Creates asymmetric diplomacy opportunities
```

---

### Option 4: **Wildcard Events System** ⭐⭐⭐

**Concept:** Low-probability, high-impact events

**Implementation:**
```r
# Add to event_generator.R
generate_wildcard_event <- function(period, state) {
  # 5% chance per period
  if (runif(1) > 0.05) return(NULL)

  wildcards <- list(
    "Leadership Change" = list(
      desc = "Surprise leadership change in key nation",
      effect = "Resets diplomatic relationships, uncertainty spike"
    ),
    "Economic Shock" = list(
      desc = "Global recession, energy crisis, or financial collapse",
      effect = "Changes cost calculations for all actors"
    ),
    "Technological Breakthrough" = list(
      desc = "New weapons system, cyber capability, or defense tech",
      effect = "Shifts military balance"
    ),
    "Popular Uprising" = list(
      desc = "Mass protests demanding war/peace",
      effect = "Constrains leader options"
    ),
    "Third Party Intervention" = list(
      desc = "Unexpected actor enters conflict",
      effect = "Complicates dynamics"
    ),
    "Intelligence Leak" = list(
      desc = "Secret plans exposed publicly",
      effect = "Forces transparency, diplomatic crisis"
    ),
    "Terrorist Attack" = list(
      desc = "Non-state actor attack blamed on rival",
      effect = "Risk of misattribution, escalation"
    ),
    "Natural Disaster" = list(
      desc = "Earthquake, pandemic, climate event",
      effect = "Humanitarian crisis, cooperation opportunity"
    )
  )

  sample(wildcards, 1)[[1]]
}
```

---

### Option 5: **Asymmetric Capabilities** ⭐⭐⭐⭐⭐

**Concept:** Make power asymmetries more explicit and actionable

**Current:** Both sides use similar action sets
**Better:** Capability-based action restrictions

```r
# In scenario definition
FACTION_CAPABILITIES <- list(
  major_power = list(
    naval = "tier_1",           # Can blockade, project power
    cyber = "tier_1_offensive",  # Advanced cyber weapons
    nuclear = "deployed",        # Has nuclear deterrent
    economic = "large_reserves", # Can sustain sanctions
    intelligence = "global_reach"
  ),

  small_power = list(
    naval = "coastal_defense",   # Cannot project naval power
    cyber = "tier_2_dependent",  # Relies on allies
    nuclear = "none",            # No WMD
    economic = "vulnerable",     # Limited reserves
    intelligence = "regional"    # Limited beyond borders
  )
)

# Actions become conditional
if (faction == "small_power" && action == "naval_blockade") {
  return("INSUFFICIENT CAPABILITY: Small power lacks blue-water navy")
}
```

**This enables:**
- Realistic asymmetric warfare
- Small power forced to use creative/unconventional tactics
- Major power has more options but at higher political cost

---

## Recommended Implementation Priority

### Phase 1: Quick Wins (1-2 hours) ⚡
✅ Enhanced domain prompts (DONE!)
✅ Creativity prompts (DONE!)
- [ ] Add naval dimension to current scenario (backstory edit)
- [ ] Add wildcard events (5% chance/period)

### Phase 2: Medium Effort (3-5 hours) 🔨
- [ ] Asymmetric capabilities system
- [ ] Extended time horizon option
- [ ] Multi-domain event triggers

### Phase 3: Major Expansion (1-2 days) 🏗️
- [ ] New multi-actor scenarios
- [ ] Campaign mode with phases
- [ ] Sophisticated cyber/information warfare

---

## Testing Strategy

After each phase:
1. Run 3-period test simulation
2. Check action variety (target: 35+ unique actions)
3. Verify creative actions appear (naval, cyber-specific, etc.)
4. Ensure narrative coherence maintained

---

## Expected Impact

### Current State:
- 28 unique actions used
- Creativity: 6.5/10
- Mostly land-based conventional tactics

### After Phase 1:
- Target: 35+ unique actions
- Creativity: 7.5/10
- Multi-domain thinking begins

### After Phase 2:
- Target: 40+ unique actions
- Creativity: 8.5/10
- Asymmetric tactics emerge

### After Phase 3:
- Target: 45+ unique actions
- Creativity: 9/10
- Sophisticated multi-domain strategies

---

## Questions for User

1. **Which expansion appeals most?**
   - Multi-domain (naval, air, cyber)?
   - Extended time horizons?
   - Multi-actor scenarios?
   - All of the above?

2. **Time commitment?**
   - Quick wins only (Phase 1)?
   - Medium effort (Phases 1-2)?
   - Full expansion (all phases)?

3. **Primary research goal?**
   - Realistic crisis simulation?
   - Testing model creativity?
   - Exploring specific domains (naval, cyber)?
   - Alliance dynamics?

4. **Acceptable complexity increase?**
   - Keep simple (current + small tweaks)?
   - Moderate complexity (asymmetric capabilities)?
   - High complexity (multi-actor, multi-phase)?
