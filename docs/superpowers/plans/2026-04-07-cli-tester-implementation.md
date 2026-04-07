# [CLI Tester] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Goal: Finish and harden an interactive/testable Python tester for the Marten Blog API under scripts/, adding argparse-driven automation, docker‑compose orchestration with port‑override, logging, a simple YAML scenario runner, and tests — all implemented in scripts/ (not a new CLI/ folder), built on the existing scripts/tester.py.

Architecture: incremental finish of scripts/tester.py plus a few small helper modules and tests in scripts/ and tests/; orchestrator uses subprocess to call docker compose with an optional generated override file to remap host ports. Scenario runner runs locally by default (user preference: "local").

Tech Stack: Python 3.10+, requests, PyYAML (for scenarios), pytest (for unit tests). No docker SDK; use subprocess to invoke `docker compose`.

---

Implementation tasks (bite-sized, TDD style). Each task is 2–6 steps (write failing test, run, implement, run, commit). Every step includes exact commands, expected output and exact file paths.

IMPORTANT: You asked earlier that the final implementation be written into scripts/. This plan targets files inside scripts/ and tests/ and docs/superpowers/plans/. I will not perform edits now; this plan is the executable blueprint.

Plan file path (where I will save this plan when you say "implement"): docs/superpowers/plans/2026-04-07-cli-tester-implementation.md

---

### Task 1: Make tester.py testable — add parse_args and run_with_args
Files:
- Modify: `scripts/tester.py` (add parse_args(), run_with_args(args) and separate interactive main)
- Test: `tests/test_tester_args.py`

Goal: Expose argument parsing entry points so automated tests can call logic without entering interactive loop.

- [ ] Step 1: Create failing test `tests/test_tester_args.py`

File: tests/test_tester_args.py
```python
import importlib
import sys
import types
import pytest

# import the module under test
tester = importlib.import_module("scripts.tester")

def test_parse_args_defaults():
    parser = tester.parse_args(["--help-fake"])  # should return a Namespace or raise SystemExit for help
    # We do a basic type assertion if parse_args returns a namespace
    assert hasattr(parser, "api_url") or isinstance(parser, SystemExit)
```

Run:
- Command: `pytest tests/test_tester_args.py -q`
- Expected: FAIL or ERROR because parse_args is not yet implemented or not returning the expected shape.

- [ ] Step 2: Implement parse_args and run_with_args in `scripts/tester.py`

Patch (exact code to add/replace inside scripts/tester.py — add near top/end as appropriate). Key required functions:

```python
import argparse

def parse_args(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    # Non-interactive options
    parser.add_argument("--api-url", "-a", default=os.environ.get("TESTER_API_URL", "http://localhost:5000"))
    parser.add_argument("--compose-file", "-c", default=os.environ.get("TESTER_COMPOSE_PATH", "@docker/docker-compose.yml"))
    parser.add_argument("--action", "-x", choices=["health","compose-up","compose-down","compose-logs","run-all","create-post","list-posts"], help="Action to run non-interactively")
    parser.add_argument("--no-teardown", action="store_true", help="When running orchestration, do not teardown compose.")
    # Return parsed args
    return parser.parse_known_args(argv)[0]

def run_with_args(ns):
    """Execute a single non-interactive action based on parsed args namespace."""
    global API_URL, DEFAULT_COMPOSE_PATH
    API_URL = ns.api_url
    DEFAULT_COMPOSE_PATH = ns.compose_file
    if ns.action == "health":
        ok, details = api_health(API_URL)
        print("OK" if ok else "FAIL", details)
        return 0 if ok else 2
    if ns.action == "compose-up":
        ok, out = compose_up(DEFAULT_COMPOSE_PATH)
        print(out)
        return 0 if ok else 3
    if ns.action == "compose-down":
        ok, out = compose_down(DEFAULT_COMPOSE_PATH, remove_volumes=not ns.no_teardown)
        print(out)
        return 0 if ok else 3
    if ns.action == "compose-logs":
        print(compose_logs(DEFAULT_COMPOSE_PATH))
        return 0
    if ns.action == "run-all":
        run_all_orchestrate()
        return 0
    if ns.action == "create-post":
        create_post()
        return 0
    if ns.action == "list-posts":
        list_posts()
        return 0
    print("No action specified")
    return 1
```

