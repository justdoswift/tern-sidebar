local Order = {}

-- Native DOM order is current-first, then API order. Display newest-first
-- within each host without letting focus change a session's position.
function Order.styles(sessions, hosts, tabs, unread, show_older, current_session)
	local groups = {}
	local older_count = 0
	local current_is_older = false
	for _, host in hosts do
		local members = {}
		for _, session in sessions do
			if session.host == host.id then
				table.insert(members, session)
			end
		end
		older_count += math.max(0, #members - 3)
		if #hosts > 1 then
			table.insert(groups, { kind = "tn-vt-host", rank = #groups + 1 })
		end
		local first = #groups
		local function group(index, session)
			local older = index <= #members - 3
			if older and session.id == current_session then current_is_older = true end
			return {
				kind = "nav-group",
				rank = first + #members - index + 1,
				session = session,
				hidden = older and not show_older,
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
		if group.hidden then
			table.insert(rules, selector .. " { display: none; }")
		end
		if group.session then
			for _, tab in tabs do
				if tab.session == group.session.id and unread[tab.id] then
					-- A tab filter can also remove rows within an otherwise complete
					-- group. Require the full row count before using its position.
					local row = selector .. " > .nav-items > div > .nav-row:nth-child(" .. tab.position
						.. "):nth-last-child(" .. (group.session.tabs - tab.position + 1) .. ")"
					table.insert(rules, row .. " { --tern-sidebar-unread: block; }")
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
