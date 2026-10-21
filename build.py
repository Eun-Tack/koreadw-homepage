# -*- coding: utf-8 -*-
"""
(주)코리아데이터월드 홈페이지 정적 빌드 스크립트

  python build.py

  → web/index.html, web/company/*.html, web/business/*.html, web/support/*.html
    (배포용 정적 페이지 · 공통 헤더/푸터/네비게이션 자동 생성)
  → web/_artifact.html
    (전체 페이지를 한 파일에 합친 미리보기용. 해시 라우팅으로 메뉴 이동 가능)

콘텐츠는 아래 PAGES 리스트만 고치면 됩니다.
"""
import io
import datetime
import hashlib
import os
import re
import shutil
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))

# 배포 대상별 기준 주소.
#   og:url, og:image 처럼 절대 주소가 필요한 곳에만 쓰인다.
#   페이지끼리의 링크는 모두 상대 경로라 어디에 올려도 그대로 동작한다.
BASES = {
    "demo": "https://eun-tack.github.io/koreadw-homepage/",   # 기본값 · 시연용
    "prod": "https://www.koreadw.co.kr/",                     # 실제 납품용
}

SITE = {
    "name": "(주)코리아데이터월드",
    "name_short": "코리아데이터월드",
    "name_en": "KOREA DATA WORLD",
    "ceo": "김근지",
    "biz_no": "296-81-00459",
    "tel": "02-780-2273",
    "fax": "070-8800-2273",
    "email": "contact@koreadw.co.kr",
    "addr_seoul": "서울특별시 영등포구 국회대로72길 11, 309/310호",
    "addr_daegu": "대구광역시 달서구 달서대로 54, 503호",
    "tel_daegu": "053-636-2273",
    "site_url": "",   # 빌드할 때 BASES 에서 채운다
}


# ─────────────────────────────────────────────────────────────
# 콘텐츠 파일 로더
#   content/ 폴더의 텍스트 파일만 고치면 화면이 바뀐다.
#   빌드 스크립트를 열지 않고도 공지·연혁·연구원을 수정할 수 있게 하는 것이 목적.
# ─────────────────────────────────────────────────────────────
CONTENT = os.path.join(HERE, "content")


def _lines(name):
    """주석(#)과 빈 줄을 걷어낸 본문 줄만 돌려준다."""
    path = os.path.join(CONTENT, name)
    if not os.path.isfile(path):
        return []
    out = []
    for raw in io.open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _cells(line, count):
    """'a | b | c' 를 count 개 칸으로 맞춰 쪼갠다. 모자란 칸은 빈 문자열."""
    parts = [c.strip() for c in line.split("|")]
    parts += [""] * (count - len(parts))
    return parts[:count]


def load_notices():
    rows = []
    for line in _lines("notices.md"):
        date, tag, title, seq = _cells(line, 4)
        if not date or not title:
            continue
        rows.append((tag or None, esc(title), date, seq.strip()))
    return rows


def load_notice_posts():
    """content/notice-posts.md 의 본문. '=== 글번호' 로 글이 나뉜다.

       후이즈에서는 이 본문을 쓰지 않는다. 거기서는 고객이 관리자에서
       쓴 게시판 글이 그대로 나온다. 이 파일은 시연 사이트에서 같은
       화면을 보여 주기 위한 사본이다."""
    path = os.path.join(CONTENT, "notice-posts.md")
    if not os.path.isfile(path):
        return {}
    def norm(s):
        # 게시판에서 가져온 글에는 줄바꿈 없는 공백(\xa0)이 섞여 있다.
        # 본문과 링크 글자를 같은 기준으로 맞춰야 서로 짝이 맞는다.
        return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()

    posts, seq, cur = {}, None, None
    for raw in io.open(path, encoding="utf-8"):
        line = norm(raw.rstrip("\n"))
        if line.startswith("==="):
            seq = line[3:].strip()
            cur = {"body": [], "imgs": [], "links": []}
            posts[seq] = cur
            continue
        if cur is None or line.startswith("#"):
            continue
        if line.startswith("[사진]"):
            cur["imgs"].append(line[4:].strip())
        elif line.startswith("[링크]"):
            label, _, url = line[4:].partition("|")
            if url.strip():
                cur["links"].append((norm(label), url.strip()))
        elif line:
            cur["body"].append(line)
    return posts


def load_clients():
    """[분류] 아래에 '번호 | 기관명' 을 적는다."""
    groups, cur = [], None
    for line in _lines("clients.md"):
        if line.startswith("[") and line.endswith("]"):
            cur = (line[1:-1].strip(), [])
            groups.append(cur)
            continue
        num, name = _cells(line, 2)
        if not num or not name or cur is None:
            continue
        cur[1].append((num.zfill(2), esc(name)))
    return [g for g in groups if g[1]]


def clients_html():
    out = ['<div class="clients">']
    for title, items in load_clients():
        out.append('<div class="client-group reveal">')
        out.append('<h3 class="client-group-title">%s<span>%d</span></h3>' % (esc(title), len(items)))
        out.append('<ul class="client-grid">')
        for num, name in items:
            out.append(
                '<li><img src="{root}assets/clients/logo-%s.png" alt="%s" '
                'width="400" height="176" loading="lazy" decoding="async"><span>%s</span></li>'
                % (num, name, name))
        out.append('</ul></div>')
    out.append('</div>')
    return chr(10).join(out)


def attr(t):
    """HTML 속성값용. 엔티티로 바꾸지 않고 속성을 깨뜨리는 문자만 막는다."""
    return (t.replace("&", "&amp;").replace('"', "&quot;")
             .replace("<", "&lt;").replace(">", "&gt;"))


KIND_LABEL = {"사내": "사내", "인증": "인증 · 선정", "협약": "협약 · 위촉",
              "언론": "언론 보도", "활동": "대외 활동"}
KIND_ORDER = ["인증", "협약", "언론", "활동", "사내"]


def load_timeline():
    """연도 | 월일 | 분류 | 내용 | 설명 | 이미지"""
    years, index = [], {}
    for line in _lines("timeline.md"):
        year, when, kind, title, desc, img = _cells(line, 6)
        if not year or not title:
            continue
        if year not in index:
            index[year] = []
            years.append((year, index[year]))
        index[year].append((when, kind, title, desc, img))
    return years


def load_ongoing():
    out = []
    for line in _lines("ongoing.md"):
        title, body = _cells(line, 2)
        if title and body:
            out.append((title, body))
    return out


def timeline_html():
    """연혁 · 인증 · 협약 · 대외활동을 한 줄기로 보여 준다.
       세 블록으로 나눠 두니 같은 사실이 두세 곳에 겹쳐 적히던 문제가 있었다."""
    years = load_timeline()
    used = []
    for _y, items in years:
        for it in items:
            if it[1] and it[1] not in used:
                used.append(it[1])
    kinds = [k for k in KIND_ORDER if k in used]

    out = ['<div class="tl-filter" role="group" aria-label="분류별 보기">',
           '<button type="button" class="tl-chip is-on" data-kind="all" aria-pressed="true">전체</button>']
    for k in kinds:
        out.append('<button type="button" class="tl-chip" data-kind="%s" aria-pressed="false">%s</button>'
                   % (k, esc(KIND_LABEL.get(k, k))))
    out.append('</div>')

    out.append('<div class="tl reveal-group" data-timeline>')
    for year, items in years:
        out.append('<section class="tl-year reveal" data-year="%s">' % esc(year))
        out.append('<h3 class="tl-y"><b>%s</b><i>년</i></h3>' % esc(year))
        out.append('<ul>')
        for when, kind, title, desc, img in items:
            k = kind if kind in KIND_LABEL else "사내"
            body = ('<span class="tl-title">%s</span>' % esc(title))
            if desc:
                body += '<span class="tl-desc">%s</span>' % esc(desc)
            inner = ('<button type="button" class="tl-item is-link" '
                     'data-cert="{root}assets/credentials/%s" data-cert-label="%s">%s</button>'
                     % (img, attr(title), body)) if img else (
                     '<span class="tl-item">%s</span>' % body)
            out.append('<li data-kind="%s"><span class="tl-when">%s</span>'
                       '<span class="tl-kind k-%s">%s</span>%s</li>'
                       % (k, esc(when), k, esc(KIND_LABEL.get(k, k)), inner))
        out.append('</ul></section>')
    out.append('</div>')

    ong = load_ongoing()
    if ong:
        out.append('<div class="tl-ongoing">')
        for title, body in ong:
            out.append('<p><b>%s</b>%s</p>' % (esc(title), esc(body)))
        out.append('</div>')
    return chr(10).join(out)


def _is_future(year, when):
    """연혁의 '2026 | 11', '2026 | 10.31' 같은 표기를 오늘과 견준다.
       월만 있으면 그 달 1일로 본다."""
    try:
        y = int(str(year)[:4])
    except ValueError:
        return False
    nums = re.findall(r"\d+", str(when))
    m = int(nums[0]) if nums else 1
    d = int(nums[1]) if len(nums) > 1 else 1
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return False
    try:
        return datetime.date(y, m, d) > datetime.date.today()
    except ValueError:
        return False


def recent_news_html(limit=3):
    """첫 화면의 '최근 소식'.
       content/timeline.md 맨 위부터 가져오므로 한 줄만 추가하면 첫 화면이 바뀐다.
       사내 항목(창립 · 시스템 도입)은 대외로 보여 줄 소식이 아니라 건너뛴다.
       아직 오지 않은 날짜('인증 예정' 같은)는 소식이 아니므로 건너뛴다."""
    picks = []
    for year, items in load_timeline():
        for when, kind, title, desc, img in items:
            if kind == "사내":
                continue
            if _is_future(year, when):
                continue
            picks.append((year, when, kind, title, img))
            if len(picks) >= limit:
                break
        if len(picks) >= limit:
            break
    if not picks:
        return ""

    out = ['<div class="news">',
           '<div class="news-head">',
           '<span class="news-label">최근 소식</span>',
           '<a class="news-more" href="{root}company/history.html">전체 보기</a>',
           '</div>',
           '<div class="news-list">']
    for year, when, kind, title, img in picks:
        k = kind if kind in KIND_LABEL else "활동"
        inner = ('<span class="news-kind k-%s">%s</span>'
                 '<span class="news-title">%s</span>'
                 '<span class="news-when">%s. %s</span>'
                 % (k, esc(KIND_LABEL.get(k, k)), esc(title), esc(year), esc(when)))
        if img:
            out.append('<button type="button" class="news-card is-link" '
                       'data-cert="{root}assets/credentials/%s" data-cert-label="%s">%s</button>'
                       % (img, attr(title), inner))
        else:
            out.append('<div class="news-card">%s</div>' % inner)
    out.append('</div></div>')
    return chr(10).join(out)


def load_advisors():
    """[분야] 아래에 '이름 | 직함 | 소속' 을 적는다."""
    groups, cur = [], None
    for line in _lines("advisors.md"):
        if line.startswith("[") and line.endswith("]"):
            cur = (line[1:-1].strip(), []); groups.append(cur); continue
        name, title, org = _cells(line, 3)
        if not name or cur is None:
            continue
        cur[1].append((esc(name), esc(title), esc(org)))
    return [g for g in groups if g[1]]


def advisors_html():
    groups = load_advisors()
    total = sum(len(g[1]) for g in groups)
    out = ['<h3 class="minor-h story-h">분야별 자문위원<span class="count">%d명</span></h3>' % total,
           '<p class="note adv-note">각 분야 전문가로 구성된 자문위원이 과업 설계와 결과 검토에 참여합니다.</p>',
           '<div class="advisors reveal-group">']
    for field, people in groups:
        out.append('<div class="adv-group reveal">')
        out.append('<h4 class="adv-field">%s</h4><ul>' % field)
        for name, title, org in people:
            t = '<span class="adv-title">%s</span>' % title if title else ''
            o = '<span class="adv-org">%s</span>' % org if org else ''
            out.append('<li><b>%s</b>%s%s</li>' % (name, t, o))
        out.append('</ul></div>')
    out.append('</div>')
    return chr(10).join(out)


def load_people():
    people, cur = [], {}
    for line in _lines("people.md"):
        if line.startswith("---"):
            if cur:
                people.append(cur)
            cur = {}
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        cur[k.strip()] = v.strip()
    if cur:
        people.append(cur)
    return people


def esc(t):
    """콘텐츠 파일은 평문이므로 HTML 특수문자만 막아 준다."""
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # 작은따옴표는 여는/닫는 모양을 번갈아 준다 ('대구일보' → &lsquo;대구일보&rsquo;)
    out, open_q = [], True
    for ch in t:
        if ch == "'":
            out.append("&lsquo;" if open_q else "&rsquo;")
            open_q = not open_q
        else:
            out.append(ch)
    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 전역 메뉴
# ─────────────────────────────────────────────────────────────
MENU = [
    ("회사소개", "company", [
        ("greeting", "대표이사 인사말"),
        ("history", "연혁"),
        ("organization", "조직도"),
        ("people", "주요 연구진 프로필"),
        ("location", "오시는 길"),
    ]),
    ("사업소개", "business", [
        ("fields", "조사분야"),
        ("methods", "조사방법"),
        ("special", "특수 설문 유형"),
        ("platform", "설문 플랫폼"),
        ("process", "진행 절차"),
    ]),
    ("공지사항", "support", [
        ("notice", "공지사항"),
    ]),
]

# 페이지는 살아 있으나 상단 메뉴에는 넣지 않는다.
# 견적문의는 헤더 우측 '견적 문의' 버튼과 겹쳐 메뉴에서 제외한다.
# platform : 고객 요청으로 임시 비공개 (추후 보강 후 오픈)
NAV_HIDDEN = {"contact", "platform"}



