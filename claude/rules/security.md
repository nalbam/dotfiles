# Security

CLAUDE.md `## Security` 의 *유일한 상세 source*.

**적용 범위**: 모든 변경에 일괄 적용이 아닌, *보안 영향이 있는 영역* 에 적용한다. 인증·권한·암호화·외부 입력·시크릿 관리·민감 데이터 처리 영역의 변경에서 체크리스트를 사용한다.

## Mandatory Checks (보안 영향 있는 변경 시)

- [ ] 하드코딩된 시크릿(API 키·패스워드·토큰) 없음
- [ ] 외부 입력 검증 (`rules/coding-style.md#input-validation`)
- [ ] SQL injection 방지 — parameterized queries / ORM
- [ ] XSS 방지 — 출력 시 sanitize, dangerous innerHTML 회피
- [ ] CSRF 방지 — 변형(mutation) 작업에 토큰
- [ ] AuthN / AuthZ 검증 — *서버 측에서* 매 요청 확인
- [ ] 엔드포인트 rate limiting / abuse 방지
- [ ] 에러 메시지에 민감 정보 누출 없음
- [ ] 로그·텔레메트리에 PII·시크릿 없음

## Secret Management

```typescript
// NEVER: Hardcoded secrets
const apiKey = "sk-proj-xxxxx"

// ALWAYS: Environment variables, fail-fast on missing
const apiKey = process.env.OPENAI_API_KEY
if (!apiKey) {
  throw new Error('OPENAI_API_KEY not configured')
}
```

원칙:
- 시크릿은 환경변수 또는 시크릿 매니저
- `.env` 는 `.gitignore` 에, `.env.example` 만 커밋
- 노출된 시크릿은 즉시 *rotate*, 코드 수정만으로는 부족

## 민감 작업 / 영향 범위 확인

다음 영역의 변경은 실행 전 영향 범위를 짧게 보고하고 사용자 확인을 받는다:

- 인증·세션·토큰 관리
- 권한 체크(authorization) 로직
- 암호화·해싱·서명
- PII / 결제 정보 처리
- 외부 시스템 인증 정보

## 보안 이슈 발견 시 대응

1. **즉시 멈춘다** — 진행 중 작업 중단
2. **CRITICAL 우선** — 다른 작업보다 먼저 수정
3. **노출된 시크릿은 rotate** — 코드 수정만으로 부족
4. **유사 패턴 스캔** — 같은 취약점이 다른 곳에도 있는지 확인

## Anti-Patterns

이 주제 안티패턴은 `rules/anti-patterns.md` 의 Code Quality / Git & Deployment 섹션 참조.
