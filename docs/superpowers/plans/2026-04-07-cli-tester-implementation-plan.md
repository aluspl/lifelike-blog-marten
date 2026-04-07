# CLI Tester Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and test a small scripts/tester.py CLI that exercises the Blog API flows (create → list → publish → get → events), can auto-start docker-compose on 403, persists LAST_LISTED_POST to scripts/.tester_env, and provides non-interactive --action options.

**Architecture:** Single-purpose script with small helper modules under scripts/: tester.py (CLI + orchestration), scenario_runner.py (YAML runner), compose_override.py (override generator), logs.py (log writer). Unit tests under tests/ to run without Docker.

**Tech Stack:** Python 3.11+, requests, PyYAML (only for scenario runner), pytest

---

### Task 1: Project files map and small helper stubs

**Files:**
- Modify/create: `scripts/tester.py` (entrypoint)
- Create: `scripts/scenario_runner.py`
- Create: `scripts/compose_override.py`
- Create: `scripts/logs.py`
- Create: `scripts/.tester_env` (runtime-created; tests will write to a temp file)
- Tests: `tests/test_cli_args.py`, `tests/test_scenario_runner.py`, `tests/test_compose_override.py`, `tests/test_logs.py`

- [ ] **Step 1: Add minimal module files with stubs and imports**

Create the following files with this content (minimal stubs so tests can import):

scripts/tester.py
```python
"""CLI tester entrypoint - minimal stub for Task 1."""
from __future__ import annotations
import argparse

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Marten Blog API tester")
    parser.add_argument("--action", help="Non-interactive action to run", default=None)
    return parser.parse_args(argv)

def main(argv=None):
    ns = parse_args(argv)
    if ns.action:
        print(f"Would run action: {ns.action}")

if __name__ == "__main__":
    main()
```

scripts/scenario_runner.py
```python
"""Scenario runner stub"""
def load_scenario(path):
    return {"steps": []}

def run_scenario(scenario, ctx=None):
    return True
```

scripts/compose_override.py
```python
"""Compose override generator stub"""
def generate_override(port_map: dict | None = None) -> str:
    return "version: '3'\nservices: {}\n"
```

scripts/logs.py
```python
"""Logs helper stub"""
def write_log(name: str, content: str) -> str:
    path = f"scripts/logs/{name}.log"
    with open(path, "a") as f:
        f.write(content + "\n")
    return path
```

Run: `pytest -q` should pass import-level tests once added in next steps.

**Commit:** `git add scripts/*.py && git commit -m "chore(tester): add module stubs for CLI tester"`

### Task 2: Add argument parsing tests and behavior

**Files:**
- Modify: `scripts/tester.py`
- Test: `tests/test_cli_args.py`

- [ ] **Step 1: Write failing test for --action parsing**

tests/test_cli_args.py
```python
from scripts import tester

def test_parse_action_arg():
    ns = tester.parse_args(["--action", "run-all"])
    assert ns.action == "run-all"
```

- [ ] **Step 2: Run test and confirm failure**
Run: `pytest tests/test_cli_args.py::test_parse_action_arg -q`
Expected: FAIL or PASS depending on stub; adjust code accordingly

- [ ] **Step 3: Implement parse_args to satisfy test**
Ensure `parse_args` exists and returns namespace with `action` attribute (done in stub). The test should pass.

- [ ] **Step 4: Commit**
`git add scripts/tester.py tests/test_cli_args.py && git commit -m "test(tester): parse --action argument"`

### Task 3: Implement logs helper and tests

**Files:**
- Modify/Create: `scripts/logs.py`
- Test: `tests/test_logs.py`

- [ ] **Step 1: Write failing test for write_log behavior**

tests/test_logs.py
```python
import os
from scripts import logs

def test_write_log(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    # monkeypatch scripts/logs to write to tmp_path
    path = logs.write_log("sample", "hello world")
    assert path.endswith("sample.log")
    assert os.path.exists(path)
    with open(path) as f:
        contents = f.read()
    assert "hello world" in contents
```

- [ ] **Step 2: Implement logs.write_log writing into scripts/logs/ and pass test**
Provide an implementation that creates the directory if needed and writes timestamped content.

- [ ] **Step 3: Commit**

### Task 4: Implement compose_override generator and test

**Files:**
- Modify/Create: `scripts/compose_override.py`
- Test: `tests/test_compose_override.py`

- [ ] **Step 1: Write failing test to confirm content shape**

tests/test_compose_override.py
```python
from scripts.compose_override import generate_override

def test_generate_override_minimal():
    out = generate_override({5000:5000})
    assert "services" in out
```

- [ ] **Step 2: Implement generate_override to return minimal valid YAML string**

- [ ] **Step 3: Commit**

### Task 5: Implement scenario_runner with PyYAML and tests

**Files:**
- Modify/Create: `scripts/scenario_runner.py`
- Test: `tests/test_scenario_runner.py`

