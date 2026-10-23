#!/usr/bin/env python3
"""Probe the real Python/browser environment and collect font metrics before production.

No automatic installs, network lookups or provider discovery. Font samples are
diagnostic evidence, not proof that a named system font exists or covers all glyphs.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("preflight.json"))
    parser.add_argument("--font", action="append", help="CSS font family to sample; repeatable")
    parser.add_argument("--text", default="人物数据海报 52岁 91岁 《代表作品》")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sample = args.output.with_name(args.output.stem + ".font-sample.png")
    started = perf_counter()
    report = {"startedAtUtc": datetime.now(timezone.utc).isoformat(),
              "python": {"executable": sys.executable, "version": sys.version.split()[0]},
              "passed": False, "errors": [], "packages": {}, "timings": {},
              "fontSample": None,
              "notes": ["Font metrics may reflect fallback fonts; visually inspect the sample and current poster.",
                        "This checks environment execution, not data accuracy or total poster-generation time."]}
    if sys.version_info < (3, 10):
        report["errors"].append("Python 3.10+ is required; select a supported interpreter")
    for package, module in [("Pillow", "PIL"), ("playwright", "playwright.sync_api")]:
        try:
            importlib.import_module(module)
            report["packages"][package] = version(package)
        except (ImportError, ValueError) as error:
            report["errors"].append(f"Cannot load {package}: {error}")
    report["timings"]["importsSeconds"] = round(perf_counter() - started, 3)
    phase = "browser-launch"
    if not report["errors"]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                mark = perf_counter()
                browser = playwright.chromium.launch(headless=True)
                report["timings"]["launchSeconds"] = round(perf_counter() - mark, 3)
                try:
                    phase = "font-probe"
                    page = browser.new_page(viewport={"width": 1200, "height": 800})
                    page.set_content('<main id="probe" style="background:#faf6f0;color:#352b25;padding:24px;width:max-content;min-width:900px"></main>')
                    report["fontMetrics"] = page.evaluate("""async ({fonts, text}) => {
                      const root = document.querySelector('#probe');
                      const canvas = document.createElement('canvas');
                      const ctx = canvas.getContext('2d');
                      const result = [];
                      for (const family of fonts) {
                        await document.fonts.load('700 108px ' + family);
                        const label = document.createElement('div'); label.textContent = family;
                        label.style.cssText = 'font:16px sans-serif;margin-top:12px';
                        const sample = document.createElement('div'); sample.textContent = text;
                        sample.style.cssText = 'font-size:108px;font-weight:700;line-height:1.4;padding:16px 0;white-space:nowrap';
                        sample.style.fontFamily = family;
                        root.append(label, sample);
                        ctx.font = '700 108px ' + family;
                        const metrics = ctx.measureText(text);
                        result.push({requestedFamily: family, text, measuredWidth: metrics.width,
                          glyphAscent: metrics.actualBoundingBoxAscent, glyphDescent: metrics.actualBoundingBoxDescent,
                          lineBoxHeight: sample.clientHeight, scrollHeight: sample.scrollHeight});
                      }
                      await document.fonts.ready;
                      return result;
                    }""", {"fonts": args.font or ["serif", "sans-serif"], "text": args.text})
                    box = page.locator("#probe").bounding_box()
                    page.set_viewport_size({"width": max(1200, int(box["width"] + 8)),
                                            "height": max(800, int(box["height"] + 8))})
                    page.locator("#probe").screenshot(path=str(sample))
                    report["fontSample"] = sample.name
                    report["browserVersion"] = browser.version
                    report["passed"] = True
                finally:
                    browser.close()
        except Exception as error:
            report["errors"].append(f"{phase}: {error}")
    report["timings"]["totalSeconds"] = round(perf_counter() - started, 3)
    if not report["passed"]:
        report["nextAction"] = "Use the selected environment's Python with scripts/requirements.txt and install its Chromium; rerun this probe before generating assets"
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(args.output),
                      "seconds": report["timings"]["totalSeconds"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
