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
    (plugins / "tern-sidebar.path").write_text(str(ROOT) + "\n")
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
                    if "nav-group" in group.get("class", "").split():
                        name = group["children"][0]["children"][0]["text"]
                        groups.append((name, group["rect"][1]))
        return sorted(groups, key=lambda row: row[1])

    def elements(selector):
        return ctl("dump", selector)["elements"]

    def capture(name):
        shot = ctl("shot", name)
        for field in ("png", "layout"):
            source = work / shot[field]
            shutil.copy2(source, OUT / source.name)

    busy = '#sidebar .nav-row[aria-label$=" · working"] > .tn-tc'
    button = '[data-plugin="tern-sidebar"]'
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
            scenario("session", "rename", "Alpha")
            scenario("rename", "#1")
            cwd = ctl("state")["focused"]["cwd"]
            assert elements(button)[0]["visible"]
            assert not ctl("state")["status_bar"]
            scenario("click", button)
            assert len(ctl("state")["sessions"]) == 2
            assert ctl("state")["focused"]["cwd"] == cwd
            scenario("session", "rename", "Beta")
            scenario("rename", "#2")
            scenario("key", "ctrl+alt+n")
            assert len(ctl("state")["sessions"]) == 3
            scenario("session", "rename", "Gamma")
            scenario("rename", "#3")
            baseline = eventually(lambda: positions() if [x[0] for x in positions()] ==
                                  ["Alpha", "Beta", "Gamma"] else None)
            for title in ("#1", "#2", "#3"):
                scenario("click", f'#sidebar .nav-row[aria-label="{title}"]')
                assert positions() == baseline, (title, positions(), baseline)
            print("PASS: button, shortcut, inherited directory, click-stable session positions")

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

            sidebar = elements("#sidebar")[0]["rect"]
            assert elements("#tabbar")[0]["rect"][0] == sidebar[0]
            assert elements("#tabbar .tn-session-tab")[0]["rect"][0] < sidebar[2]
            scenario("status-bar", "on")
            assert elements(button)[0]["visible"]
            scenario("move", 500, 200)
            scenario("tabs", "autohide", "on")
            assert eventually(lambda: not elements(button)[0]["visible"])
            scenario("tabs", "autohide", "off")
            scenario("plugins", "run", "appearance:dark")
            scenario("surface-play", fixture, "until", "1")
            ctl("resize", "720", "480")
            capture("working-dark-short")
            assert elements(button)[0]["visible"]
            assert elements(busy)[0]["visible"]
            print("PASS: left header, status-bar toggle, sidebar auto-hide, dark/short window")
            print(f"Screenshots: {OUT}")
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
