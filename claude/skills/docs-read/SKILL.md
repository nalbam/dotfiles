---
name: docs-read
description: Read project documentation for explicit onboarding or a project-overview request. Read-only. 프로젝트 온보딩·전체 구조 파악을 명시적으로 요청할 때 사용. 일반 구현의 관련 문서 확인이나 문서 수정은 대상 아님.
allowed-tools: Read, Bash, Grep, Glob
---

# Documentation Read

명시적인 온보딩·프로젝트 개요 요청에서 문서를 읽고 목적·구조·관례를 설명한다. 읽기 전용이며 문서·코드를 수정하지 않는다. 일반 구현 중 관련 문서 확인에는 이 스킬이 필요하지 않다.

## Workflow

1. 루트 `README.md`·`CLAUDE.md`·`AGENTS.md`·`CONTRIBUTING.md`와 문서 인덱스를 확인한다.
2. 질문과 연결된 문서를 선택한다. 인덱스가 없으면 파일명·헤딩을 훑고 관련 문서를 읽는다. `docs/` 전체를 기계적으로 정독하지 않는다.
3. 문서가 가리키는 진입점의 존재와 역할을 확인한다. 전체 코드 감사는 `code-audit`, 코드↔문서 검증·수정은 `docs-sync`로 구분한다.
4. 목적·구조·핵심 관례·비자명한 제약과 다음에 볼 파일을 간결하게 설명한다. 문서에 없는 내용은 추측으로 채우지 않고 모순·공백을 구분한다.

탐색 제외 기준은 `skills/code-audit/SKILL.md#exclude-patterns`를 따른다. 문서 전문을 복사하거나 결과용 새 문서를 만들지 않는다.