# ─────────────────────────────────────────────────────────────
# 아이콘
#   24x24 선 아이콘. fill 없이 stroke 만 쓰므로 CSS 의 color 를 그대로 따라간다.
#   본문에 {ico:키} 라고 적으면 render_content 가 치환한다.
# ─────────────────────────────────────────────────────────────
ICONS = {
    # 조사분야
    "satisfaction": '<path d="M4 17a8 8 0 0 1 16 0"/><path d="M12 17l4.2-4.4"/><circle cx="12" cy="17" r="1.1"/>',
    "policy":       '<path d="M3.5 9.5 12 4.5l8.5 5"/><path d="M6 9.8v8M10 9.8v8M14 9.8v8M18 9.8v8"/><path d="M3.5 20.5h17"/>',
    "fact":         '<path d="M4.5 5.5h9M4.5 9.5h5.5"/><circle cx="13.5" cy="14" r="4.2"/><path d="M16.6 17.1 20.2 20.6"/>',
    "academic":     '<path d="M2.5 9 12 5l9.5 4-9.5 4z"/><path d="M6.5 11.2v4.3c0 1.4 2.5 2.5 5.5 2.5s5.5-1.1 5.5-2.5v-4.3"/><path d="M21.5 9v5.2"/>',
    # 설문 플랫폼
    "qtype":        '<circle cx="5" cy="6.5" r="1.8"/><rect x="3.2" y="11.2" width="3.6" height="3.6" rx="1"/><path d="M3.2 19.5h3.6"/><path d="M10 6.5h10.5M10 13h10.5M10 19.5h7"/>',
    "branch":       '<circle cx="5" cy="12" r="2"/><circle cx="19" cy="6.5" r="2"/><circle cx="19" cy="17.5" r="2"/><path d="M7 12h4.5V6.5H17"/><path d="M11.5 12v5.5H17"/>',
    "quota":        '<path d="M3 20.5h18"/><path d="M6.5 20.5V13M12 20.5V7.5M17.5 20.5V11"/><path d="M3 9.5h18" stroke-dasharray="2.4 2.6"/>',
    "qrlink":       '<rect x="3.5" y="3.5" width="6" height="6" rx="1.2"/><rect x="14.5" y="3.5" width="6" height="6" rx="1.2"/><rect x="3.5" y="14.5" width="6" height="6" rx="1.2"/><path d="M14.5 14.5h2.6M20.5 14.5v2.6M14.5 20.5h6M17.6 17.6h.01"/>',
    "aidoc":        '<path d="M13 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V9z"/><path d="M13 3.5V9h5.5"/><path d="M12 11.8l.95 2.25 2.25.95-2.25.95L12 18.2l-.95-2.25-2.25-.95 2.25-.95z"/>',
    "monitor":      '<rect x="2.5" y="4.5" width="19" height="12.5" rx="2"/><path d="M9 20.5h6M12 17v3.5"/><path d="M6.5 13.5 10 10l2.5 2.5L17 8"/>',
    # 진행 절차
    "consult":      '<path d="M20.5 12.3a7.3 7 0 0 1-7.3 7c-1.1 0-2.1-.2-3-.6l-5.7 1.3 1.6-4.1a7 7 0 0 1-.6-3.6 7.3 7 0 0 1 15 0z"/><path d="M9.7 12.3h.01M13.2 12.3h.01M16.7 12.3h.01"/>',
    "design":       '<path d="M15.5 20.5H5.5A1.5 1.5 0 0 1 4 19V5a1.5 1.5 0 0 1 1.5-1.5h9A1.5 1.5 0 0 1 16 5v5.2"/><path d="M7.5 8.2h5M7.5 12.2h3.8"/><path d="M19.6 12.4a1.55 1.55 0 0 1 2.2 2.2l-4.9 4.9-2.9.7.7-2.9z"/>',
    "confirm":      '<rect x="3.5" y="4" width="17" height="16.5" rx="2"/><path d="M7 9.6l1.6 1.6 3.4-3.3"/><path d="M14.5 10h3.3"/><path d="M7 15.8h10.8"/>',
    "field":        '<path d="M3.5 13.5h4l1.5 3h6l1.5-3h4"/><path d="M3.5 13.5v5a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-5"/><path d="M12 3.2v7.3M9 7.8l3 3 3-3"/>',
    "verify":       '<path d="M3.5 4.5h17l-6.8 8v7.4l-3.4-2.2V12.5z"/>',
    "deliver":      '<path d="M13 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V9z"/><path d="M13 3.5V9h5.5"/><path d="M12 11.8v5.4M9.6 14.8 12 17.2l2.4-2.4"/>',
}



# 조사방법 전용 아이콘. 생성 일러스트 도착 전까지 쓰는 선 아이콘.
ICONS.update({
    "f2f":  '<circle cx="7.5" cy="7" r="2.4"/><circle cx="16.5" cy="7" r="2.4"/>'
            '<path d="M3.2 15.5a4.3 4.3 0 0 1 8.6 0"/><path d="M12.2 15.5a4.3 4.3 0 0 1 8.6 0"/>'
            '<path d="M3.2 18.8h17.6"/>',
    "cati": '<path d="M8 3.6a7.5 7.5 0 0 0-3.5 6.3v3.6"/><path d="M19.5 13.5V9.9A7.5 7.5 0 0 0 16 3.6"/>'
            '<rect x="2.5" y="11.5" width="3.6" height="5.6" rx="1.5"/>'
            '<rect x="17.9" y="11.5" width="3.6" height="5.6" rx="1.5"/>'
            '<path d="M19.7 17.1v1.4a2 2 0 0 1-2 2h-3.4"/>',
    "web":  '<rect x="2.5" y="4" width="12.5" height="10.5" rx="1.8"/><path d="M2.5 7.4h12.5"/>'
            '<rect x="16.5" y="9" width="5" height="11" rx="1.6"/><path d="M18.4 17.8h1.2"/>'
            '<path d="M5.5 11l1.4 1.4 2.8-2.8"/>',
    "ars":  '<rect x="6" y="3.5" width="12" height="13" rx="2"/>'
            '<path d="M9.3 7h.01M12 7h.01M14.7 7h.01M9.3 10h.01M12 10h.01M14.7 10h.01M9.3 13h.01M12 13h.01M14.7 13h.01"/>'
            '<path d="M3 19.5v1.5M6.5 18v3M10 19v2M13.5 18v3M17 19.5v1.5M20.5 18.5v2.5"/>',
    "idi":  '<circle cx="6.5" cy="7.5" r="2.6"/><path d="M2.5 17a4 4 0 0 1 8 0"/>'
            '<path d="M12.5 5.5h8.5a.8.8 0 0 1 .8.8v6.2a.8.8 0 0 1-.8.8h-4.2l-3 2.4v-2.4h-1.3a.8.8 0 0 1-.8-.8V6.3a.8.8 0 0 1 .8-.8z"/>'
            '<path d="M15.5 9.4h.01M18 9.4h.01"/>',
    "fgi":  '<circle cx="12" cy="17" r="4.5"/>'
            '<circle cx="12" cy="4.5" r="2"/><circle cx="4.5" cy="10.5" r="2"/>'
            '<circle cx="19.5" cy="10.5" r="2"/>'
            '<path d="M12 6.5v2.3M6.2 11.7l2 1.6M17.8 11.7l-2 1.6"/>',
})


def ico(key):
    return ('<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">%s</svg>'
            % ICONS.get(key, ""))


# ─────────────────────────────────────────────────────────────
# 첫 화면 추상 비주얼
#   리서치 회사들의 첫 화면은 대형 타이포 + 추상 데이터 그래픽이 표준이다.
#   생성 이미지 대신 SVG 로 그려 색이 테마와 정확히 맞고 어느 화면에서도 선명하다.
# ─────────────────────────────────────────────────────────────
HERO_VIS = """
<svg class="hvis" viewBox="0 0 560 412" role="img" aria-label="조사 데이터를 형상화한 그래픽">
  <defs>
    <radialGradient id="hv-glow" cx="50%" cy="42%" r="58%">
      <stop offset="0%" stop-color="#2E7FB0" stop-opacity=".16"/>
      <stop offset="100%" stop-color="#2E7FB0" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="hv-bar" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0%" stop-color="#3A78C4"/>
      <stop offset="100%" stop-color="#24589C"/>
    </linearGradient>
  </defs>

  <circle cx="300" cy="186" r="226" fill="url(#hv-glow)"/>

  <!-- 응답 분포를 형상화한 도넛 -->
  <g transform="translate(300 182)">
    <circle r="118" fill="none" stroke="#DCE5F2" stroke-width="22"/>
    <circle r="118" fill="none" stroke="#24589C" stroke-width="22"
            stroke-linecap="round" stroke-dasharray="470 741"
            transform="rotate(-90)"/>
    <circle r="118" fill="none" stroke="#2E7FB0" stroke-width="22"
            stroke-linecap="round" stroke-dasharray="168 741"
            transform="rotate(140)"/>
    <circle r="78" fill="#FFFFFF"/>
    <circle r="78" fill="none" stroke="#EBF0F8"/>
    <g fill="none" stroke="#3A78C4" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
      <path d="M-34 16 L-12 -8 L8 6 L34 -22"/>
    </g>
    <g fill="#24589C">
      <circle cx="-34" cy="16" r="3.4"/><circle cx="-12" cy="-8" r="3.4"/>
      <circle cx="8" cy="6" r="3.4"/><circle cx="34" cy="-22" r="3.4"/>
    </g>
  </g>

  <!-- 표본 막대 -->
  <g transform="translate(62 206)">
    <rect x="0"  y="66" width="16" height="56"  rx="8" fill="url(#hv-bar)" opacity=".45"/>
    <rect x="24" y="40" width="16" height="82"  rx="8" fill="url(#hv-bar)" opacity=".65"/>
    <rect x="48" y="14" width="16" height="108" rx="8" fill="url(#hv-bar)" opacity=".85"/>
    <rect x="72" y="0"  width="16" height="122" rx="8" fill="url(#hv-bar)"/>
  </g>

  <!-- 5점 척도 : 한 줄 띠 위에 선택 지점을 표시한다 -->
  <g transform="translate(176 366)">
    <rect x="0" y="7" width="208" height="12" rx="6" fill="#E3EBF7"/>
    <rect x="0" y="7" width="128" height="12" rx="6" fill="#24589C" opacity=".22"/>
    <g fill="#FFFFFF" stroke="#C7D6EC" stroke-width="1.4">
      <circle cx="16" cy="13" r="7"/><circle cx="68" cy="13" r="7"/>
      <circle cx="172" cy="13" r="7"/><circle cx="208" cy="13" r="7"/>
    </g>
    <circle cx="124" cy="13" r="12" fill="#FFFFFF" stroke="#24589C" stroke-width="4"/>
  </g>

  <!-- 점 격자 -->
  <g fill="#C7D6EC">
    <circle cx="96"  cy="68"  r="3"/><circle cx="126" cy="68"  r="3"/><circle cx="156" cy="68"  r="3"/>
    <circle cx="96"  cy="98" r="3"/><circle cx="126" cy="98" r="3"/>
    <circle cx="470" cy="132" r="3"/><circle cx="500" cy="132" r="3"/>
    <circle cx="470" cy="162" r="3"/><circle cx="500" cy="162" r="3"/><circle cx="530" cy="162" r="3"/>
  </g>
</svg>
"""

# ─────────────────────────────────────────────────────────────
# 공통 컴포넌트
# ─────────────────────────────────────────────────────────────
DECK = """
<div class="chips" role="group" aria-label="특수 설문 유형 선택">
  <button class="chip" type="button" data-target="ce" aria-pressed="true">CE 선택실험법</button>
  <button class="chip" type="button" data-target="ahp" aria-pressed="false">AHP 쌍대비교</button>
  <button class="chip" type="button" data-target="cvm" aria-pressed="false">CVM 조건부가치측정</button>
  <button class="chip" type="button" data-target="delphi" aria-pressed="false">Delphi 전문가 합의</button>
  <button class="chip" type="button" data-target="custom" aria-pressed="false">맞춤형 설문</button>
</div>

<div class="deck">

  <div class="dcard is-active" data-key="ce">
    <div class="dcard-top"><span class="dcard-code">CE</span><span class="dcard-step">선택 세트 3 / 8</span></div>
    <h3>선택실험법</h3>
    <p class="dcard-sub">속성과 수준을 조합한 대안 중 하나를 고르게 하여, 지불의사와 속성별 중요도를 추정합니다.</p>
    <div class="dcard-screen">
      <p class="mq">다음 두 대안 중 어느 쪽을 선택하시겠습니까?</p>
      <div class="mrow">
        <div class="mopt sel"><b>대안 A</b><u>연회비 30,000원</u><u>대기 15분</u><u>대면 상담</u></div>
        <div class="mopt"><b>대안 B</b><u>연회비 12,000원</u><u>대기 40분</u><u>비대면 상담</u></div>
      </div>
      <div class="mopt">둘 다 선택하지 않겠습니다</div>
    </div>
    <p class="dcard-foot">출력 · 더미변수 Long Format</p>
  </div>

  <div class="dcard" data-key="ahp">
    <div class="dcard-top"><span class="dcard-code">AHP</span><span class="dcard-step">쌍대비교 6 / 15</span></div>
    <h3>쌍대비교법</h3>
    <p class="dcard-sub">두 항목을 9점 척도로 비교해 가중치를 산출하고, 응답 도중 일관성 비율을 바로 확인합니다.</p>
    <div class="dcard-screen">
      <p class="mq">두 평가기준 중 어느 쪽이, 얼마나 더 중요합니까?</p>
      <div class="mline"><span>접근성</span><span>전문성</span></div>
      <div class="mslider"><i></i></div>
      <div class="mticks"><span>9</span><span>5</span><span>1</span><span>5</span><span>9</span></div>
      <span class="mpill">CR 0.043 · 일관성 확보</span>
    </div>
    <p class="dcard-foot">산출 · 기준별 가중치 &amp; 우선순위</p>
  </div>

  <div class="dcard" data-key="cvm">
    <div class="dcard-top"><span class="dcard-code">CVM</span><span class="dcard-step">DBDC 1차 제시</span></div>
    <h3>조건부가치측정법</h3>
    <p class="dcard-sub">제시금액을 응답자별로 균등 배분하고, 응답에 따라 2차 금액으로 분기합니다.</p>
    <div class="dcard-screen">
      <p class="mq">이 사업의 시행을 위해 가구당 연간 15,000원을 추가 부담할 의향이 있습니까?</p>
      <div class="mrow">
        <div class="mopt sel"><u>예, 부담하겠다</u></div>
        <div class="mopt"><u>아니오</u></div>
      </div>
      <div class="mline"><span>예 → 2차 제시</span><span>30,000원</span></div>
      <div class="mline"><span>아니오 → 2차 제시</span><span>7,500원</span></div>
    </div>
    <p class="dcard-foot">출력 · 이중양분선택형 Long Format</p>
  </div>

  <div class="dcard" data-key="delphi">
    <div class="dcard-top"><span class="dcard-code">DELPHI</span><span class="dcard-step">2라운드 진행 중</span></div>
    <h3>전문가 합의법</h3>
    <p class="dcard-sub">라운드별 통계 요약을 응답 화면에 함께 보여 주어, 전문가가 의견을 조정할 근거를 제공합니다.</p>
    <div class="dcard-screen">
      <p class="mq">1라운드 결과입니다. 귀하의 응답을 유지하시겠습니까?</p>
      <dl class="mstat">
        <div><dt>평균</dt><dd>4.2</dd></div>
        <div><dt>IQR</dt><dd>0.8</dd></div>
        <div><dt>내 응답</dt><dd>3.0</dd></div>
      </dl>
      <span class="mpill warn">사분위 범위 밖 · 사유 기입 필요</span>
    </div>
    <p class="dcard-foot">추적 · 라운드별 의견 변화 이력</p>
  </div>

  <div class="dcard custom" data-key="custom">
    <div class="dcard-top"><span class="dcard-code">CUSTOM</span><span class="dcard-step">설계서 → 화면</span></div>
    <h3>맞춤형 설문</h3>
    <p class="dcard-sub">문항 구조와 출력 형식을 검토해 과제에 맞는 구현 방법을 제안합니다.</p>
    <div class="dcard-screen">
      <p class="custom-kicker">연구계획서에 있는 그 문항,<br>화면으로 만들어 드립니다.</p>
      <ul class="custom-list">
        <li>컨조인트 · BWS · 순위형 배분</li>
        <li>조건부 분기가 여러 겹인 스크리너</li>
        <li>실험 처치군 무작위 배정 설계</li>
        <li>기관 고유 양식의 응답 화면</li>
      </ul>
    </div>
    <p class="dcard-foot">자문 · 방법론 검토부터 함께</p>
  </div>

</div>
"""

