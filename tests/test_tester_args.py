import importlib


tester = importlib.import_module("scripts.tester")


def test_parse_args_defaults():
    ns = tester.parse_args([])
    assert hasattr(ns, "api_url")
