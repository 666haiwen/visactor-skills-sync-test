"""Height-led photo half-ring, central cutout and ordered native text callouts."""

import base64
import io
import math

from collage import asset, group, header_nodes
from grid import measured_height
from page import copy, page, picture, text
from PIL import Image, ImageChops, ImageDraw


def ring_geometry(count, width, body_height):
    if not 2 <= count <= 8:
        raise ValueError("photo-ring needs 2..8 events; split longer biographies into chapters")
    margin, top = 28, 12
    radius = (body_height - 80) / 2
    inner = radius * 0.56
    card_x = margin + radius + 90
    card_w = width - card_x - margin
    step = 2 * radius / count
    if card_w < 300:
        raise ValueError("photo-ring needs at least 300px for its text column")
    # The reference crops the back half of the circle at the left page edge.
    # The visible half runs top to bottom, giving the callouts the same order.
    gap = 3 / inner
    sectors = []
    for index in range(count):
        start = -math.pi / 2 + index * math.pi / count + gap / 2
        end = -math.pi / 2 + (index + 1) * math.pi / count - gap / 2
        angle = (start + end) / 2
        anchor = (
            margin + (radius + 4) * math.cos(angle),
            top + radius + (radius + 4) * math.sin(angle),
        )
        sectors.append(
            {
                "start": start,
                "end": end,
                "anchor": anchor,
                "cardSlot": (card_x, top + index * step, card_w, step),
            }
        )
    return {
        "radius": radius,
        "inner": inner,
        "x": margin,
        "y": top,
        "laneX": margin + radius + 24,
        "sectors": sectors,
    }


def sector_polygon(radius, inner, start, end):
    steps = max(12, math.ceil((end - start) * radius / 4))
    angles = [start + (end - start) * i / steps for i in range(steps + 1)]
    return [(radius * math.cos(a), radius + radius * math.sin(a)) for a in angles] + [
        (inner * math.cos(a), radius + inner * math.sin(a)) for a in reversed(angles)
    ]


def sector_asset(item, base, radius, inner, start, end, monochrome):
    points = sector_polygon(radius, inner, start, end)
    x, y = math.floor(min(p[0] for p in points)), math.floor(min(p[1] for p in points))
    w, h = math.ceil(max(p[0] for p in points)) - x, math.ceil(max(p[1] for p in points)) - y
    cropped, _ = asset(item, base, (w, h), monochrome)
    photo = Image.open(io.BytesIO(base64.b64decode(cropped["src"].split(",", 1)[1]))).convert(
        "RGBA"
    )
    # Rasterize only each photo's geometric mask; titles/bodies remain VInfo text.
    scale = 3
    mask = Image.new("L", (w * scale, h * scale))
    ImageDraw.Draw(mask).polygon(
        [((px - x) * scale, (py - y) * scale) for px, py in points], fill=255
    )
    mask = mask.resize((w, h), Image.Resampling.LANCZOS)
    photo.putalpha(ImageChops.multiply(photo.getchannel("A"), mask))
    data = io.BytesIO()
    photo.save(data, format="PNG")
    return {
        "src": "data:image/png;base64," + base64.b64encode(data.getvalue()).decode(),
        "alt": cropped["alt"],
    }, (x, y, w, h)


def leader_node(rank, points):
    """A filled path of narrow quads keeps leaders native and renderer-independent."""
    pad, thickness = 2, 1.4
    x = min(p[0] for p in points) - pad
    y = min(p[1] for p in points) - pad
    w = max(p[0] for p in points) - x + pad
    h = max(p[1] for p in points) - y + pad
    path = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        nx, ny = -dy / length * thickness / 2, dx / length * thickness / 2
        corners = [
            (ax + nx - x, ay + ny - y),
            (bx + nx - x, by + ny - y),
            (bx - nx - x, by - ny - y),
            (ax - nx - x, ay - ny - y),
        ]
        path.append("M" + " L".join(f"{px:.3f} {py:.3f}" for px, py in corners) + " Z")
    return {
        "type": "icon",
        "id": f"event-leader-{rank}",
        "path": " ".join(path),
        "fill": "#9D9991",
        "viewBox": {"width": w, "height": h},
        "style": {"x": x, "y": y, "width": w, "height": h},
    }


