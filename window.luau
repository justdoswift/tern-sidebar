local Order = require("./order")
local last_order = nil
local busy = {}
local unread = {}
local focused_tab = nil

local function observe(tab)
	local previous = busy[tab.id]
	busy[tab.id] = tab.busy
	if tab.busy then
		unread[tab.id] = nil
	elseif previous and tab.id ~= focused_tab then
		unread[tab.id] = true
	end
	return previous ~= nil and previous ~= tab.busy
end

local function update_order(cx)
	local focused = cx.session:pane("@focused")
	local tabs = cx.session:tabs()
	local present = {}
	for _, tab in tabs do
		observe(tab)
		present[tab.id] = true
	end
	for id in busy do
		if not present[id] then
			busy[id] = nil
			unread[id] = nil
		end
	end
	-- Observe completion against the previously shown tab before acknowledging
	-- the new focus; a completion rendered during a switch was already visible.
	focused_tab = focused and focused.tab or nil
	if focused_tab then unread[focused_tab] = nil end
	local css = Order.styles(cx.sessions:list(), cx.hosts:list(), tabs, unread)
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

-- The formatter is invalidated by native busy changes, including OMP turns.
-- Returning nil preserves Tern's title and lets other title formatters run.
tern.chrome.tab_title(function(tab)
	if observe(tab) then queue_order() end
	return nil
end)

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

local sidebar_auto = false
local function sync_sidebar(cx)
	local value = cx.settings:get("tabs_autohide")
	if value ~= sidebar_auto then
		sidebar_auto = value
		tern.chrome.refresh()
	end
end

tern.command({
	id = "toggle_sidebar",
	title = "展开／折叠侧栏 / Toggle sidebar",
	icon = "sidebar",
	available = function(cx)
		return cx.settings:get("tabs") == "Vertical"
	end,
	run = function(cx)
		cx.settings:set("tabs_autohide", not cx.settings:get("tabs_autohide"))
		sync_sidebar(cx)
	end,
})

tern.chrome.status(function()
	return { {
		text = sidebar_auto and "展开侧栏 / Expand sidebar" or "折叠侧栏 / Collapse sidebar",
		icon = "sidebar",
		tone = sidebar_auto and "muted" or "accent",
		command = "plugin.tern-sidebar.toggle_sidebar",
	} }
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
		sync_sidebar(cx)
	end
	tern.timer(1000, sync)
end
tern.timer(0, sync)
