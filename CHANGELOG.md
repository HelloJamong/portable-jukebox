# Changelog

## [26.5.7] - 2026-06-19

### Fixed
- **Synology Container Manager 이미지 업데이트 미감지 수정** — `docker/build-push-action@v5`의 기본 provenance attestation으로 인해 OCI image index 형식으로 push되어 Synology가 digest 비교에 실패하던 문제 수정. `provenance: false` 옵션 추가로 단순 단일 플랫폼 manifest로 push되도록 변경

## [26.5.6] - 2026-06-18

### Fixed
- **로고 이미지 404 수정** — `src/img/logo.ico`가 `static/` 디렉터리에 없어 템플릿 4곳(base.html, dashboard.html, login.html, admin_base.html)에서 로고가 표시되지 않던 문제 수정
- **다운로드 대기 상태바 40% 고정 표시 수정** — pending 구간에서 진행 막대가 40% 너비로 고정되어 실제 진행값처럼 오해되던 문제 수정. `w-full animate-pulse`로 변경해 불확정 로딩 상태 명확화
- **다운로드 완료·오류 후 이력 자동 갱신 수정** — `hx-trigger="load"` 방식이 HTMX 2.x `outerHTML` swap 이후 불안정하게 발화되던 문제 수정. 상태 폴링 응답에 HTMX OOB swap으로 `#history-list`를 직접 포함해 완료 즉시 목록 갱신

### Changed
- **SQLAlchemy filter 비교 연산자 수정** — `== None` · `== True` 7곳을 `.is_(None)` · `.is_(True)`로 교체 (E711/E712)
- **코드 스타일 정리** — `models.py` SQLAlchemy import 순서(E402), `database.py` 빈 줄 누락(E302), `user.py` 함수 내부 import(E402) 수정

## [26.5.5] - 2026-06-18

### Fixed
- **다운로드 진행률 막대 미표시 수정** — 진행률 0%일 때 bar width가 0px로 막대가 보이지 않던 문제 수정. 진행률 미확인 구간에는 40% 너비 + animate-pulse 애니메이션으로 "진행 중" 상태 시각 표시, 실제 진행률 확인 시 실제 막대로 전환
- **다운로드 완료 후 이력 미갱신 수정 (재수정)** — HTMX 2.x에서 `hx-swap="outerHTML"` 응답의 OOB swap 신뢰성 문제로 히스토리가 자동 갱신되지 않던 문제 수정. 완료/오류 응답 div에 `hx-trigger="load"`를 적용해 DOM 삽입 즉시 `/download/history`를 별도 요청으로 fetch하여 `#history-list` 교체

## [26.5.4] - 2026-06-18

### Fixed
- **다운로드 진행률 0% 고착 수정** — yt-dlp가 `total_bytes`를 제공하지 않을 때 진행률이 항상 0%로 고착되던 문제 수정. yt-dlp 자체 계산값(`_percent_str`)을 1순위로 사용하도록 변경, `total_bytes` 없이도 실제 진행률 표시
- **다운로드 완료 후 이력 미갱신 수정** — 다운로드 완료 시 DB 커밋 전에 `TASKS["done"]`이 설정되는 race condition 수정. DB 커밋 후 TASKS 상태 변경으로 순서 변경, HTMX OOB swap으로 이력이 즉시 갱신됨

## [26.5.3] - 2026-06-18

### Fixed
- **Bitwarden Shadow DOM 우회 완전 해결** — Bitwarden이 `<bit-notification-bar-root>` 커스텀 엘리먼트에 closed Shadow DOM으로 알림 바를 주입해 `getElementById`로 접근 불가하던 문제 수정. Shadow DOM 내부 대신 호스트 요소(`bit-notification-bar-root`)를 직접 `querySelector`로 찾아 제거하도록 변경

## [26.5.2] - 2026-06-18

### Fixed
- **Bitwarden 알림 바 완전 차단** — `autocomplete="off"`를 form 레벨뿐만 아니라 username·password 개별 필드에도 적용. MutationObserver로 `#bit-notification-bar` DOM 주입 즉시 제거해 클릭 차단 문제 근본 해결

