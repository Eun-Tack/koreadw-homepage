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
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

SITE = {
    "name": "(주)코리아데이터월드",
    "name_short": "코리아데이터월드",
    "name_en": "KOREA DATA WORLD",
    "ceo": "김근지",
    "biz_no": "296-81-00459",
    "tel": "02-780-2273",
    "fax": "070-8800-2273",
    "email": "contact@koreadw.co.kr",
    "addr_seoul": "서울특별시 영등포구 국회대로72길 11, 309호",
    "addr_daegu": "대구광역시 달서구 달서대로 54, 503호",
    "tel_daegu": "053-636-2273",
    "site_url": "https://www.koreadw.co.kr/",
}

# ─────────────────────────────────────────────────────────────
# 전역 메뉴
# ─────────────────────────────────────────────────────────────
MENU = [
    ("회사소개", "company", [
        ("greeting", "대표이사 인사말"),
        ("history", "연혁"),
        ("organization", "조직도"),
        ("welfare", "복리후생"),
        ("location", "오시는 길"),
    ]),
    ("사업소개", "business", [
        ("fields", "조사분야"),
        ("special", "특수 설문 유형"),
        ("platform", "설문 플랫폼"),
        ("process", "진행 절차"),
    ]),
    ("고객지원", "support", [
        ("notice", "공지사항"),
        ("contact", "견적문의"),
    ]),
]


