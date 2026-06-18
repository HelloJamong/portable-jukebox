# Changelog

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
