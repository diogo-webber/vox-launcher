if TheNet:GetPlayerCount() <= 0 then -- Game is auto-paused.
	c_rollback({ value })
else
	SetServerPaused(false)
	TheWorld:DoTaskInTime(5, function()
		c_rollback({ value })
	end)
end
