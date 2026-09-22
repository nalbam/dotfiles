# Vitest와 DynamoDB Local 검증

## 환경

Vitest와 실제 필요한 플러그인만 설치한다. DB·도메인 테스트는 node 환경을 기본으로 하고 UI 테스트를 추가할 때 jsdom·Testing Library·Mantine 테스트 설정을 추가한다.

`test` 스크립트는 `vitest run`, watch는 별도 스크립트로 둔다. 개발 DB와 분리된 테스트 인스턴스를 사용한다.

endpoint·리전·테이블·더미 자격증명은 하나의 테스트 설정 모듈에서 정의해 Vitest 설정과 globalSetup이 함께 import한다. 실제 비밀은 이 모듈에 넣지 않는다.

```ts
// test/dynamodb-config.ts
export const testDatabase = {
  endpoint: "http://localhost:8084",
  region: "ap-northeast-2",
  table: "<project>-test",
  credentials: { accessKeyId: "local", secretAccessKey: "local" },
};
```

Vitest `test.env`에 해당 endpoint·리전·테이블을 연결해 앱의 테스트 워커에 전달한다. `test.env`는 globalSetup에 적용되지 않으므로 globalSetup은 같은 모듈을 직접 사용한다. 셸에서 상속한 환경변수까지 없다고 가정하지 않는다. [Vitest env](https://vitest.dev/config/env)를 참고한다.

## 초기화

- globalSetup에서 SDK로 지정된 테스트 테이블만 준비한다. 초기화 전에 endpoint가 테스트 loopback 주소이고 테이블명이 테스트 대상인지 확인한다.
- 삭제 후 없어질 때까지, 생성 후 준비될 때까지 기다린다. 예상한 not-found 외 오류나 생성 충돌을 무조건 삼키지 않는다.
- 앱·초기화 코드가 같은 리전·자격증명을 쓰게 한다. CI가 `-sharedDb` 없이 실행돼도 같은 DB를 봐야 한다.
- 같은 테이블을 초기화하는 테스트 실행은 병렬로 겹치지 않게 한다. 병렬 실행이 필요하면 실행별 테이블을 분리한다.
- 테스트 후 개발 테이블·다른 프로젝트의 데이터가 보존되는지 확인한다.

## 계약 테스트

실제 DynamoDB Local에 요청해 아래 동작을 검증한다. 어댑터 전체를 mock으로 대체하지 않는다.

| 대상 | 확인 |
|------|------|
| 접근 패턴 | [dynamodb.md](dynamodb.md)의 모든 조회와 페이지네이션 |
| 조건·정렬 | 지원 연산·필터·select·limit, 미지원 조건의 명확한 오류 |
| email 유니크 | 같은 정규화 email의 동시 생성 중 하나만 성공 |
| email 변경 | 새 키 조회·옛 마커 해제·충돌 시 원래 데이터 보존 |
| session token 변경 | 새 token 조회·옛 token 무효화의 원자성 |
| TTL | 저장 숫자·원본 ISO 복원·만료 세션 거부·user에 TTL 없음 |
| bulk·count | 여러 페이지·부분 실패·결과 수 |
| domain/application | DB 없이 관찰 가능한 유스케이스 동작 |

GSI의 운영 지연은 로컬 성공만으로 검증되지 않는다. 쓰기 직후 읽기의 설계를 별도로 확인한다.

UI 테스트가 필요하면 MantineProvider와 해당 버전의 브라우저 API mock을 사용한다. 도구가 지원하지 않는 async Server Component는 E2E로 검증한다.

`docker compose up -d dynamodb-test` 후 준비 상태를 확인하고 `pnpm test`를 실행한다. 외부 계정이 필요한 OAuth E2E는 실행 여부를 따로 기록한다.
