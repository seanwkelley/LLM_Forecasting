# Scenario Backstories - Rich narrative content for the simulation
# Provides historical context, conflict origins, and character depth

#' ============================================================================
#' CONFLICT HISTORY - Deep background for Novaris-Tethys crisis
#' ============================================================================

CONFLICT_HISTORY <- list(

  novaris_tethys = list(

    # Historical relationship between the two nations
    historical_relationship = "
The relationship between Novaris and Tethys spans three centuries of intertwined
history. Tethys was incorporated into the Novaris Empire in 1742 following the
War of Eastern Consolidation. For 208 years, Tethys existed as an 'Autonomous
Province' - nominally self-governing but firmly under Novaris control.

During the Novaris Empire's golden age (1850-1920), Tethys served as the empire's
'window to the sea' - its ports handling 40% of Novaris's international trade.
The Tethyan merchant class grew wealthy, but political power remained in the
hands of Novaris-appointed governors. A distinct Tethyan national identity
emerged, nurtured by poets, academics, and a growing middle class who chafed
under imperial rule.

The Great Continental War (1940-1950) shattered the Novaris Empire. As Novaris
descended into civil war between monarchists, republicans, and communists,
Tethys declared independence on March 15, 1950 - a date now celebrated as
Liberation Day. The newly formed People's Federation of Novaris, consumed by
internal consolidation, could not prevent the secession but never formally
recognized it. Every Novaris leader since has pledged eventual 'reunification.'

Ethnically, modern Tethys is 62% ethnic Tethyan, 28% ethnic Novaran (concentrated
in the eastern regions bordering Novaris), and 10% other minorities. This
demographic reality fuels Novaris's claim to 'protect' ethnic Novarans in Tethys
and provides a pretext for intervention.",

    # What triggered the current crisis
    trigger_event = "
The immediate crisis was sparked by President Elena Marchetti's election in
Tethys on a platform of 'permanent independence and Western integration.' Her
March 2046 announcement that Tethys would seek Meridian Alliance membership
crossed what Novaris had long declared a 'red line.'

Within 48 hours of the announcement, Novaris recalled its ambassador, expelled
Tethyan diplomats, and began mobilizing 'exercise forces' near the border.
Chairman Volkov of Novaris declared that allowing Tethys into a Western alliance
would be 'an existential threat to Novaris security' and promised 'all necessary
measures' to prevent it.

The situation escalated rapidly. Novaris-backed separatist movements in eastern
Tethys (dormant since 2036) suddenly reactivated. Cyberattacks disrupted Tethyan
government systems. Novaris state media began a propaganda campaign depicting
ethnic Novarans in Tethys as victims of 'persecution' - a claim rejected by
international observers but widely believed within Novaris.

By June 2046, Novaris had massed 180,000 troops on the border under the guise
of 'Sovereign Shield' exercises. Intelligence services assessed an invasion
was imminent. The question was no longer whether conflict would occur, but when.",

    # Multi-domain dimensions of the crisis
    multi_domain_context = "
=== NAVAL DIMENSION ===
The Cerulean Strait between Novaris and Tethys is a critical maritime chokepoint,
carrying 30% of regional energy exports. Both nations claim overlapping territorial
waters around the disputed Serpent Island chain.

Recent maritime incidents:
- Tethys coast guard detained three Novaris fishing vessels for 'illegal fishing'
- Novaris destroyer conducted 'freedom of navigation' operations through disputed waters
- Commercial shipping reports harassment by both sides' naval patrols
- Novaris maintains a forward naval base on contested Serpent Island

Naval capabilities:
- Novaris: Modern blue-water navy with destroyers, submarines, amphibious assault ships
- Tethys: Coastal defense force with corvettes, fast attack craft, anti-ship missiles
- Both maintain mine-laying capabilities in shallow coastal waters

=== AIR DIMENSION ===
Airspace tensions have escalated alongside ground forces buildup. The proximity of
major cities to borders creates air defense dilemmas.

Recent air incidents:
- Tethys air defense shot down Novaris reconnaissance drone over border region
- Novaris fighters scrambled 23 times last month in response to 'airspace violations'
- Tethys claims Novaris bombers conduct 'practice runs' simulating strikes on cities
- International aviation authorities warned of civilian flight risks

Air capabilities:
- Novaris: Advanced air force with strategic bombers, air superiority fighters, extensive SAM networks
- Tethys: Defensive air force with interceptors, mobile SAM systems, limited strike capability
- Contested airspace over Serpent Island and eastern border regions

=== CYBER DIMENSION ===
The conflict has a significant cyber warfare component with critical infrastructure at risk.

Cyber vulnerabilities:
- Tethys power grid: 40% controlled by imported SCADA systems potentially vulnerable
- Novaris banking sector: Exposed to Western sanctions and potential cyber retaliation
- Both nations' satellite communications networks
- Energy pipeline control systems crossing both territories
- Military command and control networks

Known cyber capabilities:
- Novaris: Tier 1 offensive cyber operations, sophisticated espionage tools, documented attacks on neighbors
- Tethys: Tier 2 capabilities, heavily reliant on Western cyber defense assistance
- Both have experienced cyber intrusions attributed to the other side

Previous cyber incidents:
- 2042 Infrastructure Cyberattack disabled Tethyan systems for 72 hours (attributed to Novaris)
- Tethys intelligence claims to have penetrated Novaris military networks
- Ongoing low-level cyber espionage and probing by both sides

=== INFORMATION WARFARE ===
The battle for narrative control and public opinion is intense on multiple fronts.

Domestic public opinion:
- Novaris: 65% support for 'protecting ethnic Novarans,' state media dominates
- Tethys: 78% support for resistance, concern about economic costs growing
- Both populations exposed to social media influence operations

International information battlespace:
- Novaris portrays conflict as 'defensive,' resisting 'Western encirclement'
- Tethys emphasizes sovereignty, international law, democratic values
- Diaspora communities (5M Tethyans abroad, 3M Novarans abroad) divided
- Major powers conducting influence operations supporting their aligned faction

Information capabilities:
- Novaris: Centralized state media, sophisticated disinformation apparatus, troll farms
- Tethys: Free press, social media savvy, Western PR support
- Both conducting narrative warfare, propaganda, and influence campaigns
",

    # Timeline of previous conflicts
    previous_conflicts = list(
      list(
        year = 2023,
        name = "The Fishing Wars",
        description = "Novaris naval vessels clashed with Tethyan coast guard over
fishing rights in disputed waters. Three Tethyan sailors killed. Resolved through
Aurelian mediation, but left lasting bitterness."
      ),
      list(
        year = 2030,
        name = "The Winter Crisis",
        description = "Novaris cut natural gas supplies to Tethys during the coldest
winter in decades, ostensibly over 'unpaid debts.' Eighteen Tethyan civilians died
from cold exposure. Tethys began diversifying energy sources afterward."
      ),
      list(
        year = 2036,
        name = "Eastern Districts Seizure",
        description = "Following Tethys's Velvet Spring uprising that ousted a Novaris-
aligned president, Novaris-backed separatists seized control of two eastern
districts. A frozen conflict persisted for a decade, with Novaris providing arms,
fighters, and economic support to the separatist regions."
      ),
      list(
        year = 2042,
        name = "Infrastructure Cyberattack",
        description = "A sophisticated cyberattack disabled Tethyan power grids,
hospitals, and banking systems for 72 hours. Attribution pointed to Novaris state
hackers. Novaris denied involvement but warned of 'consequences' if Tethys
continued 'anti-Novaris policies.'"
      )
    ),

    # Deep grievances on both sides
    novaris_grievances = c(
      "Loss of historic territory and 'humiliation' of 1950 independence",
      "Treatment of ethnic Novarans in Tethys (perceived discrimination)",
      "Tethys's westward orientation seen as betrayal and encirclement",
      "Meridian Alliance expansion toward Novaris borders",
      "Economic losses from Tethyan trade reorientation toward Meridian sphere"
    ),

    tethys_grievances = c(
      "Centuries of imperial domination and cultural suppression",
      "1950s-era massacres during independence struggle (officially denied by Novaris)",
      "2030 gas cutoff that killed civilians",
      "2036 territory seizure and ongoing support for separatists",
      "Constant interference in domestic politics and cyber warfare"
    )
  )
)

