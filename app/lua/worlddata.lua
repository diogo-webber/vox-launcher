local function SendData(data)
    print(string.format("VoxLauncherData=%s", json.encode(data)))
end

local function GetNumPlayers()
    return TheNet:GetPlayerCount() .." / ".. (TheNet:GetDefaultMaxPlayers() or "?")
end

local function GetSeason()
    return STRINGS.UI.SERVERLISTINGSCREEN.SEASONS[string.upper(TheWorld.state.season)] or "?"
end

local function GetCurrentDay()
    return TheWorld.state.cycles + 1
end

local function SendInitialData()
    SendData({
        players = GetNumPlayers(),
        season  = GetSeason(),
        day     = GetCurrentDay(),
    })
end

local function OnPlayerCountChanged(world, data)
    SendData({ players = GetNumPlayers() })
end

local function OnSeasonChanged(world, season)
    SendData({ season = GetSeason() })
end

local function OnDayChanged(world, cycles)
    SendData({ day = GetCurrentDay() })
end

if not TheWorld._vox_launcher then
    TheWorld:ListenForEvent("ms_playercounts", OnPlayerCountChanged)
    TheWorld:WatchWorldState("cycles", OnDayChanged)
    TheWorld:WatchWorldState("season", OnSeasonChanged)

    TheWorld._vox_launcher = true
end

VoxLauncher_GetServerStats = SendInitialData
VoxLauncher_UpdatePlayerCount = OnPlayerCountChanged

SendInitialData()