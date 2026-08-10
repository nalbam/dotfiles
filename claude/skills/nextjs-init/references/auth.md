# nextjs-init — 5단계: Better Auth + Google OAuth + 커스텀 어댑터

`nextjs-init` 스킬의 단계별 상세다. Stack·Scope·Rules 등 전체 맥락과 단계 색인은 `SKILL.md` 가 source 다.

## 5. Better Auth + Google OAuth + 커스텀 어댑터

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
2. **지원 연산자를 명시한다.** 최소 `eq` 와 `in`. 나머지(`contains`, `starts_with`, `lt`, `gt`)는 필요할 때 추가하고, 미지원은 명확한 에러 메시지로 거부한다. `findMany` 의 `offset` 도 거부한다 — DynamoDB 에 대응 개념이 없다
3. **`create`/`update` 에서 파생 키를 항상 재계산한다.** GSI 키는 그대로 update 하면 되지만 두 경우는 트랜잭션이다 — **session 의 token 이 바뀌면 PK 가 바뀌므로 delete+put**, **user 의 email 이 바뀌면 마커 스왑**(옛 `EMAIL#` 마커 Delete + 새 마커 조건부 Put + user Update)
4. **`expiresAt` 은 만료가 있는 모델(session·verification)에서만 숫자로 바꾸고, ISO 는 `expiresAtIso` 에 보관한다** (4단계). 내부 속성 제거는 필터·정렬보다 **먼저** 돈다
5. **동일 이메일 중복 가입 방지는 email 마커 + 트랜잭션이다.** user 의 PK 는 `USER#<id>` 라 user 아이템에 건 `attribute_not_exists(PK)` 는 id 충돌만 막고 **중복 이메일은 통과시킨다** (다른 id → 다른 PK). GSI 도 유니크 제약이 없다. user `create` 는 `TransactWriteItems` 로 user 아이템 Put + `EMAIL#<email>` 마커 Put 을 묶고 **둘 다** `attribute_not_exists(PK)` 조건을 건다 — 마커가 이미 있으면 트랜잭션 전체가 취소된다. user 삭제 시 마커도 함께 지운다. 애플리케이션 레벨 select-then-insert 는 경합에 취약해서 대안이 아니다

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
- 보호 라우트: Next.js 16 은 `middleware.ts` 가 없다 → **`proxy.ts`**(아래 참조). 단, proxy 는 *낙관적 리다이렉트*용이고 **실질 인가 검사는 각 라우트·서버 액션에서 세션을 다시 확인**한다 (CVE-2025-29927 의 교훈)
- **로그인 버튼**: 2단계에서 만든 `src/app/page.tsx` 의 자리표시자를 채운다. `"use client"` 컴포넌트에서 Mantine `Button` 으로 `authClient.signIn.social({ provider: "google" })` / `authClient.signOut()` 을 부르고, 세션 유무로 "Google 로그인" ↔ "로그아웃"을 바꾼다. `/` 화면의 요소는 **프로젝트명 + 테마 토글 + 로그인 버튼** 셋으로 끝난다 — 대시보드·프로필 같은 *새 화면*을 덧붙이지 않는다. 위 라우트 핸들러는 화면이 아니라 필수 배선이므로 이 제한과 무관하다

**`proxy.ts` 는 이 스캐폴드에서 만들지 않는다** — 보호할 라우트가 아직 없기 때문이다(페이지가 하나뿐이다). 나중에 추가할 때의 정본은 아래고, 파일 위치는 `--src-dir` 기준 **`src/proxy.ts`**(`app` 과 같은 높이), 함수는 default export 이거나 이름이 `proxy` 여야 한다:

```ts
// src/proxy.ts
import { getSessionCookie } from "better-auth/cookies";
import { NextResponse, type NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  // 쿠키의 *존재*만 본다 — 검증이 아니다. 손으로 만든 쿠키도 여기는 통과한다
  if (!getSessionCookie(request)) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"], // 보호할 경로만
};
```

`matcher` 를 생략하면 `_next/static`·`public` 까지 **모든 요청이** proxy 를 타서 CSS·이미지가 리다이렉트에 걸린다. 그리고 **서버 액션은 별도 라우트가 아니라 그 액션이 놓인 라우트로 가는 POST** 다 — matcher 를 좁히거나 액션을 다른 라우트로 옮기는 순간 커버리지가 조용히 사라진다. 그래서 인가는 라우트·액션 안에서 `auth.api.getSession` 으로 다시 확인한다.

