"""Build self-contained Skill ZIPs and a manifest from an immutable Git snapshot."""

import argparse
import hashlib
import json
import re
import stat
import subprocess
import zipfile
from pathlib import Path

ALGORITHM = "visactor-skill-content-v1"
MANIFEST = "skills-manifest.json"
TAG_PATTERN = re.compile(r"skills-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", re.ASCII)
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.ASCII)


class PackageError(ValueError):
    pass


def git(root, *args):
    try:
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        raise PackageError(f"Git snapshot operation failed: {args[0]}") from error


def digest(data):
    return hashlib.sha256(data).hexdigest()


def content_digest(files):
    """UTF-8 prefix plus sorted mode<TAB>sha256<TAB>path<LF> records."""
    records = [ALGORITHM + "\n"]
    records.extend(
        f"{file['mode']}\t{file['sha256']}\t{file['path']}\n"
        for file in sorted(files, key=lambda file: file["path"].encode("utf-8"))
    )
    return digest("".join(records).encode("utf-8"))


def validate_path(path):
    # Paths are preserved, not normalized; reject ambiguous/unsafe extraction names.
    if (
        not path
        or "\\" in path
        or any(ord(char) < 32 or ord(char) == 127 for char in path)
        or any(part in {"", ".", ".."} or ":" in part for part in path.split("/"))
    ):
        raise PackageError(f"Unsafe package path: {path!r}")


def snapshot(root, commit):
    sha = (
        git(root, "rev-parse", "--verify", "--end-of-options", f"{commit}^{{commit}}")
        .decode()
        .strip()
    )
    groups = {}
    for entry in git(root, "ls-tree", "-rz", sha, "--", "skills/").split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError as error:
            raise PackageError("Skill paths must be UTF-8") from error
        mode, kind, oid = metadata.decode().split()
        parts = path.split("/", 2)
        if len(parts) != 3 or not NAME_PATTERN.fullmatch(parts[1]):
            raise PackageError(f"Expected skills/<lowercase-hyphenated-name>/<file>: {path}")
        name, relative = parts[1:]
        validate_path(relative)
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise PackageError(f"Only regular files are supported (no symlinks/submodules): {path}")
        data = git(root, "cat-file", "blob", oid)
        groups.setdefault(name, []).append((relative, mode, data))
    if not groups:
        raise PackageError("No Skills found in the Git snapshot")
    for name, files in groups.items():
        paths = [path for path, _, _ in files]
        if len(set(path.casefold() for path in paths)) != len(paths):
            raise PackageError(f"Case-colliding paths in Skill {name}")
        skill = next((data for path, _, data in files if path == "SKILL.md"), None)
        if skill is None:
            raise PackageError(f"Missing SKILL.md in skills/{name}")
        text = skill.decode("utf-8")
        lines = text.splitlines()
        if not lines or lines[0] != "---" or "---" not in lines[1:]:
            raise PackageError(f"Missing YAML frontmatter in skills/{name}/SKILL.md")
        frontmatter = lines[1 : lines.index("---", 1)]
        names = [line for line in frontmatter if line.startswith("name:")]
        # Restrict the release identity to a plain or quoted slug; no YAML aliases/expressions.
        if len(names) != 1 or names[0].removeprefix("name:").strip() not in {
            name,
            f'"{name}"',
            f"'{name}'",
        }:
            raise PackageError(f"Frontmatter name must match directory: skills/{name}")
    return sha, groups


def build_artifacts(root, commit, tag, output, repository="VisActor/skills"):
    if not TAG_PATTERN.fullmatch(tag):
        raise PackageError("Expected stable tag skills-vMAJOR.MINOR.PATCH")
    sha, groups = snapshot(root, commit)
    # A fresh directory prevents stale ZIPs from another snapshot being published.
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": 1,
        "repository": repository,
        "tag": tag,
        "commit": sha,
        "fingerprint_algorithm": ALGORITHM,
        "skills": [],
    }
    for name in sorted(groups):
        files = []
        asset = output / f"{name}.zip"
        with zipfile.ZipFile(asset, "w", compression=zipfile.ZIP_STORED) as archive:
            for path, mode, data in sorted(groups[name], key=lambda item: item[0].encode("utf-8")):
                info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                permissions = 0o755 if mode == "100755" else 0o644
                info.external_attr = (stat.S_IFREG | permissions) << 16
                archive.writestr(info, data)
                files.append(
                    {"path": path, "mode": mode, "size": len(data), "sha256": digest(data)}
                )
        manifest["skills"].append(
            {
                "name": name,
                "path": f"skills/{name}",
                "content_sha256": content_digest(files),
                "files": files,
                "package": {
                    "asset": asset.name,
                    "size": asset.stat().st_size,
                    "sha256": digest(asset.read_bytes()),
                },
            }
        )
    (output / MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    verify_artifacts(output, manifest)
    return manifest


def verify_artifacts(output, manifest):
    """Check built ZIP bytes, file inventory, modes and logical content fingerprints."""
    expected_assets = {MANIFEST} | {skill["package"]["asset"] for skill in manifest["skills"]}
    if {file.name for file in output.iterdir()} != expected_assets:
        raise PackageError("Unexpected or missing release artifact")
    try:
        saved_manifest = json.loads((output / MANIFEST).read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PackageError("Invalid saved release manifest") from error
    if saved_manifest != manifest:
        raise PackageError("Saved release manifest differs from the verified inventory")
    for skill in manifest["skills"]:
        package = skill["package"]
        raw = (output / package["asset"]).read_bytes()
        if len(raw) != package["size"] or digest(raw) != package["sha256"]:
            raise PackageError(f"ZIP checksum mismatch: {skill['name']}")
        actual = []
        with zipfile.ZipFile(output / package["asset"]) as archive:
            for entry in archive.infolist():
                data = archive.read(entry)
                actual.append(
                    {
                        "path": entry.filename,
                        "mode": f"{entry.external_attr >> 16:o}",
                        "size": len(data),
                        "sha256": digest(data),
                    }
                )
        if actual != skill["files"] or content_digest(actual) != skill["content_sha256"]:
            raise PackageError(f"ZIP inventory/fingerprint mismatch: {skill['name']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = build_artifacts(
            Path(__file__).resolve().parents[2], args.commit, args.tag, args.output
        )
    except (PackageError, OSError, UnicodeError) as error:
        parser.exit(1, f"Packaging failed: {error}\n")
    print(
        json.dumps(
            {
                "manifest": str(args.output / MANIFEST),
                "commit": manifest["commit"],
                "skills": [s["name"] for s in manifest["skills"]],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