NOTICES = load_notices()
NOTICE_POSTS = load_notice_posts()


def notice_rows(limit=None):
    """limit 이 있으면 첫 화면용 짧은 목록(공지 페이지로 보냄),
       없으면 공지 페이지의 전체 목록(글마다 본문으로 보냄)."""
    rows = NOTICES[:limit] if limit else NOTICES
    out = []
    for tag, title, date, seq in rows:
        badge = '<span class="notice-tag">%s</span>' % (tag or "소식")
        if limit:
            title_html = '<a href="{href}">%s%s</a>' % (badge, title)
        elif seq and seq in NOTICE_POSTS:
            title_html = ('<a href="{root}support/notice/%s.html">%s%s</a>'
                          % (seq, badge, title))
        else:
            title_html = '<span class="notice-title">%s%s</span>' % (badge, title)
        out.append('<li>%s<time datetime="%s">%s</time></li>'
                   % (title_html, date, date.replace("-", ".")))
    return "\n".join(out)


OFFICES = """
<div class="offices reveal-group">
  <div class="office">
    <h3>서울 본사<span>SEOUL</span></h3>
    <dl>
      <dt>주소</dt><dd>{addr_seoul}</dd>
      <dt>전화</dt><dd><a href="tel:{tel}">{tel}</a></dd>
      <dt>팩스</dt><dd>{fax}</dd>
    </dl>
  </div>
  <div class="office">
    <h3>대구 지점<span>DAEGU</span></h3>
    <dl>
      <dt>주소</dt><dd>{addr_daegu}</dd>
      <dt>전화</dt><dd><a href="tel:{tel_daegu}">{tel_daegu}</a></dd>
      <dt>팩스</dt><dd>{fax}</dd>
    </dl>
  </div>
</div>
"""


# 첫 화면에 있던 설문 목업. 설문 플랫폼 페이지를 다시 열 때 쓰려고 남겨 둔다.
# (고객 요청 1008-9: "첫화면에 있는 플랫폼 관련 이미지는 이곳에서 활용")
VIS_DECK = """
<div class="vis-deck" aria-hidden="true">
      <span class="vis-caption">설문 화면 예시</span>
      <div class="vis-card vis-a">
        <span class="vis-tag">Q7 / LIKERT 5점</span>
        <p class="vis-q">제공받은 서비스에 전반적으로 얼마나 만족하십니까?</p>
        <div class="scale"><i>1</i><i>2</i><i>3</i><i class="on">4</i><i>5</i></div>
      </div>
      <div class="vis-card vis-b">
        <span class="vis-tag">실시간 응답 현황</span>
        <div class="bars">
          <div class="bar"><span>서울권</span><span class="bar-track"><span class="bar-fill" style="width:86%"></span></span><span class="bar-val">86%</span></div>
          <div class="bar"><span>경상권</span><span class="bar-track"><span class="bar-fill" style="width:71%"></span></span><span class="bar-val">71%</span></div>
          <div class="bar"><span>호남권</span><span class="bar-track"><span class="bar-fill" style="width:54%"></span></span><span class="bar-val">54%</span></div>
        </div>
      </div>
      <div class="vis-card vis-c">
        <span class="vis-tag">쿼터 · 목표 표본</span>
        <div class="bars">
          <div class="bar"><span>20~39세</span><span class="bar-track"><span class="bar-fill done" style="width:100%"></span></span><span class="bar-val">달성</span></div>
          <div class="bar"><span>40~59세</span><span class="bar-track"><span class="bar-fill" style="width:63%"></span></span><span class="bar-val">63%</span></div>
        </div>
      </div>
    </div>
"""

# ─────────────────────────────────────────────────────────────
# 페이지 콘텐츠
# ─────────────────────────────────────────────────────────────
PAGES = []


def page(key, path, group, nav_title, title, desc, content, sub="", hero=None,
         lnb_key=None, h1=None):
    PAGES.append(dict(key=key, path=path, group=group, nav_title=nav_title,
                      title=title, desc=desc, content=content, sub=sub, hero=hero,
                      lnb_key=lnb_key or key, h1=h1 or title))


# ── 메인 ──────────────────────────────────────────────────────
MAIN = """
<section class="hero">
  <div class="hero-bg" aria-hidden="true"></div>
  <div class="wrap hero-in">
    <div class="hero-copy">
      <span class="eyebrow">SURVEY &middot; RESEARCH &middot; CONSULTING</span>
      <h1>데이터의 확보와 분석으로<br><span class="hl">고객의 현안을 해결합니다.</span></h1>
      <p class="lede">
        (주)코리아데이터월드는 만족도·정책수요·실태·학술연구 조사를 수행하는 리서치 전문기업입니다.
        조사 설계와 자료 수집부터 분석·보고서까지, 의사결정에 필요한 근거를 함께 만듭니다.
      </p>
      <div class="hero-cta">
        <a class="btn btn-primary btn-lg" href="{root}support/contact.html">조사 의뢰 &middot; 견적 문의</a>
        <a class="btn btn-ghost btn-lg" href="{root}business/special.html">특수 설문 유형 보기</a>
      </div>
    </div>

    <div class="hero-vis" aria-hidden="false">{HEROVIS}</div>
  </div>

  <div class="wrap news-wrap">{RECENT}</div>

</section>

<section class="sec">
  <div class="wrap">
    <div class="sec-head center reveal reveal-group">
      <span class="eyebrow">조사분야</span>
      <h2>조사 목적에 맞는 네 가지 전문 분야</h2>
      <p class="lede">조사 목적이 다르면 표본, 문항 구조, 산출 지표가 모두 달라집니다. 영역별로 필요한 결과물의 형태부터 확인하고 시작합니다.</p>
    </div>
    {FIELDS}
    <p class="sec-more">
      <a class="link-more" href="{root}business/fields.html">조사분야 자세히 보기</a>
      <a class="link-more" href="{root}business/methods.html">조사방법 보기</a>
    </p>
  </div>
</section>

<section class="sec band">
  <div class="wrap">
    <div class="band-head">
      <div>
        <span class="eyebrow">특수 설문 유형</span>
        <h2>복잡한 연구 설계도<br>응답하기 쉬운 설문으로.</h2>
        <p class="lede">
          선택실험(CE), 쌍대비교(AHP), 조건부가치측정(CVM), 전문가 합의(Delphi).
          연구 방법론이 요구하는 화면과 출력 형식을 그대로 구현합니다.
        </p>
      </div>
      <p class="band-note">
        방법론마다 <b>응답자가 보는 화면</b>과 <b>분석에 넘겨야 할 데이터 형식</b>이 다릅니다.
        자체 플랫폼에서 문항 구조와 분석에 필요한 데이터 형식을 함께 설계합니다.
      </p>
    </div>
    {DECK}
    <p class="sec-more"><a class="link-more" href="{root}business/special.html">특수 설문 유형 전체 보기</a></p>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="sec-head center reveal reveal-group">
      <span class="eyebrow">자체 설문 플랫폼</span>
      <h2>조사 설계부터 원시데이터 납품까지, 한 곳에서.</h2>
      <p class="lede">문항 구성, 응답자 관리, 실시간 모니터링을 자체 플랫폼에서 연결합니다. 과제별 요구사항에 맞춰 설문 화면과 납품 형식을 조정합니다.</p>
    </div>
    {PLATFORM}
  </div>
</section>

<section class="sec band">
  <div class="wrap">
    <div class="sec-head center reveal reveal-group">
      <span class="eyebrow">주요 클라이언트</span>
      <h2>공공기관과 대학이 맡겨온 조사입니다.</h2>
      <p class="lede">국책·지자체 연구기관, 지방자치단체, 대학, 기업까지 다양한 현장에서 조사를 수행해 왔습니다.</p>
    </div>
    {CLIENTS}
    <p class="client-note reveal">
      코리아데이터월드는 <b>과업 완료 후 외부고객 만족도 조사</b>를 실시하고 있습니다.
    </p>
  </div>
</section>

<section class="sec">
  <div class="wrap two">
    <div>
      <div class="sec-head sm">
        <span class="eyebrow">공지사항</span>
        <h2>새 소식</h2>
      </div>
      <ul class="notice-list">
        {NOTICES5}
      </ul>
      <p class="sec-more left"><a class="link-more" href="{root}support/notice.html">전체 공지 보기</a></p>
    </div>
    <div>
      <div class="sec-head sm">
        <span class="eyebrow">오시는 길</span>
        <h2>서울 본사 · 대구 지점</h2>
      </div>
      {OFFICES}
    </div>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    {CTA}
  </div>
</section>
"""

FIELDS_GRID = """
<div class="fields reveal-group">
  <article class="field reveal">
    <span class="field-ico">{ico:satisfaction}</span>
    <span class="field-k">01 &nbsp;SATISFACTION</span>
    <h3>만족도 조사</h3>
    <ul>
      <li>공공기관, 대학교 만족도 조사</li>
      <li>내부·외부 고객이 서비스에 얼마나 만족하고 있는지 파악해, 개선이 필요한 지점을 찾아내는 조사입니다.</li>
    </ul>
  </article>
  <article class="field reveal">
    <span class="field-ico">{ico:policy}</span>
    <span class="field-k">02 &nbsp;POLICY DEMAND</span>
    <h3>정책 수요 조사</h3>
    <ul>
      <li>공공기관, 국책연구기관 정책 수요 조사</li>
      <li>정책을 수립하고 결정하는 단계에서 대상자의 현안 인식을 확인하고 의견을 수렴해, 근거 자료로 활용합니다.</li>
    </ul>
  </article>
  <article class="field reveal">
    <span class="field-ico">{ico:fact}</span>
    <span class="field-k">03 &nbsp;FACT-FINDING</span>
    <h3>실태 조사</h3>
    <ul>
      <li>공공기관 및 지자체 실태조사</li>
      <li>대상 집단이 처한 현재 상황과 문제점을 확인하고, 이를 근거로 개선 방안을 도출하는 조사입니다.</li>
    </ul>
  </article>
  <article class="field reveal">
    <span class="field-ico">{ico:academic}</span>
    <span class="field-k">04 &nbsp;ACADEMIC</span>
    <h3>학술 연구 조사</h3>
    <ul>
      <li>교수, 대학원생·학부생 학술 연구 조사</li>
      <li>연구기관·대학의 개인 연구과제나 논문 작성에 필요한 자료를 수집·분석해, 연구의 실증 근거로 활용합니다.</li>
    </ul>
  </article>
</div>
"""

