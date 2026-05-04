# Coding Style

CLAUDE.md `## Core Principles` 와 `## Surgical Changes` 의 *유일한 상세 source*.

각 원칙의 한 줄 요약은 CLAUDE.md, *근거·예시·체크리스트*는 이곳. 보안 상세는 `rules/security.md`, 근본 원인 분석은 `rules/problem-solving.md` 가 source.

## Core Principles (상세)

- **Solve the right problem** — 복잡도·스코프 크리프 회피. 요청 문제부터 정확히 해결, 부수 개선은 별도 PR 로 분리.
- **Handle errors explicitly** — 구체 예외 타입을 잡고, broad catch 지양. 실패 시 의미 있는 메시지와 함께 fast-fail.
- **Address root causes** — 증상이 아닌 근본 원인 수정 (`rules/problem-solving.md`).
- **Keep code readable** — 명확한 네이밍, 논리적 구조, 깊은 중첩(>4단계) 회피, 작은 함수.
- **Design for security** — 입력 검증·최소 권한·시크릿 보호 (`rules/security.md`).

## Surgical Changes / 외과적 변경

**핵심 규칙: 변경된 모든 라인은 사용자 요청에 직접 추적 가능해야 한다.**

기존 코드 수정 시 가장 흔한 LLM 실수는 *요청 범위를 넘어선 인접 개선*이다. diff 를 부풀리고, 리뷰를 어렵게 만들며, 의도치 않은 회귀를 유발한다.

### MUST NOT (절대 금지)

- 인접한 코드를 같이 "개선" 하지 않는다 (요청 외 라인은 손대지 않는다)
- 고장 나지 않은 것을 리팩토링하지 않는다
- 기존 스타일을 본인 선호로 바꾸지 않는다 (따옴표 통일, 들여쓰기, 줄바꿈, import 순서 변경 금지)
- 요청에 없는 타입 힌트·docstring·주석을 새로 추가하지 않는다
- 사용자가 묻지 않은 새 추상화·플래그·설정·옵션을 끼워 넣지 않는다
- 무관한 dead code 를 함께 삭제하지 않는다 (발견했다면 *언급만* 하고 별도 작업으로 분리 제안)
- 같은 PR/커밋에 두 가지 이상의 목적을 섞지 않는다

### MUST (반드시 한다)

- 기존 스타일·네이밍·포맷을 그대로 매치한다 (본인이라면 다르게 했을지라도)
- 본인 변경으로 *발생한* unused import/var/function 만 정리한다
- 요청과 무관한 dead code/이슈/개선 기회는 별도 PR/커밋/이슈 제안으로 분리한다
- 동작 보존 리팩토링이라면 "동작은 동일함" 을 명시한다

### 검증 체크리스트 (PR/커밋 전)

- [ ] 변경된 모든 라인이 사용자 요청에 직접 추적되는가
- [ ] 따옴표 스타일·공백·들여쓰기·import 순서를 임의로 바꾸지 않았는가
- [ ] 요청에 없는 타입 힌트·docstring·주석을 추가하지 않았는가
- [ ] 무관한 리팩토링·이름 변경이 섞이지 않았는가
- [ ] 한 PR 에 한 목적만 담겼는가
- [ ] 발견한 무관 이슈는 별도 항목으로 분리했는가

### 예시

**요청: "이메일이 비었을 때 크래시 나는 버그 수정"**

- ❌ Bad: 이메일 검증 로직 강화 + username 검증 추가 + docstring 보강 + 따옴표 통일
- ✅ Good: 빈 이메일 처리 분기만 수정. 나머지 로직·스타일은 그대로 둔다.

**요청: "upload 함수에 로깅 추가"**

- ❌ Bad: 로깅 추가하면서 타입 힌트, docstring, 반환값 패턴, 따옴표 스타일까지 변경
- ✅ Good: 기존 시그니처·스타일 유지. `logger` 호출만 삽입.

**요청: "이 함수에 캐시 추가"**