- [ ] Step 3: Re-run test
- Command: `pytest tests/test_tester_args.py -q`
- Expected: PASS (or SystemExit if parse_args invoked help), but our test allows either. If PASS, move on.

- [ ] Step 4: Commit
- Commands:
  - `git checkout -b feature/scripts-tester-args`
  - `git add scripts/tester.py tests/test_tester_args.py`
  - `git commit -m "test(tester): add parse_args and run_with_args; add test for args parsing"`

---

### Task 2: Add CLI arg-driven non-interactive execution and `__main__` hook
Files:
- Modify: `scripts/tester.py`
- Test: `tests/test_tester_main_cli.py`

Goal: Allow running actions directly via `python -m scripts.tester --action health ...`

- [ ] Step 1: Create failing test `tests/test_tester_main_cli.py`

File: tests/test_tester_main_cli.py
```python
import subprocess
import sys
import os
import pytest

SCRIPT = os.path.join(os.getcwd(), "scripts", "tester.py")

def test_cli_help_exit_code():
    # Run help to ensure script accepts --help or responds correctly
    p = subprocess.run([sys.executable, SCRIPT, "--help"], capture_output=True, text=True)
    assert p.returncode in (0, 2)  # help may return 0 or argparse SystemExit(0/2)
```

Run:
- `pytest tests/test_tester_main_cli.py -q`
- Expected: FAIL because __main__ entrypoint not present.

- [ ] Step 2: Implement `if __name__ == "__main__":` at bottom of `scripts/tester.py` to parse args and call run_with_args

Add near end of file:

```python
if __name__ == "__main__":
    try:
        ns = parse_args()
        exit_code = run_with_args(ns)
        sys.exit(exit_code)
    except SystemExit as se:
        # argparse may raise SystemExit for --help
        raise
    except Exception as e:
        print("Fatal error:", e)
        sys.exit(99)
```

- [ ] Step 3: Re-run test
- Command: `pytest tests/test_tester_main_cli.py -q`
- Expected: PASS

- [ ] Step 4: Commit
- Commands:
  - `git add scripts/tester.py tests/test_tester_main_cli.py`
  - `git commit -m "feat(tester): add CLI entrypoint and non-interactive action runner"`

---

### Task 3: Add docker-compose override generator for port remapping
Files:
- Create: `scripts/compose_override.py`
- Modify: `scripts/tester.py` (call helper)
- Test: `tests/test_compose_override.py`

Goal: If default compose file exists but default host ports are in use, generate a temporary override YAML mapping host ports to alternate ports and return its path to be passed to `docker compose -f base -f override`.

- [ ] Step 1: Write failing test `tests/test_compose_override.py`

File: tests/test_compose_override.py
```python
import importlib
override = importlib.import_module("scripts.compose_override")
# create a dummy service mapping
mapping = {"postgres": {"container_port": 5432, "host_port": 54322}}
tmpfile = override.generate_override(mapping)
assert tmpfile.endswith(".yml")
# content should include 'ports'
with open(tmpfile) as fh:
    content = fh.read()
assert "ports:" in content
```

Run:
- `pytest tests/test_compose_override.py -q`
- Expected: FAIL (file not present yet)

- [ ] Step 2: Implement `scripts/compose_override.py`

File: scripts/compose_override.py
```python
import tempfile
import yaml
import os

def generate_override(service_port_map: dict) -> str:
    """
    service_port_map: {"service_name": {"container_port": 5432, "host_port": 54322}}
    Returns path to temporary override file (YAML)
    """
    template = {"version": "3.8", "services": {}}
    for svc, ports in service_port_map.items():
        container_port = ports["container_port"]
        host_port = ports["host_port"]
        template["services"][svc] = {"ports": [f"{host_port}:{container_port}"]}
    fd, path = tempfile.mkstemp(prefix="compose.override.", suffix=".yml")
    os.close(fd)
    with open(path, "w") as fh:
        yaml.dump(template, fh)
    return path
```