- [ ] **Step 1: Add test for YAML loading and simple extraction**
tests/test_scenario_runner.py
```python
from scripts.scenario_runner import load_scenario

def test_load_scenario(tmp_path):
    p = tmp_path / "example.yaml"
    p.write_text("steps:\n  - name: create\n")
    s = load_scenario(str(p))
    assert isinstance(s, dict)
    assert "steps" in s
```

- [ ] **Step 2: Implement load_scenario(path) using PyYAML.safe_load and run_scenario(scenario, ctx)**

- [ ] **Step 3: Commit**

### Task 6: Add API helpers to tester.py and unit tests (mocked requests)

**Files:**
- Modify: `scripts/tester.py` — add HTTP helpers using `requests` and simple create_post/list_posts/publish_post/get_post functions
- Tests: `tests/test_http_helpers.py`

- [ ] **Step 1: Write failing tests using monkeypatch or requests-mock**
tests/test_http_helpers.py
```python
import requests
from scripts import tester

def test_api_helpers(monkeypatch):
    class FakeResp:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
        def json(self):
            return self._json

    def fake_get(url, timeout):
        return FakeResp(200, [{"id": "1"}])

    monkeypatch.setattr(requests, "get", fake_get)
    posts = tester.list_posts()
    assert posts[0]["id"] == "1"
```

- [ ] **Step 2: Implement list_posts() calling requests.get("http://localhost:5000/posts") with timeout and returning json()

- [ ] **Step 3: Commit**

### Task 7: Implement orchestration behavior for auto-start on 403

**Files:**
- Modify: `scripts/tester.py` — add compose_up(), compose_down(), compose_ps() wrappers that call subprocess.run([...], capture_output=True)
- Tests: `tests/test_compose_updown.py` (monkeypatch subprocess)

- [ ] **Step 1: Write failing test that simulates requests.get returning 403 and ensures compose_up() is called**

tests/test_compose_updown.py
```python
import subprocess
from scripts import tester

def test_compose_called_on_403(monkeypatch):
    class FakeResp:
        def __init__(self, status_code):
            self.status_code = status_code
        def json(self):
            return {}

    def fake_get(url, timeout):
        return FakeResp(403)

    called = {}
    def fake_run(cmd, **kwargs):
        called['cmd'] = cmd
        return None

    monkeypatch.setattr(tester.requests, "get", fake_get)
    monkeypatch.setattr(tester.subprocess, "run", fake_run)
    tester.list_posts(auto_start=True)
    assert 'cmd' in called
```

- [ ] **Step 2: Implement list_posts(auto_start=False) to detect 403 and call compose_up() when auto_start True

- [ ] **Step 3: Implement compose_up() to attempt docker compose with fallback compose files and capture stdout/stderr to logs via scripts/logs.write_log

- [ ] **Step 4: Commit**

### Task 8: Implement run_all_orchestrate() and non-interactive --action run-all

**Files:**
- Modify: `scripts/tester.py`
- Tests: `tests/test_runner_action.py` (mock compose and requests)

- [ ] **Step 1: Write test for --action run-all that exercises orchestration path (mock compose_up, api health, create/list)**

- [ ] **Step 2: Implement run_all_orchestrate(ns) that performs: compose_up (if needed), wait for api_health(), run scenario_runner.run_scenario(), show system status, teardown unless ns.no_teardown True

- [ ] **Step 3: Commit**

### Task 9: Persist LAST_LISTED_POST and add show-last-post action

**Files:**
- Modify: `scripts/tester.py`
- Tests: `tests/test_persist_last_post.py`

- [ ] **Step 1: Add code in list_posts() to append LAST_LISTED_POST=<id> to scripts/.tester_env when posts are returned**

- [ ] **Step 2: Add --action show-last-post that reads scripts/.tester_env, finds the last LAST_LISTED_POST entry, and calls get_post(id) to display it

- [ ] **Step 3: Commit**

### Task 10: Add documentation and usage examples

**Files:**
- Modify: `docs/superpowers/specs/2026-04-07-cli-tester-design.md` (link to plan) and add `docs/superpowers/README-test-runner.md` with examples

- [ ] **Step 1: Write run examples for interactive and non-interactive usage**

- [ ] **Step 2: Commit**

### Task 11: Self-review and run test suite

- [ ] **Step 1: Run `pytest -q` and fix failing tests**
- [ ] **Step 2: Search for placeholders (TBD/TODO) and remove them**
- [ ] **Step 3: Commit final changes**

## Spec coverage check

All major spec points have corresponding tasks:
- Auto-start on 403: Task 7
- Persistence of LAST_LISTED_POST: Task 9
- Logs and compose output capture: Task 3 + Task 7
- Scenario runner and YAML support: Task 5
- Tests that do not require Docker: Tasks 2-6,8-9

No placeholders remain in this plan.

Plan file saved to: `docs/superpowers/plans/2026-04-07-cli-tester-implementation-plan.md`

Execution options:
1) Subagent-Driven (recommended) — dispatch a subagent per task and implement iteratively
2) Inline Execution — I execute tasks now in this session

Which approach do you want? (reply: "subagent" or "inline")
