# Spec: Portable Jukebox

## Objective

YouTube 영상/음악을 웹 UI에서 다운로드하고 로컬 서버에 저장하는 셀프호스팅 서비스.
Docker 컨테이너로 배포하며, 버전 업데이트 시 Watchtower가 자동 감지 → 재시작.

**사용자 스토리:**
- 사용자: URL 입력 → 포맷(mp4/mp3) 및 품질 선택 → 다운로드 → 저장된 파일 목록 확인
- 관리자: 계정 관리, 다운로드 로그 조회, 파일 자동 삭제 정책 설정

**성공 기준:**
- YouTube URL → mp4(해상도 선택) / mp3(음질 선택) 다운로드 완료
- 다운로드 파일이 마운트된 `/downloads` 경로에 저장됨
- 관리자가 설정한 보관 기간 초과 파일은 자동 삭제됨
- 버전 태그 push → GitHub Actions → Docker Hub → Watchtower 자동 업데이트

---

## Tech Stack

| 항목 | 선택 | 이유 |
|---|---|---|
| 백엔드 | Python 3.12 + FastAPI | yt-dlp 네이티브, async 지원 |
| 템플릿 | Jinja2 + HTMX + Alpine.js | SPA 불필요, 서버렌더링 유지하며 동적 UX |
| DB | SQLite + SQLAlchemy | 단일 파일, 별도 컨테이너 없음 |
| 다운로더 | yt-dlp | yt-dl 후속, 활발한 유지보수 |
| 인증 | 세션 쿠키 (Starlette SessionMiddleware) + bcrypt | JWT 불필요한 단순 구조, 자동 로그인은 RememberToken (DB 저장, 30일) |
| 자동 업데이트 | Watchtower | Docker Hub 이미지 변경 감지 |
| CI/CD | GitHub Actions → Docker Hub | EE-ONE-D 동일 패턴 |

---

## Commands

```bash
# 개발
uv run fastapi dev src/main.py

# 프로덕션 (Docker)
docker compose up -d

# DB 마이그레이션 (Alembic)
uv run alembic upgrade head

# 테스트
uv run pytest

# 이미지 빌드
docker build -t portable-jukebox .

# 버전 릴리즈 (GitHub Actions 트리거)
git tag v1.0.0 && git push origin v1.0.0
```

---

## Project Structure

```
portable-jukebox/
├── src/
│   ├── main.py              # FastAPI 앱 진입점, 초기 관리자/설정 시드
│   ├── auth.py              # 세션 인증, 비밀번호 복잡성 검증
│   ├── activity.py          # ActivityLog 기록 유틸
│   ├── models.py            # SQLAlchemy 모델
│   ├── database.py          # DB 연결, 세션 팩토리
│   ├── downloader.py        # yt-dlp 래퍼 (ThreadPoolExecutor, 진행률 추적)
│   ├── scheduler.py         # APScheduler — 파일 자동 삭제 크론
│   ├── routers/
│   │   ├── user.py          # 로그인/로그아웃, 다운로드, 비밀번호 변경
│   │   └── admin.py         # 계정 관리, 시스템 로그, 설정
│   └── templates/
│       ├── base.html
│       ├── admin_base.html
│       ├── login.html
│       ├── dashboard.html      # 사용자 메인 (다운로드 폼 + 파일 목록)
│       ├── change_password.html
│       ├── partials/
│       │   └── history_list.html
│       └── admin/
│           ├── users.html
│           ├── logs.html
│           └── settings.html
├── alembic/                 # DB 마이그레이션 (미구현, TODO)
├── tests/
│   └── test_auth.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── CHANGELOG.md
```

---

## Data Models

```python
# User: id, username, hashed_password, role (admin|user), is_active, must_change_password, created_at
# DownloadLog: id, user_id, url, title, filename, format, quality, file_size,
#              status (pending|downloading|done|error), downloaded_at, deleted_at
# AppSetting: key, value
#   keys: retention_days, default_password,
#         pw_min_length, pw_require_upper, pw_require_number, pw_require_special
# RememberToken: id, user_id, token_hash, expires_at, created_at  # 자동 로그인 (30일)
# ActivityLog: id, event_type, username, detail (JSON), created_at
#   event_types: login_ok, login_fail, logout, password_change,
#                download_done, download_fail,
#                user_create, user_delete,
#                settings_change, auto_delete
```

---

## API Routes

### 인증
- `GET/POST /login` — 로그인 폼 (자동 로그인 쿠키 처리 포함)
- `GET /logout` — 세션 삭제 + RememberToken 파기

### 사용자 (로그인 필요)
- `GET /` — 대시보드 (다운로드 폼 + 파일 목록, admin이면 `/admin/users` 리다이렉트)
- `POST /download` — 다운로드 요청 (url, format, quality)
- `GET /download/status/{task_id}` — 진행률 폴링 (HTMX 2초 간격)
- `GET/POST /change-password` — 비밀번호 변경 (최초 로그인 시 강제)

