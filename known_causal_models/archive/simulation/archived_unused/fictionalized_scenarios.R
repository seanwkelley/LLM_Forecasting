# Fictionalized Scenarios with Named Countries
# Creates rich, evolving geopolitical scenarios

#' Define fictional countries with detailed backgrounds
COUNTRIES <- list(
  valdoria = list(
    name = "Valdoria",
    full_name = "The Federal Republic of Valdoria",
    region = "Northern Continent",
    government = "Parliamentary Democracy",
    population_millions = 85,
    gdp_billions = 2100,
    military_strength = "major_power",
    culture = "Individualistic, market-oriented, historically colonial power",
    recent_trajectory = "Experiencing domestic political polarization and questioning of global commitments",
    strategic_interests = c("Maintain naval access to key straits", "Protect trade routes",
                           "Contain Novaris expansion", "Preserve alliance system"),
    vulnerabilities = c("Political division", "Aging population", "Resource dependence")
  ),

  novaris = list(
    name = "Novaris",
    full_name = "The People's Federation of Novaris",
    region = "Eastern Continent",
    government = "Single-Party Technocratic State",
    population_millions = 340,
    gdp_billions = 3800,
    military_strength = "major_power",
    culture = "Collectivist, state-directed economy, historical empire with grievances",
    recent_trajectory = "Rising power challenging regional order, nationalist resurgence",
    strategic_interests = c("Reunify with Tethys", "Reclaim 'lost territories'",
                           "Break Valdorian alliance network", "Establish regional hegemony"),
    vulnerabilities = c("Economic slowdown", "Technological lag in some sectors", "Encirclement fears")
  ),

  tethys = list(
    name = "Tethys",
    full_name = "The Democratic Commonwealth of Tethys",
    region = "Eastern Continent (disputed)",
    government = "Multi-party Democracy",
    population_millions = 24,
    gdp_billions = 680,
    military_strength = "regional_power",
    culture = "Mixed heritage, entrepreneurial, technologically advanced",
    recent_trajectory = "Consolidated democracy, seeking international recognition, under constant threat",
    strategic_interests = c("Maintain independence", "Secure international support",
                           "Deter Novaris aggression", "Develop asymmetric capabilities"),
    vulnerabilities = c("Small territory", "Geographic proximity to Novaris", "Limited resources")
  ),

  azuria = list(
    name = "Azuria",
    full_name = "The Azurian Caliphate",
    region = "Southern Continent",
    government = "Constitutional Theocracy",
    population_millions = 92,
    gdp_billions = 1200,
    military_strength = "regional_power",
    culture = "Religious conservative, oil-rich, regional influencer",
    recent_trajectory = "Modernizing economy while maintaining traditional values, regional rivalry",
    strategic_interests = c("Spread religious influence", "Counter Palmyra",
                           "Control oil prices", "Develop nuclear capability"),
    vulnerabilities = c("Succession uncertainty", "Youth unemployment", "Regional isolation")
  ),

  palmyra = list(
    name = "Palmyra",
    full_name = "The Palmyran Republic",
    region = "Southern Continent",
    government = "Islamic Republic",
    population_millions = 88,
    gdp_billions = 450,
    military_strength = "regional_power",
    culture = "Revolutionary ideology, anti-Western stance, pariah state",
    recent_trajectory = "Under heavy sanctions, developing asymmetric capabilities, supporting proxies",
    strategic_interests = c("Survive international pressure", "Export revolution",
                           "Develop nuclear deterrent", "Break sanctions"),
    vulnerabilities = c("Economic crisis", "International isolation", "Internal dissent")
  ),

  meridian = list(
    name = "Meridian",
    full_name = "The United States of Meridian",
    region = "Western Continent",
    government = "Federal Democracy",
    population_millions = 425,
    gdp_billions = 8500,
    military_strength = "superpower",
    culture = "Multicultural, free-market ideology, global military presence",
    recent_trajectory = "Debating global role, domestic focus increasing, alliance fatigue",
    strategic_interests = c("Prevent peer competitors", "Maintain dollar dominance",
                           "Protect allies", "Contain Novaris and Palmyra"),
    vulnerabilities = c("Domestic polarization", "War weariness", "Deficit spending")
  ),

  aurelia = list(
    name = "Aurelia",
    full_name = "The Aurelian Union",
    region = "Central Continent",
    government = "Supranational Federation",
    population_millions = 280,
    gdp_billions = 5200,
    military_strength = "major_power",
    culture = "Post-conflict cooperation, multilateral focus, regulatory power",
    recent_trajectory = "Struggling with internal cohesion, energy dependence, migration pressures",
    strategic_interests = c("Maintain unity", "Energy security",
                           "Defend liberal order", "Strategic autonomy"),
    vulnerabilities = c("Dependence on Novaris energy", "Military weakness", "Internal divisions")
  ),

  ashanti = list(
    name = "Ashanti",
    full_name = "The Ashanti Federation",
    region = "Southern Continent",
    government = "Federal Democracy",
    population_millions = 215,
    gdp_billions = 720,
    military_strength = "emerging_power",
    culture = "Diverse, resource-rich, rapid development, non-aligned tradition",
    recent_trajectory = "Economic boom, infrastructure development, regional leadership ambitions",
    strategic_interests = c("Economic development", "Resource sovereignty",
                           "Regional stability", "Non-alignment"),
    vulnerabilities = c("Infrastructure gaps", "Corruption", "Regional conflicts")
  ),

  valkoria = list(
    name = "Valkoria",
    full_name = "The Valkorian Confederation",
    region = "Northern Continent",
    government = "Authoritarian Federation",
    population_millions = 145,
    gdp_billions = 1800,
    military_strength = "major_power",
    culture = "Historical ally of Novaris, shared authoritarian model, 'sovereign democracy' ideology rejecting Western liberalism",
    recent_trajectory = "Increasingly isolated from Western economies, deepening strategic partnership with Novaris, coordinating diplomatic positions against perceived Western encirclement",
    strategic_interests = c("Maintain Novaris alliance as counterweight to Western pressure",
                           "Prevent 'color revolution' contagion from Tethyan democracy",
                           "Secure energy transit routes through Novaris",
                           "Break Western sanctions through alternative partnerships",
                           "Preserve authoritarian governance against democratic 'threats'"),
    vulnerabilities = c("Economic dependence on Novaris", "Severe Western sanctions",
                       "Demographic decline and brain drain", "Ethnic tensions in border regions",
                       "Aging infrastructure requiring foreign investment"),
    relationship_with_novaris = "Treaty of Eternal Friendship (2020) commits both to mutual support. Not a formal military alliance but close coordination on foreign policy."
  )
)

