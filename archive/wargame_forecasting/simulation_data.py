"""
Simulation State and Events Data for Periods 1-10

Extracted from simulation outputs to support forecasting experiments.
Periods 4-10 extrapolated from observed trends.
"""

# Initial state (period 0 baseline)
INITIAL_STATE = {
    'territory_controlled': 0.0,
    'military_balance': 0.0,
    'novaris_gdp': 100.0,
    'tethys_gdp': 30.0,
    'international_support': 0.5,
    'sanctions_level': 0.0
}


# State after each period (before next period begins)
PERIOD_STATES = {
    1: {
        'territory_controlled': 0.0,  # No territory captured yet
        'military_balance': -0.05,    # Slight Novaris advantage
        'novaris_gdp': 98.0,           # Minor economic cost
        'tethys_gdp': 29.5,            # Minor economic strain
        'international_support': 0.55, # Increased support for Tethys
        'sanctions_level': 0.15        # Initial sanctions on Novaris
    },
    2: {
        'territory_controlled': 0.05,  # Small territorial gains
        'military_balance': -0.10,     # Moderate Novaris advantage
        'novaris_gdp': 95.0,           # Economic costs mounting
        'tethys_gdp': 28.5,            # Economic damage
        'international_support': 0.60, # Growing international support
        'sanctions_level': 0.25        # Increasing sanctions
    },
    3: {
        'territory_controlled': 0.08,  # Continued territorial gains
        'military_balance': -0.12,     # Novaris advantage maintained
        'novaris_gdp': 92.0,           # Significant economic impact
        'tethys_gdp': 27.5,            # Worsening economy
        'international_support': 0.65, # Strong international support
        'sanctions_level': 0.35        # Heavy sanctions
    },
    4: {
        'territory_controlled': 0.12,  # Further territorial gains
        'military_balance': -0.15,     # Novaris advantage growing
        'novaris_gdp': 89.0,           # Heavy economic toll
        'tethys_gdp': 26.0,            # Severe economic damage
        'international_support': 0.70, # Very strong international support
        'sanctions_level': 0.45        # Severe sanctions
    },
    5: {
        'territory_controlled': 0.15,  # Significant territorial losses
        'military_balance': -0.18,     # Strong Novaris advantage
        'novaris_gdp': 86.0,           # Mounting economic costs
        'tethys_gdp': 24.5,            # Critical economic situation
        'international_support': 0.75, # Maximum international support
        'sanctions_level': 0.55        # Maximum sanctions
    },
    6: {
        'territory_controlled': 0.20,  # Major territorial losses
        'military_balance': -0.22,     # Very strong Novaris advantage
        'novaris_gdp': 83.0,           # Severe economic strain
        'tethys_gdp': 22.0,            # Economy near collapse
        'international_support': 0.78, # Very high international support
        'sanctions_level': 0.65        # Heavy sanctions
    },
    7: {
        'territory_controlled': 0.25,  # Severe territorial losses
        'military_balance': -0.25,     # Overwhelming Novaris advantage
        'novaris_gdp': 80.0,           # Major economic damage
        'tethys_gdp': 19.5,            # Catastrophic economic situation
        'international_support': 0.80, # Maximum diplomatic support
        'sanctions_level': 0.70        # Maximal sanctions
    },
    8: {
        'territory_controlled': 0.30,  # Catastrophic territorial losses
        'military_balance': -0.28,     # Decisive Novaris advantage
        'novaris_gdp': 77.0,           # Severe economic toll
        'tethys_gdp': 17.0,            # Economic collapse underway
        'international_support': 0.82, # Sustained maximum support
        'sanctions_level': 0.75        # Maximum sanctions sustained
    },
    9: {
        'territory_controlled': 0.35,  # Most territory lost
        'military_balance': -0.30,     # Complete Novaris dominance
        'novaris_gdp': 74.0,           # Prolonged economic damage
        'tethys_gdp': 14.5,            # Total economic collapse
        'international_support': 0.83, # International support maintained
        'sanctions_level': 0.78        # Extreme sanctions
    },
    10: {
        'territory_controlled': 0.40,  # Critical territorial control
        'military_balance': -0.32,     # Total Novaris supremacy
        'novaris_gdp': 71.0,           # Massive economic costs
        'tethys_gdp': 12.0,            # Complete economic failure
        'international_support': 0.85, # Maximum support but ineffective
        'sanctions_level': 0.80        # Maximum sanctions maintained
    }
}


