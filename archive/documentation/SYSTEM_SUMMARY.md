# Complete System Summary

## What You Have Now

Your simulation system now has **three layers** that work together:

### Layer 1: Original Multi-Agent Framework ✅
- **11 intra-country actors** across 3 factions
- **Roles**: military, government, economic, intelligence, diplomatic, political
- **Personality traits**: hawk/dove (0-1), policy adherence (0-1), objective alignment (0-1)
- **Factions**: major_power, small_power, external
- **Interaction engine**: meetings, negotiations, communications
- **External events**: sanctions, battlefield shifts, economic shocks
- **Aggregator**: LLM evaluates government collapse probability

### Layer 2: Enhanced Cognitive Framework ✅ (NEW)
- **6 worldview types** that shape perception:
  - Realist (power-focused, threat-oriented)
  - Liberal Institutionalist (cooperation-focused, norms-oriented)
  - Constructivist (relationship-focused, identity-oriented)
  - Nationalist Populist (sovereignty-focused, emotion-driven)
  - Revolutionary Revisionist (change-focused, opportunistic)
  - Pragmatic Technocrat (data-focused, analytical)

- **Deception mechanics**:
  - Capacity (technical ability, varies by role: intel=0.9, int_org=0.2)
  - Willingness (modified by hawk/dove score and role)
  - Success based on capacity vs. target's analytical capability
  - Trust damage when detected (trust × 0.3)

- **Information asymmetry**:
  - Access levels (0-1): intelligence=0.95, military=0.8, opposition=0.4
  - Analytical capability (0-1): how well they interpret information
  - Role-specific information domains (SIGINT, HUMINT, economic data, etc.)
  - Smaller power penalty (×0.85), external actor penalty (×0.9)

- **Information filtering**:
  - Realists amplify threats (+30%)
  - Liberals amplify cooperation opportunities (+20%)
  - Nationalists weight in-group/out-group heavily
  - Each worldview has cognitive biases

### Layer 3: Fictionalized Scenarios ✅ (NEW)
- **8 named countries** with rich backgrounds:
  - **Novaris** (major power, authoritarian, revisionist) - formerly "major_power"
  - **Tethys** (small democracy, disputed territory) - formerly "small_power"
  - **Meridian** (superpower, democratic, global) - formerly "allied_power"
  - **Aurelia** (union, multilateral, cautious) - formerly "neutral_power"
  - Plus: Valdoria, Khazaran, Palmyra, Ashanti

- **3 scenario types**:
  - Territorial Dispute (Tethys Crisis)
  - Nuclear Proliferation (Khazaran Crisis)
  - Economic Warfare (Trade War)

- **Dynamic trajectories**:
  - Escalation path (aggressive actions > diplomatic × 2)
  - Deescalation path (diplomatic > aggressive × 2)
  - Wild card events (coups, terrorism, cyber attacks, pandemics)

- **Information distributed asymmetrically**:
  - Each country knows different things
  - Unknown information creates uncertainty
  - Intelligence gathering reveals secrets over time

## How It All Fits Together

### Agent Creation

```r
# Original config (config.R)
AGENTS <- list(
  major_military_chief = list(
    name = "Major Power Military Chief of Staff",
    faction = "major_power",
    role = "military",
    hawk_dove = 0.9,
    policy_adherence = 0.95,
    objective_alignment = 0.95
  ),
  # ... 10 more agents
)

# Enhanced integration (integrated_agent_system.R)
agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(
    major_power = "Novaris",
    small_power = "Tethys"
  )
)

# Result: Each agent now has:
# - Original: faction, role, hawk_dove, policy_adherence
# - Enhanced: worldview, deception capacity/willingness, information access
# - Cognitive: biases, decision style, trust levels, information filtering
```

### Worldview Assignment Logic

| Role | Hawk/Dove | → Worldview |
|------|-----------|-------------|
| military | >0.8 | nationalist_populist |
| military | 0.6-0.8 | realist |
| military | <0.6 | pragmatic_technocrat |
| government (major_power) | >0.7 | nationalist_populist |
| government (small_power) | any | liberal_institutionalist |
| economic | any | pragmatic_technocrat |
| intelligence | >0.7 | realist |
| intelligence | <0.7 | pragmatic_technocrat |
| diplomatic | any | liberal_institutionalist |
| political (opposition) | >0.6 | nationalist_populist |
| political (opposition) | <0.6 | constructivist |
| foreign_government | any | liberal_institutionalist |
| international_org | any | liberal_institutionalist |

