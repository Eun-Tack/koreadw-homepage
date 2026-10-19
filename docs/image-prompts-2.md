# 추가 이미지 생성 프롬프트 (2차)

작성 2026-10-19 · 1차 프롬프트는 [image-prompts.md](image-prompts.md), 로고 정리는 [ci-logo-prompt.md](ci-logo-prompt.md)

---

## 0. 생성해도 되는 것과 안 되는 것

제공된 자료를 전부 열어 대조한 결과, **아직 비어 있는 자리는 4곳**입니다.
그중 생성으로 채워도 되는 것은 **1곳뿐**입니다.

| 자리 | 생성 가능 | 이유 |
|---|---|---|
| **보고서 표지** | **가능** | 실제 보고서를 흉내 내지 않고, 기관명·숫자 없는 **장식용 목업**으로 만들면 됩니다 |
| 정기후원 활동 사진 | 불가 | 실제 후원 현장입니다. 만들면 허위 |
| 양평군 정책 포럼 등 대외활동 사진 | 불가 | 실제 행사 사진이어야 합니다 |
| 헤리티지아카데미 수료증 | 불가 | 실물 문서 |

> **보고서 표지에 선을 긋는 기준**: 특정 기관명, 실제 과업명, 읽히는 숫자나 그래프 수치를
> 넣으면 "실제 납품물" 로 읽혀 허위가 됩니다. **글자 없는 추상 목업**이어야 합니다.

---

## 1. 보고서 표지 목업 3종

첫 화면 롤링의 네 번째 축(보고서 표지)을 채웁니다.
지금 롤링에는 언론·협약·인증만 있어 "결과물" 이 빠져 있습니다.

**저장 위치** `web/assets/credentials/`
**규격** 1200×900 JPG (4:3, 롤링 카드 비율)

### 공통 스타일 (세 장 모두 앞에 붙일 것)

```
Flat vector mockup illustration, minimal corporate style.
A closed report booklet shown at a slight angle on a plain light background,
as a clean product mockup. Strict palette: deep navy #24589C, pale blue
#EAF1FA, thin #3A78C4 line accents, on a very light #F6F9FE ground.
No gradients, no 3D rendering, no photographic texture, no desk or hands.
Soft, very subtle shadow under the booklet only.

CRITICAL: absolutely no readable text, no letters, no words, no numbers,
no logos, no organization names anywhere. Where a title would go, draw only
plain horizontal placeholder bars. Charts, if any, must be abstract shapes
with no axis labels and no values.

1200x900 pixels, 4:3 landscape, centered with generous margin.
```

### ① 보고서 표지 — `report-cover-1.jpg`
```
Subject: a single closed A4 report cover standing upright, seen slightly
from the front-left. The cover has a wide navy band across the top third,
three short placeholder bars where a title would be, and a thin horizontal
rule near the bottom. Clean and formal.
```

### ② 보고서 묶음 — `report-cover-2.jpg`
```
Subject: three closed report booklets of the same size fanned out in a row,
overlapping slightly, seen from above at a shallow angle. Each cover shows a
different simple abstract motif in navy and pale blue: one with a bar-chart
block of four plain bars, one with a dot grid, one with a rising line.
No labels on any of them.
```

### ③ 펼친 보고서 — `report-cover-3.jpg`
```
Subject: one report opened flat to a two-page spread, seen from directly
above. The left page shows three blocks of placeholder text bars; the right
page shows one abstract bar chart and one donut chart, both unlabeled with
no numbers. Thin navy outlines, pale blue fills.
```

---

## 2. 받은 뒤 확인할 것

- **글자가 한 자라도 들어갔는지** — 들어갔으면 재생성입니다. 생성 모델은
  의미 없는 글자를 만들어 넣는 버릇이 있고, 보고서 표지에 가짜 글자가 있으면
  바로 티가 납니다
- **숫자가 보이는 차트가 있는지** — 축 값이나 퍼센트가 보이면 실제 데이터로 오해됩니다
- **3장이 한 세트로 보이는지** — 파란색 농도와 선 두께를 맞춰 주세요
- 1200×900 인지

받으시면 제가 롤링에 넣고 `content/credentials.md` 에 등록하겠습니다.

---

## 3. 생성으로 채울 수 없어 요청드려야 하는 자료

| 필요 자료 | 쓰이는 곳 |
|---|---|
| 정기후원 활동 사진 (광복회 · 천사무료급식소 · 여의도동행봉사단 · 한국보훈진흥회) | 대외활동 |
| 양평군 정책 포럼, 광복절 경축식, 상하이 탐방 현장 사진 | 대외활동 |
| 광복회 헤리티지아카데미 수료증 | 수료·교육 |
| 서울시여성능력개발원 MOU · 여성친화 일촌기업 협약 **체결일** | 날짜 미상 3건 |

이 네 가지는 **없으면 없는 대로** 목록에만 남습니다. 사진이 생기면
`content/credentials.md` 에 파일명 한 줄만 더하면 그 항목에 붙습니다.

---

## 4. 참고 — 쓸 수 없는 자료

`홈페이지 수정사항.pptx` 에 들어 있던 조사 일러스트 한 장은
**iStock 워터마크가 찍힌 미구매 샘플**입니다. 그대로 쓰면 저작권 문제가 되고,
비슷하게 다시 그리는 것도 권하지 않습니다. 조사방법 페이지에는 이미
직접 생성한 일러스트 6장이 들어가 있어 대체가 끝난 상태입니다.
