#!/usr/bin/env python3
"""Check self-contained, static magazine HTML and export each data-page to PNG."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

AUDIT = r"""() => {
  const errors = [];
  const pages = [...document.querySelectorAll('[data-page]')];
  if (!pages.length) errors.push('No [data-page] elements');
  if (document.querySelector('script,iframe,canvas,video,audio,object,embed'))
    errors.push('Use static HTML/SVG/images only; remove scripts or embedded runtime media');
  const fonts = [...document.fonts].map(f => ({family:f.family,status:f.status}));
  for (const f of fonts) if (f.status === 'error') errors.push('Font failed: '+f.family);
  const describe = el => el.tagName.toLowerCase()+(el.id?'#'+el.id:'')+' '+(el.textContent||'').trim().slice(0,45);
  const info = pages.map((page,index) => {
    const box = page.getBoundingClientRect(), style = getComputedStyle(page);
    if (page.parentElement.closest('[data-page]')) errors.push('Nested data-page');
    if (box.width < 1 || box.height < 1 || !Number.isInteger(box.width) || !Number.isInteger(box.height))
      errors.push(`Page ${index+1}: expected positive integer pixel dimensions`);
    if (style.transform !== 'none') errors.push(`Page ${index+1}: remove page transform`);
    if (!page.textContent.trim() && !page.querySelector('img,svg')) errors.push(`Page ${index+1}: empty`);
    const within = (a,b) => a.left >= b.left-1 && a.top >= b.top-1 && a.right <= b.right+1 && a.bottom <= b.bottom+1;
    // Content-image policy is explicit; decorative and explanatory SVG remain valid.
    for (const slot of page.querySelectorAll('[data-image-policy="raster"]')) {
      const images = slot.matches('img') ? [slot] : [...slot.querySelectorAll('img')];
      if (slot.matches('svg') || slot.querySelector('svg') || !images.length ||
          images.some(img => !/^data:image\/(png|jpe?g|webp|avif|gif);base64,/i.test(img.getAttribute('src') || ''))) {
        errors.push(`Page ${index+1}: content image requires acquired photo/generated illustration; replace SVG or missing asset`);
      }
    }
    for (const el of [page,...page.querySelectorAll('*')]) {
      if (el.closest('defs,title,desc,clipPath,mask,style')) continue;
      const css = getComputedStyle(el), r = el.getBoundingClientRect();
      if (css.display === 'none' || css.visibility === 'hidden' || (!r.width && !r.height)) continue;
      if (!within(r,box)) errors.push(`Page ${index+1}: outside page: ${describe(el)}`);
      const svg = el.ownerSVGElement;
      if (svg && !within(r,svg.getBoundingClientRect())) errors.push(`Page ${index+1}: outside SVG: ${describe(el)}`);
      // Visible font ascenders can exceed line-height without clipping copy.
      if (!svg && (el.scrollWidth > el.clientWidth+1 ||
          ((el === page || css.overflowY !== 'visible') && el.scrollHeight > el.clientHeight+1)) && css.display !== 'inline')
        errors.push(`Page ${index+1}: overflowing box: ${describe(el)}`);
      if (css.webkitLineClamp && css.webkitLineClamp !== 'none' && css.webkitLineClamp !== '0')
        errors.push(`Page ${index+1}: line clamp hides copy: ${describe(el)}`);
      if (el.tagName === 'IMG' && (!el.complete || !el.naturalWidth)) errors.push(`Page ${index+1}: broken image`);
      for (const child of el.childNodes) {
        if (child.nodeType !== Node.TEXT_NODE || !child.textContent.trim() || svg) continue;
        const range = document.createRange(); range.selectNodeContents(child);
        for (const rect of range.getClientRects()) {
          if (!within(rect,box)) errors.push(`Page ${index+1}: text outside page: ${describe(el)}`);
          if (css.overflow !== 'visible' && !within(rect,r)) errors.push(`Page ${index+1}: clipped text: ${describe(el)}`);
        }
      }
    }
    return {page:index+1,width:box.width,height:box.height,fontFamily:style.fontFamily};
  });
  return {pages:info,fonts,errors:[...new Set(errors)]};
}"""


def export(
    html: Path,
    output: Path,
    browser_path: str | None = None,
    font_mode: str = "auto",
    font_assets: Path | None = None,
    font_timeout: float = 20,
) -> dict:
    if font_mode not in ("auto", "offline", "system") or font_timeout <= 0:
        raise ValueError("Invalid font mode or timeout")
    html = html.resolve(strict=True)
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    report = {"ok": False, "pages": [], "errors": [], "externalRequests": []}
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            options = {"headless": True}
            if browser_path:
                options["executable_path"] = browser_path
            with pw.chromium.launch(**options) as browser:
                context = browser.new_context(
                    viewport={"width": 1600, "height": 1600},
                    device_scale_factor=1,
                    java_script_enabled=False,
                )

                def route_request(route):
                    request = route.request
                    if request.url == html.as_uri() and request.is_navigation_request():
                        route.continue_()
                    elif request.url.startswith("data:"):
                        route.continue_()
                    else:
                        report["externalRequests"].append(request.url)
                        route.abort()

                context.route("**/*", route_request)
                page = context.new_page()
                page.set_default_timeout(15000)
                page.goto(html.as_uri(), wait_until="load", timeout=30000)
                spec = importlib.util.spec_from_file_location(
                    "magazine_font_loading", Path(__file__).with_name("font_loading.py")
                )
                font_loader = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(font_loader)
                report["fontResolution"] = font_loader.resolve_fonts(
                    page,
                    context.request,
                    font_assets or Path(__file__).resolve().parent.parent / "assets",
                    font_mode,
                    font_timeout,
                )
                page.evaluate("""() => Promise.race([
                    Promise.all([document.fonts.ready,
                        ...[...document.images].map(i => i.decode().catch(() => {}))]),
                    new Promise((_, reject) => setTimeout(() => reject(Error('Resources timed out')), 15000))
                ])""")
                report.update(page.evaluate(AUDIT))
                if report["externalRequests"]:
                    report["errors"].append(
                        "External resources blocked; inline CSS, fonts and images"
                    )
                if report["errors"]:
                    raise ValueError("Layout/resource checks failed; see report.json")
                pages = page.locator("[data-page]")
                for index, meta in enumerate(report["pages"]):
                    filename = f"page-{index + 1:02d}.png"
                    pages.nth(index).screenshot(
                        path=str(output / filename), animations="disabled", timeout=30000
                    )
                    meta["file"] = filename
                # Freeze resolved fonts and status into the delivered static document.
                final_html = (
                    page.content() if report["fontResolution"] else html.read_text(encoding="utf-8")
                )
                context.close()
        (output / "magazine.html").write_text(final_html, encoding="utf-8")
        with zipfile.ZipFile(output / "images.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for meta in report["pages"]:
                archive.write(output / meta["file"], meta["file"])
        report["ok"] = True
    except Exception as exc:
        report["errors"].append(str(exc))
        # Never leave partial screenshots looking like a successful delivery.
        for path in output.glob("page-*.png"):
            path.unlink()
        for name in ("images.zip", "magazine.html"):
            (output / name).unlink(missing_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", help="Existing Chromium/Chrome executable")
    parser.add_argument("--font-mode", choices=["auto", "offline", "system"], default="auto")
    parser.add_argument(
        "--font-assets",
        type=Path,
        help="Optional assets directory containing fonts.json and licensed WOFF2",
    )
    parser.add_argument(
        "--font-timeout", type=float, default=20, help="Total CDN loading deadline in seconds"
    )
    args = parser.parse_args()
    try:
        report = export(
            args.html,
            args.output,
            args.browser,
            args.font_mode,
            args.font_assets,
            args.font_timeout,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
