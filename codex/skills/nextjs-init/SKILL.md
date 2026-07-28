---
name: nextjs-init
description: Scaffold a new Next.js 16 project — App Router, TypeScript strict, Mantine 9, Better Auth + Google OAuth on DynamoDB, Clean Architecture, ECR push. 새 Next.js 프로젝트 생성, 초기 셋업, 보일러플레이트 구성.
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
  --typescript --no-tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-pnpm --disable-git --skip-install --yes
```

**`--skip-install` 이 선택이 아니라 필수다.** pnpm 11 은 postinstall 빌드를 기본 차단하고, 미승인 상태의 `pnpm install` 을 `ERR_PNPM_IGNORED_BUILDS` 로 **exit 1** 시킨다. `--skip-install` 없이 스캐폴딩하면 `create-next-app` 이 그 실패를 그대로 받아 **`Aborting installation.` 으로 중단하고**, `AGENTS.md`·`AGENTS.md` 같은 뒷단 파일이 빠진 **반쪽 프로젝트가 남는다.** 승인을 먼저 넣고 설치하는 순서로 간다.

**빌드 스크립트 승인 — 설치 전에 파일로 적는다.** `create-next-app` 은 `pnpm-workspace.yaml` 을 `ignoredBuiltDependencies` 만 채워서 만들어 둔다. 여기에 `allowBuilds` 를 직접 추가한다:

```yaml
# pnpm-workspace.yaml — 워크스페이스를 안 써도 필요하다
allowBuilds:
  sharp: true
  unrs-resolver: true
ignoredBuiltDependencies:   # 스캐폴더가 넣은 것 — 지우지 않는다
  - sharp
  - unrs-resolver
