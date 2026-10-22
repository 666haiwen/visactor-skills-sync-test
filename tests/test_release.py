"""Release contracts, using an in-memory GitHub API; never publish real artifacts."""

import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
TAG = "skills-v1.0.0"


@pytest.fixture
def publisher(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / ".github/scripts"))
    spec = importlib.util.spec_from_file_location(
        "skills_release", ROOT / ".github/scripts/release.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def build(root, sha, tag, output, repository):
        output.mkdir(parents=True)
        (output / "example.zip").write_bytes(b"mock zip; real packaging tested separately")
        manifest = {"skills": [{"name": "example", "package": {"asset": "example.zip"}}]}
        (output / module.MANIFEST).write_text("{}")
        return manifest

    monkeypatch.setattr(module, "build_artifacts", build)
    return module


@pytest.fixture
def api(publisher):
    class FakeGitHub(publisher.GitHub):
        def __init__(self):
            self.repository = "example/repo"
            self.assets = []
            self.calls = []
            self.main = SHA
            self.tags = []
            self.releases = []
            self.runs = [
                {
                    "id": 42,
                    "head_sha": SHA,
                    "head_branch": "main",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "https://example.test/ci/42",
                }
            ]
            self.jobs = [
                {"name": name, "status": "completed", "conclusion": "success"}
                for name in publisher.REQUIRED_JOBS
            ]

        def request(self, path, data=None, *, missing_ok=False, method=None):
            self.calls.append((path, data))
            route = urlsplit(path).path
            if route == "/git/ref/heads/main":
                return {"object": {"sha": self.main}}
            if route.startswith("/git/ref/tags/"):
                return {"object": {"sha": SHA}} if route.rsplit("/", 1)[1] in self.tags else None
            if route == "/actions/workflows/ci.yml/runs":
                return {"workflow_runs": self.runs}
            if route == "/actions/runs/42/jobs":
                return {"jobs": self.jobs}
            if route == "/tags":
                return [{"name": tag} for tag in self.tags]
            if route == "/releases" and data is None:
                return self.releases
            if route == "/releases/generate-notes":
                return {"body": "Reviewed changes since the previous Skills release."}
            if route == "/releases" and data is not None:
                return {"id": 7, "html_url": f"https://example.test/releases/{data['tag_name']}"}
            if route == "/git/refs":
                self.tags.append(data["ref"].removeprefix("refs/tags/"))
                return {}
            if route == "/releases/7/assets":
                return self.assets
            if route == "/releases/7" and method == "PATCH":
                return {"html_url": "https://example.test/release/7"}
            raise AssertionError(f"Unexpected API request: {path}")

        def upload(self, release_id, path):
            asset = {
                "name": path.name,
                "size": path.stat().st_size,
                "digest": "sha256:" + publisher.digest(path.read_bytes()),
                "state": "uploaded",
            }
            self.calls.append((f"/upload/{release_id}/{path.name}", asset))
            self.assets.append(asset)
            return asset

    return FakeGitHub()


@pytest.mark.parametrize(
    "tag",
    [
        "v1.0.0",
        "skills-v01.0.0",
        "skills-v1.0",
        "skills-v1.0.0-rc.1",
        "skills-v1.0.0\n",
        "skills-v1.0.0;echo nope",
        "skills-v1.0.0+build",
    ],
)
def test_invalid_version_never_calls_api(publisher, api, tag):
    with pytest.raises(publisher.ReleaseError, match="stable version"):
        publisher.release(api, tag, SHA, ROOT, publish=True)
    assert not api.calls


@pytest.mark.parametrize(
    "ref,event",
    [
        ("refs/heads/develop", "workflow_dispatch"),
        ("refs/tags/skills-v1.0.0", "workflow_dispatch"),
        ("refs/heads/main", "push"),
    ],
)
def test_only_manual_main_context_is_accepted(publisher, ref, event):
    with pytest.raises(publisher.ReleaseError, match="manually on main"):
        publisher.check_context({"GITHUB_REF": ref, "GITHUB_EVENT_NAME": event, "GITHUB_SHA": SHA})


def test_preflight_is_read_only(publisher, api):
    result = publisher.release(api, TAG, SHA, ROOT)
    assert result["published"] is False and all(data is None for _, data in api.calls)


@pytest.mark.parametrize("kind", ["tag", "draft", "published", "downgrade"])
def test_existing_or_older_versions_cannot_publish(publisher, api, kind):
    if kind in {"tag", "downgrade"}:
        api.tags = [TAG if kind == "tag" else "skills-v1.10.0"]
    else:
        api.releases = [{"tag_name": TAG, "draft": kind == "draft", "prerelease": False}]
    with pytest.raises(publisher.ReleaseError, match="already exists|greater than"):
        publisher.release(api, TAG, SHA, ROOT, publish=True)
    assert all(data is None for _, data in api.calls)


@pytest.mark.parametrize(
    "status,conclusion",
    [
        ("in_progress", None),
        ("completed", "failure"),
        ("completed", "cancelled"),
        ("completed", "skipped"),
    ],
)
def test_unsuccessful_ci_blocks_publishing(publisher, api, status, conclusion):
    api.runs[0].update(status=status, conclusion=conclusion)
    with pytest.raises(publisher.ReleaseError, match="complete successfully"):
        publisher.release(api, TAG, SHA, ROOT, publish=True)
    assert all(data is None for _, data in api.calls)


@pytest.mark.parametrize(
    "field,value",
    [
        ("head_sha", "b" * 40),
        ("head_branch", "develop"),
        ("event", "pull_request"),
    ],
)
def test_ci_from_other_context_does_not_qualify(publisher, api, field, value):
    api.runs[0][field] = value
    with pytest.raises(publisher.ReleaseError, match="No Skills CI"):
        publisher.release(api, TAG, SHA, ROOT, publish=True)


def test_newer_failed_run_does_not_fall_back_to_old_success(publisher, api):
    api.runs.append({**api.runs[0], "id": 43, "conclusion": "failure"})
    with pytest.raises(publisher.ReleaseError, match="complete successfully"):
        publisher.release(api, TAG, SHA, ROOT, publish=True)


@pytest.mark.parametrize("condition", ["missing", "skipped"])
def test_workflow_success_requires_both_jobs(publisher, api, condition):
    if condition == "missing":
        api.jobs.pop()
    else:
        api.jobs[0]["conclusion"] = "skipped"
    with pytest.raises(publisher.ReleaseError, match="Both lint/regressions"):
        publisher.release(api, TAG, SHA, ROOT, publish=True)


def test_stale_main_is_rejected(publisher, api):
    api.main = "b" * 40
    with pytest.raises(publisher.ReleaseError, match="main has changed"):
        publisher.release(api, TAG, SHA, ROOT, publish=True)
    assert all(data is None for _, data in api.calls)


def test_first_release_ignores_sdk_versions_and_targets_exact_commit(publisher, api, tmp_path):
    api.tags = ["v2.0.8"]
    api.releases = [{"tag_name": "v2.0.8", "draft": False, "prerelease": False}]
    skill = tmp_path / "skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("name: example")
    publisher.release(api, TAG, SHA, tmp_path, publish=True)
    writes = [(path, data) for path, data in api.calls if data is not None]
    assert writes[0] == ("/git/refs", {"ref": f"refs/tags/{TAG}", "sha": SHA})
    path, payload = writes[1]
    assert path == "/releases" and payload["target_commitish"] == SHA
    assert payload["tag_name"] == TAG and payload["draft"] is True
    assert "`example`" in payload["body"]
    assert [path for path, _ in writes[2:4]] == [
        "/upload/7/example.zip",
        "/upload/7/skills-manifest.json",
    ]
    assert writes[-1] == ("/releases/7", {"draft": False, "make_latest": "true"})


def test_later_notes_use_previous_skills_release_not_sdk(publisher, api):
    api.tags = ["v2.0.8", "skills-v1.9.0", "skills-v1.10.0"]
    api.releases = [{"tag_name": tag, "draft": False, "prerelease": False} for tag in api.tags]
    publisher.release(api, "skills-v1.11.0", SHA, ROOT, publish=True)
    notes = next(data for path, data in api.calls if path == "/releases/generate-notes")
    assert notes["previous_tag_name"] == "skills-v1.10.0"


def test_main_advance_while_preparing_notes_stops_release(publisher, api):
    api.releases = [{"tag_name": TAG, "draft": False, "prerelease": False}]
    request = api.request

    def advance_main(path, data=None, **kwargs):
        result = request(path, data, **kwargs)
        if path == "/releases/generate-notes":
            api.main = "b" * 40
        return result

    api.request = advance_main
    with pytest.raises(publisher.ReleaseError, match="main has changed"):
        publisher.release(api, "skills-v1.0.1", SHA, ROOT, publish=True)
    assert not any(path == "/releases" and data is not None for path, data in api.calls)


def test_api_pagination_reads_beyond_first_page(publisher, monkeypatch):
    client = publisher.GitHub("example/repo", "test-token")
    pages = iter([list(range(100)), [100]])
    monkeypatch.setattr(client, "request", lambda path: {"jobs": next(pages)})
    assert list(client.pages("/jobs?filter=latest", "jobs")) == list(range(101))


@pytest.mark.parametrize("status", [401, 403, 500])
def test_api_failure_is_not_treated_as_missing_tag(publisher, monkeypatch, status):
    def fail(*args, **kwargs):
        raise publisher.urllib.error.HTTPError("https://example.test", status, "error", {}, None)

    monkeypatch.setattr(publisher.urllib.request, "urlopen", fail)
    with pytest.raises(publisher.ReleaseError, match=f"HTTP {status}"):
        publisher.GitHub("example/repo", "test-token").request("/git/ref/tags/tag", missing_ok=True)


@pytest.mark.parametrize("failure", ["upload", "missing", "digest", "state", "tag"])
def test_incomplete_or_mismatched_assets_never_publish(publisher, api, failure):
    upload = api.upload

    def fail_upload(release_id, path):
        if failure == "upload":
            raise publisher.ReleaseError("upload failed")
        result = upload(release_id, path)
        if failure == "missing":
            api.assets.pop()
        elif failure == "digest":
            result["digest"] = "sha256:wrong"
        elif failure == "state":
            result["state"] = "starter"
        elif failure == "tag":
            api.tags.clear()
        return result

    api.upload = fail_upload
    if failure == "tag":
        request = api.request

        def wrong_tag(path, data=None, **kwargs):
            if path == f"/git/ref/tags/{TAG}" and any(
                p.startswith("/upload/") for p, _ in api.calls
            ):
                return {"object": {"sha": "b" * 40}}
            return request(path, data, **kwargs)

        api.request = wrong_tag
    with pytest.raises(publisher.ReleaseError, match="remote inspection"):
        publisher.release(api, TAG, SHA, ROOT, publish=True)
    assert not any(path == "/releases/7" for path, _ in api.calls)


def test_packaging_failure_happens_before_remote_writes(publisher, api, monkeypatch):
    def fail(*args):
        raise publisher.PackageError("invalid package")

    monkeypatch.setattr(publisher, "build_artifacts", fail)
    with pytest.raises(publisher.PackageError):
        publisher.release(api, TAG, SHA, ROOT, publish=True)
    assert all(data is None for _, data in api.calls)


def test_asset_upload_uses_binary_body_and_fixed_github_upload_host(
    publisher, monkeypatch, tmp_path
):
    path = tmp_path / "example.zip"
    path.write_bytes(b"zip bytes")
    client = publisher.GitHub("example/repo", "test-token")
    calls = []
    monkeypatch.setattr(client, "_send", lambda *args, **kwargs: calls.append(args))
    client.upload(7, path)
    assert calls == [
        (
            "https://uploads.github.com/repos/example/repo/releases/7/assets?name=example.zip",
            b"zip bytes",
            "application/zip",
        )
    ]