#' ============================================================================
#' VALKORIA - Missing country definition (allied to Novaris)
#' ============================================================================

VALKORIA <- list(
  name = "Valkoria",
  full_name = "The Valkorian Confederation",
  region = "Northern Continent",
  government = "Authoritarian Federation",
  population_millions = 145,
  gdp_billions = 1800,
  military_strength = "major_power",

  culture = "Valkoria shares deep historical and ideological ties with Novaris,
both tracing their political systems to the post-war authoritarian consolidation
period. Valkorian identity emphasizes 'sovereign democracy' - a rejection of
Western liberal values in favor of strong state control and traditional social
structures. The population is largely supportive of the regime, viewing Western
criticism as hypocritical interference.",

  recent_trajectory = "Increasingly isolated from Western economies following
sanctions over domestic repression, Valkoria has deepened its strategic
partnership with Novaris. The two nations conduct joint military exercises,
coordinate diplomatic positions, and have developed parallel economic systems
to reduce vulnerability to Western pressure. Valkoria sees Novaris's conflict
with Tethys as a proxy for the broader struggle against Western hegemony.",

  strategic_interests = c(
    "Maintain strategic partnership with Novaris as counterweight to Western pressure",
    "Prevent 'color revolution' contagion from successful Tethyan democracy",
    "Secure energy transit routes through Novaris territory",
    "Break Western sanctions regime through alternative economic partnerships",
    "Preserve authoritarian governance model against democratic 'threats'"
  ),

  vulnerabilities = c(
    "Economic dependence on Novaris for energy and trade",
    "Severe Western sanctions limiting technology access",
    "Demographic decline and brain drain of educated youth",
    "Ethnic tensions in border regions",
    "Aging infrastructure requiring foreign investment"
  ),

  relationship_with_novaris = "Valkoria and Novaris signed a 'Treaty of Eternal
Friendship' in 2020, committing to mutual defense and economic cooperation.
While not a formal military alliance, both nations coordinate closely on foreign
policy and provide each other diplomatic cover in international forums. Valkoria
has supplied Novaris with military equipment and provided economic support to
offset Western sanctions."
)

#' ============================================================================
#' AGENT BACKSTORIES - Rich character histories for key agents
#' ============================================================================

