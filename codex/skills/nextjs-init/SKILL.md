---
name: nextjs-init
description: Scaffold a new Next.js 16 project — App Router, TypeScript strict, Tailwind v4, Better Auth + Google OAuth on DynamoDB, Clean Architecture, ECR push. 새 Next.js 프로젝트 생성, 초기 셋업, 보일러플레이트 구성.
---

# Next.js Project Init

**한국어로 응답. 코드·명령어는 원문 유지** (AGENTS.md 의 Language).

새 Next.js 프로젝트를 정해진 스택으로 부트스트랩한다. 시크릿 취급은 AGENTS.md 의 Security, 커밋은 AGENTS.md 의 Git Safety 를 따른다 — **이 스킬은 커밋하지 않는다**.

## Philosophy

- **스캐폴더가 만드는 것은 다시 만들지 않는다** — `create-next-app` 이 생성하는 보일러플레이트는 손대지 않고, *비자명한 부분*(레이어 경계·키 설계·어댑터·배포)만 추가한다
- **경계가 곧 아키텍처다** — 디렉토리 이름이 아니라 *의존 방향*을 lint 로 강제해야 유지된다
- **접근 패턴을 먼저 정하고 테이블을 만든다** — Single Table Design 은 나중에 GSI 를 붙여 고칠 수 없다
- **단계마다 검증하고 넘어간다** — 각 단계에 종료 조건이 있다 (`skills/problem-solving/SKILL.md#goal-driven-execution--목표-기반-실행`)

## Stack

| 영역 | 선택 | 고정 사항 |
|------|------|-----------|
| Runtime | Node.js 24 (LTS), pnpm 11 | `package.json` 의 `packageManager` 필드로 고정, corepack 사용 |
| Framework | Next.js 16 (App Router), React 19 | Turbopack 기본, `middleware.ts` 없음 → `proxy.ts` |
| Language | TypeScript 6 | `strict: true` 필수. `typescript@^6` 로 **핀한다** — 7.x 는 lint·build 를 깬다 (2단계) |
| Style | Tailwind CSS v4 | `@import "tailwindcss"` + `@tailwindcss/postcss` (v3 의 `tailwind.config.js` 없음) |
| Auth | Better Auth 1.6 + Google OAuth | 커스텀 DynamoDB 어댑터 |
| Data | AWS DynamoDB Single Table Design | `@aws-sdk/lib-dynamodb` DocumentClient. 개발·테스트는 DynamoDB Local |
| Structure | Clean Architecture | `domain` / `application` / `infrastructure` / `app` |
| Testing | Vitest 4 + DynamoDB Local | 게이트는 `vitest run` (watch 금지). 로컬 DB 2개 — dev `:8083` 유지, test `:8084` 초기화 |
| Deploy | Docker standalone → AWS ECR | GitHub Actions + OIDC |

**버전은 기본값일 뿐 절대 규칙이 아니다.** 사용자가 다른 버전·구성을 요청하면 그쪽을 따른다.

## Scope

- **한다**: 프로젝트 생성, 레이어 뼈대, 인증 배선, DynamoDB 어댑터, 접근 패턴·어댑터 계약 테스트, Dockerfile, CI 워크플로, `.env.example`
- **안 한다**: 도메인 비즈니스 로직, UI 디자인, AWS 리소스 *실제 생성*, git commit/push
- **경계**: 기존 프로젝트 수정은 이 스킬 대상이 아니다. 검증은 `/validate`, 커밋은 `/commit`.

## Rules

- **빈 디렉토리에서만 생성한다** — 대상 경로에 파일이 있으면 멈추고 사용자에게 확인한다
- **시크릿을 파일에 쓰지 않는다** — `.env.local` 은 사용자가 채우고, 저장소에는 `.env.example` 만 둔다 (`.gitignore` 확인)
- **AWS 계정에 리소스를 만들지 않는다** — DynamoDB 테이블·ECR 리포지토리·IAM 역할 생성은 명령을 *제시*만 하고 실행은 사용자가 한다. **로컬 DynamoDB 컨테이너는 예외** — AWS 리소스가 아니므로 직접 띄우고 테이블도 만든다 (4단계)
- **git 초기화·커밋은 사용자 요청 시에만** — `--disable-git` 으로 생성한다
- 각 단계의 검증을 통과하지 못하면 다음 단계로 넘어가지 않는다

