---
name: nextjs-init
description: Scaffold a new Next.js project with the opinionated stack (Mantine, Better Auth, DynamoDB). 새 Next.js 프로젝트 생성·초기 셋업·보일러플레이트.
---

# Next.js Project Init

**한국어로 응답. 코드·명령어는 원문 유지** (AGENTS.md 의 Language).

새 Next.js 프로젝트를 정해진 스택으로 부트스트랩한다. 시크릿 취급은 AGENTS.md 의 Security, 커밋은 AGENTS.md 의 Git Safety 를 따른다 — **이 스킬은 커밋하지 않는다**.

## Philosophy

- **스캐폴더의 *설정*은 다시 만들지 않는다** — `tsconfig`·`next.config.ts` 는 손대지 않고 *비자명한 부분*(레이어 경계·키 설계·어댑터·배포)만 추가한다. `eslint.config.mjs` 도 다시 쓰지 않고 3단계에서 배열에 객체 하나를 끼운다. **PostCSS 설정은 이 규칙 밖이다** — `--no-tailwind` 로 만들면 `postcss.config.mjs` 가 *아예 생기지 않으므로* 2단계에서 Mantine 용으로 새로 만드는 것이다. **데모 페이지·스타일시트·브랜딩 에셋도 예외다** — 남길 이유가 없으므로 2단계에서 걷어낸다
- **경계가 곧 아키텍처다** — 디렉토리 이름이 아니라 *의존 방향*을 lint 로 강제해야 유지된다
- **접근 패턴을 먼저 정하고 테이블을 만든다** — Single Table Design 은 나중에 GSI 를 붙여 고칠 수 없다
- **단계마다 검증하고 넘어간다** — 각 단계에 종료 조건이 있다 (`skills/problem-solving/SKILL.md#goal-driven-execution--목표-기반-실행`)

## Stack

| 영역 | 선택 | 고정 사항 |
|------|------|-----------|
| Runtime | Node.js 24 (LTS), pnpm 11 | `package.json` 의 `packageManager` 필드로 고정, corepack 사용 |
| Framework | Next.js 16 (App Router), React 19 | Turbopack 기본, `middleware.ts` 없음 → `proxy.ts` |
| Language | TypeScript 6 | `strict: true` 필수. `typescript@^6` 로 **핀한다** — 7.x 는 lint·build 를 깬다 (2단계) |
| Style | Mantine 9 | `@mantine/core` + `@mantine/hooks`. `styles.layer.css` 로 import 하고 내 CSS 는 `postcss-preset-mantine` 이 컴파일한다. **Tailwind 없음** — `--no-tailwind` 로 스캐폴딩한다 |
| Theme | Mantine 컬러 스킴 | `ColorSchemeScript` + `data-mantine-color-scheme` + localStorage. next-themes 를 쓰지 않는다 |
| UI | 화면 1개 (`/`) | 템플릿·샘플만 제거. `/` 는 프로젝트명·테마 토글·로그인 버튼뿐이고 셋 다 Mantine 컴포넌트다. 인증은 화면이 아니라 API 라우트로 붙는다 |
| Auth | Better Auth 1.6 + Google OAuth | 커스텀 DynamoDB 어댑터 |
| Data | AWS DynamoDB Single Table Design | `@aws-sdk/lib-dynamodb` DocumentClient. 개발·테스트는 DynamoDB Local |
| Structure | Clean Architecture | `domain` / `application` / `infrastructure` / `app` |
| Testing | Vitest 4 + DynamoDB Local | 게이트는 `vitest run` (watch 금지). 로컬 DB 2개 — dev `:8083` 유지, test `:8084` 초기화 |
| Deploy | Docker standalone → AWS ECR | GitHub Actions + OIDC |

**버전은 기본값일 뿐 절대 규칙이 아니다.** 사용자가 다른 버전·구성을 요청하면 그쪽을 따른다.

## Scope

- **한다**: 프로젝트 생성, 템플릿·샘플 제거 + `/` 화면(프로젝트명·테마 토글·로그인), 레이어 뼈대, 인증 배선(API 라우트 포함), DynamoDB 어댑터, 접근 패턴·어댑터 계약 테스트, Dockerfile, CI 워크플로, `.env.example`
- **안 한다**: 도메인 비즈니스 로직, 요청하지 않은 *화면*·UI 디자인, AWS 리소스 *실제 생성*, git commit/push
- **지우지 않는다**: 동작에 필요한 파일 — 설정·인증 라우트·레이아웃. 삭제 대상은 템플릿·샘플뿐이다 (2단계 표)
- **경계**: 기존 프로젝트 수정은 이 스킬 대상이 아니다. 검증은 `/validate`, 커밋은 `/commit`.

## Rules

- **빈 디렉토리에서만 생성한다** — 대상 경로에 파일이 있으면 멈추고 사용자에게 확인한다
- **진짜 시크릿을 파일에 쓰지 않는다** — Google client secret 등 *발급받은* 값은 사용자가 `.env.local` 에 채운다. 저장소에는 `.env.example` 만 둔다 — 단 스캐폴더의 `.gitignore` 가 `.env*` 로 그것까지 막으므로 `!.env.example` 을 넣어야 실제로 커밋된다 (5단계). **예외는 로컬 전용으로 새로 만드는 무작위 값**(`BETTER_AUTH_SECRET`) — 어디서도 발급받은 적 없고 gitignore 된 파일에만 있으므로 스킬이 생성한다 (5단계)
- **AWS 계정에 리소스를 만들지 않는다** — DynamoDB 테이블·ECR 리포지토리·IAM 역할 생성은 명령을 *제시*만 하고 실행은 사용자가 한다. **로컬 DynamoDB 컨테이너는 예외** — AWS 리소스가 아니므로 직접 띄우고 테이블도 만든다 (4단계)
- **git 초기화·커밋은 사용자 요청 시에만** — `--disable-git` 으로 생성한다
- 각 단계의 검증을 통과하지 못하면 다음 단계로 넘어가지 않는다

