# DynamoDB 접근 패턴과 로컬 환경

## 키 설계

Better Auth의 설치 버전에서 사용하는 모델·쿼리를 확인한다. 기본 단일 테이블 설계는 다음과 같다.

| 모델 | PK = SK | GSI1PK | GSI1SK | GSI2PK | GSI2SK |
|------|---------|--------|--------|--------|--------|
| user | `USER#<id>` | `EMAIL#<email>` | `USER#<id>` | — | — |
| email 마커 | `EMAIL#<email>` | — | — | — | — |
| session | `SESSION#<token>` | `SESSION#<id>` | `SESSION#<id>` | `USER#<userId>` | `SESSION#<createdAt>` |
| account | `ACCOUNT#<id>` | `PROVIDER#<providerId>#<accountId>` | `ACCOUNT#<id>` | `USER#<userId>` | `ACCOUNT#<providerId>` |
| verification | `VERIFICATION#<id>` | `IDENT#<identifier>` | `VERIFICATION#<createdAt>` | — | — |

| 접근 | 연산 |
|------|------|
| id 단건 조회 | GetItem; session만 GSI1 |
| email → user | GSI1 |
| token → session | `ConsistentRead: true`인 GetItem |
| userId → session 목록 | GSI2 |
| providerId + accountId → account | GSI1 |
| userId → account 목록 | GSI2 |
| identifier → 최신 verification | GSI1 역순 |

세션 token 조회는 로그인 직후의 읽기와 매 요청 인증 경로이므로 GSI에 두지 않는다. GSI는 강일관 읽기를 지원하지 않는다. 다른 접근 패턴도 쓰기 직후 읽기를 요구하는지 확인하고, 필요하면 기본 키·트랜잭션 설계를 보완한다. 로컬 테스트 성공으로 운영 GSI 일관성을 보장하지 않는다.

email 마커는 유니크 제약이다. user와 마커를 조건부 트랜잭션으로 함께 생성하며 email 변경·삭제도 함께 갱신한다. email 정규화 정책을 조회·생성·변경에서 일치시킨다.

## 만료

session·verification만 TTL을 가진다. 기존 명명 관례에 맞춰 TTL 속성 `expiresAt`은 epoch seconds 숫자로, Better Auth의 원본 ISO 값은 `expiresAtIso`로 저장한다. 읽을 때 내부 키를 제거하고 원래 `expiresAt`을 복원한 다음 필터·정렬한다.

TTL 정리는 즉시 일어나지 않으므로 인증 시 만료 여부도 검사한다. TTL 삭제에 보안상 만료 처리를 맡기지 않는다.

## 로컬 개발과 테스트

이 스택은 기존 공용 `localdev` 환경이 있으면 dev `:8083`, test `:8084`를 재사용한다. 먼저 컨테이너·포트·설정을 확인한다. 다른 저장소의 서비스를 재생성하거나 이름 충돌을 덮어쓰지 않는다.

신규 환경 예시이며 이미지 버전은 사용 가능한 공식 버전을 확인해 고정한다.

```yaml
name: localdev
services:
  dynamodb:
    image: amazon/dynamodb-local:<version>
    user: root
    command: ["-jar", "DynamoDBLocal.jar", "-sharedDb", "-dbPath", "./data"]
    working_dir: /home/dynamodblocal
    volumes: ["dynamodb-data:/home/dynamodblocal/data"]
    ports: ["127.0.0.1:8083:8000"]
  dynamodb-test:
    image: amazon/dynamodb-local:<version>
    command: ["-jar", "DynamoDBLocal.jar", "-sharedDb", "-inMemory"]
    ports: ["127.0.0.1:8084:8000"]
volumes:
  dynamodb-data:
```

- dev의 `user: root`는 named volume 쓰기 권한을 위한 로컬 설정이다. 호스트 경로·Docker 소켓을 마운트하지 않는다. 비루트로 바꾸면 해당 UID의 볼륨 쓰기를 확인한다.
- 컨테이너가 Up인지뿐 아니라 실제 API 응답과 로그로 준비 상태를 확인한다.
- 앱과 테이블 생성 도구에 동일한 리전·로컬 더미 자격증명을 준다. `-sharedDb`가 없는 환경은 자격증명·리전별 DB가 다르다.
- 테이블은 프로젝트별 고유 이름을 사용한다. 테스트는 별도 인스턴스의 프로젝트별 `-test` 테이블만 초기화한다.
- 공용 환경에서 `docker compose down -v`, `--remove-orphans`, 전체 테이블 삭제를 하지 않는다.
- PK/SK와 GSI 2개·TTL 설정은 SDK 기반 생성 코드로 재사용한다. 로컬 실행에는 loopback endpoint와 더미 자격증명을 명시하고, AWS의 실제 생성은 별도 권한이 있을 때만 수행한다.

[공식 DynamoDB Local 안내](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html)와 [읽기 일관성](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html)을 참고한다.