#' Create complete scenario with trajectory
#'
#' @param scenario_type Type of initial scenario
#' @return Complete scenario object with countries and initial situation
create_scenario <- function(scenario_type = "territorial_dispute") {

  if (scenario_type == "territorial_dispute") {
    scenario <- list(
      name = "Tethys Crisis",
      description = "Tensions over Novaris claims to Tethys sovereignty",

      initial_situation = "
Novaris has mobilized 40% of its forces and is massing troops on the Tethys border
in a 'decisive pressure campaign.' However, Novaris faces vulnerabilities: 30% of its
energy export revenue flows through Tethys-controlled pipelines, its cyber infrastructure
is exposed, and 15% of its population is ethnic Tethyan with democratic sympathies.

Tethys has mobilized defensive forces but also possesses offensive capabilities: advanced
cyber units targeting Novaris infrastructure, precision strike capacity against mobilization
centers, economic leverage via pipeline shutdowns, and intelligence networks inside Novaris
supporting opposition movements. Tethys can make invasion extremely costly.

Meridian has a security commitment to Tethys but faces domestic war weariness.
Aurelia is coordinating diplomatic efforts while balancing energy dependence on Novaris.
The crisis is escalating across multiple domains: cyber attacks are exchanged daily,
economic warfare is beginning, and covert operations are underway on both sides.

30 days until Novaris must decide: invade (with risk of quagmire), negotiate (risk appearing weak),
or maintain pressure (risk Tethys gains Western protection). Both sides can escalate or de-escalate.",

      key_actors = c("novaris", "tethys", "meridian", "valdoria", "aurelia"),

      background_events = c(
        "Three months ago: Tethys president delivered speech on permanent independence",
        "Two months ago: Novaris expelled Tethys diplomats and cut trade ties",
        "One month ago: Meridian Secretary of State visited Tethys, reaffirmed support",
        "Two weeks ago: Novaris began 'Sovereign Shield' exercises near Tethys waters"
      ),

      information_asymmetries = list(
        novaris_knows = c(
          "Meridian intelligence assessment shows 60% probability of intervention if invasion occurs",
          "Aurelia will not support military action due to energy dependence",
          "Tethys has only 2 weeks of ammunition for high-intensity conventional conflict",
          "Some Tethys commanders advocate preemptive strikes on mobilization centers"
        ),
        tethys_knows = c(
          "Novaris military mobilization has critical logistics vulnerabilities at current 40% readiness",
          "Some Novaris generals oppose invasion as too risky given Tethys cyber capabilities",
          "Meridian has pre-positioned equipment in allied countries",
          "30% of Novaris export revenue flows through Tethys pipelines (economic leverage)",
          "Ethnic Tethyan networks inside Novaris could support covert operations"
        ),
        meridian_knows = c(
          "Novaris leadership divided on timing and scope of action",
          "Aurelia privately assessed it would impose sanctions if invasion occurs",
          "Tethys has developed precision strike capabilities and cyber weapons",
          "Both Novaris and Tethys have conducted covert operations against each other",
          "Tethys intelligence has penetrated Novaris opposition movements"
        ),
        unknown_to_all = c(
          "Tethys cyber units have already penetrated Novaris power grid with dormant kill switches",
          "Novaris covert teams have pre-positioned sabotage equipment in Tethys infrastructure",
          "Meridian intelligence has intercepted Novaris war plans showing 3-week timeline",
          "Aurelia has secretly agreed to host Tethys government-in-exile if invasion occurs"
        )
      ),

      potential_trajectories = list(
        escalation_path_novaris_initiated = c(
          "Novaris conducts false-flag operation or border provocation",
          "Tethys responds with cyber attack disabling Novaris power grid in border regions",
          "Novaris launches limited strikes on Tethys cyber warfare centers",
          "Tethys shuts down energy transit pipelines (30% of Novaris revenue)",
          "Meridian faces decision: intervene or abandon commitment"
        ),

        escalation_path_tethys_initiated = c(
          "Tethys launches preemptive strikes on Novaris mobilization centers",
          "Novaris declares this justifies full invasion, accelerates mobilization to 100%",
          "Tethys activates cyber kill switches in Novaris infrastructure",
          "Economic warfare: both sides impose embargos and asset seizures",
          "Meridian rushed into crisis decision with limited preparation"
        ),

        deescalation_path_negotiated = c(
          "Aurelia brokers backchannel negotiations between intelligence chiefs",
          "Novaris pauses mobilization at 40%, demands Tethys guarantee neutrality",
          "Tethys agrees to postpone Western alliance bid in exchange for security guarantees",
          "Meridian provides economic aid package to both sides as face-saving mechanism",
          "Status quo maintained with monitoring regime"
        ),

        deescalation_path_deterrence_succeeds = c(
          "Tethys demonstrates precision strike capability in publicized exercise",
          "Novaris reassesses invasion cost given Tethys offensive capabilities",
          "Meridian deploys cyber defense teams and precision weapons to Tethys",
          "Novaris declares partial victory, withdraws some forces but maintains pressure",
          "Frozen conflict with ongoing cyber/economic warfare at low intensity"
        ),

        wild_card_events = c(
          "Coup attempt in Novaris by anti-war faction (Tethys intelligence supported)",
          "Tethys assassinates key Novaris military commander (escalation risk)",
          "Major cyber attack crashes Novaris financial system (Tethys suspected)",
          "Ethnic Novaran uprising in Tethys gives Novaris pretext for intervention",
          "Meridian domestic crisis forces withdrawal of security commitment",
          "Accidental border clash escalates into unintended conflict"
        )
      )
    )

  } else if (scenario_type == "nuclear_proliferation") {
    scenario <- list(
      name = "Azurian Nuclear Crisis",
      description = "Discovery of Azurian covert nuclear weapons program",

      initial_situation = "
Satellite imagery reveals Azuria has constructed an undeclared enrichment
facility in remote mountains. Intelligence suggests they may be 6-12 months
from nuclear weapon capability. Palmyra is suspected of providing technical
assistance. Meridian faces pressure for military action while Aurelia and
Ashanti prefer diplomatic solutions. Valdoria fears regional nuclear cascade.",

      key_actors = c("azuria", "palmyra", "meridian", "valdoria", "aurelia", "ashanti"),

      background_events = c(
        "Two years ago: Azuria withdrew from Nuclear Non-Proliferation Treaty",
        "One year ago: Palmyra and Azuria signed 'civilian nuclear cooperation' deal",
        "Six months ago: Azuria test-fired ballistic missile capable of reaching Valdoria",
        "Three months ago: International inspectors denied access to suspected sites"
      ),

      information_asymmetries = list(
        azuria_knows = c(
          "Palmyra has provided centrifuge designs and technical advisors",
          "Meridian military strike plans exist but lack political support",
          "Ashanti will block severe sanctions at international organizations"
        ),
        meridian_knows = c(
          "Azuria's Supreme Leader fears coup, sees nukes as regime survival",
          "Enrichment facility is vulnerable to air strikes",
          "Valdoria privately supports military option"
        ),
        palmyra_knows = c(
          "Azuria has promised to share nuclear technology once developed",
          "Meridian cyber capabilities could sabotage program",
          "Aurelia will oppose military action regardless"
        ),
        unknown_to_all = c(
          "Azuria secretly has nuclear material from black market",
          "Internal opposition in Azuria to nuclear program is growing",
          "Novaris has offered nuclear umbrella to Azuria"
        )
      ),

      potential_trajectories = list(
        escalation_path = c(
          "Meridian launches covert sabotage operation",
          "Azuria retaliates with proxy attacks",
          "Valdoria conducts preventive strike",
          "Regional war erupts"
        ),

        deescalation_path = c(
          "Comprehensive negotiations with sanctions relief",
          "Azuria agrees to intrusive inspections",
          "Palmyra ceases technical assistance",
          "Monitoring regime established"
        ),

        wild_card_events = c(
          "Azuria successfully tests nuclear device",
          "Revolution in Azuria overthrows government",
          "Meridian intelligence discovered to be flawed",
          "Other regional states announce nuclear programs"
        )
      )
    )

  } else if (scenario_type == "economic_warfare") {
    scenario <- list(
      name = "Trade War Escalation",
      description = "Meridian-Novaris economic conflict threatens global order",

      initial_situation = "
Meridian has imposed comprehensive technology export controls on Novaris,
citing national security. Novaris retaliated by restricting rare earth
exports critical to Meridian industries. Aurelia caught in middle, dependent
on both powers. Ashanti sees opportunity to attract investment. Global
supply chains fragmenting.",

      key_actors = c("meridian", "novaris", "aurelia", "ashanti", "valdoria"),

      background_events = c(
        "One year ago: Novaris announced Made in Novaris 2035 technology independence plan",
        "Eight months ago: Meridian banned Novaris telecom equipment",
        "Four months ago: Novaris sold sovereign bonds to diversify from dollar",
        "One month ago: Meridian froze Novaris central bank assets"
      ),

      information_asymmetries = list(
        meridian_knows = c(
          "Novaris has secret stockpiles of critical materials",
          "Aurelia companies planning to evade sanctions",
          "Novaris economy more vulnerable than public statements suggest"
        ),
        novaris_knows = c(
          "Meridian consumer inflation rising, political pressure mounting",
          "Ashanti willing to serve as sanctions-evasion hub",
          "Valdoria has secret rare earth deposits"
        ),
        aurelia_knows = c(
          "Both powers have contingency plans for financial decoupling",
          "Meridian considering secondary sanctions on Aurelia firms",
          "Novaris has approached Aurelia about energy payment in euros"
        ),
        unknown_to_all = c(
          "Global recession will result from continued escalation",
          "Cyber capabilities exist to disrupt opponent's financial systems",
          "Multiple countries developing alternative payment systems"
        )
      ),

      potential_trajectories = list(
        escalation_path = c(
          "Novaris dumps Meridian bonds, dollar crisis",
          "Meridian imposes secondary sanctions",
          "Aurelia forced to choose sides",
          "Global economy fragments into blocs"
        ),

        deescalation_path = c(
          "Face-saving partial rollback of measures",
          "Aurelia mediates compromise",
          "WTO dispute resolution process engaged",
          "Managed competition framework established"
        ),

        wild_card_events = c(
          "Major bank failures due to exposure",
          "Cyberattack on financial infrastructure",
          "Currency crisis in emerging markets",
          "Political change in key country"
        )
      )
    )
  }

  scenario$countries <- COUNTRIES
  scenario$turn <- 0
  scenario$max_turns <- 10

  return(scenario)
}

