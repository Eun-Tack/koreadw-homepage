# 이미지 생성 프롬프트 및 적용 기준

수정일: 2026-10-12 · 현재 웹 소스 기준 · 생성 도구: 내장 image_gen

## 1. 현재 페이지와의 적합성

- 실제 CSS 토큰: 주색 #24589C, 보조색 #3A78C4, 연한 면 #EAF1FA, 흰색 배경. 기존 문서의 색상은 일치한다.
- 조사방법은 business/methods.html의 2열 카드이며 760px 이하에서 1열이다. 이미지는 제목 왼쪽의 124px 영역(작은 모바일 104px)에 배치하고 제목·본문은 HTML로 유지한다. 원본별 피사체 크기 차이는 CSS 배율로 보정한다.
- 기존 “pure white background”와 “transparent background” 충돌을 제거했다. 조사방법은 실제 알파 투명 PNG, OG는 불투명 배경이다.
- 축소 표시에서도 읽히는 둥근 윤곽선을 요청한다. 이미지에 글자·숫자·브랜드를 생성하지 않는다.
- OG 배경은 왼쪽 70%를 비우고 우측에만 장식한다. 기존 문서의 왼쪽 장식/왼쪽 여백 충돌을 제거했다. 기존 로고와 정확한 한글은 코드로 합성한다.
- 현재 메인에는 HTML 대시보드가 있으므로 선택용 hero-visual.png는 만들거나 연결하지 않는다. 자료 미수급 시 임시 사용이라는 조건을 유지한다.
- 현재 디렉터리가 이미 web/이므로 실제 저장 경로는 assets/...이다.

## 2. 생성 금지·범위 밖

언론 지면, 수상 기록, 인증서, 위촉장, 실제 행사·후원 사진, 타사 CI, 임직원 사진을 생성물로 대체하지 않는다. 기존 로고는 원본을 그대로 사용한다. 작은 SVG 아이콘 16종은 이번 생성 범위에 포함하지 않는다.

## 3. 조사방법 공통 프롬프트

아래 공통 문단과 각 Subject를 결합해 이미지별로 요청한다. transparent_background: true.

```text
Use case: stylized-concept. One standalone production website illustration for a restrained Korean survey research firm. Square 800x800 PNG with genuinely transparent background. Flat vector-like corporate editorial illustration, smooth uniform rounded blue outlines about 7px at 800px. Palette #24589C dark blue, #3A78C4 secondary blue, #EAF1FA pale blue, white interior highlights only. Centered subject fitting central 74% of canvas, comfortable equal margins, readable at 180px. Use solid flat color fills only, absolutely NO gradient or shading. Professional simple rounded geometry, not cartoonish. No text, letters, numbers, logos, watermarks, stars, sparkles, texture, shadows, 3D or drawn checkerboard. 
```

### F2F — assets/illust/method-f2f.png

```text
Subject: exactly two simplified abstract faceless people seated opposite each other across a small round table. Oval featureless heads without hair, no anatomical facial profiles; simple solid blue or pale-blue clothing. Left interviewer holds one clipboard with exactly three short abstract strokes; one empty speech bubble between people. Simple chairs, feet fully in frame. Critical: make this a flat pictogram-like editorial illustration with completely solid colors, no glossy highlights or color gradients. Keep the entire composition compact with 15% margin on every side.
```

### CATI — assets/illust/method-cati.png

```text
Subject: a large over-ear call-center headset with two ear cushions and a curved microphone boom. Beside the microphone exactly five separate short vertical rounded waveform bars of varying height, and one small empty speech bubble above. No humans, no device screen. Balanced headset and waveform composition.
```

### WEB — assets/illust/method-web.png

```text
Subject: a smartphone upright at lower left overlapping a larger desktop browser frame at upper right. Both screens contain exactly three simple horizontal survey rows, each with one empty square checkbox; ONLY middle row checked. The row lines are abstract straight strokes, never letters. A small blue cursor arrow near the browser's middle checked box. All devices seen straight-on, flat and geometrical, no perspective bevel.
```

### ARS — assets/illust/method-ars.png

```text
Subject: one simple telephone receiver on left beside a compact three-by-three keypad of exactly nine blank rounded square buttons at right. A short connector line links receiver and keypad; four short separate rounded vertical sound-wave bars above receiver. Buttons have absolutely no numbers or symbols. No headset, no humans.
```

### IDI — assets/illust/method-idi.png

```text
Subject: exactly two abstract faceless bust silhouettes in profile facing each other. Oval heads with no hair detail, no facial features, no skin color. The left person leans slightly toward the other, suggesting attentive listening. Between them one large empty speech bubble, with one magnifying glass overlapping the lower right corner of the bubble. Distinct from face-to-face survey: no clipboard, no table, no chairs. Blue and pale blue clothing.
```

### FGI — assets/illust/method-fgi.png

```text
Subject: exactly four abstract faceless people seated evenly around one round table, slight top-down view. Four oval heads, simple blue and pale-blue torsos, no hair or facial features, no skin colors, no detailed fingers. Three empty speech bubbles above the middle of table. Make all four people individually distinct and clearly countable; none cropped. Minimal chairs and simple table, no papers or screens.
```

## 4. 공유용 배경 프롬프트

transparent_background: false. 배경: assets/og/og-bg.png. 로고·한글 합성본: assets/og/og-image.png.

```text
Use case: ads-marketing. Asset type: corporate website Open Graph background to be composited with an existing logo and Korean company title by code. Create a wide landscape 1200x630 PNG, opaque pure white background. Minimal very subtle vector-like data research motifs ONLY in far right quarter and bottom-right edge: three thin horizontal bar-chart bars, five blank rounded rating squares, sparse dot grid, using pale blue #EAF1FA fill and restrained #3A78C4 and #24589C line accents. A very soft pale blue glow is allowed behind motifs at top right. Keep the ENTIRE left 70% and center-left completely empty PURE WHITE, especially x=60..840 y=90..510, for legible logo and typography. Motifs low contrast, calm professional geometric style matching a white and blue survey research company website. No words, no letters, no numbers, no logo, no watermark, no fake UI labels, no border. Exact aspect ratio 1200:630.
```

## 5. 납품 및 품질 기준

- 조사방법 6장: 800×800 RGBA PNG. 생성 원본 비율을 유지해 축소하고 투명 여백을 추가한다. 웹에서는 object-fit: contain을 사용한다.
- 공유 배경·합성본: 1200×630. 기존 로고와 HTML 한글로 합성한다.
- 시각 검토: 조사 유형 구분, FGI 4명, ARS 9버튼, WEB 두 화면의 중간 체크, 문자·피부색·얼굴 표정 부재, 잘림·여백.
- 기술 검토: 크기, 투명도, 용량, 이미지 로딩, 모바일 가로 넘침, 정적 페이지·단일 HTML 미리보기 참조, OG 메타데이터.
- 생성물에 옅은 명암·색 변이가 남아 완전한 단색 벡터와는 다르다. 실제 표시 크기에서 통일성과 가독성을 판단하며 정확한 색상값 일치를 보장하지 않는다.
- 면접조사 초안의 머리카락 디테일을 제거하기 위해 재생성했다. 채택본은 단순한 타원형 머리와 다른 인물 일러스트에 맞춘 구성이다.

검토 결과와 화면 캡처는 docs/image-quality/에 저장한다.

