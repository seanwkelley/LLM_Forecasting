# Independent External Actors

**Implemented:** January 2026
**Version:** 3.1.1

## Change Summary

External actors are now **independent** - each makes their own decisions rather than coordinating as a single "external" faction.

---

## What Changed

### OLD System (v3.1)
```
Factions:
- major_power (Novaris): 4 agents coordinate → 1 action
- small_power (Tethys): 4 agents coordinate → 1 action
- external: 4 agents coordinate → 1 action  ❌ PROBLEM

All external actors (Meridian, Valkoria, Aurelia, UN/EU) coordinated
together despite having conflicting objectives!
```

### NEW System (v3.1.1)
```
Factions:
- major_power (Novaris): 4 agents coordinate → 1 action
- small_power (Tethys): 4 agents coordinate → 1 action
- meridian: 1 agent → 1 independent action  ✅
- valkoria: 1 agent → 1 independent action  ✅
- aurelia: 1 agent → 1 independent action   ✅
- international_org: 1 agent → 1 independent action  ✅

Each external actor pursues their own interests independently!
```

---

## The Four External Actors

### 1. Meridian (Allied Defender)
- **Supports:** Tethys (smaller power)
- **Hawk/Dove:** 0.6 (moderate hawk)
- **Objectives:**
  - Provide military aid to Tethys
  - Economic support to sustain resistance
  - Prevent Novaris expansion
- **Typical Actions:** `financial_aid`, `joint_exercises`, `economic_sanctions` (on Novaris)

### 2. Valkoria (Allied Aggressor)
- **Supports:** Novaris (major power)
- **Hawk/Dove:** 0.7 (hawk)
- **Objectives:**
  - Diplomatic cover for Novaris actions
  - Economic support despite sanctions
  - Strategic partnership benefits
- **Typical Actions:** `diplomatic_visit`, `trade_agreement`, `propaganda_campaign` (for Novaris)

### 3. Aurelia (Neutral Power)
- **Supports:** Neither (mediator)
- **Hawk/Dove:** 0.2 (dove)
- **Objectives:**
  - Regional stability
  - Mediation between parties
  - Prevent escalation
- **Typical Actions:** `mediation_offer`, `peace_talks`, `humanitarian_aid`

### 4. International Organization (UN/EU)
- **Supports:** Civilians/humanitarian
- **Hawk/Dove:** 0.1 (strong dove)
- **Objectives:**
  - Humanitarian access
  - Ceasefire
  - Civilian protection
- **Typical Actions:** `humanitarian_aid`, `peace_talks`, `mediation_offer`

---

## How It Works Now

### Each Period

**Pre-Action Phase:**
1. **Novaris faction** (4 agents) coordinates internally → Defense Minister decides action
2. **Tethys faction** (4 agents) coordinates internally → President decides action
3. **Meridian** (1 agent) → Decides action independently (no coordination)
4. **Valkoria** (1 agent) → Decides action independently (no coordination)
5. **Aurelia** (1 agent) → Decides action independently (no coordination)
6. **International Org** (1 agent) → Decides action independently (no coordination)

**Post-Action Phase:**
- Agents can still discuss across factions
- Meridian talks with Tethys (their ally)
- Valkoria talks with Novaris (their ally)
- Aurelia mediates with both sides
- International Org engages on humanitarian issues

### Example Period Output

```
========== PERIOD 3 ==========

--- MAJOR POWER Faction Decision ---
  → Pre-action coordination within MAJOR POWER faction...
    [4 agents discuss]
  → Decision maker: Defense Minister
  ACTION: full_scale_attack

--- SMALL POWER Faction Decision ---
  → Pre-action coordination within SMALL POWER faction...
    [4 agents discuss]
  → Decision maker: President
  ACTION: intelligence_gathering

--- MERIDIAN Faction Decision ---
  → Decision maker: Meridian Representative
  ACTION: financial_aid
  TARGET: Tethys

--- VALKORIA Faction Decision ---
  → Decision maker: Valkoria Representative
  ACTION: trade_agreement
  TARGET: Novaris

--- AURELIA Faction Decision ---
  → Decision maker: Aurelia Representative
  ACTION: mediation_offer

--- INTERNATIONAL ORG Faction Decision ---
  → Decision maker: International Organization Representative
  ACTION: humanitarian_aid
```

