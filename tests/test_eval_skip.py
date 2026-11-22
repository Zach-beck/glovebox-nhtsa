import json
import os
import subprocess
import sys
from pathlib import Path


def test_model_eval_skips_without_a_key(tmp_path: Path):
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)
    repo = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, str(repo / "evals" / "local.py")],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "skipped"
    assert "OPENAI_API_KEY" in report["reason"]
