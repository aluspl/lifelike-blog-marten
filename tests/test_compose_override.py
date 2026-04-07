import importlib


override = importlib.import_module("scripts.compose_override")


def test_generate_override_tmpfile():
    mapping = {"postgres": {"container_port": 5432, "host_port": 54322}}
    tmpfile = override.generate_override(mapping)
    assert tmpfile.endswith(".yml")
    with open(tmpfile, "r", encoding="utf-8") as fh:
        content = fh.read()
    assert "ports:" in content