def callout(event, rank, slot):
    x, y, w, h = slot
    date = copy(event.get("dateLabel"), "dateLabel", 16)
    title = copy(event.get("title"), "event.title", 10)
    body = copy(event.get("body"), "event.body", 65)
    headline = f"{date} · {title}"
    headline_h = measured_height(headline, w, 24)
    # Reserve an extra wrap margin for CJK punctuation/renderer text fitting;
    # a merely theoretical two-line fit can otherwise trigger SDK auto-shrink.
    body_h = measured_height(body, w - 40, 20)
    caption = (
        copy(event["imageCaption"], "event.imageCaption", 40) if event.get("imageCaption") else None
    )
    caption_h = measured_height(caption, w, 13) if caption else 0
    used = headline_h + 12 + body_h + (10 + caption_h if caption else 0)
    if used > h - 12:
        raise ValueError(
            f"event-{rank}: ring card copy exceeds the frame; shorten the paragraph/caption or split chapters"
        )
    card_y = y + (h - used) / 2
    children = [
        text(f"event-title-{rank}", headline, 0, 0, w, headline_h, 24, 700, "#202020"),
        text(f"event-body-{rank}", body, 0, headline_h + 12, w, body_h, 20, color="#202020"),
    ]
    if caption:
        children.append(
            text(
                f"image-caption-{rank}",
                caption,
                0,
                used - caption_h,
                w,
                caption_h,
                13,
                color="#77736B",
            )
        )
    return group(f"event-card-{rank}", x, card_y, w, used, children), (
        x - 8,
        card_y + headline_h / 2,
    )


def build_photo_ring(brief, base, events):
    portrait = brief.get("layout", "landscape") == "portrait"
    width, height = (1200, 1600) if portrait else (1600, 1200)
    header_h, body_h = height / 8, height * 7 / 8
    if not brief.get("portraitCutout"):
        raise ValueError(
            "photo-ring requires portraitCutout: a local transparent PNG of the subject"
        )
    if any(brief.get(key) for key in ("photoWall", "titleImage", "backgroundImage")):
        raise ValueError(
            "photo-ring uses events[].image and portraitCutout, not photoWall/titleImage/backgroundImage"
        )
    monochrome = brief.get("monochrome", True)
    if type(monochrome) is not bool:
        raise ValueError("monochrome must be true or false")
    accent = brief.get("accent", "#735248")
    title, subtitle = (
        copy(brief.get("title"), "title", 32),
        copy(brief.get("subtitle"), "subtitle", 100),
    )
    geometry = ring_geometry(len(events), width, body_h)
    r, inner = geometry["radius"], geometry["inner"]
    photos, leaders, cards = [], [], []
    for rank, (event, sector) in enumerate(zip(events, geometry["sectors"]), 1):
        if not event.get("image"):
            raise ValueError(
                "photo-ring: every event needs an event.image associated with that milestone"
            )
        img, (x, y, w, h) = sector_asset(
            event["image"], base, r, inner, sector["start"], sector["end"], monochrome
        )
        photos.append(
            picture(
                f"event-photo-{rank}", img, geometry["x"] + x, geometry["y"] + y, w, h, "contain"
            )
        )
        card, endpoint = callout(event, rank, sector["cardSlot"])
        cards.append(card)
        start = sector["anchor"]
        leaders.append(leader_node(rank, [start, (geometry["laneX"], start[1]), endpoint]))
    bounds = (inner * 1.18, r * 1.55)
    cutout, (cw, ch) = asset(
        brief["portraitCutout"], base, monochrome=monochrome, cutout=True, bounds=bounds
    )
    scale = min(bounds[0] / cw, bounds[1] / ch)
    cw, ch = cw * scale, ch * scale
    hero = picture(
        "portrait-cutout",
        cutout,
        12 + (bounds[0] - cw) / 2,
        geometry["y"] + r - ch / 2,
        cw,
        ch,
        "contain",
    )
    source = text(
        "source",
        copy(brief.get("sourceNote"), "sourceNote", 95),
        28,
        body_h - 48,
        width - 56,
        42,
        13,
        color="#77736B",
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
        group(
            "ring-body", 0, header_h, width, body_h, photos + leaders + [hero] + cards + [source]
        ),
    ]
    return page(title, width, height, nodes, background="#FAF8F3", accent=accent)