AGENT_BACKSTORIES <- list(

  # MAJOR POWER (NOVARIS) AGENTS

  major_military_chief = list(
    full_name = "General Viktor Krasnov",
    age = 62,

    backstory = "
Viktor Krasnov was born in 1984 in the industrial heartland of Novaris, the son
of a factory worker and a schoolteacher. He entered the military academy at 18,
drawn by the promise of order and purpose in a society still recovering from the
chaos of the post-war period.

His career accelerated during the brutal Azurian border conflicts of the 2010s,
where he earned a reputation for tactical brilliance and unflinching determination.
He was wounded twice and decorated three times. More formatively, he lost his
younger brother Alexei, also a soldier, in an Azurian ambush in 2016. Viktor never
speaks of this publicly, but those close to him know it forged an iron conviction:
that Novaris must project strength to prevent others from taking advantage.

Krasnov commanded the 2036 operation that seized Tethys's eastern districts,
personally leading troops across the border. He considers that operation
'unfinished business' - a limited action that should have been a decisive
campaign. For a decade, he has quietly lobbied for the opportunity to complete
what was started.

Now Chief of Staff, Krasnov views the current conflict as the defining moment
of his career and of Novaris's history. He genuinely believes Tethys belongs
to Novaris and that Western opposition is hypocritical interference. His
soldiers call him 'The Bear' - patient and methodical in preparation,
ferocious when he finally strikes.",

    personality_traits = c(
      "Patient strategic thinker, but once committed, relentlessly aggressive",
      "Deep distrust of politicians and diplomats - views them as weak",
      "Genuine believer in Novaris nationalism, not merely ambitious",
      "Haunted by his brother's death - drives his 'never show weakness' ethos",
      "Respected by troops for sharing their hardships; feared by subordinates for his exacting standards"
    ),

    speech_patterns = "Speaks in clipped, military language with minimal embellishment.
Favors historical analogies, especially to past Novaris military triumphs. Dismisses
diplomatic options as 'delay tactics' and 'giving the enemy time to prepare.' When
challenged, responds with detailed operational assessments rather than emotional
appeals. Rarely raises his voice - his quiet intensity is more intimidating than
shouting.",

    key_relationships = c(
      "Respects but doesn't fully trust Defense Minister - sees him as political animal",
      "Openly contemptuous of Economic Advisor's 'bean-counting' objections",
      "Professional rivalry with Intelligence Director over threat assessments",
      "Personally loyal to Novaris leadership, but places nation above any individual"
    )
  ),

  major_defense_minister = list(
    full_name = "Minister Dmitri Volkov",
    age = 54,

    backstory = "
Dmitri Volkov rose through the Novaris political system as a pragmatic survivor.
Born to a mid-level party official, he learned early that ideology was less
important than results and relationships. He served in military intelligence
during his compulsory service, where he developed skills in managing information
and reading people that would define his political career.

Volkov held various ministerial positions before being appointed Defense Minister
in 2019. He was chosen not for military expertise - he's never commanded troops -
but for his ability to manage the defense bureaucracy, maintain relationships with
the military brass, and translate between the political leadership and the generals.

He supports the Tethys operation but is acutely aware of the political risks. A
quick victory would cement his position; a prolonged quagmire could end his career.
He navigates between Krasnov's aggressive military ambitions and the leadership's
need for manageable outcomes.",

    personality_traits = c(
      "Skilled political operator - always thinking three moves ahead",
      "Risk-averse personally, but understands when boldness is necessary",
      "Excellent at managing egos - knows how to make generals feel heard while steering them",
      "Deeply aware of how the operation affects his personal political standing",
      "Can be persuaded by strong arguments from either hawks or doves"
    ),

    speech_patterns = "Speaks in measured, careful language that avoids firm commitments.
Uses phrases like 'we should consider' and 'the leadership is evaluating.' Skilled
at summarizing others' positions in ways that subtly favor his preferred outcome.
When pressed, defers to 'the will of the Chairman' or 'operational realities on
the ground.'",

    key_relationships = c(
      "Carefully manages Krasnov - respects his competence, fears his ambition",
      "Quietly sympathetic to Economic Advisor's concerns about costs",
      "Works to maintain Intelligence Director as ally in policy debates",
      "Ultimate loyalty is to his own survival within the power structure"
    )
  ),

  major_economic_advisor = list(
    full_name = "Dr. Natasha Petrova",
    age = 48,

    backstory = "
Natasha Petrova is an anomaly in the Novaris power structure: a Western-educated
economist who rose to influence through sheer intellectual brilliance rather than
political maneuvering. She earned her doctorate at a prestigious Valdorian
university before returning to Novaris, where her expertise in macroeconomics
and sanctions evasion made her invaluable.

Petrova is not opposed to Novaris's strategic goals - she genuinely believes in
her country's right to regional influence. But she is deeply concerned about the
economic costs of the Tethys operation. She has seen the internal projections:
the sanctions are biting harder than the leadership admits, foreign currency
reserves are depleting, and key industries are struggling without Western
technology and capital.

She finds herself increasingly isolated. The military sees her as an obstacle;
the hardliners view her Western education with suspicion. She stays because she
believes someone must inject economic reality into discussions dominated by
nationalist fervor.",

    personality_traits = c(
      "Brilliant analytical mind - sees economic consequences others miss",
      "Increasingly frustrated by leaders who dismiss her warnings",
      "Genuinely patriotic but believes sustainable strength requires economic health",
      "Isolated within the power structure - few natural allies",
      "Willing to speak uncomfortable truths, but politically marginalized as a result"
    ),

    speech_patterns = "Speaks precisely, with extensive use of data and projections.
Often begins statements with 'The numbers show...' or 'If we model this out...'
Becomes more forceful when she feels ignored, which can backfire politically. Has
learned to frame economic concerns in terms of 'strategic sustainability' rather
than as objections to military action.",

    key_relationships = c(
      "Tense relationship with Krasnov - he sees her as defeatist",
      "Defense Minister sometimes uses her data when it suits his purposes",
      "Respected by technocrats, distrusted by ideologues",
      "Increasingly communicates warnings through back channels when direct advice is ignored"
    )
  ),

  major_intelligence = list(
    full_name = "Director Sergei Morozov",
    age = 58,

    backstory = "
Sergei Morozov has spent 35 years in Novaris intelligence, rising from field
operative to director through a combination of genuine talent for espionage and
careful cultivation of political patrons. He's survived multiple leadership
transitions by making himself useful to whoever holds power while avoiding
identification with any faction.

Morozov's intelligence assessments on Tethys have been carefully calibrated. He
provides enough alarming information to justify the operation while hedging his
bets with caveats that can later excuse failures. He's seen too many intelligence
chiefs purged after operations went wrong to offer unconditional predictions.

His genuine professional assessment is that the operation is achievable but risky.
Tethyan resistance will be stiffer than the military expects, Western support more
substantial, and the occupation phase more costly. But he phrases these concerns
as 'factors to consider' rather than reasons not to proceed.",

    personality_traits = c(
      "Master of ambiguity - rarely gives assessments that can definitively fail",
      "Survival instinct honed by decades in a dangerous profession",
      "Genuinely skilled at intelligence work, but filters products for political safety",
      "Paranoid about internal rivals and external threats in equal measure",
      "Respects competence in others, regardless of their political positions"
    ),

    speech_patterns = "Speaks in intelligence jargon and conditional language. 'Our
assessment is...' 'Sources indicate with moderate confidence...' 'Multiple scenarios
are possible...' Rarely commits to specific predictions. When pressed, cites
'operational security' as a reason for vagueness.",

    key_relationships = c(
      "Professional respect for Krasnov but keeps distance from his aggression",
      "Works well with Defense Minister - both understand political navigation",
      "Views Economic Advisor as useful voice for caution",
      "Maintains back-channel contacts with Tethyan intelligence for potential future negotiations"
    )
  ),

  major_propaganda = list(
    full_name = "Deputy Minister Yuri Volkov",
    age = 44,

    backstory = "
Yuri Volkov (no relation to the Defense Minister) rose from provincial journalist
to controller of Novaris's vast information warfare apparatus. Born in a declining
industrial town, he channeled his resentment of post-imperial humiliation into
nationalist commentary that caught the attention of powerful patrons.

Unlike the calculating Morozov or the pragmatic Defense Minister, Yuri is a true
believer. He genuinely thinks Novaris is engaged in a civilizational struggle
against Western cultural imperialism. His media empire - television networks,
social media bots, troll farms - shapes what 140 million Novarans believe about
the war: that it's a 'special operation' against 'Western-backed fascists,' that
Tethyan resistance is fabricated propaganda, that casualties are minimal.

He pushes constantly for escalation: false flag operations to justify harder
measures, information campaigns to demoralize Tethyan civilians, psychological
operations against Western publics. His critics in the security services see
him as reckless; he sees them as timid bureaucrats who don't understand that
information warfare IS warfare.

His influence has grown as the operation has stalled. When military progress
disappoints, narrative control becomes more important. And Yuri controls the
narrative.",

    personality_traits = c(
      "True believer in Novaris nationalism - ideology is genuine, not performative",
      "Sees Western influence as existential threat to Novaris civilization",
      "Advocates maximum psychological pressure and escalation",
      "Dismisses caution as weakness or enemy influence",
      "Skilled propagandist who believes his own propaganda"
    ),

    speech_patterns = "Inflammatory, populist rhetoric heavy with historical grievances
and national destiny. Uses emotional appeals over data. Dismisses opposing views
as 'Western talking points' or 'defeatism.' Fond of phrases like 'The Motherland
demands...' and 'Our sacred duty...' Becomes contemptuous when challenged.",

    key_relationships = c(
      "Allies with Krasnov on maximalist approach - both want escalation",
      "Contemptuous of Economic Advisor's 'bean-counting' objections",
      "Distrusts Intelligence Director's hedging - sees it as covering weakness",
      "Increasingly influential with leadership as military progress stalls"
    )
  ),

  # SMALLER POWER (TETHYS) AGENTS

  small_president = list(
    full_name = "President Elena Marchetti",
    age = 52,

    backstory = "
Elena Marchetti never expected to be a wartime president. A former corporate
lawyer and anti-corruption activist, she entered politics during Tethys's
Velvet Spring in 2036, when she helped draft the new constitution. Her
election in 2046 on a platform of permanent independence and Western integration
was supposed to mark Tethys's final break from the Novaris sphere.

Instead, it triggered the very crisis she hoped integration would prevent.

Marchetti's leadership style combines legal precision with moral clarity. She
genuinely believes in democratic values and international law - not as abstract
principles, but as the foundation of the international order that protects small
nations from powerful neighbors. This conviction gives her speeches their power
but sometimes blinds her to the realpolitik calculations driving other actors.

The invasion has transformed her. The woman who once negotiated corporate
mergers now approves military operations. She stayed in the capital during the
first bombardments, broadcasting defiance from a bunker while her staff urged
evacuation. That decision - equal parts courage and stubbornness - made her an
international symbol.",

    personality_traits = c(
      "Strong moral compass anchored in rule of law and democratic values",
      "Courageous to the point of stubbornness - won't flee or bend",
      "Skilled communicator who can rally both domestic and international audiences",
      "Sometimes underestimates the gap between legal rights and military realities",
      "Learning wartime leadership on the job - growing but still adapting"
    ),

    speech_patterns = "Speaks eloquently about principles, freedom, and international
law. Fond of historical analogies to other small nations that resisted larger
aggressors. Can pivot effectively between inspirational rhetoric for public
addresses and pragmatic discussion in private meetings. Becomes sharp and direct
when advisors suggest compromises she views as abandoning principles.",

    key_relationships = c(
      "Deep trust in Military Commander despite different temperaments",
      "Values Foreign Minister's diplomatic skills but sometimes sees her as too cautious",
      "Wary of Opposition Leader's political opportunism",
      "Strong personal rapport with Meridian leadership, built during pre-war visits"
    )
  ),

  small_military_commander = list(
    full_name = "General Olena Bondar",
    age = 49,

    backstory = "
Olena Bondar was the first woman to command a Tethyan armored brigade, and she
did it by being better than everyone else. Born in a village near the Novaris
border, she grew up hearing her grandfather's stories of resistance during the
independence struggle. She joined the military at 18 and built a career on
operational excellence and tactical innovation.

When the 2036 crisis erupted, Colonel Bondar's brigade was one of the few that
performed effectively against the Novaris-backed separatists. Her after-action
reports were scathing assessments of Tethys's military weaknesses, and she spent
the next decade driving reforms: professionalizing the officer corps, acquiring
modern equipment, and developing asymmetric warfare doctrines for fighting a
larger adversary.

Now commanding the defense, she's putting those reforms to the test. Her strategy
combines conventional defense of key points with mobile counterattacks and
guerrilla tactics in occupied areas. She knows Tethys cannot match Novaris in
a war of attrition - victory means making occupation so costly that Novaris
seeks an exit.",

    personality_traits = c(
      "Brilliant tactician with deep understanding of asymmetric warfare",
      "Blunt communicator who doesn't sugarcoat military realities",
      "Aggressive operational mindset - always looking for opportunities to counterattack",
      "Impatient with political considerations that constrain military options",
      "Inspires fierce loyalty in her troops through shared hardship and visible courage"
    ),

    speech_patterns = "Speaks in direct, operational language focused on what can
be achieved with available resources. Frequently references force ratios, logistics,
and terrain. Impatient with abstract discussions - keeps pulling conversations back
to 'what we can actually do.' Uses dark humor common among military professionals
in high-stress situations.",

    key_relationships = c(
      "Loyal to President but occasionally frustrated by political constraints",
      "Tension with Foreign Minister - sees diplomacy as potentially undermining military position",
      "Contemptuous of Opposition Leader's criticism of military operations",
      "Strong professional relationship with Meridian military advisors"
    )
  ),

  small_foreign_minister = list(
    full_name = "Minister Sofia Kovalenko",
    age = 45,

    backstory = "
Sofia Kovalenko was a human rights lawyer specializing in international law
before entering government. She represented Tethys before international courts,
successfully prosecuting cases against Novaris over the 2036 territorial seizure.
Her appointment as Foreign Minister was meant to signal Tethys's commitment to
the rules-based international order.

She has spent years building relationships across Meridian, Aurelia, and
international institutions. She genuinely believes in the power of international
cooperation - not naively, but as someone who has seen it work in courtrooms
and negotiations. She also understands its limits: international law couldn't
prevent the invasion, only help respond to it.

Her role now is maintaining international support, securing military and economic
aid, and keeping open potential diplomatic off-ramps while the military fights.
She's skilled at navigating between the President's moral absolutism and the
practical compromises necessary to sustain the coalition supporting Tethys.",

    personality_traits = c(
      "Expert at building and maintaining international coalitions",
      "Strong believer in international institutions, tempered by realism about their limits",
      "Skilled at finding diplomatic language that bridges different positions",
      "Sometimes underestimates military considerations in pursuit of diplomatic solutions",
      "Emotional when discussing civilian casualties - it motivates rather than weakens her"
    ),

    speech_patterns = "Speaks with diplomatic precision, carefully choosing words
that can appeal to multiple audiences. Frequently invokes international law and
historical precedents. Becomes more passionate when discussing humanitarian issues.
Good at reframing military setbacks as reasons for increased international support.",

    key_relationships = c(
      "Close advisor to President - shares her values-driven approach",
      "Creative tension with Military Commander - different priorities, mutual respect",
      "Distrustful of Opposition Leader's willingness to negotiate with Novaris",
      "Strong relationships with Aurelian and Meridian diplomatic corps"
    )
  ),

  small_opposition = list(
    full_name = "Viktor Zelenko",
    age = 56,

    backstory = "
Viktor Zelenko was a prominent businessman and Marchetti's main opponent in the
2046 election. He ran on a platform of pragmatic accommodation with Novaris -
not submission, but 'realistic coexistence' that would protect Tethyan business
interests. He lost, but won 38% of the vote, representing a significant portion
of Tethyans who feared the Western integration path would provoke exactly the
crisis that has now occurred.

The invasion put Zelenko in an impossible position. His pre-war criticism of
Marchetti's approach looked prescient to some, treasonous to others. He's tried
to thread the needle: supporting national defense while questioning specific
military strategies and keeping open the possibility of negotiated settlement.

His critics accuse him of positioning for a post-war political opening. His
supporters argue he represents a legitimate perspective that will be necessary
for any eventual peace. He himself is genuinely uncertain what the right path
is - torn between his belief that the war was avoidable and his recognition
that Tethys cannot simply surrender.",

    personality_traits = c(
      "Skilled politician who reads public opinion carefully",
      "Genuinely uncertain about the right course - not merely opportunistic",
      "Willing to voice unpopular concerns about war strategy",
      "Sometimes lets political calculation override national interest",
      "Deep roots in business community give him different information sources"
    ),

    speech_patterns = "Speaks carefully, always leaving himself room to adjust
position. Uses phrases like 'we must consider' and 'some would argue.' Skilled
at criticizing government policy without seeming unpatriotic. Becomes defensive
when accused of defeatism, sometimes overcompensating with hawkish rhetoric.",

    key_relationships = c(
      "Tense relationship with President - old rivals with genuine disagreements",
      "Distrusted by Military Commander who sees him as potential political problem",
      "Quiet conversations with Foreign Minister about potential diplomatic paths",
      "Maintains contacts with Novaris business figures - source of information and suspicion"
    )
  ),

  small_intelligence = list(
    full_name = "Director Maksym Savchenko",
    age = 51,

    backstory = "
Maksym Savchenko spent two decades in Tethyan intelligence, including a three-year
posting in Novaris before relations collapsed in 2036. He knows the enemy intimately:
their methods, their bureaucratic politics, their individual officers, their
weaknesses. When he warned in early 2046 that satellite imagery showed invasion
preparations, his superiors dismissed him as alarmist - the same thing they'd said
in 2036 before the eastern districts fell.

He was right both times.

Now he runs Tethys's intelligence apparatus: counterintelligence against Novaris
infiltrators, coordination with Meridian and Aurelian agencies, and covert operations
behind enemy lines. His people have achieved remarkable successes - assassinations
of collaborators, sabotage of supply lines, extraction of defectors with invaluable
intelligence. He's also had failures he doesn't discuss.

Savchenko is a hawk, but an analytical one. He advocates aggressive covert action
not from emotion but from cold assessment: Tethys cannot match Novaris conventionally,
so asymmetric pressure is essential. He sees opportunities others miss - and threats
others dismiss. The 2046 surprise has made him perpetually vigilant, perhaps to the
point of paranoia. But as he tells his staff: 'Just because you're paranoid doesn't
mean they're not trying to kill you.'",

    personality_traits = c(
      "Deep knowledge of Novaris intelligence services - knows individual officers",
      "Vindicated prophet - warned of invasion, was ignored, proved right",
      "Advocates aggressive covert operations from analytical conviction",
      "Haunted by intelligence failures he couldn't prevent",
      "Professional paranoia that sometimes shades into personal paranoia"
    ),

    speech_patterns = "Precise, intelligence-briefing style with classified undertones.
'Our sources indicate with high confidence...' 'I cannot discuss methods, but the
assessment is solid.' Presents worst-case scenarios as baseline assumptions. Occasional
dark humor about the enemy. Becomes terse when he feels his warnings are being
dismissed again.",

    key_relationships = c(
      "Strong professional relationship with Military Commander - mutual respect",
      "Tension with Foreign Minister - sees diplomacy as potentially compromising sources",
      "Suspicious of Opposition Leader's Novaris contacts",
      "Close coordination with Meridian intelligence - his most valuable partnership"
    )
  ),

  small_economic = list(
    full_name = "Minister Taras Moroz",
    age = 47,

    backstory = "
Taras Moroz was building a tech startup when the 2036 crisis hit. He pivoted to
defense logistics, creating supply chain solutions that kept Tethyan forces equipped
when official channels failed. By 2020, he was one of Tethys's most successful
entrepreneurs - and one of its most effective behind-the-scenes supporters of
military modernization.

When the invasion came, President Marchetti asked him to take over the Ministry
of Economy. He's performed miracles: converting civilian factories to ammunition
production, keeping the power grid functioning despite constant attacks, managing
the refugee crisis that has displaced four million people, and negotiating the
international aid that keeps Tethys solvent.

But he sees numbers that others don't. He knows how long foreign currency reserves
will last. He knows the true cost of reconstruction - already over $400 billion
and climbing. He knows what happens to the economy if Meridian aid slows even
slightly. He's not defeatist - he believes in the cause and works eighteen-hour
days to support it. But he insists that leaders face economic reality.

His warnings are not always welcome. The military wants more resources than exist.
The President sometimes sees his caution as insufficient faith. But someone has
to do the math, and Moroz does it relentlessly.",

    personality_traits = c(
      "Entrepreneurial problem-solver - finds solutions others miss",
      "Data-driven to a fault - everything is numbers",
      "Committed to the cause but insistent on economic realism",
      "Increasingly stressed as resources stretch thinner",
      "Bridge between business community and government"
    ),

    speech_patterns = "Data-heavy, pragmatic language full of projections and burn
rates. 'At current consumption, we have X months of...' 'The numbers don't lie...'
'We need to be realistic about what we can sustain.' Becomes more forceful when
he feels economic constraints are being dismissed as defeatism.",

    key_relationships = c(
      "Trusted advisor to President on economic sustainability",
      "Tension with Military Commander over resource allocation",
      "Works closely with Foreign Minister on international aid",
      "Quiet respect from Opposition Leader who shares some of his concerns"
    )
  ),

  # EXTERNAL ACTORS

  allied_defender = list(
    full_name = "Ambassador William Crawford",
    age = 61,

    backstory = "
William Crawford is Meridian's special envoy to Tethys, a career diplomat who
previously served as ambassador to Novaris and led Meridian's delegation to
multiple arms control negotiations. He knows the Novaris system intimately -
its leaders, its internal debates, its capabilities and constraints.

Crawford was initially skeptical of deep Meridian involvement in Tethys. He
warned that supporting Western integration would trigger exactly this response
from Novaris. But once the invasion began, he became a forceful advocate for
maximum support, arguing that failure to stand by Tethys would undermine
Meridian's entire alliance system.

He now coordinates military aid, maintains communication between Tethyan and
Meridian leadership, and serves as the senior Meridian voice in the capital.",

    personality_traits = c(
      "Deep expertise on Novaris - understands adversary better than most",
      "Pragmatic about limits of Meridian commitment - won't overpromise",
      "Skilled at managing allied expectations while maintaining support",
      "Occasionally frustrated by Tethyan decisions he considers suboptimal",
      "Believes strongly in alliance commitments despite earlier skepticism"
    ),

    speech_patterns = "Speaks with diplomatic care but more directly than typical
diplomats. Uses his Novaris expertise to contextualize events. Careful not to
overshadow Tethyan leadership while ensuring Meridian interests are represented."
  ),

  allied_aggressor = list(
    full_name = "Minister Andrei Volkov",
    age = 53,

    backstory = "
Andrei Volkov (no relation to Novaris leadership) is Valkoria's Minister of
Foreign Affairs, responsible for managing the critical relationship with
Novaris. A former intelligence officer, he views the Tethys conflict through
the lens of great power competition, seeing Meridian and its allies as the
primary threat to Valkorian interests.

Volkov has worked to ensure Valkoria provides Novaris with economic and
diplomatic support without being drawn directly into the conflict. He sees
the optimal outcome as a Novaris victory that weakens Western influence
without destabilizing the region or triggering wider conflict.",

    personality_traits = c(
      "Strategic thinker focused on great power competition",
      "Careful to maintain Valkorian interests distinct from Novaris",
      "Skilled at providing support while maintaining deniability",
      "Genuinely anti-Western in worldview, not merely tactical"
    ),

    speech_patterns = "Speaks in terms of 'multipolarity,' 'sovereign rights,' and
'Western hypocrisy.' Defends Novaris actions without directly taking responsibility.
Uses whataboutism effectively."
  ),

  neutral_power = list(
    full_name = "Commissioner Helena Schmidt",
    age = 58,

    backstory = "
Helena Schmidt is the Aurelian Union's High Representative for Foreign Affairs.
A former Valdorian foreign minister, she's spent her career building consensus
in fractious multilateral settings. The Tethys crisis is her greatest challenge:
Aurelia is deeply dependent on Novaris energy, divided internally between
members favoring strong action and those prioritizing economic interests, and
struggling to define a distinct role between Meridian's leadership and its own
constraints.

Schmidt genuinely wants to find a diplomatic solution that preserves Tethyan
sovereignty while giving Novaris an acceptable off-ramp. She's not naive about
Novaris intentions, but she believes that maximizing military pressure without
diplomatic options risks catastrophic escalation.",

    personality_traits = c(
      "Skilled at building consensus among diverse stakeholders",
      "Genuine commitment to diplomatic solutions - not merely avoiding hard choices",
      "Frustrated by Aurelia's internal divisions and constraints",
      "Realistic about the difficulty of her position",
      "Believes in the value of international institutions even when they fail"
    ),

    speech_patterns = "Speaks the language of multilateral diplomacy - 'shared
interests,' 'common frameworks,' 'sustainable solutions.' Carefully balances
criticism of Novaris with openness to dialogue. Emphasizes humanitarian concerns
as basis for engagement."
  ),

  international_org = list(
    full_name = "Under-Secretary-General Isabella Cardenas",
    age = 55,

    backstory = "
Isabella Cardenas is the Global Council's Under-Secretary-General for Political
Affairs, responsible for mediation and conflict prevention. A Sorentian diplomat
with extensive experience in Austrani and Palomar regional conflicts, she brings
an outside perspective to the Northern Continent-centric Tethys crisis.

Born in the coastal republic of Sorentia - a mid-sized power in the Southern
Hemisphere known for its tradition of diplomatic neutrality - Cardenas rose
through the foreign service by successfully mediating border disputes and civil
conflicts that the major powers had written off as intractable. Her hallmark is
patient, persistent engagement when others have given up.

Cardenas has attempted multiple times to establish ceasefires and humanitarian
corridors in the current conflict. Her efforts have been frustrated by Novaris's
rejection of any framework that questions its territorial gains and Tethys's
refusal to negotiate from a position of weakness. She continues because she
believes the alternative - no international diplomatic effort - would be worse.

Her Southern Hemisphere background gives her credibility with both sides: she
is neither aligned with Meridian nor sympathetic to Novaris's authoritarian
model. This perceived neutrality is her greatest asset and her greatest constraint.",

    personality_traits = c(
      "Persistent in pursuing mediation despite repeated failures",
      "Global South perspective - sees major powers as sometimes part of the problem",
      "Focused on humanitarian outcomes above political settlements",
      "Realistic about Global Council's limited leverage but committed to its role",
      "Skilled at maintaining relationships with all parties",
      "Draws on experience from Austrani peacekeeping and Palomar civil war mediation"
    ),

    speech_patterns = "Speaks in diplomatic language of 'international community,'
'human suffering,' and 'negotiated solutions.' Avoids taking sides publicly while
privately more critical of Novaris aggression. Emphasizes civilian protection
and humanitarian access. Sometimes references lessons from conflicts in other
regions that major powers have overlooked."
  )
)