---

## Research Benefits

### 1. Coalition Dynamics
- How do allies coordinate their support?
- Do supporters act in sync or independently?
- Can allies disagree on how to help their partner?

### 2. Third-Party Influence
- How much do external actors affect conflict outcomes?
- Is military aid more effective than economic sanctions?
- Do neutral mediators reduce escalation?

### 3. Action Diversity
- With 6 factions acting instead of 3, more actions per period
- Richer interaction patterns
- More complex strategic environment

### 4. Competing Interests
- Meridian vs Valkoria direct competition
- Neutral actors trying to balance both sides
- International organizations pursuing humanitarian goals

### 5. Realistic International Relations
- Countries pursue their own interests
- Alliances don't mean automatic coordination
- Different actors have different constraints and capabilities

---

## Technical Details

### Files Modified

1. **`config.R`** (lines 151-190)
   - Changed `faction = "external"` to individual faction names
   - Added country names for each external actor
   - Meridian, Valkoria, Aurelia, International_org

2. **`src/agent_decision.R`** (line 536)
   - Changed faction list from 3 to 6 factions
   - `c("major_power", "small_power", "meridian", "valkoria", "aurelia", "international_org")`

3. **`src/interaction_engine.R`** (lines 59-101)
   - Updated post-action discussion scenarios
   - Meridian engages with Tethys
   - Valkoria engages with Novaris
   - Aurelia mediates
   - International Org focuses on humanitarian issues

4. **`README.md`** (lines 161-169)
   - Updated external actor descriptions
   - Clarified independent decision-making

---

## Backwards Compatibility

### Breaking Changes
- Old simulations that referenced "external" faction will need updating
- Coordination records will show 6 factions instead of 3
- Action logs will show more actors

### Migration
If you have old simulation code:
```r
# OLD
external_agents <- Filter(function(a) a$faction == "external", agents)

# NEW
meridian_agents <- Filter(function(a) a$faction == "meridian", agents)
valkoria_agents <- Filter(function(a) a$faction == "valkoria", agents)
aurelia_agents <- Filter(function(a) a$faction == "aurelia", agents)
intl_org_agents <- Filter(function(a) a$faction == "international_org", agents)
```

---

## Future Enhancements

### Possible Extensions

1. **Coalition Formation**
   - Allow external actors to coordinate on specific issues
   - Form temporary coalitions (Meridian + Aurelia + UN/EU)
   - Coalition actions with combined effects

2. **Multi-Agent External Powers**
   - Meridian could have 2-3 agents (President, Foreign Minister, Military)
   - Internal debates within supporting countries
   - More realistic decision-making for major powers

3. **Bilateral Coordination**
   - Meridian and Tethys pre-coordinate actions
   - Joint action planning
   - Conditional commitments

4. **Resource Constraints**
   - External actors have limited budgets
   - Aid decisions compete with domestic needs
   - Fatigue over time

5. **Public Opinion in External Countries**
   - Domestic pressure affects support levels
   - Opposition to costly interventions
   - Media coverage impacts

---

## Testing

To verify independent actors:

```bash
Rscript run_simulation_with_actions.R
```

You should see:
- 6 faction decision sections (not 3)
- No coordination for single-agent factions (Meridian, Valkoria, etc.)
- Each external actor choosing different actions based on their interests
- Post-action discussions between allies (Meridian-Tethys, Valkoria-Novaris)

---

**Feature Status**: ✅ **IMPLEMENTED and ACTIVE**

All external actors now act independently by default.
