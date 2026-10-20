"""Resolve declared Noto fonts before layout, then freeze them into static HTML."""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse

CDN = "https://miaoda.feishu.cn/fonts/css2"
FAMILIES = ("Noto Sans SC", "Noto Serif SC")
COLLECT = r"""families => {
  const found = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode, el = node.parentElement;
    if (!el?.closest('[data-page]') || el.closest('style,script,title,desc') || !node.textContent.trim()) continue;
    const css = getComputedStyle(el);
    if (css.display === 'none' || css.visibility === 'hidden') continue;
    const first = css.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, '');
    if (!families.includes(first)) continue;
    const key = first + '|' + css.fontWeight + '|' + css.fontStyle;
    if (!found.has(key)) found.set(key, {family:first,weight:css.fontWeight,style:css.fontStyle,text:''});
    found.get(key).text += node.textContent;
  }
  return [...found.values()].map(r => ({...r,text:[...new Set(r.text)].join('')}));
}"""
PARSE = r"""text => {
  const sheet = new CSSStyleSheet(); sheet.replaceSync(text);
  return [...sheet.cssRules].filter(r => r.type === CSSRule.FONT_FACE_RULE).map(r => {
    const get = n => r.style.getPropertyValue(n).trim();
    return {family:get('font-family').replace(/^["']|["']$/g,''), weight:get('font-weight')||'400',
      style:get('font-style')||'normal', unicodeRange:get('unicode-range'), src:get('src')};
  });
}"""
INSTALL = r"""async ({css,runs,timeout}) => {
  const before = new Set(document.fonts), tag = document.createElement('style');
  tag.dataset.magazineFonts = 'resolved'; tag.textContent = css; document.head.appendChild(tag);
  let timer;
  try {
    await Promise.race([Promise.all(runs.map(async r => {
      const faces = await document.fonts.load(`${r.style} ${r.weight} 24px "${r.family}"`, r.text);
      if (!faces.length || faces.some(f => f.status !== 'loaded')) throw Error('Font face unavailable');
    })), new Promise((_,reject) => {timer=setTimeout(() => reject(Error('Font decode timed out')), timeout);})]);
    return {ok:true};
  } catch(e) {
    // Remove both the stylesheet and its faces. No remote font remains to swap in late.
    tag.remove(); for (const face of document.fonts) if (!before.has(face)) document.fonts.delete(face);
    return {ok:false,reason:String(e)};
  } finally {clearTimeout(timer);}
}"""


def weight_matches(spec, weight):
    values = [int(x) for x in spec.split()]
    return min(values) <= int(weight) <= max(values)


def covers(ranges, text):
    if not ranges:
        return True
    chars = {ord(c) for c in text}
    for part in ranges.split(","):
        part = part.strip().upper().removeprefix("U+")
        if "?" in part:
            low, high = int(part.replace("?", "0"), 16), int(part.replace("?", "F"), 16)
        else:
            ends = part.split("-")
            low, high = int(ends[0], 16), int(ends[-1], 16)
        if any(low <= c <= high for c in chars):
            return True
    return False


def css_face(face, data):
    # Only known font descriptors enter the document, never the downloaded stylesheet.
    if face["family"] not in FAMILIES or not re.fullmatch(r"\d{1,4}(?: \d{1,4})?", face["weight"]):
        raise ValueError("Invalid font family/weight")
    if face["style"] not in ("normal", "italic", "oblique"):
        raise ValueError("Invalid font style")
    if face.get("unicodeRange") and not re.fullmatch(r"[Uu+0-9A-Fa-f?,\s-]+", face["unicodeRange"]):
        raise ValueError("Invalid unicode range")
    if data[:4] != b"wOF2":
        raise ValueError("Font response is not WOFF2")
    source = base64.b64encode(data).decode("ascii")
    rule = f'@font-face{{font-family:{json.dumps(face["family"])};font-weight:{face["weight"]};font-style:{face["style"]};font-display:block;src:url(data:font/woff2;base64,{source}) format("woff2");'
    if face.get("unicodeRange"):
        rule += "unicode-range:" + face["unicodeRange"] + ";"
    return rule + "}"


def local_faces(assets):
    manifest = assets / "fonts.json"
    if not manifest.exists():
        return []
    faces = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(faces, list):
        raise ValueError("fonts.json must be an array")
    result = []
    for raw in faces:
        face = dict(raw)
        for key in ("file", "licenseFile"):
            path = (assets / face[key]).resolve(strict=True)
            if not path.is_relative_to(assets.resolve()) or not path.is_file():
                raise ValueError("Font and license must be files inside font assets")
            face[key] = path
        if face["file"].suffix.lower() != ".woff2":
            raise ValueError("Local fonts must be WOFF2")
        face["weight"] = str(face.get("weight", "400"))
        face["style"] = face.get("style", "normal")
        face["unicodeRange"] = face.get("unicodeRange", "")
        face["license"] = face["licenseFile"].read_text(encoding="utf-8")
        if not face["license"].strip():
            raise ValueError("Font license must not be empty")
        result.append(face)
    return result