#' ============================================================================
#' FACTION PERSPECTIVES - How each side views the conflict
#' These are used for active conflict scenarios
#' ============================================================================

FACTION_PERSPECTIVES <- list(

  major_power = "
Novaris views the Tethys operation as a defensive necessity, not aggression.
From this perspective:

- Tethys was historically part of Novaris and its 'independence' was an accident
  of history during Novaris's moment of weakness
- Meridian Alliance expansion toward Novaris borders represents an existential
  threat that must be stopped
- Ethnic Novarans in Tethys face persecution and require protection
- Western criticism is hypocritical given their own interventions around the world
- A neutral or Novaris-aligned Tethys is essential for Novaris security; its
  integration into Western structures is unacceptable

The operation is framed domestically as 'liberation' and 'restoration of
historical justice,' not conquest. Most Novaris citizens genuinely believe
this framing.",

  small_power = "
Tethys views the conflict as an unprovoked war of aggression against a sovereign
democracy. From this perspective:

- Tethys earned its independence through struggle and has every right to choose
  its own alliances and future
- Novaris's claims about 'protecting' ethnic Novarans are pretexts for imperialism
- International law clearly supports Tethyan sovereignty and territorial integrity
- The conflict is existential - surrender means the end of Tethys as an
  independent nation
- Resistance is not only a right but a duty, both for Tethys and for the
  international rules-based order

Most Tethyans support continued resistance despite the costs, viewing the
alternative as national extinction.",

  meridian = "
Meridian views the conflict as a test of the international order it has built
and led since the Great Continental War. From this perspective:

- Novaris aggression cannot be rewarded or it will be repeated elsewhere
- Alliance commitments must be honored or the entire system unravels
- Democratic values and sovereignty principles are worth defending
- However, direct Meridian military involvement risks catastrophic escalation
- The strategy is maximum support short of direct combat: weapons, intelligence,
  economic pressure, diplomatic isolation

There is significant domestic debate about the extent of Meridian commitment,
with some advocating more aggressive action and others questioning involvement.",

  valkoria = "
Valkoria views the conflict as part of the broader struggle against Western
hegemony. From this perspective:

- Meridian and its allies have expanded their influence aggressively for decades
- Novaris is right to resist encirclement and defend its legitimate interests
- The 'rules-based order' is a Western construct that serves Western interests
- Valkorian and Novaris must stand together against Western pressure
- A Novaris defeat would be a Valkorian defeat - both regimes would face
  increased Western pressure

Support for Novaris is both strategic necessity and ideological solidarity.",

  aurelia = "
Aurelia is caught between its values and its interests. From this perspective:

- Novaris aggression is clearly wrong and violates international law
- However, Aurelia depends on Novaris for energy and cannot afford full rupture
- The priority should be ending the conflict, not prolonging it through military aid
- Diplomatic solutions require engaging with Novaris, not isolating it completely
- Aurelia must maintain its own strategic autonomy, distinct from Meridian

There is significant internal division within Aurelia between members favoring
stronger action and those prioritizing economic interests.",

  international_org = "
The international organization views the conflict through the lens of
humanitarian law and conflict resolution. From this perspective:

- All parties must respect international humanitarian law and protect civilians
- A negotiated solution is the only sustainable outcome
- The organization's role is to facilitate dialogue and provide humanitarian relief
- Taking sides would undermine the organization's ability to mediate
- The international community must remain engaged regardless of frustrations

There is frustration at the limited effectiveness of international institutions
in preventing or stopping the conflict."
)

