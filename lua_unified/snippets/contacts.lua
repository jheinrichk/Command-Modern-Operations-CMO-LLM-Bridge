-- CMO CommandLua recipes: topic 'contacts'

-- --- 12.30 `ScenEdit_AttackContact()` ---
local contact = ScenEdit_GetContact({side='BLUE', guid='CONTACT-GUID-HERE'})
if contact then
    ScenEdit_AttackContact('BLUE UNIT GUID HERE', contact.guid, {
        mode = 0,
        weapon = 51,
        qty = 2
    })
end

-- --- 13.15 Get contacts ---
local con = ScenEdit_GetContacts('south korea')

-- --- 14.9 Recipe: query current contacts and attack one ---
local cons = ScenEdit_GetContacts('BLUE')
if cons then
    for i, con in pairs(cons) do
        if con.type == 'Ship' or con.type == 2 then
            print('Attacking contact', con.name, con.guid)
            -- replace unit guid and weapon data as needed
            ScenEdit_AttackContact('ATTACKER-UNIT-GUID', con.guid, {
                mode = 0,
                weapon = 51,
                qty = 2
            })
            break
        end
    end
end

-- --- 4.3 Contact selector ---
local contact_selector = {
    side = 'Blue',
    guid = 'contact-guid-here'
}

-- --- 10.1 Get a known contact ---
local contact = ScenEdit_GetContact({
    side = 'Blue',
    guid = 'contact-guid-here'
})

if contact then
    print(contact.name)
    print(contact.posture)
end

-- --- 10.3 Attack a contact ---
ScenEdit_AttackContact('Blue', 'Eagle #1', {
    mode = 0,
    contactguid = 'contact-guid-here'
})

-- --- 10.4 Attack with explicit mount and weapon choice ---
ScenEdit_AttackContact('Blue', 'Eagle #1', {
    mode = 1,
    contactguid = 'contact-guid-here',
    mount = 12345,
    weapon = 678,
    qty = 2
})

