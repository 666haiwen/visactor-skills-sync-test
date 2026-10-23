"""Preview a main PR's release plan, or publish after trusted main CI completes."""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from package_skills import PackageError, git
from release import GitHub, ReleaseError, check_main, release, version

PLAN = ".github/release-plan.json"


def commit_sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ReleaseError("Expected an exact Git commit SHA.")
    return value


def context(env, event, mode):
    repository = env.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ReleaseError("GITHUB_REPOSITORY is required.")
    if mode == "preview":
        pr = event.get("pull_request", {})
        if (
            env.get("GITHUB_EVENT_NAME") != "pull_request"
            or pr.get("base", {}).get("ref") != "main"
        ):
            raise ReleaseError("Preview requires a pull_request targeting main.")
        return {
            "sha": commit_sha(env.get("GITHUB_SHA")),
            "base": commit_sha(pr["base"].get("sha")),
            "ci_url": f"https://github.com/{repository}/actions/runs/{env['GITHUB_RUN_ID']}",
        }
    run = event.get("workflow_run", {})
    if (
        env.get("GITHUB_EVENT_NAME") != "workflow_run"
        or event.get("action") != "completed"
        or run.get("name") != "Skills CI"
        or run.get("event") != "push"
        or run.get("head_branch") != "main"
        or run.get("head_repository", {}).get("full_name") != repository
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
    ):
        raise ReleaseError("Publication requires successful push CI on this repository's main.")
    return {"sha": commit_sha(run.get("head_sha")), "run_id": run["id"]}


def read_plan(root, sha, *, allow_missing=False):
    entry = git(root, "ls-tree", "-z", sha, "--", PLAN).rstrip(b"\0")
    if not entry:
        if allow_missing:
            return None
        raise ReleaseError(f'Missing {PLAN}; use {{"version": null}} for no release.')
    metadata, _ = entry.split(b"\t", 1)
    mode, kind, oid = metadata.decode().split()
    if kind != "blob" or mode not in {"100644", "100755"}:
        raise ReleaseError("Release plan must be a regular committed file.")
    try:
        plan = json.loads(git(root, "cat-file", "blob", oid))
    except (ValueError, UnicodeError) as error:
        raise ReleaseError("Release plan must contain valid UTF-8 JSON.") from error
    if not isinstance(plan, dict) or set(plan) != {"version"}:
        raise ReleaseError("Release plan must contain exactly one field: version.")
    tag = plan["version"]
    if tag is not None:
        if not isinstance(tag, str):
            raise ReleaseError("Release plan version must be a stable Skills tag or null.")
        version(tag)
    return tag


def execute(api, root, env, event, mode, output):
    selected = context(env, event, mode)
    sha = selected["sha"]
    if mode == "publish":
        # Never use workflow_run's GITHUB_SHA (the default branch may have advanced).
        check_main(api, sha)
        run = api.request(f"/actions/runs/{selected['run_id']}")
        if (
            run.get("head_sha") != sha
            or run.get("head_branch") != "main"
            or run.get("event") != "push"
            or run.get("path") != ".github/workflows/ci.yml"
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
        ):
            raise ReleaseError("Triggering run is not successful Skills CI for this main SHA.")
        # A reviewed merge commit's first parent is the preceding main snapshot.
        parents = git(root, "rev-list", "--parents", "-n", "1", sha).decode().split()
        if len(parents) < 2:
            raise ReleaseError("Release commit requires a previous main snapshot.")
        base = parents[1]
    else:
        base = selected["base"]
    tag = read_plan(root, sha)
    previous = read_plan(root, base, allow_missing=True)
    if tag is None or tag == previous:
        return {
            "mode": mode,
            "sha": sha,
            "tag": tag,
            "published": False,
            "skipped": "no-release" if tag is None else "unchanged-plan",
        }
    return release(
        api,
        tag,
        sha,
        root,
        publish=mode == "publish",
        output=output,
        preview_ci_url=selected.get("ci_url"),
    )


def write_summary(result, summary):
    metadata = json.dumps({k: v for k, v in result.items() if k != "release_body"}, indent=2)
    with open(summary, "a", encoding="utf-8") as stream:
        stream.write(f"## Skills release plan\n\n```json\n{metadata}\n```\n")
        if "release_body" in result:
            stream.write("\n## Release body preview\n\n" + result["release_body"])
            if not result["published"]:
                stream.write(
                    "\nCandidate SHA and CI link will be replaced by the final main snapshot.\n"
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["preview", "publish"], required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        token = os.environ.get("GH_TOKEN")
        if not token:
            raise ReleaseError("GH_TOKEN is required.")
        result = execute(
            GitHub(os.environ.get("GITHUB_REPOSITORY", ""), token),
            Path(__file__).resolve().parents[2],
            os.environ,
            event,
            args.mode,
            args.output,
        )
        print(json.dumps(result, indent=2))
        if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
            write_summary(result, summary)
    except (ReleaseError, PackageError, OSError, ValueError, KeyError) as error:
        print(f"Release plan stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
