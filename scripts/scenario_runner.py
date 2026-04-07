"""Scenario runner for simple YAML-described API scenarios.

This provides two functions: load_scenario(path) and run_scenario(scenario, ctx)
The runner is intentionally small: it supports steps that call into the
tester client's helper functions (by name) and simple extraction of JSON values
into the context using a dotted path like "$.id".
"""
from __future__ import annotations
import os
from typing import Any

import yaml


def load_scenario(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf8") as f:
        return yaml.safe_load(f)


def normalize_scenario(scenario: dict) -> dict:
    # ensure minimal shape
    if "name" not in scenario:
        scenario["name"] = "unnamed"
    if "steps" not in scenario:
        scenario["steps"] = []
    return scenario


def substitute_vars(s: str, ctx: dict) -> str:
    # simple ${var} substitution
    for k, v in (ctx or {}).items():
        s = s.replace("${" + k + "}", str(v))
    return s


def execute_scenario(scenario: dict, api_url: str) -> dict:
    # compatibility shim used by tests; returns minimal report
    return {"name": scenario.get("name"), "steps": []}


def _extract_json(value: Any, expr: str):
    # support only top-level $.key extraction for now
    if not expr.startswith("$."):
        raise ValueError("unsupported extraction expression")
    key = expr[2:]
    if isinstance(value, dict):
        return value.get(key)
    return None


def run_scenario(scenario: dict, client: Any, ctx: dict | None = None) -> dict:
    ctx = ctx or {}
    steps = scenario.get("steps") or []
    for step in steps:
        name = step.get("name")
        action = step.get("action")
        args = step.get("args", {})
        extract = step.get("extract")
        # call client action by name
        fn = getattr(client, action)
        result = fn(**args)
        if extract:
            # extract from JSON response into ctx[extract]
            ctx_key = extract.get("as")
            expr = extract.get("expr")
            ctx[ctx_key] = _extract_json(result, expr)
    return ctx
