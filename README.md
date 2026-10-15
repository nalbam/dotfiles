# dotfiles

macOS·Ubuntu 계열 Linux에서 개인 개발 환경을 설치하고 설정을 동기화한다. Windows PowerShell 설치기는 Git/Vim 링크와 기본 패키지만 구성한다.

- 처음 설치: [Quick Start](#quick-start)
- AI 지침·스킬 수정 및 배포: [AI Tools Sync](#ai-tools-sync)
- 설치 순서·실패 처리 확인: [Architecture](docs/ARCHITECTURE.md)
- Ubuntu 서버 준비 또는 Neovim 설치: [문서 인덱스](docs/README.md)

## Supported Platforms

| 환경 | 진입점 | 범위 |
|------|--------|------|
| macOS arm64 / x86_64 | `run.sh` | 패키지·셸·사용자 설정·AI 설정 |
| Ubuntu/WSL x86_64, Raspberry Pi aarch64 / armv7l | `run.sh` | APT·Homebrew 시도, 셸·사용자 설정·AI 설정 |
| Windows PowerShell | `run.ps1` | Git/Vim 심볼릭 링크, Git·7-Zip 설치, 선택적 `custom.ps1` 실행 |

Linux 경로는 APT를 사용한다. Raspberry Pi에서는 패키지와 Node.js가 소스 빌드되어 오래 걸릴 수 있다. 패키지 설치 범위는 각 플랫폼의 Brewfile과 명령 실행 결과로 확인한다.

## Quick Start

### macOS / Linux

로그인한 일반 사용자로 실행한다. Bash·curl·네트워크가 필요하며, 시스템 변경 단계에서 `sudo` 인증을 요청할 수 있다. AI 설정 동기화 단계에는 Python 3.11 이상이 필요하다.

```bash
curl -fsSL https://nalbam.github.io/dotfiles/run.sh | bash
```

이미 `~/.dotfiles`에 clone한 경우:

```bash
bash ~/.dotfiles/run.sh
```

전체 설치는 `~/.dotfiles`를 clone하거나 갱신하고, 사용자 설정을 복사하며, 기본 셸을 Zsh로 변경한다. 기존 checkout의 갱신이 실패하면 경고를 출력하고 현재 파일로 계속한다. AI 설정만 바꾸려면 [AI Tools Sync](#ai-tools-sync)를 사용한다.

완료 메시지와 함께 경고가 표시되면 해당 단계의 로그를 확인한다. 오류나 경고의 원인을 해결한 뒤 같은 명령을 다시 실행한다. 새 터미널에서 `command -v git zsh`와 `type cx`로 도구 경로와 셸 별칭 로딩을 확인할 수 있다. 별칭이 있다는 사실만으로 해당 AI CLI가 설치됐다고 판단하지 않는다.

### Node.js 버전 확인

전체 설치는 nvm의 기본 버전을 Node.js 24로 설정한다. Bash와 Zsh는 공통 설정
`~/.config/dotfiles/nvm.sh`를 읽어 nvm이 선택한 실행 파일을 Homebrew의 Node보다 먼저 찾는다.
터미널 시작 시 Node를 설치하거나 다른 버전을 강제로 선택하지 않는다.
프로젝트가 `.nvmrc`를 제공하면 해당 디렉터리에서 `nvm use`로 버전을 선택한다.

동기화 후 새 터미널에서 확인한다.

```bash
node --version
command -v node
nvm current
```

다른 버전을 선택하지 않았다면 `v24.x.x`와 nvm 디렉터리의 실행 파일이 표시된다.
기존 터미널에서 Homebrew Node가 계속 실행되면 `nvm deactivate` 후 `nvm use default`를
실행한다. 설치 중 실제 버전이 24가 아니면 성공 대신 경고를 출력한다.

### Windows (PowerShell)

저장소를 `$HOME\.dotfiles`에 준비하고, `winget`과 심볼릭 링크 생성 권한이 있는 PowerShell에서 실행한다.

```powershell
& "$HOME\.dotfiles\run.ps1"
```

기존 Git/Vim 대상 파일이 있으면 링크 생성을 건너뛴다. 링크 생성이나 winget 설치가 실패하면 즉시 중단한다. 이 경로는 Zsh·macOS 설정·AI 설정을 동기화하지 않는다. Windows에서 AI 설정을 동기화하려면 WSL의 `run.sh`를 사용한다.

### macOS 설정과 인증

[`macos`](macos)는 소리, 키보드, Finder, Dock, 터미널, 화면 잠금 설정을 적용한다. System Settings를 닫지만 Terminal을 종료하지는 않는다. 즉시 반영되지 않는 UI 설정은 설치 후 로그아웃하거나 재시작하면 적용된다.

- 키를 길게 누르면 악센트 메뉴 대신 문자를 반복한다. 반복 속도는 `KeyRepeat=2`, 시작 지연은 `InitialKeyRepeat=15`다.
- 자동 대문자 변환은 끄고, 스페이스 두 번으로 마침표 추가는 켠다. Finder에는 경로 막대와 상태 막대를 표시한다.
- 부팅음이 이미 꺼져 있으면 해당 `sudo` 인증을 생략한다.
- 화면 잠금이 즉시 잠금이 아니면 macOS 로그인 암호를 터미널에서 입력받는다. 터미널이 없거나 실제 잠금 시간이 바뀌지 않으면 이 단계는 실패한다. 터미널에서 재실행하거나 System Settings > Lock Screen에서 암호 요구 시간을 즉시로 바꾼다.

성공한 설정 내용은 `~/.toast/macos.applied`에 기록한다. 설정이 바뀌거나 적용에 실패하면 다음 실행에서 다시 시도한다. `~/.macos.backup`은 파일 백업이며 적용 완료 기록이 아니다.

## What Gets Installed

정확한 패키지 목록은 [macOS Brewfile](darwin/Brewfile)과 [Linux Brewfile](linux/Brewfile)을 확인한다. 주석 처리된 항목은 설치하지 않는다.

| 구성 | 설치 동작 |
|------|-----------|
| 셸 | Zsh·Oh My Zsh·Dracula 테마, 별칭·공통 nvm 초기화·플랫폼별 프로필 |
| 개발 도구 | 플랫폼별 Brewfile, nvm을 통한 Node.js 24, pip를 통한 `toast-cli` |
| 터미널·앱 | macOS Brewfile의 Ghostty·VS Code 등. iTerm2 프로필은 복사하지만 iTerm2 앱 설치는 포함하지 않음 |
| AI 설정 | Claude Code·Codex·Kiro 지침·설정·스킬 배포 |

AI 설정 배포와 CLI 설치는 별개다. `claude`가 이미 설치되어 있으면 업데이트를 시도한다. NPM 전역 패키지는 설치하지 않는다. 일부 macOS 앱은 Brewfile의 사용자 조건을 만족할 때만 설치한다.

## Repository Layout

| 경로 | 역할 |
|------|------|
| `run.sh`, `run.ps1` | 플랫폼별 설치 진입점 |
| `aliases`, `bashrc`, `zshrc`, `profile` | 셸 명령·환경 설정 |
| `gitconfig*`, `ssh/`, `aws/` | Git 프로필과 SSH·AWS 템플릿 |
| `darwin/`, `linux/` | Brewfile·플랫폼별 프로필, 별도 Ubuntu 서버 준비 스크립트 |
| `macos`, `iterm2/`, `ghostty/`, `tmux.conf`, `vimrc` | OS·터미널·편집기 설정 |
| `nvim/` | 별도로 설치하는 Neovim 설정 |
| `claude/`, `codex/`, `kiro/` | AI 도구에 배포할 원본 |
| `scripts/` | 스킬 생성·AI 설정 배포·격리 테스트 |
| `docs/` | 문서 인덱스·설치 구조 |

## Key Commands & Aliases

설치 후 새 셸에서 사용하는 주요 명령이다. 전체 정의는 [`aliases`](aliases)를 확인한다.

| 명령 | 동작 |
|------|------|
| `tt` | 전체 dotfiles 설치 다시 실행 |
| `c <workspace>` | toast-cli로 워크스페이스 이동 |
| `av <profile> <cmd>` | aws-vault 프로필로 실행. 예: `av n kubectl get pods` |
| `nn` / `nnn` / `nb` | lockfile 유지 재설치 / lockfile 삭제 후 의존성 다시 결정 / build |
| `ss` / `sl` / `sk` | 로컬 서버 시작 / 목록 / 종료. `ss`는 지정 포트의 기존 리스너를 먼저 종료 |
| `tf*` | Terraform plan·apply·destroy·state 등의 별칭 |
| `cc` / `ccc` / `ccu` | Claude Code 시작 / 이어가기 / ccusage |
| `cx` / `cxc` | Codex 시작 / 최근 세션 이어가기 |
| `ccp "prompt"` / `cxp "prompt"` | 프롬프트를 전달해 Claude Code / Codex 시작 |

`nn`과 `nnn`은 `node_modules`와 해당 빌드 출력을 지운다. `nnn`은 lockfile도 지우므로 의존성 버전이 달라질 수 있다. `ss`는 `package.json`이 있으면 Node.js 개발 서버를, 없으면 기본 `docs/` 디렉터리의 Python HTTP 서버를 실행한다. Python 서버는 실제 포트 바인딩 후 성공을 알리며, 시작·종료 신호 실패는 오류로 반환한다.

서버 도우미는 Python 3와 `lsof`가 필요하다. 등록 정보 갱신은 파일 잠금으로 직렬화하여 여러 터미널에서 동시에 실행해도 다른 포트의 기록을 보존한다.

한글 키보드 별칭: `ㅊ` → `c`, `ㅊㅇ` → `cd`, `ㅅㅅ` → `tt`, `ㅊㅊ` → `cc`.

## AI Tools Sync

Claude Code·Codex·OpenCode·Kiro의 공통 지침과 설정을 저장소에서 관리하고 각 머신에 배포한다. **Python 3.11 이상**이 필요하며 외부 Python 패키지는 사용하지 않는다.

### 원본과 배포 대상

| 저장소 원본 | 배포 대상 | 관리 방식 |
|-------------|-----------|-----------|
| `claude/CLAUDE.md`·`claude/rules/` → `codex/AGENTS.md` | `~/.codex/AGENTS.md` | Claude 지침과 규칙을 한 파일로 합친 공통 지침 |
| `claude/skills/` → `codex/skills/` | `~/.agents/skills/` | Claude 원본에서 생성한 Codex 스킬·참조 문서 |
| `codex/skills/*/agents/openai.yaml` | 해당 배포 스킬의 `agents/openai.yaml` | 직접 관리하는 Codex 메타데이터 |
| `claude/CLAUDE.md`·`claude/rules/` → `opencode/AGENTS.md` | `~/.config/opencode/AGENTS.md` | Codex와 같은 공통 지침. 스킬 호출 문법만 `@<name>`이다 |
| `claude/settings.json` → `opencode/opencode.json` | `~/.config/opencode/opencode.json` | Claude `permissions.deny`의 셸 규칙. `permissions`만 원본 우선 |
| `claude/skills/` → `opencode/skills/` | `~/.config/opencode/skills/` | Claude 원본에서 생성한 OpenCode 스킬·참조 문서 |
| `claude/agents/` → `opencode/agents/` | `~/.config/opencode/agents/` | Claude 서브에이전트에서 생성한 OpenCode 서브에이전트 |
| `codex/config.toml` | `~/.codex/config.toml` | 승인·권한 선택은 원본 우선, 나머지는 없는 키만 추가 |
| `codex/hooks.json` | `~/.codex/hooks.json` | dotfiles 소유 훅만 갱신하고 다른 훅 유지 |
| `codex/rules/default.rules` | `~/.codex/rules/default.rules` | 관리 마커 내부만 갱신하고 로컬 규칙 유지 |
| `claude/`, `kiro/` | `~/.claude/`, `~/.kiro/` | 각 도구의 지침·설정 |

루트 [AGENTS.md](AGENTS.md)는 이 저장소 작업용이며 `CLAUDE.md`는 이를 가리키는 심볼릭 링크다. 모든 프로젝트에 배포할 지침은 [claude/CLAUDE.md](claude/CLAUDE.md)와 언어·Git·보안 규칙을 담은 [claude/rules/](claude/rules/)에서 수정한다. Codex·OpenCode의 `AGENTS.md`는 이 둘을 합쳐 생성한다.

Codex 기본값은 `approval_policy = "never"`, `default_permissions = ":danger-full-access"`다. 로컬 명령의 승인 프롬프트와 샌드박스 제한을 해제한다. 실행 환경의 강제 정책은 이 설정보다 우선한다. [공식 권한 프로필 안내](https://learn.chatgpt.com/docs/permissions)를 참고한다.

Codex와 Claude는 요청 범위에서 문제가 없음을 검증한 `main` push·merge·릴리즈·배포를 별도 사용자 승인 없이 수행한다. 해당 커밋의 필수 검사·CI·리뷰 통과, 미해결 차단 문제·충돌 부재, 대상과 영향을 확인한다. 릴리즈 완료와 대상 환경의 정상 동작을 확인한 뒤 merge된 해당 작업의 로컬·원격 브랜치를 정리하며, 미반영 작업과 다른 worktree는 보존한다. 상세 조건은 [Git Workflow](claude/rules/git-workflow.md)를 따른다. 이 지침은 Git 서버의 브랜치 보호나 필수 환경 승인을 해제하지 않는다.

기술 문서는 ISO 24495-1처럼 쉽게 찾고 이해하고 사용할 수 있게, ASD-STE100처럼 짧고 명확하며 모호하지 않게 작성한다. 필요한 정보·문서 구조·표현·작업과 판단에 사용할 수 있는 설명을 함께 검토한다. 구체적인 점검 항목은 [docs-sync](claude/skills/docs-sync/SKILL.md#작성-품질)에 있다. 이는 자체 작성 규칙이며 표준 전체 준수 선언은 아니다. [ISO 개요](https://www.iso.org/standard/78907.html)와 [IPLF의 네 원칙 설명](https://www.iplfederation.org/iso-standard/), [ASD-STE100 소개](https://www.asd-ste100.org/about_STE.html)를 참고한다.

### 수정과 검증

작업 중인 checkout의 루트에서 실행한다. 공통 지침은 `claude/CLAUDE.md`·`claude/rules/`, 공유 스킬은 `claude/skills/`, 서브에이전트는 `claude/agents/`, deny 규칙은 `claude/settings.json`을 수정한 뒤 Codex·OpenCode 파일을 재생성한다. [스킬 안내](docs/SKILLS.md)에서 역할과 원본 위치를 확인할 수 있다.

```bash
python3 scripts/gen-ai-tools.py
python3 scripts/gen-ai-tools.py --check
python3 scripts/test_ai_tools.py
bash -n run.sh
git diff --check
```

`--check`는 생성 파일의 내용과 오래된 잔여 파일을 검사한다. 생성기는 원본이 바뀌어 변환 규칙이 맞지 않으면 파일을 쓰지 않고 오류로 종료한다. 예를 들어 서브에이전트에 지원하지 않는 frontmatter 필드나 `tools` 이름이 있거나, deny 규칙이 `Bash(...)` 형식이 아니거나, `claude/CLAUDE.md`에서 변환 대상 문장(제목, `rules/` 안내, 스킬 호출 문법)이 바뀐 경우다. 테스트는 임시 홈을 사용하며 실제 설정 배포나 원격 push를 하지 않는다. macOS 설치 단계를 변경했다면 `python3 scripts/test_macos.py`와 `bash -n macos`도 실행한다.

설치기·셸·플랫폼 설정을 함께 변경했다면 `python3 -m unittest discover -s scripts -p 'test_*.py'`로 전체 회귀 검사를 실행한다. 서버 검사는 임시 로컬 HTTP 서버도 실행한다. PowerShell이 없는 환경에서는 Windows 검사만 건너뛰며, 실제 OS 설정 적용과 패키지 설치는 별도 검증이 필요하다.

### 배포와 결과 확인

각 머신의 `~/.dotfiles`에 원하는 변경을 반영한 뒤 실행한다. `--vibe`는 checkout을 갱신하지 않으며, 다른 경로에서 호출해도 원본은 항상 `~/.dotfiles`에서 읽는다.

```bash
bash ~/.dotfiles/run.sh --vibe
cmp ~/.dotfiles/codex/AGENTS.md ~/.codex/AGENTS.md
cmp ~/.dotfiles/claude/CLAUDE.md ~/.claude/CLAUDE.md
diff -qr ~/.dotfiles/codex/skills ~/.agents/skills
cmp ~/.dotfiles/opencode/AGENTS.md ~/.config/opencode/AGENTS.md
diff -qr ~/.dotfiles/opencode/skills ~/.config/opencode/skills
diff -qr ~/.dotfiles/opencode/agents ~/.config/opencode/agents
```

`cmp`는 파일이 같으면 출력 없이 종료한다. 스킬 비교에서는 저장소 파일의 차이를 확인하고, 배포 대상에만 있는 사용자 설치 스킬·백업은 따로 구분한다.

### 기존 설정 보존과 실패 처리

일반 지침·스킬은 MD5로 비교해 변경된 파일을 원자적으로 교체한다. 덮어쓰기·manifest 기반 삭제 전에는 같은 경로의 `.backup`에 직전 내용을 보관하고 권한을 `600`으로 설정한다. manifest는 이전에 배포한 파일 목록이다. 목록에 없는 파일은 삭제하지 않으며, 원본 디렉터리가 없거나 비어 있으면 해당 대상과 목록을 보존한다.

Codex 원본에 `default_permissions`가 있으면 승인·권한 선택은 저장소 값을 따른다. `approval_policy`, `approvals_reviewer`, `default_permissions`, `sandbox_mode`, `sandbox_workspace_write`를 원본과 맞추고, 원본에 없는 키는 제거한다. 따라서 기존 설치도 동기화 후 같은 승인 정책을 사용하며, 예전 샌드박스 설정이 새 권한 프로필을 가리지 않는다. 변경 후 새 세션에서 권한 모드를 확인한다.

Claude `settings.json`의 `permissions.deny`와 `autoMode`도 원본에 있으면 저장소 값으로 교체한다. `autoMode`는 권한 분류기가 읽는 환경·정책 설명이므로 머신에서 생성된 예전 값이 남으면 안 된다. 머신에서 직접 추가한 deny 규칙은 다음 동기화 때 `.backup`에만 남으므로, 유지할 규칙은 `claude/settings.json`에 추가한다. OpenCode `opencode.json`의 `permissions`도 같은 방식으로 저장소 목록으로 교체한다. 셸 연산자(`|`, `&&`)로 이은 명령은 부분 명령별로 검사되므로 deny 규칙은 부분 명령 하나를 기준으로 쓴다.

Claude·Codex·Kiro의 훅은 이벤트 전체가 아니라 실행 스크립트별로 관리한다. dotfiles가 배포하는 `hooks/` 스크립트의 등록만 원본에 맞춰 갱신한다. 같은 이벤트의 VibeMon·romty·사용자 훅과 matcher는 보존한다. 이벤트 배열이 이미 있거나 비어 있어도 머신에 필요한 훅을 추가하며, 재실행해도 중복 등록하지 않는다. 원본에서 제거한 머신 스크립트는 기존 manifest를 기준으로 훅 등록도 정리한다.

OpenCode의 `opencode.jsonc`·`cli.json`·`plugins/`는 배포 대상이 아니다. 모델·provider·자격 증명·플러그인과 머신 전용 권한 규칙은 `opencode.jsonc`에서 관리한다. OpenCode는 같은 디렉터리의 `opencode.json`과 `opencode.jsonc`를 모두 읽고 `permissions` 규칙을 이 순서로 이어 붙인다.

VibeMon 전송·사용량 스크립트와 전용 훅, Claude `statusline.py`는 VibeMon 설치기가 관리한다. dotfiles는 이를 복사하거나 삭제하지 않으며, 과거 manifest에 남은 경로는 파일을 보존하고 목록에서만 제외한다. 공유 JSON 설정과 Codex `config.toml`도 원본에서 빠졌다는 이유로 파일 전체를 삭제하지 않는다. Codex의 일반 `tui.status_line` 기본값은 dotfiles에서 관리하고 기존 머신의 선택은 보존한다.

그 외 Codex TOML, Claude `settings.json`, Kiro `agents/default.json` 설정은 기존 값을 우선하고 없는 키만 채운다. 모델·UI·MCP·신뢰 목록, 일반 배열·명시적 `false`·빈 값도 유지하므로 머신별 설정은 다를 수 있다. Codex 명령 승인 규칙은 관리 블록 밖 내용을 보존한다.

VibeMon 저장소가 있으면 두 실제 설치기의 실행 순서·재설치·제거를 임시 홈에서 검증할 수 있다. 이 검사는 네트워크나 실제 머신 설정을 사용하지 않는다.

```bash
DOTFILES_VIBEMON_INSTALLER=/path/to/vibemon-app/public/install/install.py \
  python3 scripts/test_vibemon_integration.py
```

[`scripts/sync-ai-tools.py`](scripts/sync-ai-tools.py)는 모든 대상의 병합 결과를 확인한 뒤 배포한다. JSON·TOML 오류, 손상된 규칙 마커, 심볼릭 링크 대상, 지원하지 않는 TOML 편집 형태는 오류로 종료한다. 동시 실행은 잠금으로 차단한다.

파일 배포 중 I/O 오류가 나면 일부 파일이 이미 반영되었을 수 있다. 실패한 쓰기는 원본을 보존하며, 모든 파일 배포가 성공해야 대상별 manifest를 갱신한다. 오류를 해결한 뒤 재실행한다. 생성기는 원본에서 삭제된 Markdown을 미러에서 정리하고, 수동 관리하는 `agents/openai.yaml`은 보존한다.

### 지침 로딩

설치기는 Codex 설정을 `~/.codex`에 배포한다. 별도 `CODEX_HOME`이나 `AGENTS.override.md`를 사용하면 실제 로딩 위치를 확인하고 새 세션에서 지침을 확인한다. [공식 지침 로딩 규칙](https://learn.chatgpt.com/docs/agent-configuration/agents-md)을 참고한다.

Codex CLI에서는 `/skills` 또는 `$<name>`으로 스킬을 지정한다. `skills/<name>/...` 참조는 세션에 표시된 해당 스킬 경로를 기준으로 해석한다. [공식 스킬 안내](https://learn.chatgpt.com/docs/build-skills)를 참고한다.

OpenCode V2는 `AGENTS.md`만 지침으로 읽으며 `CLAUDE.md`와 `~/.claude/rules/`는 읽지 않는다. 설정의 `instructions` 항목도 아직 적용하지 않으므로 공통 지침은 `~/.config/opencode/AGENTS.md`로 배포한다. 같은 이름의 스킬은 `.claude/skills` → `.agents/skills` → `~/.config/opencode/skills` → 프로젝트 `.opencode/skills` 순서로 나중 경로가 우선한다. `.claude/skills`와 `.agents/skills`는 전역 경로 다음에 프로젝트 경로를 읽는다. 따라서 OpenCode 전용 생성본이 Claude·Codex 사본을 대체하고, 프로젝트의 `.opencode/skills`는 생성본보다 우선한다. 스킬은 `@<name>`으로 지정한다. Claude.ai에서 동기화한 `~/.claude/skills/synced/` 스킬도 함께 표시되며 dotfiles는 이를 관리하지 않는다.

OpenCode 서브에이전트는 Claude `tools` 목록을 권한 허용 목록으로 바꾼다. 모든 작업을 거부한 뒤 목록의 도구만 허용하고, `.env` 읽기와 프로젝트 밖 경로는 확인을 요청한다. OpenCode는 에이전트 규칙을 전역 `permissions` 뒤에 적용하고 마지막으로 일치한 규칙을 사용한다. 그래서 생성기는 셸을 허용한 서브에이전트에 `claude/settings.json`의 deny 규칙을 다시 넣는다. `opencode.jsonc`에 추가한 머신 전용 셸 규칙은 셸을 허용한 서브에이전트에 적용되지 않으므로, 모든 도구에 적용할 규칙은 `claude/settings.json`에 추가한다. 변환하는 frontmatter는 `name`(파일명과 일치), `description`, `tools`뿐이다. 설정 위치는 `opencode debug paths`의 `config`로, 배포된 서브에이전트는 `opencode debug agents`로 확인한다. [공식 지침](https://opencode.ai/v2/docs/instructions/), [스킬](https://opencode.ai/v2/docs/skills/), [에이전트](https://opencode.ai/v2/docs/agents/) 문서를 참고한다.

## Security

`run.sh`는 없는 SSH 키를 생성하고 SSH 디렉터리를 `700`으로 설정한다. 설치기가 복사하는 SSH·AWS 파일과 백업에는 `600`을 적용한다. Git 설정은 디렉터리별 프로필을 사용하므로 변경 전 `gitconfig*`의 이름·이메일을 확인한다.

1Password CLI를 통한 자격 증명 가져오기는 수동 작업이다. 다음은 이 저장소 소유자의 vault 경로를 사용하는 예시이며, 자신의 항목으로 바꿔 실행한다. 출력 대상은 로컬 평문 파일이고 기존 내용은 덮어쓴다. 먼저 필요한 백업을 준비하고 값을 로그·Git에 남기지 않는다.

```bash
op read op://keys/ssh-config/notesPlain > ~/.ssh/config && chmod 600 ~/.ssh/config
op read op://keys/nalbam-seoul.pem/notesPlain > ~/.ssh/nalbam-seoul.pem && chmod 600 ~/.ssh/nalbam-seoul.pem
op read op://keys/aws-config/notesPlain > ~/.aws/config && chmod 600 ~/.aws/config
op read op://keys/aws-credentials/notesPlain > ~/.aws/credentials && chmod 600 ~/.aws/credentials
```

## Documentation

[문서 인덱스](docs/README.md)에서 설치 구조, 플랫폼별 추가 설정, AI 지침과 스킬로 이동할 수 있다.

## Contributing

별도 브랜치에서 변경하고 관련 검사를 실행한 뒤 PR을 만든다. 커밋은 Conventional Commits 형식을 권장한다. 에이전트는 요청 범위의 commit·push·PR 생성을 자율 수행하며, [Git Workflow](claude/rules/git-workflow.md)의 검증 조건을 충족하면 merge·릴리즈·배포와 완료 후 브랜치 정리까지 진행한다.

## License

MIT License
