# 스캐폴딩과 Mantine

## 환경과 생성

프로젝트명·대상 경로는 요청과 현재 디렉터리에서 확인한다. 버전이 기본값과 다르다는 이유만으로 중단하거나 전역 도구를 교체하지 않는다. 호환성을 확인하고 필요한 조정만 한다. AWS 식별자·OAuth 값이 없어도 로컬 구현은 진행한다.

```bash
pnpm create next-app@latest <name> \
  --typescript --no-tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-pnpm --disable-git --skip-install --yes
```

실행 전에 현재 CLI 플래그를 확인한다. `--skip-install`로 스캐폴딩과 의존성 설치를 분리해 빌드 스크립트 정책을 먼저 설정한다.

- `packageManager`와 Node.js `engines`를 실제 선택 버전에 맞춘다.
- pnpm의 설치 스크립트 승인은 해당 버전의 [공식 설정](https://pnpm.io/settings)을 따른다. `sharp`·`unrs-resolver` 등 실제 의존성의 스크립트를 검토해 필요한 것만 허용한다. 전체 승인이나 구식 설정과의 무조건 병합을 하지 않는다.
- 승인 설정 파일·lockfile은 CI와 Docker에도 포함한다.
- TypeScript는 Next.js·린터의 peer 범위 안에서 선택한다. 특정 과거 버전의 실패를 영구적인 상한으로 만들지 않는다.
- `strict: true`, Next.js `output: "standalone"`, 실제 린터 CLI를 실행하는 `lint` 스크립트를 확인한다.

스캐폴더의 프로젝트 지침·설정·layout·favicon은 유지하고 데모 화면·에셋·불필요한 스타일만 제거한다. 삭제한 파일의 import와 참조도 함께 고친다. Docker가 `public/`을 COPY한다면 빈 디렉터리에도 `.gitkeep`을 둔다.

## Mantine

[설치 버전의 Next.js 통합 안내](https://mantine.dev/guides/next/)에 맞춰 `@mantine/core`·`@mantine/hooks`와 필요한 PostCSS 설정을 추가한다.

- `styles.layer.css` 한 판본만 import한다. 스캐폴더의 body 색상·다크 모드 CSS가 Mantine 컬러 스킴을 덮지 않게 한다.
- `ColorSchemeScript`와 `MantineProvider`의 `defaultColorScheme`을 맞추고 `mantineHtmlProps`를 적용한다.
- 스캐폴더의 폰트 변수를 Mantine 테마에 연결한다.
- 테마 토글은 서버와 클라이언트의 최초 마크업을 같게 유지한다. 두 아이콘을 렌더하고 컬러 스킴 CSS로 표시하거나 설치 버전의 공식 hydration 패턴을 따른다.
- 화면은 프로젝트명·테마 토글·로그인 버튼으로 구성한다. 필요한 클라이언트 경계만 추가한다.

토글·저장된 스킴의 새로고침·OS와 반대 스킴에서 배경색과 hydration 경고를 확인한다. 삭제한 샘플 파일의 404가 없어야 한다.

## 레이어

```text
src/
  domain/          # 엔티티·리포지토리 인터페이스
  application/     # domain을 사용하는 유스케이스
  infrastructure/  # DynamoDB·Better Auth 구현
  lib/             # 프레임워크 연결 코드
  app/             # 라우트·UI·의존성 조립
```

`domain`은 다른 레이어·프레임워크에 의존하지 않는다. `application`은 `domain`만 의존하고, `infrastructure`는 domain 인터페이스를 구현한다. `app`에서 구현을 조립한다. `lib`를 통한 우회 의존도 막는다.

기존 ESLint 설정을 유지하며 경계를 검사한다. `import/no-restricted-paths`를 쓰면 `target`은 import하는 쪽, `from`은 금지된 의존 대상이다.

| target | 금지 from |
|--------|-----------|
| `src/domain` | application, infrastructure, app, lib |
| `src/application` | infrastructure, app, lib |
| `src/infrastructure` | application, app |

설치된 ESLint preset의 플러그인·resolver 등록을 확인해 중복 등록하지 않는다. 금지 import를 넣은 임시 파일로 규칙이 실제 실패하는지 확인한 뒤 그 파일을 제거한다.
