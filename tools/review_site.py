"""Capture every public page and check layout at desktop and phone widths."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "company/greeting.html", "company/history.html",
         "company/organization.html", "company/people.html", "company/location.html",
         "business/fields.html", "business/methods.html", "business/special.html",
         "business/platform.html", "business/process.html",
         "support/notice.html", "support/contact.html"]
parser = argparse.ArgumentParser()
parser.add_argument("--base", default=ROOT.as_uri()+"/")
parser.add_argument("--output", default=".review/local")
parser.add_argument("--widths", default="1440,390")
args = parser.parse_args()
out = ROOT / args.output
out.mkdir(parents=True, exist_ok=True)
results = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(reduced_motion="reduce", device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    for width in map(int, args.widths.split(",")):
        page.set_viewport_size({"width":width,"height":1000})
        for path in PAGES:
            errors.clear()
            response = page.goto(args.base.rstrip("/")+"/"+path, wait_until="load")
            page.evaluate("document.fonts.ready")
            for img in page.locator("main img").all():
                img.scroll_into_view_if_needed()
                img.evaluate("(el) => el.decode().catch(() => {})")
            for frame in page.locator("main iframe").all():
                frame.scroll_into_view_if_needed()
                page.wait_for_timeout(1200)
            page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
            page.wait_for_timeout(100)
            result = page.evaluate("""() => ({
              title:document.title,
              height:document.documentElement.scrollHeight,
              overflow:document.documentElement.scrollWidth>innerWidth,
              brokenImages:[...document.images].filter(e=>!e.complete||!e.naturalWidth).map(e=>e.src),
              text:document.querySelector('main').innerText,
              overflows:[...document.querySelectorAll('main *')].filter(e=>{
                const r=e.getBoundingClientRect();const s=getComputedStyle(e);
                return r.width>0 && (r.right>innerWidth+1||r.left< -1)&&s.position!=='absolute';
              }).slice(0,12).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.trim().slice(0,60)}))
            })""")
            result.update(path=path, width=width, status=response.status if response else None, errors=list(errors))
            name=path.replace("/", "-").replace(".html", "")
            page.screenshot(path=str(out/f"{name}-{width}.png"), full_page=True)
            results.append(result)
            print(json.dumps({k:result[k] for k in ["path","width","status","height","overflow","brokenImages","errors"]}), flush=True)
    browser.close()
(out/"report.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
failures = [r for r in results if r["overflow"] or r["brokenImages"] or r["errors"] or r["status"] not in (None, 200)]
if failures:
    raise SystemExit(f"{len(failures)} page/viewport checks failed; see report.json")
