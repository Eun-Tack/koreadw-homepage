"""Reproduce local browser screenshots, OG composition, and image checks."""
from pathlib import Path
import json
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
report = {"assets": [], "pages": []}
for asset in sorted((ROOT / "assets/illust").glob("method-*.png")):
    with Image.open(asset) as im:
        assert im.size == (800, 800), asset
        assert im.mode == "RGBA", asset
        alpha = im.getchannel("A")
        assert alpha.getextrema() == (0, 255), asset
        report["assets"].append({"file": str(asset.relative_to(ROOT)),
            "size": im.size, "bytes": asset.stat().st_size, "alpha_bbox": alpha.getbbox()})

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width":1200,"height":630}, device_scale_factor=1)
    page.goto((OUT / "og-composition.html").as_uri())
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(ROOT / "assets/og/og-image.png"))
    for width in (1440, 390, 320):
        page.set_viewport_size({"width":width,"height":960})
        page.goto((ROOT / "business/methods.html").as_uri(), wait_until="networkidle")
        for card in page.locator(".reveal").all():
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(150)
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.wait_for_timeout(700)
        assert page.evaluate("window.scrollY") == 0
        images = page.locator(".meth-illust").evaluate_all("(els)=>els.map(e=>({loaded:e.complete&&e.naturalWidth>0,width:e.width,height:e.height}))")
        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
        assert len(images) == 6 and all(x["loaded"] for x in images)
        assert not overflow, width
        page.screenshot(path=str(OUT / f"methods-{width}.png"), full_page=True)
        if width == 390:
            page.screenshot(path=str(OUT / "methods-mobile-top.png"))
        report["pages"].append({"width":width,"images":images,"horizontal_overflow":overflow})
    page.set_viewport_size({"width":1440,"height":960})
    page.goto((ROOT / "_artifact.html").as_uri()+"#/business/methods", wait_until="networkidle")
    embedded = page.locator('[data-page="business/methods"] .meth-illust')
    assert embedded.count() == 6
    assert embedded.evaluate_all("(els)=>els.every(e=>e.src.startsWith('data:image/png;base64,'))")
    report["artifact_embedded_images"] = embedded.count()
    page.set_viewport_size({"width":1200,"height":850})
    page.goto((OUT / "contact-sheet.html").as_uri())
    page.screenshot(path=str(OUT / "contact-sheet.png"), full_page=True)
    browser.close()
for name in ("og-bg.png", "og-image.png"):
    with Image.open(ROOT / "assets/og" / name) as im:
        assert im.size == (1200, 630)
        report["assets"].append({"file": "assets/og/"+name, "size": im.size,
                                "bytes": (ROOT / "assets/og" / name).stat().st_size})
for html in [ROOT/"index.html", *ROOT.glob("business/*.html"), *ROOT.glob("company/*.html"), *ROOT.glob("support/*.html")]:
    content = html.read_text(encoding="utf-8")
    assert 'content="https://www.koreadw.co.kr/assets/og/og-image.png"' in content, html
report["og_metadata"] = "All generated pages point to 1200x630 og-image.png"
(OUT / "checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