```

두 키가 공존하는 게 정상이고 `allowBuilds` 쪽이 이긴다. 그 다음 설치한다:

```bash
pnpm install
```

**`pnpm approve-builds --all` 을 먼저 부르려 하지 않는다.** 그 명령은 설치된 `node_modules` 를 훑어 후보를 찾으므로 설치 전에는 *"There are no packages awaiting approval"* 만 출력하고 아무것도 안 한다 — 실패하는 `pnpm install` 을 한 번 돌려 `node_modules` 를 채운 뒤에야 동작하는, 순서가 뒤집힌 경로다. 두 줄을 손으로 적는 쪽이 짧고 결정적이다.

**대상은 두 개다 — `unrs-resolver` 와 `sharp`.** 전자는 `eslint-config-next` 의 TS 리졸버, 후자는 `next/image` 의 운영 이미지 최적화다. 하나만 승인하면 남은 하나로 다시 막힌다.

**막히는 건 정책 게이트 때문이고 네이티브 바이너리가 없어서가 아니다** — `unrs-resolver` 의 prebuilt `.node` 는 승인 없이도 설치돼 있고, 게이트를 우회하면 `eslint` 자체는 정상 동작한다. 그래서 "린트가 깨졌다"고 eslint 설정을 뒤지면 시간을 버린다.

**`pnpm-workspace.yaml` 을 반드시 커밋한다.** 빠지면 CI 와 Docker 의 `pnpm install --frozen-lockfile` 이 **exit 1** 로 죽고, 그쪽에는 승인을 눌러 줄 사람이 없다. 7단계 Dockerfile 의 deps 스테이지에서도 `package.json`·lockfile 과 **함께 COPY** 해야 한다.

이후:
- **`pnpm add -D typescript@^6`** — 스캐폴더는 `^5` 를 깐다. 아래 이유를 읽고 넘어간다
- `package.json` 에 `"packageManager": "pnpm@11.x.x"` 확인 (없으면 추가)
- `package.json` 에 `"engines": { "node": ">=24" }` 추가 — 1단계에서 손으로 확인한 요구를 저장소에 남겨 다른 머신·CI 에서도 드러나게 한다
- `next.config.ts` 에 `output: "standalone"` 추가 — Docker 이미지 최소화의 전제
- `tsconfig.json` 의 `strict: true` 확인
- `--eslint` 는 `eslint@^9` + `eslint-config-next` 와 `"lint": "eslint"` 스크립트를 넣는다. **Next.js 16 에서 `next lint` 는 제거됐으므로** 8단계 게이트의 `pnpm lint` 는 ESLint CLI 를 부르는 것이다

**왜 TypeScript 를 핀하는가** — `create-next-app` 이 넣는 범위는 `^5`(→ 5.9.x)라 저절로 7 로 가지는 않는다. 문제는 npm `latest` 가 이미 **7.x** 라는 것이다 — 나중에 누가 `pnpm add -D typescript` 를 한 번만 쳐도 그대로 올라간다. TS 7(Project Corsa)은 Go 네이티브 재작성이면서 **JS Compiler API 를 패키지에서 제거했다** — 메인 엔트리가 버전 스텁이고 `./unstable/*` 서브패스만 남아 있다. 결과:

- `next build` 의 타입체크가 그 API 를 쓴다 → 실패한다. Next.js 는 `tsc` CLI 를 직접 부르는 `experimental.useTypeScriptCli` 로 대응했지만 **16.3 preview 전용**이고 stable(16.2.x)엔 없다
- `@typescript-eslint/parser` 도 그 API 로 `.ts` 를 파싱한다 → `eslint-config-next` 가 통째로 죽는다. typescript-eslint 는 canary 까지 peer 가 `>=4.8.4 <6.1.0` 이라 우회로가 없다

즉 TS 7 은 3단계(레이어 강제)와 8단계(검증 게이트)를 동시에 무력화한다. **실질 상한은 typescript-eslint 의 peer 인 `<6.1.0`** 이고 `^6` 이 그 안에서 가장 높으면서 strict 기본값이라 이 스킬과 결이 맞는다 — 스캐폴더의 `^5` 를 그대로 둬도 깨지진 않으니, 요점은 버전 자체가 아니라 **상한을 알고 범위를 닫아 두는 것**이다.

한 가지 더: `eslint-config-next` 가 끌어오는 `typescript-eslint` 는 `^8.46.0` 인데 **8.46.0 자체의 peer 는 `<6.0.0`** 이다. 새로 설치하면 캐럿이 최신 8.x(`<6.1.0`)를 잡아 문제가 없지만, 오래된 lockfile 을 재사용하면 TS 6 에서 peer 경고가 뜬다.

**Next.js 16.3 이 stable 이 되면 그때 재검토한다** — 그 전엔 preview 채널 + 린터 교체(oxlint/Biome)가 딸려온다.

**보일러플레이트 제거** — 지우는 대상은 **템플릿·샘플 산출물뿐이다.** 동작에 필요한 파일은 하나도 지우지 않는다.

| | 대상 |
|---|---|
| **지운다** | `public/` 의 svg 5개 (`next`·`vercel`·`file`·`globe`·`window`), `src/app/page.tsx` 의 데모 내용, `src/app/page.module.css`, `src/app/globals.css` (+ `layout.tsx` 의 import 한 줄), `layout.tsx` 의 `"Create Next App"` metadata, `create-next-app` 이 만든 README 본문 (실제 내용은 8단계에서 쓴다) |
| **남긴다** | `src/app/layout.tsx`·`favicon.ico`, 설정 파일 전부(`tsconfig`·`eslint.config.mjs`·`next.config.ts`·`next-env.d.ts`·`pnpm-workspace.yaml`), `AGENTS.md`·`AGENTS.md` |
| **뒤에서 만든다** | `postcss.config.mjs`·`src/app/theme.ts`·`ThemeToggle` + `theme-toggle.module.css` (아래 Mantine 셋업), `src/app/api/auth/[...all]/route.ts` (5단계), `src/lib/auth-client.ts` |

```bash
rm public/next.svg public/vercel.svg public/file.svg public/globe.svg public/window.svg
rm src/app/page.module.css src/app/globals.css   # 아래 "왜 globals.css 를 지우는가" 참조
touch public/.gitkeep   # 아래 "왜 .gitkeep 인가" 참조 — 빼면 CI 의 docker build 가 깨진다
```

**왜 `.gitkeep` 인가** — `public/` 에 있는 건 저 svg 5개뿐이다(`favicon.ico` 는 `src/app/` 이다). 지우면 **빈 디렉토리**가 되고 git 은 빈 디렉토리를 추적하지 않는다. 그런데 `.next/standalone` 에는 `public/` 이 들어가지 않아서 7단계 Dockerfile 이 직접 `COPY` 해야 한다 → 신규 체크아웃에는 그 경로가 없으니 **CI 의 `docker build` 만 실패한다.** 로컬은 빈 디렉토리가 남아 있어 통과한다.

**`AGENTS.md`·`AGENTS.md` 는 남긴다** — 데모가 아니다. `AGENTS.md` 는 *"Read the relevant guide in `node_modules/next/dist/docs/` before writing any code"* 라고 지시하고 `AGENTS.md` 는 그걸 `@AGENTS.md` 로 import 하는 한 줄이다. **설치된 버전의 문서가 이 스킬의 버전 서술보다 정확하므로**, 아래 내용과 실제가 어긋나면 그쪽을 믿는다. 프로젝트 지침을 따로 쓸 때 `AGENTS.md` 의 import 한 줄을 지우지 않는다.

**"화면이 하나"라는 말은 라우트가 하나라는 뜻이 아니다.** 사람이 보는 화면은 `/` 하나지만, 인증은 **페이지가 아니라 API 라우트**로 동작한다 — `authClient.signIn.social()` 이 Google 로 보내고 돌아오는 곳이 `/api/auth/callback/google` 이며, 5단계의 catch-all 핸들러가 그걸 받는다. 그래서 이 구성에는 별도 로그인 페이지가 *필요 없을* 뿐이고, 나중에 이메일·비밀번호 로그인처럼 화면이 필요한 방식을 추가하면 그때는 만든다.

`--src-dir` 로 만들었으므로 **코드는 `src/app/` 아래**고 `public/` 만 저장소 루트에 남는다 — 아래 경로는 전부 그 기준이다.

`src/app/page.tsx` 가 `/next.svg`·`/vercel.svg` 와 `./page.module.css` 를 참조하고 `layout.tsx` 가 `./globals.css` 를 import 하므로, **에셋·스타일시트만 지우면 빌드가 깨진다** — 아래 파일 교체와 한 묶음으로 해야 한다.

**Mantine 셋업**

```bash
pnpm add @mantine/core @mantine/hooks @tabler/icons-react
pnpm add -D postcss postcss-preset-mantine postcss-simple-vars
```

**아이콘은 `@tabler/icons-react` 다** — Mantine 은 아이콘을 함께 배포하지 않는다. 이게 Mantine 문서의 짝이고, **Next.js 의 기본 `optimizePackageImports` 목록에 이미 들어 있어서** 수천 개 export 를 가진 패키지인데도 설정 없이 트리셰이킹된다 (Mantine 자신은 그 목록에 없다 — 아래 참조).

**`postcss.config.mjs` 를 새로 만든다** — `--no-tailwind` 스캐폴드에는 이 파일이 아예 없다:

```js
// postcss.config.mjs — 객체를 변수에 담고 export 한다. Mantine 문서는 익명 default
// export 로 적어 두는데, 그러면 eslint-config-next 의 import/no-anonymous-default-export
// 경고가 뜬다 (에러는 아니라 게이트는 통과하지만 매번 로그에 남는다).
const config = {
  plugins: {
    "postcss-preset-mantine": {},
    "postcss-simple-vars": {
      variables: {
        "mantine-breakpoint-xs": "36em",
        "mantine-breakpoint-sm": "48em",
        "mantine-breakpoint-md": "62em",
        "mantine-breakpoint-lg": "75em",
        "mantine-breakpoint-xl": "88em",
      },
    },
  },
};

export default config;
```

**이 프리셋은 Mantine 이 배포한 CSS 와 무관하다** — `@mantine/core` 의 스타일시트는 이미 컴파일된 채로 온다. 프리셋이 필요한 쪽은 *앞으로 쓸 CSS 모듈*이다: `light-dark()`, `@mixin dark`/`@mixin light`, `rem()`. 빠뜨리면 첫 CSS 모듈에서 **에러 없이 조용히 안 먹는다.** `postcss-simple-vars` 도 같다 — 없으면 `@media (--mantine-breakpoint-sm)` 이 그냥 무시된다.

**`@mantine/core/styles.layer.css` 로 import 한다** (`styles.css` 가 아니라). CSS 모듈의 클래스와 Mantine 의 클래스는 specificity 가 같아서 **import 순서가 승부를 가르는데**, Next.js 의 CSS 순서는 import 그래프를 따라가므로 손으로 보장할 수 없다. Mantine 이 `@layer mantine` 판본을 따로 배포하고 문서가 Next.js 를 그 대표 사례로 드는 이유가 이것이다 — layer 에 들어가면 layer 밖의 내 CSS 가 항상 이긴다. **`styles.css` 와 `styles.layer.css` 를 동시에 import 하지 않는다.**

**왜 `globals.css` 를 지우는가** — `@mantine/core` 의 스타일시트에 리셋(`box-sizing`, `margin: 0`)과 `body` 의 배경·색·폰트가 **이미 들어 있다.** 스캐폴더의 `globals.css` 는 같은 것을 `--background`/`--foreground` 와 `@media (prefers-color-scheme: dark)` 로 칠하므로, 남겨두면 두 벌이 겹치고 **다크 모드가 Mantine 토글이 아니라 OS 설정을 따라간다.** 전역 CSS 가 나중에 필요해지면 그때 빈 파일로 다시 만든다.

교체할 파일 2개 + 신규 3개:

- **`src/app/layout.tsx`** — 지운 `./globals.css` import 자리에 `import "@mantine/core/styles.layer.css"`. `metadata.title` 을 프로젝트명으로 (기본값 `"Create Next App"` 을 남기지 않는다). `<html lang="ko" {...mantineHtmlProps} className={/* Geist 변수 — 그대로 둔다 */}>`, `<head>` 에 `<ColorSchemeScript defaultColorScheme="auto" />`, `<body>` 를 `<MantineProvider theme={theme} defaultColorScheme="auto">` 로 감싼다
- **`src/app/theme.ts`** (신규) — `createTheme({ fontFamily: "var(--font-geist-sans)", fontFamilyMonospace: "var(--font-geist-mono)" })`
- **`src/app/page.tsx`** — 아래로 전부 교체
- **`ThemeToggle`** + **`theme-toggle.module.css`** (신규) — 아래

```tsx
import { Stack, Title } from "@mantine/core";
import { ThemeToggle } from "./theme-toggle";

