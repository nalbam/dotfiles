# nextjs-init — 7–8단계: Docker·ECR 릴리스와 검증 게이트

`nextjs-init` 스킬의 단계별 상세다. Stack·Scope·Rules 등 전체 맥락과 단계 색인은 `SKILL.md` 가 source 다.

## 7. Docker + ECR

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

## 8. 검증 게이트

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
