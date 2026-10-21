"""Random choice, user overrides and durable retry behavior across biography layouts."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from select_template import TEMPLATES, select_template

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/life-chronicle/scripts"


class SelectionChecks(unittest.TestCase):
    def test_random_pool_respects_capacity_and_excludes_storyline(self):
        for count in range(2, 9):
            expected = list(TEMPLATES) if count >= 4 else ["photo-wall-timeline", "photo-ring"]
            for picked in expected:
                with patch("select_template.secrets.choice", return_value=picked) as draw:
                    plan = select_template(count)
                draw.assert_called_once_with(expected)
                self.assertEqual(plan["template"], picked)
                self.assertEqual(plan["mode"], "random")

    def test_explicit_template_does_not_draw(self):
        for name in (*TEMPLATES, "storyline"):
            with patch(
                "select_template.secrets.choice", side_effect=AssertionError("unexpected draw")
            ):
                self.assertEqual(select_template(6, name)["template"], name)
        with self.assertRaisesRegex(ValueError, "4..8"):
            select_template(3, "center-grid")

    def test_invalid_count_or_template_is_not_silently_replaced(self):
        for count in (0, 1, 9):
            with self.assertRaises(ValueError):
                select_template(count)
        with self.assertRaises(ValueError):
            select_template(6, "favourite")

    def test_cli_saves_choice_even_when_content_needs_repair_and_reuses_it(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            brief = {
                "title": "测试",
                "subtitle": "测试",
                "layout": "portrait",
                "sources": [{"type": "test"}],
                "events": [{"order": n} for n in range(4)],
            }
            source = base / "brief.json"
            source.write_text(json.dumps(brief))
            command = [
                sys.executable,
                str(SCRIPTS / "build.py"),
                "--brief",
                str(source),
                "--output",
                str(base / "output"),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)  # Missing cutout, not a successful poster.
            path = base / "output/template-selection.json"
            first = json.loads(path.read_text())
            self.assertIn(first["template"], TEMPLATES)
            subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(json.loads(path.read_text()), first)
            brief["template"] = next(t for t in TEMPLATES if t != first["template"])
            source.write_text(json.dumps(brief))
            subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(json.loads(path.read_text())["template"], brief["template"])

    def test_planning_cli_will_not_reroll_existing_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "template-selection.json"
            command = [
                sys.executable,
                str(SCRIPTS / "select_template.py"),
                "--event-count",
                "6",
                "--output",
                str(path),
            ]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            first = path.read_text()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(first, path.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
