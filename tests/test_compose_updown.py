import importlib


tester = importlib.import_module("scripts.tester")


def test_compose_up_nonexistent():
    ok, out = tester.compose_up("/non/existent/docker-compose.yml")
    assert ok is False
