"""
conn.agents  -  commander profiles for LLM-driven sides.

A commander profile turns a side into a prompt: who it is, what it is trying
to do, what it may not do, and how many orders it gets this turn. The same
profile shape is used for player_vs_llm (one profile) and llm_vs_llm (two).

The situation report Lua is deliberately read-only. It is injected before the
order prompt so the commander reasons from the console output rather than from
assumptions about the scenario.
"""

SITREP_LUA = """-- CONN situation report (read only, indexed symbols only)
local side = '{side}'
local function sval(v) if v == nil then return '' end return tostring(v) end
print('=== SITREP for ' .. side .. ' ===')
local okT, t = pcall(GetScenarioTitle)
if okT then print('TITLE: ' .. sval(t)) end
local okN, n = pcall(ScenEdit_CurrentTime)
if okN then print('SCEN_TIME: ' .. sval(n)) end
local okS, sides = pcall(VP_GetSides)
if okS and type(sides) == 'table' then
  for _, sd in ipairs(sides) do
    print('SIDE: ' .. sval(sd.name))
    if sval(sd.name) == side then
      local units = sd.units or {{}}
      print('OWN_UNITS: ' .. tostring(#units))
      for i, u in ipairs(units) do
        if i <= 60 and u then
          print(string.format('UNIT|%s|%s|%s', sval(u.name), sval(u.type),
            sval(u.guid)))
        end
      end
      local ms = sd.missions or {{}}
      print('OWN_MISSIONS: ' .. tostring(#ms))
      for _, m in ipairs(ms) do
        if m then
          print(string.format('MISSION|%s|%s|active=%s', sval(m.name),
            sval(m.typeS or m.type), sval(m.isactive)))
        end
      end
    end
  end
else
  print('CMO_ERROR|FUNCTION=' .. sval(_errfnc_) .. '|NUMBER=' .. sval(_errnum_) ..
        '|MESSAGE=' .. sval(_errmsg_))
end
local okC, cs = pcall(ScenEdit_GetContacts, side)
if okC and type(cs) == 'table' then
  print('CONTACT_COUNT: ' .. tostring(#cs))
  for i, c in ipairs(cs) do
    if i <= 40 and c then
      print(string.format('CONTACT|%s|%s|%s', sval(c.name), sval(c.type),
        sval(c.posture)))
    end
  end
end
print('SITREP_END')
"""
ORDER_CONTRACT = (
    "MODE:CONN_COMMANDER\n"
    "ROLE:YOU_COMMAND_ONE_SIDE_IN_A_RUNNING_CMO_SCENARIO\n"
    "GROUNDING:USE_ONLY_THE_RETRIEVED_CMO_CONTEXT_AND_THE_SITREP_BELOW\n"
    "RETURN:FIRST_EXECUTABLE_LUA_CODE_BLOCK_ONLY\n"
    "HARD_LIMIT:EDITOR_FUNCTIONS_ARE_FORBIDDEN;NO_UNIT_CREATION;NO_SCORE_EDITS;"
    "NO_SIDE_EDITS;ORDERS_ONLY\n"
    "API_FACTS:CMO_API_IS_CALLABLE_USERDATA;USE_ONLY_INDEXED_SYMBOLS;"
    "VP_GetSides_RETURNS_WRAPPERS\n"
    "ORDERS_MAY:CREATE_OR_EDIT_MISSIONS;ASSIGN_UNITS;SET_DOCTRINE_AND_WRA;SET_EMCON;"
    "SET_COURSES_AND_SPEEDS;SET_RTB\n"
    "REQ:PRINT_EACH_ORDER_AS_IT_EXECUTES;WRAP_CRITICAL_CALLS_IN_PCALL\n"
    "REQ:END_WITH_A_LINE_'TURN_INTENT:<one sentence>'\n"
    "EVIDENCE:THE_SITREP_IS_A_FULL_STATUS_REPORT:TIME,SCORE,LOSSES,KILLS,ORDER_OF_BATTLE,CONTACTS,MISSIONS,"
    "AND_IT_ENDS_WITH_THE_MESSAGE_LOG_SINCE_YOUR_LAST_TURN;"
    "PRINT_'BRIDGE_ATTACH: MAPSHOT'_FOR_A_MAP_SCREENSHOT_NEXT_TURN\n"
    "OUTPUT:CODE_FIRST;NO_PROSE_BEFORE_CODE"
)


class Commander:
    def __init__(self, side, profile, order_budget=12):
        self.side = side
        self.profile = profile or {}
        self.order_budget = order_budget

    @property
    def label(self):
        return self.profile.get("label", self.side + " Commander")

    def sitrep_lua(self):
        # the full status report: time, score, losses and kills, order of
        # battle with positions, fuel, damage and mounts, contacts, missions
        from .status_lua import status_lua
        return status_lua(self.side)

    def order_prompt(self, turn_no, sitrep_text, rag_context="", history=""):
        p = self.profile
        return "\n".join([
            ORDER_CONTRACT,
            "",
            "COMMANDER: {}".format(self.label),
            "SIDE: {}".format(self.side),
            "PERSONA: {}".format(p.get("persona", "")),
            "OBJECTIVES: {}".format(p.get("objectives", "")),
            "RULES_OF_ENGAGEMENT: {}".format(p.get("roe", "")),
            "ORDER_BUDGET_THIS_TURN: {} discrete orders maximum".format(self.order_budget),
            "TURN: {}".format(turn_no),
            "",
            rag_context or "",
            "",
            "PRIOR_TURN_INTENTS:\n{}".format(history or "(none)"),
            "",
            "SITREP_FROM_CONSOLE:\n{}".format(sitrep_text or "(no sitrep captured)"),
        ])


def build_commanders(cfg):
    """Return {side_name: Commander} from config."""
    out = {}
    budget = int(cfg.get("play.order_budget_per_turn", 12))
    mapping = {
        cfg.get("play.my_side", "Blue"): cfg.get("play.agents.blue", {}),
        cfg.get("play.opponent_side", "Red"): cfg.get("play.agents.red", {}),
    }
    for side, prof in mapping.items():
        out[side] = Commander(side, prof, budget)
    return out