## Process

### 1. 사전 확인 — 환경과 대상 경로

```bash
node -v            # v24.x 기대
corepack enable && pnpm -v   # 11.x 기대
aws sts get-caller-identity  # AWS 사용 시 (실패해도 진행 가능 — 배포 단계에서만 필요)
ls -A <target-dir> 2>/dev/null
```

버전이 다르면 *멈추고 보고*한다 — 임의로 다운그레이드하지 않는다. 대상 디렉토리가 비어있지 않으면 사용자에게 확인한다.

사용자에게 확인할 값: **프로젝트명**, **AWS 계정 ID**, **AWS 리전**, **DynamoDB 테이블명**, **ECR 리포지토리명**, **OIDC IAM 역할명**. 정해지지 않았으면 프로젝트명 기반 기본값을 제안하고 승인받는다 — 계정 ID·리전·역할명은 7단계 워크플로에 평문으로 박히므로 여기서 확정해야 한다.

> 검증: 위 값이 모두 확정됨.

### 2. 스캐폴딩

```bash
pnpm create next-app@latest <name> \
  --typescript --tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-pnpm --disable-git --yes
```

이후:
- **`pnpm add -D typescript@^6`** — 스캐폴더가 깐 TypeScript 를 되돌린다. 아래 이유를 읽고 넘어간다
- `package.json` 에 `"packageManager": "pnpm@11.x.x"` 확인 (없으면 추가)
- `next.config.ts` 에 `output: "standalone"` 추가 — Docker 이미지 최소화의 전제
- `tsconfig.json` 의 `strict: true` 확인

**왜 TypeScript 를 핀하는가** — `create-next-app` 은 `typescript@latest` 를 설치하는데 현재 latest 는 **7.x** 다. TS 7(Project Corsa)은 Go 네이티브 재작성이면서 **JS Compiler API 를 패키지에서 제거했다** — 메인 엔트리가 버전 스텁이고 `./unstable/*` 서브패스만 남아 있다. 결과:

- `next build` 의 타입체크가 그 API 를 쓴다 → 실패한다. Next.js 는 `tsc` CLI 를 직접 부르는 `experimental.useTypeScriptCli` 로 대응했지만 **16.3 preview 전용**이고 stable(16.2.x)엔 없다
- `@typescript-eslint/parser` 도 그 API 로 `.ts` 를 파싱한다 → `eslint-config-next` 가 통째로 죽는다. typescript-eslint 는 canary 까지 peer 가 `>=4.8.4 <6.1.0` 이라 우회로가 없다

즉 TS 7 은 3단계(레이어 강제)와 8단계(검증 게이트)를 동시에 무력화한다. `^6` 은 typescript-eslint 지원 상한이면서 strict 기본값이라 이 스킬과 결이 맞는다. **Next.js 16.3 이 stable 이 되면 그때 재검토한다** — 그 전엔 preview 채널 + 린터 교체(oxlint/Biome)가 딸려온다.

> 검증: `pnpm exec tsc -v` 가 6.x → `pnpm dev` 기동 후 `/` 200 응답. 확인 뒤 종료.

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

**로컬 DynamoDB** (`compose.yaml`) — 개발과 테스트 모두 여기를 쓴다. 실제 AWS 테이블은 배포용이지 개발용이 아니다:

