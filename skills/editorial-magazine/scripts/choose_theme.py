#!/usr/bin/env python3
"""Choose a content-family accent once; persist the returned seed and CSS colors."""

import argparse
import json
import random
import secrets

PALETTES = {
    "general": ["#762437", "#284D66", "#435947", "#624064"],
    "technology": ["#254D72", "#404B81", "#246062"],
    "nature": ["#315D45", "#56623C", "#286265"],
    "culture": ["#792A40", "#684379", "#82512E"],
    "lifestyle": ["#8B463A", "#596039", "#80455E"],
}

# Matched paper, ink and reversed text colors for the editorial collage series.
EDITORIAL_PALETTES = {
    "oxblood": ("#870D10", "#F7E6CD", "#321D16", "#FFF0D7"),
    "forest": ("#234C3C", "#F1EBDD", "#24362C", "#FFF7E8"),
    "navy": ("#243E5C", "#F0EEE5", "#27313B", "#FFF8ED"),
    "plum": ("#573653", "#F3E9E5", "#382D35", "#FFF9F0"),
    "ochre": ("#70431D", "#F5E8CF", "#382C1F", "#FFF7E7"),
    "teal": ("#235454", "#EBF1E9", "#253936", "#FAF9EC"),
}
EDITORIAL_FAMILIES = {
    "general": list(EDITORIAL_PALETTES),
    "technology": ["navy", "teal", "plum"],
    "nature": ["forest", "teal", "ochre"],
    "culture": ["oxblood", "plum", "ochre"],
    "lifestyle": ["forest", "plum", "oxblood"],
}


# Quiet neutral backgrounds: independent of the actual clothing colors.
OUTFIT_PAPERS = {
    "ivory": "#F5F2EB",
    "oat": "#EBE5D9",
    "stone": "#ECEBE7",
    "linen": "#EEE8DF",
    "chalk": "#F4F4F0",
    "greige": "#E8E5DF",
}


def contrast(a, b):
    def light(value):
        rgb = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return sum(x * y for x, y in zip(linear, (0.2126, 0.7152, 0.0722)))

    x, y = sorted((light(a), light(b)))
    return (y + 0.05) / (x + 0.05)


def choose(family, seed=None, style="news"):
    if seed is None:
        seed = secrets.randbits(32)
    if style == "outfits":
        rng = random.Random(seed)
        name = rng.choice(list(OUTFIT_PAPERS))
        pattern = rng.choice(["plain", "grid"])
        accent = "#514D45"
        result = dict(
            family=family,
            seed=seed,
            style=style,
            palette=name,
            accent=accent,
            paper=OUTFIT_PAPERS[name],
            ink="#2C2D29",
            onAccent="#FFFFFF",
            pattern=pattern,
            backgroundImage=(
                "none"
                if pattern == "plain"
                else "linear-gradient(#514D450A 1px, transparent 1px), "
                "linear-gradient(90deg, #514D450A 1px, transparent 1px)"
            ),
            backgroundSize="44px 44px",
            outline="#FFFCF5",
            panel="transparent",
            rule="#514D4530",
        )
    elif style == "editorial":
        name = random.Random(seed).choice(EDITORIAL_FAMILIES[family])
        accent, paper, ink, on_accent = EDITORIAL_PALETTES[name]
        result = dict(
            family=family,
            seed=seed,
            style=style,
            palette=name,
            accent=accent,
            paper=paper,
            ink=ink,
            onAccent=on_accent,
        )
    elif style == "news":
        accent = random.Random(seed).choice(PALETTES[family])
        result = dict(
            family=family,
            seed=seed,
            accent=accent,
            paper="#FAF8F2",
            ink="#252823",
            onAccent="#FFFFFF",
        )
    else:
        raise ValueError("Unknown palette style: " + style)
    ratios = {
        "accentOnPaper": contrast(accent, result["paper"]),
        "whiteOnAccent": contrast(result["onAccent"], accent),
        "inkOnPaper": contrast(result["ink"], result["paper"]),
    }
    if min(ratios.values()) < 4.5:
        raise ValueError("Palette has insufficient text contrast")
    result["contrast"] = {k: round(v, 2) for k, v in ratios.items()}
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--family", choices=PALETTES, default="general")
    p.add_argument("--seed", type=int)
    p.add_argument("--style", choices=["news", "editorial", "outfits"], default="news")
    a = p.parse_args()
    print(json.dumps(choose(a.family, a.seed, a.style), ensure_ascii=False, indent=2))
