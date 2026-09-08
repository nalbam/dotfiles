---
name: code-audit
description: Deep read-only audit of an entire codebase — severity-ranked report, no code changes. 저장소 전체 심층 감사(수정 없음) — 변경분·PR 리뷰는 /code-review, 검사 실행·수정은 /validate.
allowed-tools: Read, Bash, Grep, Glob, Agent
---

# Code Audit

저장소 전체 구현을 읽기 전용으로 감사한다. 발견 사항은 보고하고 코드·외부 상태를 바꾸지 않는다. 변경분 리뷰는 `code-review`, 검사 실행·수정은 `validate`, 문서 정합은 `docs-sync`의 범위다.

## Exclude Patterns

다음은 탐색 시 기본 제외 대상이다. 저장소가 직접 관리하거나 감사 대상에 필요한 파일은 이름만으로 제외하지 않는다.

| Category | Directories / files |
|----------|---------------------|
| Dependencies | `node_modules/`, `vendor/`, `bower_components/`, `.pnp/` |
| Build outputs | `dist/`, `build/`, `out/`, `target/`, `.next/`, `.nuxt/`, `.vercel/` |
| Cache | `.cache/`, `.tmp/`, `tmp/`, `__pycache__/`, `.turbo/`, `.parcel-cache/` |
| Virtual envs | `.venv/`, `venv/`, `.env/`, `env/` |
| VCS / IDE | `.git/`, `.svn/`, `.hg/`, `.idea/`, `.vscode/`, `.vs/` |
| Test outputs | `coverage/`, `.nyc_output/`, `test-results/` |
| Generated / OS | `*.min.js`, `*.bundle.js`, `.DS_Store`, `Thumbs.db` |

lockfile·배포 설정은 의존성·운영 위험을 확인할 때 읽는다. 시크릿 파일의 값을 출력하지 않는다.

## 조사

1. README·CLAUDE.md·manifest·CI와 주요 설정으로 목적·구조·진입점·운영 제약을 파악한다.
2. 다음 네 축으로 구현·호출·데이터 흐름을 추적한다. 실제 위임 도구와 권한이 있으면 독립 영역을 나누고, 없으면 직접 수행한다. 에이전트 수나 역할명을 고정하지 않는다.

| 축 | 확인할 내용 |
|----|-------------|
| Security | 입력·권한·주입·시크릿·의존성 위험과 source-to-sink 흐름 |
| Architecture | 모듈 책임·의존 방향·데이터/오류 전파·공유 상태·API 계약 |
| Code Quality | 실제 결함으로 이어지는 중복·복잡도·타입·자원 처리 |
| Testing & Reliability | 중요 경로·실패 처리·mock 정확성·경쟁 상태·CI 누락 |

3. 위임 시 범위·제외 패턴·프로젝트 제약·산출물 형식을 전달한다. 메인은 근거를 확인하고 같은 원인의 중복 findings를 합친다.
4. 의심 항목의 발생 조건·실제 영향·가역성을 확인한다. 파일 줄 수·타입 사용·취향 차이만으로 문제를 만들지 않는다.

## 보고

심각도 기준은 `skills/code-review/SKILL.md#severity`를 따른다. 각 finding에 파일·줄, 문제, 발생 조건, 근거, 영향, 권장 조치를 담는다.

실제 위험을 먼저 제시하고 공통 근본 원인은 필요한 경우에만 묶는다. 직접 확인한 범위·제외한 영역·실행하지 않은 검사를 밝힌다. 읽지 않은 영역까지 감사 완료로 표현하거나 측정하지 않은 커버리지·성능 수치를 쓰지 않는다.
