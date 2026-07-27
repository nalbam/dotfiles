---
name: nextjs-init
description: Scaffold a new Next.js 16 project — App Router, TypeScript strict, Tailwind v4, Better Auth + Google OAuth on DynamoDB, Clean Architecture, ECR push. 새 Next.js 프로젝트 생성, 초기 셋업, 보일러플레이트 구성.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Next.js Project Init

**한국어로 응답. 코드·명령어는 원문 유지** (`rules/language.md`).

새 Next.js 프로젝트를 정해진 스택으로 부트스트랩한다. 시크릿 취급은 `rules/security.md`, 커밋은 `rules/git-workflow.md` 를 따른다 — **이 스킬은 커밋하지 않는다**.

## Philosophy

- **스캐폴더가 만드는 것은 다시 만들지 않는다** — `create-next-app` 이 생성하는 보일러플레이트는 손대지 않고, *비자명한 부분*(레이어 경계·키 설계·어댑터·배포)만 추가한다
- **경계가 곧 아키텍처다** — 디렉토리 이름이 아니라 *의존 방향*을 lint 로 강제해야 유지된다
- **접근 패턴을 먼저 정하고 테이블을 만든다** — Single Table Design 은 나중에 GSI 를 붙여 고칠 수 없다
- **단계마다 검증하고 넘어간다** — 각 단계에 종료 조건이 있다 (`skills/problem-solving/SKILL.md#goal-driven-execution--목표-기반-실행`)

## Stack

| 영역 | 선택 | 고정 사항 |
|------|------|-----------|
| Runtime | Node.js 22 (LTS), pnpm 11 | `package.json` 의 `packageManager` 필드로 고정, corepack 사용 |
| Framework | Next.js 16 (App Router), React 19 | Turbopack 기본, `middleware.ts` 없음 → `proxy.ts` |
| Language | TypeScript strict | `strict: true` 필수 |
| Style | Tailwind CSS v4 | `@import "tailwindcss"` + `@tailwindcss/postcss` (v3 의 `tailwind.config.js` 없음) |
| Auth | Better Auth 1.6 + Google OAuth | 커스텀 DynamoDB 어댑터 |
| Data | AWS DynamoDB Single Table Design | `@aws-sdk/lib-dynamodb` DocumentClient |
| Structure | Clean Architecture | `domain` / `application` / `infrastructure` / `app` |
| Deploy | Docker standalone → AWS ECR | GitHub Actions + OIDC |

**버전은 기본값일 뿐 절대 규칙이 아니다.** 사용자가 다른 버전·구성을 요청하면 그쪽을 따른다.

## Scope

- **한다**: 프로젝트 생성, 레이어 뼈대, 인증 배선, DynamoDB 어댑터, Dockerfile, CI 워크플로, `.env.example`
- **안 한다**: 도메인 비즈니스 로직, UI 디자인, AWS 리소스 *실제 생성*, git commit/push
- **경계**: 기존 프로젝트 수정은 이 스킬 대상이 아니다. 검증은 `/validate`, 커밋은 `/commit`.

## Rules

- **빈 디렉토리에서만 생성한다** — 대상 경로에 파일이 있으면 멈추고 사용자에게 확인한다
- **시크릿을 파일에 쓰지 않는다** — `.env.local` 은 사용자가 채우고, 저장소에는 `.env.example` 만 둔다 (`.gitignore` 확인)
- **AWS 리소스를 만들지 않는다** — DynamoDB 테이블·ECR 리포지토리·IAM 역할 생성은 명령을 *제시*만 하고 실행은 사용자가 한다
- **git 초기화·커밋은 사용자 요청 시에만** — `--disable-git` 으로 생성한다
- 각 단계의 검증을 통과하지 못하면 다음 단계로 넘어가지 않는다

## Process

### 1. 사전 확인 — 환경과 대상 경로

```bash
node -v            # v22.x 기대
corepack enable && pnpm -v   # 11.x 기대
aws sts get-caller-identity  # AWS 사용 시 (실패해도 진행 가능 — 배포 단계에서만 필요)
ls -A <target-dir> 2>/dev/null
```

버전이 다르면 *멈추고 보고*한다 — 임의로 다운그레이드하지 않는다. 대상 디렉토리가 비어있지 않으면 사용자에게 확인한다.

사용자에게 확인할 값: **프로젝트명**, **AWS 리전**, **DynamoDB 테이블명**, **ECR 리포지토리명**. 정해지지 않았으면 프로젝트명 기반 기본값을 제안하고 승인받는다.

