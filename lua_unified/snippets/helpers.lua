-- CMO CommandLua recipes: topic 'helpers'

-- --- 21.2 Safe print of CommandLua error state ---
function print_last_commandlua_error()
    print('Function: ' .. tostring(_errfnc_))
    print('Message: ' .. tostring(_errmsg_))
    print('Number: ' .. tostring(_errnum_))
end