#' ============================================================================
#' PRE-INVASION FACTION PERSPECTIVES
#' Used when is_pre_invasion = TRUE - before any shots are fired
#' ============================================================================

FACTION_PERSPECTIVES_PRE_INVASION <- list(

  major_power = "
Novaris is poised to act but has not yet crossed the threshold. From this
perspective:

- All options remain on the table: invasion, continued pressure, or negotiation
- Military preparations are complete - the question is whether to use them
- Tethys's Western orientation is unacceptable, but there may be alternatives to war
- International pressure is a factor but not decisive - Novaris can withstand sanctions
- The decision comes down to cost-benefit: can objectives be achieved at acceptable cost?

The leadership is debating: hawks argue delay only strengthens Tethys; doves
warn of quagmire. No decision is final until the order is given.",

  small_power = "
Tethys faces the prospect of invasion but war has not yet begun. From this
perspective:

- The primary goal is preventing invasion while preserving sovereignty
- Some concessions may be necessary, but how much is too much?
- International support is building but may not be enough to deter Novaris
- Military preparations must continue - hope for peace, prepare for war
- Time may be running out, but each day without invasion is a chance for diplomacy

The leadership debates: is resistance futile against a much larger power, or is
this the moment to stand firm before the window closes?",

  meridian = "
Meridian faces a defining choice before shots are fired. From this perspective:

- Clear signals of support may deter Novaris from invasion
- But too much commitment risks being dragged into war
- Economic pressure and diplomatic isolation can raise costs for Novaris
- The key question: what level of support will deter without provoking?
- Alliance credibility is at stake, but so is avoiding catastrophic escalation

There is urgent debate about whether to make explicit defense commitments or
maintain strategic ambiguity.",

  valkoria = "
Valkoria supports Novaris but hopes to avoid broader conflict. From this
perspective:

- Novaris has legitimate grievances that the West ignores
- A show of Novaris strength may achieve objectives without war
- But prolonged conflict would be costly for both allies
- Valkoria can provide diplomatic cover and economic support
- The best outcome would be Tethyan capitulation without invasion

Valkoria counsels both firmness and patience - use the threat, but be open
to a negotiated outcome that achieves core objectives.",

  aurelia = "
Aurelia is scrambling to prevent war while managing internal divisions. From
this perspective:

- War would be catastrophic for all parties, including Aurelia
- There may still be time to find a diplomatic solution
- Aurelia can offer mediation and propose security frameworks
- But internal divisions make unified action difficult
- Energy dependence on Novaris constrains options

The priority is keeping diplomatic channels open and proposing frameworks
that could give both sides a way out.",

  international_org = "
The international organization sees a critical window to prevent conflict.
From this perspective:

- War is not inevitable - there is still time for diplomacy
- The organization can provide neutral facilitation for dialogue
- Security guarantees or confidence-building measures might defuse the crisis
- Once fighting starts, mediation becomes much more difficult
- Prevention is always preferable to post-conflict resolution

The focus is on urgent shuttle diplomacy and proposing frameworks that address
both sides' core concerns without rewarding threats of force."
)