**Google Cloud Console 리다이렉트 URI** (사용자가 등록):
- `http://localhost:3000/api/auth/callback/google`
- `https://<domain>/api/auth/callback/google`

**환경변수** — `.env.example` 은 커밋한다. **발급받은 시크릿만 비우고, 비밀이 아닌 로컬 기본값은 채운다** — 받는 사람이 뭘 넣어야 할지 알 수 있어야 한다:

```
BETTER_AUTH_SECRET=      # openssl rand -hex 32
BETTER_AUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
AWS_REGION=ap-northeast-2
DYNAMODB_TABLE_NAME=<table>               # 1단계에서 확정한 값 — 비밀이 아니므로 채워 둔다
DYNAMODB_ENDPOINT=http://localhost:8083   # 로컬 개발 전용. 운영에서는 반드시 비운다
```

**`.gitignore` 에 예외를 추가해야 실제로 커밋된다.** 스캐폴더의 `.gitignore` 는 `.env*` 로 **`.env.example` 까지 무시한다**:

```
# env files (can opt-in for committing if needed)
.env*
!.env.example
```

`!.env.example` 한 줄을 그 아래에 넣는다. 빼면 `git add -A` 가 **조용히 건너뛴다** — 에러도 경고도 없고, 필요한 환경변수를 알려주는 유일한 파일이 저장소에 영원히 안 들어간다.

저장소가 있으면 `git check-ignore -q .env.example` 가 **exit 1**(= 무시되지 않음)이어야 한다. **`-v` 를 붙이지 않는다** — verbose 모드는 negation 규칙까지 "매치"로 세서 exit 0 을 돌려주므로 판정이 뒤집힌다. 더 확실한 확인은 `git add .env.example && git ls-files .env.example` 가 비어 있지 않은 것이다.

**`.env.local` 은 스킬이 만든다** — `.env.example` 을 복사하고 `BETTER_AUTH_SECRET` 만 `openssl rand -hex 32` 로 채운다. 이 값은 어디서도 발급받은 게 아니라 이 머신에서 방금 만든 난수이고 `.gitignore` 안에 있으므로, 사용자를 기다릴 이유가 없다 — 없으면 `pnpm dev` 가 아예 안 떠서 아래 검증을 못 한다. **Google 값 2개는 비워 두고 사용자가 채운다.**

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

**로컬 기본값 두 개는 운영에서 반드시 바꾼다** — 둘 다 `.env.example` 에 localhost 로 적혀 있어 그대로 배포되기 쉽다:

| 키 | 운영에서 |
|---|---|
| `DYNAMODB_ENDPOINT` | **비운다.** 남으면 앱이 존재하지 않는 localhost:8083 을 치며 죽는다 |
| `BETTER_AUTH_URL` | **실제 오리진**(`https://<domain>`). localhost 로 남으면 Better Auth 가 OAuth 리다이렉트 URI 를 localhost 로 만들어 Google 이 거부하고, 쿠키 도메인도 어긋나 로그인이 통째로 실패한다 |

배포 매니페스트에서 이 두 키를 확인한다.

운영에서 AWS 자격증명은 **환경변수가 아니라 역할**로 준다 (ECS 태스크 롤 / EKS IRSA). `NEXT_PUBLIC_*` 은 빌드 시점에 이미지에 박히므로 시크릿을 넣지 않는다.

> 검증: `docker compose up -d dynamodb` → `pnpm dev` → Google 로그인 → 세션 유지 → 로그아웃. `aws dynamodb scan --table-name <table> --endpoint-url http://localhost:8083` 에 `user`·`session`·`account` 아이템이 보임. **AWS 계정에는 아무것도 만들지 않은 상태여야 한다.**
>
> **Google OAuth 클라이언트가 아직 없으면** 여기서 로그인 플로우를 검증할 수 없다. 이때는 멈추지 말고 (a) 사용자에게 클라이언트 발급과 리다이렉트 URI 등록을 *요청*한 뒤 (b) 6단계 어댑터 테스트로 배선의 정합을 대신 검증하고 (c) 완료 보고에 로그인 플로우를 `SKIP + 사유` 로 기록한다. 이 단계는 Rules 의 "검증 통과 전 진행 금지"에 대한 **명시적 예외**다 — 사용자 계정 작업에 의존하기 때문이다.