> 검증: 위 값이 모두 확정됨.

### 2. 스캐폴딩

```bash
pnpm create next-app@latest <name> \
  --typescript --tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-pnpm --disable-git --yes
```

이후:
- `package.json` 에 `"packageManager": "pnpm@11.x.x"` 확인 (없으면 추가)
- `next.config.ts` 에 `output: "standalone"` 추가 — Docker 이미지 최소화의 전제
- `tsconfig.json` 의 `strict: true` 확인

> 검증: `pnpm dev` 기동 후 `/` 200 응답. 확인 뒤 종료.

### 3. 레이어 뼈대 — Clean Architecture

```
src/
├── domain/           # 엔티티·값 객체·리포지토리 인터페이스. 외부 의존 0
├── application/      # 유스케이스. domain 만 의존
├── infrastructure/   # DynamoDB·Better Auth·외부 API 구현. domain 인터페이스를 구현
│   ├── dynamodb/     #   client.ts, single-table 키 헬퍼, 리포지토리 구현
│   └── auth/         #   better-auth 설정 + DynamoDB 어댑터
└── app/              # Next.js App Router. application 호출 + infrastructure 조립(DI)
```

**의존 방향**: `app` → `application` → `domain` ← `infrastructure`

`domain` 은 어떤 레이어도 import 하지 않는다. `infrastructure` 는 `domain` 의 인터페이스만 구현하고 `application` 을 모른다.

디렉토리만 나누면 반드시 무너진다 — **ESLint 로 강제한다**. `eslint-plugin-import` 의 `import/no-restricted-paths` zones 로 금지 방향을 선언한다:

| from | 금지 target |
|------|-------------|
| `src/domain` | `src/application`, `src/infrastructure`, `src/app` |
| `src/application` | `src/infrastructure`, `src/app` |
| `src/infrastructure` | `src/application`, `src/app` |

> 검증: 금지 방향으로 import 한 임시 파일이 lint 에러를 내는지 확인 후 삭제.

### 4. DynamoDB Single Table Design

Better Auth 코어 스키마는 4개 모델이다 (테이블명 단수형): `user`, `session`, `account`, `verification`.

**필수 접근 패턴** — 어댑터가 이걸 못 하면 인증이 동작하지 않는다:

| # | 패턴 | 연산 |
|---|------|------|
| 1 | id 로 단건 조회 (전 모델) | GetItem |
| 2 | email 로 user 조회 | Query GSI1 |
| 3 | token 으로 session 조회 | Query GSI1 |
| 4 | userId 로 session 목록 | Query GSI2 |
| 5 | (providerId, accountId) 로 account 조회 | Query GSI1 |
| 6 | userId 로 account 목록 | Query GSI2 |
| 7 | identifier 로 verification 조회 (최신) | Query GSI1, `ScanIndexForward: false` |

**키 레이아웃** — 단일 테이블, GSI 2개:

| 모델 | PK | SK | GSI1PK | GSI1SK | GSI2PK | GSI2SK |
|------|----|----|--------|--------|--------|--------|
| user | `USER#<id>` | `USER#<id>` | `EMAIL#<email>` | `USER#<id>` | — | — |
| session | `SESSION#<id>` | `SESSION#<id>` | `TOKEN#<token>` | `SESSION#<id>` | `USER#<userId>` | `SESSION#<createdAt>` |
| account | `ACCOUNT#<id>` | `ACCOUNT#<id>` | `PROVIDER#<providerId>#<accountId>` | `ACCOUNT#<id>` | `USER#<userId>` | `ACCOUNT#<providerId>` |
| verification | `VERIFICATION#<id>` | `VERIFICATION#<id>` | `IDENT#<identifier>` | `VERIFICATION#<createdAt>` | — | — |

추가 속성:
- `entity` — 모델명 (`user` / `session` / …). 필터·디버깅용
- `ttl` — **session·verification 만**. `expiresAt` 을 epoch seconds 로 변환. DynamoDB TTL 을 이 속성에 설정하면 만료 세션이 자동 정리된다

테이블 생성 명령은 *제시만* 한다 (실행은 사용자):

