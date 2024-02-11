local function SendData(data)
    print(string.format("VoxLauncherData=%s", json.encode(data)))
end

local function GetCurrentPlayers()
    local _secondaryShardPlayers, _secondaryShardGhosts = TheShard:GetSecondaryShardPlayerCounts(USERFLAGS.IS_GHOST)
end

local function SendInitialData()
    SendData({
            players = math.max(0, #TheNet:GetClientTable() - 1) .." / ".. (TheNet:GetDefaultMaxPlayers() or "?"),
            season = STRINGS.UI.SERVERLISTINGSCREEN.SEASONS[string.upper(TheWorld.state.season)] or "?",
            day = TheWorld.state.cycles + 1,
    })
end

local function OnPlayerCountChanged(world, data)
    SendData({ players = (data.total or "?") .." / ".. (TheNet:GetDefaultMaxPlayers() or "?") })
end

local function OnDayChanged(world, cycles)
    SendData({ day = cycles + 1 })
end

local function OnSeasonChanged(world, season)
    SendData({ season = STRINGS.UI.SERVERLISTINGSCREEN.SEASONS[string.upper(season)] or "?" })
end

if not TheWorld._vox_launcher then
    TheWorld:ListenForEvent("ms_playercounts", OnPlayerCountChanged)
    TheWorld:WatchWorldState("cycles", OnDayChanged)
    TheWorld:WatchWorldState("season", OnSeasonChanged)

    TheWorld._vox_launcher = true
end

VoxLauncher_GetServerStats = SendInitialData

SendInitialData()