#' Update scenario trajectory based on actions
#'
#' @param scenario Scenario object
#' @param actions Actions taken this turn
#' @return Updated scenario with trajectory changes
update_scenario_trajectory <- function(scenario, actions) {
  scenario$turn <- scenario$turn + 1

  # Track escalation level
  aggressive_actions <- sum(sapply(actions, function(a) {
    a$category %in% c("covert_operations", "open_conflict", "wmd")
  }))

  diplomatic_actions <- sum(sapply(actions, function(a) {
    a$category == "diplomatic"
  }))

  # Update trajectory
  if (aggressive_actions > diplomatic_actions * 2) {
    scenario$current_trajectory <- "escalation"
    scenario$crisis_level <- min(10, scenario$crisis_level + 2)
  } else if (diplomatic_actions > aggressive_actions * 2) {
    scenario$current_trajectory <- "deescalation"
    scenario$crisis_level <- max(1, scenario$crisis_level - 1)
  } else {
    scenario$current_trajectory <- "stable"
  }

  # Add random events based on trajectory
  if (runif(1) < 0.3) {
    wild_card <- sample(scenario$potential_trajectories$wild_card_events, 1)
    scenario$recent_events <- c(scenario$recent_events, wild_card)
  }

  return(scenario)
}

#' Generate situation update for agents
#'
#' @param scenario Current scenario
#' @param agent Agent receiving update
#' @param other_agents Other agents in scenario
#' @return Situation update with information filtered by access level
generate_situation_update <- function(scenario, agent, other_agents) {
  # Base information everyone gets
  update <- list(
    turn = scenario$turn,
    crisis_level = scenario$crisis_level,
    public_events = scenario$recent_events
  )

  # Add information based on agent's access level
  if (agent$information$access > 0.7) {
    # High-quality intelligence
    country_name <- agent$country

    if (country_name %in% names(scenario$information_asymmetries)) {
      known_info <- scenario$information_asymmetries[[paste0(tolower(country_name), "_knows")]]
      update$intelligence <- sample(known_info, min(3, length(known_info)))
    }
  } else if (agent$information$access > 0.4) {
    # Moderate intelligence
    update$intelligence <- c("Limited intelligence available")
  }

  # Add assessments of other agents (with potential errors)
  update$threat_assessments <- list()
  for (other_agent in other_agents) {
    if (other_agent$name != agent$name) {
      # Assessment accuracy depends on information quality
      accuracy <- agent$information$accuracy

      base_threat <- runif(1)
      noise <- rnorm(1, 0, 1 - accuracy)
      perceived_threat <- max(0, min(1, base_threat + noise))

      update$threat_assessments[[other_agent$name]] <- perceived_threat
    }
  }

  return(update)
}
