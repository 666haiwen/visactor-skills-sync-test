"""Biography photo wall: title 1/8, photos 4/8, editable timeline 3/8."""

import base64
import io
import math
from pathlib import Path

from page import copy, page, picture, text
from PIL import Image, ImageFilter, ImageOps


def group(id_, x, y, width, height, children, **style):
    return {
        "type": "container",
        "id": id_,
        "layout": "absolute",
        "style": {"x": x, "y": y, "width": width, "height": height, **style},
        "children": children,
    }


def local_image(item, base):
    path = Path(copy(item.get("src"), "image.src (local file)", 4096))
    with Image.open(path if path.is_absolute() else base / path) as source:
        return ImageOps.exif_transpose(source).convert("RGBA")


def validate_cutout(image):
    histogram = image.getchannel("A").histogram()
    pixels = image.width * image.height
    if sum(histogram[:16]) / pixels < 0.03 or sum(histogram[128:]) / pixels < 0.01:
        raise ValueError(
            "portraitCutout must contain a visible person and a transparent background; run cutout.py or MediaKit first"
        )


def sticker_outline(image, bounds, width):
    """White silhouette stroke measured in final page pixels, with alpha outside."""
    if (
        not isinstance(width, (int, float))
        or isinstance(width, bool)
        or not math.isfinite(width)
        or not 0 <= width <= 16
    ):
        raise ValueError("portraitCutout.outlineWidth must be 0..16 page pixels")
    if width == 0:
        return image
    supersample = 3
    radius = round(width * supersample)
    padding = radius + supersample * 2
    scale = min(
        (bounds[0] * supersample - 2 * padding) / image.width,
        (bounds[1] * supersample - 2 * padding) / image.height,
    )
    subject = image.resize(
        (round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS
    )
    layer = Image.new("RGBA", (subject.width + 2 * padding, subject.height + 2 * padding))
    layer.paste(subject, (padding, padding))
    silhouette = layer.getchannel("A").point(lambda a: 255 if a >= 32 else 0)
    stroke = silhouette.filter(ImageFilter.MaxFilter(radius * 2 + 1)).filter(
        ImageFilter.GaussianBlur(0.6)
    )
    paper = Image.new("RGBA", layer.size, "white")
    paper.putalpha(stroke)
    paper.alpha_composite(layer)
    return paper.resize(
        (round(paper.width / supersample), round(paper.height / supersample)),
        Image.Resampling.LANCZOS,
    )


def asset(item, base, size=None, monochrome=True, cutout=False, bounds=None):
    image = local_image(item, base)
    if cutout:
        validate_cutout(image)
        bbox = image.getchannel("A").point(lambda a: 255 if a >= 16 else 0).getbbox()
        image = image.crop(bbox)
    if monochrome:
        alpha = image.getchannel("A")
        image = ImageOps.grayscale(image).convert("RGBA")
        image.putalpha(alpha)
    if cutout and bounds:
        image = sticker_outline(image, bounds, item.get("outlineWidth", 6))
    if size:
        position = item.get("cropPosition", [0.5, 0.5])
        if (
            not isinstance(position, (list, tuple))
            or len(position) != 2
            or any(
                not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1
                for v in position
            )
        ):
            raise ValueError("image.cropPosition must be two numbers in [0, 1]")
        fit = item.get("fit", "cover")
        if fit not in {"cover", "contain"}:
            raise ValueError("image.fit must be cover or contain")
        image = (
            ImageOps.fit(image, size, Image.Resampling.LANCZOS, centering=position)
            if fit == "cover"
            else ImageOps.pad(image, size, Image.Resampling.LANCZOS, color="#ECEBE7")
        )
    else:
        image.thumbnail((2400, 2400))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return {
        "src": "data:image/png;base64," + base64.b64encode(out.getvalue()).decode(),
        "alt": copy(item.get("alt"), "image.alt", 180),
    }, image.size


def wall_slots(count, width, height, aspects=None):
    """Two staggered photo banks; the central cutout overlaps their inner edges."""
    gap = 5
    bank = (width - gap) // 2
    slots = []
    offset = 0
    for x, n in [(0, (count + 1) // 2), (width - bank, count // 2)]:
        if n == 1:
            slots.append((x, 0, bank, height))
        elif n == 2:
            if aspects and all(a < 1 for a in aspects[offset : offset + n]):
                half = (bank - gap) // 2
                slots.extend([(x, 0, half, height), (x + half + gap, 0, bank - half - gap, height)])
            else:
                half = (height - gap) // 2
                slots.extend([(x, 0, bank, half), (x, half + gap, bank, height - half - gap)])
        else:
            # A large upper photo and two/three lower details form a photo wall,
            # not equal-sized cards. All inner boundaries stay behind the cutout.
            upper = round(height * 0.56)
            slots.append((x, 0, bank, upper))
            small = (bank - gap * (n - 2)) // (n - 1)
            for j in range(n - 1):
                sw = bank - j * (small + gap) if j == n - 2 else small
                slots.append((x + j * (small + gap), upper + gap, sw, height - upper - gap))
        offset += n
    return slots


def header_nodes(title, subtitle, width, height, ink, portrait=False):
    if not portrait:
        return [
            text("heading", title, 28, 24, round(width * 0.55), height - 47, 44, 700, ink),
            text(
                "summary",
                subtitle,
                round(width * 0.60625),
                26,
                round(width * 0.375),
                height - 43,
                18,
                color=ink,
            ),
        ]
    title_h = math.ceil(len(title) * 44 / (width - 100)) * 64
    summary_y = 24 + title_h + 16
    return [
        text("heading", title, 28, 24, width - 56, title_h, 44, 700, ink),
        text(
            "summary", subtitle, 28, summary_y, width - 56, height - summary_y - 16, 18, color=ink
        ),
    ]


def portrait_timeline(events, ranks, width, height, margin, accent, ink):
    """Two top-to-bottom tracks preserve legible copy on a narrow canvas."""
    nodes = []
    columns = 1 if len(events) <= 3 else 2
    rows = math.ceil(len(events) / columns)
    col_w = (width - 2 * margin) / columns
    step = (height - 92) / rows
    for c in range(columns):
        count = min(rows, len(events) - c * rows)
        nodes.append(
            group(
                f"time-axis-{c + 1}",
                margin + c * col_w + 14,
                35,
                2,
                max(2, step * (count - 1)),
                [],
                background="#BCBDB7",
            )
        )
    for i, event in enumerate(events):
        c, r = divmod(i, rows)
        x, y = margin + c * col_w, 20 + r * step
        tx, tw = x + 48, col_w - 72
        nodes.append(
            group(
                f"event-ref-{i + 1}",
                x,
                y,
                30,
                30,
                [
                    text(
                        f"event-number-{i + 1}",
                        ranks[event["order"]],
                        8,
                        3,
                        16,
                        26,
                        16,
                        700,
                        "#FFFFFF",
                    )
                ],
                background=accent,
            )
        )
        nodes.append(
            text(
                f"date-{i + 1}",
                copy(event.get("dateLabel"), "dateLabel", 16),
                tx,
                y,
                tw,
                30,
                18,
                700,
                ink,
            )
        )
        nodes.append(
            text(
                f"event-title-{i + 1}",
                copy(event.get("title"), "event.title", 10),
                tx,
                y + 34,
                tw,
                36,
                24,
                700,
                ink,
            )
        )
        nodes.append(
            text(
                f"event-body-{i + 1}",
                copy(event.get("body"), "event.body", 65),
                tx,
                y + 80,
                tw,
                step - 92,
                20,
                color=ink,
            )
        )
    return nodes


def build_photo_wall(brief, base, events):
    portrait = brief.get("layout", "landscape") == "portrait"
    width, height = (1080, 1920) if portrait else (1600, 1000)
    header_h, wall_h, timeline_h = height // 8, height // 2, height * 3 // 8
    margin, ink = 28, "#202020"
    accent = brief.get("accent", "#B46B79")
    title = copy(brief.get("title"), "title", 32)
    subtitle = copy(brief.get("subtitle"), "subtitle", 100)
    if not brief.get("portraitCutout"):
        raise ValueError(
            "photo-wall-timeline requires portraitCutout: a local transparent PNG of the subject"
        )
    if brief.get("titleImage") or brief.get("backgroundImage"):
        raise ValueError(
            "photo-wall-timeline uses portraitCutout and photoWall; titleImage/backgroundImage belong to template: storyline"
        )
    monochrome = brief.get("monochrome", True)
    photos = brief.get("photoWall")
    if photos is None:
        photos = [
            {
                "image": e["image"],
                "eventOrder": e["order"],
                **({"caption": e["imageCaption"]} if e.get("imageCaption") else {}),
            }
            for e in events
            if e.get("image")
        ]
    if not isinstance(photos, list) or not 2 <= len(photos) <= 8:
        raise ValueError("photoWall needs 2..8 verified photos; use 4..8 for a denser collage")
    if type(monochrome) is not bool:
        raise ValueError("monochrome must be true or false")
    ranks = {e["order"]: str(i + 1) for i, e in enumerate(events)}
    event_by_order = {e["order"]: e for e in events}
    for photo in photos:
        if photo.get("eventOrder") not in ranks:
            raise ValueError(
                "photoWall.eventOrder must reference an existing events.order; do not number photos independently"
            )
    photos = sorted(photos, key=lambda photo: photo["eventOrder"])

    # Three bounded, inspectable regions express the requested height ratios.
    header = header_nodes(title, subtitle, width, header_h, ink, portrait)
    wall_width = width - 2 * margin
    wall = []
    aspects = []
    for photo in photos:
        with local_image(photo["image"], base) as im:
            aspects.append(im.width / im.height)
    for i, (photo, slot) in enumerate(
        zip(photos, wall_slots(len(photos), wall_width, wall_h, aspects))
    ):
        x, y, w, h = slot
        img, _ = asset(photo["image"], base, (w, h), monochrome)
        wall.append(picture(f"photo-{i + 1}", img, x, y, w, h))
        event_order = photo["eventOrder"]
        badge_x = x + 8 if x < wall_width / 2 else x + w - 38
        badge = group(
            f"photo-ref-{i + 1}",
            badge_x,
            y + 8,
            30,
            30,
            [text(f"photo-number-{i + 1}", ranks[event_order], 8, 3, 16, 26, 16, 700, "#FFFFFF")],
            background=accent,
            zIndex=20,
        )
        wall.append(badge)
        caption = copy(
            photo.get("caption", event_by_order[event_order]["title"]), "photoWall.caption", 24
        )
        caption_w = min(300, w - 16)
        caption_x = x + 8 if x < wall_width / 2 else x + w - caption_w - 8
        # Narrow detail slots need multiple caption lines. Keep date caveats and
        # font size intact, expanding upward inside the owning photograph.
        caption_lines = sum(
            max(1, math.ceil(len(line) * 14 / max(14, caption_w - 30)))
            for line in caption.splitlines()
        )
        caption_text_h = max(33, caption_lines * math.ceil(14 * 1.45))
        caption_h = caption_text_h + 6
        if caption_h > h - 54:
            raise ValueError("photoWall.caption exceeds its photo; shorten it or use fewer photos")
        wall.append(
            group(
                f"photo-caption-{i + 1}",
                caption_x,
                y + h - caption_h - 8,
                caption_w,
                caption_h,
                [
                    text(
                        f"caption-text-{i + 1}",
                        caption,
                        8,
                        3,
                        caption_w - 16,
                        caption_text_h,
                        14,
                        color="#FFFFFF",
                    )
                ],
                background="#242424",
                zIndex=20,
            )
        )
    # Keep the subject undistorted; transparent pixels reveal the photo banks.
    cutout, (cw, ch) = asset(
        brief["portraitCutout"],
        base,
        monochrome=monochrome,
        cutout=True,
        bounds=(wall_width * 0.43, wall_h),
    )
    scale = min(wall_h / ch, wall_width * 0.43 / cw)
    cw, ch = round(cw * scale), round(ch * scale)
    hero_y = (wall_h - ch) / 2 if portrait else wall_h - ch
    hero = picture("portrait-cutout", cutout, (wall_width - cw) / 2, hero_y, cw, ch, "contain")
    hero["style"]["zIndex"] = 10
    wall.append(hero)

    # VInfo primitives give this bounded timeline a straight baseline and editable
    # date/title/body columns. Portrait reflows them into vertical tracks below.
    timeline = []
    inner = width - 2 * margin
    step = inner / len(events)
    line_y = 76
    timeline.append(group("time-axis", margin, line_y, inner, 3, [], background=ink))
    for i, event in enumerate([] if portrait else events):
        x = margin + i * step
        col = step - 24
        date = copy(event.get("dateLabel"), "dateLabel", 16)
        name = copy(event.get("title"), "event.title", 10)
        body = copy(event.get("body"), "event.body", 65)
        number = ranks[event["order"]]
        timeline.append(
            group(
                f"event-ref-{i + 1}",
                x,
                18,
                30,
                30,
                [text(f"event-number-{i + 1}", number, 8, 3, 16, 26, 16, 700, "#FFFFFF")],
                background=accent,
            )
        )
        timeline.append(text(f"date-{i + 1}", date, x + 42, 16, col - 42, 54, 18, 700, ink))
        timeline.append(
            group(f"time-dot-{i + 1}", x + 10, line_y - 5, 13, 13, [], background=accent, radius=7)
        )
        timeline.append(
            group(f"time-stem-{i + 1}", x + 16, line_y + 7, 1, 21, [], background="#BCBDB7")
        )
        timeline.append(text(f"event-title-{i + 1}", name, x, 110, col, 64, 24, 700, ink))
        timeline.append(
            text(f"event-body-{i + 1}", body, x, 180, col, timeline_h - 226, 20, color=ink)
        )
    if portrait:
        timeline = portrait_timeline(events, ranks, width, timeline_h, margin, accent, ink)
    source_note = copy(brief.get("sourceNote"), "sourceNote", 95)
    timeline.append(
        text(
            "source",
            source_note,
            margin,
            timeline_h - (64 if portrait else 44),
            width - 2 * margin if portrait else 1050,
            42,
            13,
            color="#666666",
        )
    )
    timeline.append(
        text(
            "time-scale-note",
            "先左列后右列，按事件顺序排列，间距不表示年数"
            if portrait and len(events) > 3
            else "按事件顺序排列，间距不表示年数",
            margin if portrait else 1135,
            timeline_h - (24 if portrait else 44),
            width - 2 * margin if portrait else 437,
            24 if portrait else 33,
            13,
            color="#666666",
        )
    )
    nodes = [
        group("title-band", 0, 0, width, header_h, header),
        group(
            "photo-wall",
            margin,
            header_h,
            wall_width,
            wall_h,
            wall,
            background="#E5E3DE",
            overflow="hidden",
        ),
        group("timeline-band", 0, header_h + wall_h, width, timeline_h, timeline),
    ]
    return page(title, width, height, nodes, background="#FAFAF8", accent=accent)
