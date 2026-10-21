"""Build fixed stories by invoking scripts from the copied Skill."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_story(workspace: Path, config: dict) -> list[dict]:
    runtime = workspace / "outputs/runtime"
    runtime.mkdir(parents=True)
    for file in (workspace / "inputs").iterdir():
        shutil.copy2(file, runtime / file.name)
    (runtime / "generated-assets").mkdir()
    skill = workspace / ".agents/skills/chart-storytelling"
    commands = [
        ("validate_story_plan.py", ["--plan-file", "outputs/runtime/plan.md"]),
        (
            f"build-{'html' if config['target'] == 'html' else 'ppt'}/scripts/prepare_story_head.py",
            [
                "--preset",
                config["preset"],
                "--plan-file",
                "outputs/runtime/plan.md",
                "--head-output",
                "outputs/runtime/story-head.html",
            ],
        ),
        (
            "assemble_story_specs.py",
            [
                "--plan-file",
                "outputs/runtime/plan.md",
                "--dataset-json",
                "outputs/runtime/dataset_map.json",
                "--specs-json",
                "outputs/runtime/chart_specs.json",
                "--output",
                "outputs/runtime/spec_map.json",
            ],
        ),
        (
            "normalize_story_assets.py",
            [
                "--plan-file",
                "outputs/runtime/plan.md",
                "--assets-dir",
                "outputs/runtime/generated-assets",
                "--output",
                "outputs/runtime/resolved_asset_bindings.json",
                "--report-output",
                "outputs/runtime/asset_resolution_report.json",
            ],
        ),
        (
            "compose_story.py",
            [
                "--target",
                config["target"],
                "--runtime-dir",
                "outputs/runtime",
                "--body-file",
                f"outputs/runtime/{config['body']}",
                "--config-file",
                "outputs/runtime/page.json",
                "--output",
                "outputs/output.html",
            ],
        ),
        ("validate_js.py", ["outputs/output.html"]),
    ]
    logs = []
    for name, args in commands:
        script = skill / (name if "/" in name else f"scripts/{name}")
        result = subprocess.run(
            [sys.executable, "-B", str(script), *args],
            cwd=workspace,
            env={k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL", "TMPDIR"}},
            capture_output=True,
            text=True,
            timeout=30,
        )
        logs.append({
            "script": name, "args": args, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
        })
        (workspace.parent / "generate.json").write_text(
            json.dumps(logs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if result.returncode:
            raise RuntimeError(f"{name}: {result.stderr}\n{result.stdout}")
    return logs