PLATFORM_GRID = """
<div class="plat reveal-group">
  <article class="plat-item reveal">
    <span class="plat-top"><span class="plat-ico">{ico:qtype}</span><span class="plat-n">01</span></span>
    <h3>문항 유형 13종</h3>
    <p>단일·복수선택, 척도, 리커트, 매트릭스, 순위, 숫자, 단답, 서술, 휴대전화 인증, 섹션 구분까지 조사 현장에서 실제로 쓰는 유형을 모두 지원합니다.</p>
  </article>
  <article class="plat-item reveal">
    <span class="plat-top"><span class="plat-ico">{ico:branch}</span><span class="plat-n">02</span></span>
    <h3>분기 로직 · 스크리너</h3>
    <p>앞선 응답에 따라 뒤 문항을 건너뛰거나 다른 문항으로 이동시키고, 조사 대상 조건에 맞지 않으면 그 자리에서 응답을 종료합니다.</p>
  </article>
  <article class="plat-item reveal">
    <span class="plat-top"><span class="plat-ico">{ico:quota}</span><span class="plat-n">03</span></span>
    <h3>쿼터 관리</h3>
    <p>성별·연령·지역 등 집단별 목표 응답 수를 정해 두면 실시간으로 집계하고, 목표를 채운 집단은 자동으로 마감합니다.</p>
  </article>
  <article class="plat-item reveal">
    <span class="plat-top"><span class="plat-ico">{ico:qrlink}</span><span class="plat-n">04</span></span>
    <h3>개인 링크 · QR 발급</h3>
    <p>응답자마다 고유 URL과 QR코드를 발급합니다. 응답 도중 창을 닫아도 이어서 작성할 수 있습니다.</p>
  </article>
  <article class="plat-item reveal">
    <span class="plat-top"><span class="plat-ico">{ico:aidoc}</span><span class="plat-n">05</span></span>
    <h3>AI 문서 변환</h3>
    <p>HWPX·PDF 설문지를 올리면 AI가 문항을 읽어 유형별로 분류하고 초안을 만들어 둡니다. 담당자는 검토와 수정만 하면 됩니다.</p>
  </article>
  <article class="plat-item reveal">
    <span class="plat-top"><span class="plat-ico">{ico:monitor}</span><span class="plat-n">06</span></span>
    <h3>모니터링 · 데이터 납품</h3>
    <p>응답 수와 완료율을 실시간으로 확인하고, 원시데이터를 XLSX·CSV로 내려받을 수 있습니다. 분석에 쓰실 코딩북도 함께 정리해 드립니다.</p>
  </article>
</div>
"""

CTA_TPL = """
<div class="cta">
  <div>
    <span class="eyebrow">{EYEBROW}</span>
    <h2>{HEAD}</h2>
    <p class="lede sm">{LEAD}</p>
    <div class="hero-cta">
      <a class="btn btn-primary" href="mailto:{email}">메일로 문의하기</a>
      <a class="btn btn-ghost" href="tel:{tel}">{tel}</a>
    </div>
  </div>
  <dl class="cta-lines">
    <div><dt>전화</dt><dd><b>{tel}</b></dd></div>
    <div><dt>팩스</dt><dd><b>{fax}</b></dd></div>
    <div><dt>이메일</dt><dd><b>{email}</b></dd></div>
    <div><dt>운영시간</dt><dd><b>평일 10:00 – 18:00</b></dd></div>
  </dl>
</div>
"""


def cta(eyebrow, head, lead):
    return (CTA_TPL.replace("{EYEBROW}", eyebrow)
                   .replace("{HEAD}", head)
                   .replace("{LEAD}", lead))


# 메인 하단: 아직 결정을 안 한 방문자를 움직이는 문구
CTA = cta("견적 문의",
          "조사 목적만 알려주시면,<br>설계부터 같이 시작합니다.",
          "문항이 아직 확정되지 않아도 괜찮습니다. 무엇을 알고 싶으신지, 그 결과를 어디에 쓰실지부터 말씀해 주세요.")

# 견적문의 페이지: 이미 같은 말이 페이지 제목에 있으므로 '연락 수단' 안내로 역할을 나눈다
CTA_CONTACT = cta("연락처",
                  "편하신 방법으로<br>연락 주세요.",
                  "메일로 보내주시면 문의 내용을 정리해 담당 연구원이 회신드립니다. 급하신 건은 전화로 말씀해 주세요.")

page("home", "index.html", None, "홈", "코리아데이터월드",
     "(주)코리아데이터월드 — 만족도·정책수요·실태·학술연구 조사와 CE·AHP·CVM·Delphi 특수 설문을 직접 구현하는 리서치 전문기업",
     MAIN)

# ── 회사소개 ──────────────────────────────────────────────────
page("greeting", "company/greeting.html", "company", "대표이사 인사말",
     "대표이사 인사말", "코리아데이터월드 대표이사 인사말",
     """
<div class="greet">
  <figure class="greet-photo">
    <img src="{root}assets/people/ceo-greeting.jpg" alt="(주)코리아데이터월드 대표이사 김근지" width="480" height="640">
    <figcaption>(주)코리아데이터월드 대표이사 <b>김근지</b></figcaption>
  </figure>
  <div class="prose">
    <p class="prose-lead">안녕하십니까?<br>(주)코리아데이터월드 대표이사 김근지입니다.</p>
    <p>
      저는 2007년 리서치 회사에서 리서치 연구원으로 시작해,
      창업 10년을 맞은 2026년 지금까지 20년간 조사 현장에서 일해 왔습니다.
    </p>
    <p>
      (주)코리아데이터월드는 정부기관, 지자체, 공공기관, 연구기관, 대학, 기업 등과 함께
      다양한 과업을 수행하고 있습니다.
    </p>
    <p>
      과업마다 최적의 방법을 찾아 데이터를 확보하고 분석하여,
      고객이 바라는 연구 성과, 정책 개발, 매출 향상에 기여하고자 합니다.
    </p>
    <blockquote>
      신뢰할 수 있는 데이터와 통찰력 있는 분석을 위해,
      설문 설계의 완결성, 데이터 수집의 윤리성, 분석의 전문성
      무엇 하나 놓치지 않고 철저히 지키고 있습니다.
    </blockquote>
    <p>
      항상 고객의 입장에서 생각하며,
      다음 과업에서도 함께할 수 있는 파트너가 되겠습니다. 감사합니다.
    </p>
  </div>
</div>
""",
     sub="데이터로 고객의 현안을 푸는 일을 합니다.")

page("history", "company/history.html", "company", "연혁",
     "연혁", "코리아데이터월드 연혁 · 인증 · 협약 · 대외활동",
     timeline_html(),
     sub="2016년 창립 이후 걸어온 길입니다. 분류를 눌러 나눠 볼 수 있습니다.")

page("organization", "company/organization.html", "company", "조직도",
     "조직도", "코리아데이터월드 조직도",
     """
<div class="org">
  <div class="org-head">
    <span class="org-advisor advisor-left">분야별 자문위원</span>
    <span class="org-node lead">대표이사</span>
    <span class="org-advisor advisor-right">경영지원팀</span>
  </div>
  <div class="org-row">
    <div class="org-col">
      <span class="org-node">연구팀</span>
      <div class="org-leaf"><span>공공분야</span><span>마케팅분야</span></div>
    </div>
    <div class="org-col">
      <span class="org-node">분석팀</span>
      <div class="org-leaf"><span>QC팀</span><span>통계분석</span></div>
    </div>
    <div class="org-col">
      <span class="org-node">실사팀</span>
      <div class="org-leaf"><span>서울 본사</span><span>대구 지점</span></div>
    </div>
    <div class="org-col">
      <span class="org-node">부설연구소</span>
    </div>
  </div>
</div>
""" + advisors_html(), sub="연구·분석·실사 조직이 함께 과제를 수행합니다.")

def people_html():
    """대표 1장을 위에 가로로, 나머지를 아래 한 줄로.
       구분 라벨(연구 책임자/실무 연구진)은 고객 요청(1015)으로 넣지 않는다."""
    rows = load_people()
    lead = [r for r in rows if r.get("대표") == "예"]
    rest = [r for r in rows if r.get("대표") != "예"]

    def card(pr, is_lead):
        o = ['<article class="person%s reveal">' % (" lead-person" if is_lead else "")]
        o.append('<h3>%s<small>%s</small></h3>'
                 % (esc(pr.get("이름", "")), esc(pr.get("직책", ""))))
        o.append('<dl class="person-meta">')
        for label in ("리서치경력", "이력", "대외", "학력"):
            if pr.get(label):
                val = "<br>".join(x.strip() for x in esc(pr[label]).split(" / "))
                o.append('<div><dt>%s</dt><dd>%s</dd></div>' % (label, val))
        o.append('</dl>')
        if pr.get("자격"):
            certs = [c.strip() for c in pr["자격"].split(" / ")]
            files = [f.strip() for f in pr.get("자격파일", "").split(" / ") if f.strip()]
            chips = []
            for n, name in enumerate(certs):
                if n < len(files):
                    chips.append(
                        '<button type="button" class="person-cert is-link" '
                        'data-cert="{root}assets/certs/%s" '
                        'data-cert-label="%s %s">%s</button>'
                        % (files[n], esc(pr.get("이름", "")), esc(name), esc(name)))
                else:
                    chips.append('<span class="person-cert">%s</span>' % esc(name))
            o.append('<div class="person-certs"><dt>보유자격증</dt><div>%s</div></div>'
                     % "".join(chips))
        o.append('</article>')
        return chr(10).join(o)

    out = []
    if lead:
        out.append('<div class="people people-lead reveal-group">')
        out.append(card(lead[0], True))
        out.append('</div>')
    if rest:
        out.append('<div class="people people-rest reveal-group">')
        for pr in rest:
            out.append(card(pr, False))
        out.append('</div>')
    out.append('<p class="note">※ 자격증을 누르면 원본을 볼 수 있습니다. '
               '자격번호와 생년월일은 개인정보 보호를 위해 가려 두었습니다.</p>')
    return chr(10).join(out)


page("people", "company/people.html", "company", "주요 연구진 프로필",
     "주요 연구진 프로필", "코리아데이터월드 주요 연구진 소개",
     """
<p class="deck-intro">
  조사 설계부터 분석까지 함께하는 연구진입니다.
  <b>연구팀장 전원이 사회조사분석사 2급 자격증을 보유</b>하고 있습니다.
</p>
""" + people_html(),
     sub="조사와 분석을 수행하는 연구진을 소개합니다.")

def office_maps():
    offices = (
        ("서울 본사", SITE["addr_seoul"], SITE["tel"]),
        ("대구 지점", SITE["addr_daegu"], SITE["tel_daegu"]),
    )
    parts = ['<div class="office-maps">']
    for name, address, phone in offices:
        query = quote(address.split(",")[0])
        parts.append("""
<article class="office-map">
  <div class="office-map-info">
    <h2>%s</h2>
    <p class="office-map-address">%s</p>
    <a class="office-map-phone" href="tel:%s">%s</a>
    <div class="map-actions">
      <a class="btn btn-primary" href="https://map.naver.com/p/search/%s" target="_blank" rel="noopener noreferrer">네이버 지도<span class="sr-only"> (새 창)</span></a>
      <a class="btn btn-ghost" href="https://www.google.com/maps/dir/?api=1&amp;destination=%s" target="_blank" rel="noopener noreferrer">길찾기<span class="sr-only"> (새 창)</span></a>
    </div>
  </div>
  <iframe class="office-map-frame" title="%s 위치 지도" src="https://www.google.com/maps?q=%s&amp;z=16&amp;output=embed&amp;hl=ko" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>
</article>""" % (name, address, phone, phone, query, query, name, query))
    parts.append("</div>")
    return "".join(parts)


page("location", "company/location.html", "company", "오시는 길",
     "오시는 길", "코리아데이터월드 서울 본사 · 대구 지점 위치 안내",
     office_maps() + """
<div class="prose sm">
  <p>방문 상담을 원하시면 전화나 메일로 미리 일정을 잡아 주세요. 담당 연구원이 자료를 준비해 두고 맞이하겠습니다.</p>
</div>
""", sub="서울 본사와 대구 지점의 위치 및 방문 경로를 안내합니다.")

# ── 사업소개 ──────────────────────────────────────────────────
page("fields", "business/fields.html", "business", "조사분야",
     "조사분야", "만족도 · 정책수요 · 실태 · 학술연구 조사",
     FIELDS_GRID + """
<div class="callout reveal">
  <h3>조사 목적에 맞는 방법을 함께 찾습니다</h3>
  <p>
    실제 과제는 만족도와 실태, 정책수요가 섞여 있는 경우가 대부분입니다.
    무엇을 알고 싶으신지, 그 결과를 어디에 쓰실지만 알려주시면 그에 맞는 조사 형태를 저희가 정리해 제안드립니다.
  </p>
  <a class="btn btn-primary" href="{root}support/contact.html">조사 상담 요청</a>
</div>
""",
     sub="조사 목적이 다르면 표본, 문항 구조, 산출 지표가 모두 달라집니다.")