export default function Page() {
  return (
    <Stack align="center" justify="center" mih="100dvh" gap="lg">
      <Title order={1}>{/* 프로젝트명 */}</Title>
      <ThemeToggle />
      {/* 로그인 버튼은 5단계에서 추가 */}
    </Stack>
  );
}
```

**`providers.tsx` 는 만들지 않는다.** `@mantine/*` 패키지의 엔트리에는 `'use client'` 가 이미 붙어 있어서 `MantineProvider` 를 Server Component 인 `layout.tsx` 에 바로 넣을 수 있다 — 클라이언트 경계를 만들자고 파일을 하나 더 두지 않는다.

**`mantineHtmlProps` 를 손으로 풀어 쓰지 않는다.** 실제 값은 `{ suppressHydrationWarning: true, "data-mantine-color-scheme": "light" }` 두 개이고, hydration 경고 억제와 *페인트 이전의 초기 색상 속성*이 한 세트로 온다. `suppressHydrationWarning` 만 따로 붙이면 후자를 빠뜨린다.

**`defaultColorScheme` 은 `ColorSchemeScript` 와 `MantineProvider` 에 같은 값을 준다.** 다르면 스크립트가 세운 속성과 provider 가 마운트하며 세우는 속성이 어긋나 첫 렌더에 색이 한 번 튄다.

**`ThemeToggle` 은 현재 스킴으로 *렌더 결과를 분기하지 않는다*.** 서버는 localStorage 를 볼 수 없으므로, 스킴 값으로 JSX 를 고르는 순간 hydration mismatch 다. 아이콘 **둘 다 렌더하고 CSS 로 하나를 가린다** — 스킴 값은 `onClick` 안에서만 쓴다:

```tsx
"use client";

import { ActionIcon, useComputedColorScheme, useMantineColorScheme } from "@mantine/core";
import { IconMoon, IconSun } from "@tabler/icons-react";
import classes from "./theme-toggle.module.css";

export function ThemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const computed = useComputedColorScheme("light", { getInitialValueInEffect: true });

  return (
    <ActionIcon
      variant="default"
      aria-label="테마 전환"
      onClick={() => setColorScheme(computed === "light" ? "dark" : "light")}
    >
      {/* 두 아이콘을 항상 렌더한다 — 분기는 아래 CSS 가 한다 */}
      <IconSun className={classes.light} size={18} stroke={1.5} />
      <IconMoon className={classes.dark} size={18} stroke={1.5} />
    </ActionIcon>
  );
}
```

```css
/* src/app/theme-toggle.module.css — postcss-preset-mantine 의 mixin 이 여기서 처음 쓰인다 */
.light {
  @mixin dark { display: none; }
}