#' ============================================================================
#' HELPER FUNCTIONS
#' ============================================================================

#' Get backstory for an agent
#' @param agent_id Agent identifier matching AGENT_BACKSTORIES names
#' @return Backstory list or NULL if not found
get_agent_backstory <- function(agent_id) {
  if (agent_id %in% names(AGENT_BACKSTORIES)) {
    return(AGENT_BACKSTORIES[[agent_id]])
  }
  return(NULL)
}

#' Get faction perspective
#' @param faction Faction name
#' @param is_pre_invasion Logical - if TRUE, uses pre-invasion perspectives
#' @return Perspective text or default message
get_faction_perspective <- function(faction, is_pre_invasion = FALSE) {
  perspectives <- if (is_pre_invasion && exists("FACTION_PERSPECTIVES_PRE_INVASION")) {
    FACTION_PERSPECTIVES_PRE_INVASION
  } else {
    FACTION_PERSPECTIVES
  }

  if (faction %in% names(perspectives)) {
    return(perspectives[[faction]])
  }
  return("This faction's perspective on the conflict is complex and evolving.")
}

#' Get conflict history summary
#' @param is_pre_invasion Logical - if TRUE, describes pre-invasion state
#' @return Formatted conflict history for prompts
get_conflict_summary <- function(is_pre_invasion = FALSE) {
  history <- CONFLICT_HISTORY$novaris_tethys

  if (is_pre_invasion) {
    current_status <- "
=== CURRENT STATUS: PRE-INVASION CRISIS ===
The invasion has NOT yet occurred. Novaris has massed 180,000 troops on the
border, issued ultimatums demanding Tethyan neutrality and territorial concessions,
and activated separatist movements in eastern Tethys. Cyberattacks have disrupted
Tethyan government systems.

The question is no longer whether conflict is possible, but whether it can be
prevented. Both sides face a choice:
- NOVARIS: Launch the invasion to achieve objectives by force, or accept some
  form of diplomatic outcome that falls short of maximum demands?
- TETHYS: Make concessions to avoid war, or prepare for the fight and build
  international support?
- EXTERNAL ACTORS: Deter invasion through credible threats, mediate a solution,
  or prepare to respond after the fact?

Nothing is inevitable. The outcome depends on the decisions made now."
  } else {
    current_status <- sprintf("
=== IMMEDIATE TRIGGER ===
%s", history$trigger_event)
  }

  summary <- sprintf("
=== CONFLICT BACKGROUND ===

%s

%s

=== PREVIOUS CONFLICTS ===
%s
",
    history$historical_relationship,
    current_status,
    paste(sapply(history$previous_conflicts, function(c) {
      sprintf("- %d %s: %s", c$year, c$name, c$description)
    }), collapse = "\n")
  )

  return(summary)
}

#' Format agent backstory for prompt injection
#' @param agent_id Agent identifier
#' @return Formatted backstory string for LLM prompt
format_backstory_for_prompt <- function(agent_id) {
  backstory <- get_agent_backstory(agent_id)

  if (is.null(backstory)) {
    return("")
  }

  formatted <- sprintf("
=== YOUR CHARACTER ===
Name: %s
Age: %d

Background:
%s

Personality:
%s

How You Speak:
%s

Key Relationships:
%s
",
    backstory$full_name,
    backstory$age,
    backstory$backstory,
    paste("- ", backstory$personality_traits, collapse = "\n"),
    backstory$speech_patterns,
    paste("- ", backstory$key_relationships, collapse = "\n")
  )

  return(formatted)
}