```bash
aws dynamodb create-table --table-name <table> \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S \
    AttributeName=GSI1PK,AttributeType=S AttributeName=GSI1SK,AttributeType=S \
    AttributeName=GSI2PK,AttributeType=S AttributeName=GSI2SK,AttributeType=S \
  --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
  --global-secondary-indexes \
    'IndexName=GSI1,KeySchema=[{AttributeName=GSI1PK,KeyType=HASH},{AttributeName=GSI1SK,KeyType=RANGE}],Projection={ProjectionType=ALL}' \
    'IndexName=GSI2,KeySchema=[{AttributeName=GSI2PK,KeyType=HASH},{AttributeName=GSI2SK,KeyType=RANGE}],Projection={ProjectionType=ALL}' \
  --billing-mode PAY_PER_REQUEST --region <region>

aws dynamodb update-time-to-live --table-name <table> \
  --time-to-live-specification 'Enabled=true,AttributeName=ttl' --region <region>
```

> 검증: 접근 패턴 7개가 각각 어떤 인덱스로 처리되는지 표로 대응됨. 대응되지 않는 패턴이 남아 있으면 키 설계를 고친다.

### 5. Better Auth + Google OAuth + 커스텀 어댑터

```bash
pnpm add better-auth @aws-sdk/client-dynamodb @aws-sdk/lib-dynamodb
```

**어댑터** (`src/infrastructure/auth/dynamodb-adapter.ts`) — `createAdapterFactory` 를 사용한다:

```ts
import { createAdapterFactory } from "better-auth/adapters";

export const dynamodbAdapter = (client: DynamoDBDocumentClient, table: string) =>
  createAdapterFactory({
    config: {
      adapterId: "dynamodb",
      adapterName: "DynamoDB Single Table",
      supportsNumericIds: false, // 문자열 ID
      supportsDates: false,      // ISO 8601 문자열로 저장 — 사전순 = 시간순
      supportsJSON: true,        // DocumentClient 가 map 을 네이티브 처리
      supportsBooleans: true,
    },
    adapter: ({ getFieldName }) => ({
      create: async ({ model, data, select }) => { /* PutItem */ },
      update: async ({ model, where, update }) => { /* UpdateItem */ },
      updateMany: async ({ model, where, update }) => { /* Query → 개별 Update */ },
      findOne: async ({ model, where, select }) => { /* GetItem or Query GSI */ },
      findMany: async ({ model, where, limit, sortBy, offset }) => { /* Query */ },
      delete: async ({ model, where }) => { /* DeleteItem */ },
      deleteMany: async ({ model, where }) => { /* Query → BatchWrite */ },
      count: async ({ model, where }) => { /* Query Select=COUNT */ },
    }),
  });
```

**어댑터 계약 — 반드시 지킬 것:**

1. **`where` 절을 인덱스로 해석하지 못하면 던진다.** 조용히 `Scan` 으로 폴백하지 않는다 — 개발 중엔 동작하는 것처럼 보이다가 운영에서 비용·지연으로 터진다
2. **지원 연산자를 명시한다.** 최소 `eq` 와 `in`. 나머지(`contains`, `starts_with`, `lt`, `gt`)는 필요할 때 추가하고, 미지원은 명확한 에러 메시지로 거부한다
3. **`create`/`update` 에서 GSI 키를 항상 재계산한다.** email·token 이 바뀌면 GSI1 키도 바뀐다
4. **`ttl` 은 `expiresAt` 이 있는 모델에서만 계산한다**
5. **동일 이메일 중복 가입 방지**는 `ConditionExpression: attribute_not_exists(PK)` 로 조건부 쓰기 — 애플리케이션 레벨 select-then-insert 는 경합에 취약하다

**설정** (`src/infrastructure/auth/auth.ts`):

```ts
export const auth = betterAuth({
  database: dynamodbAdapter(docClient, process.env.DYNAMODB_TABLE_NAME!),
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    },
  },
  plugins: [nextCookies()], // 반드시 plugins 배열의 마지막
});
```

**배선:**
- 라우트 핸들러: `src/app/api/auth/[...all]/route.ts` → `export const { GET, POST } = toNextJsHandler(auth)`
- 클라이언트: `src/lib/auth-client.ts` → `createAuthClient()` from `better-auth/react`
- 서버 세션: `auth.api.getSession({ headers: await headers() })`
- 보호 라우트: Next.js 16 은 `middleware.ts` 가 없다 → **`proxy.ts`** 사용. 단, proxy 는 *낙관적 리다이렉트*용이고 **실질 인가 검사는 각 라우트·서버 액션에서 세션을 다시 확인**한다 (CVE-2025-29927 의 교훈)

