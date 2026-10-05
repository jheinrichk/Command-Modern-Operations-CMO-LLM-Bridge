# CMO LUA :: VERIFIED SESSION KNOWLEDGE
### Everything this project established the hard way, on CMO v1.09 / DB3000 v515

Each entry below was **observed in play**, not inferred. Where I asserted a cause
and was wrong, the retraction is recorded too, because the wrong hypotheses cost
more cycles than the right ones saved.

Paste the whole file into the mission field, or keep it alongside the bridge and
paste the sections that apply.

---

## 1. DOCTRINE

**Mission-level doctrine overrides side-level doctrine.** This is the single most
expensive lesson of the project. Setting `ScenEdit_SetDoctrine({side='Iran'}, ...)`
does nothing for units that are on a mission whose own doctrine says hold. A
mission built with `weapon_control_status_surface = 2` will not fire even when the
side is weapons-free and the mission is active. Symptoms look like "the swarm
launched but nothing attacked" and "the salvo never fired". Always set doctrine on
the **mission** as well as the side.

```lua
ScenEdit_SetDoctrine({ side = S, mission = M }, { weapon_control_status_surface = 0 })
```

**WCS values.** 0 = free, 1 = tight, 2 = hold. Weapons-tight still fires on
anything auto-classified hostile, which is enough to shoot down a civil airliner.
If something must never fire, use 2, not 1.

**A side-wide air release is dangerous with civil traffic present.** An action that
frees air weapons side-wide puts every SAM battery onto airliners. A small-boat
swarm has no reason to touch air doctrine; scope each release to the warfare domain
it actually needs.

**Doctrine can be read back.** `ScenEdit_GetDoctrine` returns a table with the same
field names. Always verify rather than trusting the setter's return.

---

## 2. POSTURE

**Postures drift during a run.** Iran↔Merchant was verified Neutral at H-hour and
found Hostile hours later, with nothing in the scripts changing it. Re-assert
critical postures periodically rather than setting them once at build.

**Hostile posture toward a neutral side makes its units valid targets.** With
Merchant hostile, Iranian coastal batteries spent 12 anti-ship missiles, 144
rockets and 654 shells on Iran's own detained merchant ships anchored in harbour,
because those were the nearest valid contacts.

**Posture is per-viewer for map colour.** Blue on the map means "friendly or
neutral to the side you are currently viewing as", not a property of the unit.

---

## 3. MISSIONS

**Assign units at build, not at runtime inside an event.** A mission that gets its
units from a script running inside a prompt can end up empty. Assign at build with
the mission inactive; activating then costs one flag instead of sixteen
reassignments that may not take.

**A unit belongs to one mission.** Assigning to a second moves it off the first.
Two missions that both want the same hulls will silently starve one of them.

**`ScenEdit_GetMission(...).unitlist` and `.targetlist` are countable** and are the
reliable way to confirm a mission is actually populated. Do this before trusting
any mission to do anything.

**Patrol subtypes confirmed on this build:** `AAW`, `ASW`, `SEAD`. Strike type
`land`. Others including `surface`, `asuw`, `Mine`, `MineClear`, `MCM`,
`SeaControl` and `Recon` are rejected with "missing mission sub-type".

**Mission zone binding does not work reliably.** Inline `zone`, inline `Zone`,
`SetMission` with either spelling, and reference-point GUIDs all produced
`zonepts = 0`. Aircraft still fly their missions correctly without it. Do not
spend cycles on this.

---

## 4. UNITS AND MOVEMENT

**Never judge movement from a readback in the same script that issued the order.**
A ship ordered to cruise reads `FullStop` and speed 0 microseconds later. This
error was made twice and produced two false "throttle is broken" diagnoses.
Judge movement in the *next* cycle.

**`ScenEdit_SetUnit` with `course` and `manualthrottle` works** on ships and
aircraft. Throttle 0 = stop, 2 = cruise, 3 = flank.

**`ScenEdit_SetUnit` with `base` works for aircraft on this build**, despite being
undocumented. The base wrapper is returned by `unit.base` and you must read
`.name` off it, or you will print the entire wrapper into your log.

