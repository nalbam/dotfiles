# Anti-Patterns to Avoid

## Code Quality

- 전체 맥락을 읽지 않고 코드 수정
- 기존 유사 코드·유틸리티 탐색 없이 새로 구현
- 실패·경고·엣지 케이스 무시
- Premature optimization / abstraction
- Broad exception handler (`catch (e)` 같은 통짜 캐치)
- Mutation을 통한 상태 변경 (불변 패턴 위반)
- 깊은 중첩 (>4단계 들여쓰기)
- 하드코딩된 시크릿·값
- 사용되지 않는 변수·import 방치

## Problem Solving

- 근본 원인 파악 없이 빠른 수정
- 증상 치료(try-catch 도배)로 원인 회피
- 첫 번째 그럴듯한 설명에서 멈춤
- 수정 후 검증 생략
- "일시적 이슈"로 단정하고 종결

## Testing

- 통합 테스트를 전부 mock으로 대체 (프로덕션 동작과 괴리)
- 버그 수정 시 회귀 테스트 누락
- 테스트 간 상태 공유로 순서 의존성 발생
- 실패하는 테스트를 수정 대신 skip / `.only` 처리

## Git & Deployment

- 사용자 허가 없이 `commit` 또는 `push`
- 훅 우회 (`--no-verify`, `--no-gpg-sign`)
- 공유 브랜치에 force push
- 시크릿·바이너리·생성 파일 커밋
- 덮어쓰기 전 백업·검증 생략
- `rm -rf`, `git reset --hard` 등 파괴적 명령을 확인 없이 실행

## Communication & Process

- 사용자 요구 없이 자동 커밋/리팩토링
- 계획(Plan Mode) 없이 대규모 변경 시작
- 불확실한 내용을 질문 없이 추측으로 작성
- 긴 요약·장황한 설명 남발 (사용자는 diff를 볼 수 있다)
- 없는 Skill·Agent를 추측해서 호출
- 훈련 데이터를 맹신하고 최신 문서(Context7 등) 확인 생략

## Claude Code 고유 안티패턴

- `EnterPlanMode` 없이 다중 파일 변경 시작
- 독립적 도구 호출을 순차 실행 (병렬 가능한데 직렬)
- 대규모 탐색을 subagent 없이 메인 컨텍스트에서 수행
- `TaskCreate` 없이 3단계 이상 복잡 작업 추적
- Context7에서 조회해야 할 라이브러리 문서를 훈련 데이터로 답변