**Google Cloud Console 리다이렉트 URI** (사용자가 등록):
- `http://localhost:3000/api/auth/callback/google`
- `https://<domain>/api/auth/callback/google`

**환경변수** — `.env.example` 에 키만, 값은 비워서 커밋:

```
BETTER_AUTH_SECRET=      # openssl rand -base64 32
BETTER_AUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
AWS_REGION=
DYNAMODB_TABLE_NAME=
```

운영에서 AWS 자격증명은 **환경변수가 아니라 역할**로 준다 (ECS 태스크 롤 / EKS IRSA). `NEXT_PUBLIC_*` 은 빌드 시점에 이미지에 박히므로 시크릿을 넣지 않는다.

> 검증: `pnpm dev` → Google 로그인 → 세션 유지 → 로그아웃. DynamoDB 에 `user`·`session`·`account` 아이템 생성 확인.

### 6. Docker + ECR

**Dockerfile** — 멀티스테이지, standalone 출력:

- `node:22-slim` 기준 (deps / builder / runner 3단계)
- deps: `corepack enable pnpm && pnpm install --frozen-lockfile`
- builder: `pnpm build` (`output: "standalone"` 전제)
- runner: `.next/standalone` → `./`, `.next/static` → `./.next/static`, `public` → `./public`
- 비루트 실행 (`USER node`), `ENV HOSTNAME=0.0.0.0 PORT=3000`, `CMD ["node", "server.js"]`
- `.dockerignore` 필수: `node_modules`, `.next`, `.git`, `.env*`

**GitHub Actions** (`.github/workflows/ecr.yml`) — 장기 액세스 키 대신 **OIDC**:

```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: actions/checkout@v7
  - uses: aws-actions/configure-aws-credentials@v6
    with:
      role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
      aws-region: ${{ vars.AWS_REGION }}
  - uses: aws-actions/amazon-ecr-login@v2
    id: ecr
  - uses: docker/build-push-action@v7
    with:
      push: true
      tags: ${{ steps.ecr.outputs.registry }}/${{ vars.ECR_REPOSITORY }}:${{ github.sha }}
```

태그는 `latest` 가 아니라 **커밋 SHA**를 기본으로 한다 — 롤백 대상이 특정된다.

> 검증: `docker build` 성공 → `docker run -p 3000:3000` → `/` 200. CI 는 첫 푸시 후 Actions 로그로 확인.

### 7. 검증 게이트

```bash
pnpm lint && pnpm exec tsc --noEmit && pnpm build
```

전부 통과해야 완료다. 실패는 `/validate` 절차로 근본원인을 고친다.

## 완료 보고

```
## Next.js 프로젝트 생성 완료

경로: <path>
스택: Next.js 16 / React 19 / TS strict / Tailwind v4 / Better Auth 1.6 / DynamoDB

검증:
- pnpm build: PASS
- Google 로그인 플로우: PASS (또는 SKIP + 사유)
- docker build: PASS (또는 SKIP + 사유)

사용자 후속 작업 (실행하지 않음):
- [ ] DynamoDB 테이블 생성 — 명령 위 4단계 참조
- [ ] ECR 리포지토리 생성 + OIDC IAM 역할
- [ ] Google OAuth 클라이언트 발급 + 리다이렉트 URI 등록
- [ ] .env.local 값 채우기
- [ ] git init / 첫 커밋 (요청 시)
```

## Anti-Patterns

- `create-next-app` 결과물을 즉시 재작성하지 않는다 — 필요한 것만 덧붙인다
- 레이어를 디렉토리로만 나누고 lint 강제를 생략하지 않는다 — 한 달이면 무너진다
- 어댑터에서 `Scan` 으로 폴백하지 않는다 — 지원 못 하는 쿼리는 던진다
- GSI 를 나중에 붙이면 된다고 미루지 않는다 — 접근 패턴을 4단계에서 확정한다
- `middleware.ts` 를 만들지 않는다 (Next.js 16 에 없다) — `proxy.ts` 이고, 인가는 라우트에서 다시 확인한다
- proxy/middleware 만으로 인가를 끝내지 않는다
- `nextCookies()` 를 plugins 배열 중간에 두지 않는다 — 마지막이어야 한다
- `.env.local` 을 커밋하거나 시크릿 값을 파일에 쓰지 않는다
- 사용자 허가 없이 AWS 리소스를 만들거나 git commit 하지 않는다
- 검증 없이 "완료"라고 보고하지 않는다