### Information Access by Role

| Role | Base Access | Has Access To |
|------|-------------|---------------|
| intelligence | 0.95 | SIGINT, HUMINT, satellite, intercepted comms |
| military | 0.80 | Battlefield reports, tactical intel, troop movements |
| government | 0.75 | Intel briefings, diplomatic cables, polls |
| diplomatic | 0.65 | Diplomatic cables, embassy reports, int'l media |
| economic | 0.60 | Economic stats, trade data, sanctions impact |
| foreign_gov | 0.70 | Diplomatic reports, intelligence sharing |
| international_org | 0.50 | Public info, humanitarian reports |
| political (opp) | 0.40 | Public info, media, leaked documents |

**Modified by faction:**
- Major power: no change
- Small power: ×0.85
- External: ×0.90

### Example: Same Agent Before/After

**Before (config.R only):**
```
Major Power Intelligence Director
- Faction: major_power
- Role: intelligence
- Hawk/Dove: 0.6
- Policy Adherence: 0.85
- Objective Alignment: 0.7
```

**After (with integrated_agent_system.R):**
```
Major Power Intelligence Director (Novaris)
- Faction: major_power → Country: Novaris
- Role: intelligence
- Hawk/Dove: 0.6 (moderate)
- Worldview: realist (power-focused, threat-oriented)
- Decision Style: rational_calculator
- Information Processing: threat_focused

Deception:
- Capacity: 0.9 (expert intelligence operative)
- Willingness: 0.7 (part of the job)
- Success Rate: ~72% baseline
- Detected Count: 0

Information:
- Access: 0.95 (best intelligence)
- Analytical Capability: 0.85 (trained analysts)
- Uncertainty: 0.19 (very confident)
- Has Access To: [SIGINT, HUMINT, satellite imagery,
                  intercepted communications, foreign agent reports]

Cognitive Biases:
- Assumes worst intentions
- Overweights military threats
- Underweights cooperation benefits
- Conspiracy thinking
- Trust baseline: 0.2 (low)

Trust Levels: (updated dynamically)
- Tethys President: 0.15
- Aurelia Representative: 0.25
- Meridian Representative: 0.10
```

## Usage Patterns

### Pattern 1: Intra-Faction Coordination

```r
# Novaris internal debate on Tethys crisis
novaris_agents <- get_agents_by_faction(agents, "major_power")

coordination <- intra_faction_coordination(
  novaris_agents,
  topic = "Response to Tethys referendum",
  context = current_situation
)

# Military Chief (hawk=0.9, nationalist): "military_buildup"
# Defense Minister (hawk=0.7, nationalist): "troop_movements"
# Economic Advisor (hawk=0.3, technocrat): "economic_sanctions"
# Intelligence (hawk=0.6, realist): "intelligence_gathering"

# Weighted consensus: 0.72 → "aggressive"
```

### Pattern 2: Information Sharing with Deception

```r
# Novaris Intelligence tries to deceive Aurelia
result <- share_information(
  sender = novaris_intel,      # Deception capacity: 0.9
  receiver = aurelia_diplomat,  # Analytical capability: 0.75
  information = false_intel,
  context = list(under_threat = TRUE)
)

# Success probability: 0.9 × (1 - 0.75 × 0.5) = 0.56
# If successful: Aurelia believes false info
# If detected: Trust × 0.3, relationship severely damaged
```

### Pattern 3: Worldview Filtering

```r
raw_situation <- list(
  threat_level = 0.4,
  cooperation_potential = 0.6
)

# Realist (Novaris Military)
realist_view <- filter_information(novaris_military, raw_situation, "intel")
# threat_level: 0.4 → 0.52 (amplified)
# cooperation_potential: 0.6 → 0.6 (no change)

# Liberal Institutionalist (Tethys Foreign Minister)
liberal_view <- filter_information(tethys_fm, raw_situation, "cable")
# threat_level: 0.4 → 0.4 (no change)
# cooperation_potential: 0.6 → 0.72 (amplified)

# Same facts, different perceptions!
```

### Pattern 4: Trust Evolution

```r
# Meridian-Novaris relationship over time
meridian_rep <- agents$allied_power
novaris_gov <- agents$major_defense_minister

# Turn 1: Diplomatic visit → Trust increases slowly
# Turn 2: Intelligence sharing with DETECTED deception → Trust × 0.3
# Turn 3: Trade agreement → Trust rebuilds slowly
# Turn 4: Cyber attack → Trust × 0.5
# Turn 5: Peace talks → Trust rebuilds slowly

# Final: Trust = 0.22 (severely damaged, cooperation very difficult)
# Would take many positive interactions to rebuild
```