# External events by period
PERIOD_EVENTS = {
    1: [
        "Battlefield: Initial skirmishes along border - limited engagements",
        "Economic: International financial sanctions imposed on Novaris",
        "Diplomatic: Meridian reaffirms security commitment to Tethys",
        "Intelligence: Cyber operations detected by both sides"
    ],
    2: [
        "Battlefield: Novaris launches limited offensive - captures border positions",
        "Economic: Energy prices surge due to supply concerns",
        "Diplomatic: International Organization calls for ceasefire negotiations",
        "Intelligence: Reports of covert operations escalating"
    ],
    3: [
        "Battlefield: Continued fighting - Novaris advances slowly against resistance",
        "Economic: Sanctions enforcement increasing pressure on Novaris",
        "Diplomatic: Peace talks proposed by international mediators",
        "Intelligence: Both sides conducting active espionage campaigns"
    ],
    4: [
        "Battlefield: Novaris offensive intensifies - major territorial gains",
        "Economic: Both economies under severe strain from prolonged conflict",
        "Diplomatic: International calls for immediate ceasefire grow urgent",
        "Intelligence: Reports of potential WMD preparations by Novaris"
    ],
    5: [
        "Battlefield: Heavy fighting continues - Tethys defenses weakening",
        "Economic: Tethys economy nearing collapse - critical shortages",
        "Diplomatic: Emergency UN Security Council session called",
        "Intelligence: Indications of internal political instability in Tethys"
    ],
    6: [
        "Battlefield: Major Novaris breakthrough - Tethys defenses crumbling",
        "Economic: Both economies in severe crisis - prolonged war costs mounting",
        "Diplomatic: International intervention proposals debated but stalled",
        "Intelligence: Reports of coup plotting within Tethys government"
    ],
    7: [
        "Battlefield: Tethys capital under threat - strategic retreat underway",
        "Economic: Mass exodus from Tethys - refugee crisis developing",
        "Diplomatic: Ceasefire negotiations fail - no diplomatic breakthrough",
        "Intelligence: Novaris prepares for decisive offensive operations"
    ],
    8: [
        "Battlefield: Tethys loses major strategic cities - military collapse accelerating",
        "Economic: International aid to Tethys insufficient to prevent collapse",
        "Diplomatic: International community divided on intervention scale",
        "Intelligence: Internal fragmentation of Tethys military command"
    ],
    9: [
        "Battlefield: Tethys military resistance fragmenting - organized defense failing",
        "Economic: Complete economic paralysis in Tethys - basic services failing",
        "Diplomatic: Last-ditch diplomatic efforts for conditional surrender",
        "Intelligence: Tethys government preparing contingency evacuation plans"
    ],
    10: [
        "Battlefield: Final major battles - Tethys capital encircled",
        "Economic: Total economic collapse - humanitarian catastrophe",
        "Diplomatic: International community preparing post-conflict stabilization",
        "Intelligence: Multiple factions within Tethys negotiating separately with Novaris"
    ]
}


def get_state_before(period: int) -> dict:
    """
    Get the state BEFORE a period begins (i.e., after previous period ends).

    Args:
        period: Period number (1-10)

    Returns:
        State dictionary
    """
    if period == 1:
        return INITIAL_STATE.copy()
    elif period in PERIOD_STATES:
        # State after period-1 ended
        return PERIOD_STATES[period - 1].copy()
    else:
        raise ValueError(f"State data not available for period {period}")


def get_events(period: int) -> list:
    """
    Get external events for a specific period.

    Args:
        period: Period number (1-10)

    Returns:
        List of event description strings
    """
    if period in PERIOD_EVENTS:
        return PERIOD_EVENTS[period].copy()
    else:
        raise ValueError(f"Events data not available for period {period}")


if __name__ == "__main__":
    print("="*60)
    print("SIMULATION DATA - PERIODS 1-3")
    print("="*60)

    for period in [1, 2, 3]:
        print(f"\n=== PERIOD {period} ===")

        state = get_state_before(period)
        print(f"\nState (before period {period}):")
        for key, value in state.items():
            print(f"  {key}: {value}")

        events = get_events(period)
        print(f"\nExternal Events:")
        for i, event in enumerate(events, 1):
            print(f"  {i}. {event}")

    print("\n" + "="*60)
    print("[OK] Simulation data loaded successfully")
    print("="*60)
