# Better Auth와 Google OAuth

설치 버전의 [Next.js 통합](https://www.better-auth.com/docs/integrations/next)과 어댑터 API를 확인한다. 서버 인증 코드는 `src/infrastructure/auth/`에 둔다.

## 어댑터 계약

`createAdapterFactory` 기반으로 실제 호출되는 CRUD·조회·count 계약을 구현한다. SDK의 DocumentClient를 사용하며 다음을 확인한다.

- 문자열 ID, 날짜 직렬화, JSON·boolean 지원은 저장 형식에 맞춰 선언한다. field mapping·select·반환값은 factory의 계약을 따른다.
- `where` 전체와 연산자·정렬·limit을 처리한다. 인덱스로 처리할 수 없는 조건을 무시하거나 Scan으로 숨기지 않는다. 미지원 연산과 0이 아닌 offset은 명시적으로 거부하고 실제 인증 흐름이 이를 요구하는지 검사한다.
- Query의 페이지 끝을 처리하고 필터 적용 전 limit 때문에 누락되지 않게 한다. `count`, bulk update/delete도 여러 페이지를 포함한다.
- user 생성은 user + email 마커의 조건부 트랜잭션이다. email 변경은 옛 마커 삭제·새 마커 조건부 생성·user 갱신을 묶는다. 삭제 시 마커도 지운다.
- session token 변경은 기본 키가 바뀌므로 delete + put 트랜잭션이다. 다른 파생 인덱스 키도 갱신한다.
- 만료 값은 [dynamodb.md](dynamodb.md)의 저장·복원 계약을 따른다. 인증에 사용하는 반환값에 내부 키나 다른 모델의 TTL 속성이 섞이지 않게 한다.
- bulk 쓰기의 크기 제한·부분 실패를 처리한다. 실패한 항목이 남았는데 성공으로 반환하지 않는다.

## 배선

- `src/app/api/auth/[...all]/route.ts`: 설치 버전의 `toNextJsHandler(auth)`로 GET/POST를 연결한다.
- `src/lib/auth-client.ts`: `better-auth/react`의 `createAuthClient()`.
- 서버 세션: 요청 headers를 전달해 `auth.api.getSession`을 호출한다.
- `nextCookies()`가 필요한 구성에서는 plugins의 마지막에 둔다.
- Mantine 로그인 버튼에서 Google sign-in/sign-out을 연결한다. 추가 로그인·대시보드 화면은 만들지 않는다.
- 보호할 경로가 없으면 proxy를 만들지 않는다. 인가는 보호된 라우트·서버 액션에서 확인하며 쿠키 존재 검사나 리다이렉트만으로 허용하지 않는다.

## 환경변수

```dotenv
BETTER_AUTH_SECRET=
BETTER_AUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
AWS_REGION=ap-northeast-2
DYNAMODB_TABLE_NAME=<project>
DYNAMODB_ENDPOINT=http://localhost:8083
```

`.env.example`에는 비밀이 아닌 기본값만 둔다. `.gitignore`의 `.env*` 뒤에 `!.env.example`을 추가한다. 확인을 위해 사용자 index를 stage하지 않는다.

`.env.local`을 만들 때 기존 값은 보존한다. 로컬 전용 `BETTER_AUTH_SECRET`은 난수로 생성해 파일에만 저장하고 출력하지 않는다. Google 값은 사용자가 설정한다.

| 환경 | 설정 |
|------|------|
| 로컬 DB | loopback endpoint + 더미 자격증명 |
| 운영 DB | endpoint override·더미 자격증명 제거, AWS 역할 사용 |
| 운영 OAuth | 실제 HTTPS origin과 일치하는 `BETTER_AUTH_URL`·Google redirect URI |

Google Console의 callback URI는 `<origin>/api/auth/callback/google`이다. 런타임 필수값 누락은 명확한 설정 오류로 처리하고 시크릿을 `NEXT_PUBLIC_*`·이미지·로그에 넣지 않는다.

## 검증

로그인 → 세션 유지 → 로그아웃과 어댑터의 원본 저장·반환 계약을 확인한다. OAuth 계정이 없으면 실제 로그인은 미검증으로 보고하고 어댑터·라우트 검증을 계속한다.