.dark {
  @mixin light { display: none; }
}
```

**`getInitialValueInEffect: true` 로는 부족하다.** 이 옵션이 미루는 건 *OS 미디어쿼리 조회*뿐이고, localStorage 에 `light`/`dark` 가 명시적으로 저장돼 있으면 클라이언트 첫 렌더에서 **그 값이 곧바로 잡힌다.** 그래서 값으로 JSX 를 분기하면 서버가 그린 것과 어긋난다 — **첫 방문에는 안 나고 토글 후 새로고침해야 드러나므로** 특히 놓치기 쉽다. `computed` 는 이벤트 핸들러에서만 읽는 값으로 두는 게 규칙이다.

**`optimizePackageImports` 는 켜지 않는다.** Next.js 의 기본 최적화 목록에 Mantine 은 없어서 켜려면 `next.config.ts` 에 명시해야 하는데, Next 문서가 이 옵션 자체를 experimental·프로덕션 비권장으로 표시한다. dev 컴파일이 느려지면 그때 `experimental: { optimizePackageImports: ["@mantine/core", "@mantine/hooks"] }` 를 추가한다.

Geist 폰트와 `favicon.ico` 는 브랜딩이 아니라 그대로 둔다. **단 Geist 는 `theme.ts` 로 연결해야 실제로 쓰인다** — 스캐폴더는 `next/font` 로 폰트를 받아 `<html>` 에 `--font-geist-sans` 를 심어줄 뿐이고, Mantine 은 그와 무관하게 자체 시스템 폰트 스택을 기본값으로 쓴다. 연결을 빠뜨리면 폰트를 다운로드해 놓고 안 쓴다. 바꾸고 싶으면 사용자에게 확인한다.

> 검증: `pnpm exec tsc -v` 가 6.x → `pnpm dev` → `/` 에 **프로젝트명과 테마 토글만** 보인다 (데모 내용이 남아 있으면 교체가 덜 된 것) → 브라우저 콘솔에 404(지운 svg)와 hydration 경고가 없다 → `grep -rn "next.svg\|vercel.svg\|Create Next App\|globals.css\|page.module.css" src public` 이 비어 있다 → `ls -A public` 에 `.gitkeep` 만 있다.
>
> **테마는 `<html>` 의 `data-mantine-color-scheme` 과 배경색을 같이 본다.** 토글할 때 속성이 `light`↔`dark` 로 바뀌고 배경이 따라와야 하며, 새로고침해도 유지돼야 한다 (localStorage). **OS 를 다크로 둔 상태에서 light 로 토글**해 봐야 `globals.css` 잔재가 드러난다 — 속성은 `light` 인데 배경만 다크로 남으면 그 파일을 안 지운 것이다.
>
> **hydration 은 토글한 뒤 새로고침해서 확인한다.** 첫 방문은 저장된 값이 없어 통과하므로, `localStorage` 에 `light`/`dark` 가 들어간 상태로 다시 그려 봐야 스킴 분기 mismatch 가 드러난다. OS 와 반대 값을 저장해 두고 새로고침하는 게 가장 확실하다.
>
> **폰트는 Geist 여야 한다.** 렌더된 텍스트의 `font-family` 가 시스템 폰트로 나오면 `theme.ts` 를 `MantineProvider` 에 안 물린 것이다.

### 3. 레이어 뼈대 — Clean Architecture

```
src/
├── domain/           # 엔티티·값 객체·리포지토리 인터페이스. 외부 의존 0
├── application/      # 유스케이스. domain 만 의존
├── infrastructure/   # DynamoDB·Better Auth·외부 API 구현. domain 인터페이스를 구현
│   ├── dynamodb/     #   client.ts, single-table 키 헬퍼, 리포지토리 구현
│   └── auth/         #   better-auth 설정 + DynamoDB 어댑터
├── lib/              # 프레임워크 글루 — auth-client 등. 그래프 밖이고 domain 만 못 쓴다
└── app/              # Next.js App Router. application 호출 + infrastructure 조립(DI)
```

**의존 방향**: `app` → `application` → `domain` ← `infrastructure`

`domain` 은 어떤 레이어도 import 하지 않는다. `infrastructure` 는 `domain` 의 인터페이스만 구현하고 `application` 을 모른다. `lib` 은 어느 레이어도 아닌 글루라 나머지 셋은 쓸 수 있고 `domain` 만 못 쓴다 — `domain` 의 "외부 의존 0" 을 깨는 가장 흔한 경로가 여기다.

디렉토리만 나누면 반드시 무너진다 — **ESLint 로 강제한다**. `import/no-restricted-paths` zones 로 금지 방향을 선언한다:

| from | 금지 target |
|------|-------------|
| `src/domain` | `src/application`, `src/infrastructure`, `src/app`, `src/lib` |
| `src/application` | `src/infrastructure`, `src/app` |
| `src/infrastructure` | `src/application`, `src/app` |

**플러그인은 따로 깔지 않는다** — `eslint-config-next` 가 `eslint-plugin-import` 를 의존성으로 갖고, flat config 에서 `import` 플러그인과 TS 리졸버(`import/resolver.typescript`)까지 이미 등록해 둔다. 같은 이름으로 다시 등록하면 인스턴스가 갈릴 때 `Cannot redefine plugin "import"` 로 죽는다. **규칙만 얹는다** — 2단계에서 생성된 `eslint.config.mjs` 의 배열에 객체 하나를 끼워 넣는다:

```js
// eslint.config.mjs — nextVitals·nextTs·globalIgnores 는 스캐폴더가 만든 그대로 둔다
const layers = {
  files: ["src/**/*.{ts,tsx}"],
  rules: {
    "import/no-restricted-paths": ["error", {
      // basePath 기본값은 cwd — 저장소 루트에서 `pnpm lint` 를 도는 전제다
      zones: [
        {
          target: "./src/domain",
          from: ["./src/application", "./src/infrastructure", "./src/app", "./src/lib"],
          message: "domain 은 어떤 레이어도 import 하지 않는다.",
        },
        {
          target: "./src/application",
          from: ["./src/infrastructure", "./src/app"],
          message: "application 은 domain 인터페이스만 의존한다 — 구현은 주입받는다.",
        },
        {
          target: "./src/infrastructure",
          from: ["./src/application", "./src/app"],
          message: "infrastructure 는 domain 인터페이스만 구현한다.",
        },
      ],
    }],
  },
};

