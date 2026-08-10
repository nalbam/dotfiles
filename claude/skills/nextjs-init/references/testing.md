# nextjs-init — 6단계: 테스트 (Vitest + DynamoDB Local)

`nextjs-init` 스킬의 단계별 상세다. Stack·Scope·Rules 등 전체 맥락과 단계 색인은 `SKILL.md` 가 source 다.

## 6. 테스트 — Vitest + DynamoDB Local

```bash
pnpm add -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom vite-tsconfig-paths
```

`vitest.config.mts` — Next.js 공식 구성에 `env`·`globalSetup` 두 줄만 더한다:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    // 테스트 워커로 전달 — 아래 "엔드포인트는 test.env 로" 참조.
    // 세 개를 다 줘야 한다. CI 에는 .env.local 이 없어서 여기가 유일한 출처다.
    env: {
      DYNAMODB_ENDPOINT: "http://localhost:8084",
      AWS_REGION: "ap-northeast-2",          // 빠지면 "Region is missing"
      DYNAMODB_TABLE_NAME: "<table>-test",
    },
    globalSetup: ["./vitest.globalSetup.ts"], // 테이블 생성
  },
});
```

**세 개를 다 주는 이유** — 5단계 클라이언트가 `process.env.AWS_REGION!` 과 `DYNAMODB_TABLE_NAME` 을 읽는데, **테스트 워커는 `.env.local` 을 물려받지 않는다.** Vite 는 `.env` 파일에서 `VITE_` 접두사가 붙은 값만 노출하므로, 이 세 변수의 출처는 로컬이든 CI 든 `test.env` 하나뿐이다. `AWS_REGION` 이 없으면 `endpoint` 를 명시했어도 AWS SDK 가 자체 리전 탐색 체인을 돌고 실패한다 — `Error: Region is missing`.

`package.json` 에 `"test": "vitest run"`, `"test:watch": "vitest"`. **CI·검증 게이트에는 반드시 `vitest run`** — 인자 없는 `vitest` 는 watch 모드로 떠서 영원히 끝나지 않는다.

전역 환경은 jsdom 이고, 도메인·어댑터 테스트는 파일 상단 docblock 으로 node 로 내린다:

```ts
// @vitest-environment node
```

glob 으로 환경을 나누는 `environmentMatchGlobs` 는 현행 Vitest 문서에 없다 — docblock 을 쓴다.

**테스트는 `dynamodb-test`(포트 8084)를 쓴다** — 4단계에서 띄운 개발용 인스턴스가 아니다. `-sharedDb` 때문에 같은 인스턴스를 쓰면 테스트가 개발 데이터를 지운다.

**테이블명에 `-test` 를 붙이는 것이 그 방어선의 두 번째 겹이다.** `test.env` 의 엔드포인트가 어떤 이유로든 8083 으로 새도, 이름이 다르면 테스트가 개발 테이블에 닿지 못한다. 인스턴스를 다른 프로젝트와 공유하므로(4단계) 값이 어긋날 경로가 그만큼 늘어난다.

테스트 인스턴스는 `-inMemory` 라 기동할 때마다 비어 있으므로 **테이블 생성을 `globalSetup` 에 둔다**. 4단계의 스키마를 **SDK `CreateTableCommand` 로** 만든다 — AWS CLI 를 호출하지 않는다. 테스트가 CLI 설치 여부에 의존하면 CI 에서 깨진다.

```ts
// vitest.globalSetup.ts — 테이블 생성만 한다
// 상수로 박는다. globalSetup 은 process.env 로 아무것도 받지 못한다 (아래 참조).
const ENDPOINT = "http://localhost:8084";
const REGION = "ap-northeast-2";
const TABLE = "<table>-test";

