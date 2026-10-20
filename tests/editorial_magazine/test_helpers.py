"""Behavior checks for reproducible themes and alpha/color inspection."""

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

ROOT = Path(__file__).resolve().parents[2] / "skills/editorial-magazine/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


t = load("choose_theme")
c = load("inspect_cutout")


def test_themes_and_cutout_inspection():
    for family, colors in t.PALETTES.items():
        seen = set()
        for seed in range(100):
            result = t.choose(family, seed)
            assert result == t.choose(family, seed)
            assert result["accent"] in colors
            assert min(result["contrast"].values()) >= 4.5
            seen.add(result["accent"])
        assert seen == set(colors)
    for family, names in t.EDITORIAL_FAMILIES.items():
        seen = set()
        for seed in range(100):
            result = t.choose(family, seed, "editorial")
            assert result == t.choose(family, seed, "editorial")
            assert result["palette"] in names
            assert min(result["contrast"].values()) >= 4.5
            seen.add(result["palette"])
        assert seen == set(names)
    seen = set()
    patterns = set()
    for seed in range(100):
        result = t.choose("general", seed, "outfits")
        assert result == t.choose("general", seed, "outfits")
        assert result["paper"] in t.OUTFIT_PAPERS.values()
        assert min(result["contrast"].values()) >= 4.5
        assert result["pattern"] in ["plain", "grid"]
        assert (result["backgroundImage"] == "none") == (result["pattern"] == "plain")
        assert t.choose("nature", seed, "outfits")["paper"] == result["paper"]
        seen.add(result["palette"])
        patterns.add(result["pattern"])
    assert seen == set(t.OUTFIT_PAPERS) and patterns == {"plain", "grid"}
    try:
        t.choose("general", 0, "unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown style accepted")
    with TemporaryDirectory() as temp:
        p = Path(temp)
        # Synthetic test fixture, not a processed user photograph.
        fixture = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
        for x in range(3, 9):
            for y in range(3, 9):
                fixture.putpixel((x, y), (32, 128, 64, 255))
        fixture.save(p / "valid.png")
        r = c.inspect(p / "valid.png", (3, 3, 9, 9))
        assert r["transparentFraction"] == 0.75 and r["candidateColors"] == ["#208040"]
        for mode, color, name in [
            ("RGB", (255, 255, 255), "opaque"),
            ("RGBA", (0, 0, 0, 0), "empty"),
        ]:
            Image.new(mode, (12, 12), color).save(p / f"{name}.png")
            try:
                c.inspect(p / f"{name}.png")
            except ValueError:
                pass
            else:
                raise AssertionError(name)
        for region in [(0, 0, 3, 3), (0, 0, 20, 20), (9, 9, 3, 3)]:
            try:
                c.inspect(p / "valid.png", region)
            except ValueError:
                pass
            else:
                raise AssertionError(region)