page("methods", "business/methods.html", "business", "조사방법",
     "조사방법", "면접 · 전화 · 온라인 · ARS 정량조사와 IDI · FGI 정성조사",
     """
<p class="deck-intro">
  조사 목적과 대상, 일정과 예산에 따라 적합한 방법이 달라집니다.
  <b>코리아데이터월드가 직접 수행하는 조사방법</b>은 다음과 같습니다.
</p>

<h3 class="minor-h">정량조사</h3>
<div class="meth reveal-group">
  <article class="meth-item reveal">
    <img class="meth-illust method-f2f" src="{root}assets/illust/method-f2f.png" alt="" width="800" height="800" loading="lazy" decoding="async">
    <span class="meth-top"><span class="meth-k">F2F</span></span>
    <h4>면접조사<small>Face-to-Face Interview</small></h4>
    <p>조사원이 응답자를 직접 만나 설문을 진행하는 대면 조사입니다. 복잡한 질문이나 시각자료 제시가 필요한 조사, 응답 신뢰도가 특히 중요한 조사에 적합합니다.</p>
  </article>
  <article class="meth-item reveal">
    <img class="meth-illust method-cati" src="{root}assets/illust/method-cati.png" alt="" width="800" height="800" loading="lazy" decoding="async">
    <span class="meth-top"><span class="meth-k">CATI</span></span>
    <h4>전화조사<small>Telephone Interview</small></h4>
    <p>조사원이 전화로 응답자에게 직접 질문하는 방식입니다. 빠른 시일 내 다수의 응답을 확보해야 하거나, 전국 단위로 넓은 지역을 조사할 때 효율적입니다.</p>
  </article>
  <article class="meth-item reveal">
    <img class="meth-illust method-web" src="{root}assets/illust/method-web.png" alt="" width="800" height="800" loading="lazy" decoding="async">
    <span class="meth-top"><span class="meth-k">WEB</span></span>
    <h4>온라인 조사<small>Web &middot; Mobile</small></h4>
    <p>웹이나 모바일 화면을 통해 응답자가 직접 응답하는 방식입니다. 비용과 시간 효율이 높고, 이미지&middot;동영상 등 다양한 자료를 활용한 설문 설계가 가능합니다.</p>
  </article>
  <article class="meth-item reveal">
    <img class="meth-illust method-ars" src="{root}assets/illust/method-ars.png" alt="" width="800" height="800" loading="lazy" decoding="async">
    <span class="meth-top"><span class="meth-k">ARS</span></span>
    <h4>ARS 조사<small>Automatic Response System</small></h4>
    <p>자동응답시스템을 통해 응답자가 전화기 버튼으로 답변하는 방식입니다. 짧고 간단한 문항을 대규모로, 빠르게 조사해야 할 때 효과적입니다.</p>
  </article>
</div>

<h3 class="minor-h story-h">정성조사</h3>
<div class="meth reveal-group">
  <article class="meth-item reveal">
    <img class="meth-illust method-idi" src="{root}assets/illust/method-idi.png" alt="" width="800" height="800" loading="lazy" decoding="async">
    <span class="meth-top"><span class="meth-k">IDI</span></span>
    <h4>심층면접<small>In-depth Interview</small></h4>
    <p>전문 면접원이 응답자 한 명과 깊이 있는 대화를 나누며 생각과 경험을 자세히 파악하는 방식입니다. 숫자로 드러나지 않는 배경과 맥락을 이해해야 할 때 활용합니다.</p>
  </article>
  <article class="meth-item reveal">
    <img class="meth-illust method-fgi" src="{root}assets/illust/method-fgi.png" alt="" width="800" height="800" loading="lazy" decoding="async">
    <span class="meth-top"><span class="meth-k">FGI</span></span>
    <h4>집단심층토의<small>Focus Group Interview</small></h4>
    <p>소수의 참여자가 한자리에 모여 특정 주제를 자유롭게 토의하는 방식입니다. 참여자 간 의견 교환 속에서 새로운 아이디어나 다양한 관점을 발굴할 때 적합합니다.</p>
  </article>
</div>

<div class="callout reveal">
  <h3>어떤 방법이 맞을지 모르겠다면</h3>
  <p>
    조사 목적과 대상, 일정과 예산을 알려주시면 적합한 방법과 예상 표본 규모를 정리해 제안드립니다.
    여러 방법을 섞어 설계하는 경우도 많습니다.
  </p>
  <a class="btn btn-primary" href="{root}support/contact.html">조사 상담 요청</a>
</div>
""",
     sub="조사 목적과 대상에 따라 적합한 방법을 설계합니다.")

page("special", "business/special.html", "business", "특수 설문 유형",
     "특수 설문 유형", "CE · AHP · CVM · Delphi 등 전문 연구방법론 설문 구현",
     """
<p class="deck-intro">
  방법론마다 <b>응답자가 보는 화면</b>과 <b>분석에 넘겨야 할 데이터 형식</b>이 다릅니다.
  CE는 더미변수 Long Format, AHP는 응답 중 실시간 CR 확인, CVM은 응답자별 제시금액 배분이 필요합니다.
  저희는 이 네 가지를 자체 플랫폼에 직접 구현해 두었으며, 목록에 없는 유형도 설계서만 주시면 구현해 드립니다.
</p>
""" + '<h2 class="minor-h">응답 화면 예시</h2>' + DECK + """

<h2 class="minor-h story-h">방법론별 활용 분야와 결과물</h2>
<div class="specs reveal-group">
  <article class="spec reveal">
    <div class="spec-head">
      <span class="spec-code">CE</span>
      <div>
        <h3>선택실험법<small>Choice Experiment</small></h3>
      </div>
    </div>
    <div class="spec-body">
      <div>
        <h4>활용 분야</h4>
        <ul>
          <li>신제품&middot;신규 서비스의 속성 조합을 설계할 때</li>
          <li>가격을 바꾸면 선택이 얼마나 달라지는지 알아야 할 때</li>
          <li>정책&middot;제도의 여러 대안 중 선호를 비교할 때</li>
        </ul>
      </div>
      <div>
        <h4>주요 결과물</h4>
        <ul>
          <li>속성별 중요도 (효용 가중치)</li>
          <li>가장 선호되는 최적 조합</li>
          <li>조합별 선택확률 시뮬레이션</li>
          <li>가격 민감도 구간</li>
        </ul>
      </div>
    </div>
    <p class="spec-tags"><span>신제품 컨셉테스트</span><span>요금제 설계</span><span>정책 대안 비교</span></p>
  </article>

  <article class="spec reveal">
    <div class="spec-head">
      <span class="spec-code">AHP</span>
      <div>
        <h3>쌍대비교법<small>Analytic Hierarchy Process</small></h3>
      </div>
    </div>
    <div class="spec-body">
      <div>
        <h4>활용 분야</h4>
        <ul>
          <li>여러 사업&middot;정책 대안의 우선순위를 정해야 할 때</li>
          <li>성격이 다른 평가 기준을 함께 비교해야 할 때</li>
          <li>이해관계자들의 판단을 정량적 근거로 남기고 싶을 때</li>
        </ul>
      </div>
      <div>
        <h4>주요 결과물</h4>
        <ul>
          <li>기준별 상대적 중요도 (가중치)</li>
          <li>대안별 최종 우선순위표</li>
          <li>응답 일관성 지표(CR)로 신뢰도 확인</li>
        </ul>
      </div>
    </div>
    <p class="spec-tags"><span>투자&middot;사업 우선순위</span><span>평가지표 설계</span><span>입지 선정</span></p>
  </article>

  <article class="spec reveal">
    <div class="spec-head">
      <span class="spec-code">CVM</span>
      <div>
        <h3>조건부가치측정법<small>Contingent Valuation Method</small></h3>
      </div>
    </div>
    <div class="spec-body">
      <div>
        <h4>활용 분야</h4>
        <ul>
          <li>환경&middot;문화재 등 무형가치를 화폐가치로 보여줘야 할 때</li>
          <li>공공사업의 경제적 타당성 근거가 필요할 때</li>
          <li>요금 인상에 대한 이용자 지불의사를 확인할 때</li>
        </ul>
      </div>
      <div>
        <h4>주요 결과물</h4>
        <ul>
          <li>평균 지불의사금액 (WTP)</li>
          <li>총 사회적 가치 (WTP &times; 대상인구)</li>
          <li>지불의사에 영향을 주는 요인 분석</li>
        </ul>
      </div>
    </div>
    <p class="spec-tags"><span>예비타당성조사</span><span>환경가치 평가</span><span>공공요금 타당성</span></p>
  </article>

  <article class="spec reveal">
    <div class="spec-head">
      <span class="spec-code">Delphi</span>
      <div>
        <h3>전문가 합의법<small>Delphi Method</small></h3>
      </div>
    </div>
    <div class="spec-body">
      <div>
        <h4>활용 분야</h4>
        <ul>
          <li>데이터가 부족한 미래 예측 주제를 다룰 때</li>
          <li>그 분야를 잘 아는 전문가의 판단이 꼭 필요할 때</li>
          <li>소수 의견에 좌우되지 않는 결론이 필요할 때</li>
        </ul>
      </div>
      <div>
        <h4>주요 결과물</h4>
        <ul>
          <li>최종 합의된 전망&middot;판단치</li>
          <li>전문가 간 의견 일치도</li>
          <li>라운드별 의견 변화와 근거</li>
        </ul>
      </div>
    </div>
    <p class="spec-tags"><span>기술&middot;산업 전망</span><span>정책 방향 설정</span><span>리스크 우선순위</span></p>
  </article>
</div>

<h3 class="minor-h story-h">구현 범위 한눈에 보기</h3>
<div class="spec-table-wrap">
  <table class="spec-table">
    <caption>방법론별 구현 범위</caption>
    <thead>
      <tr><th>방법론</th><th>응답 화면</th><th>실시간 처리</th><th>분석 출력</th></tr>
    </thead>
    <tbody>
      <tr><td><b>CE</b> 선택실험법</td><td>속성-수준 프로파일 선택 세트</td><td>세트 순서 무작위화</td><td>더미변수 Long Format</td></tr>
      <tr><td><b>AHP</b> 쌍대비교법</td><td>9점 척도 쌍대비교</td><td>응답 중 CR 피드백</td><td>기준별 가중치 · 우선순위</td></tr>
      <tr><td><b>CVM</b> 조건부가치측정</td><td>제시금액 수락 여부</td><td>응답자별 금액 균등 배분</td><td>DBDC 분기 Long Format</td></tr>
      <tr><td><b>Delphi</b> 전문가 합의</td><td>라운드별 재응답 화면</td><td>통계 요약 자동 표시</td><td>라운드별 의견 수렴 추적</td></tr>
      <tr><td><b>Custom</b> 그 외</td><td colspan="3">설계서 기준으로 협의 후 구현 — 컨조인트, BWS, 순위형 배분, 실험 처치군 무작위 배정, 기관 고유 양식 등</td></tr>
    </tbody>
  </table>
</div>

<div class="callout reveal">
  <h3>연구계획서 단계에서 먼저 상의해 주세요</h3>
  <p>
    문항 설계를 마친 뒤보다 방법론을 정하는 단계에서 함께 검토할 때, 필요한 표본 수와 설계 효율이 크게 달라집니다.
    설계서 초안만 보내주셔도 구현 가능 여부와 적정 표본 규모를 정리해 회신드립니다.
  </p>
  <a class="btn btn-primary" href="{root}support/contact.html">방법론 자문 요청</a>
</div>
""",
     sub="연구 방법론이 요구하는 화면과 출력 형식을 그대로 구현합니다.")

page("platform", "business/platform.html", "business", "설문 플랫폼",
     "설문 플랫폼", "코리아데이터월드 자체 설문 플랫폼 기능 안내",
     PLATFORM_GRID + """
<div class="callout reveal">
  <h3>과제에 필요한 기능을 함께 설계합니다</h3>
  <p>
    외부 설문 도구를 빌려 쓰지 않기에, 과제마다 다른 요구사항을 화면에 그대로 반영할 수 있습니다.
    기관 고유의 응답 양식, 별도의 동의 절차, 특정 형식의 데이터 납품 요건 모두 협의할 수 있습니다.
  </p>
  <a class="btn btn-primary" href="{root}business/special.html">특수 설문 유형 보기</a>
</div>
""",
     sub="조사 설계부터 원시데이터 납품까지, 한 곳에서.")

page("process", "business/process.html", "business", "진행 절차",
     "진행 절차", "문의부터 결과 납품까지의 조사 진행 절차",
     """
<div class="proc reveal-group">
  <article class="proc-step reveal"><span class="proc-top"><span class="proc-ico">{ico:consult}</span><span class="n">1</span></span><h3>문의 · 상담</h3><p>조사 목적과 결과 활용 계획을 함께 확인합니다.</p></article>
  <article class="proc-step reveal"><span class="proc-top"><span class="proc-ico">{ico:design}</span><span class="n">2</span></span><h3>설계 · 견적</h3><p>표본 설계와 문항 구조를 잡아 견적을 드립니다.</p></article>
  <article class="proc-step reveal"><span class="proc-top"><span class="proc-ico">{ico:confirm}</span><span class="n">3</span></span><h3>문항 확정</h3><p>문항 초안을 실제 화면으로 만들어 함께 검토합니다.</p></article>
  <article class="proc-step reveal"><span class="proc-top"><span class="proc-ico">{ico:field}</span><span class="n">4</span></span><h3>실사</h3><p>온라인·대면·전화 등 적합한 방식으로 응답을 수집합니다.</p></article>
  <article class="proc-step reveal"><span class="proc-top"><span class="proc-ico">{ico:verify}</span><span class="n">5</span></span><h3>검증 · 분석</h3><p>불성실 응답을 걸러낸 뒤 통계 분석을 진행합니다.</p></article>
  <article class="proc-step reveal"><span class="proc-top"><span class="proc-ico">{ico:deliver}</span><span class="n">6</span></span><h3>보고 · 납품</h3><p>결과보고서와 원시데이터를 함께 제출합니다.</p></article>
</div>
<div class="prose sm">
  <p>
    일정은 조사 규모와 방법에 따라 달라집니다. 일반적인 온라인 조사는 문항을 확정한 뒤 2~4주가 걸리며,
    전문 조사기법(CE·AHP·CVM·Delphi)이 포함되면 설계를 검토할 기간이 더 필요합니다.
  </p>
</div>
<h3 class="minor-h story-h">보고 · 납품 단계에 드리는 것</h3>
<div class="deliver reveal-group">
  <article class="deliver-item reveal">
    <img src="{root}assets/deliverables/deliver-report.jpg" alt="" width="900" height="675" loading="lazy" decoding="async">
    <h4>결과보고서</h4>
    <p>조사 설계와 표본 구성, 주요 결과와 해석을 담습니다. 보고서 목차는 착수 단계에서 함께 정합니다.</p>
  </article>
  <article class="deliver-item reveal">
    <img src="{root}assets/deliverables/deliver-tables.jpg" alt="" width="900" height="675" loading="lazy" decoding="async">
    <h4>통계표 · 분석 결과</h4>
    <p>문항별 빈도와 교차분석표를 정리해 드립니다. 과제에 필요한 추가 분석은 협의해 포함합니다.</p>
  </article>
  <article class="deliver-item reveal">
    <img src="{root}assets/deliverables/deliver-dataset.jpg" alt="" width="900" height="675" loading="lazy" decoding="async">
    <h4>원시데이터 · 코딩북</h4>
    <p>XLSX·CSV 원시데이터와 변수 설명을 담은 코딩북을 함께 드립니다. 재분석이 필요할 때 바로 쓸 수 있습니다.</p>
  </article>
</div>

<div class="callout">
  <h3>필요한 결과와 희망 일정을 알려주세요</h3>
  <p>조사 목적과 대상, 납품 기한을 알려주시면 단계별 일정과 준비할 자료를 정리해 드립니다. 설문 초안이 없어도 상담을 시작할 수 있습니다.</p>
  <a class="btn btn-primary" href="{root}support/contact.html">조사 일정 · 견적 상담</a>
</div>
""",
     sub="문의부터 결과 납품까지, 여섯 단계로 진행합니다.")