# ─────────────────────────────────────────────────────────────
# 공통 컴포넌트
# ─────────────────────────────────────────────────────────────
DECK = """
<div class="chips" role="group" aria-label="특수 설문 유형 선택">
  <button class="chip" type="button" data-target="ce" aria-pressed="false">CE 선택실험법</button>
  <button class="chip" type="button" data-target="ahp" aria-pressed="false">AHP 쌍대비교</button>
  <button class="chip" type="button" data-target="cvm" aria-pressed="false">CVM 조건부가치측정</button>
  <button class="chip" type="button" data-target="delphi" aria-pressed="false">Delphi 전문가 합의</button>
  <button class="chip" type="button" data-target="custom" aria-pressed="true">그 외 모든 유형</button>
</div>

<div class="deck">

  <div class="dcard" role="button" tabindex="0" data-key="ce" style="--i:0">
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

  <div class="dcard" role="button" tabindex="0" data-key="ahp" style="--i:1">
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

  <div class="dcard" role="button" tabindex="0" data-key="cvm" style="--i:2">
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

  <div class="dcard" role="button" tabindex="0" data-key="delphi" style="--i:3">
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

  <div class="dcard custom is-active" role="button" tabindex="0" data-key="custom" style="--i:4">
    <div class="dcard-top"><span class="dcard-code">CUSTOM</span><span class="dcard-step">설계서 → 화면</span></div>
    <h3>그 밖의 모든 유형</h3>
    <p class="dcard-sub">목록에 없는 방법론이라도 문항 구조와 출력 형식만 정해져 있다면 구현할 수 있습니다.</p>
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

NOTICES = [
    # koreadw.co.kr 공지사항 게시판 실제 게시물 (2026-09 기준)
    ("소식", "방유진 전임연구원, 지역사회 후배들을 위한 장학금 기탁", "2026-08-18"),
    ("소식", "대표이사, 제81주년 광복절 경축식 및 청와대 영빈관 초청 오찬 참석", "2026-08-18"),
    ("공지", "(주)코리아데이터월드, 중소벤처기업부 &lsquo;스마트서비스 지원사업&rsquo; 선정", "2026-08-13"),
    ("공지", "메가박스 코엑스 부티크 스위트(Boutique Suite)에서 임직원 &lsquo;문화의 날&rsquo; 진행", "2026-08-05"),
    ("안내", "대표이사, 한국로봇산업진흥원 경영전략 자문위원회 위원 위촉", "2026-06-17"),
    ("공지", "매월 마지막 주 금요일 단축 근무(오후 4시 퇴근) 안내", "2026-05-29"),
    ("공지", "2026년 5월 연휴기간 안내 (5월 4일 휴무)", "2026-05-04"),
    (None, "(주)코리아데이터월드 임직원 워크샵 안내", "2026-04-24"),
    ("공지", "임직원 Refresh 호주 포상 휴가 실시 안내", "2026-04-16"),
    ("공지", "ARS 전화 조사 시스템 도입 및 시행 안내", "2026-03-17"),
    ("공지", "사내 서버 점검 완료 안내", "2026-03-17"),
    (None, "[ 서버 점검에 따른 메일 서비스 이용 안내 ]", "2026-03-16"),
    ("조사 안내", "2026년 한국환경연구원 연구주제 대국민 수요조사 실시", "2026-03-11"),
    ("공지", "2026년 외부 고객만족도 조사 안내", "2026-01-15"),
    (None, "(주)코리아데이터월드 2025년 종무식 및 2026년 시무식 안내", "2025-12-31"),
]


def notice_rows(limit=None):
    rows = NOTICES[:limit] if limit else NOTICES
    out = []
    for tag, title, date in rows:
        badge = '<span class="notice-tag">%s</span>' % tag if tag else ''
        out.append(
            '<li><a href="{href}">%s%s</a>'
            '<time datetime="%s">%s</time></li>'
            % (badge, title, date, date.replace("-", "."))
        )
    return "\n".join(out)


OFFICES = """
<div class="offices">
  <div class="office">
    <h3>서울 본사<span>SEOUL</span></h3>
    <dl>
      <dt>주소</dt><dd>{addr_seoul}</dd>
      <dt>전화</dt><dd>{tel}</dd>
      <dt>팩스</dt><dd>{fax}</dd>
    </dl>
  </div>
  <div class="office">
    <h3>대구 지점<span>DAEGU</span></h3>
    <dl>
      <dt>주소</dt><dd>{addr_daegu}</dd>
      <dt>전화</dt><dd>{tel_daegu}</dd>
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
        문제를 정의하는 첫 단계부터 함께 설계하고, 끝내 손에 쥐어야 할 정보의 형태와 의미까지 같이 고민합니다.
      </p>
      <div class="hero-cta">
        <a class="btn btn-primary btn-lg" href="{root}support/contact.html">조사 의뢰 &middot; 견적 문의</a>
        <a class="btn btn-ghost btn-lg" href="{root}business/special.html">특수 설문 유형 보기</a>
      </div>
    </div>

    <div class="hero-vis" aria-hidden="true">
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

  <div class="wrap">
    <dl class="facts">
      <div class="fact"><dt>창립</dt><dd>2016<small>년</small></dd></div>
      <div class="fact"><dt>거점</dt><dd>2<small>개소 · 서울, 대구</small></dd></div>
      <div class="fact"><dt>조사분야</dt><dd>4<small>개 영역</small></dd></div>
      <div class="fact"><dt>전문 조사기법</dt><dd>4<small>종 · CE·AHP·CVM·Delphi</small></dd></div>
    </dl>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="sec-head center">
      <span class="eyebrow">조사분야</span>
      <h2>네 개 영역에서, 목적이 다른 조사를 설계합니다.</h2>
      <p class="lede">조사 목적이 다르면 표본, 문항 구조, 산출 지표가 모두 달라집니다. 영역별로 필요한 결과물의 형태부터 확인하고 시작합니다.</p>
    </div>
    {FIELDS}
    <p class="sec-more"><a class="link-more" href="{root}business/fields.html">조사분야 자세히 보기</a></p>
  </div>
</section>

