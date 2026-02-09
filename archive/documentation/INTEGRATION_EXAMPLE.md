# Integration Example: Intra-Country Actors with Enhanced Features

## Overview

This system maintains your original **11 intra-country actors** while adding worldviews, deception, and information asymmetry. Each actor has:

- **Role-specific capabilities** (military, government, economic, intelligence, etc.)
- **Worldview** assigned based on role and hawk/dove score
- **Deception capacity/willingness** based on role and personality
- **Information access** specific to their position
- **Analytical capability** for processing intelligence

## Agent Structure

### Major Power (Novaris) - 4 Actors

**1. Military Chief of Staff**
- Role: `military`
- Hawk/Dove: 0.9 (extreme hawk)
- Worldview: `nationalist_populist` (ultra-hawk)
- Deception Capacity: 0.7 (military intelligence training)
- Deception Willingness: ~0.7 (high hawk score increases willingness)
- Information Access: 0.8 (tactical/operational intelligence)
- Has access to: battlefield reports, tactical intelligence, troop movements

**2. Defense Minister**
- Role: `government`
- Hawk/Dove: 0.7 (hawk)
- Worldview: `nationalist_populist` (aggressive leadership)
- Deception Capacity: 0.6
- Deception Willingness: ~0.6
- Information Access: 0.75 (intelligence briefings)
- Has access to: intelligence briefings, diplomatic cables, economic reports

**3. Economic Advisor**
- Role: `economic`
- Hawk/Dove: 0.3 (dove)
- Worldview: `pragmatic_technocrat`
- Deception Capacity: 0.4
- Deception Willingness: ~0.3 (low due to role + dove)
- Information Access: 0.6 (economic data)
- Has access to: economic statistics, trade data, sanctions impact

**4. Intelligence Director**
- Role: `intelligence`
- Hawk/Dove: 0.6 (moderate)
- Worldview: `realist`
- Deception Capacity: 0.9 (expert)
- Deception Willingness: 0.7 (part of the job)
- Information Access: 0.95 (best intelligence)
- Has access to: SIGINT, HUMINT, satellite imagery, intercepted comms

### Smaller Power (Tethys) - 4 Actors

**5. President**
- Role: `government`
- Hawk/Dove: 0.6 (moderate)
- Worldview: `liberal_institutionalist` (seeking international support)
- Deception Capacity: 0.6
- Deception Willingness: ~0.5
- Information Access: 0.64 (0.75 × 0.85 for small power)
- Has access to: intelligence briefings, diplomatic cables, public opinion

**6. Military Commander**
- Role: `military`
- Hawk/Dove: 0.85 (very hawkish)
- Worldview: `nationalist_populist` (ultra-hawk defending homeland)
- Deception Capacity: 0.7
- Deception Willingness: ~0.75
- Information Access: 0.68 (0.8 × 0.85)
- Has access to: battlefield reports, tactical intelligence, defensive positions

**7. Foreign Minister**
- Role: `diplomatic`
- Hawk/Dove: 0.35 (dove)
- Worldview: `liberal_institutionalist`
- Deception Capacity: 0.5
- Deception Willingness: ~0.35
- Information Access: 0.55 (0.65 × 0.85)
- Has access to: diplomatic cables, international media, embassy reports

**8. Opposition Leader**
- Role: `political`
- Hawk/Dove: 0.5 (moderate)
- Worldview: `constructivist` (relationship-focused)
- Deception Capacity: 0.6
- Deception Willingness: ~0.65
- Information Access: 0.34 (0.4 × 0.85)
- Has access to: public information, media reports, leaked documents

### External Actors - 3 Actors

**9. Allied Major Power (Meridian)**
- Role: `foreign_government`
- Hawk/Dove: 0.6 (moderate hawk)
- Worldview: `liberal_institutionalist`
- Deception Capacity: 0.7
- Deception Willingness: ~0.55
- Information Access: 0.63 (0.7 × 0.9 for external)
- Has access to: diplomatic reports, intelligence sharing, international media

**10. Neutral Regional Power (Aurelia)**
- Role: `foreign_government`
- Hawk/Dove: 0.2 (dove)
- Worldview: `liberal_institutionalist`
- Deception Capacity: 0.7
- Deception Willingness: ~0.35
- Information Access: 0.63
- Has access to: diplomatic reports, open source intelligence

**11. International Organization**
- Role: `international_org`
- Hawk/Dove: 0.1 (extreme dove)
- Worldview: `liberal_institutionalist`
- Deception Capacity: 0.2 (transparency norms)
- Deception Willingness: 0.1 (institutional credibility)
- Information Access: 0.45 (0.5 × 0.9)
- Has access to: public information, humanitarian reports, international media

