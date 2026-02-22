--- @sync entry
return {
	entry = function(st, job)
		if st.old then
			Tab.layout, st.old = st.old, nil
		else
			st.old = Tab.layout
			Tab.layout = function(self)
				self._chunks = ui.Layout()
					:direction(ui.Layout.HORIZONTAL)
					:constraints({
						ui.Constraint.Percentage(0),
						ui.Constraint.Percentage(0),
						ui.Constraint.Percentage(100),
					})
					:split(self._area)
			end
		end
		ui.render()
	end,
}