export default async function () {
  // 재실행 가능하게: 이미 있으면 지우고 다시 만든다. -inMemory 는 컨테이너 기동에만
  // 비워지므로, 이게 없으면 두 번째 `pnpm test` 가 첫 번째의 행과 충돌한다.
  // DeleteTable 은 반드시 이 TABLE 한 개만 — 인스턴스를 다른 프로젝트와 공유한다 (4단계).
  //
  // new DynamoDBClient({
  //   endpoint: ENDPOINT,
  //   region: REGION,
  //   credentials: { accessKeyId: "local", secretAccessKey: "local" },
  // }).send(new CreateTableCommand({ /* 4단계 키 레이아웃 */ }))
  // ResourceNotFoundException(삭제) / ResourceInUseException(생성) 은 무시한다 (멱등)
}
```

**`globalSetup` 은 `process.env` 로 아무것도 받지 못한다.** `test.env` 는 워커 전용이고(Vitest 문서: *"These variables will not be available in the main process"*), `.env.local` 은 Vite 가 `VITE_` 접두사 없는 값을 `process.env` 에 넣지 않아 역시 안 보인다 — Vitest 4 에서 확인했다. 그래서 엔드포인트·리전·테이블명을 **상수로 박고, `test.env` 에 같은 값을 적는다.** 여기서 `process.env.AWS_REGION` 을 읽으려 하면 `undefined` 로 `Region is missing` 이 난다.

**두 곳의 값이 갈리면 조용히 깨진다.** globalSetup 이 만든 테이블과 워커가 찾는 테이블이 달라져 `ResourceNotFoundException` 이 난다. 리전까지 맞춰야 하는 이유는 **CI 의 `services:` 컨테이너가 `-sharedDb` 없이 돌기 때문**이다 — DynamoDB Local 이 (accessKeyId, region) 조합마다 별도 DB 를 만든다 (4단계 함정 2). **로컬에서는 `-sharedDb` 가 이 불일치를 가려주므로 CI 에서만 드러난다.**

**엔드포인트를 `globalSetup` 에서 `process.env` 로 넘기려 하지 않는다.** Vitest 문서가 못박는다 — *"the global setup is running in a different global scope before test workers are even created."* globalSetup 은 컨테이너에 테이블을 만드는 부수효과만 맡고, 테스트가 읽을 값은 `test.env` 로 준다. 그러면 5단계의 클라이언트가 `DYNAMODB_ENDPOINT` 를 그대로 집어 8084 를 본다. 워커가 실제로 8084 를 보는지 확인하는 가드가 필요하면 `setupFiles` 에 둔다 — 거기가 `test.env` 가 보이는 유일한 자리다.

**무엇을 테스트하는가** — 4·5단계에서 표로만 적어둔 것을 실행 가능하게 만든다:

| 대상 | 테스트 |
|------|--------|
| 4단계 접근 패턴 7개 | 패턴마다 실제 쿼리 1개. 통과 = 키 설계가 실제로 성립한다는 증거 |
| 어댑터 계약 1 (Scan 폴백 금지) | 인덱스로 못 푸는 `where` 에 **throw 하는지**. 조용히 결과를 돌려주면 실패 |
| 어댑터 계약 2 (지원 연산자) | `eq`·`in` 통과, 미지원 연산자는 명확한 에러 |
| 어댑터 계약 3 (파생 키 재계산) | email 변경 후 새 email 로 조회되고 옛 키로는 안 잡히는지 — 마커 스왑 후 옛 email 로 재가입이 *가능*해지는 것까지 |
| 어댑터 계약 4 (TTL) | session `create` → 저장 아이템의 `expiresAt` 이 **Number**(epoch seconds), `expiresAtIso` 는 원본 ISO, 반환값의 `expiresAt` 은 다시 ISO. user `create` → 둘 다 부재 |
| 어댑터 계약 5 (중복 가입 방지) | 같은 email 로 `create` 2회 → 하나만 성공 |
| 도메인·유스케이스 | DynamoDB 없이 순수 단위 테스트 (외부 의존 0 이라는 3단계 경계의 증명) |

**Server Component 는 대상에서 뺀다** — Next.js 공식 문서가 *"Since `async` Server Components are new to the React ecosystem, Vitest currently does not support them"* 이라고 명시한다. 동기 컴포넌트만 단위 테스트하고 async 는 E2E 로 미룬다.

**Mantine 컴포넌트 테스트를 추가한다면 셋업이 두 가지 더 붙는다** — 위 표에 컴포넌트 테스트가 없으므로 *지금은 하지 않고*, 필요해질 때 이 두 개를 같이 넣는다. 빠뜨리면 첫 테스트가 렌더 단계에서 죽는다:

1. **`MantineProvider theme={theme} env="test"` 로 감싸는 커스텀 `render` 헬퍼.** provider 없이 렌더하면 Mantine 컴포넌트가 테마를 못 찾는다. `env="test"` 는 전환 애니메이션을 끈다
2. **jsdom 에 없는 브라우저 API 목** (`setupFiles`) — `window.matchMedia`, `ResizeObserver`, `HTMLElement.prototype.scrollIntoView`. Mantine 의 Vitest 가이드에 정본이 있다

> 검증: `docker compose up -d dynamodb-test` → `pnpm test` 전부 통과. 접근 패턴 7개 테스트가 모두 존재해야 한다. 테스트 후 개발용 인스턴스의 데이터가 그대로 남아 있는지도 확인한다 (남지 않으면 두 인스턴스가 섞인 것이다).
