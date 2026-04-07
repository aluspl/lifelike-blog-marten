import subprocess
import sys
import os

SCRIPT = os.path.join(os.getcwd(), "scripts", "tester.py")


def test_cli_help_exit_code():
    p = subprocess.run([sys.executable, SCRIPT, "--help"], capture_output=True, text=True)
    assert p.returncode in (0, 2)
