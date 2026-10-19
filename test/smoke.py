#!/usr/bin/env python3
"""Opt-in native UI regression: opens only its own profile, daemon and window."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--native", action="store_true", required=True,
                    help="Allow opening and closing an isolated Tern window")
parser.parse_args()
TERN = shutil.which("tern")
if not TERN:
    raise SystemExit("tern must be on PATH")
OUT = ROOT / "artifacts" / "smoke"
OUT.mkdir(parents=True, exist_ok=True)


def eventually(check, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (OSError, ValueError, RuntimeError):
            pass
        time.sleep(0.05)
    raise AssertionError("Native operation did not reach its expected state")


def nodes(node):
    yield node
    for child in node.get("children", []):
        yield from nodes(child)


with tempfile.TemporaryDirectory(prefix="tsb-") as temp:
    work = Path(temp)
    config = work / "config"
    plugins = config / "plugins"
    plugins.mkdir(parents=True)
    # Tern watches linked sources recursively: screenshots written under ROOT
    # must not reload the plugin and erase the unread state being tested.
    shutil.copytree(ROOT, plugins / "tern-sidebar",
                    ignore=shutil.ignore_patterns("artifacts", "tern.d.luau", ".git"))
    control = work / "window.sock"
    daemon_socket = work / "daemon.sock"
    env = {k: v for k, v in os.environ.items() if not k.startswith("TERN_")}
    env.update(TERN_CONFIG_DIR=str(config), TERN_DAEMON_SOCKET=str(daemon_socket),
               STENCIL_LOG_DIR=str(work / "logs"))
    processes = []

    def ctl(command, *args):
        result = subprocess.run([TERN, "ctl", "--control", str(control), command, *args],
                                cwd=work, env=env, capture_output=True, text=True, timeout=25)
        payload = json.loads(result.stdout)
        if not payload.get("ok"):
            raise RuntimeError(payload.get("error", result.stderr))
        return payload

    def scenario(command, *args):
        return ctl(command, *(str(x) if isinstance(x, (int, float)) else
                              json.dumps(x, ensure_ascii=False) for x in args))

    def positions():
        groups = []
        for root in ctl("tree")["tree"]:
            if root.get("id") == "sidebar":
                for group in nodes(root):
                    if ("nav-group" in group.get("class", "").split()
                            and group["rect"][2] > 0 and group["rect"][3] > 0):
                        name = group["children"][0]["children"][0]["text"]
                        groups.append((name, group["rect"][1]))
        return sorted(groups, key=lambda row: row[1])

    def elements(selector):
        return ctl("dump", selector)["elements"]

    def assert_footer_button():
        control = elements(button)[0]
        sidebar = elements("#sidebar")[0]["rect"]
        search = elements("#sidebar .tn-vt-find")[0]["rect"]
        listing = elements("#sidebar > nav.tn-vt")[0]["rect"]
        x, y, width, height = control["rect"]
        assert control["visible"]
        assert sidebar[0] <= x and x + width <= sidebar[0] + sidebar[2]
        assert listing[1] + listing[3] <= y
        assert y == search[1] and height == search[3]
        assert search[0] + search[2] < x
        assert width == height

    def assert_header_toggle():
        control = elements(toggle)[0]
        switch = elements("#tabbar .tn-session-tab")[0]
        sx, sy, sw, sh = switch["rect"]
        x, y, width, height = control["rect"]
        assert control["visible"] and switch["visible"]
        assert elements("#tabbar")[0]["opacity"] == "1"
        assert 0 <= x - sx - sw <= 12
        assert abs(y + height / 2 - sy - sh / 2) <= 1
        assert x + width <= ctl("state")["viewport"][0]

    def sidebar_collapsed():
        x, _, width, _ = elements("#sidebar")[0]["rect"]
        return x + width <= 8

    def exercise_sidebar_toggle():
        before = ctl("state")
        pane_id = before["focused"]["id"]
        columns = next(p["cols"] for p in before["panes"] if p["id"] == pane_id)
        assert_header_toggle()
        scenario("click", toggle)
        scenario("move", 500, 200)
        eventually(sidebar_collapsed)
        assert_header_toggle()
        assert next(p["cols"] for p in ctl("state")["panes"] if p["id"] == pane_id) > columns
        assert not elements(button)[0]["visible"]
        assert ctl("state")["focused"]["id"] == before["focused"]["id"]
        assert ctl("state")["status_bar"] == before["status_bar"]
        scenario("click", toggle)
        eventually(lambda: elements("#sidebar")[0]["rect"][0] == 0)
        assert_header_toggle()
        assert_footer_button()
        assert ctl("state")["focused"]["id"] == before["focused"]["id"]

    def capture(name):
        shot = ctl("shot", name)
        for field in ("png", "layout"):
            source = work / shot[field]
            shutil.copy2(source, OUT / source.name)

    busy = '#sidebar .nav-row[aria-label$=" · working"] > .tn-tc'
    button = "#tabbar .tb-add"
    toggle = '#statusline .sl-plugin[title="plugin.tern-sidebar.toggle_sidebar"]'
    older = '#statusline .sl-plugin[title="plugin.tern-sidebar.toggle_older_sessions"]'
    def marker(title):
        return elements(f'#sidebar .nav-row[aria-label^="{title}"] > .tn-tc')[0]

    def unread_marker(title):
        value = marker(title)
        return value["visible"] and value["backgroundColor"] != "rgba(0, 0, 0, 0)"

    fixture = str(ROOT / "test" / "omp-progress.jsonl")
    try:
        with (OUT / "runtime.log").open("w") as log:
            daemon = subprocess.Popen([TERN, "daemon", "--socket", str(daemon_socket)],
                                      cwd=work, env=env, stdout=log, stderr=log)
            processes.append(daemon)
            eventually(daemon_socket.exists)
            window = subprocess.Popen([TERN, "--control", str(control), "--dir", str(work)],
                                      cwd=work, env=env, stdout=log, stderr=log)
            processes.append(window)
            eventually(lambda: control.exists() and ctl("state")["gate"]["phase"] == "off")
            ctl("ready")
            scenario("tabs", "vertical")
            scenario("tabs", "autohide", "off")
            scenario("status-bar", "off")
            eventually(lambda: elements("#sidebar")[0]["rect"][0] == 0)
            scenario("session", "rename", "Alpha")
            scenario("rename", "#1")
            cwd = ctl("state")["focused"]["cwd"]
            assert_footer_button()
            exercise_sidebar_toggle()
            capture("toggle-expanded-light")
            assert not any(item["visible"] for item in elements("#sidebar .nav-row > .tn-dk"))
            assert not ctl("state")["status_bar"]
            original_pane = ctl("state")["focused"]["id"]
            scenario("click", button)
            state = ctl("state")
            assert len(state["sessions"]) == 1 and state["sessions"][0]["tabs"] == 2
            assert state["focused"]["id"] != original_pane
            assert state["focused"]["cwd"] == cwd
            scenario("tab", "close")
            assert ctl("state")["focused"]["id"] == original_pane
            scenario("key", "ctrl+alt+n")
            assert len(ctl("state")["sessions"]) == 2
            scenario("session", "rename", "Beta")
            scenario("rename", "#2")
            scenario("key", "ctrl+alt+n")
            assert len(ctl("state")["sessions"]) == 3
            scenario("session", "rename", "Gamma")
            scenario("rename", "#3")
            baseline = eventually(lambda: positions() if [x[0] for x in positions()] ==
                                  ["Gamma", "Beta", "Alpha"] else None)
            for title in ("#1", "#2", "#3"):
                scenario("click", f'#sidebar .nav-row[aria-label="{title}"]')
                assert positions() == baseline, (title, positions(), baseline)
            print("PASS: footer creates a tab, shortcut creates a session, rows keep their positions")

            scenario("plugins", "run", "reload_plugins")
            assert eventually(lambda: positions() == baseline)
            scenario("filter", "#2")
            assert [row[0] for row in positions()] == ["Beta"]
            ctl("filter")
            assert positions() == baseline
            print("PASS: reload preserves order; filtering never assigns another group's position")

            scenario("session", "switch", "Alpha")
            scenario("surface-play", fixture, "until", "1")
            assert ctl("state")["focused"]["busy"]
            first = elements(busy)[0]
            assert first["visible"] and first["backgroundColor"] == "rgba(0, 0, 0, 0)"
            assert eventually(lambda: elements(busy)[0]["transform"] != first["transform"])
            scenario("session", "switch", "Beta")
            assert elements(busy)[0]["visible"]
            scenario("session", "switch", "Alpha")
            capture("working-light")
            scenario("surface-play", fixture, "from", "1", "until", "2")
            assert not elements(busy)
            scenario("surface-play", fixture, "from", "2", "until", "3")
            assert not ctl("state")["focused"]["busy"] and not elements(busy)
            print("PASS: OMP progress animates across sessions; waiting/idle stops the spinner")

            assert not marker("#1")["visible"]
            scenario("session", "switch", "Beta")
            assert not marker("#1")["visible"], "Foreground completion must stay read"
            scenario("session", "switch", "Alpha")
            scenario("surface-play", fixture, "paced", 0.25)
            scenario("session", "switch", "Beta")
            assert elements(busy)[0]["visible"]
            eventually(lambda: not elements(busy))
            assert not any(item["visible"] for item in elements("#sidebar .nav-row > .tn-tc")), \
                "Waiting for input is not a completed turn"
            eventually(lambda: unread_marker("#1"))
            completed = marker("#1")
            exercise_sidebar_toggle()
            assert unread_marker("#1"), "Collapsing the sidebar must not mark background work read"
            assert completed["backgroundColor"] != "rgba(0, 0, 0, 0)"
            assert completed["transform"] == "none"
            capture("unread-light")
            scenario("filter", "#2")
            assert not any(item["visible"] for item in elements("#sidebar .nav-row > .tn-tc"))
            ctl("filter")
            assert marker("#1")["visible"], "Filtering must not mark a completion read"
            scenario("click", '#sidebar .nav-row[aria-label^="#1"]')
            assert not marker("#1")["visible"]
            scenario("session", "switch", "Beta")
            assert not marker("#1")["visible"], "Read completion must not reappear"

            # A different tab in the same named session is also background work.
            scenario("session", "switch", "Alpha")
            scenario("tab", "new")
            scenario("rename", "Alpha other")
            scenario("click", '#sidebar .nav-row[aria-label^="#1"]')
            scenario("surface-play", fixture, "paced", 0.25)
            scenario("click", '#sidebar .nav-row[aria-label="Alpha other"]')
            eventually(lambda: unread_marker("#1"))
            assert not marker("Alpha other")["visible"]
            scenario("plugins", "run", "appearance:dark")
            ctl("resize", "720", "480")
            capture("unread-dark-short")
            scenario("click", '#sidebar .nav-row[aria-label^="#1"]')
            assert not marker("#1")["visible"]
            scenario("click", '#sidebar .nav-row[aria-label="Alpha other"]')
            assert not marker("#1")["visible"]
            scenario("tab", "close")
            print("PASS: background completion stays unread until opened; waiting and foreground completion do not")

            sidebar = elements("#sidebar")[0]["rect"]
            assert elements("#tabbar")[0]["rect"][0] == sidebar[0]
            assert elements("#tabbar .tn-session-tab")[0]["rect"][0] < sidebar[2]
            scenario("status-bar", "on")
            assert_footer_button()
            scenario("move", 500, 200)
            scenario("tabs", "autohide", "on")
            assert eventually(lambda: not elements(button)[0]["visible"])
            scenario("tabs", "autohide", "off")
            scenario("session", "rename", "长会话名称 — A very long session title that must not cover the toggle")
            for layout in ("rail", "studio", "float", "tiles"):
                scenario("layout", layout)
                assert_footer_button()
                exercise_sidebar_toggle()
            capture("toggle-long-title")
            scenario("session", "rename", "Alpha")
            scenario("tabs", "horizontal")
            header = elements("#tabbar")[0]["rect"]
            tab_button = elements(button)[0]["rect"]
            assert tab_button[1] + tab_button[3] <= header[1] + header[3]
            assert not any(item["visible"] for item in elements(toggle))
            scenario("tabs", "vertical")
            scenario("plugins", "run", "appearance:dark")
            scenario("surface-play", fixture, "until", "1")
            ctl("resize", "720", "480")
            capture("working-dark-short")
            assert_footer_button()
            assert elements(busy)[0]["visible"]
            assert not any(item["visible"] for item in elements("#sidebar .nav-row > .tn-dk"))
            exercise_sidebar_toggle()
            scenario("click", toggle)
            scenario("move", 500, 200)
            eventually(sidebar_collapsed)
            capture("toggle-collapsed-dark-short")
            assert_header_toggle()
            scenario("plugins", "run", "reload_plugins")
            eventually(sidebar_collapsed)
            assert_header_toggle()
            scenario("click", toggle)
            eventually(lambda: elements("#sidebar")[0]["rect"][0] == 0)
            assert_footer_button()
            print("PASS: adjacent header toggle, collapsed recovery, saved preference, status bar independence, unread retention")
            print("PASS: footer in all layouts, horizontal tabs, auto-hide, icon-free rows, dark/short window")
            scenario("surface-play", fixture, "from", "1", "until", "3")
            scenario("plugins", "run", "appearance:light")
            ctl("resize", "1280", "800")
            scenario("status-bar", "off")
            # The limit counts sessions, not tabs, and only hides the older ones.
            assert not elements(older)
            scenario("tab", "new")
            assert not elements(older)
            scenario("tab", "close")
            for name, title in (("Delta", "#4"), ("Epsilon", "#5")):
                scenario("session", "new", name)
                scenario("rename", title)
            recent = ["Epsilon", "Delta", "Gamma"]
            all_sessions = recent + ["Beta", "Alpha"]
            eventually(lambda: [row[0] for row in positions()] == recent)
            assert elements(older)[0]["visible"]
            pane_id = ctl("state")["focused"]["id"]
            scenario("click", older)
            assert [row[0] for row in positions()] == all_sessions
            assert ctl("state")["focused"]["id"] == pane_id
            scenario("palette", "Show or hide older sessions")
            scenario("key", "enter")
            assert [row[0] for row in positions()] == recent
            scenario("filter", "#1")
            assert [row[0] for row in positions()] == ["Alpha"]
            ctl("filter")
            assert [row[0] for row in positions()] == recent
            scenario("session", "switch", "Alpha")
            assert [row[0] for row in positions()] == all_sessions
            scenario("surface-play", fixture, "paced", 0.25)
            scenario("session", "switch", "Epsilon")
            scenario("click", older)
            assert [row[0] for row in positions()] == recent
            eventually(lambda: not elements(busy))
            scenario("click", older)
            eventually(lambda: unread_marker("#1"))
            scenario("click", '#sidebar .nav-row[aria-label^="#1"]')
            assert not marker("#1")["visible"]
            scenario("session", "switch", "Epsilon")
            scenario("click", older)
            scenario("plugins", "run", "reload_plugins")
            eventually(lambda: [row[0] for row in positions()] == recent)
            capture("recent-sessions-light")
            scenario("status-bar", "on")
            for layout in ("rail", "studio", "float", "tiles"):
                scenario("layout", layout)
                fold_control = elements(older)[0]
                sidebar = elements("#sidebar")[0]["rect"]
                listing = elements("#sidebar > nav.tn-vt")[0]["rect"]
                search = elements("#sidebar .tn-vt-find")[0]["rect"]
                x, y, width, height = fold_control["rect"]
                assert fold_control["visible"]
                assert sidebar[0] <= x and x + width <= sidebar[0] + sidebar[2]
                assert listing[1] + listing[3] <= y and y + height <= search[1]
                exercise_sidebar_toggle()
            scenario("plugins", "run", "appearance:dark")
            ctl("resize", "720", "480")
            capture("recent-sessions-dark-short")
            scenario("tabs", "horizontal")
            assert not any(item["visible"] for item in elements(older))
            scenario("tabs", "vertical")
            scenario("session", "close")
            eventually(lambda: len(ctl("state")["sessions"]) == 4)
            scenario("session", "close")
            eventually(lambda: not elements(older))
            # Tern 0.9.4 can retain its pre-close DOM, even without plugins.
            # A mismatched row count must never hide another live session.
            assert {"Gamma", "Beta", "Alpha"} <= {row[0] for row in positions()}
            scenario("plugins", "run", "appearance:light")
            ctl("resize", "1280", "800")
            print("PASS: newest three, older-session toggle, hidden-session navigation, unread retention, filtering and deletion")
            print(f"Screenshots: {OUT}")
    except Exception:
        capture("failure")
        (OUT / "failure-state.json").write_text(json.dumps(ctl("state"), indent=2))
        raise
    finally:
        if control.exists():
            try:
                ctl("quit")
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
                pass
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