# ── 고객지원 ──────────────────────────────────────────────────
page("notice", "support/notice.html", "support", "공지사항",
     "공지사항", "코리아데이터월드 공지사항 및 새 소식",
     """
<ul class="notice-list full">
  {NOTICES_ALL}
</ul>
""",
     sub="회사의 소식과 안내 사항을 전해드립니다.")


def register_notice_posts():
    """공지 한 건마다 본문 페이지를 만든다 (support/notice/<글번호>.html).

       후이즈에서는 이 페이지들이 필요 없다. 거기서는 게시판의 읽기화면이
       같은 일을 한다. 시연 사이트에서 최종 화면을 그대로 보여 주려고 만든다."""
    listed = [(tag, title, date, seq) for tag, title, date, seq in NOTICES
              if seq and seq in NOTICE_POSTS]
    for i, (tag, title, date, seq) in enumerate(listed):
        post = NOTICE_POSTS[seq]
        parts = ['<article class="post">',
                 '<header class="post-head">',
                 '<span class="notice-tag">%s</span>' % (tag or "소식"),
                 '<h2>%s</h2>' % title,
                 '<time datetime="%s">%s</time>' % (date, date.replace("-", ".")),
                 '</header>',
                 '<div class="post-body">']
        for img in post["imgs"]:
            parts.append('<figure class="post-fig">'
                         '<img src="{root}assets/notice/%s" alt="" loading="lazy">'
                         '</figure>' % attr(img))
        # 관련 기사 링크는 대개 본문 문장 안에 이미 들어 있다.
        # 그 자리를 링크로 바꾸고, 본문에 없는 것만 아래에 따로 붙인다.
        used = set()
        for b in post["body"]:
            line = esc(b)
            for label, url in post["links"]:
                if not label:
                    continue
                marker = esc(label)
                if marker and marker in line:
                    line = line.replace(
                        marker,
                        '<a href="%s" target="_blank" rel="noopener">%s</a>'
                        % (attr(url), marker), 1)
                    used.add(url)
            parts.append("<p>%s</p>" % line)
        for label, url in post["links"]:
            if url in used:
                continue
            parts.append('<p class="post-link">'
                         '<a href="%s" target="_blank" rel="noopener">%s</a></p>'
                         % (attr(url), esc(label or "관련 기사")))
        parts.append("</div>")

        nav = ['<nav class="post-nav">']
        if i + 1 < len(listed):
            nav.append('<a class="post-prev" href="{root}support/notice/%s.html">'
                       '<span>이전 글</span>%s</a>' % (listed[i + 1][3], listed[i + 1][1]))
        nav.append('<a class="post-list" href="{root}support/notice.html">목록으로</a>')
        if i > 0:
            nav.append('<a class="post-next" href="{root}support/notice/%s.html">'
                       '<span>다음 글</span>%s</a>' % (listed[i - 1][3], listed[i - 1][1]))
        nav.append("</nav>")
        parts.append("\n".join(nav))
        parts.append("</article>")

        plain = re.sub(r"<[^>]+>", "", title)
        page("notice-%s" % seq, "support/notice/%s.html" % seq, "support",
             "공지사항", plain, (post["body"][0][:110] if post["body"] else plain),
             "\n".join(parts), lnb_key="notice", h1="공지사항")


register_notice_posts()

page("contact", "support/contact.html", "support", "견적 문의",
     "견적 문의", "조사 의뢰 및 견적 문의 안내",
     CTA_CONTACT + """
<div class="two contact-two">
  <div>
    <h3 class="minor-h">문의하실 때 알려주시면 좋은 것</h3>
    <ul class="check">
      <li>조사 목적과 결과 활용 계획 (보고서, 정책 근거, 논문 등)</li>
      <li>조사 대상과 예상 표본 규모</li>
      <li>희망 조사 방법 (온라인 / 대면 / 전화)</li>
      <li>납품 기한과 예산 범위</li>
      <li>전문 조사기법 포함 여부 (CE · AHP · CVM · Delphi 등)</li>
    </ul>
    <p class="note">아직 정해지지 않은 항목은 비워 두셔도 됩니다. 상담하면서 함께 정리해 나가겠습니다.</p>
  </div>
  <div>
    <h3 class="minor-h">오시는 길</h3>
    {OFFICES}
  </div>
</div>
""",
     sub="조사 목적만 알려주시면, 설계부터 같이 시작합니다.")


# ─────────────────────────────────────────────────────────────
# 셸 생성
# ─────────────────────────────────────────────────────────────
def build_nav(root, active_group, active_key, href):
    parts = ['<nav class="nav" id="gnb">']
    for label, gid, items in MENU:
        shown = [(k, t) for k, t in items if k not in NAV_HIDDEN]
        if not shown:
            continue
        first = href(gid + "/" + shown[0][0])
        cls = "nav-top is-active" if gid == active_group else "nav-top"
        parts.append('<div class="nav-item" data-group="%s">' % gid)
        parts.append('<a class="%s" href="%s">%s</a>' % (cls, first, label))
        if len(shown) > 1:
            parts.append('<div class="nav-sub"><div class="nav-sub-in">')
            for k, t in shown:
                sc = ' class="is-active"' if k == active_key else ""
                parts.append('<a href="%s"%s>%s</a>' % (href(gid + "/" + k), sc, t))
            parts.append('</div></div>')
        parts.append('</div>')
    parts.append('<a class="nav-contact btn btn-primary" href="%s">견적 문의</a>'
                 % href("support/contact"))
    parts.append("</nav>")
    return "\n".join(parts)


def build_lnb(group, active_key, href):
    for label, gid, items in MENU:
        if gid != group:
            continue
        shown = [(k, t) for k, t in items if k not in NAV_HIDDEN]
        if len(shown) < 2:
            return ""
        out = ['<nav class="lnb" aria-label="%s 하위 메뉴"><div class="wrap lnb-shell">' % label,
               '<button class="lnb-scroll" type="button" data-direction="-1" aria-label="이전 메뉴 보기">&#8249;</button>',
               '<div class="lnb-in">']
        for k, t in shown:
            cls = ' class="is-active" aria-current="page"' if k == active_key else ""
            out.append('<a href="%s"%s>%s</a>' % (href(gid + "/" + k), cls, t))
        out.append('</div><button class="lnb-scroll" type="button" data-direction="1" aria-label="다음 메뉴 보기">&#8250;</button></div></nav>')
        return "\n".join(out)
    return ""


def build_footer(href):
    links = []
    for label, gid, items in MENU:
        if gid == "support":
            links.append('<div class="ftr-col"><b>%s</b>'
                         '<a href="%s">공지사항</a><a href="%s">견적 문의</a></div>'
                         % (label, href("support/notice"), href("support/contact")))
            continue
        links.append('<div class="ftr-col"><b>%s</b>%s</div>' % (
            label,
            "".join('<a href="%s">%s</a>' % (href(gid + "/" + k), t)
                    for k, t in items if k not in NAV_HIDDEN)
        ))
    return """
<footer class="ftr">
  <div class="wrap">
    <div class="ftr-top">
      <div class="ftr-brand">
        <a class="brand" href="{HOME}">
          <span class="brand-logo" role="img" aria-label="코리아데이터월드"></span>
        </a>
        <p class="ftr-addr"><b>서울 본사</b> {addr_seoul}<br><b>대구 지점</b> {addr_daegu}</p>
      </div>
      <div class="ftr-cols">%s</div>
    </div>
    <div class="ftr-bottom">
      <p class="ftr-info">
        <b>{name}</b> &nbsp;|&nbsp; 대표이사 {ceo} &nbsp;|&nbsp; 사업자등록번호 {biz_no}<br>
        전화 {tel} &nbsp;|&nbsp; 팩스 {fax} &nbsp;|&nbsp; 메일 <a href="mailto:{email}">{email}</a>
      </p>
      <p class="ftr-copy">Copyright &copy; KOREA DATA WORLD Co., Ltd. All rights reserved.</p>
    </div>
  </div>
</footer>
""" % "".join(links)


ASK_CTA = """
<div class="ask">
  <div class="ask-copy">
    <h3>지금 하시는 고민을 들려주세요</h3>
    <p>조사 목적과 결과를 어디에 쓰실지만 알려주시면, 적합한 방법과 예상 일정을 정리해 드립니다.
       문항이 정해지지 않아도 괜찮습니다.</p>
  </div>
  <div class="ask-act">
    <a class="btn btn-primary" href="{root}support/contact.html">견적 · 조사 문의</a>
    <a class="ask-tel" href="tel:{tel}">{tel}</a>
  </div>
</div>
"""

# 문의 동선이 없던 페이지들. 신뢰를 쌓은 바로 그 자리에서 다음 행동으로 잇는다.
ASK_ON = {"greeting", "history", "organization", "people", "location", "notice"}


def page_head_block(p, href):
    crumb = "홈"
    if p["key"] in NAV_HIDDEN:
        crumb = '홈 <i>/</i> %s' % p["nav_title"]
    else:
        for label, gid, items in MENU:
            if gid == p["group"]:
                crumb = ('홈 <i>/</i> %s' % label if label == p["nav_title"]
                         else '홈 <i>/</i> %s <i>/</i> %s' % (label, p["nav_title"]))
    sub = ('<p class="ph-sub">%s</p>' % p["sub"]) if p["sub"] else ""
    return """
<section class="phead">
  <div class="wrap">
    <p class="ph-crumb">%s</p>
    <h1>%s</h1>
    %s
  </div>
</section>
""" % (crumb, p.get("h1") or p["title"], sub)


def render_content(p, href, root):
    c = p["content"]
    c = c.replace("{DECK}", DECK)
    c = c.replace("{FIELDS}", FIELDS_GRID)
    c = c.replace("{PLATFORM}", PLATFORM_GRID)
    c = c.replace("{CLIENTS}", clients_html())
    c = c.replace("{HEROVIS}", HERO_VIS)
    c = c.replace("{RECENT}", recent_news_html())
    c = c.replace("{CTA}", CTA)
    c = c.replace("{OFFICES}", OFFICES)
    c = c.replace("{NOTICES5}", notice_rows(5))
    c = c.replace("{NOTICES_ALL}", notice_rows())
    c = c.replace("{href}", href("support/notice"))
    c = re.sub(r"\{ico:(\w+)\}", lambda m: ico(m.group(1)), c)
    c = c.replace("{root}", root)
    for k, v in SITE.items():
        c = c.replace("{%s}" % k, v)
    return c


HTML_SHELL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<link rel="icon" href="{ROOT}assets/favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="{ROOT}assets/favicon-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="{ROOT}assets/favicon-180.png">
<meta name="theme-color" content="#24589C">
<meta property="og:type" content="website">
<meta property="og:site_name" content="(주)코리아데이터월드">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESC}">
<meta property="og:image" content="{OGIMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="코리아데이터월드 — 조사 설계부터 데이터 분석까지">
<meta property="og:url" content="{PAGEURL}">
<meta property="og:locale" content="ko_KR">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{ROOT}assets/site.css?v={ASSET_VERSION}">
</head>
<body{BODYCLASS}>
{HEADER}
<main id="main">
{BODY}
</main>
{FOOTER}
<script src="{ROOT}assets/site.js?v={ASSET_VERSION}"></script>
</body>
</html>
"""

HEADER_TPL = """
<a class="skip" href="#main">본문 바로가기</a>
<header class="hdr">
  <div class="wrap hdr-in">
    <a class="brand" href="{HOME}">
      <span class="brand-logo" role="img" aria-label="코리아데이터월드"></span>
    </a>
    {NAV}
    <a class="btn btn-primary hdr-cta" href="{CONTACT}">견적 문의</a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="gnb" aria-label="메뉴 열기">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>
