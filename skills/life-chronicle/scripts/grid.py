"""A central cutout cell surrounded by dated event cards, in either orientation."""

import math

from collage import asset, group, header_nodes
from page import copy, page, picture, text


def grid_slots(count, width, height, gap=14):
    if not 4 <= count <= 8:
        raise ValueError(
            "center-grid needs 4..8 events; use photo-wall-timeline for fewer events or split chapters"
        )
    col = (width - 2 * gap) / 3
    center_h = (height - 2 * gap) / 3
    hero = (col + gap, center_h + gap, col, center_h)
    # Merge outer-row cells when fewer than eight events are available. This
    # keeps the center occupied without creating narrow, page-height cards.
    slots = [(0, center_h + gap, col, center_h), (2 * (col + gap), center_h + gap, col, center_h)]
    for y, n in [(0, math.ceil((count - 2) / 2)), (2 * (center_h + gap), (count - 2) // 2)]:
        w = (width - gap * (n - 1)) / n
        slots.extend((i * (w + gap), y, w, center_h) for i in range(n))
    return sorted(slots, key=lambda s: (s[1], s[0])), hero


def measured_height(content, width, size):
    return sum(
        max(1, math.ceil(len(line) * size / max(size, width - size)))
        for line in content.splitlines()
    ) * math.ceil(size * 1.45)


def event_card(event, rank, slot, base, monochrome, accent):
    x, y, w, h = slot
    pad, gap, ink = 18, 10, "#202020"
    inner = w - 2 * pad
    date = copy(event.get("dateLabel"), "dateLabel", 16)
    title = copy(event.get("title"), "event.title", 10)
    body = copy(event.get("body"), "event.body", 65)
    if not event.get("image"):
        raise ValueError(
            "center-grid: every event card needs an event.image; use a verified related artifact if no scene exists"
        )
    caption = (
        copy(event["imageCaption"], "event.imageCaption", 40) if event.get("imageCaption") else None
    )
    children = [
        group(
            f"card-ref-{rank}",
            pad,
            pad,
            30,
            30,
            [text(f"card-number-{rank}", str(rank), 8, 3, 16, 26, 16, 700, "#FFFFFF")],
            background=accent,
        ),
        text(f"date-{rank}", date, pad + 42, pad, inner - 42, 30, 18, 700, ink),
    ]
    title_y = pad + 38
    title_h = measured_height(title, inner, 26)
    children.append(text(f"event-title-{rank}", title, pad, title_y, inner, title_h, 26, 700, ink))
    content_y = title_y + title_h + gap
    content_h = h - pad - content_y
    # Wide cards put image beside body; tall cards stack all three elements.
    if w / h > 1.25:
        image_w = round(inner * 0.46)
        body_x, body_w = pad + image_w + gap, inner - image_w - gap
        cap_h = measured_height(caption, image_w, 13) if caption else 0
        image_h = content_h - cap_h - (gap if caption else 0)
        body_y, body_h = content_y, content_h
    else:
        image_w = inner
        body_x, body_w = pad, inner
        cap_h = measured_height(caption, inner, 13) if caption else 0
        body_h = measured_height(body, body_w, 20)
        image_h = content_h - body_h - cap_h - gap * (2 if caption else 1)
        body_y = h - pad - body_h
    if image_h < 80:
        raise ValueError(
            f"event-{rank}: card copy leaves too little image space; shorten it or split chapters"
        )
    img, _ = asset(event["image"], base, (round(image_w), round(image_h)), monochrome)
    children.append(picture(f"event-image-{rank}", img, pad, content_y, image_w, image_h))
    if caption:
        children.append(
            text(
                f"image-caption-{rank}",
                caption,
                pad,
                content_y + image_h + gap,
                image_w,
                cap_h,
                13,
                color="#666666",
            )
        )
    children.append(text(f"event-body-{rank}", body, body_x, body_y, body_w, body_h, 20, color=ink))
    return group(f"event-card-{rank}", x, y, w, h, children)


def build_center_grid(brief, base, events):
    portrait = brief.get("layout", "landscape") == "portrait"
    width, height = (1080, 1920) if portrait else (1920, 1280)
    header_h, margin = height // 8, 28
    if not brief.get("portraitCutout"):
        raise ValueError(
            "center-grid requires portraitCutout: a local transparent PNG of the subject"
        )
    if brief.get("photoWall") or brief.get("titleImage") or brief.get("backgroundImage"):
        raise ValueError(
            "center-grid uses events[].image and portraitCutout, not photoWall/titleImage/backgroundImage"
        )
    mono = brief.get("monochrome", True)
    if type(mono) is not bool:
        raise ValueError("monochrome must be true or false")
    accent = brief.get("accent", "#735248")
    title, subtitle = (
        copy(brief.get("title"), "title", 32),
        copy(brief.get("subtitle"), "subtitle", 100),
    )
    inner, grid_h = width - 2 * margin, height - header_h - 64
    slots, hero_slot = grid_slots(len(events), inner, grid_h)
    cards = [
        event_card(e, i, slot, base, mono, accent)
        for i, (e, slot) in enumerate(zip(events, slots), 1)
    ]
    x, y, w, h = hero_slot
    cutout, (cw, ch) = asset(
        brief["portraitCutout"], base, monochrome=mono, cutout=True, bounds=(w - 12, h - 12)
    )
    scale = min((w - 12) / cw, (h - 12) / ch)
    cw, ch = cw * scale, ch * scale
    cards.append(
        group(
            "portrait-cell",
            x,
            y,
            w,
            h,
            [picture("portrait-cutout", cutout, (w - cw) / 2, (h - ch) / 2, cw, ch, "contain")],
            background="#DFDDD6",
            radius=8,
        )
    )
    cards.append(
        text(
            "source",
            copy(brief.get("sourceNote"), "sourceNote", 95),
            0,
            grid_h + 12,
            inner,
            42,
            13,
            color="#666666",
        )
    )
    nodes = [
        group(
            "title-band",
            0,
            0,
            width,
            header_h,
            header_nodes(title, subtitle, width, header_h, "#202020", portrait),
        ),
        group("event-grid", margin, header_h, inner, height - header_h, cards),
    ]
    return page(title, width, height, nodes, background="#F0EFEB", accent=accent)