```yaml
services:
  # 로컬 개발용 — 데이터가 유지된다 (재시작해도 로그인 세션·테이블이 남음)
  dynamodb:
    image: amazon/dynamodb-local:3.3.0
    user: root                          # 아래 "왜 user: root 인가" 참조 — 지우면 조용히 멈춘다
    command: ["-jar", "DynamoDBLocal.jar", "-sharedDb", "-dbPath", "./data"]
    working_dir: /home/dynamodblocal
    volumes: ["dynamodb-data:/home/dynamodblocal/data"]
    ports: ["8083:8000"]

  # 테스트용 — 매 기동마다 초기화된다
  dynamodb-test:
    image: amazon/dynamodb-local:3.3.0
    command: ["-jar", "DynamoDBLocal.jar", "-sharedDb", "-inMemory"]
    ports: ["8084:8000"]

volumes:
  dynamodb-data:
```

**왜 인스턴스를 둘로 나누는가** — `-sharedDb` 는 모든 클라이언트가 *하나의 DB* 를 보게 만든다. 하나만 띄우면 테스트가 개발 중이던 데이터를 매번 지운다. 포트를 나누는 게 유일하게 안 헷갈리는 방법이다.

**왜 `user: root` 인가** — 이미지에 `/home/dynamodblocal/data` 가 없어서 Docker 가 마운트 지점을 **root 소유 755** 로 새로 만든다. 컨테이너는 uid 1000(`dynamodblocal`)으로 도니 SQLite 가 DB 파일을 못 만들고, 다음을 3초마다 무한 반복한다:

```
WARNING: [sqlite] cannot open DB: SQLiteException: [14] unable to open database file
         SQLiteQueue[shared-local-instance.db]: stopped abnormally, reincarnating in 3000ms
```

**가장 나쁜 형태로 실패한다** — `docker compose ps` 는 `Up` 으로 보이고, 클라이언트는 에러 대신 *무응답으로 멈춘다*. 로그를 보기 전엔 원인을 알 수 없다. AWS 공식 예제는 대신 호스트 bind mount 를 쓰는데, 그건 Docker Desktop·OrbStack 이 uid 를 remap 해줘서 macOS 에서만 동작한다 — Linux(WSL 포함)에서 호스트 uid 가 1000 이 아니면 똑같이 깨진다. 로컬 개발용 컨테이너라 root 실행의 위험은 없다.

OrbStack·Docker Desktop 모두 소켓이 표준 위치라 `docker compose up -d dynamodb` 로 그대로 뜬다.

**함정 4개 — 여기서 시간을 가장 많이 버린다:**

1. **자격증명을 반드시 준다.** AWS 문서가 *"Downloadable DynamoDB requires any credentials to work"* 라고 명시한다. 값은 검증되지 않지만, 없으면 SDK 가 자격증명 탐색 단계에서 먼저 죽는다
2. **`-sharedDb` 를 빼지 않는다.** 없으면 DynamoDB Local 이 (accessKeyId, region) 조합마다 별도 DB 를 만든다. 테이블 생성 스크립트와 앱의 자격증명·리전이 조금이라도 다르면 서로 다른 DB 를 보고 `ResourceNotFoundException` 이 난다 — "분명히 만들었는데 없다"의 정체
3. **`-inMemory` 와 `-dbPath` 는 동시에 못 쓴다.** 그래서 위 두 서비스의 설정이 다르다. 테스트 인스턴스는 기동할 때마다 테이블이 사라지므로 **테이블 생성을 vitest `globalSetup` 에서 해야 한다**
4. **GSI 일관성이 운영과 다르다.** DynamoDB Local 은 GSI 를 동기로 갱신하지만 실제 DynamoDB 의 GSI 는 *eventually consistent* 다. 위 접근 패턴 7개 중 6개가 GSI 경유이므로, 쓰기 직후 GSI 를 읽는 코드는 **로컬에서 되고 운영에서 깨진다**

**테이블 생성** — 아래가 정본이다. **로컬에는 지금 실행**하고(`--endpoint-url http://localhost:8083` 을 덧붙인다), **AWS 에는 제시만** 한다 (실행은 사용자):

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

로컬 실행 시 `--region` 값은 무엇이든 되지만 **앱의 `AWS_REGION` 과 반드시 같아야 한다** (함정 2). 테스트 인스턴스용은 `--endpoint-url http://localhost:8084` 이고, 이건 6단계의 `globalSetup` 이 맡는다.

