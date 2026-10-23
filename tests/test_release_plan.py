"""Automatic release intent and event trust boundaries; no live GitHub writes."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_release import api as api
from test_release import publisher as publisher
from test_release import release_module as release_module

ROOT = Path(__file__).resolve().parents[1]
TAG = "skills-v1.0.0"


@pytest.fixture
def planner(publisher, monkeypatch):
    monkeypatch.setitem(sys.modules, "release", publisher)
    spec = importlib.util.spec_from_file_location(
        "release_plan", ROOT / ".github/scripts/release_plan.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    def git(*args):
        return (
            subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)
            .decode()
            .strip()
        )

    git("init", "-q")
    git("config", "core.hooksPath", "/dev/null")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    git("commit", "--allow-empty", "-qm", "Before release plans", "--no-gpg-sign")

    def commit(value):
        path = root / ".github/release-plan.json"
        path.parent.mkdir(exist_ok=True)
        if path.is_symlink():
            path.unlink()
        path.write_text(value, encoding="utf-8")
        git("add", ".")
        git("commit", "--allow-empty", "-qm", "Snapshot", "--no-gpg-sign")
        return git("rev-parse", "HEAD")

    return root, git, commit


def events(sha, base):
    env = {
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REPOSITORY": "example/repo",
        "GITHUB_SHA": sha,
        "GITHUB_RUN_ID": "123",
    }
    preview = {"pull_request": {"base": {"ref": "main", "sha": base}}}
    completed = {
        "action": "completed",
        "workflow_run": {
            "id": 42,
            "name": "Skills CI",
            "event": "push",
            "head_branch": "main",
            "head_sha": sha,
            "head_repository": {"full_name": "example/repo"},
            "status": "completed",
            "conclusion": "success",
        },
    }
    return env, preview, completed


def configure_api(api, sha):
    api.main = api.tag_sha = sha
    api.runs[0]["head_sha"] = sha


@pytest.mark.parametrize(
    "raw",
    [
        "{}",
        "[]",
        "{",
        '{"version": true}',
        '{"version": "v1.0.0"}',
        '{"version": null, "publish": true}',
    ],
)
def test_invalid_plan_is_rejected(planner, repo, raw):
    root, _, commit = repo
    with pytest.raises(planner.ReleaseError):
        planner.read_plan(root, commit(raw))


def test_plan_uses_committed_json_and_allows_absent_legacy_base(planner, repo):
    root, git, commit = repo
    base = git("rev-parse", "HEAD")
    assert planner.read_plan(root, base, allow_missing=True) is None
    with pytest.raises(planner.ReleaseError, match="Missing"):
        planner.read_plan(root, base)
    sha = commit(json.dumps({"version": TAG}))
    (root / planner.PLAN).write_text('{"version": null}')
    assert planner.read_plan(root, sha) == TAG


def test_symlink_plan_is_rejected(planner, repo):
    root, git, commit = repo
    commit('{"version": null}')
    path = root / planner.PLAN
    path.unlink()
    path.symlink_to("other.json")
    git("add", ".")
    git("commit", "-qm", "Symlink", "--no-gpg-sign")
    with pytest.raises(planner.ReleaseError, match="regular"):
        planner.read_plan(root, git("rev-parse", "HEAD"))


@pytest.mark.parametrize("value,reason", [(None, "no-release"), (TAG, "unchanged-plan")])
@pytest.mark.parametrize("mode", ["preview", "publish"])
def test_disabled_or_unchanged_plan_never_publishes(
    planner, api, repo, tmp_path, value, reason, mode
):
    root, _, commit = repo
    base = commit(json.dumps({"version": value}))
    sha = commit(json.dumps({"version": value}))
    env, preview, completed = events(sha, base)
    configure_api(api, sha)
    env["GITHUB_EVENT_NAME"] = "pull_request" if mode == "preview" else "workflow_run"
    result = planner.execute(
        api, root, env, preview if mode == "preview" else completed, mode, tmp_path / "output"
    )
    assert result["skipped"] == reason
    assert all(data is None for _, data in api.calls)
    assert not (tmp_path / "output").exists()


def test_main_pr_previews_new_plan_without_requiring_main_ci(planner, api, repo, tmp_path):
    root, git, commit = repo
    base = git("rev-parse", "HEAD")
    sha = commit(json.dumps({"version": TAG}))
    env, event, _ = events(sha, base)
    api.runs = []  # The candidate is not main, and its CI is still running.
    result = planner.execute(api, root, env, event, "preview", tmp_path / "output")
    assert result["tag"] == TAG and result["published"] is False
    assert "Reviewed migration steps." in result["release_body"]
    assert (tmp_path / "output/example.zip").exists()
    assert all(data is None for _, data in api.calls)


def test_successful_main_ci_publishes_changed_plan_without_editing_it(planner, api, repo, tmp_path):
    root, git, commit = repo
    base = git("rev-parse", "HEAD")
    sha = commit(json.dumps({"version": TAG}))
    env, _, event = events(sha, base)
    env.update(GITHUB_EVENT_NAME="workflow_run", GITHUB_SHA="b" * 40)
    configure_api(api, sha)
    before = (root / planner.PLAN).read_bytes()
    result = planner.execute(api, root, env, event, "publish", tmp_path / "output")
    assert result["published"] is True and result["sha"] == sha
    assert (root / planner.PLAN).read_bytes() == before
    assert not git("status", "--porcelain")


def test_merge_compares_plan_with_first_parent_not_develop_parent(planner, api, repo, tmp_path):
    root, git, commit = repo
    commit('{"version": null}')
    main = git("branch", "--show-current")
    git("switch", "-c", "candidate")
    commit(json.dumps({"version": TAG}))
    git("switch", main)
    base = commit('{"version": null}')
    git("-c", "commit.gpgsign=false", "merge", "--no-ff", "candidate", "-m", "Release PR")
    sha = git("rev-parse", "HEAD")
    env, _, event = events(sha, base)
    env["GITHUB_EVENT_NAME"] = "workflow_run"
    configure_api(api, sha)
    result = planner.execute(api, root, env, event, "publish", tmp_path / "output")
    assert result["published"] is True


@pytest.mark.parametrize(
    "event_name,base", [("pull_request", "develop"), ("push", "main"), ("workflow_run", "main")]
)
def test_preview_is_only_for_main_pull_requests(planner, api, repo, tmp_path, event_name, base):
    root, git, _ = repo
    sha = git("rev-parse", "HEAD")
    env, event, _ = events(sha, sha)
    env["GITHUB_EVENT_NAME"] = event_name
    event["pull_request"]["base"]["ref"] = base
    with pytest.raises(planner.ReleaseError, match="targeting main"):
        planner.execute(api, root, env, event, "preview", tmp_path / "output")
    assert not api.calls


def test_stale_workflow_run_never_publishes_new_main(planner, api, repo, tmp_path):
    root, _, commit = repo
    sha = commit(json.dumps({"version": TAG}))
    env, _, event = events(sha, sha)
    env["GITHUB_EVENT_NAME"] = "workflow_run"
    api.main = "b" * 40
    with pytest.raises(planner.ReleaseError, match="main has changed"):
        planner.execute(api, root, env, event, "publish", tmp_path / "output")
    assert all(data is None for _, data in api.calls)


@pytest.mark.parametrize(
    "field,value",
    [
        ("event", "pull_request"),
        ("head_branch", "develop"),
        ("conclusion", "failure"),
        ("status", "in_progress"),
        ("name", "Other CI"),
        ("head_repository", {"full_name": "attacker/repo"}),
        ("head_sha", "main"),
    ],
)
def test_untrusted_or_unsuccessful_ci_cannot_publish(planner, api, repo, tmp_path, field, value):
    root, git, _ = repo
    sha = git("rev-parse", "HEAD")
    env, _, event = events(sha, sha)
    env["GITHUB_EVENT_NAME"] = "workflow_run"
    event["workflow_run"][field] = value
    with pytest.raises(planner.ReleaseError):
        planner.execute(api, root, env, event, "publish", tmp_path / "output")
    assert not api.calls


@pytest.mark.parametrize(
    "field,value", [("path", ".github/workflows/other.yml"), ("head_sha", "b" * 40)]
)
def test_trigger_run_is_verified_through_github(planner, api, repo, tmp_path, field, value):
    root, _, commit = repo
    sha = commit(json.dumps({"version": TAG}))
    env, _, event = events(sha, sha)
    env["GITHUB_EVENT_NAME"] = "workflow_run"
    configure_api(api, sha)
    api.runs[0][field] = value
    with pytest.raises(planner.ReleaseError, match="Triggering run"):
        planner.execute(api, root, env, event, "publish", tmp_path / "output")
    assert all(data is None for _, data in api.calls)


def test_preview_mode_cannot_be_used_to_bypass_publish_ci(publisher, api):
    with pytest.raises(publisher.ReleaseError, match="cannot publish"):
        publisher.release(api, TAG, "a" * 40, ROOT, publish=True, preview_ci_url="pr-ci")
    assert not api.calls


def test_preview_summary_contains_full_body_and_candidate_notice(planner, tmp_path):
    summary = tmp_path / "summary.md"
    planner.write_summary({"published": False, "release_body": "Reviewed notes.\n"}, summary)
    text = summary.read_text()
    assert "## Release body preview\n\nReviewed notes.\n" in text
    assert "final main snapshot" in text
