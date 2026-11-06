# Scenario Showcase — jheinrichk

[[Home]] · [[Scenario Development Workflow|Scenario-Development-Workflow]]

These published [Command: Modern Operations Workshop items by jheinrichk](https://steamcommunity.com/profiles/76561198123053700/myworkshopfiles/?appid=1076160) illustrate the author's scenario design and Lua development. The author describes using a chatbot for scripting while personally designing the Surovikin campaign and developing the bridge's offline RAG and database libraries ([Workshop discussion](https://steamcommunity.com/sharedfiles/filedetails/?id=3813282207)). This page presents them as examples of the **bridge-assisted scenario-development approach**, not as content included in the CMO Bridge repository or proof that any individual scenario was generated entirely automatically.

## Orbittoblast — Objects in Orbit Are Closer Than They Appear

**[Steam Workshop: Orbittoblast](https://steamcommunity.com/sharedfiles/filedetails/?id=3830546106)**

- **Scenario dates:** 14–17 January 2027; approximately 72 hours.
- **Playable sides:** Russia, Ukraine, United States/NATO.
- **Database reported in release:** DB3000 v519.
- **Premise:** A fictional escalation against satellite links serving the war in Ukraine. Orbital activity, jamming and anti-satellite engagements affect ground warfare and the wider space environment.
- **Notable design features:** Satellite networks across orbital shells; debris persistence by altitude; effects on drone links, artillery accuracy and ISR; 24 decisions across three chains; AI control of unselected sides; six endings and a 2037 epilogue.
- **Author credit:** Scenario design and Lua build by Johannes Kohler.

The scenario emphasizes second-order consequences: a local tactical decision can affect orbital debris and third parties far beyond the immediate battlefield.

## Election Day Surprise

**[Steam Workshop: Election Day Surprise](https://steamcommunity.com/sharedfiles/filedetails/?id=3827337947)**

- **Scenario date:** 1 November 2026; approximately 72 hours.
- **Playable sides:** United States and Iran; solo, PBEM or hotseat as described by the release.
- **Database reported in release:** DB3000 v515.
- **Scale:** Approximately 540 units; high complexity.
- **Premise:** A fictional Gulf and Middle East crisis unfolds on the eve of American and Israeli elections. Political decisions open or close escalating military options.
- **Notable design features:** Decision-led escalation ladder; time-stopped briefing choices with images; automated air/missile operations between decisions; regional economic, infrastructure and water-supply consequences; multiple epilogues.
- **Credits:** Concept attributed by the author to alby001; scenario design and Lua build by Johannes Kohler.

Rather than assuming a single preferred victory path, the scenario asks players to accept the consequences of political choices.

## Surovikin's Return: The Fortress Belt (Campaign)

**[Steam Workshop campaign](https://steamcommunity.com/sharedfiles/filedetails/?id=3813282207)** · **[Matrix Games forum discussion](https://forums.matrixgames.com/viewtopic.php?t=418897)**

- **Setting:** A fictional October 2026 Donbas offensive.
- **Playable sides:** Ukraine or Russia; the AI takes the opposing side.
- **Four chapters:** *Winter* (21 Oct, 6h); *Saturation* (23 Oct, 8h); *Other Avenues* (25 Oct, 8h); *The Line* (27 Oct, 6h).
- **Database:** Workshop currently lists DB3000 v519; earlier Matrix discussion referenced v515. Check the current Workshop package for the required version.
- **Design:** Decisions occur at operational turning points. Drone decoys, stand-in loitering munitions, GNSS jamming, electronic warfare, artillery displacement and resupply, air support and tactical simulations form an interconnected campaign. State and scoring carry between chapters.
- **Additional features:** Player-controlled flight sequences are described for the Su-25 loft run and Ukrainian Dragon's Breath drone; timed script events and choice prompts require careful performance testing.

**Development provenance:** In Workshop comments, the author expressly distinguishes personal design/timeline decisions from chatbot-assisted scripting and identifies the external bridge and its offline libraries. This is the strongest direct public description of the bridge-assisted workflow.

The Steam package is the primary source for current build/update instructions. The Matrix forum thread contains design explanation and technical development notes.

## Hormuz 2026: The Southern Route

**[Steam Workshop scenario](https://steamcommunity.com/sharedfiles/filedetails/?id=3808807124)** · **[Matrix Games forum discussion](https://forums.matrixgames.com/viewtopic.php?t=418898)**

- **Scenario date:** 3 September 2026, 0100Z; 24 hours.
- **Playable sides:** United States or Iran, with a described IKE PBEM option.
- **Scale:** Five sides, 154 units.
- **Database reported in release:** DB3000 v515.
- **Premise:** A US-supported convoy attempts to pass through the Strait of Hormuz while Iran contests mine clearance and transit.
- **Design:** The importance of two US mine-countermeasure ships, regional political restraint, escalation thresholds, scripted choices and a linked Gulf of Aden threat create strategic constraints beyond missile exchanges.
- **Playtesting and revision:** The Matrix discussion documents a performance issue traced to excessive per-minute checks and a subsequent patch reducing the workload.

This scenario is a useful demonstration of Lua events, prompts, multi-sided decision logic, scoring and feedback-led optimization.

## Playing the published scenarios

Subscribe through each individual Steam Workshop page. Most items become available through CMO's Steam Workshop support. The Surovikin campaign's current release instructions additionally describe copying its campaign folder from the Workshop content directory into CMO's `Scenarios` directory to use the Campaigns interface.

These scenarios are separate from CONN: **players do not need to install CMO LLM Bridge just to play the published Workshop content**. CONN is primarily the author's creation and automation environment.

## References

- [jheinrichk's CMO Steam Workshop items](https://steamcommunity.com/profiles/76561198123053700/myworkshopfiles/?appid=1076160)
- [Matrix Games — Surovikin's Return](https://forums.matrixgames.com/viewtopic.php?t=418897)
- [Matrix Games — Hormuz 2026](https://forums.matrixgames.com/viewtopic.php?t=418898)
- [CMO LLM Bridge repository](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge)

The scenario narratives describe fiction, not predictions or verified real-world operational events.