> 검증: 접근 패턴 7개가 각각 어떤 인덱스로 처리되는지 표로 대응됨 (대응 안 되는 패턴이 남으면 키 설계를 고친다). `docker compose up -d dynamodb` 후 `aws dynamodb list-tables --endpoint-url http://localhost:8083` 에 테이블이 보임.

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

**환경변수** — `.env.example` 은 커밋한다. **시크릿만 비우고, 비밀이 아닌 로컬 기본값은 채운다** — 받는 사람이 뭘 넣어야 할지 알 수 있어야 한다:

```
BETTER_AUTH_SECRET=      # openssl rand -base64 32
BETTER_AUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
AWS_REGION=ap-northeast-2
DYNAMODB_TABLE_NAME=
DYNAMODB_ENDPOINT=http://localhost:8083   # 로컬 개발 전용. 운영에서는 반드시 비운다
```

**DynamoDB 클라이언트는 엔드포인트로 로컬/운영을 가른다** (`src/infrastructure/dynamodb/client.ts`):

```ts
const endpoint = process.env.DYNAMODB_ENDPOINT;

export const docClient = DynamoDBDocumentClient.from(
  new DynamoDBClient({
    region: process.env.AWS_REGION!,
    // 로컬일 때만 엔드포인트와 더미 자격증명을 준다. 운영에서는 둘 다 생략해야
    // SDK 가 실제 리전 엔드포인트로 가고 자격증명을 역할에서 가져온다.
    ...(endpoint
      ? { endpoint, credentials: { accessKeyId: "local", secretAccessKey: "local" } }
      : {}),
  })
);
```

`DYNAMODB_ENDPOINT` 가 운영 환경에 남으면 앱이 존재하지 않는 localhost:8083 을 치면서 조용히 죽는다 — 배포 매니페스트에서 이 키가 비어 있는지 확인한다.

운영에서 AWS 자격증명은 **환경변수가 아니라 역할**로 준다 (ECS 태스크 롤 / EKS IRSA). `NEXT_PUBLIC_*` 은 빌드 시점에 이미지에 박히므로 시크릿을 넣지 않는다.

> 검증: `docker compose up -d dynamodb` → `pnpm dev` → Google 로그인 → 세션 유지 → 로그아웃. `aws dynamodb scan --table-name <table> --endpoint-url http://localhost:8083` 에 `user`·`session`·`account` 아이템이 보임. **AWS 계정에는 아무것도 만들지 않은 상태여야 한다.**
>
> **Google OAuth 클라이언트가 아직 없으면** 여기서 로그인 플로우를 검증할 수 없다. 이때는 멈추지 말고 (a) 사용자에게 클라이언트 발급과 리다이렉트 URI 등록을 *요청*한 뒤 (b) 6단계 어댑터 테스트로 배선의 정합을 대신 검증하고 (c) 완료 보고에 로그인 플로우를 `SKIP + 사유` 로 기록한다. 이 단계는 Rules 의 "검증 통과 전 진행 금지"에 대한 **명시적 예외**다 — 사용자 계정 작업에 의존하기 때문이다.

### 6. 테스트 — Vitest + DynamoDB Local

```bash
pnpm add -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom vite-tsconfig-paths
```