export default defineConfig([...nextVitals, ...nextTs, layers, globalIgnores([/* 그대로 */])]);
```

`from` 한 배열에는 **디렉토리 경로만, 또는 glob 만** 담는다 — 섞으면 스키마에서 거부된다.

**여기서 `pnpm lint` 가 `ERR_PNPM_IGNORED_BUILDS` 로 죽으면 2단계의 빌드 승인을 빠뜨린 것이다** — eslint 설정이 아니라 `pnpm-workspace.yaml` 의 `allowBuilds` 를 본다. pnpm 은 스크립트 실행 전에 의존성 상태를 다시 확인하므로 `pnpm lint`·`pnpm test`·`pnpm build` 가 전부 같은 에러로 멈춘다.

> 검증: `src/domain/` 에 `import "@/infrastructure/dynamodb/client"` 한 임시 파일을 만들고 `pnpm lint` 가 위 message 로 에러를 내는지 확인 후 삭제. 통과해버리면 zones 가 아니라 `files` 패턴이나 cwd 를 의심한다.

### 4. DynamoDB Single Table Design

Better Auth 코어 스키마는 4개 모델이다 (테이블명 단수형): `user`, `session`, `account`, `verification`.

**필수 접근 패턴** — 어댑터가 이걸 못 하면 인증이 동작하지 않는다:

| # | 패턴 | 연산 |
|---|------|------|
| 1 | id 로 단건 조회 | GetItem — **session 만 Query GSI1** (아래 키 설계 참조) |
| 2 | email 로 user 조회 | Query GSI1 |
| 3 | token 으로 session 조회 — **매 요청의 hot path** | GetItem |
| 4 | userId 로 session 목록 | Query GSI2 |
| 5 | (providerId, accountId) 로 account 조회 | Query GSI1 |
| 6 | userId 로 account 목록 | Query GSI2 |
| 7 | identifier 로 verification 조회 (최신) | Query GSI1, `ScanIndexForward: false` |

**키 레이아웃** — 단일 테이블, GSI 2개:

| 모델 | PK | SK | GSI1PK | GSI1SK | GSI2PK | GSI2SK |
|------|----|----|--------|--------|--------|--------|
| user | `USER#<id>` | `USER#<id>` | `EMAIL#<email>` | `USER#<id>` | — | — |
| email 마커 | `EMAIL#<email>` | `EMAIL#<email>` | — | — | — | — |
| session | `SESSION#<token>` | `SESSION#<token>` | `SESSION#<id>` | `SESSION#<id>` | `USER#<userId>` | `SESSION#<createdAt>` |
| account | `ACCOUNT#<id>` | `ACCOUNT#<id>` | `PROVIDER#<providerId>#<accountId>` | `ACCOUNT#<id>` | `USER#<userId>` | `ACCOUNT#<providerId>` |
| verification | `VERIFICATION#<id>` | `VERIFICATION#<id>` | `IDENT#<identifier>` | `VERIFICATION#<createdAt>` | — | — |

**session 만 token 이 PK 다** — 패턴 3(token→session)은 인증된 *모든* 요청이 타고, 특히 로그인 직후엔 방금 쓴 세션을 곧바로 되읽는다. 이 경로를 GSI 에 두면 통째로 eventually consistent 가 된다(아래 함정 4) — PK 로 두면 강일관 GetItem 이고, token 기준 update·delete 도 GSI 선조회 없이 바로 친다. id 조회(패턴 1)는 드물어서 GSI1 로 보낸다. 대신 **token 은 PK 구성 요소라 in-place update 로 바꿀 수 없다** — token 이 바뀌는 update 는 delete+put 트랜잭션이다 (5단계 계약 3).

**email 마커는 유니크 제약이다** — user 의 GSI1(`EMAIL#<email>`)은 *조회*용일 뿐 중복을 막지 못한다 (GSI 에는 유니크 제약이 없다). 중복 방지는 이 마커 아이템과 트랜잭션이 맡는다 — 5단계 계약 5 참조.

추가 속성:
- `entity` — 모델명 (`user` / `session` / …). 필터·디버깅용
- `expiresAt` — **테이블의 TTL 속성. session·verification 만.** epoch seconds(**Number**)로 저장한다. 이 속성에 TTL 을 걸면 만료 세션이 자동 정리된다
- `expiresAtIso` — 바로 위 때문에 밀려난 Better Auth 의 ISO 문자열 (아래)

**`expiresAt` 이름 충돌을 그냥 넘기면 조용히 깨진다.** Better Auth 는 `supportsDates: false` 로 이 필드를 **ISO 문자열**로 주고 받는데, DynamoDB TTL 은 **Number 만** 수거하고 다른 타입은 *에러 없이 무시한다*. 그대로 두면 세션이 영원히 쌓이는데 아무 신호가 없다. 그래서 저장 시 `expiresAt` 에는 숫자를 넣고 원본 문자열은 `expiresAt` 로 되돌린다:

- **쓰기** — `expiresAtIso = <ISO>`, `expiresAt = Math.floor(Date.parse(ISO) / 1000)`
- **읽기** — 내부 속성을 벗길 때 `expiresAtIso` 를 지우고 그 값을 `expiresAt` 에 돌려놓는다. `expiresAtIso` 가 없는 옛 행은 문자열 `expiresAt` 을 그대로 갖고 있으므로 그냥 통과시킨다 (수거만 안 될 뿐 읽기는 정상)
- **순서** — 내부 속성 제거를 `where`·`sortBy` 적용 **앞**에 둔다. 저장 아이템의 `expiresAt` 은 숫자, 반환 레코드의 `expiresAt` 은 문자열이라, 원본 행에 필터를 걸면 타입이 어긋나 아무것도 안 걸린다

TTL 속성명을 `ttl` 로 따로 두면 이 장치가 전부 필요 없지만, **다른 프로젝트와 이름을 맞추는 쪽을 택했다** — 한 테이블에 auth 외 엔티티(트레이스·사용량 등)가 들어오면 그쪽 만료 필드도 자연스럽게 `expiresAt` 이 되기 때문이다.

**로컬 DynamoDB** (`compose.yaml`) — 개발과 테스트 모두 여기를 쓴다. 실제 AWS 테이블은 배포용이지 개발용이 아니다.

**이 블록은 프로젝트마다 고쳐 쓰는 것이 아니라 그대로 복사한다** — 아래 "공유 인스턴스" 참조:

