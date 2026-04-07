Title: CLI Tester Design
Date: 2026-04-07

Summary
-------
This document specifies the design for a small interactive CLI tester under scripts/ that exercises the Marten Blog API flows (create → list → publish → get → events), and provides safe orchestration to start an isolated docker-compose environment when the API is unavailable.

Goals
-----
- Provide an interactive menu and non-interactive actions (--action) to run E2E scenarios against the Blog API.
- When the API returns 403 (or otherwise appears down/unhealthy), automatically start a local docker-compose environment (user selected: Auto-start), wait for health, retry the request, run the scenario, and provide a compact debug menu and status outputs.
- Persist the last-listed post ID to scripts/.tester_env for later inspection.
- Keep orchestration via subprocess docker compose commands; do not use Docker SDK.
- All code lives under scripts/; unit tests live under tests/ and the design/plans under docs/superpowers.

Constraints
-----------
- Must use subprocess to run docker compose (no Docker SDK).
- Keep changes minimal and localized to scripts/ and docs/ unless necessary.
- Avoid destructive git operations; this repo may not have an initialized git remote in the environment.
- Provide safe defaults: ask before teardown unless --no-teardown set.

Key user decision
-----------------
User selected behavior: Auto-start the docker-compose environment when the tester receives a 403 from the API. That means the tester will not prompt for confirmation in that case; it will attempt to bring up compose, wait for health, and continue the scenario. Interactive flows still show status and allow explicit teardown control.

Alternatives Considered
-----------------------
1) Prompt Before Starting (Current interactive behavior)
   - Pros: Safer for local machines; user stays in control.
   - Cons: Interrupts unattended runs / CI.
2) Auto-start (Chosen)
   - Pros: Works smoothly in CI/unattended runs and reflects user's selection.
   - Cons: May start containers unexpectedly on a developer machine; mitigated by clear logs and an opt-out flag.
3) Never Start; Show Instructions
   - Pros: Zero risk of side effects.
   - Cons: Requires manual steps and interferes with automation.

Recommendation
--------------
Proceed with Auto-start (per user choice). Add a configuration override and environment variable TESTER_COMPOSE_PATH so users can point at a different compose file. Respect --no-auto-start flag if users want to opt out explicitly.

Architecture and Components
---------------------------
- scripts/tester.py (main)
  - CLI parsing (argparse) with --action for non-interactive operations and global flags: --compose-path, --no-teardown, --no-auto-start, --debug, --wait-timeout
  - Interactive menu and compact debug menu mode
  - Orchestration: compose_up(), compose_down(), compose_ps(), compose_logs() implemented with subprocess calling "docker compose -f <path> up -d" (support multiple candidate compose file locations)
  - API helpers: create_post(), list_posts(), publish_post(), get_post(), get_events(), api_health()
  - Persistence: write LAST_LISTED_POST=<id> lines to scripts/.tester_env when listing posts
  - run_all_orchestrate(): full scenario orchestration (start compose if needed, wait for health, run scenario, show status, wait for Enter, teardown unless --no-teardown)

- scripts/scenario_runner.py
  - Load YAML scenarios (PyYAML), support variable substitution and extraction (simple $.id extraction).
  - Execute scenario steps using tester API helpers and store extracted values into context for later steps.

- scripts/compose_override.py
  - Provide helper to generate a minimal override compose file if a particular port mapping or environment override is needed for the tester.

- scripts/logs.py
  - Centralized logging helper that writes runner and compose output to scripts/logs/ with timestamped files and a tail helper.

- scripts/.tester_env
  - Persisted file appended with lines like LAST_LISTED_POST=<id>

Data Flow
---------
1. User invokes scripts/tester.py (interactive) or scripts/tester.py --action run-all (non-interactive).
2. Tester calls list_posts() or the first API endpoint in the scenario.
3. If API responds with 403 or cannot be reached, and auto-start is enabled, tester runs compose_up() and waits for api_health() to pass (with timeout). After health is OK, it retries the failed request.
4. Scenario steps execute in order; scenario_runner extracts outputs into the context and writes LAST_LISTED_POST when list_posts is called.
5. After scenario run, tester prints system status (API health, docker compose ps) and stores logs under scripts/logs/. If interactive, tester waits for Enter to tear down (unless --no-teardown).

Error Handling and Retries
-------------------------
- On network errors (ConnectionError, Timeout), retry with exponential backoff up to a configured attempt count before deciding to start compose (or fail if auto-start disabled).
- On 403 specifically, follow the auto-start rule: bring up compose and retry once the health check passes.
- Compose failures: capture stdout/stderr to logs and present the last N lines to the user, then fail the scenario with a helpful message and suggested manual commands to inspect (compose ps, compose logs).

Health Checks
-------------
- API health: GET http://localhost:5000/health (or root GET /posts) with a short timeout. Consider using a small loop with total wait time controlled by --wait-timeout.
- DB health: optional TCP connect to configured DB port if compose health is slow; make this pluggable.

Testing Strategy
----------------
- Unit tests (pytest) for scenario_runner (YAML parsing, extraction), compose_override generation, logs writer, and CLI argument parsing. These tests should avoid touching Docker or the real API.
- Integration tests (optional) that run with Docker in CI (marked separately). For local development, run the main script with --action run-all and allow auto-start to bring up containers.

Acceptance Criteria
-------------------
1. scripts/tester.py provides interactive and --action modes and documents usage in the top-level README or docs/superpowers.
2. When the API returns 403, tester auto-starts docker-compose (using TESTER_COMPOSE_PATH or fallbacks), waits for health, retries the request, and proceeds.
3. LAST_LISTED_POST entries are appended to scripts/.tester_env when list_posts runs.
4. compose up/down operations are executed via subprocess and logs are captured to scripts/logs/.
5. Unit tests covering logic mentioned above pass in a fresh environment without requiring Docker.

Security and Safety Notes
-------------------------
- Auto-start can unintentionally run containers; provide --no-auto-start and document implications.
- Respect user environment and do not force teardown if --no-teardown is set.

Next Steps
----------
1. User review and approval of this design file.
2. After approval, invoke the writing-plans skill to create a step-by-step implementation plan that will: a) add/modify scripts/tester.py, scenario_runner, compose helpers, logs, tests; b) add tests and CI gating as needed.

Revision History
----------------
- 2026-04-07: Initial design drafted and saved.