### Changed
- **시스템 로그 페이지당 표시 수 선택 UI 변경** — 버튼 그룹 → 드롭다운 셀렉트로 교체
- **관리자 페이지 콘텐츠 폭 유동화** — `max-w-5xl` 고정 폭 제거, 화면 너비에 따라 자동 확장되도록 수정

## [26.5.1] - 2026-06-18

### Fixed
- **푸터 이중 v 제거** — `APP_VERSION`이 이미 `v` 접두사를 포함하고 있어 `Release-vv26.x.x`로 표시되던 문제 수정 (`Release-v{{ app_version }}` → `Release-{{ app_version }}`)
- **관리자 푸터 위치 수정** — 관리자 페이지 outer div에 `flex flex-col`, `<main>`에 `flex-1` 추가로 콘텐츠가 적을 때 푸터가 화면 하단에 고정되도록 수정

### Changed
- **푸터 통일** — 사용자/관리자 푸터를 `Release-버전 / © 2026 Portable-Jukebox Service. All rights reserved. / GitHub 아이콘` 구조로 통일

## [26.5.0] - 2026-06-18

### Added
- **시스템 로그 페이지네이션** — 페이지당 표시 건수 선택(20/30/50/100, 기본값 30)과 페이지 이동 기능 추가. 카테고리 필터와 페이지당 표시 건수 설정이 페이지 이동 시 유지됨

### Fixed
- **Bitwarden 알림 바로 인한 헤더 버튼 클릭 불가 수정** — 로그인 폼에 `autocomplete="off"` 추가. Bitwarden이 로그인 성공을 감지해 dashboard/admin 우측 상단에 주입하던 `#bit-notification-bar`(z-index: 2147483647) 차단

## [26.4.4] - 2026-06-18

### Fixed
- **Brave bfcache 복원으로 인한 버튼 클릭 불가 근본 해결** — `Cache-Control: no-store` 미들웨어만으로는 Brave 일부 버전에서 bfcache 복원을 막지 못하는 버그 우회. `pageshow` 이벤트에서 `e.persisted === true` 감지 시 즉시 `location.reload()`를 호출해 bfcache 복원 페이지를 강제로 신선하게 재로드. Alpine.js·HTMX가 항상 새 상태로 초기화되어 버튼 이벤트 핸들러가 올바르게 등록됨

## [26.4.3] - 2026-06-18

### Fixed
- **Brave 브라우저 로그아웃 버튼 차단 문제 해결** — Brave의 "Bounce Tracking Prevention"이 `GET /logout → 302 → /login` 리다이렉트 체인을 트래킹 bounce로 오탐해 내비게이션을 차단하던 문제 수정. 로그아웃을 `<a href>` GET에서 `<form method="post">` POST 방식으로 변경(POST→303→GET은 표준 PRG 패턴으로 차단되지 않음). 백엔드도 GET·POST 모두 수용하도록 `@router.post("/logout")` 추가
- **Brave Fingerprinting Protection 대응** — `localStorage` 접근을 `try/catch`로 감싸 Brave의 aggressive 지문 차단 모드에서 FOSC 스크립트 또는 `themeToggle()`이 예외를 던져도 Alpine.js 초기화에 영향을 주지 않도록 수정
- **Bitwarden 알림 바 차단** — 로그인 폼에 `autocomplete="off"` 추가로 Bitwarden이 로그인 폼을 추적하지 않게 하여 로그인 후 dashboard/admin 우측 상단에 주입되던 `#bit-notification-bar`(z-index: 2147483647) 제거

## [26.4.2] - 2026-06-18

