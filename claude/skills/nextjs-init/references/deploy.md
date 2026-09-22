# Docker·CI·ECR 설정과 검증

## Docker

Node.js는 로컬과 호환되는 버전으로 고정하고 deps / builder / runner를 나눈다.

- deps: package.json·lockfile·pnpm 승인 설정을 복사하고 frozen lockfile로 설치한다.
- builder: 소스와 PostCSS 등 빌드 설정을 포함해 standalone 빌드를 실행한다.
- runner: standalone·static·public을 실행 사용자 소유로 복사한다. 비루트로 실행하고 필요한 캐시 경로만 쓰기 가능하게 한다.
- `.dockerignore`에 node_modules·빌드 출력·.git·실제 환경변수 파일을 제외한다.
- `HOSTNAME=0.0.0.0`, 앱 포트, `node server.js`를 설정한다.
- 이미지에 실제 시크릿을 넣지 않는다. 빌드에서 인증 설정 오류가 나면 원인을 확인한다. exit 0만으로 정상이라 단정하거나 오류를 일괄 무시하지 않는다.

새 checkout 기준 Docker 빌드로 빈 public 디렉터리·승인 설정·PostCSS 누락을 확인한다.

## CI

저장소 기본 브랜치와 PR에서 다음을 실행하는 워크플로를 만든다.

1. checkout, pnpm 준비, Node.js 설정·pnpm 캐시.
2. frozen lockfile 설치.
3. lint, typecheck, `vitest run`, Next.js build.
4. push 없는 Docker 빌드.

DynamoDB Local 서비스는 테스트 endpoint의 포트를 사용하고 준비 후 테스트한다. 생성 코드와 워커의 리전·자격증명·테이블이 일치해야 한다. Actions 버전은 공식 릴리스에서 지원 여부를 확인해 고정한다.

## ECR 릴리스

기본은 `v*` 태그와 수동 실행이다. 워크플로 작성과 실제 릴리스 실행을 구분한다.

- GitHub OIDC와 `id-token: write`·`contents: read`를 사용하고 AWS 역할의 권한을 대상 ECR에 제한한다.
- AWS 리전·역할 ARN·ECR 주소는 GitHub repository variables로 받을 수 있다. 값이 없으면 배포 준비 항목으로 보고하고 로컬 생성을 중단하지 않는다.
- OIDC trust는 `aud: sts.amazonaws.com`과 해당 저장소의 허용된 ref 또는 GitHub environment로 제한한다. 저장소의 모든 ref·PR을 와일드카드로 허용하지 않는다.
- 태그용 예: `repo:<org>/<repo>:ref:refs/tags/v*`. 수동 실행도 지원하면 허용할 브랜치 ref 또는 보호된 environment를 명시한다.
- Buildx와 ECR 로그인 후 이미지를 빌드·push한다. 대상 CPU 아키텍처를 확인한다.
- 이미지 태그는 버전 태그 또는 commit SHA를 사용한다. 수동 실행의 브랜치명에는 이미지 태그에 쓸 수 없는 문자가 있을 수 있다.
- `latest`를 추가하면 ECR의 mutable tag 정책과 맞춘다. provenance·SBOM은 실제 배포 호환성 문제가 확인된 경우에만 조정한다.

[GitHub의 AWS OIDC 안내](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)를 따른다. AWS 리소스 생성·태그 push·워크플로 실행은 요청 범위에 있을 때만 수행한다.

## 완료

설정된 lint·typecheck·테스트·build와 로컬 Docker의 HTTP 응답을 확인한다. 이미 통과한 결과는 변경이 없으면 재사용한다. 실패 수정은 `/validate` 범위로 진행한다.

README에는 실제 로컬 셋업·DB·환경변수·테스트·릴리스 절차를 기록한다. 필요한 AWS/OAuth/GitHub 설정과 미실행 검증을 밝힌다. 로컬 검증만으로 실제 ECR 배포나 OAuth 성공을 주장하지 않는다.