**Aircraft with no home base fly until they run dry.** A route that ends anywhere
on the map leaves them loitering to exhaustion. Either give them a destination
airfield on their own side, or route them past the map edge.

**Placement is checked against terrain.** Ships placed on land and facilities
placed in water are both rejected at `ScenEdit_AddUnit`. Coastlines are finer than
they look: the Musandam peninsula, Qeshm and Larak all caught units that appeared
to be offshore. Expect to iterate.

---

## 5. EVENTS AND TRIGGERS

**`ScenLoaded` fires on a file load but NOT on a scenario reset.** A player who
restarts from the menu gets no opening event, so a scenario that depends on it for
setup is dead on restart. Add a backstop.

**`UnitRemainsInArea` with a `TD` in seconds works as a timer** when pointed at a
static facility that never moves. This is the reliable way to schedule timed
events; the `RegularTime` trigger's interval codes are undocumented.

**`UnitDestroyed` with only a side filter counts expended weapons as destroyed
units.** One run fired the Iranian-loss handler 176 times because Iran had spent
822 shells, rockets and missiles. Guard with `if tostring(u.type) == 'Weapon' then
return end`, or filter by `TargetType`.

**`ScenEdit_GetEvents` returns wrappers whose `description` is not the name you
passed to `ScenEdit_SetEvent`.** Matching on description will report your events as
missing when they exist. This produced a completely false "the opening events did
not build" diagnosis. Check several fields, or trust `SetTrigger` returning
"Existing event trigger" as proof the object is there.

**A failed trigger can take its event with it.** If a trigger references reference
points that do not exist yet, creation fails and the event in the same block may
not register. Create reference points before the triggers that use them.

**`UnitX()` inside an event action returns the unit that fired the trigger.** It is
documented and works.

---

## 6. SPECIAL ACTIONS AND PROMPTS

**`ScenEdit_MsgBox(text, 3)` is modal and pauses the simulation** while open.
Returns 6 for Yes, 7 for No, 2 for Cancel. This is what makes prompt-driven
scenarios possible.

**`ScenEdit_SpecialMessage(side, html)` renders HTML**, including
`<img src="file:///...">` for local images and animated GIFs. The scenario
description field renders HTML too. Side **briefing** fields do not: they are
plain text, and there is no Lua setter for them or for the description.

**`ScenEdit_GetSpecialAction` needs `mode = 'list'`.** Without it the query returns
nothing and you will conclude your special actions were never created.

**`ScenEdit_PlayerSide()` tells you whether the human is on this side**, which is
how a prompt decides between showing a box and taking an AI default.

---

## 7. SCENARIO AND TIME

**Set both the current time and the start time.** `ScenEdit_SetTime` with only
`StartDate`/`StartTime` leaves the current time at the real-world clock. If that is
past start plus duration, the scenario ends on its first tick. Symptom: a freshly
built scenario immediately shows "The scenario has concluded".

**`VP_RunSimulation` and `VP_PauseSimulation` are Professional Edition only** and
are nil on Standard. Lua cannot start or stop the clock there.

**`VP_SetTimeCompression` exists and returns true**, but the UI may not reflect it.
Do not trust the return value as proof the compression took.

**Play and pause are one toggle button at one screen location.** Any automation
that clicks it must track state, and that state desyncs the moment a human clicks
it manually.

---

## 8. THE API SURFACE

**CMO API symbols are callable userdata, not Lua functions.** `type(x) == 'function'`
is false for every one of them. Probe existence with `_G[name] ~= nil`. This single
error made a working `VP_SetTimeCompression` report itself as missing for an entire
session.

**Confirmed absent on this build:** `ScenEdit_GetEventActions`,
`ScenEdit_GetLoadouts`, `ScenEdit_GetAircraftLoadouts`, `ScenEdit_QueryUnitDB`,
`ScenEdit_GetDatabaseInfo`, `VP_GetLoadout`.

**`ScenEdit_QueryDB` handles weapons, mounts and sensors only.** There is no Lua
route to look up a unit class or its DBID. Those must come from the database viewer
or a prior extraction.

