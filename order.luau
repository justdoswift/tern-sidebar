local Order = {}

-- Native DOM order is current-first, then API order. Display newest-first
-- within each host without letting focus change a session's position.
function Order.styles(sessions, hosts, tabs, unread, show_older, current_tab)
	local groups = {}
	local older_count = 0
	local current_is_older = false
	for _, host in hosts do
		local members = {}
		for _, session in sessions do
			if session.host == host.id then
				table.insert(members, session)
				older_count += math.max(0, session.tabs - 3)
			end
		end
		if #hosts > 1 then
			table.insert(groups, { kind = "tn-vt-host", rank = #groups + 1 })
		end
		local first = #groups
		local function group(index, session)
			return {
				kind = "nav-group",
				rank = first + #members - index + 1,
				session = session,
			}
		end
		for index, session in members do
			if session.current then
				table.insert(groups, group(index, session))
			end
		end
		for index, session in members do
			if not session.current then
				table.insert(groups, group(index, session))
			end
		end
	end

	local rules = {}
	local root = "#sidebar > nav.tn-vt > "
	-- Search omits nonmatching groups. Apply positional rules only when every
	-- expected child is present; never assign another session's position.
	for index, group in groups do
		local selector = root .. "." .. group.kind .. ":nth-child(" .. index
			.. "):nth-last-child(" .. (#groups - index + 1) .. ")"
		table.insert(rules, selector .. " { order: " .. group.rank .. "; }")
		if group.session then
			for _, tab in tabs do
				if tab.session == group.session.id then
					-- Filters can remove rows from a group: order/hide only when
					-- the entire expected tab list is still present.
					local rank = group.session.tabs - tab.position + 1
					local row = selector .. " > .nav-items > div > .nav-row:nth-child(" .. tab.position
						.. "):nth-last-child(" .. rank .. ")"
					table.insert(rules, row .. " { order: " .. rank .. "; }")
					if rank > 3 then
						if tab.id == current_tab then current_is_older = true end
						if not show_older then
							table.insert(rules, row .. " { display: none; }")
						end
					end
					if unread[tab.id] then
						table.insert(rules, row .. " { --tern-sidebar-unread: block; }")
					end
				end
			end
		end
	end
	if older_count > 0 then
		table.insert(rules, "html.tabs-v #sidebar > nav.tn-vt { margin-bottom: 36px; }")
	end
	return table.concat(rules, "\n"), older_count, current_is_older
end

return Order