<section class="sec band">
  <div class="wrap">
    <div class="band-head">
      <div>
        <span class="eyebrow">특수 설문 유형</span>
        <h2>일반 설문 도구로는 만들 수 없는 문항이<br>연구를 가로막지 않도록.</h2>
        <p class="lede">
          선택실험(CE), 쌍대비교(AHP), 조건부가치측정(CVM), 전문가 합의(Delphi).
          연구 방법론이 요구하는 화면과 출력 형식을 그대로 구현합니다.
        </p>
      </div>
      <p class="band-note">
        방법론마다 <b>응답자가 보는 화면</b>과 <b>분석에 넘겨야 할 데이터 형식</b>이 다릅니다.
        일반 설문 도구가 감당하지 못하는 지점이 바로 여기입니다.
        저희는 네 가지 방법론을 자체 플랫폼에 직접 구현해 두었습니다.
      </p>
    </div>
    {DECK}
    <p class="sec-more"><a class="link-more" href="{root}business/special.html">특수 설문 유형 전체 보기</a></p>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="sec-head center">
      <span class="eyebrow">자체 설문 플랫폼</span>
      <h2>조사 설계부터 원시데이터 납품까지, 한 곳에서.</h2>
      <p class="lede">외부 설문 도구를 빌려 쓰지 않습니다. 조사 현장에서 필요한 기능을 직접 만들어 운영하기 때문에, 요구사항이 생기면 화면을 바꿉니다.</p>
    </div>
    {PLATFORM}
    <p class="sec-more"><a class="link-more" href="{root}business/platform.html">플랫폼 기능 자세히 보기</a></p>
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
<div class="fields">
  <article class="field">
    <span class="field-k">01 &nbsp;SATISFACTION</span>
    <h3>만족도 조사</h3>
    <ul>
      <li>공공기관, 대학교 만족도 조사</li>
      <li>내부·외부 고객이 서비스에 얼마나 만족하고 있는지 파악해, 개선이 필요한 지점을 찾아내는 조사입니다.</li>
    </ul>
  </article>
  <article class="field">
    <span class="field-k">02 &nbsp;POLICY DEMAND</span>
    <h3>정책 수요 조사</h3>
    <ul>
      <li>공공기관, 국책연구기관 정책 수요 조사</li>
      <li>정책을 수립하고 결정하는 단계에서 대상자의 현안 인식을 확인하고 의견을 수렴해, 근거 자료로 활용합니다.</li>
    </ul>
  </article>
  <article class="field">
    <span class="field-k">03 &nbsp;FACT-FINDING</span>
    <h3>실태 조사</h3>
    <ul>
      <li>공공기관 및 지자체 실태조사</li>
      <li>대상 집단이 처한 현재 상황과 문제점을 확인하고, 이를 근거로 개선 방안을 도출하는 조사입니다.</li>
    </ul>
  </article>
  <article class="field">
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
<div class="plat">
  <article class="plat-item">
    <span class="plat-n">01</span>
    <h3>문항 유형 13종</h3>
    <p>단일·복수선택, 척도, 리커트, 매트릭스, 순위, 숫자, 단답, 서술, 휴대전화 인증, 섹션 구분까지 조사 현장에서 실제로 쓰는 유형을 모두 지원합니다.</p>
  </article>
  <article class="plat-item">
    <span class="plat-n">02</span>
    <h3>분기 로직 · 스크리너</h3>
    <p>앞선 응답에 따라 뒤 문항을 건너뛰거나 다른 문항으로 이동시키고, 조사 대상 조건에 맞지 않으면 그 자리에서 응답을 종료합니다.</p>
  </article>
  <article class="plat-item">
    <span class="plat-n">03</span>
    <h3>쿼터 관리</h3>
    <p>성별·연령·지역 등 집단별 목표 응답 수를 정해 두면 실시간으로 집계하고, 목표를 채운 집단은 자동으로 마감합니다.</p>
  </article>
  <article class="plat-item">
    <span class="plat-n">04</span>
    <h3>개인 링크 · QR 발급</h3>
    <p>응답자마다 고유 URL과 QR코드를 발급합니다. 응답 도중 창을 닫아도 이어서 작성할 수 있습니다.</p>
  </article>
  <article class="plat-item">
    <span class="plat-n">05</span>
    <h3>AI 문서 변환</h3>
    <p>HWPX·PDF 설문지를 올리면 AI가 문항을 읽어 유형별로 분류하고 초안을 만들어 둡니다. 담당자는 검토와 수정만 하면 됩니다.</p>
  </article>
  <article class="plat-item">
    <span class="plat-n">06</span>
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
<div class="prose">
  <p class="prose-lead">안녕하십니까?</p>
  <p>
    (주)코리아데이터월드는 데이터를 확보하고 분석하는 일로 고객의 현안을 해결하는 데 힘을 보태고,
    나아가 고객이 목표를 이루는 데 기여하고자 노력하고 있습니다.
  </p>
  <p>
    오늘날은 정보와 데이터가 넘쳐나는 만큼, 정작 무엇을 위한 자료였는지 방향을 잃기 쉬운 시대이기도 합니다.
    그래서 저희 코리아데이터월드는 문제를 정의하는 첫 단계부터 함께 설계하고,
    끝내 손에 쥐어야 할 정보가 어떤 형태와 의미를 가져야 하는지까지 같이 고민하겠습니다.
  </p>
  <p>그 고민에 답하기 위해, 저희는 서베이와 컨설팅 분야의 전문 인력을 갖추고 있습니다.</p>
  <blockquote>
    (주)코리아데이터월드가 드리는 신뢰할 수 있는 데이터와 통찰력 있는 분석은<br>
    고객의 성과로, 정책의 근거로, 연구의 결실로 이어질 것입니다.
  </blockquote>
  <p>늘 고객의 자리에서 생각하며 최선의 결과를 드리겠습니다. 언제든 편하게 찾아주시기 바랍니다. 감사합니다.</p>
  <p class="sign">(주)코리아데이터월드 대표이사 <b>김근지</b></p>
