# Project Context for Claude

## System Version
**Current Version**: v3.6 (January 2026)

## Primary Language
- **R** - Main programming language for this project

## LLM Access
- **OpenRouter** - API access for multiple LLM models

## Project Overview: Multi-Agent Wargame Simulation

### Core Concept
Sophisticated multi-agent simulation with **15 actors** (5 Novaris, 6 Tethys, 4 external) across **entirely fictionalized countries** (Novaris, Tethys, Meridian, Aurelia, Valkoria, Sorentia). Features cognitive worldviews, information asymmetry, deception mechanics, trust dynamics, and dynamic trajectories. Each agent represents a specific role (military, government, economic, intelligence, diplomatic, political) with unique information access and cognitive biases.

**IMPORTANT: Complete Fictionalization**
All countries, organizations, and characters in this simulation are entirely fictional:
- **No real countries**: Novaris, Tethys, Meridian, Aurelia, Valkoria, Sorentia are invented nations
- **No real people**: All agent names and backstories are fictional characters
- **No real alliances**: "Meridian Alliance" is a fictional entity (not NATO, EU, etc.)
- **No real organizations**: "Global Council" replaces UN references
- This ensures the simulation explores dynamics without mapping to real-world events

**Key capability**: Agents execute **49 concrete actions** across 7 categories (Diplomatic, Intelligence, Economic, Military Posture, Covert Operations, Open Conflict, WMD) that have real consequences on simulation state (GDP, military strength, territory, crisis level).

### Central Research Question
**What is the probability that the government of the smaller power (Tethys) is toppled?**

### Key Innovation: Four-Layer Architecture
1. **Original Layer**: 15 role-based agents with hawk/dove personalities
2. **Cognitive Layer**: Worldviews (realist, liberal, nationalist, etc.), deception mechanics, information filtering, trust dynamics
3. **Scenario Layer**: Fictionalized countries with rich backgrounds, dynamic trajectories, information asymmetry
4. **Action Layer**: 49 executable actions with probabilistic outcomes and cascading state effects

## Simulation Architecture

### Participants (15 LLM Agents)

Each agent has a distinct **persona** defined by multiple trait dimensions:

#### Core Behavioral Traits
- **Hawk/Dove propensity** (0-1): Preference for aggressive vs. diplomatic approaches
- **Policy adherence** (0-1): Degree of alignment with official government policy
- **Objective alignment** (0-1): Level of agreement with their faction's central objectives

#### Rationality Components (Four Dimensions)
- **Cognitive Rationality** (0-1): Logical, data-driven decision-making vs. impulsive, emotional choices
  - High (0.8-1.0): Consistent, analytical, strong cost-benefit analysis
  - Low (0.0-0.3): Impulsive, emotional override, poor risk assessment
- **Paranoia** (0-1): Threat perception and trust levels
  - High (0.7-1.0): Sees threats everywhere, conspiracy thinking, extreme distrust
  - Low (0.0-0.2): Trusting, may miss real threats, optimistic bias
- **Behavioral Consistency** (0-1): Predictability and stability of actions
  - High (0.8-1.0): Predictable, follows patterns, reliable
  - Low (0.0-0.3): Chaotic, unpredictable, mood-driven
- **Emotional Volatility** (0-1): Strength of emotional reactions
  - High (0.7-1.0): Strong emotions override logic, dramatic reactions
  - Low (0.0-0.2): Cool, detached, unemotional decision-making

#### Cognitive & Information Traits
- **Worldview**: Ideological lens shaping interpretation of events
  - Types: realist, liberal_institutionalist, nationalist_populist, pragmatic_technocrat, constructivist, revolutionary_revisionist
  - **Faction-aware assignment (v3.3)**: Major power agents more likely to be realist/nationalist; smaller power more varied
- **Deception Capacity** (0-1): Skill at executing deception successfully
- **Deception Willingness** (0-1): Propensity to attempt deception
- **Information Access** (0-1): Quality and quantity of intelligence available
- **Analytical Capability** (0-1): Ability to process and interpret information effectively

#### Role-Specific Characteristics
- **Role**: Functional position (military, government, economic, intelligence, diplomatic, political)
- **Information Sources**: Role-specific access (e.g., signals_intelligence, battlefield_reports, diplomatic_cables)
- **Typical Biases**: Cognitive biases associated with role (e.g., "overweight military solutions", "domestic politics focus", "efficiency emphasis")

#### Major Power (Aggressor) - Novaris (5 agents)
**Central Objective**: Achieve territorial/political control over smaller power

Named character agents:
- **General Viktor Krasnov** (Military Chief): Ultra-hawk (0.92), realist worldview, volatile personality
- **Minister Dmitri Volkov** (Defense Minister): Moderate hawk (0.68), pragmatic_technocrat worldview, high policy adherence
- **Dr. Natasha Petrova** (Economic Advisor): Dove (0.25), liberal_institutionalist worldview, LOW policy adherence (0.50) - often dissents from official policy
- **Director Sergei Morozov** (Intelligence Director): Moderate hawk (0.58), realist worldview, high paranoia, hedges assessments
- **Deputy Minister Yuri Volkov** (Propaganda/Political): Ultra-hawk (0.95), revolutionary_revisionist worldview - true believer pushing escalation (v3.6)

#### Smaller Power (Defender) - Tethys (6 agents)
**Central Objective**: Preserve sovereignty and territorial integrity