"""


def build_site():
    digest = hashlib.sha256()
    for name in ("site.css", "site.js"):
        with open(os.path.join(HERE, "assets", name), "rb") as asset:
            digest.update(asset.read())
    asset_version = digest.hexdigest()[:12]
    for p in PAGES:
        depth = p["path"].count("/")
        root = "../" * depth

        def href(target, root=root):
            if target == "home":
                return root + "index.html"
            return root + target + ".html"

        nav = build_nav(root, p["group"], p["key"], href)
        header = (HEADER_TPL
                  .replace("{NAV}", nav)
                  .replace("{HOME}", root + "index.html")
                  .replace("{CONTACT}", root + "support/contact.html"))
        footer = (build_footer(href)
                  .replace("{HOME}", root + "index.html")
                  )
        for k, v in SITE.items():
            footer = footer.replace("{%s}" % k, v)

        body = ""
        if p["group"]:
            body += page_head_block(p, href)
            body += build_lnb(p["group"], p.get("lnb_key") or p["key"], href)
            inner = render_content(p, href, root)
            if p["key"] in ASK_ON:
                inner += ASK_CTA.replace("{root}", root).replace("{tel}", SITE["tel"])
            body += '<section class="sec"><div class="wrap">' + inner + "</div></section>"
        else:
            body = render_content(p, href, root)

        html = (HTML_SHELL
                .replace("{TITLE}", p["title"] if p["key"] == "home"
                         else p["title"] + " | 코리아데이터월드")
                .replace("{DESC}", p["desc"])
                .replace("{ROOT}", root)
                .replace("{ASSET_VERSION}", asset_version)
                .replace("{OGIMAGE}", SITE["site_url"] + "assets/og/og-image.png")
                .replace("{PAGEURL}", SITE["site_url"] + ("" if p["key"] == "home" else p["path"]))
                .replace("{BODYCLASS}", ' class="is-home"' if p["key"] == "home" else "")
                .replace("{HEADER}", header)
                .replace("{FOOTER}", footer)
                .replace("{BODY}", body))

        out = os.path.join(HERE, p["path"])
        d = os.path.dirname(out)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        io.open(out, "w", encoding="utf-8").write(html)
        print("  ->", p["path"])


# ─────────────────────────────────────────────────────────────
# 단일 파일 미리보기 (_artifact.html)
# ─────────────────────────────────────────────────────────────
def build_artifact():
    css = io.open(os.path.join(HERE, "assets", "site.css"), encoding="utf-8").read()
    js = io.open(os.path.join(HERE, "assets", "site.js"), encoding="utf-8").read()
    # 단일 파일에서는 외부 파일을 못 읽으므로 로고를 data URI 로 심는다
    import base64
    with open(os.path.join(HERE, "assets", "logo.png"), "rb") as f:
        logo_uri = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

    def href(target):
        if target == "home":
            return "#/home"
        return "#/" + target

    parts = []
    for p in PAGES:
        nav = build_nav("", p["group"], p["key"], href)
        header = (HEADER_TPL
                  .replace("{NAV}", nav)
                  .replace("{HOME}", "#/home")
                  .replace("{CONTACT}", "#/support/contact"))
        footer = (build_footer(href)
                  .replace("{HOME}", "#/home")
                  )
        for k, v in SITE.items():
            footer = footer.replace("{%s}" % k, v)

        body = ""
        if p["group"]:
            body += page_head_block(p, href)
            body += build_lnb(p["group"], p.get("lnb_key") or p["key"], href)
            body += '<section class="sec"><div class="wrap">' + render_content(p, href, "") + "</div></section>"
        else:
            body = render_content(p, href, "")
        # 단일 파일에서는 파일 경로 링크를 해시 링크로 치환
        body = re.sub(r'href="((?:company|business|support)/[a-z]+)\.html"', r'href="#/\1"', body)
        body = body.replace('href="index.html"', 'href="#/home"')
        # 조사방법 이미지도 단일 파일 미리보기에 포함한다.
        def embed_illustration(match):
            with open(os.path.join(HERE, match.group(1)), "rb") as asset:
                uri = "data:image/png;base64," + base64.b64encode(asset.read()).decode("ascii")
            return 'src="' + uri + '"'
        body = re.sub(r'src="(assets/illust/method-[a-z0-9]+\.png)"',
                      embed_illustration, body)

        pid = "home" if p["key"] == "home" else p["path"].replace(".html", "")
        cls = "vpage" + (" is-home" if p["key"] == "home" else "")
        # 한 문서에 모든 페이지가 들어가므로 id 가 중복되지 않도록 페이지별 접미사를 붙인다
        uid = p["key"]
        main_id = "main-" + uid
        header = (header
                  .replace('href="#main"', 'href="#%s"' % main_id)
                  .replace('id="gnb"', 'id="gnb-%s"' % uid)
                  .replace('aria-controls="gnb"', 'aria-controls="gnb-%s"' % uid))
        parts.append('<div class="%s" data-page="%s" hidden>%s<main id="%s">%s</main>%s</div>'
                     % (cls, pid, header, main_id, body, footer))

    router = """
