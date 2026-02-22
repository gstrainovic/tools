--- @sync entry
return {
	entry = function(st, job)
		local arg = job and job.args and job.args[1]

		-- Reset: restore original layout
		if arg == "reset" then
			if st.old then
				Tab.layout = st.old
				st.old = nil
				st.parent, st.current, st.preview = nil, nil, nil
				ui.render()
			end
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