Named character agents:
- **President Elena Marchetti** (Government): Moderate hawk (0.62), liberal_institutionalist worldview
- **General Olena Bondar** (Military Commander): High hawk (0.88), realist worldview
- **Minister Sofia Kovalenko** (Foreign Minister): Dove (0.32), liberal_institutionalist worldview
- **Viktor Zelenko** (Opposition Leader): Moderate (0.45), nationalist_populist worldview, LOW policy adherence - unpredictable
- **Director Maksym Savchenko** (Intelligence Director): Hawk (0.72), realist worldview, high paranoia - advocates covert operations (v3.6)
- **Minister Taras Moroz** (Economic Advisor): Dove (0.28), pragmatic_technocrat worldview - warns about economic sustainability (v3.6)

#### External Forces (4 Independent Actors)
- **Allied Defender (Meridian)**: Moderate hawk, supports smaller power (Tethys), provides military/economic aid
  - Acts independently as separate faction
  - Makes own action decisions each period
- **Allied Aggressor (Valkoria)**: Moderate-high hawk, supports major power (Novaris), provides diplomatic cover and economic support
  - Acts independently as separate faction
  - Makes own action decisions each period
- **Neutral Regional Power (Aurelia)**: Dove, seeks mediation, prioritizes stability
  - Acts independently as separate faction
  - Makes own action decisions each period
- **International Organization (Global Council)**: Dove, policy-driven, humanitarian focus
  - Acts independently as separate faction
  - Makes own action decisions each period
  - Representative: Isabella Cardenas (Sorentian diplomat with Austrani/Palomar experience)

**Key Change (v3.1.1)**: External actors no longer coordinate as a single "external" faction. Each pursues their own interests independently while engaging diplomatically with other factions.

**Key Changes (v3.5)**: Rich narrative backstories, named character personas, dynamic action selection (all 49 actions available), interpersonal deception mechanics, and enhanced faction dynamics. See version history at end of document.

### External Influences
Dynamic factors that affect the simulation:
- Geopolitical events
- Commodity prices (oil, gas, wheat, etc.)
- International sanctions
- Military aid flows
- Economic conditions
- Public opinion shifts

### Scenario Configuration (v3.6)
Five configurable scenario presets determine initial conflict intensity:

| Scenario | Territory Captured | Crisis Level | Military Balance | Description |
|----------|-------------------|--------------|------------------|-------------|
| **pre_invasion** | 0% | 5/10 | -0.15 to 0.0 | Troops massed, ultimatums issued, invasion NOT yet occurred (v3.6) |
| **low_intensity** | 2-5% | 7/10 | -0.1 to 0.0 | Limited border incursion, probing actions |
| **medium_intensity** | 5-12% | 9/10 | -0.3 to -0.1 | Full-scale invasion (DEFAULT) |
| **high_intensity** | 15-25% | 10/10 | -0.5 to -0.3 | Total war, cities under siege |
| **stalemate** | 8-15% | 6/10 | -0.1 to 0.1 | Frozen conflict, stable frontlines |

Scenarios determine initial GDP, military strength, sanctions levels, and crisis intensity.

**Pre-Invasion Scenario (v3.6)**: The `pre_invasion` preset enables simulating the crisis escalation phase before any shots are fired. Invasion is emergent - it may or may not happen based on agent decisions. This allows for richer exploration of deterrence, diplomacy, and escalation dynamics.

## Simulation Flow

### 1. Initialization (t=0)
- **Triggering Event**: Invasion by major power
- Establish initial conditions for all agents
- Set baseline parameters for external forces

### 2. Time-Discrete Simulation Loop (t0 → t1 → t2 → ...)

Each time period:
1. **External Events**: Random or scheduled geopolitical/economic events
2. **Pre-Action Coordination** (v3.1): Agents within each faction discuss and debate what action to take
   - **Multi-agent factions** (major_power, small_power): Internal team debate
     - Intelligence directors brief on threats and opportunities
     - Military commanders recommend military options
     - Economic advisors warn about costs
     - Foreign ministers suggest diplomatic alternatives
     - Two rounds of discussion before leader decides
   - **Single-agent factions** (meridian, valkoria, aurelia, international_org): Skip to decision
     - No internal debate needed (single agent represents entire faction)
   - **Crisis Override Mechanic (v3.3)**: In high crisis (level 8+), military leaders may override civilian decision-makers
     - Override probability based on: crisis severity, hawk differential between military and government
     - Reflects realistic civil-military dynamics during existential threats
3. **Action Decision & Execution**: **All 6 factions take concrete actions**
   - **major_power** (Novaris) → Takes 1 action (e.g., full_scale_attack, economic_sanctions)
   - **small_power** (Tethys) → Takes 1 action (e.g., military_buildup, peace_talks)
   - **meridian** (Allied Defender) → Takes 1 action (e.g., financial_aid to Tethys, joint_exercises)
   - **valkoria** (Allied Aggressor) → Takes 1 action (e.g., diplomatic_visit to Novaris, trade_agreement)
   - **aurelia** (Neutral Power) → Takes 1 action (e.g., mediation_offer, humanitarian_aid)
   - **international_org** (UN/EU) → Takes 1 action (e.g., peace_talks, economic_sanctions)
   - **Total: 6 actions executed per period**
4. **Action Execution Results**: Actions take effect with real consequences
   - GDP changes, military strength adjustments, territory shifts
   - Crisis level updates, sanctions impacts
   - Detection/exposure of covert operations
   - Attrition from combat operations (asymmetric based on outcome)
   - **Economic sustainability (v3.3)**: GDP below thresholds triggers military capability degradation
   - **International support effects (v3.3)**: Aid and condemnation now modify state variables
5. **Post-Action Discussion**: Agents react to results and coordinate responses
   - Intra-faction coordination (review outcomes)
   - Inter-faction negotiation (respond to opponent actions)
   - External engagement (all external actors engage every period - v3.1.2)
