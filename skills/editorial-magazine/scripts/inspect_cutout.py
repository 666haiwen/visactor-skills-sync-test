#!/usr/bin/env python3
"""Read a transparent PNG and suggest coarse colors; never edit image pixels."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def inspect(path, region=None):
    from PIL import Image

    with Image.open(path) as source:
        if source.format != "PNG":
            raise ValueError("Cutout must be a PNG with transparency")
        im = source.convert("RGBA")
    w, h = im.size
    # RGB PNG conversion produces opaque alpha, so it is correctly rejected below.
    alpha = im.getchannel("A").histogram()
    total = w * h
    clear, visible = alpha[0], total - alpha[0]
    if not clear or not visible:
        raise ValueError("Need both fully transparent background and visible subject pixels")
    bounds = region or (0, 0, w, h)
    x0, y0, x1, y1 = bounds
    if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
        raise ValueError("Region must be a nonempty rectangle inside the image")
    pixels = im.load()
    bins, sums = Counter(), {}
    step = max(1, int(((x1 - x0) * (y1 - y0) / 120000) ** 0.5))
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            red, green, blue, a = pixels[x, y]
            if a < 224:
                continue
            key = (red // 32, green // 32, blue // 32)
            bins[key] += 1
            v = sums.setdefault(key, [0, 0, 0])
            for i, value in enumerate((red, green, blue)):
                v[i] += value
    if not bins:
        raise ValueError("Region contains no sufficiently opaque subject pixels for color sampling")
    colors = []
    for key, count in bins.most_common(5):
        rgb = [round(v / count) for v in sums[key]]
        colors.append("#" + "".join(f"{v:02X}" for v in rgb))
    return {
        "image": str(Path(path).resolve()),
        "width": w,
        "height": h,
        "transparentFraction": round(clear / total, 4),
        "partialAlphaFraction": round(sum(alpha[1:255]) / total, 4),
        "sampleRegion": list(bounds),
        "candidateColors": colors,
        "requiresVisualReview": True,
        "note": "Alpha presence only; check edges, missing accessories, residual background and garment colors visually.",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--region", help="Garment sampling rectangle: x0,y0,x1,y1 in original pixels")
    a = p.parse_args()
    try:
        region = tuple(map(int, a.region.split(","))) if a.region else None
        if region and len(region) != 4:
            raise ValueError("Region requires four integers")
        print(json.dumps(inspect(a.image, region), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
