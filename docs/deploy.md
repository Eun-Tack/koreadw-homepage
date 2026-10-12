# 배포 방법

페이지끼리의 링크와 이미지 경로는 **전부 상대 경로**입니다.
그래서 루트든 하위 폴더든, 어느 호스팅에 올려도 그대로 동작합니다.

절대 주소가 필요한 곳은 `og:url` / `og:image` 두 군데뿐이고,
이건 빌드할 때 지정합니다. 카카오톡·슬랙에 링크를 보냈을 때
뜨는 미리보기 썸네일에 쓰입니다.

## 빌드 명령

| 명령 | 기준 주소 | 쓰임 |
|---|---|---|
| `python build.py` | `https://eun-tack.github.io/koreadw-homepage/` | **시연용 (기본값)** |
| `python build.py --prod` | `https://www.koreadw.co.kr/` | 실제 납품용 |
| `python build.py --base=https://...` | 지정한 주소 | Vercel 등 임시 주소 |
| `--bundle` 추가 | — | `dist/` 에 올릴 파일만 따로 모음 |

## 1. GitHub Pages (현재 시연용)

```
python build.py
git add -A && git commit -m "..." && git push
```

푸시하면 자동 배포됩니다. 주소는 https://eun-tack.github.io/koreadw-homepage/

## 2. Vercel (시연용)

GitHub 저장소를 그대로 연결하면 됩니다. 빌드 설정이 필요 없습니다
(Framework Preset: Other, Build Command 비움, Output Directory 비움).

배포 주소를 받은 뒤 썸네일까지 맞추려면 그 주소로 다시 빌드해서 푸시합니다.

```
python build.py --base=https://받은주소.vercel.app
```

> 참고: Vercel 무료(Hobby) 플랜은 약관상 개인·비상업 용도입니다.
> 시연은 괜찮지만 고객사 운영 사이트로 쓰려면 Pro 결제가 필요합니다.

## 3. 후이즈 웹호스팅 (실제 납품)

```
python build.py --prod --bundle
```

`dist/` 폴더가 만들어집니다. **그 안의 내용물을** FTP로 웹 루트에 올리면 됩니다
(`dist` 폴더째가 아니라 안의 `index.html`, `assets/`, `company/` ... 를 올립니다).

올라가는 것은 HTML과 이미지뿐입니다. PHP·데이터베이스가 필요 없습니다.

```
dist/
  index.html
  assets/      (css, js, 이미지, 로고, 파비콘)
  company/     greeting, history, organization, people, location
  business/    fields, methods, special, platform, process
  support/     notice, contact
```

### 올린 뒤 확인할 것

- 기존 PHP 사이트 파일과 섞이지 않게, 올리기 전에 **기존 파일을 백업**해 둡니다
- `index.html` 이 기존 `index.php` 보다 먼저 열리는지 확인합니다.
  안 되면 호스팅의 기본 문서(DirectoryIndex) 설정을 바꾸거나 `index.php` 를 치웁니다
- HTTPS 인증서 — 현재 자체서명 더미라 브라우저 경고가 뜹니다.
  후이즈에 정식 인증서 발급을 요청하세요

## 콘텐츠만 고칠 때

공지·연혁·연구원은 `content/` 안의 텍스트 파일만 고치면 됩니다.
빌드 스크립트를 열 필요가 없습니다.

```
content/notices.md   공지사항
content/history.md   연혁 · 성장 스토리
content/people.md    연구원 프로필
```

고친 뒤 `python build.py` 를 실행하면 화면에 반영됩니다.
