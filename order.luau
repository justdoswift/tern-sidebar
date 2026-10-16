local Order = {}

-- Tern 0.8.4 paints each host's current session first, followed by its
-- remaining sessions in API order. Keep visual order in that API order.
function Order.styles(sessions, hosts)
	local groups = {}
	for _, host in hosts do
		local members = {}
		for _, session in sessions do
			if session.host == host.id then
				table.insert(members, session)
			end
		end
		if #hosts > 1 then
			table.insert(groups, { kind = "tn-vt-host", rank = #groups + 1 })
		end
		local first = #groups
		for index, session in members do
			if session.current then
				table.insert(groups, { kind = "nav-group", rank = first + index })
			end
		end
		for index, session in members do
			if not session.current then
				table.insert(groups, { kind = "nav-group", rank = first + index })
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
	end
	return table.concat(rules, "\n")
end

return Order
