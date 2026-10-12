"""Interaction and regression checks for the static site (Playwright required)."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote
from html.parser import HTMLParser
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--base", default=ROOT.as_uri()+"/")
parser.add_argument("--output", default=".review/interactions")
args = parser.parse_args()
out = ROOT/args.output
out.mkdir(parents=True, exist_ok=True)
summary = []

class References(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for k,v in attrs:
            if k in ("href", "src") and v:
                u = urlsplit(v)
                if not u.scheme and not u.netloc and u.path:
                    assert (self.source.parent/unquote(u.path)).is_file(), (self.source, v)

for source in [ROOT/"index.html", *ROOT.glob("company/*.html"), *ROOT.glob("business/*.html"), *ROOT.glob("support/*.html")]:
    check = References()
    check.source = source
    check.feed(source.read_text(encoding="utf-8"))
summary.append("All local HTML asset and navigation targets exist")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(reduced_motion="reduce")
    for width in (1440, 768, 390, 320):
        page.set_viewport_size({"width":width,"height":900})
        for path in ("index.html", "business/special.html"):
            page.goto(args.base.rstrip("/")+"/"+path)
            for tab in page.get_by_role("tab").all():
                tab.click()
                assert tab.get_attribute("aria-selected") == "true"
                assert page.get_by_role("tabpanel").count() == 1
                panel = page.get_by_role("tabpanel")
                assert panel.get_attribute("aria-labelledby") == tab.get_attribute("id")
                assert panel.evaluate("(e)=>e.scrollHeight<=e.clientHeight+1")
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            tabs = page.get_by_role("tab")
            tabs.first.focus()
            page.keyboard.press("ArrowRight")
            assert tabs.nth(1).get_attribute("aria-selected") == "true"
            page.keyboard.press("End")
            assert tabs.last.get_attribute("aria-selected") == "true"
            page.keyboard.press("Home")
            assert tabs.first.get_attribute("aria-selected") == "true"
            if width in (1440,390):
                page.locator(".deck").screenshot(path=str(out/f"example-{width}.png"))
        summary.append(f"{width}px: all 5 tabs work on both pages; keyboard and clipping checks pass")
        page.goto(args.base.rstrip("/")+"/company/people.html")
        for photo in page.locator(".person-photo").all():
            box = photo.bounding_box()
            assert abs(box["width"]/box["height"] - .75) < .01, box
        page.goto(args.base.rstrip("/")+"/company/organization.html")
        boxes = [node.bounding_box() for node in page.locator(".org-head > *").all()]
        for i,a in enumerate(boxes):
            for b in boxes[i+1:]:
                assert a["x"]+a["width"]<=b["x"] or b["x"]+b["width"]<=a["x"] or a["y"]+a["height"]<=b["y"] or b["y"]+b["height"]<=a["y"]
        if width < 1040:
            for entry, destination in (("company/greeting.html", "company/location.html"),
                                       ("business/fields.html", "business/process.html")):
                page.goto(args.base.rstrip("/")+"/"+entry)
                next_button = page.get_by_role("button", name="다음 메뉴 보기")
                for _ in range(6):
                    if next_button.is_disabled():
                        break
                    next_button.click()
                    page.wait_for_timeout(450)
                last = page.locator(".lnb-in a").last
                assert last.evaluate("(e)=>{const a=e.getBoundingClientRect(),b=e.parentElement.getBoundingClientRect();return a.left>=b.left-1&&a.right<=b.right+1}")
                last.click()
                assert page.url.endswith(destination)
            summary.append(f"{width}px: scrolled both submenu rows to the end and followed the final links")
            page.locator(".nav-toggle").click()
            assert page.locator(".nav-toggle").get_attribute("aria-expanded")=="true"
            contact = page.locator(".nav-contact")
            contact.scroll_into_view_if_needed()
            assert contact.is_visible()
            contact.click()
            assert page.url.endswith("support/contact.html")
            page.locator(".nav-toggle").click()
            page.keyboard.press("Escape")
            assert page.locator(".nav-toggle").get_attribute("aria-expanded")=="false"
            assert page.locator(".nav-toggle").evaluate("(e)=>e===document.activeElement")
            page.goto(args.base.rstrip("/")+"/business/process.html")
            current = page.locator(".lnb .is-active")
            assert current.evaluate("(e)=>{const a=e.getBoundingClientRect(),b=e.parentElement.getBoundingClientRect();return a.left>=b.left-1&&a.right<=b.right+1}")
        summary.append(f"{width}px: portrait ratios, organization chart, and navigation pass")
    page.goto(args.base.rstrip("/")+"/support/notice.html")
    assert page.locator(".notice-list a").count()==0
    summary.append("Notice list no longer presents self-links as article links")
    if args.base.startswith("file:"):
        page.goto((ROOT/"_artifact.html").as_uri()+"#/business/special")
        scope = page.locator('.vpage:not([hidden])')
        scope.get_by_role("tab").nth(2).click()
        assert scope.get_by_role("tabpanel").count()==1
        ids=page.locator("[id]").evaluate_all("(els)=>els.map(e=>e.id)")
        assert len(ids)==len(set(ids)), "Duplicate IDs in artifact"
        summary.append("Single-file preview tabs work and element IDs are unique")
    nojs = browser.new_context(java_script_enabled=False, viewport={"width":390,"height":900})
    fallback = nojs.new_page()
    fallback.goto(args.base.rstrip("/")+"/business/special.html")
    assert fallback.locator(".dcard:visible").count()==5
    assert fallback.locator(".chips").is_hidden()
    summary.append("All survey examples remain readable without JavaScript")
    browser.close()
(out/"checks.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("\n".join(summary))
