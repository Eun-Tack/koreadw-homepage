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
        date, tag, title = _cells(line, 3)
        if not date or not title:
            continue
        rows.append((tag or None, esc(title), date))
    return rows


def load_history():
    """([(연도, [(월일, 내용, 설명), ...]), ...], [(시점, 제목, 설명), ...])"""
    years, story, mode = [], [], "연혁"
    index = {}
    for line in _lines("history.md"):
        if line.startswith("[") and line.endswith("]"):
            mode = line[1:-1].strip()
            continue
        if mode == "연혁":
            year, when, text, note = _cells(line, 4)
            if not year or not text:
                continue
            if year not in index:
                index[year] = []
                years.append((year, index[year]))
            index[year].append((when, esc(text), esc(note)))
        else:
            when, title, desc = _cells(line, 3)
            if not title:
                continue
            story.append((esc(when), esc(title), esc(desc)))
    return years, story


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


def notice_rows(limit=None):
    rows = NOTICES[:limit] if limit else NOTICES
    out = []
    for tag, title, date in rows:
        badge = '<span class="notice-tag">%s</span>' % (tag or "소식")
        title_html = ('<a href="{href}">%s%s</a>' % (badge, title) if limit
                      else '<span class="notice-title">%s%s</span>' % (badge, title))
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


# ─────────────────────────────────────────────────────────────
# 페이지 콘텐츠
# ─────────────────────────────────────────────────────────────
PAGES = []


def page(key, path, group, nav_title, title, desc, content, sub="", hero=None):
    PAGES.append(dict(key=key, path=path, group=group, nav_title=nav_title,
                      title=title, desc=desc, content=content, sub=sub, hero=hero))


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

    <div class="hero-vis" aria-hidden="true">
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
  </div>

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

def history_html():
    years, story = load_history()
    out = ['<div class="hist reveal-group">']
    for year, items in years:
        out.append('<div class="hist-year reveal"><b>%s<i>년</i></b><ul>' % year)
        for when, text, note in items:
            em = ' <em>(%s)</em>' % note if note else ''
            out.append('<li><span class="hist-date">%s</span><div class="hist-entry">%s%s</div></li>'
                       % (when, text, em))
        out.append('</ul></div>')
    out.append('</div>')
    if story:
        out.append('<h3 class="minor-h story-h">성장 스토리</h3>')
        out.append('<div class="story reveal-group">')
        for when, title, desc in story:
            out.append(
                '<article class="story-item reveal">'
                '<span class="story-when">%s</span><h4>%s</h4><p>%s</p></article>'
                % (when, title, desc))
        out.append('</div>')
    return chr(10).join(out)


page("history", "company/history.html", "company", "연혁",
     "연혁", "코리아데이터월드 연혁 및 주요 활동",
     '<h3 class="minor-h">기업 주요 연혁</h3>' + history_html(),
     sub="2016년 창립 이후 걸어온 길입니다.")

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
        parts.append('<div class="nav-item">')
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
""" % (crumb, p["title"], sub)


def render_content(p, href, root):
    c = p["content"]
    c = c.replace("{DECK}", DECK)
    c = c.replace("{FIELDS}", FIELDS_GRID)
    c = c.replace("{PLATFORM}", PLATFORM_GRID)
    c = c.replace("{CLIENTS}", clients_html())
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
            body += build_lnb(p["group"], p["key"], href)
            body += '<section class="sec"><div class="wrap">' + render_content(p, href, root) + "</div></section>"
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
            body += build_lnb(p["group"], p["key"], href)
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
    print("done.")