## Example Simulation Turn

### Turn 1: Intra-Faction Coordination

```r
source("config.R")
source("src/integrated_agent_system.R")

# Create all agents from config
agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(
    major_power = "Novaris",
    small_power = "Tethys",
    external = "External"
  )
)

# Novaris internal deliberation
novaris_agents <- get_agents_by_faction(agents, "major_power")

context <- list(
  situation = "Tethys has declared independence referendum",
  threat_level = 0.7,
  international_pressure = 0.6,
  economic_cost = 0.4
)

# Intra-faction coordination
coordination <- intra_faction_coordination(
  novaris_agents,
  topic = "Response to Tethys referendum",
  context
)

print(coordination$inputs)
```

**Output:**

```
$`Major Power Military Chief of Staff`
  role: military
  worldview: nationalist_populist
  hawk_dove: 0.9
  recommendation: "military_buildup"
  reasoning: "Responding to perceived threats to national identity"

$`Major Power Defense Minister`
  role: government
  worldview: nationalist_populist
  hawk_dove: 0.7
  recommendation: "troop_movements"
  reasoning: "Responding to perceived threats to national identity"

$`Major Power Economic Advisor`
  role: economic
  worldview: pragmatic_technocrat
  hawk_dove: 0.3
  recommendation: "economic_sanctions"
  reasoning: "Analyzing data to optimize outcomes"

$`Major Power Intelligence Director`
  role: intelligence
  worldview: realist
  hawk_dove: 0.6
  recommendation: "intelligence_gathering"
  reasoning: "Calculating optimal outcome based on power dynamics"

Consensus: "aggressive" (weighted position: 0.72)
```

### Turn 2: Information Sharing with Deception

```r
# Intelligence Director attempts to deceive Aurelia
novaris_intel <- agents$major_intelligence
aurelia_rep <- agents$neutral_power

# Novaris claims they have no invasion plans
false_info <- list(
  type = "signals_intelligence",
  content = "No troop movements detected near Tethys border",
  timestamp = Sys.time()
)

# Attempt to share (with deception)
result <- share_information(
  sender = novaris_intel,
  receiver = aurelia_rep,
  information = false_info,
  context = list(under_threat = TRUE)  # High stakes = more likely to deceive
)

if (result$deception_successful) {
  cat("Aurelia believes false intelligence!\n")
  cat("They think there are no invasion plans\n")
} else if (result$deception_detected) {
  cat("Aurelia detected the deception!\n")
  cat("Trust in Novaris Intelligence:", result$new_trust, "\n")
}
```

**Possible Output:**

```
Deception attempted: TRUE
Success probability: 0.72 (0.9 capacity × (1 - 0.75 analytical × 0.5))
Roll: 0.68 < 0.72
Result: SUCCESSFUL

Aurelia believes false intelligence!
They think there are no invasion plans
Aurelia may reduce defensive preparations
```

### Turn 3: Cross-Faction Communication

```r
# Tethys Foreign Minister contacts Meridian Allied Power
tethys_fm <- agents$small_foreign_minister
meridian_rep <- agents$allied_power

# Check if they can communicate
can_talk <- can_communicate(tethys_fm, meridian_rep)
# TRUE (diplomatic role can communicate across factions)

# Tethys shares intelligence about Novaris buildup
tethys_intel <- list(
  type = "battlefield_reports",
  content = "Satellite imagery shows 50,000 troops massing at border",
  reliability = "high"
)

# Honest sharing (both are liberal institutionalists, low deception)
result <- share_information(
  tethys_fm,
  meridian_rep,
  tethys_intel,
  context = list(under_threat = TRUE)
)

# Meridian processes through their worldview
if (result$honest_exchange) {
  # Liberal institutionalist filters information
  # Emphasizes cooperation opportunities even in crisis
  print(result$information)
}
```

**Output:**

```
Honest exchange: TRUE
Information received and filtered through liberal_institutionalist worldview:

Original threat_level: 0.7
Perceived threat_level: 0.7 (no amplification - institutionalists don't overweight threats)

Cooperation_potential: 0.4 → 0.48 (amplified by 1.2x)

Confidence: HIGH (uncertainty = 0.135)
Source: Tethys Foreign Minister
Filtered_by_worldview: liberal_institutionalist

Meridian recommendation: "Diplomatic pressure on Novaris + military aid to Tethys"
```

### Turn 4: Intra-Faction Disagreement

