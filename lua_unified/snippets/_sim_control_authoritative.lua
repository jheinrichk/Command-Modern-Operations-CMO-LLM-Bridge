-- =====================================================================
-- CMO SIMULATION CONTROL — AUTHORITATIVE PATTERNS
-- Hand-authored for the LLM bridge. Grounded in confirmed CommandLua
-- function names from the master library v3 (sections 11.10, 11.11).
--
-- IMPORTANT EDITION NOTE:
--   VP_RunSimulation / VP_PauseSimulation / VP_RunForTimeAndHalt /
--   VP_RunToTimeAndHalt are listed under "Professional Edition only".
--   VP_SetTimeCompression is available in the standard branch.
--   If a VP_ call errors (nil global), the bridge falls back to UI-click
--   control via calibrated coordinates (cmo_play / cmo_pause / cmo_time_*).
-- =====================================================================

-- --- Guarded runner: call a global only if it exists ---
-- FIXED: CMO API symbols are CALLABLE USERDATA, not Lua functions.
-- type(x)=="function" is FALSE for every CMO symbol, which made this
-- helper report SIMCTL_MISSING for functions that actually exist
-- (VP_SetTimeCompression demonstrably works). Test existence instead.
local function _has(fn) return _G[fn] ~= nil end
local function _try(fn, ...)
    if _has(fn) then
        local ok, err = pcall(_G[fn], ...)
        if not ok then print("SIMCTL_ERR:" .. fn .. ":" .. tostring(err)) end
        return ok
    end
    print("SIMCTL_MISSING:" .. fn)
    return false
end

-- --- PLAY: start / resume the simulation ---
function AGENT_SimPlay()
    return _try("VP_RunSimulation")
end

-- --- PAUSE: halt the simulation, scenario stays loaded ---
function AGENT_SimPause()
    return _try("VP_PauseSimulation")
end

-- --- TIME COMPRESSION: set a compression multiplier ---
-- Accepts a raw multiplier understood by the build (e.g. 1,2,5,15,30,60,300...).
function AGENT_SimSetCompression(mult)
    return _try("VP_SetTimeCompression", mult)
end

-- --- RUN FOR A FIXED WINDOW THEN HALT (Pro) ---
-- seconds = simulated seconds to advance before auto-pausing.
function AGENT_SimRunForAndHalt(seconds)
    return _try("VP_RunForTimeAndHalt", seconds)
end

-- --- RUN TO AN ABSOLUTE TIME THEN HALT (Pro) ---
-- ticks = value from ScenEdit_GetDateTimeTicks(...) target.
function AGENT_SimRunToAndHalt(ticks)
    return _try("VP_RunToTimeAndHalt", ticks)
end

-- --- SCENARIO LIFECYCLE ------------------------------------------------

-- STARTED? returns true if the scenario clock has begun.
function AGENT_ScenHasStarted()
    if _has("ScenEdit_GetScenHasStarted") then
        local ok, v = pcall(ScenEdit_GetScenHasStarted)
        if ok then return v end
    end
    return nil
end

-- RESET-BY-REBUILD: for generated/sandbox scenarios, tear down to a
-- fresh blank and re-seed. Real reset/reload of a saved .scen is done on
-- the bridge side (UI: File > reload) because CommandLua cannot reload a
-- save file from inside the running instance.
function AGENT_ScenRebuildBlank(title)
    if _has("Tool_BuildBlankScenario") then
        Tool_BuildBlankScenario(title or "LLM Bridge Sandbox")
        if _has("SetScenarioTitle") then SetScenarioTitle(title or "LLM Bridge Sandbox") end
        return true
    end
    print("SIMCTL_MISSING:Tool_BuildBlankScenario")
    return false
end

-- END the scenario (scores/verdict finalize).
function AGENT_ScenEnd()
    return _try("ScenEdit_EndScenario")
end

-- --- STATE BANNER: emit a machine-parseable status line for the bridge --
-- The bridge greps NEXT_RECOMMENDED_STATE and SIM_STATE from stdout.
function AGENT_SimBanner(next_state, note)
    local started = AGENT_ScenHasStarted()
    print("=== SIM BANNER ===")
    print("SCEN_STARTED: " .. tostring(started))
    if note then print("NOTE: " .. tostring(note)) end
    print("NEXT_RECOMMENDED_STATE: " .. tostring(next_state or "CONTINUE"))
    print("==================")
end

-- --- COMBINED: advance a test window at compression, then pause & banner
-- Preferred deterministic test step for the DEPLOY/TEST stages.
function AGENT_TestWindow(compression, seconds, next_state)
    AGENT_SimSetCompression(compression or 15)
    if _has("VP_RunForTimeAndHalt") then
        AGENT_SimRunForAndHalt(seconds or 300)   -- Pro: exact window
    else
        AGENT_SimPlay()                          -- Std: bridge times the pause
    end
    AGENT_SimBanner(next_state or "EVALUATE", "test window ~" .. tostring(seconds) .. "s")
end