</div>
""")

page("history", "company/history.html", "company", "연혁",
     "연혁", "코리아데이터월드 연혁",
     """
<div class="hist">
  <div class="hist-year">
    <b>2023</b>
    <ul><li><span>06.01</span>신사업팀 신설</li></ul>
  </div>
  <div class="hist-year">
    <b>2018</b>
    <ul>
      <li><span>04.01</span>연구팀 / 실사팀 / 분석팀 / 제작팀 운영</li>
      <li><span>04.01</span>서울 본사 · 대구 지점 통합 운영 체계 구축</li>
      <li><span>03.05</span>대구 지점 신설</li>
      <li><span>03.05</span>서울 여의도로 본사 이전</li>
    </ul>
  </div>
  <div class="hist-year">
    <b>2017</b>
    <ul><li><span>10.31</span>(주)코리아데이터월드 창립 1주년</li></ul>
  </div>
  <div class="hist-year">
    <b>2016</b>
    <ul>
      <li><span>12.01</span>여성창업보육센터로 본사 이전</li>
      <li><span>10.31</span>(주)코리아데이터월드 창립</li>
    </ul>
  </div>
</div>
""")

page("organization", "company/organization.html", "company", "조직도",
     "조직도", "코리아데이터월드 조직도 — 서울 본사 및 대구 지점",
     """
<div class="org-block">
  <h3 class="org-title">서울 본사<span>SEOUL HEAD OFFICE</span></h3>
  <div class="org">
    <div class="org-head">
      <span class="org-node lead">대표이사</span>
      <span class="org-advisor">분야별 자문위원</span>
    </div>
    <div class="org-row">
      <div class="org-col">
        <span class="org-node">연구팀</span>
        <div class="org-leaf"><span>공공분야</span><span>마케팅분야</span></div>
      </div>
      <div class="org-col"><span class="org-node">분석팀</span></div>
      <div class="org-col"><span class="org-node">실사팀</span></div>
      <div class="org-col"><span class="org-node">제작팀</span></div>
      <div class="org-col"><span class="org-node">신사업팀</span></div>
      <div class="org-col"><span class="org-node">경영지원팀</span></div>
    </div>
  </div>
</div>

