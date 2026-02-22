-- Force preview to fullscreen (idempotent, no toggle)
-- Unlike toggle-pane, this always sets max-preview state regardless of current state
--- @sync entry

local function entry(st, job)
	local R = rt.mgr.ratio

	-- Initialize state on first call
	st.parent = st.parent or R.parent
	st.current = st.current or R.current
	st.preview = st.preview or R.preview

	-- Always maximize preview (idempotent)
	st.preview = 65535

	-- Replace layout function only once
	if not st.old then
		st.old = Tab.layout
		Tab.layout = function(self)
			local all = st.parent + st.current + st.preview
			self._chunks = ui.Layout()
				:direction(ui.Layout.HORIZONTAL)
				:constraints({
					ui.Constraint.Ratio(st.parent, all),
					ui.Constraint.Ratio(st.current, all),
					ui.Constraint.Ratio(st.preview, all),
				})
				:split(self._area)
		end
	end

	ya.emit("app:resize", {})
end

return { entry = entry }
