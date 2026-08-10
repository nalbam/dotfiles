# nextjs-init — 1–3단계: 사전 확인 · 스캐폴딩 · 레이어

`nextjs-init` 스킬의 단계별 상세다. Stack·Scope·Rules 등 전체 맥락과 단계 색인은 `SKILL.md` 가 source 다.

## 1. 사전 확인 — 환경과 대상 경로

```bash
node -v            # v24.x 기대
corepack enable && pnpm -v   # 11.x 기대
aws sts get-caller-identity  # AWS 사용 시 (실패해도 진행 가능 — 배포 단계에서만 필요)
ls -A <target-dir> 2>/dev/null
```

버전이 다르면 *멈추고 보고*한다 — 임의로 다운그레이드하지 않는다. 대상 디렉토리가 비어있지 않으면 사용자에게 확인한다.

사용자에게 확인할 값: **프로젝트명**, **AWS 계정 ID**, **AWS 리전**, **DynamoDB 테이블명**, **ECR 리포지토리명**, **OIDC IAM 역할명**. 정해지지 않았으면 프로젝트명 기반 기본값을 제안하고 승인받는다 — 계정 ID·리전·역할명은 7단계 워크플로에 평문으로 박히므로 여기서 확정해야 한다.

> 검증: 위 값이 모두 확정됨.

## 2. 스캐폴딩

```bash
pnpm create next-app@latest <name> \
  --typescript --no-tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-pnpm --disable-git --skip-install --yes
```

**`--skip-install` 이 선택이 아니라 필수다.** pnpm 11 은 postinstall 빌드를 기본 차단하고, 미승인 상태의 `pnpm install` 을 `ERR_PNPM_IGNORED_BUILDS` 로 **exit 1** 시킨다. `--skip-install` 없이 스캐폴딩하면 `create-next-app` 이 그 실패를 그대로 받아 **`Aborting installation.` 으로 중단하고**, `AGENTS.md`·`CLAUDE.md` 같은 뒷단 파일이 빠진 **반쪽 프로젝트가 남는다.** 승인을 먼저 넣고 설치하는 순서로 간다.

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
| **남긴다** | `src/app/layout.tsx`·`favicon.ico`, 설정 파일 전부(`tsconfig`·`eslint.config.mjs`·`next.config.ts`·`next-env.d.ts`·`pnpm-workspace.yaml`), `AGENTS.md`·`CLAUDE.md` |
| **뒤에서 만든다** | `postcss.config.mjs`·`src/app/theme.ts`·`ThemeToggle` + `theme-toggle.module.css` (아래 Mantine 셋업), `src/app/api/auth/[...all]/route.ts` (5단계), `src/lib/auth-client.ts` |

```bash
rm public/next.svg public/vercel.svg public/file.svg public/globe.svg public/window.svg
rm src/app/page.module.css src/app/globals.css   # 아래 "왜 globals.css 를 지우는가" 참조
touch public/.gitkeep   # 아래 "왜 .gitkeep 인가" 참조 — 빼면 CI 의 docker build 가 깨진다
```

**왜 `.gitkeep` 인가** — `public/` 에 있는 건 저 svg 5개뿐이다(`favicon.ico` 는 `src/app/` 이다). 지우면 **빈 디렉토리**가 되고 git 은 빈 디렉토리를 추적하지 않는다. 그런데 `.next/standalone` 에는 `public/` 이 들어가지 않아서 7단계 Dockerfile 이 직접 `COPY` 해야 한다 → 신규 체크아웃에는 그 경로가 없으니 **CI 의 `docker build` 만 실패한다.** 로컬은 빈 디렉토리가 남아 있어 통과한다.

**`AGENTS.md`·`CLAUDE.md` 는 남긴다** — 데모가 아니다. `AGENTS.md` 는 *"Read the relevant guide in `node_modules/next/dist/docs/` before writing any code"* 라고 지시하고 `CLAUDE.md` 는 그걸 `@AGENTS.md` 로 import 하는 한 줄이다. **설치된 버전의 문서가 이 스킬의 버전 서술보다 정확하므로**, 아래 내용과 실제가 어긋나면 그쪽을 믿는다. 프로젝트 지침을 따로 쓸 때 `CLAUDE.md` 의 import 한 줄을 지우지 않는다.

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

- **`src/app/layout.tsx`** — 지운 `./globals.css` import 자리에 `import "@mantine/core/styles.layer.css"`. `metadata.title` 을 프로젝트명으로 (기본값 `"Create Next App"` 을 남기지 않는다). `<html lang="ko" {...mantineHtmlProps} className={/* Geist 변수 — 그대로 둔다 */}>`, `<head>` 에 `<ColorSchemeScript defaultColorScheme="auto" />` (빼면 hydration 전에 색상 속성을 못 세워 새로고침마다 색이 번쩍인다), `<body>` 를 `<MantineProvider theme={theme} defaultColorScheme="auto">` 로 감싼다
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

## 3. 레이어 뼈대 — Clean Architecture

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
