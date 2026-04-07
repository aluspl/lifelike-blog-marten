import importlib


sr = importlib.import_module("scripts.scenario_runner")


def test_normalize():
    sc = {"name": "create_and_get", "steps": []}
    loaded = sr.normalize_scenario(sc)
    assert loaded["name"] == "create_and_get"


def test_substitute_vars_simple():
    s = "/posts/${id}/publish"
    res = sr.substitute_vars(s, {"id": "abc-123"})
    assert res == "/posts/abc-123/publish"