### 관리자 (`role=admin` 필요)
- `GET /admin/users` — 계정 목록
- `POST /admin/users` — 계정 생성 (기본 패스워드 자동 적용)
- `DELETE /admin/users/{id}` — 계정 소프트 삭제 (`is_active=False`)
- `GET /admin/logs` — 시스템 로그 (카테고리 필터: auth/download/account/system)
- `GET/POST /admin/settings` — 보관 기간, 기본 패스워드, 비밀번호 복잡성 설정

---

## Docker 구성

```yaml
# docker-compose.yml 구조
services:
  app:
    image: hellojamong/portable-jukebox:latest
    volumes:
      - ./downloads:/downloads   # 로컬 저장 경로
      - ./data:/app/data         # SQLite DB
    ports:
      - "8000:8000"
    env_file: .env
    restart: unless-stopped

  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 300 portable-jukebox-app-1
    restart: unless-stopped
```

---

## 자동 삭제 정책

- `AppSetting` 테이블에 `retention_days` 키 저장 (기본값: 30일, 0 = 비활성)
- APScheduler가 매일 자정 `DOWNLOAD_DIR` 스캔 → `downloaded_at + retention_days < now` 파일 삭제
- 삭제 시 `DownloadLog.deleted_at` 업데이트, `ActivityLog`에 `auto_delete` 이벤트 기록

## 동시 다운로드 제한

- 전체 동시 다운로드 최대 **3개** (`ThreadPoolExecutor(max_workers=3)` + `threading.Semaphore(3)`)
- 사용자별 제한 없음, 서버 전체 기준

---

## CI/CD (GitHub Actions)

EE-ONE-D 동일 패턴:
- 트리거: `git tag v*.*.*`
- 빌드 → Docker Hub push (`:latest` + `:v*.*.*`)
- GitHub Release 생성 (CHANGELOG 기반 릴리즈 노트)
- 릴리즈 첨부파일: `docker-compose.yml`, `.env.example`
- Watchtower가 새 `:latest` 이미지 감지 → 자동 재시작

---

## Code Style

```python
# 라우터 예시
@router.post("/download")
async def start_download(
    request: DownloadRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    task_id = await downloader.enqueue(request.url, request.format, request.quality, log.id, user.username)
    return HTMLResponse(_progress_html(task_id, 0, "pending"))
```

- 타입 힌트 필수
- Pydantic v2 request/response 모델
- 라우터별 파일 분리 (user.py / admin.py)
- 환경변수: `python-dotenv` + `.env.example` 유지

---

## Testing Strategy

- **프레임워크**: pytest + httpx (FastAPI TestClient)
- **커버리지 대상**: auth 흐름, downloader 래퍼, scheduler 삭제 로직
- **DB**: 테스트용 인메모리 SQLite
- **yt-dlp**: mock (실제 네트워크 호출 불필요)
- 실행: `uv run pytest`

---

## Boundaries

- **Always:** 환경변수로 시크릿 관리, 비밀번호 bcrypt 해싱, 권한 체크 미들웨어 통과 후 라우터 진입
- **Ask first:** DB 스키마 변경, 의존성 추가, 포트/볼륨 구조 변경
- **Never:** `.env` 커밋, `/downloads` 외부 경로 접근, `sudo` 실행

---

## Open Questions

1. **초기 관리자 계정**: ✅ `.env`의 `ADMIN_USERNAME` / `ADMIN_PASSWORD`로 앱 최초 실행 시 자동 생성
2. **동시 다운로드 제한**: ✅ 전체 3개로 결정 및 구현
3. **파일 브라우저**: 저장 파일 목록에서 직접 다운로드(브라우저로 전송) 기능 필요? → 미구현, 필요 시 추가

---

## Implementation Phases

### Phase 1 — 기반
- [x] 프로젝트 초기화 (pyproject.toml, uv, FastAPI)
- [x] DB 모델 (`Base.metadata.create_all`, Alembic은 미도입)
- [x] 세션 인증 (로그인/로그아웃, 권한 미들웨어, 자동 로그인, 비밀번호 변경)

### Phase 2 — 핵심 기능
- [x] yt-dlp 래퍼 (ThreadPoolExecutor, 진행률 추적, 오류 분류)
- [x] 다운로드 UI (폼 + HTMX 실시간 진행률 폴링)
- [x] 파일 목록 (대시보드 통합, 최근 20건)

### Phase 3 — 관리자
- [x] 계정 관리 UI (생성/소프트 삭제, 기본 패스워드 자동 적용)
- [x] 시스템 로그 조회 (카테고리 필터, 최대 200건)
- [x] 자동 삭제 정책 설정 + APScheduler (보관 기간, 비밀번호 복잡성)

### Phase 4 — 배포
- [x] Dockerfile (multi-stage, Python slim)
- [x] docker-compose.yml (app + watchtower)
- [x] GitHub Actions CI/CD (EE-ONE-D 패턴)
- [x] .env.example, CHANGELOG.md 초기화