6. **Aggregator Resolution**: Separate LLM evaluates central question
   - Is the smaller power's government still in existence?
   - Calculate probability of government collapse
7. **State Update**: Update conditions for next period
   - Archive all interaction data from this period
   - Update agent states based on interactions and events

### 3. Period Summary
After each discrete time period:
- Summary of key dynamics
- Agent decisions and interactions
- Impact of external events
- Updated probability assessment

### 4. Iteration
- External/internal events trigger new dynamics
- Agents respond to changed conditions
- Aggregator re-evaluates central question
- Continue until simulation end or resolution

## Action System (v3.2)

### 49 Executable Actions Across 7 Categories

#### 1. DIPLOMATIC (6 actions)
`diplomatic_visit`, `peace_talks`, `trade_negotiation`, `cultural_exchange`, `humanitarian_aid`, `mediation_offer`
- Build relationships, negotiate settlements, improve trust
- Example effects: Trust +0.05, Crisis -1, Relations improved

#### 2. INTELLIGENCE (5 actions)
`intelligence_gathering`, `surveillance_operation`, `counterintelligence`, `spread_disinformation`, `propaganda_campaign`
- Collect information, deceive opponents, shape narratives
- **Detection risk**: Covert intelligence can be exposed, damaging trust (-0.3 to -0.5)

#### 3. ECONOMIC (6 actions)
`trade_agreement`, `economic_sanctions`, `financial_aid`, `resource_embargo`, `currency_manipulation`, `cyber_theft`
- Impose costs, provide support, economic warfare
- Example effects: Sanctions → Target GDP -15%, Actor GDP -4.5% (blowback)

#### 4. MILITARY POSTURE (6 actions)
`military_buildup`, `naval_deployment`, `air_patrols`, `troop_movements`, `joint_exercises`, `arms_development`
- Build capabilities, signal resolve, prepare for conflict
- Example effects: Military strength +0.05, Cost $5B, Crisis +1

#### 5. COVERT OPERATIONS (6 actions - HIGH RISK)
`sabotage`, `assassination_attempt`, `regime_destabilization`, `proxy_support`, `false_flag_operation`, `cyber_attack`
- Disrupt enemy operations, undermine governments, deniable attacks
- **High detection risk**: If exposed → severe diplomatic consequences, trust collapse

#### 6. OPEN CONFLICT (6 actions - KINETIC)
`border_incursion`, `limited_strike`, `full_scale_attack`, `occupation`, `blockade`, `siege_warfare`
- Direct military action with immediate consequences
- **Attrition modeling**: Combat reduces both sides' military capabilities
- **Economic costs**: Military operations drain GDP significantly

#### 7. WMD (5 actions - EXTREME)
`nuclear_development`, `chemical_weapons`, `biological_program`, `tactical_nuclear_use`, `strategic_nuclear_strike`
- Ultimate escalation options
- Example effects: Nuclear use → Crisis = 10, International condemnation, unpredictable escalation

### Action Execution Mechanics
- **Probabilistic outcomes**: Success rates based on capabilities, force ratios, information access
- **Military balance integration (v3.3)**: Combat success modified by current military balance (+/-15%)
- **Asymmetric attrition (v3.3)**: Winners lose less (2%) than losers (5-6%) in combat
- **Economic costs applied (v3.3)**: Action costs (e.g., $5B for military_buildup) deducted from faction GDP
- **Cascading effects**: Actions affect multiple state variables (GDP, military strength, territory, crisis level, sanctions)
- **Dynamic state tracking**: All effects logged and carried forward to next period
- **State history (v3.3)**: Complete period-by-period snapshots stored for analysis
- **Detection risk**: Covert actions can fail and expose the actor, damaging trust and reputation
- **Diminishing returns (v3.3)**: Repeated peace_talks have reduced effectiveness (15% reduction per attempt, minimum 10%)

## Technical Components

### Required Modules
1. **Agent Framework**: Individual LLM agents with distinct roles/perspectives
   - Persona definitions (hawk/dove, policy adherence, objective alignment, rationality components)
   - Cognitive traits (worldview, deception capabilities, information access, analytical ability)
   - Rationality system (cognitive rationality, paranoia, behavioral consistency, emotional volatility)
   - **Trust dynamics**: Deception damages trust, cooperation builds trust, trust affects information sharing
   - **Information filtering**: Agents perceive events through worldview lens (realists see threats, liberals see cooperation opportunities)
   - Role-specific constraints, biases, and decision-making authority
   - Internal consistency mechanisms for agent behavior
2. **Action Execution System** (v3.3): Execute 49 actions with real consequences
   - Probabilistic success/failure based on capabilities and military balance
   - State updates (GDP, military, territory, crisis, sanctions)
   - Attrition modeling with asymmetric outcomes (winner/loser differentiation)
   - Economic cost deduction from faction GDP
   - Detection mechanics for covert operations
   - Diminishing returns for repeated diplomatic actions
