# Enhanced Features Guide

## Overview

This system implements a sophisticated multi-agent simulation with:
- **Fictionalized countries** with detailed backgrounds and strategic interests
- **Cognitive worldviews** that shape how agents process information
- **Information asymmetry** - agents have different knowledge and intelligence capabilities
- **Deception mechanics** - agents can attempt to deceive based on capacity and willingness
- **Dynamic trajectories** - scenarios evolve based on agent actions
- **Rich action space** - diplomatic, economic, military, intelligence, and covert operations

## Fictional Countries

### Major Powers

**Meridian** (The United States of Meridian)
- Superpower on Western Continent
- Federal democracy with global military presence
- Experiencing domestic polarization and alliance fatigue
- GDP: $8.5 trillion, Population: 425 million

**Novaris** (The People's Federation of Novaris)
- Rising power on Eastern Continent
- Single-party technocratic state
- Seeks to reclaim "lost territories" and challenge regional order
- GDP: $3.8 trillion, Population: 340 million

**Aurelia** (The Aurelian Union)
- Supranational federation on Central Continent
- Post-conflict cooperation model
- Struggling with unity and energy dependence
- GDP: $5.2 trillion, Population: 280 million

### Regional Powers

**Valdoria** (The Federal Republic of Valdoria)
- Parliamentary democracy, Northern Continent
- Former colonial power facing domestic polarization
- Seeks to maintain naval access and contain Novaris
- GDP: $2.1 trillion, Population: 85 million

**Tethys** (The Democratic Commonwealth of Tethys)
- Multi-party democracy on disputed Eastern territory
- Claimed by Novaris, supported by Meridian
- Technologically advanced but vulnerable
- GDP: $680 billion, Population: 24 million

**Khazaran** (The Khazaran Caliphate)
- Constitutional theocracy, Southern Continent
- Oil-rich, regional influencer
- Seeking nuclear capability
- GDP: $1.2 trillion, Population: 92 million

**Palmyra** (The Palmyran Republic)
- Islamic republic, Southern Continent
- Revolutionary ideology, under heavy sanctions
- Developing asymmetric capabilities
- GDP: $450 billion, Population: 88 million

**Ashanti** (The Ashanti Federation)
- Federal democracy, Southern Continent
- Emerging power, resource-rich, non-aligned
- Economic boom and regional leadership ambitions
- GDP: $720 billion, Population: 215 million

## Worldview Frameworks

Agents don't just execute actions - they perceive and interpret the world through cognitive frameworks.

### 1. Realist
**Core belief:** International relations is a struggle for power; security comes from strength

**Information processing:**
- Overweights military threats
- Assumes worst intentions from others
- Focuses on relative gains vs. absolute gains
- Threat-focused attention

**Decision style:** Rational calculator
**Deception tendency:** Moderate
**Base trust:** 0.2 (low)

**Example countries:** Novaris military leadership, Valdoria hawks

### 2. Liberal Institutionalist
**Core belief:** International cooperation through institutions creates mutual benefit

**Information processing:**
- Overweights diplomatic solutions
- Assumes good faith initially
- Focuses on opportunities for cooperation
- Opportunity-focused attention

**Decision style:** Norm follower
**Deception tendency:** Low
**Base trust:** 0.6 (high)

**Example countries:** Aurelia bureaucracy, Meridian State Department

### 3. Constructivist
**Core belief:** Identity, culture, and relationships shape state behavior

**Information processing:**
- Overweights historical relationships
- Values shared identity and norms
- Pattern-focused attention on social dynamics
- Underweights material power

**Decision style:** Relationship-oriented
**Deception tendency:** Low
**Base trust:** 0.5 (moderate)

**Example countries:** Ashanti diplomats, Tethys cultural ministry

### 4. Nationalist Populist
**Core belief:** National sovereignty and cultural preservation above all

**Information processing:**
- Overweights sovereignty threats
- Strong in-group/out-group bias
- Identity-focused attention
- Underweights international opinion

**Decision style:** Emotion-driven
**Deception tendency:** High
**Base trust:** 0.1 (very low)

**Example countries:** Khazaran clerics, Novaris nationalists

### 5. Revolutionary Revisionist
**Core belief:** Existing order is unjust; must be overturned

**Information processing:**
- Overweights opportunities for change
- Assumes system rigged against them
- Advantage-focused attention
- Underweights stability costs

**Decision style:** Opportunistic
**Deception tendency:** Very high
**Base trust:** 0.05 (minimal)

**Example countries:** Palmyra leadership, Novaris hardliners

### 6. Pragmatic Technocrat
**Core belief:** Evidence-based policy produces optimal outcomes

**Information processing:**
- Overweights quantifiable metrics
- Data-focused attention
- Underweights intangibles (culture, emotion)
- Assumes rational actors

**Decision style:** Analytical
**Deception tendency:** Situational
**Base trust:** 0.4 (moderate-low)

**Example countries:** Novaris economic planners, Meridian defense analysts

## Information Asymmetry

Agents have different levels of **information access** and **analytical capability**:

### Information Access (0-1 scale)
- **0.9-1.0**: Superpower intelligence (satellite, SIGINT, HUMINT)
- **0.7-0.9**: Major power intelligence (good regional coverage)
- **0.5-0.7**: Regional power intelligence (focused capabilities)
- **0.3-0.5**: Limited intelligence (public sources, some covert)
- **0.0-0.3**: Poor intelligence (mostly public information)

### Analytical Capability (0-1 scale)
- **0.9-1.0**: Sophisticated analysis, accurate interpretations
- **0.7-0.9**: Professional intelligence analysis
- **0.5-0.7**: Competent analysis with some blind spots
- **0.3-0.5**: Mediocre analysis, frequent errors
- **0.0-0.3**: Poor analysis, biased interpretations

### What Agents Know

Information is distributed asymmetrically in scenarios:

**Example - Tethys Crisis:**

*Novaris knows:*
- Meridian intelligence shows 60% intervention probability
- Aurelia won't support military action (energy dependence)
- Tethys has only 2 weeks ammunition for high-intensity conflict

*Tethys knows:*
- Novaris has logistics problems for sustained operations
- Some Novaris generals oppose military action
- Meridian has pre-positioned equipment

*Meridian knows:*
- Novaris leadership divided on timing
- Aurelia will impose sanctions if invasion occurs
- Khazaran offered mediation but favors Novaris

*Unknown to all:*
- Palmyra secretly providing missile technology to Novaris
- Tethys developed cyberweapons targeting Novaris
- Valdoria penetrated Novaris military

## Deception Mechanics

Agents can attempt deception based on:

### Deception Capacity (0-1)
Technical ability to conduct deception operations:
- Intelligence tradecraft
- Communication security
- Operational security
- Cover story development

### Deception Willingness (0-1)
Strategic/moral willingness to deceive:
- Cultural norms around honesty
- Strategic necessity
- Historical precedent
- Leadership personality

### Deception Process

1. **Attempt Probability** = Base worldview tendency × Willingness
   - Modified by context (higher if under threat)
   - Reduced if recently caught deceiving

2. **Success Probability** = Deception capacity × (1 - Target's analytical capability)

3. **Outcomes:**
   - **Successful**: Target receives false information, acts on it
   - **Detected**: Target knows deception occurred, trust plummets
   - **Suspected**: Target uncertain, reduced trust

### Trust Dynamics

Trust between agents evolves:

- **Initial trust** = Worldview base trust (0.05 to 0.6)
- **Detected deception** → Trust × 0.3 (major loss)
- **Positive interaction** → Trust + (1 - Trust) × 0.1 (slow build)
- **Aggressive action** → Trust × 0.5 (significant loss)
- **Neutral interaction** → No change

Once trust falls below 0.1, cooperation becomes nearly impossible.

## Action Space

### 7 Action Categories

**1. Diplomatic**
- diplomatic_visit, peace_talks, trade_negotiation
- cultural_exchange, humanitarian_aid, mediation_offer

**2. Intelligence**
- share_intelligence, intelligence_gathering, surveillance_operation
- counterintelligence, spread_disinformation, propaganda_campaign

**3. Economic**
- trade_agreement, economic_sanctions, financial_aid
- resource_embargo, currency_manipulation, cyber_theft

**4. Military Posture**
- military_buildup, naval_deployment, air_patrols
- troop_movements, joint_exercises, arms_development

**5. Covert Operations**
- sabotage, assassination_attempt, regime_destabilization
- proxy_support, false_flag_operation, cyber_attack

**6. Open Conflict**
- border_incursion, limited_strike, full_scale_attack
- occupation, blockade, siege_warfare

**7. WMD (Weapons of Mass Destruction)**
- nuclear_development, chemical_weapons, biological_program
- tactical_nuclear_use, strategic_nuclear_strike

## Dynamic Scenarios

### Three Scenario Types

**1. Territorial Dispute (Tethys Crisis)**
- Novaris claims sovereignty over democratic Tethys
- Meridian security commitment tested
- Aurelia caught in middle
- Potential for major power conflict

**2. Nuclear Proliferation (Khazaran Nuclear Crisis)**
- Khazaran covert nuclear program discovered
- Palmyra providing technical assistance
- Preventive strike vs. diplomatic options
- Regional nuclear cascade risk

**3. Economic Warfare (Trade War)**
- Meridian-Novaris technology/trade conflict
- Global supply chain fragmentation
- Currency and financial system stress
- Alliance network pressures

### Trajectory Evolution

Scenarios evolve based on agent actions:

**Escalation Trajectory:**
- Aggressive actions > Diplomatic actions × 2
- Crisis level increases
- Wild card events more likely
- Harder to reverse course

**Deescalation Trajectory:**
- Diplomatic actions > Aggressive actions × 2
- Crisis level decreases
- Window for settlement opens
- Trust can be rebuilt

**Stable Trajectory:**
- Balanced mix of actions
- Status quo maintained
- Uncertainty about future
- Either side could tip balance

### Wild Card Events

Random events inject uncertainty:
- Coups or regime changes
- Terrorist attacks
- Cyber attacks on infrastructure
- Natural disasters or pandemics
- Intelligence failures
- Domestic political shifts

## Usage Examples

### Create Agents with Worldviews

```r
source("src/enhanced_action_space.R")

# Realist military planner for Novaris
novaris_general <- create_cognitive_agent(
  name = "General Chen",
  country = "Novaris",
  worldview = "realist",
  deception_capacity = 0.7,
  deception_willingness = 0.6,
  information_access = 0.8,
  analytical_capability = 0.75
)

# Liberal institutionalist diplomat for Aurelia
aurelia_diplomat <- create_cognitive_agent(
  name = "Ambassador Rousseau",
  country = "Aurelia",
  worldview = "liberal_institutionalist",
  deception_capacity = 0.3,
  deception_willingness = 0.2,
  information_access = 0.6,
  analytical_capability = 0.7
)

# Revolutionary leader for Palmyra
palmyra_leader <- create_cognitive_agent(
  name = "Supreme Guide Al-Rashid",
  country = "Palmyra",
  worldview = "revolutionary_revisionist",
  deception_capacity = 0.9,
  deception_willingness = 0.9,
  information_access = 0.5,
  analytical_capability = 0.6
)
```

### Create and Run Scenario

```r
source("src/fictionalized_scenarios.R")

# Create territorial dispute scenario
scenario <- create_scenario("territorial_dispute")

# Get scenario details
cat(scenario$name, "\n")
cat(scenario$description, "\n")
cat(scenario$initial_situation, "\n")

# Generate situation update for agent
update <- generate_situation_update(
  scenario,
  novaris_general,
  list(aurelia_diplomat, palmyra_leader)
)

# Check what intelligence Novaris has
print(update$intelligence)
```

### Deception in Action

```r
# Novaris attempts deception in diplomatic message
deception_attempt <- attempt_deception(
  novaris_general,
  action_type = "diplomatic_visit",
  target = aurelia_diplomat,
  context = list(under_threat = TRUE)
)

if (deception_attempt$attempted) {
  if (deception_attempt$successful) {
    cat("Deception succeeded - Aurelia fooled\n")
  } else {
    cat("Deception detected - Trust damaged\n")

    # Update trust
    aurelia_diplomat <- update_trust(
      aurelia_diplomat,
      novaris_general,
      "diplomatic_visit",
      deception_detected = TRUE
    )

    cat("New trust level:", aurelia_diplomat$trust_levels$`General Chen`, "\n")
  }
}
```

### Information Filtering

```r
# Raw intelligence report
raw_info <- list(
  threat_level = 0.4,
  cooperation_potential = 0.6,
  cultural_similarity = 0.3
)

# Realist processes it (amplifies threats)
realist_view <- filter_information(
  novaris_general,
  raw_info,
  "intelligence_report"
)

# Liberal institutionalist processes same info
liberal_view <- filter_information(
  aurelia_diplomat,
  raw_info,
  "intelligence_report"
)

# Compare interpretations
print(realist_view$threat_level)    # ~0.52 (amplified)
print(liberal_view$cooperation_potential)  # ~0.72 (amplified)
```

## Integration Example

Here's how to integrate with your simulation:

```r
# Setup
source("src/enhanced_action_space.R")
source("src/fictionalized_scenarios.R")

# Create scenario
scenario <- create_scenario("territorial_dispute")

# Create agents for key actors
agents <- list(
  create_cognitive_agent("Admiral Zhang", "Novaris", "realist",
                        0.75, 0.65, 0.85, 0.8),
  create_cognitive_agent("President Lin", "Tethys", "liberal_institutionalist",
                        0.4, 0.3, 0.6, 0.65),
  create_cognitive_agent("SecDef Williams", "Meridian", "pragmatic_technocrat",
                        0.6, 0.5, 0.95, 0.9)
)

# Simulation loop
for (turn in 1:scenario$max_turns) {
  cat("\n=== Turn", turn, "===\n")

  # Each agent makes decision
  actions <- list()
  for (agent in agents) {
    # Get situation update (filtered by information access)
    situation <- generate_situation_update(scenario, agent, agents)

    # Agent decides action based on worldview
    decision <- generate_cognitive_action(agent, situation, ACTION_TYPES)

    actions[[agent$name]] <- decision

    cat(agent$name, "- Action:", decision$action,
        "| Worldview:", decision$worldview_influence,
        "| Deception:", decision$deception$attempted, "\n")
  }

  # Update scenario trajectory
  scenario <- update_scenario_trajectory(scenario, actions)

  cat("Trajectory:", scenario$current_trajectory,
      "| Crisis Level:", scenario$crisis_level, "\n")

  # Check for scenario end
  if (scenario$crisis_level >= 10) {
    cat("\n!!! CRISIS: Open conflict erupted !!!\n")
    break
  } else if (scenario$crisis_level <= 1) {
    cat("\n*** Crisis resolved peacefully ***\n")
    break
  }
}
```

## Research Applications

### Study Worldview Effects on Escalation

```r
# Run simulation with different worldview combinations
results <- list()

worldview_combos <- list(
  c("realist", "realist", "realist"),
  c("liberal_institutionalist", "liberal_institutionalist", "liberal_institutionalist"),
  c("realist", "liberal_institutionalist", "pragmatic_technocrat")
)

for (combo in worldview_combos) {
  # Create agents with this worldview combo
  # Run simulation
  # Track escalation metrics
}

# Compare: Do realist dyads escalate more?
```

### Measure Impact of Information Asymmetry

```r
# Symmetric information condition
agents_symmetric <- create_agents_with_access(c(0.8, 0.8, 0.8))

# Asymmetric information condition
agents_asymmetric <- create_agents_with_access(c(0.9, 0.5, 0.7))

# Compare outcomes - does information advantage prevent conflict?
```

### Analyze Deception Dynamics

```r
# Track deception over time
deception_log <- data.frame(
  turn = integer(),
  agent = character(),
  target = character(),
  attempted = logical(),
  successful = logical(),
  trust_after = numeric()
)

# Analyze patterns:
# - Who deceives most?
# - Does deception lead to worse outcomes?
# - Can trust recover after detected deception?
```

## Next Steps

1. **Integrate with LLM agents** - Use worldviews in prompts
2. **Implement action effects** - How actions change scenario state
3. **Add more scenarios** - Climate crisis, pandemic, cyber warfare
4. **Expand countries** - Add more regional actors
5. **Validate** - Compare to real-world crisis escalation patterns
