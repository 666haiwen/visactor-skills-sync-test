import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_evaluation_lockfile_uses_public_npm_registry():
    lock = json.loads((ROOT / "evals/package-lock.json").read_text())
    resolved = [
        package["resolved"] for package in lock["packages"].values() if "resolved" in package
    ]
    assert resolved and all(urlsplit(url).hostname == "registry.npmjs.org" for url in resolved)


@pytest.mark.parametrize("skill", ["vchart-skill", "vtable-skill"])
def test_copied_skill_generates_without_source_checkout(tmp_path, skill):
    installed = tmp_path / "installed skill"
    shutil.copytree(ROOT / "skills" / skill, installed)
    cwd = tmp_path / "user project"
    cwd.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts/generate_demo_html.py"),
            "--output-dir",
            "result files",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    html = cwd / "result files/demo.html"
    assert html.exists(), result.stderr
    assert str(ROOT) not in html.read_text()


def test_copied_editorial_skill_selects_theme_without_source_checkout(tmp_path):
    installed = tmp_path / "editorial skill"
    shutil.copytree(ROOT / "skills/editorial-magazine", installed)
    command = [sys.executable, str(installed / "scripts/choose_theme.py"), "--seed", "42"]
    first = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=True)
    second = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(first.stdout) == json.loads(second.stdout)
    assert min(json.loads(first.stdout)["contrast"].values()) >= 4.5


def test_copied_life_chronicle_builds_schema_and_html_without_source_checkout(tmp_path):
    from PIL import Image, ImageDraw

    installed = tmp_path / "biography skill"
    shutil.copytree(ROOT / "skills/life-chronicle", installed)
    project = tmp_path / "user project"
    project.mkdir()
    # Synthetic geometry checks packaging only; it is not a real person or source photo.
    Image.new("RGB", (600, 400), "#448899").save(project / "photo.png")
    portrait = Image.new("RGBA", (240, 400))
    ImageDraw.Draw(portrait).ellipse((45, 30, 195, 380), fill="#CA6030")
    portrait.save(project / "cutout.png")
    brief = {
        "title": "Synthetic biography",
        "subtitle": "Packaging test",
        "sourceNote": "Synthetic packaging fixture",
        "layout": "landscape",
        "template": "photo-wall-timeline",
        "portraitCutout": {"src": "cutout.png", "alt": "Synthetic cutout"},
        "sources": [{"type": "fixture"}],
        "events": [
            {
                "order": i,
                "dateLabel": str(1900 + i),
                "title": "Stage",
                "body": "Synthetic event.",
                "image": {"src": "photo.png", "alt": "Fixture"},
            }
            for i in range(1, 5)
        ],
    }
    (project / "brief.json").write_text(json.dumps(brief))
    subprocess.run(
        [
            sys.executable,
            str(installed / "scripts/build.py"),
            "--brief",
            "brief.json",
            "--output",
            "result files",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(installed / "scripts/render.py"),
            "--schema",
            "result files/page-01.schema.json",
            "--html",
            "result files/page-01.html",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    )
    html = (project / "result files/page-01.html").read_text()
    assert "__SCHEMA__" not in html and "__RENDER_SETUP__" not in html
    assert "data:image/png;base64," in html
    assert str(ROOT) not in html
    plan = json.loads((project / "result files/template-selection.json").read_text())
    assert plan["template"] == brief["template"]