def get_bytes(request, url, deadline, limit=32 * 1024 * 1024):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError("Font resources must use HTTPS")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Font CDN timed out")
    response = request.get(
        url,
        timeout=max(1, int(remaining * 1000)),
        headers={"User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"},
    )
    try:
        if not response.ok:
            raise ValueError(f"Font HTTP {response.status}")
        data = response.body()
        if len(data) > limit:
            raise ValueError("Font resource exceeds size limit")
        return data
    finally:
        response.dispose()


def select_faces(faces, runs):
    return [
        f
        for f in faces
        if any(
            f["family"] == r["family"]
            and f["style"] == r["style"]
            and weight_matches(f["weight"], r["weight"])
            and covers(f.get("unicodeRange", ""), r["text"])
            for r in runs
        )
    ]


def require_weights(faces, runs):
    for run in runs:
        if not any(
            f["family"] == run["family"]
            and f["style"] == run["style"]
            and weight_matches(f["weight"], run["weight"])
            for f in faces
        ):
            raise ValueError(
                f"Required font weight/style unavailable: {run['weight']} {run['style']}"
            )


def resolve_fonts(page, request, assets, mode="auto", timeout=20):
    runs = page.evaluate(COLLECT, list(FAMILIES))
    if not runs:
        return []
    local = local_faces(assets) if mode != "system" else []
    records = []
    # One shared CDN deadline across all families, not 20s per shard/request.
    deadline = time.monotonic() + timeout
    for family in dict.fromkeys(r["family"] for r in runs):
        needed = [r for r in runs if r["family"] == family]
        base = {
            "family": family,
            "weights": sorted({r["weight"] for r in needed}),
            "glyphCount": len(set("".join(r["text"] for r in needed))),
        }
        existing = page.evaluate(
            'family => [...document.fonts].some(f => f.family.replace(/["\']/g, "") === family)',
            family,
        )
        if existing:
            # Already embedded delivery or user-owned face: do not fetch duplicates.
            page.evaluate(
                'async runs => {for(const r of runs) await document.fonts.load(`${r.style} ${r.weight} 24px "${r.family}"`,r.text)}',
                needed,
            )
            records.append({**base, "status": "loaded", "source": "existing-html"})
            continue
        failures = []
        chosen = None
        if mode == "auto":
            weights = sorted({int(r["weight"]) for r in needed})
            query = family + ":wght@" + ";".join(map(str, weights))
            url = CDN + "?" + urlencode({"family": query, "display": "swap"})
            try:
                css = get_bytes(request, url, deadline, 4 * 1024 * 1024).decode("utf-8")
                faces = select_faces(page.evaluate(PARSE, css), needed)
                if not faces:
                    raise ValueError("CDN returned no matching font faces")
                require_weights(faces, needed)
                license_text = (
                    Path(__file__).resolve().parent.parent
                    / "assets"
                    / (family.replace(" ", "") + "-OFL.txt")
                ).read_text(encoding="utf-8")
                cache, rules = {}, []
                for face in faces:
                    match = re.search(r'url\(\s*["\']?([^\s)"\']+)', face["src"])
                    if not match:
                        raise ValueError("CDN font source missing")
                    font_url = urljoin(url, match.group(1))
                    if font_url not in cache:
                        cache[font_url] = get_bytes(request, font_url, deadline)
                    rules.append(css_face(face, cache[font_url]))
                remaining = int((deadline - time.monotonic()) * 1000)
                if remaining <= 0:
                    raise TimeoutError("Font CDN timed out")
                result = page.evaluate(
                    INSTALL, {"css": "\n".join(rules), "runs": needed, "timeout": remaining}
                )
                if not result["ok"]:
                    raise ValueError(result["reason"])
                page.evaluate(
                    'text => {const m=document.createElement("meta");m.name="magazine-font-license";m.content=text;document.head.appendChild(m)}',
                    license_text,
                )
                chosen = {
                    **base,
                    "status": "loaded",
                    "source": "cdn",
                    "url": url,
                    "faces": len(faces),
                }
            except Exception as exc:
                failures.append("cdn: " + str(exc)[:350])
        if not chosen and mode != "system":
            try:
                faces = select_faces(local, needed)
                if not faces:
                    raise ValueError("No matching local WOFF2 configured")
                require_weights(faces, needed)
                rules = [css_face(f, f["file"].read_bytes()) for f in faces]
                result = page.evaluate(
                    INSTALL, {"css": "\n".join(rules), "runs": needed, "timeout": 20000}
                )
                if not result["ok"]:
                    raise ValueError(result["reason"])
                # Keep license text in safely serialized metadata, outside CSS.
                page.evaluate(
                    'items => {for(const text of items){const m=document.createElement("meta");m.name="magazine-font-license";m.content=text;document.head.appendChild(m)}}',
                    list(dict.fromkeys(f["license"] for f in faces)),
                )
                chosen = {**base, "status": "loaded", "source": "local-woff2"}
            except Exception as exc:
                failures.append("local: " + str(exc)[:350])
        records.append(
            chosen
            or {
                **base,
                "status": "fallback",
                "source": "system",
                "reason": "; ".join(failures) or "System fonts requested",
            }
        )
        if chosen and failures:
            records[-1]["fallbackReason"] = "; ".join(failures)
    page.evaluate(
        'records => {window.__MAGAZINE_FONTS__=records; const m=document.createElement("meta");m.name="magazine-font-status";m.content=JSON.stringify(records);document.head.appendChild(m)}',
        records,
    )
    return records