- ❌ Bad: 캐시 추가 + 함수 분리 + 변수명 개선 + 에러 처리 강화
- ✅ Good: 캐시 데코레이터/로직만 추가. 나머지는 별도 PR 로 제안.

## Immutability

새 객체를 만들고 mutate 하지 않는다.

```javascript
// WRONG: Mutation
function updateUser(user, name) {
  user.name = name  // MUTATION!
  return user
}

// CORRECT: Immutability
function updateUser(user, name) {
  return { ...user, name }
}
```

## File / Function Organization

수치는 *권장 가이드*이며 절대 기준이 아니다. 프로젝트 관례 우선.

- 함수: 50줄 이내 권장. 복잡해지면 헬퍼 추출.
- 파일: 200~400줄 권장, 800줄 근접 시 리팩토링 고려.
- High cohesion, low coupling.
- Single Responsibility — 한 함수 한 책임.
- 파일은 feature/domain 기준으로 묶기, type 기준 지양.

## Error Handling

- 구체 예외 타입을 잡는다. broad `catch (e)` 지양.
- 로그에 맥락 포함, 민감 정보 제외.
- 복구 가능한 에러만 삼키고, 나머지는 상위로 전파.

```typescript
try {
  return await riskyOperation()
} catch (error) {
  logger.error('Operation failed', { context, error })
  throw new OperationError('Detailed user-friendly message', { cause: error })
}
```

## Input Validation

시스템 경계(사용자 입력, 외부 API)에서만 검증한다. 내부 호출은 타입 시스템과 불변식에 의존.

```typescript
const schema = z.object({
  email: z.string().email(),
  age: z.number().int().min(0).max(150)
})
const validated = schema.parse(input)
```

## Documentation

- 자기 설명적 코드 — 명확한 이름, 논리적 구조
- 주석은 비자명한 *why* 만. *what* 은 코드가 말한다.
- README.md 는 설치·사용·아키텍처 개요를 최신으로 유지
- API 는 요청/응답 예시와 에러 케이스 문서화
- 동작 변경·기능 추가 시 문서 동시 갱신
- 오래된 주석은 수정이 아닌 삭제 (틀린 주석은 없는 주석보다 해롭다)

### 현재 상태만 기록한다

**문서와 주석은 *지금 코드가 어떻게 동작하는지* 만 정확하게 기록한다.** 과거 상태·시행착오·번복 이력은 남기지 않는다.

- ❌ "이전엔 X 였는데 Y 로 변경됨", "원래 A 방식이었으나 B 로 교체"
- ❌ "TODO: 예전엔 ~ 했음", "// 과거 호환을 위해 남겨둠" (실제 호환이 필요하지 않다면)
- ❌ "처음엔 X 로 시도했지만 실패해서 Y 로 변경" (PR/커밋 메시지로 충분)
- ❌ AI 에이전트가 거친 추측·수정·롤백 흔적을 문서에 누적
- ✅ 현재 동작·계약·제약을 그대로 기술
- ✅ 변경 이력은 `git log`·PR 본문·CHANGELOG 가 source

이유: 문서가 과거 상태를 누적하면 *현재 진실*을 흐린다. 독자는 "지금 어떻게 동작하는가" 를 알고 싶지 "어떻게 변해왔는가" 가 궁금한 게 아니다 (필요하면 git history 로 간다).

## Code Quality Checklist (작업 완료 전)

- [ ] 변경된 모든 라인이 사용자 요청에 직접 추적되는가
- [ ] 함수·파일 크기가 합리적인가 (프로젝트 관례 기준)
- [ ] 적절한 에러 처리가 있는가 (broad catch 없음)
- [ ] 하드코딩된 시크릿·값이 없는가
- [ ] Mutation 이 없는가 (불변 패턴)
- [ ] 기존 유틸리티를 재사용했는가 (중복 구현 없는가)
- [ ] 무관한 리팩토링·스타일 변경이 섞이지 않았는가

## Anti-Patterns

이 주제 안티패턴은 `rules/anti-patterns.md#code-quality`, `rules/anti-patterns.md#surgical--외과적-변경-위반` 이 source.
