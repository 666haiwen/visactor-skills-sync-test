#!/usr/bin/env python3
"""Draw a biography layout before preparing template-specific copy and pictures."""

import argparse
import json
import secrets
from pathlib import Path

TEMPLATES = ("photo-wall-timeline", "center-grid", "photo-ring")


def select_template(event_count, requested="random"):
    if not 2 <= event_count <= 8:
        raise ValueError(
            "Use 2..8 selected life milestones per page; split longer biographies into chapters"
        )
    candidates = [name for name in TEMPLATES if name != "center-grid" or event_count >= 4]
    if requested not in (*TEMPLATES, "storyline", "random"):
        raise ValueError(
            "template must be random, photo-wall-timeline, center-grid, photo-ring or storyline"
        )
    if requested == "center-grid" and event_count < 4:
        raise ValueError("center-grid needs 4..8 events")
    return {
        "template": secrets.choice(candidates) if requested == "random" else requested,
        "mode": "random" if requested == "random" else "explicit",
        "candidates": candidates,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-count", type=int, required=True)
    parser.add_argument("--template", default="random")
    parser.add_argument(
        "--output",
        required=True,
        help="Save once per new generation; reuse the chosen template for revisions",
    )
    args = parser.parse_args()
    try:
        result = select_template(args.event_count, args.template)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        # A saved plan belongs to one generation, not to each render attempt.
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError) as error:
        parser.error(str(error))