3. **External Event Generator**: Inject realistic geopolitical/economic shocks
4. **Interaction Engine**: Facilitate communication and decision-making among agents
   - **Pre-action coordination** (v3.1): Agents within same faction discuss before deciding actions (2 rounds)
   - **Intra-faction coordination**: Agents within same power coordinate responses
   - **Inter-faction negotiation/conflict**: Across powers (Novaris ↔ Tethys)
   - **External engagement**: Independent external actors engage with primary combatants
   - **Information sharing and strategic messaging**: Intelligence, deception, propaganda

   **Detailed Pre-Action Coordination Flow (v3.5)**:

   The `run_pre_action_coordination()` function orchestrates intra-faction debate before each period's action decision. Here's the complete flow:

   ```
   ┌─────────────────────────────────────────────────────────────────┐
   │                    PRE-ACTION COORDINATION                      │
   │                  (run_pre_action_coordination)                  │
   └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ SETUP: Build context for all agents                            │
   │ - Generate dynamic action options (all 49 actions)             │
   │ - Format situation summary (filtered by worldview/paranoia)    │
   │ - Get faction perspective from backstories                     │
   │ - Prepare recent events summary                                │
   └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ ROUND 1: INITIAL POSITIONS                                     │
   │                                                                 │
   │ Each agent receives prompt including:                          │
   │ - Character identity (name, hawk/dove, worldview)              │
   │ - Full persona description and speech style                    │
   │ - Covert capability assessment                                 │
   │ - Interpersonal dynamics instructions (if low policy adherence)│
   │ - Situation summary + recent events                            │
   │ - Full action catalog with costs and effects                   │
   │                                                                 │
   │ Agent must provide:                                            │
   │ 1. RECOMMENDED ACTION: exact action name                       │
   │ 2. RATIONALE: 2-3 sentences in character voice                 │
   │ 3. RISKS: key concerns from their perspective                  │
   │ 4. ALTERNATIVE CONSIDERED: what they rejected and why          │
   └─────────────────────────────────────────────────────────────────┘
                                    │
           All agents submit initial positions
                                    │
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ ROUND 2: STRUCTURED DEBATE                                     │
   │                                                                 │
   │ Each agent receives:                                           │
   │ - All Round 1 positions (with hawk/dove/worldview labels)      │
   │ - Identity of most different colleague (by hawk_dove score)    │
   │ - Faction dynamics reminder ("Not everyone is being honest")   │
   │ - Manipulation instructions (if applicable)                    │
   │                                                                 │
   │ Agent must:                                                    │
   │ 1. AGREEMENT: Name one colleague they support                  │
   │ 2. DISAGREEMENT: Directly challenge the most different view    │
   │ 3. FINAL RECOMMENDATION: May change or hold firm               │
   │ 4. WARNING: Consequences of following the opposed approach     │
   │                                                                 │
   │ Character-specific instructions:                               │
   │ - Hawks: Push back against peace_talks, explain why diplomacy  │
   │          is dangerous                                          │
   │ - Doves: Warn about escalation costs, defend diplomatic paths  │
   │ - Moderates: Synthesize but maintain clear position            │
   └─────────────────────────────────────────────────────────────────┘
                                    │
           Coordination record saved to state
                                    │
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ DECISION MAKER SELECTION                                       │
   │                                                                 │
   │ Normal priority: government > military > intelligence > other  │
   │                                                                 │
   │ Crisis Override (v3.3): In high crisis (>=8):                  │
   │ - Check if military is more hawkish than government            │
   │ - Override probability = (crisis-7) * 0.15 * hawk_differential │
   │ - If override: military takes decision authority               │
   └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ FINAL ACTION DECISION                                          │
   │ (agent_decide_action with coordination input)                  │
   │                                                                 │
   │ Decision maker receives:                                       │
   │ - Full action decision prompt (all 49 actions)                 │
   │ - Round 2 positions from all colleagues                        │
   │ - Their own character context and backstory                    │
   │ - Personal agenda instructions (if applicable)                 │
   │                                                                 │
   │ Note: Decision maker "considers" team input but final          │
   │ choice reflects their own worldview and personality            │
   └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ ACTION EXECUTION                                               │
   │ (execute_agent_decision → execute_action)                      │
   │                                                                 │
   │ - Probabilistic success based on capabilities                  │
   │ - State updates (GDP, military, territory, crisis)             │
   │ - Attrition if combat action                                   │
   │ - Detection check if covert action                             │
   │ - Results logged to state$action_results                       │
   └─────────────────────────────────────────────────────────────────┘
   ```

   **Key Design Principles**:
   - **Character-driven debate**: Agents argue from their defined perspectives, not generically
   - **Genuine disagreement**: Hawks and doves are instructed to oppose each other's recommendations
   - **Interpersonal dynamics**: Low-adherence agents may manipulate the discussion
   - **Crisis dynamics**: High crisis can shift power from civilians to military
   - **Information asymmetry**: Agents see the situation through their worldview filters
5. **Aggregator LLM**: Separate evaluator for probability assessment
6. **State Manager**: Track simulation state across time periods
   - **Dynamic state variables**: GDP, military strength, territory controlled, crisis level, sanctions level, nuclear usage
   - **Capability tracking**: Military and economic capabilities updated each period based on actions
7. **Logging System**: Record all interactions, decisions, and outcomes
   - **Full interaction transcripts**: Complete record of all agent-to-agent communications
   - **Agent position evolution**: Track how individual stances change over time
   - **Faction cohesion metrics**: Measure internal alignment within each power
   - **Influence patterns**: Map who influences whom and how
   - **Decision provenance**: Link decisions to specific interactions and information
   - **Action history**: Complete log of all actions taken and their effects

### State Tracking Variables

The simulation dynamically tracks multiple state dimensions:

```r
scenario_state <- list(
  crisis_level = 0-10,              # Current crisis intensity
  military_balance = -1 to 1,       # Negative = aggressor advantage
  sanctions_level = 0-1,            # International sanctions severity
  territory_controlled = 0-1,       # Proportion under aggressor control
  nuclear_used = TRUE/FALSE         # Whether WMD threshold crossed
)

faction_capabilities <- list(
  major_power_military = 0.6-2.0,   # Updated by actions/combat
  small_power_military = 0.3-1.0,   # Subject to attrition
  major_power_gdp = 50-150B,        # Affected by sanctions/costs
  small_power_gdp = 15-50B,         # Economic warfare impact
  external_support = 0-1            # Aid from allies
)

trust_levels <- matrix()            # Agent-to-agent trust (0-1)
                                    # Damaged by deception, built by cooperation
```

