"""Behavioral checks for photo masks, chronological links and text capacity."""

import base64
import io
import math
import re
import tempfile
import unittest
from pathlib import Path

from build import build
from PIL import Image, ImageDraw
from ring import callout, ring_geometry, sector_asset

ROOT = Path(__file__).resolve().parents[2]


class RingChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        Image.new("RGB", (600, 400), "#D5703A").save(self.base / "scene.png")
        image = Image.new("RGBA", (200, 360))
        ImageDraw.Draw(image).ellipse((25, 10, 175, 345), fill="#4B8A91")
        image.save(self.base / "cutout.png")
        self.brief = {
            "title": "人物模板验证",
            "subtitle": "虚构资料与几何图，仅检验布局。",
            "template": "photo-ring",
            "portraitCutout": {"src": "cutout.png", "alt": "透明几何示意图", "outlineWidth": 0},
            "sourceNote": "测试资料",
            "sources": [{"type": "fixture"}],
            "events": [
                {
                    "order": i,
                    "dateLabel": f"约{1900 + i}年",
                    "title": "阶段转折",
                    "body": f"阶段{i}：这一事件的内容与意义。",
                    "image": {"src": "scene.png", "alt": f"事件{i}的测试场景图"},
                }
                for i in range(1, 7)
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_masks_keep_photos_only_in_their_annular_sector(self):
        radius, inner = 200, 112
        for index in range(5):
            a, b = (
                -math.pi / 2 + index * math.pi / 5 + 0.01,
                -math.pi / 2 + (index + 1) * math.pi / 5 - 0.01,
            )
            image, (x, y, w, h) = sector_asset(
                self.brief["events"][0]["image"], self.base, radius, inner, a, b, False
            )
            result = Image.open(io.BytesIO(base64.b64decode(image["src"].split(",", 1)[1])))
            self.assertEqual(result.size, (w, h))
            alpha = result.getchannel("A")
            self.assertEqual(alpha.getextrema(), (0, 255))
            angle, distance = (a + b) / 2, (radius + inner) / 2
            p = (
                round(distance * math.cos(angle) - x),
                round(radius + distance * math.sin(angle) - y),
            )
            self.assertGreater(alpha.getpixel(p), 245)
            self.assertEqual(result.getpixel(p)[:3], (213, 112, 58))
            for yy in range(0, h, 7):
                for xx in range(0, w, 7):
                    if alpha.getpixel((xx, yy)) > 128:
                        distance = math.hypot(xx + x, yy + y - radius)
                        self.assertGreaterEqual(distance, inner - 2)
                        self.assertLessEqual(distance, radius + 2)

    def test_ordered_photos_cards_and_bounds_in_both_orientations(self):
        for orientation in ["landscape", "portrait"]:
            self.brief["layout"] = orientation
            self.brief["events"].reverse()
            result = build(self.brief, self.base)[0]
            h = result["canvas"]["height"]
            header, body = result["body"]["children"]
            self.assertEqual(header["style"]["height"], h / 8)
            self.assertEqual(body["style"]["height"], h * 7 / 8)

            def check(parent):
                ps = parent["style"]
                for child in parent.get("children", []):
                    cs = child["style"]
                    self.assertGreaterEqual(cs["x"], 0)
                    self.assertGreaterEqual(cs["y"], 0)
                    self.assertLessEqual(cs["x"] + cs["width"], ps["width"] + 0.01)
                    self.assertLessEqual(cs["y"] + cs["height"], ps["height"] + 0.01)
                    check(child)

            check(result["body"])
            photos = [n for n in body["children"] if n["id"].startswith("event-photo-")]
            cards = [n for n in body["children"] if n["id"].startswith("event-card-")]
            leaders = [n for n in body["children"] if n["id"].startswith("event-leader-")]
            self.assertEqual((len(photos), len(cards), len(leaders)), (6, 6, 6))
            for rank, (photo, card) in enumerate(zip(photos, cards), 1):
                self.assertIn(f"事件{rank}", photo["alt"])
                self.assertIn(f"阶段{rank}", card["children"][1]["text"])
                self.assertNotIn("background", card["style"])
                self.assertEqual(card["children"][0]["type"], "text")
                self.assertEqual(card["children"][1]["type"], "text")
            hero = next(n for n in body["children"] if n["id"] == "portrait-cutout")
            self.assertLess(hero["style"]["x"] + hero["style"]["width"], cards[0]["style"]["x"])

    def test_shuffled_sparse_orders_keep_photo_card_links_without_visible_numbers(self):
        colors = [
            (220, 40, 50),
            (45, 170, 70),
            (30, 70, 230),
            (190, 70, 200),
            (200, 180, 30),
            (30, 170, 190),
        ]
        for i, event in enumerate(self.brief["events"]):
            event["order"] = (i + 1) * 10
            Image.new("RGB", (600, 400), colors[i]).save(self.base / f"scene-{i}.png")
            event["image"]["src"] = f"scene-{i}.png"
        self.brief["events"] = [self.brief["events"][i] for i in [3, 0, 5, 2, 1, 4]]
        self.brief["monochrome"] = False
        for orientation in ["portrait", "landscape"]:
            self.brief["layout"] = orientation
            result = build(self.brief, self.base)[0]
            body = result["body"]["children"][1]
            nodes = {n["id"]: n for n in body["children"]}
            geometry = ring_geometry(6, result["canvas"]["width"], body["style"]["height"])

            def check_no_numbers(node):
                self.assertFalse(
                    node["id"].startswith(
                        ("photo-ref-", "event-ref-", "photo-number-", "event-number-")
                    )
                )
                for child in node.get("children", []):
                    check_no_numbers(child)

            check_no_numbers(body)
            for rank in range(1, 7):
                card = nodes[f"event-card-{rank}"]
                self.assertIn(f"阶段{rank}", card["children"][1]["text"])
                photo = Image.open(
                    io.BytesIO(
                        base64.b64decode(nodes[f"event-photo-{rank}"]["src"].split(",", 1)[1])
                    )
                )
                opaque = next(
                    photo.getpixel((x, y))
                    for y in range(photo.height)
                    for x in range(photo.width)
                    if photo.getpixel((x, y))[3] == 255
                )
                self.assertEqual(opaque[:3], colors[rank - 1])
                # The unnumbered ring uses leaders alone to connect photos and cards.
                line = nodes[f"event-leader-{rank}"]
                values = list(map(float, re.findall(r"-?\d+(?:\.\d+)?", line["path"])))
                points = list(zip(values[::2], values[1::2]))
                start = tuple(
                    (points[0][i] + points[3][i]) / 2 + line["style"][key]
                    for i, key in enumerate(["x", "y"])
                )
                end = tuple(
                    (points[-3][i] + points[-2][i]) / 2 + line["style"][key]
                    for i, key in enumerate(["x", "y"])
                )
                cs = card["style"]
                expected_start = geometry["sectors"][rank - 1]["anchor"]
                expected_end = (cs["x"] - 8, cs["y"] + card["children"][0]["style"]["height"] / 2)
                for actual, expected in zip(start + end, expected_start + expected_end):
                    self.assertAlmostEqual(actual, expected, places=3)

    def test_two_through_eight_leaders_have_monotonic_non_crossing_lanes(self):
        for width, height in [(1600, 1200), (1200, 1600)]:
            for count in range(2, 9):
                geometry = ring_geometry(count, width, height * 7 / 8)
                anchors, ends, cards = [], [], []
                for i, sector in enumerate(geometry["sectors"]):
                    card, endpoint = callout(self.brief["events"][0], i + 1, sector["cardSlot"])
                    anchors.append(sector["anchor"][1])
                    ends.append(endpoint[1])
                    cards.append(card["style"])
                    self.assertLess(sector["anchor"][0], geometry["laneX"])
                    self.assertLess(geometry["laneX"], endpoint[0])
                # All diagonal leaders use the same x interval with both ends in
                # strictly increasing y order, so they cannot cross each other.
                self.assertTrue(all(a < b for a, b in zip(anchors, anchors[1:])))
                self.assertTrue(all(a < b for a, b in zip(ends, ends[1:])))
                self.assertTrue(
                    all(a["y"] + a["height"] < b["y"] for a, b in zip(cards, cards[1:]))
                )

    def test_missing_images_cutout_and_overflow_are_explicit_failures(self):
        self.brief["events"][0].pop("image")
        with self.assertRaisesRegex(ValueError, "every event needs"):
            build(self.brief, self.base)
        self.brief.pop("portraitCutout")
        with self.assertRaisesRegex(ValueError, "requires portraitCutout"):
            build(self.brief, self.base)
        event = {**self.brief["events"][0], "body": "\n".join(["正文"] * 10)}
        with self.assertRaisesRegex(ValueError, "exceeds the frame"):
            callout(event, 1, (700, 0, 400, 160))


if __name__ == "__main__":
    unittest.main(verbosity=2)