```yaml
# 이 머신의 모든 프로젝트가 같은 컨테이너 쌍을 재사용한다 (아래 "공유 인스턴스").
name: localdev

services:
  # 로컬 개발용 — 데이터가 유지된다 (재시작해도 로그인 세션·테이블이 남음)
  dynamodb:
    image: amazon/dynamodb-local:3.3.0
    user: root                          # 아래 "왜 user: root 인가" 참조 — 지우면 조용히 멈춘다
    command: ["-jar", "DynamoDBLocal.jar", "-sharedDb", "-dbPath", "./data"]
    working_dir: /home/dynamodblocal
    volumes: ["dynamodb-data:/home/dynamodblocal/data"]
    ports: ["8083:8000"]
    restart: unless-stopped        # 머신 공용이라 Docker 재시작 후 알아서 돌아온다

  # 테스트용 — 매 기동마다 초기화된다
  dynamodb-test:
    image: amazon/dynamodb-local:3.3.0
    command: ["-jar", "DynamoDBLocal.jar", "-sharedDb", "-inMemory"]
    ports: ["8084:8000"]
    restart: unless-stopped

volumes:
  dynamodb-data:
```

**왜 인스턴스를 둘로 나누는가** — `-sharedDb` 는 모든 클라이언트가 *하나의 DB* 를 보게 만든다. 하나만 띄우면 테스트가 개발 중이던 데이터를 매번 지운다. 포트를 나누는 게 유일하게 안 헷갈리는 방법이다.

**공유 인스턴스 — 프로젝트마다 새 포트를 고르지 않는다.** 8083·8084 는 *이 머신의* 로컬 DynamoDB 포트이며, 모든 프로젝트가 같은 컨테이너 쌍을 재사용한다. `name: localdev` 가 그 장치다 — compose 프로젝트명이 같고 서비스 스탠자가 동일하면, 두 번째 저장소에서 `docker compose up -d dynamodb` 를 해도 기존 컨테이너를 그대로 쓰고 끝난다(`Running`). **스탠자가 한 글자라도 다르면 compose 가 컨테이너를 recreate 하므로 위 블록을 그대로 복사한다** — 출력에 `Recreated` 가 보이면 어긋난 것이다.

여기서 따라 나오는 규칙 셋:

1. **테이블명 = 프로젝트명.** 공유 인스턴스에서 테이블명이 프로젝트를 가르는 *유일한* 수단이다. `app` 같은 범용 이름을 쓰면 두 프로젝트가 에러 없이 같은 데이터를 본다
2. **초기화·정리 코드는 자기 테이블만 건드린다.** `ListTables` 로 훑어 전부 지우는 로직은 남의 프로젝트를 지운다
3. **`docker compose down -v` 를 쓰지 않는다.** 볼륨이 공유라 이 머신의 모든 프로젝트 개발 데이터가 함께 날아간다. `--remove-orphans` 도 다른 저장소가 띄운 서비스를 지운다

`docker compose ps` 에 다른 저장소의 서비스가 같이 보이는 것은 정상이다 — 한 compose 프로젝트를 나눠 쓰고 있기 때문이다. CI 는 잡마다 자기 컨테이너를 띄우므로 공유 개념이 없다 (7단계).

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
4. **GSI 일관성이 운영과 다르다.** DynamoDB Local 은 GSI 를 동기로 갱신하지만 실제 DynamoDB 의 GSI 는 *eventually consistent* 다. 위 접근 패턴 중 5개(2·4·5·6·7)가 GSI 경유이므로, 쓰기 직후 GSI 를 읽는 코드는 **로컬에서 되고 운영에서 깨진다**. 세션의 token 조회를 GSI 가 아니라 PK 로 설계한 이유가 이것이다 — 매 요청 + 로그인 직후 경로는 여기서 빼야 한다

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
  --time-to-live-specification 'Enabled=true,AttributeName=expiresAt' --region <region>
```

`<table>` 은 **프로젝트명이다** — 8083 인스턴스를 다른 프로젝트와 나눠 쓰므로 여기서 유일하지 않으면 데이터가 섞인다 (위 "공유 인스턴스").

로컬 실행 시 `--region` 값은 무엇이든 되지만 **앱의 `AWS_REGION` 과 반드시 같아야 한다** (함정 2). 테스트 인스턴스용은 `--endpoint-url http://localhost:8084` + 테이블명 `<table>-test` 이고, 이건 6단계의 `globalSetup` 이 맡는다.

> 검증: 접근 패턴 7개가 각각 어떤 인덱스로 처리되는지 표로 대응됨 (대응 안 되는 패턴이 남으면 키 설계를 고친다). `docker compose up -d dynamodb` 후 `aws dynamodb list-tables --endpoint-url http://localhost:8083` 에 테이블이 보임 — 다른 프로젝트의 테이블이 같이 나오는 것은 정상이다.

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

### 6. 테스트 — Vitest + DynamoDB Local

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

### 7. Docker + ECR

**Dockerfile** — 멀티스테이지, standalone 출력:

- `node:24-slim` 기준 (deps / builder / runner 3단계)
- deps: `COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./` → `corepack enable pnpm && pnpm install --frozen-lockfile`
- builder: 소스 전체를 COPY 한 뒤 `pnpm build` (`output: "standalone"` 전제). **`postcss.config.mjs` 가 반드시 이미지에 들어가야 한다** — 2단계에서 손으로 만든 파일이라 `.dockerignore` 를 넓게 쓰면 조용히 빠지고, 그러면 CSS 모듈의 Mantine mixin 이 컴파일되지 않는다
- runner: `.next/standalone` → `./`, `.next/static` → `./.next/static`, `public` → `./public` — 셋 다 **`COPY --chown=node:node`**. 기본 COPY 는 root 소유로 남아서, `USER node` 로 돌면 `next/image` 가 `.next/cache` 에 최적화 캐시를 못 쓴다 — `sharp` 를 승인해 둔 의미가 사라진다
- 비루트 실행 (`USER node`), `ENV HOSTNAME=0.0.0.0 PORT=3000`, `CMD ["node", "server.js"]`
- `.dockerignore` 필수: `node_modules`, `.next`, `.git`, `.env*`

**deps 스테이지에 `pnpm-workspace.yaml` 을 반드시 포함한다** — 빌드 승인(`allowBuilds`)이 그 파일에 있으므로, 빠지면 `pnpm install --frozen-lockfile` 이 `ERR_PNPM_IGNORED_BUILDS` 로 exit 1 한다 (2단계).

