-- CMO CommandLua recipes: topic 'ui_messages'

-- --- 12.26 `ScenEdit_PlaySound()`, `ScenEdit_MsgBox()`, `ScenEdit_InputBox()`, `ScenEdit_SpecialMessage()` ---
ScenEdit_MsgBox('This is a test message')

-- --- 16.1 Popup message box ---
ScenEdit_MsgBox('Enemy raid detected')

-- --- 16.2 Input box ---
local answer = ScenEdit_InputBox('Enter reinforcement callsign', 'Reserve #3')
print(answer)

-- --- 16.4 Play a sound ---
ScenEdit_PlaySound('alarm.wav')

-- --- 16.5 Bark notification on a unit ---
ScenEdit_CreateBarkNotification_Unit({
    side = 'Blue',
    unitname = 'Eagle #1',
    text = 'Bandits detected'
})

-- --- 21.1 Find a unit by name and return its GUID ---
function get_unit_guid(side_name, unit_name)
    local unit = ScenEdit_GetUnit({ side = side_name, unitname = unit_name })
    if unit then
        return unit.guid
    end
    return nil
end