### Key Design Considerations
- Agents should have realistic information asymmetries
- Decision-making should reflect role-appropriate constraints and incentives
- **Persona consistency**: Agent behavior should align with their hawk/dove orientation and policy adherence
- **Internal faction dynamics**: Agents within same power may disagree based on objective alignment
- **Policy vs. personal objectives**: Low policy adherence agents may pursue divergent goals
- **Interpersonal deception (v3.5)**: Agents with low policy adherence may selectively present information, build coalitions against leadership, or frame discussions to advance personal agendas
- **Trust dynamics**: Successful deception damages trust; exposed deception severely damages trust and reputation
- **Information filtering**: Worldviews shape perception (realists emphasize threats, liberals emphasize cooperation)
- **Action consequences**: All actions have real effects on state variables, creating path dependencies
- External events should be plausible and impact-weighted
- Aggregator should be isolated from agent-level reasoning
- Time periods should be meaningful intervals (days, weeks, months)

### Agent Persona Examples

**High Hawk + Low Policy Adherence + High Paranoia** (e.g., rogue general):
- Pushes for aggressive action beyond official policy
- Sees threats everywhere, may advocate preemptive strikes
- May undermine diplomatic efforts
- Creates tension within own faction

**Dove + High Objective Alignment + High Cognitive Rationality** (e.g., smaller power's foreign minister):
- Strongly committed to sovereignty
- Seeks diplomatic solutions that preserve independence through logical negotiation
- May clash with military hawks on tactics, not goals
- Data-driven approach to international relations

**Moderate Position + Low Objective Alignment + Low Behavioral Consistency** (e.g., opportunistic economic advisor):
- Questions overall strategic direction
- Advocates for compromise or de-escalation inconsistently
- Unpredictable positions based on personal/political calculations
- Creates internal policy debates and friction

**High Hawk + Low Cognitive Rationality + High Emotional Volatility** (e.g., nationalist political leader):
- Makes impulsive, emotion-driven decisions
- Sudden escalations based on perceived slights
- Poor cost-benefit analysis, overconfident in military solutions
- Charismatic but unstable influence on policy

**Intelligence Director + High Paranoia + High Analytical Capability** (professional archetype):
- Expert at deception and counter-intelligence
- Sees worst-case scenarios everywhere
- Methodical analysis but through lens of extreme distrust
- May advocate overly defensive or preemptive actions

## Output Requirements

### Primary Outputs
- Time-series probability estimates for government collapse
- Final forecast with confidence intervals

### Interaction Data
- **Complete interaction logs**: All agent-to-agent communications with timestamps
  - Message content (questions, statements, proposals)
  - Sender and recipient(s)
  - Communication channel (formal meeting, backchannel, public statement)
  - Response patterns and timing
- **Interaction network analysis**:
  - Frequency of communication between agent pairs
  - Direction of influence (who convinces whom)
  - Formation of coalitions or alliances
  - Isolation or exclusion patterns

### Analytical Outputs
- Summary of key agent dynamics per period
- Event timeline and impact assessment
- Agent position trajectories (hawk/dove shifts over time)
- Faction coherence measures (internal agreement levels)
- Critical decision points and their interaction precursors

### Human Forecasting Outputs (NEW)
- **Forecasting prompts**: Period-by-period summaries for human participants
  - Initial scenario information (Period 1)
  - Cumulative event and interaction summaries (Period 2+)
  - Previous LLM forecast for reference
  - Structured question format for probability estimates
- **Answer key**: LLM aggregator forecasts with confidence and reasoning
- **Comparison data**: Side-by-side LLM vs human forecast analysis
- **CSV template**: Easy data entry for multiple human forecasters

## Data Storage Structure

### Interaction Database Schema
```
interactions/
├── period_1/
│   ├── interaction_001.json  # {timestamp, sender, recipient(s), message, type}
│   ├── interaction_002.json
│   └── ...
├── period_2/
│   └── ...
└── period_n/
```

### Agent State Tracking
```
agent_states/
├── agent_name_timeline.csv  # {period, hawk_dove, policy_adherence, objective_alignment,
│                            #  cognitive_rationality, paranoia, behavioral_consistency,
│                            #  emotional_volatility, key_positions}
└── ...
```

### Network Metrics
```
networks/
├── period_1_network.csv  # {agent_A, agent_B, interaction_count, influence_direction, sentiment}
└── ...
```

### Interaction CSV Files (v3.5)
All agent interactions are automatically saved to CSV files for analysis:

```
output/interactions/
├── period_01_coordination.csv     # Pre-action faction debates
│   # Columns: period, faction, topic, round, timestamp, sender_name,
│   #          sender_role, hawk_dove, policy_adherence, objective_alignment,
│   #          worldview, content
├── period_01_actions.csv          # Action decisions and results
│   # Columns: period, faction, agent_name, agent_role, timestamp,
│   #          action, target, reasoning, expected_outcome, success, result_message
├── period_01_interactions_summary.csv  # Interaction metadata
│   # Columns: period, session_id, interaction_id, timestamp, type,
│   #          topic, participants, participant_factions, n_messages, duration_seconds
├── period_01_interactions_messages.csv # Full message content
│   # Columns: period, session_id, interaction_id, interaction_type,
│   #          message_id, timestamp, sender_id, sender_name, sender_faction,
│   #          exchange_number, content
├── period_02_*.csv                # Same structure for each period
├── ...
├── all_coordination.csv           # Combined from all periods
├── all_actions.csv                # Combined from all periods
├── all_interactions_summary.csv   # Combined from all periods
└── all_interactions_messages.csv  # Combined from all periods
```

Key functions:
- `save_coordination_to_csv()`: Saves pre-action coordination debates
- `save_actions_to_csv()`: Saves action decisions and execution results
- `save_interactions_to_csv()`: Saves inter-faction interactions
- `combine_all_csvs()`: Merges all period files into master files

### State Tracking
```
state_history/
├── capabilities_timeline.csv     # GDP, military strength by faction over time
├── territory_timeline.csv        # Territory control progression
├── crisis_timeline.csv           # Crisis level and sanctions evolution
├── action_history.csv            # All actions taken with outcomes
└── trust_matrix_period_N.csv    # Agent trust levels each period
```

## Research Applications

### LLM vs Human Forecasting (IMPLEMENTED)
- **Direct comparison**: Human participants make same forecasts as LLM aggregator
- **Information parity**: Humans receive same period summaries as LLM
- **Structured collection**: Automated prompt generation and data templates
- **Metrics**: MAE, correlation, Brier scores, calibration analysis
- **Research questions**:
  - Do LLMs forecast better than domain experts?
  - How do humans vs LLMs process new information?
  - Which is better calibrated?
  - Does aggregating multiple humans beat single LLM?

### Action System Research (NEW)
- **Escalation dynamics**: What triggers nuclear threshold crossing? Can conflicts de-escalate?
- **Action effectiveness**: Do covert operations achieve goals better than open conflict?
- **Economic pressure**: Can sanctions prevent military escalation?
- **Diplomatic efficacy**: How effective is diplomacy after violence begins?
- **Worldview-action correlation**: Do realists choose military actions more often? Do liberals prefer economic/diplomatic tools?
- **Detection consequences**: How does exposure of covert operations affect trust and future cooperation?

### Future Considerations
- Calibration against historical conflicts (real Russia-Ukraine data)
- Sensitivity analysis on initial conditions (scenario presets enable this)
- Comparison across different LLM models
- Multiple simulation scenarios for robustness (4 presets implemented)
- Natural language processing of interaction content for sentiment/stance extraction
- Network centrality analysis to identify key influencers
- Temporal analysis of coalition formation and dissolution
- Expert vs novice human forecaster comparison
- Incentivized forecasting tournaments
- Trust network evolution analysis
- Path dependency analysis (how early actions constrain later options)

---

## Version History

### v3.6 (January 2026) - Action Diversity, New Agents & Pre-Invasion Scenarios

#### New Agents (15 total)
Three new agents added to enrich faction dynamics:

- **Deputy Minister Yuri Volkov** (Novaris Propaganda/Political)
  - Ultra-hawk (0.95), revolutionary_revisionist worldview
  - True believer pushing for escalation, information warfare, false flag operations
  - Creates tension with more cautious Morozov and Petrova

- **Director Maksym Savchenko** (Tethys Intelligence)
  - Hawk (0.72), realist worldview, high paranoia
  - Vindicated prophet who warned of invasion, advocates aggressive covert operations
  - Fills gap in Tethys intelligence capability

- **Minister Taras Moroz** (Tethys Economic Advisor)
  - Dove (0.28), pragmatic_technocrat worldview
  - Warns about economic sustainability, insists on facing resource reality
  - Creates hawk/dove tension around war economy sustainability

#### Action Diversity Improvements
Four fixes to address limited action variety observed in simulations:

- **Fix A: Previous Period Actions in Context** (`agent_decision.R`)
  - New `format_previous_actions()` function provides agents with memory of recent actions
  - Shows actions from last 3 periods with success/failure status
  - Highlights own faction's action history for strategic continuity
  - Enables more informed, varied decision-making

- **Fix B: Role-Based Perspective (Softened)** (`agent_decision.R`)
  - `get_role_action_guidance()` now DESCRIPTIVE not prescriptive
  - Describes what expertise each role brings without mandating action choices
  - Acknowledges roles can recommend outside their domain based on circumstances
  - Hawk/dove framing softened to "tendency" not requirement

- **Fix C: Anti-Repetition (Observational)** (`agent_decision.R`)
  - Changed from warnings to neutral observations
  - Now shows: "Repeated actions: X (2x), Y (3x). (Note: Some actions benefit from repetition; others may have diminishing effects or become predictable.)"
  - Lets agents decide if repetition is strategic vs problematic

- **Fix E: External Actor Variety Pressure** (`interaction_engine.R`)
  - Enhanced `generate_dynamic_action_options()` for external actors
  - Faction-specific guidance for strategic interests
  - Notes about diminishing returns without prescribing behavior

#### External Actor Drift Mechanics (NEW)
External actors can now shift their positions based on how the conflict develops:

- **Drift Parameters** added to external actors in `config.R`:
  - `base_alignment`: Starting position (pro_tethys, pro_novaris, neutral)
  - `alignment_strength`: How committed (higher = more stable)
  - `drift_sensitivity`: How responsive to events
  - Trigger lists for what could shift alignment

- **New `calculate_alignment_drift()` function** (`agent_decision.R`)
  - Analyzes state and recent events for drift triggers
  - Considers: crisis level, territory changes, sanctions, nuclear use, atrocities
  - Generates context about "shifting dynamics" for agent prompts
  - Drift is suggestive, not deterministic - agents still choose

- **Example drift scenarios**:
  - Meridian might face pressure to reduce support if Tethys suffers major defeats
  - Valkoria might distance from Novaris if costs become too high
  - Aurelia's neutrality could shift toward either side based on events
  - International org might become more assertive after atrocities

#### Pre-Invasion Scenario Support
New scenario preset for simulating crisis escalation before invasion:

- **New `pre_invasion` scenario preset** (`config.R`)
  - Territory: 0% captured (no invasion yet)
  - Crisis level: 5/10 (elevated but not maximum)
  - Military balance: -0.15 to 0.0 (advantage but not overwhelming)
  - Sanctions: 10% (warning shots only)
  - `is_pre_invasion = TRUE` flag for conditional behavior

- **Scenario-Adaptive Context** (`agent_decision.R`)
  - New `get_scenario_context()` function provides different framing
  - Pre-invasion: "War has NOT yet begun... Invasion is POSSIBLE but NOT INEVITABLE"
  - Active war: "The invasion is ONGOING. Territory has been captured..."
  - Adjusts agent role descriptions for pre-war vs wartime decisions

- **Pre-Invasion Faction Perspectives** (`scenario_backstories.R`)
  - New `FACTION_PERSPECTIVES_PRE_INVASION` list
  - All 6 factions have distinct pre-war framing
  - Major power: "All options remain on the table: invasion, continued pressure, or negotiation"
  - Small power: "The primary goal is preventing invasion while preserving sovereignty"
  - External actors focus on deterrence, mediation, and preventing escalation

- **Conflict Summary Adaptation** (`scenario_backstories.R`)
  - `get_conflict_summary()` now accepts `is_pre_invasion` parameter
  - Pre-invasion: "CURRENT STATUS: PRE-INVASION CRISIS - The invasion has NOT yet occurred..."
  - Provides context for agents about what choices remain available

#### Files Modified
- `src/agent_decision.R`: Previous actions context, role guidance, scenario context, pre-invasion support
- `src/interaction_engine.R`: External actor variety pressure, pre-invasion faction perspective
- `src/scenario_backstories.R`: Pre-invasion faction perspectives, adapted conflict summary
- `config.R`: New `pre_invasion` scenario preset, `is_pre_invasion` flag on all presets

---

### v3.5 (January 2026) - Rich Narratives, Character Personas & Interpersonal Dynamics

#### Rich Narrative Backstories
- **New file `src/scenario_backstories.R`**: 850+ lines of narrative content
  - `CONFLICT_HISTORY`: Detailed 3-century Novaris-Tethys relationship (Great Sundering, Soviet era, Independence, current invasion)
  - `VALKORIA`: Complete country definition (previously missing)
  - `AGENT_BACKSTORIES`: Full character profiles for all 12 agents with:
    - Personal history and career trajectory
    - Formative experiences shaping worldview
    - Key relationships with other agents
    - Speech patterns and communication style
    - Hidden motivations and personal stakes
  - `FACTION_PERSPECTIVES`: How each faction frames the conflict
  - Helper functions: `get_agent_backstory()`, `get_faction_perspective()`, `format_backstory_for_prompt()`

#### Named Character Personas
- **Agents now have names, not just roles**: "General Viktor Krasnov" not "Military Chief of Staff"
- **Enhanced `config.R`** with naturalistic persona definitions:
  - `backstory_id`: Links to full backstory in scenario_backstories.R
  - `speech_style`: How the agent communicates ("blunt military language", "diplomatic hedging")
  - `typical_arguments`: Arguments the character naturally makes
  - `description`: Full prose character description (not just trait numbers)

#### Dynamic Action Selection
- **All 49 actions now available** to all factions (was 6-8 hardcoded)
- **New function `generate_dynamic_action_options()`** in `interaction_engine.R`:
  - Context-sensitive action recommendations based on crisis level, military balance
  - Faction-specific strategic guidance (aggressor vs defender vs external)
  - Full action catalog with costs, risks, and expected effects
  - Situational analysis helping agents choose appropriate actions

#### Interpersonal Deception Mechanics
- **Personal agendas**: Agents with low policy_adherence (<0.5) receive instructions to:
  - Emphasize information supporting their preferred approach
  - Downplay contradictory information
  - Build coalitions against leadership's preferred course
  - Frame discussions to advance personal narratives
- **Role-specific manipulation**:
  - Intelligence agents: Hedge assessments, maintain ambiguity, protect themselves
  - Government figures: Steer toward politically safe options
  - Opposition: Balance national vs political interests, may use crisis for positioning
  - Economic advisors: Emphasize worst-case scenarios to force attention

#### Enhanced Faction Dynamics in Coordination
- **Round 2 prompts** explicitly note: "Not everyone is being fully honest - some may emphasize information that supports their preferred outcome"
- **Manipulation instructions** added based on policy adherence and role
- **Conflict-driven debate**: Hawks instructed to push back against peace_talks; doves warned about escalation
- **NA option**: Agents can respond "NA" for agreement/disagreement/warning if they genuinely have nothing to add

#### Complete Fictionalization
- **Isabella Cardenas** (Sorentian diplomat) replaces Brazilian reference
- **Sorentia**: New fictional Southern Hemisphere country with diplomatic neutrality tradition
- **Austrani and Palomar**: Fictional regions with conflict history for diplomat's experience
- All references to real-world entities (NATO, UN, etc.) replaced with fictional equivalents

#### CSV Export System
- **All interactions automatically saved to CSV** for analysis
- Per-period files: coordination, actions, interaction summaries, full messages
- Combined master files: `all_coordination.csv`, `all_actions.csv`, etc.
- Functions: `save_coordination_to_csv()`, `save_actions_to_csv()`, `save_interactions_to_csv()`, `combine_all_csvs()`

#### Files Modified
- `src/scenario_backstories.R`: NEW FILE - 850+ lines of narrative content
- `config.R`: Named characters, speech styles, typical arguments, rebalanced worldviews
- `src/interaction_engine.R`: Dynamic action generation, enhanced coordination prompts, interpersonal dynamics
- `src/agent_decision.R`: Backstory integration, personal agenda sections, deception awareness
- `src/fictionalized_scenarios.R`: Added Valkoria country definition

---

### v3.4 (January 2026) - Cognitive Integration & Symmetric Events

#### Worldview-Filtered Situation Perception
- **Agents now see the world through their worldview lens**: The `format_situation_for_agent()` function applies worldview-specific interpretations
  - **Realists**: See military balance as more threatening ("DANGEROUS - enemy has significant advantage")
  - **Liberal institutionalists**: See opportunities for negotiation ("Balanced - ideal conditions for talks")
  - **Nationalist populists**: See any adversary advantage as existential ("ENEMY ADVANCING - national survival at stake")
  - **Pragmatic technocrats**: Focus on exact numbers and GDP impact estimates

#### Paranoia Affects Threat Perception
- **High paranoia (>0.7)**: Amplifies perceived crisis level by 25%, territory losses labeled "UNACCEPTABLE"
- **Low paranoia (<0.3)**: Underestimates crisis by 15%, situation seen as "manageable"

#### Enhanced Agent Prompts
- Agent prompts now include full worldview descriptions, role-specific expertise, and cognitive style
- Response constraints enforce brief, policy-focused output (2-4 paragraphs)
- Explicit instructions to disagree when proposals conflict with agent's orientation

#### Structured Debate in Coordination
- Round 1: Agents provide structured recommendations (ACTION, RATIONALE, RISKS, ALTERNATIVES)
- Round 2: Agents must respond to colleagues with different views, explicitly naming disagreements
- Hawks challenged to explain why negotiations are risky; doves warned to address escalation concerns

#### Adversarial Inter-Faction Negotiations
- Negotiations explicitly framed as adversarial with conflicting interests
- Agents instructed to make demands, probe for information, and refuse weak positions
- Response prompts force counter-proposals rather than agreement

#### Symmetric External Events (50/50)
- **Shock events rebalanced**: 8 defender-favorable events, 8 aggressor-favorable events
- **50-50 random selection** ensures neither side is systematically favored
- New defender-favorable events: Allied Support Surge, Defender Counteroffensive Success, Aggressor Economic Crisis, Aggressor Alliance Fractures
- New aggressor-favorable events: Aggressor Breakthrough, Defender Economic Crisis

#### Symmetric Config Events
- External events in `config.R` now balanced between defender/aggressor favorable
- Added `favors` field to track event direction

#### Files Modified
- `src/agent_system.R`: Enhanced prompts with worldview, role expertise, cognitive style, response constraints
- `src/agent_decision.R`: Worldview filtering in situation perception, paranoia affects threat perception, rationality trait access fixed
- `src/interaction_engine.R`: Structured debate format, adversarial negotiation framing
- `src/event_generator.R`: Symmetric shock events (50/50), balanced diplomatic events
- `config.R`: Balanced external event types

---

### v3.3 (January 2026) - Realism Enhancements

#### Worldview & Cognitive Diversity
- **Faction-aware worldview assignment**: Major power agents now more likely to receive `realist` or `nationalist_populist` worldviews; smaller power agents receive more varied worldviews reflecting defensive/diplomatic orientation
- **Lowered rationality for key agents**: Ultra-hawks (-20% rationality, +15% volatility), major power government (-15% rationality, +10% paranoia), political opposition (-15% rationality, +20% volatility, -30% consistency)
- **Added `revolutionary_revisionist` worldview** to the six available types

#### Combat & Attrition Mechanics
- **Military balance integration**: Combat success probability now modified by current military balance (±15% based on faction advantage)
- **Asymmetric attrition**: Combat outcomes differentiate winner/loser losses:
  - Successful attacker: 2% attrition (vs 5% for defender)
  - Failed attacker: 6% attrition (vs 2% for successful defender)

#### Economic Realism
- **Action costs applied to GDP**: Military operations and other costly actions now deduct `cost_billions` from faction GDP
- **Economic sustainability checks**: GDP falling below threshold ($50B for major power, $15B for smaller power) triggers military capability degradation (2% per period)
- **International support effects**: Financial aid and international condemnation now modify state variables (GDP, sanctions)

#### Decision-Making Dynamics
- **Crisis override mechanic**: In high crisis (level 8+), military leaders can override civilian decision-makers based on crisis severity and hawk/dove differential
- **Action costs in decision prompt**: Agents now see estimated costs and effects when choosing actions
- **Diminishing returns for peace_talks**: Each peace_talks attempt reduces effectiveness by 15% (minimum 10% effectiveness); high crisis further reduces efficacy

#### State Tracking
- **State history tracking**: Complete period-by-period snapshots stored in `state$state_history` for analysis
- **Peace talks counter**: Tracks cumulative diplomatic attempts for diminishing returns calculation

#### Files Modified
- `src/integrated_agent_system.R`: Worldview assignment, rationality adjustments
- `src/action_execution.R`: Military balance, attrition, diminishing returns
- `src/simulation_with_actions.R`: State history, economic costs, sustainability checks
- `src/agent_decision.R`: Crisis override, action costs in prompt
- `src/interaction_engine.R`: Fixed agent list combination (c() → list())

### v3.2 (January 2026)
- Scenario configuration presets (low/medium/high intensity, stalemate)
- 49 executable actions across 7 categories
- Action execution system with probabilistic outcomes

### v3.1.2
- External engagement every period

### v3.1.1
- External actors as independent factions

### v3.1
- Pre-action coordination with internal faction debate
