if TheNet:GetPlayerCount() <= 0 then
    c_rollback({value})
else
    SetServerPaused(false)
    TheWorld:DoTaskInTime(5, function() c_rollback({value}) end)
end