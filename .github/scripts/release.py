"""Build release previews and publish verified snapshots for release_plan.py."""

import json
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from package_skills import MANIFEST, build_artifacts, digest, git
from package_skills import PackageError as PackageError

TAG_PATTERN = re.compile(r"skills-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", re.ASCII)
REQUIRED_JOBS = {"Lint and regressions", "Browser smoke (no model)"}


class ReleaseError(Exception):
    pass


class GitHub:
    def __init__(self, repository, token):
        self.repository = repository
        self.base = f"https://api.github.com/repos/{repository}"
        self.token = token

    def request(self, path, data=None, *, missing_ok=False, method=None):
        return self._send(
            self.base + path,
            json.dumps(data).encode() if data is not None else None,
            "application/json",
            missing_ok=missing_ok,
            method=method,
        )

    def upload(self, release_id, path):
        url = f"https://uploads.github.com/repos/{self.repository}/releases/{release_id}/assets"
        url += "?" + urllib.parse.urlencode({"name": path.name})
        content_type = "application/zip" if path.suffix == ".zip" else "application/json"
        return self._send(url, path.read_bytes(), content_type)

    def _send(self, url, data, content_type, *, missing_ok=False, method=None):
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": content_type,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            raise ReleaseError(f"GitHub API {url}: HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ReleaseError(f"GitHub API {url}: {type(error).__name__}") from None

    def pages(self, path, key=None):
        separator = "&" if "?" in path else "?"
        page = 1
        while True:
            response = self.request(f"{path}{separator}per_page=100&page={page}")
            items = response[key] if key else response
            yield from items
            if len(items) < 100:
                return
            page += 1


def version(tag):
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ReleaseError("Use a stable version such as skills-v1.0.0 (no leading zeros).")
    return tuple(map(int, match.groups()))


def check_main(api, sha):
    if api.request("/git/ref/heads/main")["object"]["sha"] != sha:
        raise ReleaseError("main has changed. Review a new release plan for the current main commit.")


def check_ci(api, sha):
    runs = [
        run
        for run in api.pages(f"/actions/workflows/ci.yml/runs?head_sha={sha}", "workflow_runs")
        if run["head_sha"] == sha and run["head_branch"] == "main" and run["event"] == "push"
    ]
    if not runs:
        raise ReleaseError("No Skills CI run found for this main commit.")
    run = max(runs, key=lambda item: item["id"])
    if run["status"] != "completed" or run["conclusion"] != "success":
        raise ReleaseError("The latest Skills CI run for this commit must complete successfully.")
    jobs = list(api.pages(f"/actions/runs/{run['id']}/jobs?filter=latest", "jobs"))
    successful = {
        job["name"]
        for job in jobs
        if job["status"] == "completed" and job["conclusion"] == "success"
    }
    if not REQUIRED_JOBS <= successful:
        raise ReleaseError(
            "Both lint/regressions and browser smoke must pass; skipped jobs do not qualify."
        )
    return run["html_url"]


def check_version(api, tag):
    requested = version(tag)
    if api.request(f"/git/ref/tags/{tag}", missing_ok=True) is not None:
        raise ReleaseError(f"Tag {tag} already exists; never move or overwrite it.")
    # Include drafts: a reserved version must not be published over accidentally.
    releases = list(api.pages("/releases"))
    if any(item["tag_name"] == tag for item in releases):
        raise ReleaseError(f"Release {tag} already exists (possibly a draft).")
    tags = [item["name"] for item in api.pages("/tags")]
    reserved = tags + [item["tag_name"] for item in releases]
    versions = [version(name) for name in reserved if TAG_PATTERN.fullmatch(name)]
    if not versions and requested != (1, 0, 0):
        raise ReleaseError("The first Skills version must be skills-v1.0.0.")
    if versions and requested <= max(versions):
        raise ReleaseError("Choose a version greater than all existing Skills versions.")
    published = [
        item["tag_name"]
        for item in releases
        if not item["draft"] and not item["prerelease"] and TAG_PATTERN.fullmatch(item["tag_name"])
    ]
    return max(published, key=version) if published else None