<script>
(function(){
  var pages = Array.prototype.slice.call(document.querySelectorAll('.vpage'));
  function show(id){
    var found = false;
    pages.forEach(function(el){
      var on = el.dataset.page === id;
      el.hidden = !on;
      if (on) found = true;
    });
    if (!found) show('home');
    document.body.classList.toggle('is-home', id === 'home');
    window.scrollTo(0,0);
    if (window.KDW && window.KDW.init) window.KDW.init();
  }
  function fromHash(){
    var h = location.hash.replace(/^#\\//,'');
    show(h || 'home');
  }
  window.addEventListener('hashchange', fromHash);
  fromHash();
})();
</script>
"""
    css = css.replace("url(logo.png)", "url(" + logo_uri + ")")

    out = ('<title>코리아데이터월드</title>\n'
           '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
           '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700'
           '&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;700&display=swap">\n'
           "<style>\n" + css + "\n.vpage[hidden]{display:none}\n</style>\n"
           + "\n".join(parts)
           + "\n<script>\n" + js + "\n</script>\n" + router)
    io.open(os.path.join(HERE, "_artifact.html"), "w", encoding="utf-8").write(out)
    print("  -> _artifact.html (%d KB)" % (len(out) // 1024))


def make_bundle():
    """후이즈 등 일반 웹호스팅에 그대로 올릴 파일만 dist/ 에 모은다."""
    dist = os.path.join(HERE, "dist")
    if os.path.isdir(dist):
        shutil.rmtree(dist)
    os.makedirs(dist)
    for p in PAGES:
        src = os.path.join(HERE, p["path"])
        dst = os.path.join(dist, p["path"])
        d = os.path.dirname(dst)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        shutil.copy2(src, dst)
    shutil.copytree(os.path.join(HERE, "assets"), os.path.join(dist, "assets"))
    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, fs in os.walk(dist) for f in fs)
    count = sum(len(fs) for _, _, fs in os.walk(dist))
    print("  -> dist/  (%d개 파일, %.1f MB)" % (count, total / 1048576.0))
    print("     이 폴더의 내용을 웹호스팅 루트에 그대로 올리면 됩니다.")


# ─────────────────────────────────────────────────────────────
# 후이즈 홈페이지빌더 이식용 조각 (--whois)
#
# 후이즈는 파일 업로드형 호스팅이 아니라 템플릿 빌더다. 그래서
# 완성된 HTML 파일을 그대로 올릴 수 없고, 관리자 화면의 각
# textarea 에 붙여넣어야 한다. 이 함수는 붙여넣을 조각을 만든다.
#
#   레이아웃      디자인 관리 > 레이아웃            layout-home / layout-sub
#   스타일시트    디자인 관리 > CSS/JS > 스타일시트   common.css
#   자바스크립트  디자인 관리 > CSS/JS > 자바스크립트 common.js
#   메인          디자인 관리 > 메인페이지           main.html
#   서브 본문     디자인 관리 > 새 페이지 > 설정      page-<pcode>.html
#   이미지        디자인 관리 > FTP(이미지관리)       images/ 목록
# ─────────────────────────────────────────────────────────────

# 웹FTP 의 이미지 경로. 기존 사이트가 /images/kor01-14-0033/ 를 쓰고 있어
# 그 아래 kdw/ 를 새로 만들어 우리 이미지만 따로 둔다.
WHOIS_IMG = "/images/kor01-14-0033/kdw/"

# 고객이 지금 쓰는 페이지코드(company_history 등)는 건드리지 않는다.
# kdw_ 접두사로 새로 만들어 두고, 검수가 끝난 뒤 메뉴만 갈아끼운다.
WHOIS_PCODE = {
    "greeting": "kdw_greeting",
    "history": "kdw_history",
    "organization": "kdw_org",
    "people": "kdw_people",
    "location": "kdw_location",
    "fields": "kdw_fields",
    "methods": "kdw_methods",
    "special": "kdw_special",
    "platform": "kdw_platform",
    "process": "kdw_process",
    "contact": "kdw_contact",
}

# 공지사항은 빌더 게시판에 이미 47건이 쌓여 있다. 다시 만들지 않고 그대로 쓴다.
WHOIS_NOTICE_URL = "/?act=board&amp;bbs_code=notice"


def whois_rewrite(html):
    """정적 사이트용 절대경로를 빌더 URL 로 바꾼다."""
    html = html.replace('href="/index.html"', 'href="/"')
    # 공지사항 -> 빌더 게시판
    for grp in ("support", "company", "business"):
        html = html.replace('href="/%s/notice.html"' % grp,
                            'href="%s"' % WHOIS_NOTICE_URL)
    # 나머지 페이지 -> ?act=info.page&pcode=
    for grp in ("company", "business", "support"):
        for key, pcode in WHOIS_PCODE.items():
            html = html.replace(
                'href="/%s/%s.html"' % (grp, key),
                'href="/?act=info.page&amp;pcode=%s"' % pcode)
    # 이미지 -> 웹FTP 경로
    html = html.replace('"/assets/', '"' + WHOIS_IMG)
    html = html.replace("(/assets/", "(" + WHOIS_IMG)
    html = html.replace("'/assets/", "'" + WHOIS_IMG)
    return html


def whois_body(p):
    """build_site() 와 같은 본문을, 루트를 / 로 두고 만든다."""
    root = "/"

    def href(target, root=root):
        if target == "home":
            return root + "index.html"
        return root + target + ".html"

    if p["group"]:
        body = page_head_block(p, href)
        body += build_lnb(p["group"], p["key"], href)
        inner = render_content(p, href, root)
        if p["key"] in ASK_ON:
            inner += ASK_CTA.replace("{root}", root).replace("{tel}", SITE["tel"])
        body += '<section class="sec"><div class="wrap">' + inner + "</div></section>"
    else:
        body = render_content(p, href, root)
    return body


WHOIS_LAYOUT = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_SITE.site_browser_title}</title>
<link rel="shortcut icon" href="{_SITE.site_favicon}" />
<!-- DEFAULT HEAD AREA : 빌더 기본 정보입니다. 해당 내용 삭제 시 문제가 발생할 수 있습니다. -->
{_DESIGN.designp_doc_head}
<!-- /DEFAULT HEAD AREA -->
<meta name="theme-color" content="#24589C">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&amp;family=IBM+Plex+Mono:wght@400;500;600&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<!-- user common css -->
<link href="/data/tpl/common.css" type="text/css" rel="stylesheet">
<!-- /user common css -->
</head>
<body{BODYCLASS}>
<!--[[AREA_TOP_START]]-->
{HEADER}
<!--[[AREA_TOP_END]]-->
<!--[[AREA_BODY_START]]-->
<main id="main">
{{BODY}}
</main>
<!--[[AREA_BODY_END]]-->
<!--[[AREA_BOTTOM_START]]-->
{FOOTER}
<!--[[AREA_BOTTOM_END]]-->
<!-- user js -->
<script type="text/javascript" src="/data/tpl/common.js"></script>
<!-- /user js -->
</body>
</html>
"""


WHOIS_NAV_JS = """

/* ── 후이즈 빌더 전용 ──────────────────────────────────────────
   서브 페이지가 레이아웃 하나를 공유하므로, 상단 메뉴의 현재 위치
   표시를 주소(pcode)를 보고 붙인다. 정적 사이트에서는 서버가 찍어
   주기 때문에 이 파일에만 들어간다. */
(function () {
  var GROUP = {{MAP}};
  var q = location.search || "";
  var m = q.match(/pcode=([A-Za-z0-9_]+)/);
  var group = null, pcode = null;
  if (m) { pcode = m[1]; group = GROUP[pcode] || null; }
  else if (/bbs_code=notice/.test(q)) { group = "support"; }
  if (!group) return;
  var top = document.querySelector('.nav .nav-item[data-group="' + group + '"] > .nav-top');
  if (top) top.classList.add("is-active");
  if (!pcode) return;
  var links = document.querySelectorAll('.nav .nav-item[data-group="' + group + '"] .nav-sub a');
  for (var i = 0; i < links.length; i++) {
    if ((links[i].getAttribute("href") || "").indexOf("pcode=" + pcode) >= 0) {
      links[i].classList.add("is-active");
    }
  }
})();
"""


WHOIS_BOARD_JS = """

/* ── 후이즈 게시판 전용 ─────────────────────────────────────────
   게시판은 카테고리 기능을 쓰지 않아서 '[소식]' 같은 머리표가 제목
   글자 안에 들어 있다. 글은 손대지 않고, 화면에 보여 줄 때만 떼어
   배지로 만든다. 등록일의 시각도 같이 덜어 낸다. */
;(function () {
  var HEAD = /^\\s*[\\[(]\\s*([^\\])]{1,10}?)\\s*[\\])]\\s*/;

  function badge(text) {
    var el = document.createElement("span");
    el.className = "notice-tag";
    el.textContent = text;
    return el;
  }

  var links = document.querySelectorAll(".notice-list a");
  for (var i = 0; i < links.length; i++) {
    var a = links[i], m = a.textContent.match(HEAD);
    if (!m) continue;
    a.textContent = a.textContent.replace(HEAD, "");
    a.insertBefore(badge(m[1]), a.firstChild);
  }

  var h = document.querySelector(".post-head h2");
  if (h) {
    var hm = h.textContent.match(HEAD);
    if (hm) {
      h.textContent = h.textContent.replace(HEAD, "");
      h.parentNode.insertBefore(badge(hm[1]), h);
    }
  }

  /* 이전 글 · 다음 글 제목에서도 머리표를 덜어 낸다 (배지는 붙이지 않는다) */
  var sib = document.querySelectorAll(".post-prev, .post-next");
  for (var j = 0; j < sib.length; j++) {
    var kids = sib[j].childNodes;
    for (var n = 0; n < kids.length; n++) {
      if (kids[n].nodeType === 3 && HEAD.test(kids[n].nodeValue)) {
        kids[n].nodeValue = kids[n].nodeValue.replace(HEAD, "");
        break;
      }
    }
  }

  var times = document.querySelectorAll(".notice-list time, .post-head time");
  for (var k = 0; k < times.length; k++) {
    var t = times[k];
    var s = t.textContent.trim().replace(/\\s+\\d{1,2}:\\d{2}(:\\d{2})?$/, "");
    t.textContent = s;
    t.setAttribute("datetime", s.replace(/\\./g, "-").replace(/-+$/, ""));
  }
})();
"""

# 게시판 목록화면. 빌더의 표 대신 우리 목록 마크업을 쓴다.
# {@LIST} 반복과 {.변수} 는 빌더 문법이라 그대로 두어야 한다.
WHOIS_BOARD_LIST = """{PHEAD}
<section class="sec">
  <div class="wrap">

    <ul class="notice-list full">
      {@LIST}
      <li>
        <a href="{.url_view}">{.bbs_title}</a>
        <time>{.bbs_reg_date}</time>
      </li>
      {:}
      <li><span class="notice-title">등록된 글이 없습니다.</span></li>
      {/}
    </ul>

    <div class="board-foot">
      <div class="board-pager">{pagebar}</div>
      <form class="board-search" name="dataForm" action="./" method="post">
        <input type="hidden" name="act" value="{act}">
        <input type="hidden" name="ch" value="{ch}">
        <input type="hidden" name="bbs_code" value="{bbs_code}">
        <input type="hidden" name="bbs_mode" value="{bbs_mode}">
        <input type="hidden" name="page" value="1">
        <input type="hidden" name="sc" value="bbs_title">
        <label class="sr-only" for="bbs-ss">제목 검색</label>
        <input id="bbs-ss" name="ss" value="{ss}" type="text" placeholder="제목으로 찾기">
        <button type="submit">검색</button>
      </form>
    </div>

    {?auth_write}
    <p class="board-admin"><a class="btn btn-ghost" href="{url_write}">글쓰기</a></p>
    {/}

  </div>
</section>
{ASK}
"""

# 게시판 읽기화면. 시연 사이트의 공지 본문 페이지와 같은 모양으로 맞춘다.
WHOIS_BOARD_VIEW = """{PHEAD}
<section class="sec">
  <div class="wrap">

    <article class="post">
      <header class="post-head">
        <h2>{bbs_title}</h2>
        <time>{bbs_reg_date}</time>
      </header>

      <div class="post-body">
        {bbs_content}
      </div>

      {?dataFileList}
      <ul class="post-files">
        {@FILE}
        <li><a href="{.url_download}" target="download">{.bbs_file_name}</a></li>
        {/}
      </ul>
      {/}

      <nav class="post-nav">
        {?prev_data.bbs_seq}
        <a class="post-prev" href="{prev_data.url_view}">
          <span>이전 글</span>{prev_data.bbs_title}</a>
        {/}
        <a class="post-list" href="{url_list}">목록으로</a>
        {?next_data.bbs_seq}
        <a class="post-next" href="{next_data.url_view}">
          <span>다음 글</span>{next_data.bbs_title}</a>
        {/}
      </nav>

      {?auth_write}
      <p class="board-admin">
        <a class="btn btn-ghost" href="{url_modify}">수정</a>
        <a class="btn btn-ghost" href="{url_delete}">삭제</a>
        <a class="btn btn-primary" href="{url_write}">글쓰기</a>
      </p>
      {/}
    </article>

  </div>
</section>
{ASK}
"""


def build_whois():
    out = os.path.join(HERE, "dist-whois")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    def write(name, text):
        io.open(os.path.join(out, name), "w", encoding="utf-8").write(text)
        return len(text)

    root = "/"

    def href(target, root=root):
        if target == "home":
            return root + "index.html"
        return root + target + ".html"

    # 1) 레이아웃 (홈 / 서브) — 헤더·푸터는 공통이므로 body class 만 다르다
    footer = build_footer(href).replace("{HOME}", "/index.html")
    for k, v in SITE.items():
        footer = footer.replace("{%s}" % k, v)

    # 빌더는 서브 페이지 전체가 레이아웃 하나를 공유한다. 그래서 상단 메뉴의
    # 활성 표시를 서버에서 찍을 수 없다 → 활성 표시 없이 내보내고,
    # common.js 끝에 붙인 스크립트가 주소(pcode)를 보고 표시한다.
    sizes = []
    for tag, bodyclass in (("home", ' class="is-home"'), ("sub", "")):
        nav = build_nav(root, "", "", href)
        header = (HEADER_TPL
                  .replace("{NAV}", nav)
                  .replace("{HOME}", "/index.html")
                  .replace("{CONTACT}", "/support/contact.html"))
        layout = (WHOIS_LAYOUT
                  .replace("{BODYCLASS}", bodyclass)
                  .replace("{HEADER}", header)
                  .replace("{FOOTER}", footer))
        sizes.append(("layout-%s.html" % tag,
                      write("layout-%s.html" % tag, whois_rewrite(layout))))

    # 2) CSS / JS
    css = io.open(os.path.join(HERE, "assets", "site.css"), encoding="utf-8").read()
    js = io.open(os.path.join(HERE, "assets", "site.js"), encoding="utf-8").read()
    # site.css 는 assets/ 안에 있어서 url(logo.png) 같은 상대경로를 쓴다.
    # common.css 는 /data/tpl/ 에 놓이므로 상대경로가 깨진다 → 절대경로로 바꾼다.
    css = re.sub(r"url\((['\"]?)(?!/|https?:|data:)([^)'\"]+)\1\)",
                 lambda m: "url(%s%s)" % (WHOIS_IMG, m.group(2)), css)
    sizes.append(("common.css", write("common.css", whois_rewrite(css))))

    pcode_group = {}
    for _, gid, items in MENU:
        for k, _t in items:
            if k in WHOIS_PCODE:
                pcode_group[WHOIS_PCODE[k]] = gid
    js = whois_rewrite(js) + WHOIS_NAV_JS.replace(
        "{MAP}", ",".join('"%s":"%s"' % (pc, g) for pc, g in sorted(pcode_group.items())))
    js += WHOIS_BOARD_JS
    sizes.append(("common.js", write("common.js", js)))

    # 게시판 두 화면. 공지 페이지와 같은 머리글 · 문의 블록을 붙인다.
    phead = """
<section class="phead">
  <div class="wrap">
    <p class="ph-crumb">홈 <i>/</i> 공지사항</p>
    <h1>공지사항</h1>
    <p class="ph-sub">회사의 소식과 안내 사항을 전해드립니다.</p>
  </div>
</section>
""".strip()
    ask = whois_rewrite(ASK_CTA.replace("{root}", "/").replace("{tel}", SITE["tel"]))
    for name, tpl in (("board-list.html", WHOIS_BOARD_LIST),
                      ("board-view.html", WHOIS_BOARD_VIEW)):
        sizes.append((name, write(name, tpl.replace("{PHEAD}", phead)
                                  .replace("{ASK}", ask))))

    # 3) 메인 + 서브 본문
    for p in PAGES:
        body = whois_rewrite(whois_body(p))
        if p["key"] == "home":
            sizes.append(("main.html", write("main.html", body)))
        elif p["key"] == "notice":
            continue  # 빌더 게시판을 그대로 쓴다
        else:
            pcode = WHOIS_PCODE.get(p["key"])
            if not pcode:
                continue
            name = "page-%s.html" % pcode
            sizes.append((name, write(name, body)))

    # 4) 업로드할 이미지 목록
    imgs = []
    adir = os.path.join(HERE, "assets")
    for r, _, fs in os.walk(adir):
        for f in fs:
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico")):
                rel = os.path.relpath(os.path.join(r, f), adir).replace("\\", "/")
                imgs.append((rel, os.path.getsize(os.path.join(r, f))))
    imgs.sort()

    lines = ["# 후이즈 빌더 이식 체크리스트", "",
             "`python build.py --whois` 로 만들어진 조각입니다.",
             "관리자 화면의 각 textarea 에 **파일 내용을 그대로** 붙여넣습니다.", "",
             "## 1. 이미지 업로드 (먼저)", "",
             "디자인 관리 > FTP(이미지관리) > `images` 아래에 `kdw` 폴더를 만들고,",
             "`assets/` 의 하위 폴더 구조를 그대로 올립니다.",
             "최종 경로가 `%s...` 가 되어야 합니다." % WHOIS_IMG, "",
             "| 올릴 파일 (assets/ 기준) | 크기 |", "|---|---|"]
    for rel, sz in imgs:
        lines.append("| `%s` | %.0f KB |" % (rel, sz / 1024.0))
    lines += ["", "합계 %d개 · %.1f MB" % (len(imgs), sum(s for _, s in imgs) / 1048576.0), "",
              "## 2. 붙여넣기", "",
              "| 파일 | 붙여넣을 곳 | 글자수 |", "|---|---|---|",
              "| `common.css` | 디자인 관리 > CSS/JS > 스타일시트(css) 편집 | %d |"
              % dict(sizes)["common.css"],
              "| `common.js` | 디자인 관리 > CSS/JS > 자바스크립트(js) 편집 | %d |"
              % dict(sizes)["common.js"],
              "| `layout-home.html` | 디자인 관리 > 레이아웃 > **새 이름 저장** `KDW_HOME` | %d |"
              % dict(sizes)["layout-home.html"],
              "| `layout-sub.html` | 디자인 관리 > 레이아웃 > **새 이름 저장** `KDW_SUB` | %d |"
              % dict(sizes)["layout-sub.html"],
              "| `main.html` | 디자인 관리 > 메인페이지 | %d |" % dict(sizes)["main.html"]]
    for p in PAGES:
        pcode = WHOIS_PCODE.get(p["key"])
        if not pcode:
            continue
        name = "page-%s.html" % pcode
        lines.append("| `%s` | 새 페이지 > 추가 > 코드 `%s` · 이름 `%s` · 레이아웃 `KDW_SUB` | %d |"
                     % (name, pcode, p["nav_title"], dict(sizes)[name]))
    lines += ["", "## 3. 그대로 두는 것", "",
              "- **공지사항 글 47건** — 빌더 게시판(`bbs_code=notice`)에 이미 있습니다. 글·제목·본문·사진은 **하나도 건드리지 않습니다**.",
              "  메뉴에서 `%s` 로 연결하고, 아래 두 화면의 **디자인만** 바꿉니다."
              % WHOIS_NOTICE_URL.replace("&amp;", "&"),
              "", "| 파일 | 붙여넣을 곳 |", "|---|---|",
              "| `board-list.html` | 디자인 관리 > 게시판 > 공지사항 > **목록화면** |",
              "| `board-view.html` | 디자인 관리 > 게시판 > 공지사항 > **읽기화면** |", "",
              "  (주소: `setup.design_page_edit&ch=design&module_code=board.board_list&bbs_code=notice`,",
              "  `…&module_code=board.board_view&bbs_code=notice`)", "",
              "  게시판은 카테고리 기능을 쓰지 않아 `[소식]` 같은 머리표가 제목 글자 안에 있습니다.",
              "  글을 고치지 않고 `common.js` 가 화면에서만 떼어 배지로 보여 줍니다. 등록일의 시각도 같이 덜어 냅니다.",
              "- 기존 페이지코드(`company_history`, `company_greeting`, `sub3_1` 등) — 검수 전까지 건드리지 않습니다.", "",
              "## 4. 시험 페이지로 실제 확인한 것", "",
              "비공개 페이지 `kdw_test` 를 만들어 직접 넣어 보고 읽어서 대조했습니다.", "",
              "- **길이 제한 없음.** 82,259자를 넣어도 잘리지 않았습니다. 가장 큰 페이지가 1만자 미만이라 여유가 많습니다.",
              "- **HTML 은 보존됩니다.** 태그 · 속성 · 링크 개수가 모두 같았고 엔티티만 풀립니다",
              "  (`&amp;` -> `&`, `&#8249;` -> `‹`). 엔티티를 되돌려 비교하면 원본과 글자 단위로 같습니다.",
              "  주소의 `&pcode=` 는 브라우저가 그대로 읽으므로 문제되지 않습니다.", "",
              "### 본문에 중괄호를 넣으면 안 됩니다", "",
              "`page_src` 는 템플릿 엔진이 PHP 로 컴파일합니다. `{` `}` 가 템플릿 문법이라,",
              "본문에 CSS 나 JS 를 `<style>` · `<script>` 로 끼워 넣으면 페이지 전체가",
              "`Parse error: syntax error` 로 죽습니다. 시험 중 실제로 그렇게 됐습니다.", "",
              "그래서 CSS 와 JS 는 반드시 `디자인 관리 > CSS/JS` 쪽 파일로만 넣습니다.",
              "이 폴더의 본문 조각에는 중괄호가 하나도 없도록 만들어 두었습니다.", "",
              "## 5. 아직 남은 것", "",
              "- **HTTPS** — `https://koreadw.co.kr` 인증서가 self-signed 입니다. 문의 폼으로 연락처를 받으려면 후이즈 SSL 신청이 필요합니다(별도 비용).",
              "- 모바일: `모바일 디자인 관리 > 기본설정 > 모바일홈페이지 사용여부` 가 **미체크**라 모바일도 PC 레이아웃을 받습니다. 우리 반응형 CSS 가 그대로 동작하므로 이 설정은 **그대로 두어야** 합니다.",
              "- `common.css` 와 `common.js` 는 **지금 운영 중인 사이트가 쓰는 공용 파일**입니다.",
              "  여기에 붙여넣는 순간 현재 디자인이 바뀌므로, 이미지 업로드와 페이지 생성을 모두 끝낸 뒤 **맨 마지막에** 합니다."]
    write("README.md", "\n".join(lines) + "\n")

    print("  -> dist-whois/")
    for name, n in sizes:
        print("     %-28s %7d자" % (name, n))
    print("     %-28s %7d개 (%.1f MB)" % ("업로드할 이미지", len(imgs),
                                          sum(s for _, s in imgs) / 1048576.0))
    print("     README.md 에 붙여넣기 순서를 적어 두었습니다.")


if __name__ == "__main__":
    args = sys.argv[1:]
    target = "prod" if "--prod" in args else "demo"
    base = BASES[target]
    for a in args:
        if a.startswith("--base="):
            base, target = a.split("=", 1)[1], "custom"
    if not base.endswith("/"):
        base += "/"
    SITE["site_url"] = base

    print("building pages...  [%s] %s" % (target, base))
    build_site()
    print("building single-file preview...")
    build_artifact()
    if "--bundle" in args:
        print("packing deploy bundle...")
        make_bundle()
    if "--whois" in args:
        print("building whois builder fragments...")
        build_whois()
    print("done.")