**`public` COPY 는 저장소에 `public/` 이 있을 때만 성공한다** — `.next/standalone` 에는 `public/` 이 들어가지 않아서 이 COPY 가 필수인데, 2단계에서 svg 를 지우면 빈 디렉토리가 되고 git 이 추적하지 않는다. `public/.gitkeep` 이 그래서 있다. 로컬 `docker build` 는 빈 디렉토리가 남아 있어 통과하므로 **CI 에서만 실패한다** — `failed to compute cache key: ... "/public": not found`.

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

**IAM 신뢰 정책** — 역할 생성은 사용자가 한다. `Principal` 의 provider ARN 은 계정에 IAM OIDC identity provider(`token.actions.githubusercontent.com`)가 **이미 등록돼 있어야** 성립한다 — GitHub OIDC 를 처음 쓰는 계정이면 그것부터다. `sub` 조건이 이 구성의 유일한 접근 통제다:

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

게이트 통과 후 **README 를 쓴다** — 2단계에서 비운 자리를 실제 내용으로 채운다. 최소 구성: 프로젝트 한 줄 소개, 로컬 셋업(`.env.example` → `.env.local` 복사 + Google 값 2개 채우기, `docker compose up -d dynamodb`, `pnpm dev`), 테스트(`docker compose up -d dynamodb-test && pnpm test`), 릴리스(`git tag v* && git push origin v*`). 이 스킬이 만든 것만 적고 도메인 설명을 지어내지 않는다.

**같은 게이트를 CI 에도 둔다** (`.github/workflows/ci.yml`) — 7단계의 릴리스 워크플로는 태그에서만 돌기 때문에 PR 을 막아주지 못한다:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  verify:
    runs-on: ubuntu-latest
    services:
      dynamodb:
        image: amazon/dynamodb-local:3.3.0
        ports: ["8084:8000"]
    steps:
      - uses: actions/checkout@v7

      - uses: pnpm/action-setup@v6      # version 생략 = packageManager 필드를 따른다
      - uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: pnpm

      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm exec tsc --noEmit
      - run: pnpm test
      - run: pnpm build

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: docker/setup-buildx-action@v4
      - uses: docker/build-push-action@v7
        with:
          context: .
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**`docker` 잡은 push 없는 빌드 스모크다** — `public/` COPY·`pnpm-workspace.yaml` 누락처럼 **신규 체크아웃에서만 깨지는 회귀**를 첫 태그 릴리스가 아니라 PR 에서 잡는다. 이게 없으면 2단계·7단계에서 말한 "CI 의 docker build 실패"가 실제로는 릴리스 시점까지 숨는다. gha 캐시를 7단계 릴리스 빌드와 공유하므로 중복 비용도 크지 않다.

**서비스 컨테이너에는 커맨드 인자를 넘길 수 없다** — `services:` 가 받는 건 `image`·`env`·`ports`·`volumes`·`options` 뿐이고, `options` 로 entrypoint 는 바꿔도 그 뒤 인자는 못 준다. 그래서 compose 의 `-sharedDb -inMemory` 가 여기엔 없는데, **CI 에서는 둘 다 필요가 없다** — 잡마다 새 컨테이너라 이미 비어 있고(`-inMemory`), 자격증명·리전이 한 잡 안에서 하나뿐이라 DB 가 갈릴 일도 없다(`-sharedDb`). 대신 **호스트 포트를 8084 로 맞추는 건 필수다** — 6단계 `globalSetup` 이 그 주소를 박아 두기 때문이다.

`pnpm/action-setup` 을 `setup-node` **앞에** 둔다 — `cache: pnpm` 이 pnpm 바이너리를 먼저 찾는다.

**`pnpm build` 로그의 `BetterAuthError: You are using the default secret` 은 무시한다.** CI 에는 `BETTER_AUTH_SECRET` 이 없어서 `next build` 가 라우트 모듈을 수집할 때 Better Auth 가 이 에러와 `Base URL is not set` 경고를 뱉는다. 빌드는 **exit 0 으로 통과한다** — 빨간 줄만 보고 시크릿을 CI 에 넣으러 가지 않는다. 빌드에는 시크릿이 필요 없고, 런타임 환경변수로 주는 게 맞다.

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

