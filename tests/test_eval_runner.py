import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fixed_runner", ROOT / "evals/scripts/run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_preparation_copies_only_runtime_and_inputs(tmp_path):
    task = runner.load_tasks()[0]
    workspace = runner.prepare(task, tmp_path / "case")
    assert sorted(p.name for p in workspace.iterdir()) == [".agents", "inputs", "outputs"]
    assert (workspace / ".agents/skills" / task["skill"] / "SKILL.md").exists()
    assert not list(workspace.rglob("expectations.json"))


def test_capture_preserves_nonzero_exit_and_redacts_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-fixture-value")
    result = runner.capture(
        [
            sys.executable,
            "-c",
            'import os,sys; print(os.environ["TEST_API_KEY"]); print("failure", file=sys.stderr); sys.exit(7)',
        ],
        "",
        tmp_path,
        10,
    )
    assert result["exitCode"] == 7
    assert (tmp_path / "events.jsonl").read_text() == "[REDACTED]\n"
    assert "failure" in (tmp_path / "stderr.log").read_text()


def test_timeout_is_a_failure_and_keeps_early_output(tmp_path):
    result = runner.capture(
        [sys.executable, "-c", 'import time; print("started", flush=True); time.sleep(30)'],
        "",
        tmp_path,
        1,
    )
    assert result["timedOut"] is True
    assert result["exitCode"] != 0
    assert "started" in (tmp_path / "events.jsonl").read_text()


def test_visual_review_is_never_implied_by_file_existence(tmp_path):
    task = next(t for t in runner.load_tasks() if t["id"] == "story-retention-html")
    workspace = runner.prepare(task, tmp_path / "case")
    for filename in runner.load_expectations(task)["artifacts"]:
        output = workspace / "outputs" / filename
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("fixture")
    result = runner.evaluate_files(task, tmp_path / "case", {"exitCode": 0, "timedOut": False})
    assert result["status"] == "needs-review"
    assert result["visualReview"]["status"] == "not-run"
    assert result["browser"]["status"] == "not-run"


def test_answer_only_task_rejects_unwanted_artifacts(tmp_path):
    task = {"id": "explanation", "skill": "data-storytelling", "inputs": []}
    directory = tmp_path / "case"
    workspace = runner.prepare(task, directory)
    runner.write_json(
        directory / "expectations.json",
        {"answerOnly": True, "artifacts": [], "review": ["Answer the question"]},
    )
    (directory / "final-response.md").write_text("Explain the supplied observations.")
    (workspace / "outputs/demo.html").write_text("unrequested")
    result = runner.evaluate_files(task, directory, {"exitCode": 0})
    assert result["status"] == "failed"
    assert result["browser"]["status"] == "not-applicable"


def test_continuation_copies_prior_artifacts_without_mutating_snapshot(tmp_path):
    task = runner.load_tasks()[0]
    first = runner.prepare(task, tmp_path / "first")
    (first / "outputs/spec.js").write_text("first")
    second = runner.prepare(task, tmp_path / "second", first)
    assert (second / "outputs/spec.js").read_text() == "first"
    (second / "outputs/spec.js").write_text("second")
    assert (first / "outputs/spec.js").read_text() == "first"


def test_continuation_cannot_pass_with_unchanged_source(tmp_path):
    task = runner.load_tasks()[0]
    directory = tmp_path / "case"
    workspace = runner.prepare(task, directory)
    runner.write_json(
        directory / "expectations.json", {"artifacts": ["spec.js", "demo.html"], "review": []}
    )
    for name in ["spec.js", "demo.html"]:
        (workspace / "outputs" / name).write_text("original")
    result = runner.evaluate_files(
        task,
        directory,
        {
            "exitCode": 0,
            "previousArtifacts": {"spec.js": runner.digest(workspace / "outputs/spec.js")},
        },
    )
    assert result["status"] == "failed"


