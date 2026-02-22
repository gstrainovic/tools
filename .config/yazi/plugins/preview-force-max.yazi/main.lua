--- @sync entry
return {
	entry = function(st, job)
		local arg = job and job.args and job.args[1]

		-- Reset: restore original layout from rt.mgr.ratio (yazi.toml values)
		if arg == "reset" then
			Tab.layout = function(self)
				local R = rt.mgr.ratio
				local all = R.parent + R.current + R.preview
				self._chunks = ui.Layout()
					:direction(ui.Layout.HORIZONTAL)
					:constraints({
						ui.Constraint.Ratio(R.parent, all),
						ui.Constraint.Ratio(R.current, all),
						ui.Constraint.Ratio(R.preview, all),
					})
					:split(self._area)
			end
			st.old = nil
			st.parent, st.current, st.preview = nil, nil, nil
			ui.render()
			return
		end

		-- Force max preview (idempotent)
		local R = rt.mgr.ratio
		st.parent = st.parent or R.parent
		st.current = st.current or R.current
		st.preview = st.preview or R.preview
		st.preview = 65535

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

		ui.render()
	end,
}
