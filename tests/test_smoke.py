def test_import():
    import bist_extractor  # noqa: F401


def test_cli_help(capsys):
    # simple smoke test: can we parse help
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "-m", "bist_extractor.cli", "--help"], capture_output=True, text=True
    )
    assert res.returncode == 0
    assert "BIST100 Extractor CLI" in res.stdout