def read_release_notes(root, sha, tag):
    """Read reviewed notes from the same committed snapshot as the packages."""
    path = f"docs/releases/{tag}.md"
    entry = git(root, "ls-tree", "-z", sha, "--", path).rstrip(b"\0")
    if not entry:
        raise ReleaseError(f"Missing reviewed release notes in {sha}: {path}")
    metadata, _ = entry.split(b"\t", 1)
    mode, kind, oid = metadata.decode().split()
    if kind != "blob" or mode not in {"100644", "100755"}:
        raise ReleaseError(f"Release notes must be a regular committed file: {path}")
    notes = git(root, "cat-file", "blob", oid).decode("utf-8").strip()
    if not notes:
        raise ReleaseError(f"Release notes must not be empty: {path}")
    return notes


def render_release_body(notes, repository, tag, sha, ci_url, previous, manifest):
    body = notes + "\n\n## Release snapshot\n\nIncluded Skills:\n\n"
    body += "\n".join(f"- `{skill['name']}`" for skill in manifest["skills"])
    body += f"\n\nSource commit: `{sha}`\n\n[Skills CI]({ci_url})"
    if previous:
        body += f"\n\n[Changes since {previous}](https://github.com/{repository}/compare/{previous}...{tag})"
    return body + "\n"


def release(api, tag, sha, root, *, publish=False, output=None, preview_ci_url=None):
    version(tag)
    if publish and preview_ci_url is not None:
        raise ReleaseError("PR preview context cannot publish.")
    if output is None:
        with tempfile.TemporaryDirectory(prefix="skills-release-") as scratch:
            return release(
                api,
                tag,
                sha,
                root,
                publish=publish,
                output=Path(scratch) / "artifacts",
                preview_ci_url=preview_ci_url,
            )
    if preview_ci_url is None:
        check_main(api, sha)
    previous = check_version(api, tag)
    ci_url = preview_ci_url if preview_ci_url is not None else check_ci(api, sha)
    notes = read_release_notes(root, sha, tag)
    manifest = build_artifacts(root, sha, tag, output, api.repository)
    body = render_release_body(notes, api.repository, tag, sha, ci_url, previous, manifest)
    result = {
        "tag": tag,
        "sha": sha,
        "previous_tag": previous,
        "ci_url": ci_url,
        "assets": [s["package"]["asset"] for s in manifest["skills"]] + [MANIFEST],
        "release_body": body,
    }
    if not publish:
        return {**result, "mode": "preflight", "published": False}

    # Recheck immediately before writing; never substitute a newer main commit.
    check_main(api, sha)
    check_version(api, tag)
    check_ci(api, sha)
    # Reserve the exact ref first: concurrent creation must fail, never silently retarget.
    api.request("/git/refs", {"ref": f"refs/tags/{tag}", "sha": sha})
    created = api.request(
        "/releases",
        {
            "tag_name": tag,
            "target_commitish": sha,
            "name": f"VisActor Skills {tag.removeprefix('skills-v')}",
            "body": body,
            "draft": True,
            "prerelease": False,
        },
    )
    release_id = created["id"]
    paths = [output / name for name in result["assets"]]
    expected = {
        path.name: (path.stat().st_size, "sha256:" + digest(path.read_bytes())) for path in paths
    }
    try:
        for path in paths:
            api.upload(release_id, path)
        uploaded = list(api.pages(f"/releases/{release_id}/assets"))
        actual = {
            asset["name"]: (asset["size"], asset.get("digest"))
            for asset in uploaded
            if asset["state"] == "uploaded"
        }
        if len(uploaded) != len(expected) or actual != expected:
            raise ReleaseError("Uploaded assets do not match the local manifest/ZIP checksums.")
        if api.request(f"/git/ref/tags/{tag}")["object"]["sha"] != sha:
            raise ReleaseError("Release tag no longer matches the verified commit.")
        published = api.request(
            f"/releases/{release_id}", {"draft": False, "make_latest": "true"}, method="PATCH"
        )
    except ReleaseError as error:
        raise ReleaseError(
            f"Release {tag} requires remote inspection before retrying: {error}. "
            "Do not move the tag or blindly republish; the draft or publication may already exist."
        ) from error
    return {**result, "mode": "publish", "published": True, "url": published["html_url"]}
