# Coding Style

CLAUDE.md의 핵심 원칙을 상세히 설명한다. 원칙 자체는 CLAUDE.md에 있고, 이 파일은 근거·예시·체크리스트를 제공한다.

## Core Principles (상세)

- **Solve the right problem** — 복잡도·스코프 크리프를 피하라. 요청받은 문제부터 정확히 해결하고, 부수적 개선은 별도 PR로 분리.
- **Favor standard solutions** — 잘 알려진 라이브러리·패턴을 먼저 고려. 커스텀 코드는 표준 해법이 맞지 않을 때만.
- **Keep code readable** — 명확한 네이밍, 논리적 구조, 깊은 중첩(>4단계) 회피.
- **Handle errors explicitly** — 구체적 예외를 잡아라. broad catch 금지. 실패 시 의미 있는 메시지와 함께 fast-fail.
- **Design for security** — 입력 검증, 최소 권한, 시크릿 노출 금지.
- **Keep dependencies shallow** — 강결합 최소화. 경계 명확화.
- **Address root causes** — 증상이 아닌 근본 원인을 수정. (`rules/problem-solving.md` 참조)

## Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate:

```javascript
// WRONG: Mutation
function updateUser(user, name) {
  user.name = name  // MUTATION!
  return user
}

// CORRECT: Immutability
function updateUser(user, name) {
  return {
    ...user,
    name
  }
}
```

## File Organization

MANY SMALL FILES > FEW LARGE FILES:

- 200~400줄 권장, 800줄 절대 상한
- 500줄에 근접하면 리팩토링 고려
- High cohesion, low coupling
- 유틸리티는 큰 컴포넌트에서 분리
- 파일은 feature/domain 기준으로 묶기, type 기준 지양

## Function Organization

- 함수는 50줄 미만 유지
- 로직이 복잡해지면 헬퍼 함수로 추출
- Single Responsibility Principle — 하나의 함수, 하나의 책임

## Error Handling

ALWAYS handle errors comprehensively:

```typescript
try {
  const result = await riskyOperation()
  return result
} catch (error) {
  console.error('Operation failed:', error)
  throw new Error('Detailed user-friendly message')
}
```

- 구체적 예외 타입을 잡는다 (broad `catch (e)` 지양)
- 로그에는 맥락 포함, 민감 정보 제외
- 복구 가능한 에러만 삼키고, 나머지는 상위로 전파

## Input Validation

ALWAYS validate user input:

```typescript
import { z } from 'zod'

const schema = z.object({
  email: z.string().email(),
  age: z.number().int().min(0).max(150)
})

const validated = schema.parse(input)
```

- 시스템 경계(사용자 입력, 외부 API)에서만 검증
- 내부 함수 호출은 타입 시스템과 불변식에 의존

## Documentation

- 자기 설명적 코드 작성 — 명확한 이름, 논리적 구조
- 주석은 비자명한 로직에만 (what이 아닌 why 설명)
- README.md는 설치·사용·아키텍처 개요를 최신으로 유지
- API는 요청/응답 예시와 에러 케이스 문서화
- 동작 변경 또는 기능 추가 시 문서 동시 갱신
- 오래된 주석은 수정이 아닌 삭제 (틀린 주석은 없는 주석보다 해롭다)

## Code Quality Checklist

Before marking work complete:

- [ ] 읽기 쉽고 이름이 명확한가
- [ ] 함수가 50줄 미만인가
- [ ] 파일이 800줄 미만인가
- [ ] 중첩이 4단계 이하인가
- [ ] 적절한 에러 처리가 있는가
- [ ] 하드코딩된 값이 없는가
- [ ] 불변 패턴을 사용했는가 (mutation 없는가)
- [ ] 기존 유틸리티를 재사용했는가 (중복 구현 없는가)