<div class="org-block">
  <h3 class="org-title">대구 지점<span>DAEGU BRANCH</span></h3>
  <div class="org">
    <div class="org-head"><span class="org-node lead">본부장</span></div>
    <div class="org-row">
      <div class="org-col">
        <span class="org-node">연구팀</span>
        <div class="org-leaf"><span>공공분야</span><span>마케팅분야</span></div>
      </div>
      <div class="org-col"><span class="org-node">분석팀</span></div>
      <div class="org-col"><span class="org-node">실사팀</span></div>
    </div>
  </div>
</div>
""")

page("welfare", "company/welfare.html", "company", "복리후생",
     "복리후생", "코리아데이터월드 복리후생 제도",
     """
<div class="wel">
  <article class="wel-item">
    <span class="wel-k">유연근무제</span>
    <p>육아기 단축근무제 · 탄력근무제 · 주 1~2일 재택근무제 시행</p>
  </article>
  <article class="wel-item">
    <span class="wel-k">식사 제공</span>
    <p>아침·점심 간식 제공</p>
  </article>
  <article class="wel-item">
    <span class="wel-k">자기계발비</span>
    <p>발레, 미술, 검도, 골프, 필라테스, 피부관리 중 선택 <b>(200만원 상당)</b></p>
  </article>
  <article class="wel-item">
    <span class="wel-k">인센티브</span>
    <p>연말 인센티브 지급 · 우수 사원 해외 연수</p>
  </article>
  <article class="wel-item">
    <span class="wel-k">창립기념일</span>
    <p>기쁨 선물 박스 증정 <b>(50~100만원 상당)</b></p>
  </article>
  <article class="wel-item">
    <span class="wel-k">생일</span>
    <p>축하금 지급 · 케이크와 꽃바구니 증정 <b>(20만원 상당)</b></p>
  </article>
</div>
<p class="note">※ 근무시간 오전 10시 – 오후 6시 · 주 35시간 근무제</p>
""")

page("location", "company/location.html", "company", "오시는 길",
     "오시는 길", "코리아데이터월드 서울 본사 · 대구 지점 위치 안내",
     OFFICES + """
<div class="prose sm">
  <p>방문 상담을 원하시면 전화나 메일로 미리 일정을 잡아 주세요. 담당 연구원이 자료를 준비해 두고 맞이하겠습니다.</p>
</div>
""")

# ── 사업소개 ──────────────────────────────────────────────────
page("fields", "business/fields.html", "business", "조사분야",
     "조사분야", "만족도 · 정책수요 · 실태 · 학술연구 조사",
     FIELDS_GRID + """
<div class="callout">
  <h3>어느 영역인지 애매해도 괜찮습니다</h3>
  <p>
    실제 과제는 만족도와 실태, 정책수요가 섞여 있는 경우가 대부분입니다.
    무엇을 알고 싶으신지, 그 결과를 어디에 쓰실지만 알려주시면 그에 맞는 조사 형태를 저희가 정리해 제안드립니다.
  </p>
  <a class="btn btn-primary" href="{root}support/contact.html">조사 상담 요청</a>
</div>
""",
     sub="조사 목적이 다르면 표본, 문항 구조, 산출 지표가 모두 달라집니다.")

page("special", "business/special.html", "business", "특수 설문 유형",
     "특수 설문 유형", "CE · AHP · CVM · Delphi 등 전문 연구방법론 설문 구현",
     """
<p class="deck-intro">
  방법론마다 <b>응답자가 보는 화면</b>과 <b>분석에 넘겨야 할 데이터 형식</b>이 다릅니다.
  CE는 더미변수 Long Format, AHP는 응답 중 실시간 CR 확인, CVM은 응답자별 제시금액 배분이 필요합니다.
  저희는 이 네 가지를 자체 플랫폼에 직접 구현해 두었으며, 목록에 없는 유형도 설계서만 주시면 구현해 드립니다.
</p>
""" + DECK + """
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