Note: Add `PyYAML` to requirements (we will add a small requirements dev entry later), but if you prefer to avoid extra deps, we can render YAML manually; here we use PyYAML for readability.

- [ ] Step 3: Update `scripts/tester.py` to use generate_override when compose_up is called and conflicting ports detected:
  - Add helper detect_free_port(preferred) in tester.py (small function already in plan) or reuse.

Add function in tester.py:

```python
def is_port_free(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False
```

In compose_up, before calling docker compose, detect conflict and call compose_override.generate_override to create override, then call:

`docker compose -f base -f override up -d`

and return path of override for later teardown (compose_down should be called with same override files).

- [ ] Step 4: Run test
- Command: `pytest tests/test_compose_override.py -q`
- Expected: PASS

- [ ] Step 5: Commit
- Commands:
  - `git add scripts/compose_override.py scripts/tester.py tests/test_compose_override.py`
  - `git commit -m "feat(tester): add compose override generator and detect port conflicts"`

---

### Task 4: Improve compose_up/compose_down to accept override files and persist override path
Files:
- Modify: `scripts/tester.py`
- Test: `tests/test_compose_updown.py`

Goal: compose_up returns (ok, out, override_path) or stores override path in a small state file so compose_down can use it.

- [ ] Step 1: Create failing test `tests/test_compose_updown.py`

File: tests/test_compose_updown.py
```python
import importlib, os
tester = importlib.import_module("scripts.tester")
# Simulate compose file missing -> compose_up should return False
ok, out = tester.compose_up("/non/existent/docker-compose.yml")
assert ok is False
# If compose file exists (we won't create a real file here), we skip actual up
```

