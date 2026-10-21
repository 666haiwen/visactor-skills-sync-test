"""Observe orientation routing, region bounds, copy retention and asset compatibility."""

import base64
import io
import tempfile
import unittest
from pathlib import Path

from build import build
from collage import wall_slots
from cutout import prepare
from grid import grid_slots
from PIL import Image, ImageDraw
from render import embedded_fonts, make_html

ROOT = Path(__file__).resolve().parents[2]


class CollageChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        Image.new("RGB", (600, 400), "#D5703A").save(self.base / "photo.png")
        im = Image.new("RGBA", (240, 400))
        ImageDraw.Draw(im).ellipse((45, 30, 195, 380), fill="#CA6030")
        im.save(self.base / "alpha.png")
        image = {"src": "photo.png", "alt": "测试几何图，非真实人物"}
        self.brief = {
            "title": "人物模板验证",
            "subtitle": "虚构资料，仅检验版式与日期精度。",
            "layout": "landscape",
            "template": "photo-wall-timeline",
            "portraitCutout": {"src": "alpha.png", "alt": "透明几何测试图"},
            "sourceNote": "程序构造的测试资料",
            "sources": [{"type": "fixture"}],
            "events": [
                {
                    "order": i,
                    "dateLabel": f"约{1900 + i}年",
                    "title": "阶段转折",
                    "body": "这是一个测试事件，核验文案保留和排序。",
                    "image": image,
                }
                for i in range(1, 5)
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_regions_in_both_orientations_and_explicit_storyline(self):
        result = build(self.brief, self.base)[0]
        regions = result["body"]["children"]
        self.assertEqual(
            [n["style"]["height"] / result["canvas"]["height"] for n in regions],
            [1 / 8, 4 / 8, 3 / 8],
        )
        self.assertEqual([n["style"]["y"] for n in regions], [0, 125, 625])
        self.brief["layout"] = "portrait"
        portrait = build(self.brief, self.base)[0]
        self.assertEqual(
            [n["style"]["height"] / 1920 for n in portrait["body"]["children"]],
            [1 / 8, 4 / 8, 3 / 8],
        )
        self.assertEqual(portrait["body"]["children"][1]["id"], "photo-wall")
        self.brief["template"] = "storyline"
        self.brief.pop("portraitCutout")
        portrait = build(self.brief, self.base)[0]
        self.assertEqual(portrait["body"]["children"][0]["type"], "storyline")
        self.assertEqual(portrait["canvas"]["height"], 1920)
        self.assertFalse(any(n.get("id") == "photo-wall" for n in portrait["body"]["children"]))

    def test_alpha_provider_and_gray_embedding_keep_foreground(self):
        report = prepare(
            self.base / "alpha.png", self.base / "normalized.png", provider="byted-mediakit-image"
        )
        self.assertEqual(report["provider"], "byted-mediakit-image")
        self.assertEqual(report["mode"], "RGBA")
        self.brief["portraitCutout"]["src"] = "normalized.png"
        wall = build(self.brief, self.base)[0]["body"]["children"][1]
        hero = wall["children"][-1]
        result = Image.open(io.BytesIO(base64.b64decode(hero["src"].split(",", 1)[1])))
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.getchannel("A").getextrema(), (0, 255))
        self.assertTrue(all(r == g == b for r, g, b, a in result.get_flattened_data()))
        self.assertEqual(hero["fit"], "contain")

    def test_opaque_empty_and_missing_cutout_rejected(self):
        for name, color in [("opaque.png", (22, 33, 44, 255)), ("empty.png", (0, 0, 0, 0))]:
            Image.new("RGBA", (240, 400), color).save(self.base / name)
            self.brief["portraitCutout"]["src"] = name
            with self.assertRaisesRegex(ValueError, "transparent background"):
                build(self.brief, self.base)
        self.brief.pop("portraitCutout")
        with self.assertRaisesRegex(ValueError, "requires portraitCutout"):
            build(self.brief, self.base)

    def test_date_precision_and_photo_event_links(self):
        self.brief["events"][0]["dateLabel"] = "约19世纪末"
        self.brief["events"].reverse()
        self.brief["photoWall"] = [
            {"image": self.brief["events"][0]["image"], "eventOrder": n} for n in [4, 1]
        ]
        nodes = build(self.brief, self.base)[0]["body"]["children"]
        dates = [n["text"] for n in nodes[2]["children"] if n["id"].startswith("date-")]
        self.assertIn("约19世纪末", dates[0])
        labels = [
            n["children"][0]["text"]
            for n in nodes[1]["children"]
            if n["id"].startswith("photo-ref-")
        ]
        self.assertEqual(labels, ["1", "4"])
        timeline_labels = [
            n["children"][0]["text"]
            for n in nodes[2]["children"]
            if n["id"].startswith("event-ref-")
        ]
        self.assertEqual(timeline_labels, ["1", "2", "3", "4"])
        self.brief["photoWall"][0]["eventOrder"] = 999
        with self.assertRaisesRegex(ValueError, "eventOrder"):
            build(self.brief, self.base)
        self.brief["photoWall"][0].pop("eventOrder")
        with self.assertRaisesRegex(ValueError, "eventOrder"):
            build(self.brief, self.base)

    def test_caption_and_wall_remain_visible_under_transparent_subject(self):
        self.brief["photoWall"] = [
            {
                "image": self.brief["events"][0]["image"],
                "eventOrder": i,
                "caption": "约1904年 · 实验室资料照",
            }
            for i in [4, 1]
        ]
        wall = build(self.brief, self.base)[0]["body"]["children"][1]
        captions = [
            n["children"][0]["text"]
            for n in wall["children"]
            if n["id"].startswith("photo-caption-")
        ]
        self.assertEqual(captions, ["约1904年 · 实验室资料照"] * 2)
        slots = wall_slots(2, 1544, 500)
        self.assertLessEqual(slots[1][0] - (slots[0][0] + slots[0][2]), 6)

    def test_wall_corner_numbers_and_grid_cards_follow_the_event_not_photo_position(self):
        colors = [
            (220, 40, 50),
            (45, 170, 70),
            (30, 70, 230),
            (190, 70, 200),
            (200, 180, 30),
            (30, 170, 190),
        ]
        events = []
        for i, color in enumerate(colors, 1):
            Image.new("RGB", (600, 400), color).save(self.base / f"scene-{i}.png")
            events.append(
                {
                    **self.brief["events"][0],
                    "order": i * 15,
                    "dateLabel": str(1900 + i),
                    "body": f"事件{i}的说明",
                    "image": {"src": f"scene-{i}.png", "alt": f"事件{i}场景"},
                }
            )
        self.brief.update(events=[events[i] for i in [4, 0, 5, 2, 1, 3]], monochrome=False)
        self.brief["portraitCutout"]["outlineWidth"] = 0

        def color_of(node):
            image = Image.open(io.BytesIO(base64.b64decode(node["src"].split(",", 1)[1])))
            return image.getpixel((image.width // 2, image.height // 2))[:3]

        for orientation in ["portrait", "landscape"]:
            self.brief["layout"] = orientation
            self.brief["template"] = "photo-wall-timeline"
            for selected in [[5, 2, 4, 3], [6, 3, 1, 5, 2, 4]]:
                self.brief["photoWall"] = [
                    {"eventOrder": events[i - 1]["order"], "image": events[i - 1]["image"]}
                    for i in selected
                ]
                schema = build(self.brief, self.base)[0]
                wall = {n["id"]: n for n in schema["body"]["children"][1]["children"]}
                timeline = {n["id"]: n for n in schema["body"]["children"][2]["children"]}
                for position, rank in enumerate(sorted(selected), 1):
                    self.assertEqual(
                        wall[f"photo-ref-{position}"]["children"][0]["text"], str(rank)
                    )
                    self.assertEqual(color_of(wall[f"photo-{position}"]), colors[rank - 1])
                    self.assertEqual(
                        timeline[f"event-ref-{rank}"]["children"][0]["text"], str(rank)
                    )
                    self.assertEqual(timeline[f"date-{rank}"]["text"], str(1900 + rank))
            self.brief.pop("photoWall")
            self.brief["template"] = "center-grid"
            grid = build(self.brief, self.base)[0]["body"]["children"][1]
            for rank, card in enumerate(
                [n for n in grid["children"] if n["id"].startswith("event-card-")], 1
            ):
                children = {n["id"]: n for n in card["children"]}
                self.assertEqual(children[f"card-ref-{rank}"]["children"][0]["text"], str(rank))
                self.assertEqual(children[f"date-{rank}"]["text"], str(1900 + rank))
                self.assertEqual(color_of(children[f"event-image-{rank}"]), colors[rank - 1])

    def test_font_resources_and_schema_use_cdn_family(self):
        assets = ROOT / "skills/life-chronicle/assets"
        self.assertEqual(embedded_fonts(assets), [])
        self.assertFalse(list(assets.rglob("*.woff2")))
        schema = build(self.brief, self.base)[0]
        self.assertIn('"Noto Serif SC"', schema["appearance"]["typography"]["fontFamily"])
        self.assertIn('"STSong"', schema["appearance"]["typography"]["fontFamily"])
        output = make_html(schema, self.base / "landscape.html")
        self.assertIn("miaoda.feishu.cn/fonts/css2", output.read_text())
        self.assertNotIn("url(data:font/", output.read_text())

    def test_generic_event_images_keep_photo_date_caveats(self):
        self.brief["events"][0]["imageCaption"] = "拍摄年份不详 · 相关资料照"
        schema = build(self.brief, self.base)[0]
        wall = schema["body"]["children"][1]
        caption = next(n for n in wall["children"] if n["id"] == "photo-caption-1")
        self.assertEqual(caption["children"][0]["text"], self.brief["events"][0]["imageCaption"])

    def test_capacity_and_bounds_for_two_through_eight(self):
        # Geometry/copy checks do not need repeated high-resolution outline rasterization.
        self.brief["portraitCutout"]["outlineWidth"] = 0
        for count in range(2, 9):
            self.brief["events"] = [{**self.brief["events"][0], "order": i} for i in range(count)]
            schema = build(self.brief, self.base)[0]

            def check(parent):
                w, h = parent["style"]["width"], parent["style"]["height"]
                for node in parent.get("children", []):
                    s = node["style"]
                    self.assertGreaterEqual(s["x"], 0)
                    self.assertGreaterEqual(s["y"], 0)
                    self.assertLessEqual(s["x"] + s["width"], w)
                    self.assertLessEqual(s["y"] + s["height"], h)
                    if "children" in node:
                        check(node)

            check(schema["body"])
        self.brief["events"][0]["body"] = "密" * 65
        with self.assertRaisesRegex(ValueError, "exceeds the frame"):
            build(self.brief, self.base)

    def test_local_model_download_and_source_preservation(self):
        with self.assertRaisesRegex(ValueError, "Model is not cached"):
            prepare(
                self.base / "photo.png",
                self.base / "result.png",
                "rembg",
                model_dir=self.base / "models",
            )
        (self.base / "models").mkdir()
        (self.base / "models/u2netp.onnx").write_bytes(b"incomplete model")
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            prepare(
                self.base / "photo.png",
                self.base / "result.png",
                "rembg",
                model_dir=self.base / "models",
            )
        with self.assertRaisesRegex(ValueError, "Keep the source"):
            prepare(self.base / "alpha.png", self.base / "alpha.png")

    def test_templates_reflow_keep_copy_and_fit_for_all_counts(self):
        # Geometry/copy checks do not need repeated high-resolution outline rasterization.
        self.brief["portraitCutout"]["outlineWidth"] = 0
        event = self.brief["events"][0]
        for template in ["photo-wall-timeline", "center-grid"]:
            for layout in ["landscape", "portrait"]:
                for count in range(4 if template == "center-grid" else 2, 9):
                    with self.subTest(template=template, layout=layout, count=count):
                        self.brief.update(
                            template=template,
                            layout=layout,
                            events=[
                                {**event, "order": i, "imageCaption": "拍摄年份不详 · 资料图"}
                                for i in range(count)
                            ],
                        )
                        schema = build(self.brief, self.base)[0]
                        seen = []

                        def check(parent):
                            ps = parent["style"]
                            for node in parent.get("children", []):
                                s = node["style"]
                                self.assertGreaterEqual(s["x"], 0)
                                self.assertGreaterEqual(s["y"], 0)
                                self.assertLessEqual(s["x"] + s["width"], ps["width"] + 0.01)
                                self.assertLessEqual(s["y"] + s["height"], ps["height"] + 0.01)
                                if node["id"].startswith("event-body-"):
                                    seen.append(node["text"])
                                if node["id"].startswith("caption-text-"):
                                    self.assertEqual(node["text"], "拍摄年份不详 · 资料图")
                                    self.assertEqual(node["textStyle"]["fontSize"], 14)
                                check(node)

                        check(schema["body"])
                        self.assertEqual(seen, [event["body"]] * count)
                        self.assertEqual(
                            schema["canvas"]["width"] < schema["canvas"]["height"],
                            layout == "portrait",
                        )

    def test_grid_no_overlap_central_subject_and_sorted_images(self):
        # Geometry/copy checks do not need repeated high-resolution outline rasterization.
        self.brief["portraitCutout"]["outlineWidth"] = 0
        for count in range(4, 9):
            slots, hero = grid_slots(count, 1024, 1616)
            self.assertAlmostEqual(hero[0] + hero[2] / 2, 512)
            self.assertAlmostEqual(hero[1] + hero[3] / 2, 808)
            all_slots = slots + [hero]
            for i, (x, y, w, h) in enumerate(all_slots):
                for xx, yy, ww, hh in all_slots[i + 1 :]:
                    self.assertFalse(
                        min(x + w, xx + ww) - max(x, xx) > 0.01
                        and min(y + h, yy + hh) - max(y, yy) > 0.01
                    )
        self.brief["template"] = "center-grid"
        self.brief["events"].reverse()
        self.brief["events"][0]["image"] = {"src": "alpha.png", "alt": "最后一个事件的图"}
        grid = build(self.brief, self.base)[0]["body"]["children"][1]
        cards = [n for n in grid["children"] if n["id"].startswith("event-card-")]
        last_image = next(n for n in cards[-1]["children"] if n["type"] == "image")
        self.assertEqual(last_image["alt"], "最后一个事件的图")
        self.brief["events"][0].pop("image")
        with self.assertRaisesRegex(ValueError, "every event card needs"):
            build(self.brief, self.base)

    def test_invalid_template_and_grid_card_budget(self):
        self.brief["template"] = "portrait"
        with self.assertRaisesRegex(ValueError, "template must"):
            build(self.brief, self.base)
        self.brief.update(template="center-grid", layout="portrait")
        self.brief["events"] = [
            {
                **self.brief["events"][0],
                "order": i,
                "body": "\n".join(["密密密密密"] * 10),
                "imageCaption": "资料照片中的实际拍摄日期尚未核实，事件年份不等于图片年份。",
            }
            for i in range(8)
        ]
        # Dense cards must fail rather than hide text or crush their photographs.
        with self.assertRaisesRegex(ValueError, "image space|exceeds the frame"):
            build(self.brief, self.base)


if __name__ == "__main__":
    unittest.main(verbosity=2)