<div class="callout">
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
<div class="callout">
  <h3>필요한 기능이 없으면, 만듭니다</h3>
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
<div class="proc">
  <article class="proc-step"><span class="n">1</span><h3>문의 · 상담</h3><p>조사 목적과 결과 활용 계획을 함께 확인합니다.</p></article>
  <article class="proc-step"><span class="n">2</span><h3>설계 · 견적</h3><p>표본 설계와 문항 구조를 잡아 견적을 드립니다.</p></article>
  <article class="proc-step"><span class="n">3</span><h3>문항 확정</h3><p>문항 초안을 실제 화면으로 만들어 함께 검토합니다.</p></article>
  <article class="proc-step"><span class="n">4</span><h3>실사</h3><p>온라인·대면·전화 등 적합한 방식으로 응답을 수집합니다.</p></article>
  <article class="proc-step"><span class="n">5</span><h3>검증 · 분석</h3><p>불성실 응답을 걸러낸 뒤 통계 분석을 진행합니다.</p></article>
  <article class="proc-step"><span class="n">6</span><h3>보고 · 납품</h3><p>결과보고서와 원시데이터를 함께 제출합니다.</p></article>
</div>
<div class="prose sm">
  <p>
    일정은 조사 규모와 방법에 따라 달라집니다. 일반적인 온라인 조사는 문항을 확정한 뒤 2~4주가 걸리며,
    전문 조사기법(CE·AHP·CVM·Delphi)이 포함되면 설계를 검토할 기간이 더 필요합니다.
  </p>
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

page("contact", "support/contact.html", "support", "견적문의",
     "견적문의", "조사 의뢰 및 견적 문의 안내",
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
        first = href(gid + "/" + items[0][0])
        cls = "nav-top is-active" if gid == active_group else "nav-top"
        parts.append('<div class="nav-item">')
        parts.append('<a class="%s" href="%s">%s</a>' % (cls, first, label))
        parts.append('<div class="nav-sub"><div class="nav-sub-in">')
        for k, t in items:
            sc = ' class="is-active"' if k == active_key else ""
            parts.append('<a href="%s"%s>%s</a>' % (href(gid + "/" + k), sc, t))
        parts.append('</div></div></div>')
    parts.append("</nav>")
    return "\n".join(parts)


def build_lnb(group, active_key, href):
    for label, gid, items in MENU:
        if gid != group:
            continue
        out = ['<div class="lnb"><div class="wrap lnb-in">']
        for k, t in items:
            cls = ' class="is-active"' if k == active_key else ""
            out.append('<a href="%s"%s>%s</a>' % (href(gid + "/" + k), cls, t))
        out.append("</div></div>")
        return "\n".join(out)
    return ""


def build_footer(href):
    links = []
    for label, gid, items in MENU:
        links.append('<div class="ftr-col"><b>%s</b>%s</div>' % (
            label,
            "".join('<a href="%s">%s</a>' % (href(gid + "/" + k), t) for k, t in items)
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
    for label, gid, items in MENU:
        if gid == p["group"]:
            crumb = '홈 <i>/</i> %s <i>/</i> %s' % (label, p["nav_title"])
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
    c = c.replace("{CTA}", CTA)
    c = c.replace("{OFFICES}", OFFICES)
    c = c.replace("{NOTICES5}", notice_rows(5))
    c = c.replace("{NOTICES_ALL}", notice_rows())
    c = c.replace("{href}", href("support/notice"))
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
<meta property="og:url" content="{PAGEURL}">
<meta property="og:locale" content="ko_KR">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{ROOT}assets/site.css">
</head>
<body{BODYCLASS}>
{HEADER}
<main id="main">
{BODY}
</main>
{FOOTER}
<script src="{ROOT}assets/site.js"></script>
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
                .replace("{OGIMAGE}", SITE["site_url"] + "assets/favicon-512.png")
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


if __name__ == "__main__":
    print("building pages...")
    build_site()
    print("building single-file preview...")
    build_artifact()
    print("done.")
