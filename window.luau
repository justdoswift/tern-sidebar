local Order = require("./order")
local last_order = nil

local function update_order(cx)
	local css = Order.styles(cx.sessions:list(), cx.hosts:list())
	if css ~= last_order then
		tern.css("session-order", css)
		last_order = css
	end
end

local queued = false
local function queue_order()
	if queued then return end
	queued = true
	-- Coalesce lifecycle events and inspect the resulting state with a fresh cx.
	tern.timer(0, function(cx)
		queued = false
		if cx then update_order(cx) end
	end)
end

local function create_session(cx)
	local pane = cx.session:pane("@focused")
	local cwd = pane and pane.cwd or nil
	cx.sessions:create({ cwd = cwd ~= "" and cwd or nil })
	update_order(cx)
end

tern.command({
	id = "new_session",
	title = "新建会话 / New session",
	icon = "plus",
	keys = { "ctrl+alt+n" },
	run = create_session,
})

tern.chrome.status(function()
	return {
		{
			text = "新建会话",
			icon = "plus",
			tone = "tern-sidebar-new",
			command = "plugin.tern-sidebar.new_session",
		},
	}
end)

for _, event in { "focus", "pane_created", "pane_closed", "tab_created", "tab_closed" } do
	tern.on(event, function()
		queue_order()
	end)
end

-- A daemon can add/remove sessions without a local focus or tab event.
-- Reload cancels old timers; starting here also handles plugin reloads.
local function sync(cx)
	if cx then
		update_order(cx)
	end
	tern.timer(1000, sync)
end
tern.timer(0, sync)
