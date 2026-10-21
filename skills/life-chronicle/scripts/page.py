"""Small VInfo page primitives, vendored into each independently shipped skill."""

import base64
import io
import json
import math
from pathlib import Path


def copy(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field}: provide 1..{limit} characters; split or summarize longer copy")
    return value.strip()


def image_asset(item, base, grayscale=False):
    """Materialized local images only: portable HTML, no hotlinks/CORS/expired URLs."""
    from PIL import Image, ImageOps

    src = Path(copy(item.get("src"), "image.src (local file)", 4096))
    path = src if src.is_absolute() else base / src
    with Image.open(path) as source:
        img = ImageOps.exif_transpose(source)
        img.load()
        if grayscale:
            img = ImageOps.grayscale(img).convert("RGB")
        else:
            img = img.convert(
                "RGBA" if "A" in img.getbands() or "transparency" in img.info else "RGB"
            )
        img.thumbnail((2400, 2400))
        out = io.BytesIO()
        img.save(out, format="PNG")
    return {
        "src": "data:image/png;base64," + base64.b64encode(out.getvalue()).decode(),
        "alt": copy(item.get("alt"), "image.alt", 180),
    }


def text(id_, content, x, y, w, h, size=24, weight=400, color="#202624", serif=False):
    content = copy(content, id_, 2000)
    # Conservative CJK-width budget. Do not silently shrink/drop editorial copy.
    lines = sum(
        max(1, math.ceil(len(line) * size / max(size, w - size))) for line in content.splitlines()
    )
    if lines * math.ceil(size * 1.45) > h:
        raise ValueError(f"{id_}: copy exceeds the frame; shorten it or paginate")
    return {
        "type": "text",
        "id": id_,
        "text": content,
        "textStyle": {
            "fontSize": size,
            "lineHeight": math.ceil(size * 1.45),
            "fontWeight": weight,
            "fill": color,
            "fontFamily": '"Noto Serif CJK SC", "Songti SC", serif'
            if serif
            else '"Noto Sans CJK SC", "PingFang SC", sans-serif',
        },
        "style": {"x": x, "y": y, "width": w, "height": h},
    }


def picture(id_, asset, x, y, w, h, fit="cover"):
    return {
        "type": "image",
        "id": id_,
        **asset,
        "fit": fit,
        "style": {"x": x, "y": y, "width": w, "height": h},
    }


def rule(id_, x, y, w):
    return {
        "type": "divider",
        "id": id_,
        "direction": "horizontal",
        "style": {"x": x, "y": y, "width": w, "height": 2},
    }


def page(title, w, h, nodes, background="#FBFAF6", accent="#275B49"):
    return {
        "type": "infographic-page",
        "version": 3,
        "canvas": {
            "size": "custom",
            "width": w,
            "height": h,
            "fitContent": False,
            "background": background,
        },
        "meta": {"name": title},
        "appearance": {
            "mode": "light",
            "palette": {
                "canvas": background,
                "text": "#202624",
                "mutedText": "#646864",
                "accent": accent,
                "divider": "#BCBDB7",
            },
            "typography": {"fontFamily": '"Noto Sans CJK SC", "PingFang SC", sans-serif'},
        },
        "body": {
            "type": "container",
            "id": "page",
            "layout": "absolute",
            "style": {"width": w, "height": h},
            "children": nodes,
        },
    }


def write_pages(pages, output, provenance):
    output.mkdir(parents=True, exist_ok=True)
    for index, schema in enumerate(pages, 1):
        (output / f"page-{index:02}.schema.json").write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    (output / "sources.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def run_builder(builder):
    import argparse

    parser = argparse.ArgumentParser(
        description="Build scene-specific VInfo v3 page schemas from an editorial brief"
    )
    parser.add_argument("--brief", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        brief_path = Path(args.brief).resolve()
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        if not isinstance(brief.get("sources"), list) or not brief["sources"]:
            raise ValueError(
                "sources must record actual research, user input, or an explicit demonstration source"
            )
        pages = builder(brief, brief_path.parent)
        write_pages(pages, Path(args.output), brief.get("sources", []))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