### Fixed
- **로그인 후 헤더 버튼 클릭 불가 근본 원인 수정** — 세 가지 원인 동시 해결
  1. HTMX `historyEnabled: false` — 이전 방문 시 저장된 page snapshot이 로그인 후 복원되며 폴링을 재개시켜 탭 스피너·이벤트 간섭을 유발하던 문제 제거
  2. 관리자 헤더에 `sticky top-0 z-50` 추가 — z-index 없던 헤더가 `<main>` 요소에 가려지던 stacking context 문제 해결 (사용자 헤더와 동일하게 맞춤)
  3. HTML 응답에 `Cache-Control: no-store` 미들웨어 추가 — 브라우저 bfcache가 이전 페이지 상태를 재사용하지 못하도록 차단

## [26.4.1] - 2026-06-18

### Fixed
- **헤더 버튼 클릭 불가 완전 해결** — Pretendard(jsdelivr)·Font Awesome(cdnjs) 외부 CSS가 render-blocking 리소스로 작동해 Alpine.js 초기화가 지연되던 문제 제거. Docker 빌드 시 Font Awesome CSS·웹폰트(woff2 3종) 및 Pretendard Variable 폰트를 `/static/`에 내려받아 로컬 서빙으로 전환, 외부 CDN 의존성 완전 제거

## [26.4.0] - 2026-06-18

### Added
- **다크/라이트 모드** — 시스템 설정 자동 감지(`prefers-color-scheme`), 로그인 후 헤더 토글 버튼으로 전환, `localStorage` 에 설정 저장. FOSC 방지용 인라인 스크립트로 깜빡임 없이 적용

## [26.3.3] - 2026-06-18

### Fixed
- **로그인 후 버튼 클릭 불가 문제 완전 해결** — HTMX(`unpkg.com`)·Alpine.js(`jsdelivr.net`)를 Docker 빌드 시 정적 파일로 내려받아 `/static/`에서 서빙, 외부 CDN JS 의존 완전 제거. `<script defer>`로 메인 스레드 블로킹 없음

## [26.3.2] - 2026-06-18

### Fixed
- `user.py`에 `import os` 누락으로 컨테이너 시작 시 `NameError` 발생하던 문제 수정

## [26.3.1] - 2026-06-18

### Added
- **버전 표시** — 대시보드·관리자 패널 좌측 하단에 `Release-v{버전}` 표시, Docker 빌드 시 `APP_VERSION` 환경 변수로 자동 주입

## [26.3.0] - 2026-06-18

### Added
- **다운로드 이력 정리 버튼** — `DELETE /download/{log_id}` 엔드포인트 추가, 완료·오류 항목에 정리 버튼 표시, 클릭 시 실제 파일 삭제 및 이력 soft delete (HTMX로 행 즉시 제거)
- **로고 적용** — `logo.ico`를 파비콘, 로그인·대시보드·관리자 화면 헤더 및 중앙 로고 영역에 적용

### Fixed
- **버튼 클릭 불가 문제 해결** — Tailwind Play CDN(동기 JS, MutationObserver 재컴파일)을 제거하고 Docker 빌드 시 Tailwind CLI로 정적 CSS 컴파일로 교체, Alpine.js 초기화 이후 메인 스레드 블로킹 제거
- **SQLite WAL 모드 활성화** — 다운로드 백그라운드 스레드와의 write lock 경합 해소

## [26.2.2] - 2026-06-18

### Fixed
- HTMX 폴링 무한 루프 방지 — `_progress_html()`이 `poll` 카운터를 URL에 포함해 전달하고, 300회(10분) 초과 시 폴링을 중단하고 타임아웃 메시지 반환
- yt-dlp hung 등으로 다운로드가 stuck될 경우 탭이 영구 로딩 상태에 빠지는 문제 해결

## [26.2.1] - 2026-06-18

### Fixed
- 다운로드 진행 중 로그아웃 버튼이 눌리지 않는 문제 수정 — `_progress_html()`이 생성하는 폴링 `<div>`에 `id="progress-container"`가 중복 부여되어 DOM에 같은 ID 요소가 2~3개 중첩되는 버그 제거
- 다운로드 완료·오류·작업 없음 응답에서도 동일한 `id="progress-container"` 중복 제거
- `hx-swap-oob="true"` → `hx-swap-oob="outerHTML"` 명시 (HTMX 2.x 권장 방식)

