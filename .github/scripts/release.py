"""Manually publish a verified main snapshot; read-only unless --publish is given."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TAG_PATTERN = re.compile(r"skills-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", re.ASCII)
REQUIRED_JOBS = {"Lint and regressions", "Browser smoke (no model)"}


class ReleaseError(Exception):
    pass


class GitHub:
    def __init__(self, repository, token):
        self.base = f"https://api.github.com/repos/{repository}"
        self.token = token

    def request(self, path, data=None, *, missing_ok=False):
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            raise ReleaseError(f"GitHub API {path}: HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ReleaseError(f"GitHub API {path}: {type(error).__name__}") from None

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


def check_context(env):
    if (
        env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or env.get("GITHUB_REF") != "refs/heads/main"
    ):
        raise ReleaseError("Run this workflow manually on main.")
    sha = env.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ReleaseError("The workflow must identify an exact commit SHA.")
    return sha


def check_main(api, sha):
    if api.request("/git/ref/heads/main")["object"]["sha"] != sha:
        raise ReleaseError("main has changed. Start a new workflow run on main and review its CI.")


def check_ci(api, sha):
    runs = [
        run
        for run in api.pages(f"/actions/workflows/ci.yml/runs?head_sha={sha}", "workflow_runs")
        if run["head_sha"] == sha
        and run["head_branch"] == "main"
        and run["event"] in {"push", "workflow_dispatch"}
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
    if versions and requested <= max(versions):
        raise ReleaseError("Choose a version greater than all existing Skills versions.")
    published = [
        item["tag_name"]
        for item in releases
        if not item["draft"] and not item["prerelease"] and TAG_PATTERN.fullmatch(item["tag_name"])
    ]
    return max(published, key=version) if published else None


def release(api, tag, sha, root, *, publish=False):
    version(tag)
    check_main(api, sha)
    previous = check_version(api, tag)
    ci_url = check_ci(api, sha)
    result = {"tag": tag, "sha": sha, "previous_tag": previous, "ci_url": ci_url}
    if not publish:
        return {**result, "mode": "preflight", "published": False}

    if previous:
        notes = api.request(
            "/releases/generate-notes",
            {
                "tag_name": tag,
                "target_commitish": sha,
                "previous_tag_name": previous,
            },
        )["body"]
    else:
        skills = sorted(path.parent.name for path in (root / "skills").glob("*/SKILL.md"))
        if not skills:
            raise ReleaseError("No Skills found in the checked-out release snapshot.")
        notes = "First VisActor Skills release. Included Skills:\n\n" + "\n".join(
            f"- `{name}`" for name in skills
        )
        notes += "\n\nHistorical VMind SDK releases remain available separately."
    notes += f"\n\nSource commit: `{sha}`\n\n[Skills CI]({ci_url})"
    # Recheck immediately before writing; never substitute a newer main commit.
    check_main(api, sha)
    check_version(api, tag)
    check_ci(api, sha)
    # GitHub creates the tag at this exact SHA as part of creating the release.
    created = api.request(
        "/releases",
        {
            "tag_name": tag,
            "target_commitish": sha,
            "name": f"VisActor Skills {tag.removeprefix('skills-v')}",
            "body": notes,
            "draft": False,
            "prerelease": False,
            "make_latest": "true",
        },
    )
    return {**result, "mode": "publish", "published": True, "url": created["html_url"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--publish", action="store_true", help="Create the tag and release after checks"
    )
    args = parser.parse_args()
    try:
        version(args.version)
        sha = check_context(os.environ)
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        token = os.environ.get("GH_TOKEN", "")
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or not token:
            raise ReleaseError("GITHUB_REPOSITORY and GH_TOKEN are required.")
        result = release(
            GitHub(repository, token),
            args.version,
            sha,
            Path(__file__).resolve().parents[2],
            publish=args.publish,
        )
        output = json.dumps(result, indent=2)
        print(output)
        if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(summary, "a") as stream:
                stream.write(f"## Skills release\n\n```json\n{output}\n```\n")
    except ReleaseError as error:
        print(f"Release stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
