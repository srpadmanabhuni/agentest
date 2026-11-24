"""After `pip install agentest-ai`, a clone-only path gives a friendly hint and exit 2, not a traceback."""
from agentest.cli import main


def test_missing_agents_dir_gives_clone_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["std", "run", "--agents", "examples/agnostic_demo/agents", "--agent", "refill_bot_buggy"])
    err = capsys.readouterr().err
    assert code == 2
    assert "examples/agnostic_demo/agents not found" in err
    assert "git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git" in err
    assert "agentest demo" in err
    assert "Traceback" not in err


def test_missing_config_file_gives_clone_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["std", "run", "--config", "examples/missing.yaml", "--agent", "a22", "--ids", "T1-018"])
    err = capsys.readouterr().err
    assert code == 2
    assert "examples/missing.yaml not found" in err
    assert "agentest demo" in err


def test_bundled_agent_still_runs_without_a_clone(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["std", "run", "--agent", "a22", "--ids", "T1-018", "--format", "md"]) == 0
    assert "| T1-018 | fail |" in capsys.readouterr().out
