import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def packager():
    spec = importlib.util.spec_from_file_location(
        "package_skills", ROOT / ".github/scripts/package_skills.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root, *args):
    return (
        subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)
        .decode()
        .strip()
    )


def commit(root):
    git(root, "add", "--all")
    git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "fixture",
        "--no-gpg-sign",
    )
    return git(root, "rev-parse", "HEAD")


def write(root, path, data):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data, encoding="utf-8")
    return target


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "core.hooksPath", "/dev/null")
    write(root, ".gitignore", "*.pyc\n.cache/\n")
    write(root, "skills/alpha/SKILL.md", "---\nname: alpha\ndescription: example\n---\n")
    write(root, "skills/alpha/scripts/run.sh", "echo test\n")
    write(root, "skills/alpha/references/说明.md", "原始内容\r\n")
    write(root, "skills/beta/SKILL.md", "---\nname: 'beta'\n---\n")
    write(root, "README.md", "documentation")
    commit(root)
    return root


def build(packager, repo, tmp_path, name="output", tag="skills-v1.0.0", sha="HEAD"):
    output = tmp_path / name
    return packager.build_artifacts(repo, sha, tag, output), output


def test_committed_blobs_define_contents_not_dirty_or_ignored_files(packager, repo, tmp_path):
    original = (repo / "skills/alpha/SKILL.md").read_bytes()
    write(repo, "skills/alpha/SKILL.md", "dirty content")
    write(repo, "skills/alpha/untracked.txt", "not committed")
    write(repo, "skills/alpha/cache.pyc", "ignored")
    manifest, output = build(packager, repo, tmp_path)
    with zipfile.ZipFile(output / "alpha.zip") as archive:
        assert set(archive.namelist()) == {"SKILL.md", "scripts/run.sh", "references/说明.md"}
        assert archive.read("SKILL.md") == original
    assert manifest["commit"] == git(repo, "rev-parse", "HEAD")


def test_zip_bytes_and_fingerprint_do_not_change_with_tag_time_or_directory(
    packager, repo, tmp_path
):
    first, output1 = build(packager, repo, tmp_path, "first")
    for file in repo.rglob("*.md"):
        os.utime(file, (1000000000, 1000000000))
    second, output2 = build(packager, repo, tmp_path, "second", tag="skills-v1.1.0")
    assert first["skills"] == second["skills"]
    assert (output1 / "alpha.zip").read_bytes() == (output2 / "alpha.zip").read_bytes()


def test_documentation_change_does_not_change_skill_fingerprints(packager, repo, tmp_path):
    first, _ = build(packager, repo, tmp_path, "first")
    write(repo, "README.md", "new repository documentation")
    write(repo, "cases/alpha/prompt.md", "task input")
    commit(repo)
    second, _ = build(packager, repo, tmp_path, "second")
    assert first["commit"] != second["commit"]
    assert first["skills"] == second["skills"]


@pytest.mark.parametrize("change", ["bytes", "mode", "path", "delete", "add"])
def test_each_runtime_change_affects_only_the_owned_skill(packager, repo, tmp_path, change):
    first, _ = build(packager, repo, tmp_path, "first")
    script = repo / "skills/alpha/scripts/run.sh"
    if change == "bytes":
        script.write_text("echo changed\n")
    elif change == "mode":
        git(repo, "update-index", "--chmod=+x", "skills/alpha/scripts/run.sh")
        script.chmod(0o755)
    elif change == "path":
        script.rename(script.with_name("other.sh"))
    elif change == "delete":
        script.unlink()
    else:
        write(repo, "skills/alpha/templates/page.html", "<main>template</main>")
    commit(repo)
    second, _ = build(packager, repo, tmp_path, "second")
    assert first["skills"][0]["content_sha256"] != second["skills"][0]["content_sha256"]
    assert first["skills"][1] == second["skills"][1]


def test_name_changes_and_deletion_are_visible_in_complete_inventory(packager, repo, tmp_path):
    shutil.rmtree(repo / "skills/beta")
    (repo / "skills/alpha").rename(repo / "skills/gamma")
    write(repo, "skills/gamma/SKILL.md", "---\nname: gamma\n---\n")
    commit(repo)
    manifest, _ = build(packager, repo, tmp_path)
    assert [s["name"] for s in manifest["skills"]] == ["gamma"]


@pytest.mark.parametrize("defect", ["name", "missing", "symlink", "submodule", "unsafe", "shared"])
def test_ambiguous_or_nonportable_layouts_fail(packager, repo, tmp_path, defect):
    if defect == "name":
        write(repo, "skills/alpha/SKILL.md", "---\nname: wrong\n---\n")
    elif defect == "missing":
        (repo / "skills/alpha/SKILL.md").unlink()
    elif defect == "symlink":
        (repo / "skills/alpha/external").symlink_to("../../README.md")
    elif defect == "unsafe":
        write(repo, "skills/alpha/tab\tname.txt", "data")
    elif defect == "shared":
        write(repo, "skills/shared.json", "{}")
    else:
        git(
            repo,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{git(repo, 'rev-parse', 'HEAD')},skills/alpha/submodule",
        )
        git(
            repo,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "gitlink",
            "--no-gpg-sign",
        )
    if defect != "submodule":
        commit(repo)
    with pytest.raises(packager.PackageError):
        build(packager, repo, tmp_path)


def test_fixed_fingerprint_vector_documents_cross_language_encoding(packager):
    files = [
        {"path": "z.txt", "mode": "100755", "sha256": "b" * 64},
        {"path": "a.txt", "mode": "100644", "sha256": "a" * 64},
    ]
    expected_bytes = (
        "visactor-skill-content-v1\n100644\t"
        + "a" * 64
        + "\ta.txt\n100755\t"
        + "b" * 64
        + "\tz.txt\n"
    ).encode()
    assert packager.content_digest(files) == hashlib.sha256(expected_bytes).hexdigest()


def test_existing_output_cannot_mix_in_stale_packages(packager, repo, tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "old.zip").write_bytes(b"old")
    with pytest.raises(FileExistsError):
        build(packager, repo, tmp_path)


def test_transport_corruption_is_detected(packager, repo, tmp_path):
    manifest, output = build(packager, repo, tmp_path)
    (output / "alpha.zip").write_bytes(b"corrupt")
    with pytest.raises(packager.PackageError, match="checksum"):
        packager.verify_artifacts(output, manifest)


def test_manifest_matches_the_written_inventory(packager, repo, tmp_path):
    manifest, output = build(packager, repo, tmp_path)
    assert json.loads((output / "skills-manifest.json").read_text()) == manifest


@pytest.mark.parametrize("content", ["{}", "invalid json"])
def test_changed_manifest_is_rejected(packager, repo, tmp_path, content):
    manifest, output = build(packager, repo, tmp_path)
    (output / "skills-manifest.json").write_text(content)
    with pytest.raises(packager.PackageError, match="manifest"):
        packager.verify_artifacts(output, manifest)
