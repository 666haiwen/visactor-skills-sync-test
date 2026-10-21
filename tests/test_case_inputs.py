"""Protect fixed input bytes and inventory, without testing prompt wording."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = sorted((ROOT / "cases").glob("*/*/fixtures.json"))


@pytest.mark.parametrize("manifest", FIXTURES, ids=lambda p: str(p.parent.relative_to(ROOT)))
def test_case_inputs_match_declared_files_and_hashes(manifest):
    folder = manifest.parent
    fixtures = json.loads(manifest.read_text())
    assert (ROOT / "skills" / folder.parent.name / "SKILL.md").is_file()
    assert set(fixtures) == {p.name for p in (folder / "inputs").iterdir()}
    for name, record in fixtures.items():
        assert (
            hashlib.sha256((folder / "inputs" / name).read_bytes()).hexdigest() == record["sha256"]
        )
