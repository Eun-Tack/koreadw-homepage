# 이미지 품질 검토

검토일: 2026-10-11. 대상은 현재 작업 폴더의 웹 소스와 로컬 Chromium 렌더링이다. 운영 사이트 배포는 수행하지 않았다.

## 결과

조사방법 일러스트 6장과 OG 배경 1장을 내장 image_gen으로 생성했다. 면접조사는 초안의 머리카락 디테일을 없애기 위해 재생성했다. 채택한 이미지 7장과 기존 로고·HTML 한글로 만든 OG 합성본 1장을 프로젝트에 저장했다.

| 파일 | 규격 | 검토 |
|---|---|---|
| assets/illust/method-f2f.png | 800×800 RGBA | 2명, 테이블, 클립보드와 빈 말풍선. 얼굴 표정·피부색 없음 |
| assets/illust/method-cati.png | 800×800 RGBA | 헤드셋, 마이크, 5개 음성 막대. ARS와 구별 가능 |
| assets/illust/method-web.png | 800×800 RGBA | 모바일·데스크톱에 각각 3개 체크 행, 중간 행 선택 |
| assets/illust/method-ars.png | 800×800 RGBA | 수화기, 숫자 없는 9개 버튼, 4개 음성 막대 |
| assets/illust/method-idi.png | 800×800 RGBA | 대화하는 2명과 돋보기. 면접조사와 구별 가능 |
| assets/illust/method-fgi.png | 800×800 RGBA | 4명, 원탁, 3개 빈 말풍선 |
| assets/og/og-bg.png | 1200×630 | 좌측 여백, 우측 데이터 장식, 생성 문자 없음 |
| assets/og/og-image.png | 1200×630 | 원본 로고, 정확한 HTML 한글, 장식과 텍스트 겹침 없음 |

## 시각 판정

- 흰색과 #EAF1FA 배경에서 이미지 6장을 비교했다. 투명 배경 사각형, 대상 잘림, 눈에 띄는 외곽 얼룩은 실제 표시 크기에서 발견하지 못했다.
- 페이지의 파란색·흰색·둥근 카드와 어울린다. 카드에서는 180px 정사각 영역에 비율을 유지해 표시하며, 제목과 본문은 HTML로 남겼다.
- 글자·숫자·워터마크가 생성 이미지에 들어가지 않았다. OG의 회사명과 문구는 생성 결과가 아니라 기존 로고 및 HTML 합성이다.
- 완전한 단색 벡터는 아니다. 일부 면에 옅은 색 변화가 남고 이미지별 윤곽선 두께에 작은 차이가 있다. 100px 비교표와 실제 180px 카드에서는 유형 구분과 세트의 통일성을 해치지 않아 채택했다. 정확한 CSS 색상값 일치가 필요한 로고·UI 아이콘용으로 전용하지 않는다.
- 선택용 히어로는 생성하지 않았다. 현재 HTML 대시보드와 중복되고, 기존 문서에서도 실제 자료 미수급 시에만 사용하는 조건부 항목이다.

## 확인한 기능

- python build.py 성공.
- 1440px, 390px, 320px에서 조사방법 이미지 6장 로딩 성공 및 문서 가로 넘침 없음.
- 800×800 RGBA, 알파 최솟값 0·최댓값 255를 6장 모두 확인. 개별 파일 약 176~312 KiB.
- 두 OG 파일 모두 1200×630 확인.
- 생성된 전체 페이지의 OG 이미지 참조를 새 합성본으로 연결.
- 단일 파일 미리보기 _artifact.html에 조사방법 이미지 6장 내장 확인.
- git diff --check 통과.

## 검토 자료 및 재현

- [전체 이미지 비교표](contact-sheet.png)
- [데스크톱 페이지](methods-1440.png)
- [모바일 페이지](methods-390.png)
- [320px 페이지](methods-320.png)
- [모바일 상단 원래 크기](methods-mobile-top.png)
- [자동 확인 결과](checks.json)
- [공유용 최종 이미지](../../assets/og/og-image.png)
- [최종 프롬프트](../image-prompts.md)

재현: python build.py 실행 후 python docs/image-quality/verify.py 실행.
verify.py는 Pillow로 파일을 검사하고 Playwright로 OG HTML을 캡처하여 og-image.png를 재생성한다. Chromium, Pillow, Playwright와 Windows의 맑은 고딕이 필요하다. 운영 서버 응답이나 메신저 공유 캐시는 이번 로컬 검토에 포함하지 않는다.
