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
| 인증 | 세션 쿠키 (itsdangerous) | JWT 불필요한 단순 구조 |
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
│   ├── main.py              # FastAPI 앱 진입점
│   ├── auth.py              # 세션 인증, 로그인/로그아웃
│   ├── models.py            # SQLAlchemy 모델 (User, DownloadLog)
│   ├── database.py          # DB 연결, 세션 팩토리
│   ├── downloader.py        # yt-dlp 래퍼 (비동기 다운로드)
│   ├── scheduler.py         # APScheduler — 파일 자동 삭제 크론
│   ├── routers/
│   │   ├── user.py          # 다운로드, 파일 목록 엔드포인트
│   │   └── admin.py         # 계정 관리, 로그, 설정 엔드포인트
│   └── templates/
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html   # 사용자 메인 (다운로드 폼 + 파일 목록)
│       └── admin/
│           ├── users.html
│           ├── logs.html
│           └── settings.html
├── static/
│   └── app.js               # 다운로드 진행률 폴링
├── alembic/                 # DB 마이그레이션
├── tests/
│   ├── test_auth.py
│   ├── test_downloader.py
│   └── test_scheduler.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── CHANGELOG.md
```

---

## Data Models

```python
# User: id, username, hashed_password, role (admin|user), created_at, is_active
# DownloadLog: id, user_id, url, filename, format, quality, file_size, downloaded_at, deleted_at
# AppSetting: key, value  # 관리자 설정 (보관 기간 등)
```

---

## API Routes

### 인증
- `GET/POST /login` — 로그인 폼
- `POST /logout` — 세션 삭제

### 사용자 (로그인 필요)
- `GET /` — 대시보드 (다운로드 폼 + 파일 목록)
- `POST /download` — 다운로드 요청 (url, format, quality)
- `GET /download/status/{task_id}` — 진행률 폴링
- `GET /files` — 저장된 파일 목록

### 관리자 (`role=admin` 필요)
- `GET /admin/users` — 계정 목록
- `POST /admin/users` — 계정 생성
- `DELETE /admin/users/{id}` — 계정 삭제
- `GET /admin/logs` — 다운로드 로그
- `GET/POST /admin/settings` — 자동 삭제 정책 설정

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
- APScheduler가 매일 자정 `/downloads` 스캔 → `downloaded_at + retention_days < now` 파일 삭제
- 삭제 시 `DownloadLog.deleted_at` 업데이트

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
    user: User = Depends(require_user),
) -> DownloadResponse:
    task_id = await downloader.enqueue(request.url, request.format, request.quality)
    return DownloadResponse(task_id=task_id)
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

1. **초기 관리자 계정**: `.env`의 `ADMIN_USERNAME` / `ADMIN_PASSWORD`로 앱 최초 실행 시 자동 생성? → 기본값으로 진행 예정
2. **동시 다운로드 제한**: 사용자당 1개? 전체 N개? → 우선 전체 3개로 진행
3. **파일 브라우저**: 저장 파일 목록에서 직접 다운로드(브라우저로 전송) 기능 필요? → 필요 시 추가

---

## Implementation Phases

### Phase 1 — 기반
- [ ] 프로젝트 초기화 (pyproject.toml, uv, FastAPI)
- [ ] DB 모델 + Alembic 마이그레이션
- [ ] 세션 인증 (로그인/로그아웃, 권한 미들웨어)

### Phase 2 — 핵심 기능
- [ ] yt-dlp 래퍼 (비동기, 진행률 추적)
- [ ] 다운로드 UI (폼 + 실시간 진행률 폴링)
- [ ] 파일 목록 페이지

### Phase 3 — 관리자
- [ ] 계정 관리 UI
- [ ] 다운로드 로그 조회
- [ ] 자동 삭제 정책 설정 + APScheduler

### Phase 4 — 배포
- [ ] Dockerfile (multi-stage, Python slim)
- [ ] docker-compose.yml (app + watchtower)
- [ ] GitHub Actions CI/CD (EE-ONE-D 패턴)
- [ ] .env.example, CHANGELOG.md 초기화