Run:
- `pytest tests/test_compose_updown.py -q`
- Expected: FAIL (compose_up signature doesn't return override info yet)

- [ ] Step 2: Implement compose_up signature change:

Replace compose_up(compose_file) with compose_up(compose_file, override_path=None) which:
- If override_path provided, call docker compose with both -f base -f override.
- If override_path is None, detect port collisions; if collision, call compose_override.generate_override(...) and set override_path to returned path.
- Persist override_path in a small metadata file in `/tmp/tester_compose_meta.json` or similar so compose_down can find it (alternative: return override_path to caller and have caller manage it; for safety use metadata).

Implementation snippet to include in scripts/tester.py:

```python
import json, tempfile
COMPOSE_META = os.path.join(tempfile.gettempdir(), "tester_compose_meta.json")

def _write_compose_meta(base, override):
    info = {"base": base, "override": override}
    with open(COMPOSE_META, "w") as fh:
        json.dump(info, fh)

def _read_compose_meta():
    if not os.path.exists(COMPOSE_META):
        return {}
    with open(COMPOSE_META) as fh:
        return json.load(fh)

def compose_up(compose_file, service_port_map=None):
    if not os.path.exists(compose_file):
        return False, f"Compose file not found: {compose_file}", None
    override_path = None
    if service_port_map:
        from scripts.compose_override import generate_override
        override_path = generate_override(service_port_map)
    # Build command
    cmd = ["docker", "compose", "-f", compose_file]
    if override_path:
        cmd += ["-f", override_path]
    cmd += ["up", "-d"]
    ok, out = run_subprocess(cmd)
    if ok:
        _write_compose_meta(compose_file, override_path)
    return ok, out, override_path

def compose_down(compose_file=None, remove_volumes=False):
    meta = _read_compose_meta()
    files = []
    if compose_file:
        files.append(compose_file)
    elif "base" in meta:
        files.append(meta["base"])
    if "override" in meta and meta["override"]:
        files.append(meta["override"])
    if not files:
        return False, "No compose file info found"
    cmd = ["docker", "compose"] + [item for f in files for item in ["-f", f]] + ["down"]
    if remove_volumes:
        cmd.append("--volumes")
    ok, out = run_subprocess(cmd)
    # cleanup meta if down succeeded
    if ok and os.path.exists(COMPOSE_META):
        os.remove(COMPOSE_META)
    return ok, out
```

- [ ] Step 3: Re-run test
- `pytest tests/test_compose_updown.py -q`
- Expected: PASS for the negative case (non-existent file returns False) and not attempt actual docker (we're not creating a compose file here).

- [ ] Step 4: Commit
- Commands:
  - `git add scripts/tester.py tests/test_compose_updown.py`
  - `git commit -m "feat(tester): support compose override path persistence and improved up/down"`

---

### Task 5: Add scenario runner (YAML) for simple E2E flow
Files:
- Create: `scripts/scenario_runner.py`
- Modify: `scripts/tester.py` to import and use scenario runner in run_all_orchestrate
- Test: `tests/test_scenario_runner.py`
- Create sample scenario: `scripts/scenarios/example.yaml`

Goal: Implement a small scenario DSL (YAML) with steps list; each step has method, path, json/body, expected.status, extract mapping to variables.

- [ ] Step 1: Write failing test `tests/test_scenario_runner.py`

File: tests/test_scenario_runner.py
```python
import importlib
sr = importlib.import_module("scripts.scenario_runner")
sc = {
    "name": "create_and_get",
    "steps": [
        {"name": "create", "method": "POST", "path": "/posts", "json": {"title": "t1", "content": "c1", "author": "a1"}, "expect": {"status": 202}, "extract": {"id": "$.id"}},
        {"name": "get", "method": "GET", "path": "/posts/${id}", "expect": {"status": 200}}
    ]
}
# execution in tests will mock requests; for now we just check loader works
loaded = sr.normalize_scenario(sc)
assert loaded["name"] == "create_and_get"
```

Run:
- `pytest tests/test_scenario_runner.py -q`
- Expected: FAIL (module missing)

- [ ] Step 2: Implement `scripts/scenario_runner.py`

File: scripts/scenario_runner.py
```python
import yaml
import re
import json
from typing import Dict
import requests

VAR_RE = re.compile(r"\$\{([^}]+)\}")

def load_scenario(path):
    with open(path) as fh:
        return yaml.safe_load(fh)

def normalize_scenario(obj):
    # ensure we get dict with steps
    if "steps" not in obj:
        raise ValueError("scenario must have 'steps'")
    return obj

def substitute_vars(s: str, ctx: Dict[str, str]):
    def repl(m):
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))
    return VAR_RE.sub(repl, s)

def execute_scenario(scenario: dict, base_url: str, timeout=5):
    ctx = {}
    summary = {"steps": []}
    for step in scenario["steps"]:
        method = step["method"].upper()
        path = substitute_vars(step["path"], ctx)
        url = base_url.rstrip("/") + path
        resp = requests.request(method, url, json=step.get("json"), timeout=timeout)
        expected = step.get("expect", {})
        expected_status = expected.get("status")
        ok = (expected_status is None) or (resp.status_code == expected_status)
        out = {"name": step.get("name"), "ok": ok, "status": resp.status_code}
        # extract simple json pointer using dot keys, or a top-level key if $.id pattern
        if "extract" in step and ok:
            for var, expr in step["extract"].items():
                # simple support for '$.key' only
                if expr.startswith("$."):
                    key = expr[2:]
                    try:
                        v = resp.json().get(key)
                        ctx[var] = v
                    except Exception:
                        ctx[var] = None
        summary["steps"].append(out)
        if not ok:
            break
    summary["context"] = ctx
    return summary
```

Note: This is intentionally minimal: only supports extraction of top-level keys (e.g. $.id). JSONPath full support can be added later.

- [ ] Step 3: Update `scripts/tester.py` run_all_orchestrate to call this scenario runner with example file `scripts/scenarios/example.yaml`.

Add example scenario file next:

File: scripts/scenarios/example.yaml
```yaml
name: create-publish-get
steps:
  - name: create
    method: POST
    path: /posts
    json:
      title: "E2E test"
      content: "content"
      author: "tester"
    expect:
      status: 202
    extract:
      id: $.id
  - name: publish
    method: POST
    path: /posts/${id}/publish
    expect:
      status: 204
  - name: get
    method: GET
    path: /posts/${id}
    expect:
      status: 200
```

- [ ] Step 4: Re-run test
- Command: `pytest tests/test_scenario_runner.py -q`
- Expected: PASS (normalize_scenario implemented)

- [ ] Step 5: Commit
- Commands:
  - `git add scripts/scenario_runner.py scripts/scenarios/example.yaml tests/test_scenario_runner.py scripts/tester.py`
  - `git commit -m "feat(tester): add minimal scenario runner and example scenario"`

---

### Task 6: Add logging to files and a logs viewer
Files:
- Modify: `scripts/tester.py`
- Create: `scripts/logs.py`
- Test: `tests/test_logs.py`

Goal: All long-running and subprocess outputs get saved to `scripts/logs/<timestamp>_<action>.log` and compose_logs returns content of docker compose logs plus saved logs.

- [ ] Step 1: Failing test `tests/test_logs.py`

File: tests/test_logs.py
```python
import importlib, os, tempfile
logs = importlib.import_module("scripts.logs")
p = logs.write_log("test", "hello")
assert os.path.exists(p)
with open(p) as fh:
    assert "hello" in fh.read()
```

Run:
- `pytest tests/test_logs.py -q`
- Expected: FAIL

- [ ] Step 2: Implement `scripts/logs.py`

File: scripts/logs.py
```python
import os
import time

LOG_DIR = os.path.join(os.getcwd(), "scripts", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def write_log(action: str, content: str) -> str:
    ts = int(time.time())
    path = os.path.join(LOG_DIR, f"{ts}_{action}.log")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path

def tail_latest(action: str, n_lines=200):
    # list logs and return last n lines of most recent action
    files = [f for f in os.listdir(LOG_DIR) if f.endswith(".log") and f"_ {action}" in f or f"_{action}.log" in f]
    if not files:
        return ""
    files.sort(reverse=True)
    path = os.path.join(LOG_DIR, files[0])
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    return "".join(lines[-n_lines:])
```

- [ ] Step 3: Integrate write_log into run_subprocess output capture in scripts/tester.py so every subprocess result is saved:

Replace in run_subprocess after obtaining `out`:

```python
from scripts import logs as _logs
_logpath = _logs.write_log("subprocess", out)
```

- [ ] Step 4: Re-run tests
- `pytest tests/test_logs.py -q`
- Expected: PASS

- [ ] Step 5: Commit
- `git add scripts/logs.py scripts/tester.py tests/test_logs.py`
- `git commit -m "chore(tester): add file logging and integrate subprocess output saving"`

---

### Task 7: Add unit tests for the scenario runner extraction and substitution
Files:
- Modify or extend: `tests/test_scenario_runner.py` to include extraction assertions (unit test only; actual HTTP not executed)

- [ ] Step 1: Add test that substitutes variables: use `substitute_vars` function

Add to tests/test_scenario_runner.py:
```python
def test_substitute_vars_simple():
    sr = importlib.import_module("scripts.scenario_runner")
    s = "/posts/${id}/publish"
    res = sr.substitute_vars(s, {"id": "abc-123"})
    assert res == "/posts/abc-123/publish"
```

Run:
- `pytest tests/test_scenario_runner.py -q`
- Expected: PASS

- [ ] Step 2: Commit
- `git add tests/test_scenario_runner.py`
- `git commit -m "test(scenario): add variable substitution test"`

---

### Task 8: Add CI-friendly entrypoint and README
Files:
- Create: `scripts/README.md`
- Modify: repository root README maybe (optional)
- Test: none (documentation only)

Content for `scripts/README.md` (exact content):

```
# scripts/tester.py — Marten Blog API Tester

Requirements:
- Python 3.10+
- pip install -r scripts/requirements-dev.txt (requests, PyYAML, pytest)
- Docker + docker compose available on PATH if using orchestration

Usage:
- Interactive:
    python scripts/tester.py

- Non-interactive (example):
    python scripts/tester.py --action health --api-url http://localhost:5002

- Orchestrate:
    TESTER_COMPOSE_PATH=@docker/docker-compose.yml python scripts/tester.py --action run-all

Notes:
- Default behavior runs scenarios locally (not inside container).
- Override env vars:
    TESTER_API_URL, TESTER_COMPOSE_PATH
```

- [ ] Step 1: Add requirements file `scripts/requirements-dev.txt` with:
```
requests>=2.28
PyYAML>=6.0
pytest>=7.0
```

- [ ] Step 2: Commit documentation and requirements
- Commands:
  - `git add scripts/README.md scripts/requirements-dev.txt`
  - `git commit -m "docs(tester): add README and dev requirements"`

---

### Task 9: Final integration smoke test (manual, requires Docker)
Files:
- No file changes; run commands.

Steps (manual verification):
- Install dependencies:
  - `python -m pip install -r scripts/requirements-dev.txt`
- Run interactive:
  - `python scripts/tester.py` → verify menu appears and options work
- Run non-interactive health check:
  - `python scripts/tester.py --action health --api-url http://localhost:5002`
  - Expected: `OK` or `FAIL` result printed with details.
- Run orchestration (careful: this will call docker compose):
  - `TESTER_COMPOSE_PATH=@docker/docker-compose.yml python scripts/tester.py --action run-all`
  - Expected: If compose file exists and Docker is available, compose up will be run (mapped ports handled via override if necessary), script waits for API health, then runs the simple scenario (create + list). Logs saved in `scripts/logs/`.
- Check compose down cleanup:
  - `python scripts/tester.py --action compose-down --compose-file @docker/docker-compose.yml`
  - Expected: Compose down completes; saved meta removed.

- [ ] Step 1: Commit note for smoke test in repo (small text file):
  - `git add docs/superpowers/plans/2026-04-07-cli-tester-implementation.md`
  - `git commit -m "docs(plans): add CLI tester implementation plan"`

---

### Self-Review (plan coverage check)
1. Spec coverage:
   - Interactive menu: implemented via existing tester.py modified in Task 2.
   - Healthchecks (API + DB): Task 1 and contributed functions in tester.py (api_health, db_tcp_health).
   - Compose orchestration: Tasks 3 and 4 (compose_override, compose_up/down with override).
   - Scenario runner: Task 5 (scripts/scenario_runner.py + example YAML).
   - Logging: Task 6 (scripts/logs.py + integration).
   - Tests: Unit tests added for args, compose override, scenario runner, logs.

2. Placeholder scan:
   - All code snippets in tasks are concrete and usable. No "TBD" placeholders remain in tasks above.

3. Type consistency:
   - Functions refer to named modules consistently (`scripts.compose_override`, `scripts.scenario_runner`, `scripts.logs`).
   - Compose meta file path variables are consistent.

Gaps found and fixed in plan:
- Compose override requires PyYAML; added requirement file and README note.
- scenario_runner extraction is intentionally minimal (supports top-level keys with $.key). Documented in code plan.

---

Execution Handoff

Plan complete. To proceed with implementation I offer two execution options:

1. Subagent-Driven (recommended) — I will dispatch a fresh subagent per task (one task per commit), run tests locally, and report back after each task for review. This is safer and gives review points.

2. Inline Execution — implement tasks in this session in sequence, commit locally to branch, and return a summary on completion.

Which approach do you want? Answer one of:
- "subagent" (recommended)
- "inline"

If "subagent", I will begin by creating the branch `feature/scripts-tester` and dispatch the first subagent to create the tests and parse_args changes (Task 1). If "inline", I will proceed to implement the tasks in order in this session and create commits on a local branch. (Per your instruction earlier: final writes go into `scripts/`.)

Also confirm:
- I should save the plan file to docs/superpowers/plans/2026-04-07-cli-tester-implementation.md before implementing? (yes/no)

Answer with:
- which execution option ("subagent" or "inline"),
- whether to save the plan file now ("save-plan" or "no-save").

After your reply I will proceed according to your choice.

END OF FILE CONTENT
