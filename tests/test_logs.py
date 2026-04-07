import importlib
import os


logs = importlib.import_module("scripts.logs")


def test_write_log():
    p = logs.write_log("test", "hello")
    assert os.path.exists(p)
    with open(p, "r", encoding="utf-8") as fh:
        assert "hello" in fh.read()
