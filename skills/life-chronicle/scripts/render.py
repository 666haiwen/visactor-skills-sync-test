#!/usr/bin/env python3
"""Generate native VInfo HTML; optionally export its verified canvas to PNG."""

import argparse
import base64
import functools
import html
import json
import os
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RUNTIME = "https://sf-unpkg-src.bytedance.net/@dp/vinfo-graphics@0.12.4/dist/index.umd.js"


def json_script(value):
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def schema_font_families(value):
    families = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "fontFamily" and isinstance(child, str):
                families.update(name.strip().strip("\"'") for name in child.split(","))
            else:
                families.update(schema_font_families(child))
    elif isinstance(value, list):
        for child in value:
            families.update(schema_font_families(child))
    return families


def embedded_fonts(assets, families=None):
    """Optional skill-owned fonts; local faces are checked, licensed files embedded."""
    manifest = assets / "fonts.json"
    if not manifest.exists():
        return []
    faces = json.loads(manifest.read_text(encoding="utf-8"))
    if families is not None:
        faces = [face for face in faces if face["family"] in families]
    for face in faces:
        if "file" in face:
            path = (assets / face.pop("file")).resolve()
            if not path.is_relative_to(assets.resolve()) or path.suffix != ".woff2":
                raise ValueError("Packaged fonts must be WOFF2 files inside assets")
            face["source"] = (
                "url(data:font/woff2;base64," + base64.b64encode(path.read_bytes()).decode() + ")"
            )
            license_path = (assets / face.pop("licenseFile")).resolve()
            if not license_path.is_relative_to(assets.resolve()):
                raise ValueError("Font license must be inside assets")
            face["license"] = license_path.read_text(encoding="utf-8")
        elif "local" in face:
            face["source"] = ",".join(
                "local(" + json.dumps(name) + ")" for name in face.pop("local")
            )
        else:
            raise ValueError("Font requires a packaged file or installed local face")
    return faces


def make_html(schema, output, runtime_js=None):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    assets = Path(__file__).resolve().parent.parent / "assets"
    config = assets / "runtime.json"
    runtime_url = json.loads(config.read_text())["url"] if config.exists() else RUNTIME
    if runtime_js:
        # Explicit local SDK keeps the preview independent of intranet CDN access.
        target = output.parent / "vinfo-runtime.js"
        if Path(runtime_js).resolve() != target:
            shutil.copyfile(runtime_js, target)
        runtime_url = target.name
    template = (assets / "page.html").read_text(encoding="utf-8")
    rendered = template.replace(
        "__TITLE__", html.escape(schema.get("meta", {}).get("name", "信息图"))
    )
    rendered = rendered.replace("__RUNTIME__", html.escape(runtime_url, quote=True)).replace(
        "__SCHEMA__", json_script(schema)
    )
    rendered = rendered.replace(
        "__FONTS__", json_script(embedded_fonts(assets, schema_font_families(schema)))
    )
    setup = assets / "render-setup.js"
    rendered = rendered.replace(
        "__RENDER_SETUP__", setup.read_text(encoding="utf-8") if setup.exists() else ""
    )
    output.write_text(rendered, encoding="utf-8")
    return output


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def export_png(html_path, output, browser_path=None):
    from playwright.sync_api import sync_playwright

    html_path, output = Path(html_path).resolve(), Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(html_path.parent))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            options = {"headless": True}
            if browser_path:
                options["executable_path"] = browser_path
            browser = pw.chromium.launch(**options)
            try:
                tab = browser.new_page(
                    viewport={"width": 1600, "height": 1000}, device_scale_factor=1
                )
                failures = []
                tab.on("requestfailed", lambda request: failures.append(request.failure))
                tab.on("pageerror", lambda error: failures.append(str(error)))
                tab.goto(
                    f"http://127.0.0.1:{server.server_port}/{html_path.name}",
                    wait_until="load",
                    timeout=60000,
                )
                tab.wait_for_function(
                    "window.__VINFO_READY__ || window.__VINFO_ERROR__", timeout=60000
                )
                error = tab.evaluate("window.__VINFO_ERROR__")
                if error:
                    raise RuntimeError(f"{error}; browser failures: {failures}")
                tab.locator("#page canvas").first.screenshot(path=str(output))
                return {"fonts": tab.evaluate("window.__VINFO_FONTS__ || []"), "png": str(output)}
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--png")
    parser.add_argument(
        "--runtime-js",
        help="Trusted UMD matching this skill's pinned SDK version; no dependency install occurs",
    )
    parser.add_argument("--browser", default=os.environ.get("CHROME_PATH"))
    args = parser.parse_args()
    result = make_html(
        json.loads(Path(args.schema).read_text(encoding="utf-8")), args.html, args.runtime_js
    )
    if args.png:
        export_png(result, args.png, args.browser)
    print(result)