## [26.2.0] - 2026-06-18

### Added
- **파일 직접 다운로드** — `GET /files/{filename}` 엔드포인트 추가, 파일 목록에서 브라우저로 직접 전송 (path traversal 방어 포함)
- **테스트 커버리지** — `test_auth.py` 확장(로그인 흐름·권한·복잡성 검증), `test_downloader.py`·`test_scheduler.py` 신규 작성 (총 16개)
- **Alembic 마이그레이션** — 초기 스키마 리비전 생성, `alembic upgrade head` 적용

## [26.1.1] - 2026-06-18

### Fixed
- 다운로드 완료/오류 후 `TASKS` 딕셔너리에 항목이 무한 누적되는 메모리 누수 수정 (완료 후 10분 자동 제거)

### Changed
- SPEC.md 현행화 — 구현된 모델/라우트/구조를 실제 코드 기준으로 갱신
- `pyproject.toml`에 dev 의존성 명시 추가 (`pytest>=8.0.0`, `httpx>=0.27.0`)

### Removed
- 푸터 `Vinsign` 브랜딩 텍스트 제거

## [26.1.0] - 2026-06-18

### Added
- **아이디 저장** — 로그인 페이지 체크박스, localStorage에 아이디 보존
- **자동 로그인** — 보안 토큰 기반 30일 유지, 로그아웃 시 서버 토큰 즉시 파기
- **비밀번호 변경** — 관리자/사용자 헤더에 버튼 추가, 언제든 변경 가능
- **시스템 로그** — 로그인/로그아웃, 다운로드, 계정 관리, 설정 변경, 자동 삭제 이력 통합 기록
- **로그 카테고리 필터** — 인증 / 다운로드 / 계정 관리 / 시스템 4개 카테고리로 필터링
- **다운로드 오류 분류** — 잘못된 URL, 비공개/멤버십, 403/404, 네트워크 오류, 저작권 등 유형별 상세 메시지
- **최초 로그인 비밀번호 변경 강제** — 신규 계정 첫 로그인 시 변경 화면으로 강제 이동
- **기본 패스워드 설정** — 관리자 설정 페이지에서 신규 계정 초기 비밀번호 지정
- **패스워드 복잡성 설정** — 최소 자릿수, 대문자/숫자/특수문자 포함 여부 설정 가능
- **계정 생성 간소화** — 비밀번호 입력란 제거, 설정의 기본 패스워드 자동 적용
- **KST 시간 적용** — DB 저장 시각 전체 한국 표준시(UTC+9) 기준으로 통일

### Changed
- 관리자 계정으로 일반 다운로드 페이지(`/`) 접근 차단, 어드민 패널로 자동 리다이렉트
- 다운로드 로그 페이지 → 시스템 로그 페이지로 개편 (네비게이션 탭명 포함)
- 서비스 명칭 전체 변경: `YouTube Downloader` → `Portable-Jukebox`
- 푸터 문구 변경: `Vinsign YouTube Downloader Service` → `Vinsign Portable-Jukebox Service`
- Tailwind CDN `@tailwindcss/browser@4` → `cdn.tailwindcss.com` 교체 (브라우저 freeze 해결)
- 로그아웃 버튼 `<form POST>` 방식 → `<a href="/logout">` GET 방식으로 변경 (터치 기기 호환)
- 프로필 아바타 이미지 제거 (외부 API 요청으로 인한 페이지 지연 원인 제거)

## [0.1.0] - 2026-06-17

### Added
- YouTube 영상(mp4) / 음악(mp3) 다운로드
- 해상도(1080p/720p/480p/360p) 및 음질(320/192/128/96kbps) 선택
- 웹 UI — HTMX 실시간 진행률, Alpine.js 포맷 토글
- 관리자/사용자 계정 분리 (세션 인증)
- 관리자 패널 — 계정 관리, 다운로드 로그, 파일 자동 삭제 설정
- Docker 배포 지원 (Watchtower 자동 업데이트)