## Process

8단계를 순서대로 진행한다. 각 단계의 상세 절차·근거·검증 조건은 이 스킬 디렉토리의 `references/` 파일이 담는다 — **단계를 시작하기 전에 해당 파일을 읽고, 기억만으로 진행하지 않는다.**

| 단계 | 내용 | 상세 |
|------|------|------|
| 1 | 사전 확인 — 환경·대상 경로·이름 확정 | `references/setup.md` |
| 2 | 스캐폴딩 — create-next-app·빌드 승인·Mantine·보일러플레이트 제거 | `references/setup.md` |
| 3 | 레이어 뼈대 — Clean Architecture + ESLint 강제 | `references/setup.md` |
| 4 | DynamoDB Single Table Design + 로컬 인스턴스 | `references/dynamodb.md` |
| 5 | Better Auth + Google OAuth + 커스텀 어댑터 | `references/auth.md` |
| 6 | 테스트 — Vitest + DynamoDB Local | `references/testing.md` |
| 7 | Docker + ECR 릴리스 (OIDC) | `references/deploy.md` |
| 8 | 검증 게이트 + README + CI | `references/deploy.md` |

단계 번호가 파일 간 상호 참조의 기준이다 — "4단계 함정 2", "5단계 계약 3" 같은 표기는 위 표의 해당 파일에서 찾는다.

## 완료 보고

```
## Next.js 프로젝트 생성 완료

경로: <path>
스택: Next.js 16 / React 19 / TS 6 strict / Mantine 9 / Better Auth 1.6 / DynamoDB / Vitest 4

검증:
- pnpm lint + tsc --noEmit: PASS (레이어 zones 위반 시 에러 확인 포함)
- pnpm test: PASS (접근 패턴 7/7, 어댑터 계약 5/5)
- pnpm build: PASS
- Google 로그인 플로우: PASS (또는 SKIP + 사유 — OAuth 클라이언트 미발급 등)
- docker build: PASS (또는 SKIP + 사유)

로컬에 이미 만들어 둔 것:
- 로컬 DynamoDB 2개 (dev :8083 / test :8084 — 다른 프로젝트가 이미 띄워 뒀으면 재사용) + dev 테이블 `<table>`

사용자 후속 작업 (실행하지 않음):
- [ ] **AWS** DynamoDB 테이블 생성 — 4단계 명령에서 `--endpoint-url` 만 빼면 된다 (로컬은 완료됨)
- [ ] ECR 리포지토리 생성 (tag mutability: MUTABLE) + IAM OIDC identity provider 등록(계정에 처음이면) + OIDC IAM 역할·신뢰 정책 — 7단계 참조
- [ ] Google OAuth 클라이언트 발급 + 리다이렉트 URI 등록
- [ ] `.env.local` 의 `GOOGLE_CLIENT_ID`·`GOOGLE_CLIENT_SECRET` 채우기 (나머지는 생성됨)
- [ ] 배포 시 `BETTER_AUTH_URL` 을 실제 오리진으로, `DYNAMODB_ENDPOINT` 를 빈 값으로
- [ ] git init / 첫 커밋 (요청 시)
- [ ] 첫 릴리스 — `git tag v0.1.0 && git push origin v0.1.0`
```

## Anti-Patterns

단계 안에서 끝나는 함정은 각 `references/` 파일이 본문에서 다룬다. 아래는 *원인 단계와 증상 단계가 달라* 파일 하나만 읽어서는 놓치기 쉬운 것만 모은다.

- `pnpm-workspace.yaml`(`allowBuilds`)을 커밋이나 Dockerfile 의 deps COPY 에서 빠뜨리지 않는다 — CI·Docker 에는 승인을 눌러 줄 사람이 없다 (2단계 → 7단계)
- `public/` 을 빈 디렉토리로 남기지 않는다 — git 이 추적하지 않아 CI 의 `docker build` 만 `COPY public` 에서 죽는다. `.gitkeep` 을 둔다 (2단계 → 7단계)
- `postcss.config.mjs` 를 Docker 이미지에서 빠뜨리지 않는다 — CSS 모듈의 Mantine mixin 이 조용히 컴파일되지 않는다 (2단계 → 7단계)
- `typescript` 를 `@latest`(7.x)로 올리지 않는다 — lint(3단계)와 build(8단계)가 함께 죽는다. 상한은 `<6.1.0` (2단계)
- `globalSetup` 의 리전·테이블명을 `test.env` 와 다르게 두지 않는다 — 로컬은 `-sharedDb` 가 가려 주고 CI 에서만 깨진다 (6단계 → CI)
- 쓰기 직후 GSI 읽기를 강일관으로 가정하지 않는다 — DynamoDB Local 은 동기, 실제 DynamoDB 는 eventually consistent 라 로컬에서만 통과한다 (4단계 → 운영)
- `DYNAMODB_ENDPOINT`·`BETTER_AUTH_URL` 의 로컬 기본값을 운영에 남기지 않는다 — 앱 기동과 OAuth·쿠키가 함께 깨진다 (5단계 → 배포)
