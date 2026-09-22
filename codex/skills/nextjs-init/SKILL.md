---
name: nextjs-init
description: Scaffold a new Next.js app with Mantine, Better Auth, DynamoDB, and Docker/ECR configuration. 지정 스택의 새 프로젝트 생성; 기존 앱 수정은 제외.
---

# Next.js Project Init

사용자가 다른 구성을 지정하지 않으면 아래 스택으로 새 프로젝트를 만든다. 일반적인 Next.js 수정 요청에는 적용하지 않는다.

| 영역 | 기본 선택 |
|------|-----------|
| Runtime | Node.js LTS, pnpm (`packageManager`에 버전 고정) |
| Framework | Next.js App Router, React, TypeScript strict |
| UI | Mantine·컬러 스킴, 프로젝트명·테마 토글·로그인 버튼만 있는 `/` |
| Auth / Data | Better Auth·Google OAuth, 커스텀 DynamoDB 단일 테이블 어댑터 |
| Structure | domain / application / infrastructure / app |
| Testing | Vitest, 개발 DB와 분리한 DynamoDB Local |
| Deploy | Docker standalone, GitHub Actions·OIDC를 통한 ECR 배포 설정 |

버전 번호를 이 문서에서 최신이라고 가정하지 않는다. 스캐폴더·설치 버전의 공식 문서와 peer dependencies를 확인해 호환되는 조합을 고정한다.

## 범위

- 프로젝트·인증·어댑터·테스트·Docker·CI·README·환경변수 예시를 만든다. 도메인 기능이나 추가 화면은 요청에 있을 때만 포함한다.
- 대상 디렉터리의 기존 파일을 덮어쓰지 않는다. 비어 있지 않으면 안전한 생성 경로를 확인한다.
- 스캐폴더는 git 초기화 없이 실행한다. commit·push·릴리스·AWS 리소스 생성은 별도 요청이 있을 때만 수행한다.
- 로컬 DB는 기존 공용 인스턴스를 확인하고 필요한 서비스·테이블만 준비한다. 다른 프로젝트의 데이터·컨테이너를 초기화하지 않는다.
- 발급받은 시크릿은 사용자가 안전한 경로로 설정한다. 로컬 개발용 난수는 gitignore된 파일에 생성할 수 있으며 출력하지 않는다.
- 필수 검사의 실제 실패는 해결한다. OAuth 계정·배포 권한 등 외부 조건이 없으면 해당 검증을 미실행으로 남기고 독립 작업을 계속한다.

## 참조

관련 작업 전에 해당 파일을 읽는다. 설치·데이터·인증의 의존 순서는 지키되 같은 검사를 단계마다 반복하지 않는다.

| 작업 | 참조 |
|------|------|
| 환경·스캐폴딩·Mantine·레이어 | [setup.md](references/setup.md) |
| 접근 패턴·키·로컬 DB | [dynamodb.md](references/dynamodb.md) |
| 어댑터 계약·OAuth·환경변수 | [auth.md](references/auth.md) |
| DB 격리·계약 테스트 | [testing.md](references/testing.md) |
| Docker·CI·ECR·최종 검증 | [deploy.md](references/deploy.md) |

프로젝트 경로·실제 스택·검증 결과·남은 계정 설정·생성한 로컬 자원을 보고한다. 로컬 검증과 실제 OAuth·AWS 배포 성공을 구분한다.