**`UI_OpenNewDatabaseWindow(type, dbid)` opens one specific entry.** It is not a
search window.

---

## 9. DATABASE IDENTIFIERS

**DBIDs are namespaced per platform type.** Ship 3226 and aircraft 3226 are
different things. Any validation must compare within type.

**Name searches return the wrong national variant constantly.** In one pass of nine
aircraft: the P-8A was South Korean, the MQ-9A French, the F-35A Norwegian, the
F-35C listed under a "Junkyard" operator, and the MH-60R was flagged Hypothetical.
Every one is named exactly what you expect. Always check `operator_country`,
`operator_service`, `hypothetical` and `deprecated`.

**A wrong-nation aircraft carries wrong-nation weapons.** The South Korean P-8A
came with a K-745 Blue Shark torpedo, which is how the error was noticed at all.

**Aircraft loadouts must be validated against the airframe.** The
aircraft-to-loadout relation is a separate table; a loadout ID alone means nothing.
Loadout 3 is "Reserve" and 4 is "Maintenance" — both mean unarmed, and an aircraft
holding one will not generate sorties.

**Weapon quantities live in `DataWeaponRecord.DefaultLoad`.** A `quantity` column
in a naive extraction is a component index, not a count.

---

## 10. PROCESS RULES, EARNED

**Measure before asserting a cause.** Five hypotheses were asserted and disproven
in this project: loadout, base condition, doctrine, detection and proximity, all
for a single "units will not act" symptom. The actual cause was found by measuring
ranges and reading target lists.

**A silent success is not a success.** `SetUnit`, `SetDoctrine` and
`AssignUnitAsTarget` all return true while doing nothing. Read the value back every
time.

**Report failures loudly at build time.** A build that printed `created=150
failed=0` while 25 units were missing wasted a full session. Print the side, type,
name, DBID and the full CMO error for every failure.

**An empty target list means the AI takes the nearest contact.** Coastal batteries
with no assigned targets will shoot whatever is closest, including their own side's
detained ships.

**Check the state flags before "correcting" state.** Six missions were switched off
because an earlier expectation said zero should be active, when in fact the opening
event had legitimately activated them. `h26_opened` said so and was not read.

**Size a run window to the next decision point, minus a margin.** Windows longer
than the gap consume the decision unattended and the AI default is taken for both
sides. This spoiled two full playtest runs.

## 11. SCENARIO SETUP FROM LUA (learned 20 Sep 2026, v1.09 build 1825.15)

- **`ScenEdit_UpdateRSetting(name, bool)` sets every realism option.** Documented names: DetailedGunFireControl, UnlimitedBaseMagazines, AircraftDamage, RealisticSubComms, LandTypeEffects, LandTypeEffects_Advanced, CommsDisruption, WeatherAffectsShipSpeed, ACS_NAW_Limitations, AllowLandingPlannerInstantLoading (Pro only). Undocumented names this build accepts: **CommsJamming, DroneAutonomyLevels, VariableBurnoutSpeed, ASCMTerrainFollowingRestriction**. The function returns true only for a valid name, so probing is safe. A rebuild resets them; set them in the build.

- **`ScenEdit_SetSideOptions({side=, computerControlledOnly=true})` makes a side non-selectable**, and `proficiency=` sets its skill; both read back on the Side wrapper. No editor ticking needed.

- **`ScenEdit_RunScript(fullpath, true)` runs a file from anywhere** (customPath=true), so a one-line console command chains build, embed, settings and `Command_SaveScen(path)`. The Lua console's paste limit and the Load Script dialog both disappear.

- **No Lua field exists for the scenario description or a side briefing.** The live wrapper field lists (`obj.fields`) were probed on this build: nothing description-like on the Scenario wrapper, nothing briefing-like on the Side wrapper. Those two remain pastes through Edit HTML.

- **Play-mode HTML is a WebView2 page with no origin.** Chromium refuses file:// images for it ("Not allowed to load local resource"); the editor's older control allows them, which is why pictures show in the editor and not in play. Embed pictures as data: URLs, stored in the keystore for prompt windows and inline for briefings and the description. A 1 MB keystore value was accepted.
