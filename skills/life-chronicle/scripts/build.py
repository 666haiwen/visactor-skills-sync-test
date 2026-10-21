#!/usr/bin/env python3
"""人物志：choose a template independently of canvas orientation."""

from collage import build_photo_wall
from grid import build_center_grid
from page import copy, image_asset, page, text, write_pages
from ring import build_photo_ring
from select_template import select_template
from typography import apply_typography


def build(brief, base):
    title = copy(brief.get("title"), "title", 32)
    layout = brief.get("layout", "landscape")
    if layout not in {"landscape", "portrait"}:
        raise ValueError("layout must be landscape or portrait")
    template = select_template(len(brief.get("events", [])), brief.get("template", "random"))[
        "template"
    ]
    builders = {
        "photo-wall-timeline": build_photo_wall,
        "center-grid": build_center_grid,
        "photo-ring": build_photo_ring,
    }
    if template not in {*builders, "storyline"}:
        raise ValueError(
            "template must be photo-wall-timeline, center-grid, photo-ring or storyline"
        )
    events = brief.get("events", [])
    if not 2 <= len(events) <= 8:
        raise ValueError(
            "Use 2..8 selected life milestones per page; split longer biographies into chapters"
        )
    ordered = sorted(events, key=lambda e: e["order"])
    if len({e["order"] for e in ordered}) != len(ordered):
        raise ValueError("events.order must be unique; preserve uncertain dates in dateLabel")
    if template != "storyline":
        return [apply_typography(builders[template](brief, base, ordered))]
    blocks = [
        {
            "id": f"event-{i}",
            "marker": copy(e.get("dateLabel"), "dateLabel", 16),
            # Native event headings do not wrap to the body column width.
            # Keep the heading short; put award names/details in body.
            "title": copy(e.get("title"), "event.title", 7),
            "content": copy(e.get("body"), "event.body", 65),
            "image": image_asset(e["image"], base),
        }
        for i, e in enumerate(ordered)
    ]
    for block, event in zip(blocks, ordered):
        # Keep uncertain dates/ranges in full copy as well as a compact axis marker.
        block["content"] = f"{block['marker']} · {block['content']}"
        block["marker"] = copy(event.get("marker", str(event["order"])), "compact marker", 4)
        if event.get("subImage"):
            block["subImage"] = image_asset(event["subImage"], base)
    w, h = (1080, 1920) if layout == "portrait" else (1600, 1000)
    stage = {
        "type": "storyline",
        "id": "life-story",
        "title": title,
        "subtitle": copy(brief.get("subtitle"), "subtitle", 100),
        "layout": layout,
        "blocks": blocks,
        "storylineStyle": {"themeColor": brief.get("accent", "#735248")},
        "style": {"x": 24, "y": 20, "width": w - 48, "height": h - 86},
    }
    if brief.get("titleImage"):
        stage["titleImage"] = image_asset(brief["titleImage"], base)
    if brief.get("backgroundImage"):
        stage["backgroundImage"] = image_asset(brief["backgroundImage"], base)
    nodes = [
        stage,
        text("source", copy(brief.get("sourceNote"), "sourceNote", 95), 32, h - 54, w - 64, 48, 15),
    ]
    return [page(title, w, h, nodes)]


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        source = Path(args.brief).resolve()
        brief = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(brief.get("sources"), list) or not brief["sources"]:
            raise ValueError(
                "sources must record actual research, user input, or an explicit demonstration source"
            )
        output = Path(args.output)
        plan_path = output / "template-selection.json"
        requested = brief.get("template", "random")
        if requested == "random" and plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if plan["template"] not in {"photo-wall-timeline", "center-grid", "photo-ring"}:
                raise ValueError(
                    "Saved random selection must be one of the three biography templates"
                )
            select_template(len(brief.get("events", [])), plan["template"])
        else:
            plan = select_template(len(brief.get("events", [])), requested)
        output.mkdir(parents=True, exist_ok=True)
        # Persist before layout validation so a copy/image repair never rerolls.
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        pages = build({**brief, "template": plan["template"]}, source.parent)
        write_pages(pages, output, brief["sources"])
        print(json.dumps(plan, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