def test_custom_inputs_are_copied_without_modifying_sources(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Explain the provided data")
    data = tmp_path / "input.csv"
    data.write_text("x,y\n1,2\n")
    task = runner.custom_task("data-storytelling", prompt, [data], None)
    workspace = runner.prepare(task, tmp_path / "custom")
    assert (workspace / "inputs/input.csv").read_bytes() == data.read_bytes()
    (workspace / "inputs/input.csv").write_text("changed copy")
    assert data.read_text() == "x,y\n1,2\n"


def test_custom_task_rejects_missing_or_duplicate_inputs(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Task")
    with pytest.raises(ValueError, match="must be a file"):
        runner.custom_task("data-storytelling", prompt, [tmp_path / "absent"], None)
    for name in ["first", "second"]:
        (tmp_path / name).mkdir()
        (tmp_path / name / "same.csv").touch()
    with pytest.raises(ValueError, match="Duplicate"):
        runner.custom_task(
            "data-storytelling",
            prompt,
            [tmp_path / "first/same.csv", tmp_path / "second/same.csv"],
            None,
        )


@pytest.mark.parametrize("html", ["../outside.html", "/absolute.html", "demo.js"])
def test_custom_html_must_be_within_outputs(tmp_path, html):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Task")
    with pytest.raises(ValueError, match="relative .html"):
        runner.custom_task("data-storytelling", prompt, [], html)


def test_custom_task_checks_answer_without_inventing_artifact_requirements(tmp_path):
    directory = tmp_path / "custom"
    (directory / "workspace/outputs").mkdir(parents=True)
    runner.write_json(
        directory / "expectations.json", {"artifacts": [], "requireAnswer": True, "review": []}
    )
    task = {"id": "custom"}
    failed = runner.evaluate_files(task, directory, {"exitCode": 0})
    assert failed["status"] == "failed"
    (directory / "final-response.md").write_text("Explanation")
    result = runner.evaluate_files(task, directory, {"exitCode": 0})
    assert result["status"] == "needs-review" and result["artifacts"] == []


@pytest.mark.parametrize(
    "extra", [["--case", "story-retention-html"], ["--group", "core"], ["--browser"]]
)
def test_custom_cli_rejects_ambiguous_selection_before_model_access(tmp_path, monkeypatch, extra):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Task")
    monkeypatch.setattr(
        sys,
        "argv",
        ["run.py", "--skill", "data-storytelling", "--prompt-file", str(prompt), *extra],
    )
    with pytest.raises(SystemExit) as failed:
        runner.main()
    assert failed.value.code == 2


@pytest.mark.parametrize(
    "skill,cases,group,count,skills",
    [
        (None, None, None, 3, {"data-storytelling"}),
        ("data-storytelling", None, "extended", 2, {"data-storytelling"}),
        ("data-storytelling", None, "all", 5, {"data-storytelling"}),
        # Runtime Skills may exist before fixed model cases are added.
        (
            None,
            None,
            "all",
            len(runner.load_tasks()),
            {task["skill"] for task in runner.load_tasks()},
        ),
        (None, ["story-retention-html"], None, 1, {"data-storytelling"}),
    ],
)
def test_fixed_selection_scopes_groups_to_skills(skill, cases, group, count, skills):
    selected = runner.select_tasks(runner.load_tasks(), skill, cases, group)
    assert len(selected) == count
    assert {task["skill"] for task in selected} == skills


@pytest.mark.parametrize(
    "cases,group,message",
    [(["removed-chart"], None, "Unknown case ids"), (None, "missing-group", "No cases match")],
)
def test_invalid_skill_selection_fails_before_model_access(cases, group, message):
    with pytest.raises(ValueError, match=message):
        runner.select_tasks(runner.load_tasks(), "data-storytelling", cases, group)


def test_skill_cli_lists_fixed_cases_without_custom_prompt_or_credentials(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run.py", "--skill", "data-storytelling", "--list"])
    runner.main()
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert all(line.startswith("story-") and ", core," in line for line in lines)


def test_preparation_uses_inputs_from_the_selected_catalog(tmp_path, monkeypatch):
    catalogs = tmp_path / "cases"
    for skill, value in [
        ("other-skill", "other"),
        ("data-storytelling", "story"),
    ]:
        folder = catalogs / skill / "inputs"
        folder.mkdir(parents=True)
        (folder / "same.csv").write_text(value)
    monkeypatch.setattr(runner, "CASES", catalogs)
    task = {"id": "test", "skill": "data-storytelling", "inputs": ["same.csv"]}
    workspace = runner.prepare(task, tmp_path / "run")
    assert (workspace / "inputs/same.csv").read_text() == "story"


def test_saved_expectations_do_not_depend_on_current_catalog(tmp_path, monkeypatch):
    directory = tmp_path / "run"
    (directory / "workspace/outputs").mkdir(parents=True)
    runner.write_json(directory / "expectations.json", {"artifacts": [], "review": ["snapshot"]})
    monkeypatch.setattr(runner, "CASES", tmp_path / "missing-catalog")
    result = runner.evaluate_files({"id": "old-case"}, directory, {"exitCode": 0})
    assert result["visualReview"]["checklist"] == ["snapshot"]


@pytest.mark.parametrize("problem", ["mismatched-skill", "duplicate-id"])
def test_catalog_loader_rejects_ambiguous_ownership(tmp_path, monkeypatch, problem):
    catalogs = tmp_path / "cases"
    folder = catalogs / "data-storytelling"
    folder.mkdir(parents=True)
    tasks = [
        {
            "id": "duplicate",
            "skill": "wrong" if problem == "mismatched-skill" else "data-storytelling",
        }
    ]
    if problem == "duplicate-id":
        tasks.append(dict(tasks[0]))
    runner.write_json(folder / "tasks.json", tasks)
    monkeypatch.setattr(runner, "CASES", catalogs)
    with pytest.raises(ValueError, match="does not belong|Duplicate case id"):
        runner.load_tasks()


def test_story_acceptance_requires_intermediates_but_not_standalone_spec_js(tmp_path):
    task = next(t for t in runner.load_tasks() if t["id"] == "story-retention-html")
    directory = tmp_path / "story"
    workspace = runner.prepare(task, directory)
    contract = runner.load_expectations(task)
    assert "spec.js" not in contract["artifacts"]
    for filename in contract["artifacts"]:
        file = workspace / "outputs" / filename
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("fixture")
    execution = {"exitCode": 0, "timedOut": False}
    assert runner.evaluate_files(task, directory, execution)["status"] == "needs-review"
    (workspace / "outputs/runtime/spec_map.json").unlink()
    assert runner.evaluate_files(task, directory, execution)["status"] == "failed"
