# Common Patterns

CLAUDE.md `## Project Conventions` 의 보강 자료.

**중요**: 이 파일의 패턴·코드 스니펫은 *예시*다. 실제 프로젝트에 동일·유사 패턴이 이미 있으면 그것을 따른다 — 이 파일을 *덮어쓰는 표준* 으로 적용하지 말 것. 언어·프레임워크가 다른 프로젝트에서는 *개념*만 가져오고 표현은 해당 환경에 맞춘다.

## API Response Shape

성공·실패를 명확히 구분하는 packing 이 일반적이다. 구체 형태는 프로젝트마다 다름.

```typescript
type ApiResponse<T> =
  | { ok: true; data: T; meta?: { total: number; page: number } }
  | { ok: false; error: { code: string; message: string } }
```

## Repository Pattern

데이터 접근은 인터페이스 뒤에 둔다 — 테스트·구현 교체가 용이.

```typescript
interface Repository<T> {
  findAll(filters?: Filters): Promise<T[]>
  findById(id: string): Promise<T | null>
  create(data: CreateDto): Promise<T>
  update(id: string, data: UpdateDto): Promise<T>
  delete(id: string): Promise<void>
}
```

## Skeleton Projects

새 기능 구현 시 검증된 skeleton 에서 시작한다.

1. 도메인에 적합한 후보 검색 (Context7·공식 예제)
2. 보안·확장성·관련성 평가 — 병렬 subagent 활용 가능 (`rules/claude-code.md#subagents--서브에이전트`)
3. 최적안을 기반으로 클론
4. 검증된 구조 안에서 반복