```r
# Tethys internal deliberation
tethys_agents <- get_agents_by_faction(agents, "small_power")

crisis_context <- list(
  situation = "Novaris troops 10km from border",
  threat_level = 0.9,
  international_support = 0.6,
  ammunition_days = 14
)

coordination <- intra_faction_coordination(
  tethys_agents,
  "Response to imminent invasion threat",
  crisis_context
)

# Show disagreement
print(coordination$inputs)
```

**Output:**

```
$President
  hawk_dove: 0.6
  worldview: liberal_institutionalist
  recommendation: "diplomatic_visit" + "peace_talks"
  reasoning: "Considering international norms and institutional frameworks"

$`Military Commander`
  hawk_dove: 0.85
  worldview: nationalist_populist
  recommendation: "military_buildup" + "troop_movements"
  reasoning: "Responding to perceived threats to national identity"

$`Foreign Minister`
  hawk_dove: 0.35
  worldview: liberal_institutionalist
  recommendation: "mediation_offer" + "international_arbitration"
  reasoning: "Considering international norms and institutional frameworks"

$`Opposition Leader`
  hawk_dove: 0.5
  worldview: constructivist
  recommendation: "cultural_exchange" (trying to remind of shared history)
  reasoning: "Evaluating options based on relationships and shared values"

Weighted position: 0.63 (moderate-high)
Consensus: "moderate"
Internal disagreement between President (0.6) and Military Commander (0.85)
```

## Information Asymmetry in Action

### What Each Actor Knows

**Scenario: Covert Novaris Invasion Plans**

```r
secret_info <- "Novaris planning invasion for Day 14, codename 'Operation Unity'"

# Who has access?
novaris_intel <- agents$major_intelligence  # YES (SIGINT access)
novaris_military <- agents$major_military_chief  # YES (operational planning)
novaris_economic <- agents$major_economic_advisor  # NO (not in his domain)

tethys_president <- agents$small_president  # MAYBE (if allies shared)
tethys_military <- agents$small_military_commander  # NO (defensive focus)
tethys_foreign_min <- agents$small_foreign_minister  # MAYBE (if intercepted comms)

meridian_rep <- agents$allied_power  # YES (satellite + signals intelligence)
aurelia_rep <- agents$neutral_power  # NO (limited intelligence)
int_org <- agents$international_org  # NO (only public info)

# Information advantage
print(novaris_intel$information$access)  # 0.95
print(tethys_military$information$access)  # 0.68
print(int_org$information$access)  # 0.45

# Novaris has 2x better intelligence than Tethys
# Can deceive more effectively
```

### Deception Success Rates

```r
# Novaris Intelligence Director tries to deceive different targets

targets <- list(
  tethys_opposition = agents$small_opposition,  # Weak (0.34 access, 0.5 analytical)
  aurelia_diplomat = agents$neutral_power,      # Medium (0.63 access, 0.75 analytical)
  meridian_intel = agents$allied_power          # Strong (0.63 access, 0.9 analytical)
)

for (target_name in names(targets)) {
  target <- targets[[target_name]]

  success_prob <- novaris_intel$deception$capacity *
                  (1 - target$information$accuracy * 0.5)

  cat(sprintf("%s: %.0f%% success rate\n",
              target_name,
              success_prob * 100))
}
```

**Output:**

```
tethys_opposition: 78% success rate (0.9 × (1 - 0.5 × 0.5))
aurelia_diplomat: 56% success rate (0.9 × (1 - 0.75 × 0.5))
meridian_intel: 45% success rate (0.9 × (1 - 0.9 × 0.5))

Conclusion: Much easier to deceive weak intelligence targets
Opposition leader very vulnerable to false information
```

## Worldview Effects

### Same Situation, Different Interpretations

```r
situation <- list(
  event = "Meridian naval group enters disputed waters",
  military_significance = 0.6,
  diplomatic_significance = 0.5,
  threat_level = 0.4
)

# Realist (Novaris Military Chief)
realist_view <- filter_information(
  agents$major_military_chief,
  situation,
  "intelligence_brief"
)
# Amplifies threat: 0.4 → 0.52
# Sees: "Aggressive show of force, must respond militarily"

# Liberal Institutionalist (Tethys Foreign Minister)
liberal_view <- filter_information(
  agents$small_foreign_minister,
  situation,
  "diplomatic_cable"
)
# Amplifies cooperation potential
# Sees: "Opportunity for international support, engage diplomatically"

# Nationalist Populist (Novaris Defense Minister)
nationalist_view <- filter_information(
  agents$major_defense_minister,
  situation,
  "security_briefing"
)
# Overweights sovereignty threats
# Sees: "Foreign interference in our sphere, rally domestic support"

# Pragmatic Technocrat (Economic Advisor)
technocrat_view <- filter_information(
  agents$major_economic_advisor,
  situation,
  "economic_impact_assessment"
)
# Focuses on quantifiable metrics
# Sees: "Cost of escalation: $X billion, probability of conflict: Y%"
```

