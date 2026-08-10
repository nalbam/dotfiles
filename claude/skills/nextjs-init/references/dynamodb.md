# nextjs-init — 4단계: DynamoDB Single Table Design

`nextjs-init` 스킬의 단계별 상세다. Stack·Scope·Rules 등 전체 맥락과 단계 색인은 `SKILL.md` 가 source 다.

## 4. DynamoDB Single Table Design

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

**로컬 DynamoDB** (`compose.yaml`) — 개발과 테스트 모두 여기를 쓴다. 실제 AWS 테이블은 배포용이지 개발용이 아니다 (비용·데이터 오염·오프라인 불가).

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