## Key Files and Their Purposes

| File | Purpose | When to Use |
|------|---------|-------------|
| `config.R` | Define 11 agents with roles, factions, personalities | Start here - setup simulation |
| `integrated_agent_system.R` | Convert config agents to cognitive agents | Required - creates enhanced agents |
| `enhanced_action_space.R` | Worldview definitions, deception logic, filtering | Auto-loaded by integrated system |
| `fictionalized_scenarios.R` | Country definitions, scenario templates | Create scenarios with named countries |
| `action_space.R` | Optional escalation scoring from paper | Use if you want escalation metrics |
| `INTEGRATION_EXAMPLE.md` | Complete examples of how system works | Read this for usage patterns |
| `ENHANCED_FEATURES_GUIDE.md` | Deep dive on worldviews, deception, info asymmetry | Read for cognitive framework details |
| `ACTION_SPACE_GUIDE.md` | Guide to action categories and escalation | Read if using action_space.R |

## What Changed vs Original

### Preserved ✅
- 11 intra-country actors
- Factions (major_power, small_power, external)
- Roles (military, government, economic, etc.)
- Hawk/dove, policy adherence, objective alignment
- Interaction engine
- External events
- Aggregator probability assessment
- Forecasting prompt generation
- All logging and analysis

### Added ✨
- **Worldviews** (6 types) automatically assigned
- **Deception mechanics** (capacity, willingness, success probability)
- **Information asymmetry** (role-specific access and analytical capability)
- **Information filtering** through cognitive biases
- **Trust dynamics** that evolve over time
- **Fictionalized countries** with rich backgrounds
- **Dynamic scenarios** that evolve based on actions
- **Role-based communication** (not everyone can talk to everyone)
- **Information domains** (what each role can access)
- **Intra-faction coordination** with internal disagreement
- **Wild card events** for uncertainty

### Removed ❌
- Nothing! It's all additive

## Quick Start

```r
# 1. Load the integrated system
source("config.R")
source("src/integrated_agent_system.R")

# 2. Create enhanced agents from your config
agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(
    major_power = "Novaris",
    small_power = "Tethys"
  )
)

# 3. Examine an agent
print(get_agent_description(agents$major_intelligence))

# 4. Run intra-faction coordination
novaris <- get_agents_by_faction(agents, "major_power")
coordination <- intra_faction_coordination(novaris, "Crisis response", context)

# 5. Test deception
result <- share_information(
  agents$major_intelligence,
  agents$neutral_power,
  list(type = "signals_intelligence", content = "False flag operation"),
  list(under_threat = TRUE)
)

# 6. Continue with your existing simulation.R
# The agents work exactly like before, but with enhanced cognition!
```

## Research Questions You Can Now Answer

### Original Questions ✅
- What's the probability of government collapse?
- How do agent personalities affect outcomes?
- What role do external events play?
- How do LLM forecasts compare to humans?

### New Questions ✨
1. **Worldview Effects**
   - Do realist dyads escalate more than liberal dyads?
   - Can constructivists bridge conflicts?
   - Are technocrats better at avoiding war?

2. **Deception Dynamics**
   - Does deception lead to worse outcomes?
   - Can trust recover after detected deception?
   - Do intelligence agencies deceive more than diplomats?

3. **Information Asymmetry**
   - Does information advantage prevent conflict?
   - What happens when one side is blind?
   - Do poor analysts make worse decisions even with good intelligence?

4. **Intra-Faction Dynamics**
   - How do internal hawks/doves affect policy?
   - Can economic advisors restrain military chiefs?
   - Does opposition pressure change government behavior?

5. **Trust Evolution**
   - How long does it take to build trust?
   - Is trust damage irreversible?
   - Do different worldviews trust differently?

6. **Trajectory Dynamics**
   - What tipping points lead to escalation?
   - Can wild cards prevent war or cause it?
   - Are certain scenarios more prone to conflict?

## Next Steps

1. **Test the integrated system** with a simple example
2. **Run your existing simulation** with enhanced agents
3. **Compare outcomes** with/without deception
4. **Analyze worldview effects** on escalation
5. **Study trust dynamics** between factions
6. **Explore information asymmetry** impact on decisions

The system is backwards compatible - your existing code will work, but now with cognitive depth! 🎯