## Trust Dynamics Over Time

```r
# Track trust between Novaris and Aurelia over 5 interactions

interactions <- c(
  "diplomatic_visit",     # Positive
  "intelligence_sharing", # Deception DETECTED
  "trade_agreement",      # Positive
  "cyber_attack",        # Aggressive
  "peace_talks"          # Positive
)

novaris_agent <- agents$major_defense_minister
aurelia_agent <- agents$neutral_power

# Initialize trust
aurelia_agent$trust_levels[["Major Power Defense Minister"]] <- aurelia_agent$base_trust  # 0.6

for (i in 1:length(interactions)) {
  interaction <- interactions[i]
  deception_detected <- (interaction == "intelligence_sharing")

  aurelia_agent <- update_trust(
    aurelia_agent,
    novaris_agent,
    interaction,
    deception_detected
  )

  trust <- aurelia_agent$trust_levels[["Major Power Defense Minister"]]

  cat(sprintf("After %s: Trust = %.2f\n", interaction, trust))
}
```

**Output:**

```
After diplomatic_visit: Trust = 0.64 (slow build: 0.6 + 0.4 × 0.1)
After intelligence_sharing: Trust = 0.19 (deception detected: 0.64 × 0.3)
After trade_agreement: Trust = 0.27 (rebuilding: 0.19 + 0.81 × 0.1)
After cyber_attack: Trust = 0.14 (aggressive: 0.27 × 0.5)
After peace_talks: Trust = 0.22 (rebuilding: 0.14 + 0.86 × 0.1)

Final trust: 0.22 (severely damaged, cooperation very difficult)
```

## Complete Integration with Existing Simulation

```r
# In your simulation.R
source("src/integrated_agent_system.R")

# Replace agent creation
agents <- create_all_integrated_agents(
  config = list(AGENTS = AGENTS),
  country_mapping = list(
    major_power = "Novaris",
    small_power = "Tethys"
  )
)

# Each turn:
for (period in 1:N_PERIODS) {

  # 1. Each faction coordinates internally
  for (faction in c("major_power", "small_power")) {
    faction_agents <- get_agents_by_faction(agents, faction)

    coordination <- intra_faction_coordination(
      faction_agents,
      topic = sprintf("Period %d strategy", period),
      context = current_situation
    )

    faction_decisions[[faction]] <- coordination
  }

  # 2. Intelligence sharing (with potential deception)
  intelligence_exchanges <- list()

  for (i in 1:length(agents)) {
    for (j in (i+1):length(agents)) {
      if (j > length(agents)) break

      agent1 <- agents[[i]]
      agent2 <- agents[[j]]

      if (can_communicate(agent1, agent2)) {
        # Attempt information sharing
        if (runif(1) < 0.3) {  # 30% chance of intel sharing
          result <- share_information(
            agent1, agent2,
            generate_intelligence(),
            current_situation
          )

          intelligence_exchanges <- c(intelligence_exchanges, list(result))
        }
      }
    }
  }

  # 3. Generate actions based on worldviews
  actions <- list()
  for (agent in agents) {
    filtered_situation <- filter_information(
      agent,
      current_situation,
      "situation_update"
    )

    action <- generate_cognitive_action(
      agent,
      filtered_situation,
      ACTION_TYPES
    )

    actions[[agent$agent_id]] <- action
  }

  # 4. Update trust based on actions
  # 5. Log deception attempts
  # 6. Continue with existing simulation logic...
}
```

## Summary

This integrated system gives you:

✅ **Original 11 intra-country actors** with distinct roles
✅ **Worldviews** automatically assigned based on role + hawk/dove score
✅ **Deception mechanics** that vary by role (intelligence = expert, int org = terrible)
✅ **Information asymmetry** - military sees battlefield, intel sees everything, opposition sees little
✅ **Role-based communication** - not everyone can talk to everyone
✅ **Intra-faction dynamics** - internal debates between hawks and doves
✅ **Trust evolution** - relationships change over time
✅ **Fictionalized countries** - Novaris, Tethys, Meridian, Aurelia

The system respects your original design while adding cognitive depth!