- `create-next-app` 의 *설정 파일*을 재작성하지 않는다 — 필요한 것만 덧붙인다
- 반대로 데모 페이지·Vercel 에셋(`next.svg` 등 5개)·`"Create Next App"` metadata 를 남기지 않는다 — 2단계에서 지운다
- **템플릿·샘플이 아닌 것을 지우지 않는다** — 인증 라우트·설정·레이아웃은 화면이 아니어도 필수다. "화면 1개"를 "파일 1개"로 읽지 않는다
- 요청하지 않은 *화면*을 만들지 않는다 — `/` 의 요소는 프로젝트명·테마 토글·로그인 버튼 셋이다
- `styles.css` 와 `styles.layer.css` 를 동시에 import 하지 않는다 — 같은 스타일이 두 벌 들어간다. Next.js 에서는 `styles.layer.css` 쪽이다
- `ColorSchemeScript` 를 빼지 않는다 — hydration 전에 색상 속성을 못 세워 새로고침마다 색이 번쩍인다
- `mantineHtmlProps` 를 빼고 `suppressHydrationWarning` 만 손으로 붙이지 않는다 — 초기 색상 속성이 같이 오는 프롭이다
- `defaultColorScheme` 을 `ColorSchemeScript` 와 `MantineProvider` 에 다르게 주지 않는다 — 첫 렌더에 색이 튄다
- 컬러 스킴 값으로 **렌더 결과를 분기하지 않는다** — 서버는 localStorage 를 못 봐서 hydration mismatch 다. `getInitialValueInEffect: true` 로도 못 막는다 (그건 OS 미디어쿼리만 미룬다). 둘 다 렌더하고 CSS mixin 으로 가린다
- hydration 검증을 첫 방문만으로 끝내지 않는다 — 스킴 분기 mismatch 는 **토글 후 새로고침**해야 드러난다
- `globals.css` 를 남긴 채 Mantine 을 얹지 않는다 — `body` 배경·폰트를 양쪽이 칠하고 다크 모드가 토글이 아니라 OS 설정을 따라간다
- Geist 를 `theme.fontFamily` 에 물리지 않은 채 두지 않는다 — 폰트를 받아만 놓고 안 쓴다
- Mantine 이 아이콘을 함께 준다고 가정하지 않는다 — 안 준다. `@tabler/icons-react` 를 따로 깐다
- `postcss.config.mjs` 를 Docker 이미지에서 빠뜨리지 않는다 — CSS 모듈의 mixin 이 컴파일되지 않는다
- `public/` 을 빈 디렉토리로 남기지 않는다 — git 이 추적하지 않아 CI 의 `docker build` 가 `COPY public` 에서 죽는다. `.gitkeep` 을 둔다
- `create-next-app` 이 만든 `AGENTS.md`·`AGENTS.md` 를 보일러플레이트로 오해해 지우지 않는다 — 설치된 Next.js 문서를 가리키는 포인터다
- 레이어를 디렉토리로만 나누고 lint 강제를 생략하지 않는다 — 한 달이면 무너진다
- `eslint.config.mjs` 에 `import` 플러그인을 다시 등록하지 않는다 — `eslint-config-next` 가 이미 등록한다. 규칙만 얹는다
- `typescript` 를 `@latest`(7.x)로 올리지 않는다 — Compiler API 가 없어 lint·build 가 함께 죽는다. 상한은 `<6.1.0`
- 어댑터에서 `Scan` 으로 폴백하지 않는다 — 지원 못 하는 쿼리는 던진다
- TTL 속성(`expiresAt`)에 ISO 문자열을 남기지 않는다 — DynamoDB 는 Number 가 아니면 *에러 없이* 무시한다. 세션이 영원히 쌓이는데 신호가 없다
- 내부 속성 제거를 `where`·`sortBy` *뒤*에 두지 않는다 — 저장 아이템의 `expiresAt` 은 숫자, 반환 레코드는 문자열이라 필터가 아무것도 못 잡는다
- email 유니크를 GSI 나 select-then-insert 로 보장하려 하지 않는다 — GSI 엔 유니크 제약이 없고 select-then-insert 는 경합에 진다. `EMAIL#` 마커 + `TransactWriteItems` 다
- session 의 token 조회를 GSI 에 두지 않는다 — 매 요청 + 로그인 직후 경로가 eventually consistent 가 된다. token 이 PK 다
- 게이트에 인자 없는 `vitest` 를 넣지 않는다 — watch 모드로 떠서 CI 가 끝나지 않는다
- `globalSetup` 에서 `process.env` 를 세팅해 테스트에 넘기려 하지 않는다 — 워커 생성 *전* 다른 스코프라 닿지 않는다. `test.env` 를 쓴다
- `globalSetup` 에서 `process.env` 로 엔드포인트·리전을 읽지 않는다 — `test.env` 도 `.env.local` 도 거기엔 닿지 않아 `undefined` 다. 상수로 박고 `test.env` 와 같은 값을 유지한다
- `pnpm-workspace.yaml`(`allowBuilds`)을 커밋이나 Dockerfile 의 deps COPY 에서 빠뜨리지 않는다 — CI·Docker 에는 승인을 눌러 줄 사람이 없다. 승인 대상은 `unrs-resolver` 와 `sharp` **둘 다**다
- `create-next-app` 을 `--skip-install` 없이 돌리지 않는다 — 빌드 승인 전이라 install 이 exit 1 하고, 스캐폴딩이 `Aborting installation.` 으로 중단돼 반쪽 프로젝트가 남는다
- 빌드 승인을 `pnpm approve-builds` 로 먼저 해결하려 하지 않는다 — `node_modules` 가 있어야 후보를 찾으므로 설치 전에는 아무것도 안 한다. `pnpm-workspace.yaml` 에 두 줄을 적는다
- `test.env` 에 `AWS_REGION`·`DYNAMODB_TABLE_NAME` 을 빠뜨리지 않는다 — 워커는 `.env.local` 을 물려받지 않아 `test.env` 가 유일한 출처다. 없으면 `Region is missing`
- `globalSetup` 의 리전·테이블명을 `test.env` 와 다르게 두지 않는다 — CI 는 `-sharedDb` 없이 돌아 DB 가 갈린다. 로컬에서만 통과한다
- `BETTER_AUTH_URL` 을 운영에서 localhost 로 두지 않는다 — OAuth 리다이렉트와 쿠키 도메인이 함께 깨진다
- DynamoDB Local 을 `-sharedDb` 없이 띄우지 않는다 — 자격증명·리전이 다르면 다른 DB 를 본다
- 개발과 테스트가 같은 DynamoDB Local 인스턴스를 쓰지 않는다 — `-sharedDb` 라 테스트가 개발 데이터를 지운다
- 프로젝트마다 새 포트 쌍을 고르지 않는다 — 8083·8084 고정이고 `name: localdev` 로 컨테이너를 공유한다
- 테이블명을 프로젝트명과 다르게 두지 않는다 — 공유 인스턴스에서 테이블명이 유일한 격리 수단이라, 겹치면 에러 없이 데이터가 섞인다
- `docker compose down -v` 를 쓰지 않는다 — 볼륨이 공유라 이 머신의 모든 프로젝트 개발 데이터가 함께 날아간다
- CI 의 `services:` 로 DynamoDB Local 에 `-sharedDb` 같은 인자를 넘기려 하지 않는다 — 넘길 방법이 없다. 대신 호스트 포트를 8084 로 맞춘다
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
- 반대로 `.env.example` 이 `.gitignore` 의 `.env*` 에 걸린 채 두지 않는다 — `!.env.example` 이 없으면 `git add` 가 조용히 건너뛴다
- 사용자 허가 없이 AWS 리소스를 만들거나 git commit 하지 않는다
- 검증 없이 "완료"라고 보고하지 않는다