`vitest.config.mts` — Next.js 공식 구성 그대로:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: { environment: "jsdom" },
});
```

`package.json` 에 `"test": "vitest run"`, `"test:watch": "vitest"`. **CI·검증 게이트에는 반드시 `vitest run`** — 인자 없는 `vitest` 는 watch 모드로 떠서 영원히 끝나지 않는다.

전역 환경은 jsdom 이고, 도메인·어댑터 테스트는 파일 상단 docblock 으로 node 로 내린다:

```ts
// @vitest-environment node
```

glob 으로 환경을 나누는 `environmentMatchGlobs` 는 현행 Vitest 문서에 없다 — docblock 을 쓴다.

**테스트는 `dynamodb-test`(포트 8084)를 쓴다** — 4단계에서 띄운 개발용 인스턴스가 아니다. `-sharedDb` 때문에 같은 인스턴스를 쓰면 테스트가 개발 데이터를 지운다.

테스트 인스턴스는 `-inMemory` 라 기동할 때마다 비어 있으므로 **테이블 생성을 `globalSetup` 에 둔다**. 4단계의 스키마를 **SDK `CreateTableCommand` 로** 만든다 — AWS CLI 를 호출하지 않는다. 테스트가 CLI 설치 여부에 의존하면 CI 에서 깨진다.

```ts
// vitest.globalSetup.ts — vitest.config.mts 의 test.globalSetup 에 등록
export default async function () {
  process.env.DYNAMODB_ENDPOINT = "http://localhost:8084";  // 5단계 클라이언트를 그대로 재사용
  // new DynamoDBClient({...}).send(new CreateTableCommand({ /* 4단계 키 레이아웃 */ }))
  // 이미 존재하면 ResourceInUseException — 무시한다 (멱등)
}
```

**무엇을 테스트하는가** — 4·5단계에서 표로만 적어둔 것을 실행 가능하게 만든다:

| 대상 | 테스트 |
|------|--------|
| 4단계 접근 패턴 7개 | 패턴마다 실제 쿼리 1개. 통과 = 키 설계가 실제로 성립한다는 증거 |
| 어댑터 계약 1 (Scan 폴백 금지) | 인덱스로 못 푸는 `where` 에 **throw 하는지**. 조용히 결과를 돌려주면 실패 |
| 어댑터 계약 2 (지원 연산자) | `eq`·`in` 통과, 미지원 연산자는 명확한 에러 |
| 어댑터 계약 3 (GSI 키 재계산) | email 변경 후 새 email 로 조회되고 옛 키로는 안 잡히는지 |
| 어댑터 계약 5 (중복 가입 방지) | 같은 email 로 `create` 2회 → 하나만 성공 |
| 도메인·유스케이스 | DynamoDB 없이 순수 단위 테스트 (외부 의존 0 이라는 3단계 경계의 증명) |

**Server Component 는 대상에서 뺀다** — Next.js 공식 문서가 *"Since `async` Server Components are new to the React ecosystem, Vitest currently does not support them"* 이라고 명시한다. 동기 컴포넌트만 단위 테스트하고 async 는 E2E 로 미룬다.

> 검증: `docker compose up -d dynamodb-test` → `pnpm test` 전부 통과. 접근 패턴 7개 테스트가 모두 존재해야 한다. 테스트 후 개발용 인스턴스의 데이터가 그대로 남아 있는지도 확인한다 (남지 않으면 두 인스턴스가 섞인 것이다).

### 7. Docker + ECR

**Dockerfile** — 멀티스테이지, standalone 출력:

- `node:24-slim` 기준 (deps / builder / runner 3단계)
- deps: `corepack enable pnpm && pnpm install --frozen-lockfile`
- builder: `pnpm build` (`output: "standalone"` 전제)
- runner: `.next/standalone` → `./`, `.next/static` → `./.next/static`, `public` → `./public`
- 비루트 실행 (`USER node`), `ENV HOSTNAME=0.0.0.0 PORT=3000`, `CMD ["node", "server.js"]`
- `.dockerignore` 필수: `node_modules`, `.next`, `.git`, `.env*`

**GitHub Actions** (`.github/workflows/release.yml`) — 장기 액세스 키 대신 **OIDC**. 아래를 그대로 쓰고 `<...>` 만 1단계에서 확정한 값으로 채운다:

```yaml
name: Release (ecr)

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: <region>
  AWS_ROLE_ARN: arn:aws:iam::<account-id>:role/<role-name>
  ECR_REPOSITORY: <account-id>.dkr.ecr.<region>.amazonaws.com/<repo>

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ env.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4

      - name: Build and push
        uses: docker/build-push-action@v7
        with:
          context: .
          platforms: linux/amd64
          push: true
          provenance: false
          sbom: false
          tags: |
            ${{ env.ECR_REPOSITORY }}:${{ github.ref_name }}
            ${{ env.ECR_REPOSITORY }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**왜 이렇게 쓰는지 — 바꾸기 전에 읽을 것:**

- **태그 푸시가 곧 릴리스다.** 브랜치 푸시로는 이미지가 나가지 않는다 — `git tag v0.1.0 && git push origin v0.1.0`. `workflow_dispatch` 는 같은 커밋 재빌드용이고, 이때 `github.ref_name` 은 태그가 아니라 *브랜치명*이 된다
- **이미지 태그는 `github.ref_name`(= `v0.1.0`) + `latest`.** 버전 태그가 롤백 대상을 특정하고 `latest` 는 배포 편의용이다. 따라서 ECR 리포지토리의 tag mutability 는 **MUTABLE** 이어야 한다 — IMMUTABLE 이면 두 번째 릴리스의 `latest` 푸시가 실패한다
- **역할 ARN·레지스트리 URI 는 시크릿이 아니다.** 식별자일 뿐이고 실제 접근은 OIDC 신뢰 정책이 통제하므로 `env:` 에 평문으로 둔다. 대신 신뢰 정책의 `sub` 조건을 **저장소 단위로** 좁힌다 (아래 JSON). `repo:<org>/*` 같은 와일드카드는 조직 내 아무 저장소나 이 역할을 가져다 쓰게 만든다
- **`docker/setup-buildx-action` 을 생략하지 않는다.** 기본 `docker` 드라이버는 캐시 export 를 지원하지 않아 `cache-to: type=gha` 가 그대로 실패한다
- **`provenance: false`, `sbom: false`.** buildx 는 기본으로 attestation 을 붙여 결과를 OCI image index 로 만든다. ECR 콘솔과 일부 배포 대상이 이를 단일 이미지로 읽지 못한다
- **`platforms: linux/amd64`.** 실행 대상이 arm64(Graviton)면 바꾼다. 멀티 아키텍처는 QEMU 에뮬레이션으로 빌드 시간이 몇 배가 되므로 실제로 두 아키텍처가 필요할 때만

**IAM 신뢰 정책** — 역할 생성은 사용자가 한다. `sub` 조건이 이 구성의 유일한 접근 통제다:

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
    "StringLike": { "token.actions.githubusercontent.com:sub": "repo:<org>/<repo>:*" }
  }
}
```

**경계는 저장소 하나다.** `:*` 는 그 저장소의 모든 ref 를 허용한다 — GitHub 의 `sub` 는 태그가 `repo:<org>/<repo>:ref:refs/tags/<tag>`, 브랜치·`workflow_dispatch` 가 `ref:refs/heads/<branch>`, PR 이 `repo:<org>/<repo>:pull_request` 형태다. 즉 이 저장소에 푸시 권한이 있는 사람이면 어떤 ref 로든 역할을 쓸 수 있고, 그건 이미 릴리스를 낼 수 있는 사람과 같은 집합이라 실질적인 추가 노출이 아니다. 트리거를 추가해도 신뢰 정책을 같이 고칠 필요가 없다는 게 이 방식의 값어치다.

더 좁히려면 ref 단위로 나열한다 (`ref:refs/tags/*` + `ref:refs/heads/main`). 단, 이 워크플로는 태그 푸시와 `workflow_dispatch` 두 트리거를 쓰고 후자는 *브랜치*에서 돌기 때문에 **태그만 넣으면 수동 실행이 `sts:AssumeRoleWithWebIdentity` 에서 거부된다** — 좁힐 거면 두 항목을 다 넣어야 한다.

바꾸지 말아야 할 것은 **저장소 경계**다. `repo:<org>/*` 로 열면 조직 내 아무 저장소나 이 역할을 가져다 쓴다.

> 검증: `docker build` 성공 → `docker run -p 3000:3000` → `/` 200. CI 는 첫 태그 푸시 후 Actions 로그와 `aws ecr describe-images --repository-name <repo> --region <region>` 로 확인.

### 8. 검증 게이트

```bash
docker compose up -d dynamodb-test
pnpm lint && pnpm exec tsc --noEmit && pnpm test && pnpm build
```

전부 통과해야 완료다. 실패는 `/validate` 절차로 근본원인을 고친다.

## 완료 보고

```
## Next.js 프로젝트 생성 완료

경로: <path>
스택: Next.js 16 / React 19 / TS 6 strict / Tailwind v4 / Better Auth 1.6 / DynamoDB / Vitest 4

검증:
- pnpm test: PASS (접근 패턴 7/7, 어댑터 계약 5/5)
- pnpm build: PASS
- Google 로그인 플로우: PASS (또는 SKIP + 사유 — OAuth 클라이언트 미발급 등)
- docker build: PASS (또는 SKIP + 사유)

로컬에 이미 만들어 둔 것:
- 로컬 DynamoDB 2개 (dev :8083 / test :8084) + dev 테이블

사용자 후속 작업 (실행하지 않음):
- [ ] **AWS** DynamoDB 테이블 생성 — 4단계 명령에서 `--endpoint-url` 만 빼면 된다 (로컬은 완료됨)
- [ ] ECR 리포지토리 생성 (tag mutability: MUTABLE) + OIDC IAM 역할·신뢰 정책 — 7단계 참조
- [ ] Google OAuth 클라이언트 발급 + 리다이렉트 URI 등록
- [ ] .env.local 값 채우기
- [ ] git init / 첫 커밋 (요청 시)
- [ ] 첫 릴리스 — `git tag v0.1.0 && git push origin v0.1.0`
```

## Anti-Patterns

- `create-next-app` 결과물을 즉시 재작성하지 않는다 — 필요한 것만 덧붙인다
- 레이어를 디렉토리로만 나누고 lint 강제를 생략하지 않는다 — 한 달이면 무너진다
- `create-next-app` 이 깐 `typescript@latest`(7.x)를 그대로 두지 않는다 — Compiler API 가 없어 lint·build 가 함께 죽는다
- 어댑터에서 `Scan` 으로 폴백하지 않는다 — 지원 못 하는 쿼리는 던진다
- 게이트에 인자 없는 `vitest` 를 넣지 않는다 — watch 모드로 떠서 CI 가 끝나지 않는다
- DynamoDB Local 을 `-sharedDb` 없이 띄우지 않는다 — 자격증명·리전이 다르면 다른 DB 를 본다
- 개발과 테스트가 같은 DynamoDB Local 인스턴스를 쓰지 않는다 — `-sharedDb` 라 테스트가 개발 데이터를 지운다
- 로컬 개발을 실제 AWS DynamoDB 로 하지 않는다 — 비용·오염·오프라인 불가. `DYNAMODB_ENDPOINT` 로 가른다
- `DYNAMODB_ENDPOINT` 를 운영 환경에 남기지 않는다 — 앱이 localhost:8083 을 치며 죽는다
- 쓰기 직후 GSI 읽기를 강일관으로 가정하지 않는다 — 로컬에서만 통과하고 운영에서 깨진다
- GSI 를 나중에 붙이면 된다고 미루지 않는다 — 접근 패턴을 4단계에서 확정한다
- `middleware.ts` 를 만들지 않는다 (Next.js 16 에 없다) — `proxy.ts` 이고, 인가는 라우트에서 다시 확인한다
- proxy/middleware 만으로 인가를 끝내지 않는다
- `nextCookies()` 를 plugins 배열 중간에 두지 않는다 — 마지막이어야 한다
- OIDC 신뢰 정책의 `sub` 를 `repo:<org>/*` 로 열어두지 않는다 — 이 조건이 유일한 접근 통제다
- `cache-to: type=gha` 를 쓰면서 `setup-buildx-action` 을 빼지 않는다 — 기본 드라이버는 캐시 export 를 못 한다
- `.env.local` 을 커밋하거나 시크릿 값을 파일에 쓰지 않는다
- 사용자 허가 없이 AWS 리소스를 만들거나 git commit 하지 않는다
- 검증 없이 "완료"라고 보고하지 않는다
