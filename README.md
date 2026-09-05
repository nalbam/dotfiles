# dotfiles

개인 개발 환경을 macOS, Linux, Windows에서 일관되게 자동으로 구성하는 스크립트 모음이다.

한 번의 명령으로 shell, git, SSH, 패키지 매니저, 개발 도구, AI 도구 설정까지 동기화한다.

## Supported Platforms

| OS | Architecture |
|----|--------------|
| macOS | Apple Silicon (arm64), Intel (x86_64) |
| Linux | Ubuntu/WSL (x86_64), Raspberry Pi (aarch64, armv7l) |
| Windows | MinGW64 (PowerShell) |

## Quick Start

### macOS / Linux

```bash
curl -fsSL nalbam.github.io/dotfiles/run.sh | bash
```

### Windows (PowerShell)

```powershell
./run.ps1
```

### 이미 clone한 경우

```bash
cd ~/.dotfiles
./run.sh
```

## Highlights

- **Cross-platform**: 한 저장소로 macOS / Linux / Windows 지원
- **11-step installer**: OS 감지부터 AI 도구 동기화까지 단계별 자동 진행
- **Resilient**: 네트워크 재시도(exponential backoff), 6시간 업데이트 스로틀링, MD5 무결성 체크
- **Organization-aware Git**: 디렉터리별 `includeIf`로 개인/회사 계정 자동 전환
- **AI tools sync**: Claude Code, Codex, Kiro 설정을 여러 머신에서 동일하게 유지
- **Secret-safe**: 1Password CLI 통합으로 자격 증명을 평문 파일 없이 관리

## What Gets Installed

설치 스크립트는 다음을 자동으로 구성한다.

- **Shell**: ZSH + Oh My ZSH, Dracula 테마, 자동 완성/구문 강조 플러그인
- **Terminal**: iTerm2, Ghostty, tmux (시스템 메트릭 상태바 포함)
- **Cloud/DevOps**: `awscli`, `eksctl`, `kubectl`, `helm`, `argocd`, `k9s`, `tenv`
- **Dev tools**: `git`, `gh`, `jq`, `yq`, `fzf`, `ripgrep`, `httpie`, Go, Node.js (nvm), Python (pyenv)
- **Editors/Apps** (macOS): VS Code, iTerm2, Ghostty, 1Password, Google Drive
- **Fonts**: D2Coding, DejaVu Sans Mono Nerd Font

전체 패키지 목록은 `darwin/Brewfile`, `linux/Brewfile`을 참고하라.

## Repository Layout

```
.
├── run.sh / run.ps1          # Installer entry points
├── aliases                   # Shell aliases & helper functions
├── gitconfig*                # Base + organization-specific Git profiles
├── zshrc, bashrc, profile    # Shell configuration
├── tmux.conf, vimrc, macos   # Tool-specific configs
│
├── darwin/                   # macOS Brewfile + arch-specific zprofile
├── linux/                    # Linux Brewfile + arch-specific zprofile
├── ssh/, aws/                # SSH/AWS config templates
├── iterm2/, ghostty/         # Terminal profiles
│
├── claude/                   # Claude Code settings → ~/.claude/
├── codex/                    # Codex settings → ~/.codex/ (skills/ → ~/.agents/skills/)
├── kiro/                     # Kiro settings → ~/.kiro/
├── scripts/                  # Dev tools (codex skills mirror generator)
└── docs/                     # Architecture & deeper documentation
```

## Key Commands & Aliases

설치 후 사용 가능한 주요 단축 명령이다. 전체 목록은 [`aliases`](./aliases) 파일을 참고하라.

| Alias | Description |
|-------|-------------|
| `tt` | dotfiles 재설치 |
| `c <workspace>` | toast-cli 워크스페이스 디렉터리 이동 |
| `av <profile> <cmd>` | aws-vault 프로파일 실행 (e.g. `av n kubectl get pods`) |
| `nn` / `nb` | Node.js: clean install / build (npm·pnpm·yarn 자동 판별) |
| `ss` / `sl` / `sk` | 로컬 dev 서버 (node dev 또는 python http.server 자동): start / list / kill |
| `tf*` | Terraform: plan/apply/destroy/state |
| `tm*` | tmux: new / attach / list / kill |
| `cc`, `ccc`, `ccu` | Claude Code: 실행 / continue / ccusage |
| `cx`, `cxc` | Codex: 실행 / 최근 세션 이어가기 |
| `ccp "prompt"`, `cxp "prompt"` | Claude Code / Codex에 프롬프트를 전달해 시작 |

**한글 키보드 단축키**: `ㅊ` → `c`, `ㅊㅇ` → `cd`, `ㅅㅅ` → `tt`, `ㅊㅊ` → `cc`

## AI Tools Sync

Claude Code, Codex, Kiro의 공통 지침·훅·규칙·스킬을 저장소에 버전 관리하고 `run.sh`로 macOS·Linux·WSL에 배포한다. AI 동기화에는 **Python 3.11 이상**이 필요하며 외부 Python 패키지는 사용하지 않는다. `run.ps1`에는 AI 설정 동기화가 없으므로 Windows에서는 WSL의 `run.sh`를 사용한다.

| 저장소 원본 | 배포 대상 | 관리 방식 |
|-------------|-----------|-----------|
| `codex/AGENTS.md` | `~/.codex/AGENTS.md` | 모든 프로젝트에 적용할 공통 지침 |
| `claude/skills/` → `codex/skills/` | `~/.agents/skills/` | 공유 원본에서 생성한 Codex 스킬·참조 문서 |
| `codex/skills/*/agents/openai.yaml` | 해당 배포 스킬의 `agents/openai.yaml` | 직접 관리하는 Codex 메타데이터 |
| `codex/config.toml`, `codex/hooks.json` | `~/.codex/`의 같은 파일 | 없는 키만 추가하고 기존 값 유지 |
| `codex/rules/default.rules` | `~/.codex/rules/default.rules` | 관리 마커 내부만 갱신하고 로컬 규칙 유지 |
| `claude/`, `kiro/` | `~/.claude/`, `~/.kiro/` | 각 도구의 지침·설정 |

루트 [`AGENTS.md`](./AGENTS.md)는 이 저장소 작업용이고, [`codex/AGENTS.md`](./codex/AGENTS.md)는 머신에 배포할 전역 지침이다. 전역에는 공통 규칙만 두고 프로젝트별 명령·관례는 각 프로젝트에서 관리한다.

Claude 전역 지침은 [`claude/CLAUDE.md`](./claude/CLAUDE.md), 자동 로드되는 언어·Git·보안 규칙은 `claude/rules/`에서 관리한다. 루트 `CLAUDE.md`는 `AGENTS.md`를 가리키는 심볼릭 링크로 두 도구가 저장소 지침을 공유한다. 스킬별 역할은 [스킬 안내](./claude/skills/README.md)를 참고하라.

수정·검증은 작업 중인 checkout에서 실행한다. 생성된 Codex 스킬을 직접 편집하지 않는다.

```bash
python3 scripts/gen-codex-skills.py
python3 scripts/gen-codex-skills.py --check
python3 scripts/test_ai_tools.py
bash -n run.sh claude/hooks/memory-sync.sh
git diff --check
```

배포는 각 머신의 `~/.dotfiles`에 원하는 변경이 반영된 상태에서 실행한다. `--vibe`는 Git checkout을 갱신하지 않으며, 다른 경로에서 호출해도 원본은 항상 `~/.dotfiles`에서 읽는다.

```bash
~/.dotfiles/run.sh --vibe
cmp ~/.dotfiles/codex/AGENTS.md ~/.codex/AGENTS.md
diff -qr ~/.dotfiles/codex/skills ~/.agents/skills
```

`cmp`는 전역 지침의 동일 여부를 확인한다. 스킬 비교에서는 저장소에 있는 파일의 차이를 확인하고, 배포 대상에만 있는 사용자 설치 스킬은 별도로 구분한다.

일반 지침·스킬은 MD5로 비교해 변경분을 원자적으로 교체한다. 덮어쓰기·manifest 기반 삭제 전에는 같은 경로의 `.backup`에 직전 내용을 보관하고 권한을 `600`으로 설정한다. manifest에 없는 파일은 삭제하지 않는다. 원본 디렉터리가 없거나 비어 있으면 해당 대상과 manifest를 보존한다.

`config.toml`·`hooks.json`의 기존 값과 관리 블록 밖 명령 승인 규칙은 보존하므로, 동기화 후에도 머신별 설정값은 다를 수 있다. Claude `settings.json`과 Kiro `agents/default.json`도 없는 키만 채우며 기존 배열·명시적 `false`·빈 값은 유지한다. 공통 기본값 변경으로 기존 머신의 선택을 덮어쓰지 않는다.

[`scripts/sync-ai-tools.py`](./scripts/sync-ai-tools.py)가 모든 대상의 병합 결과를 검증한 뒤 배포한다. JSON·TOML 오류, 손상된 규칙 마커, 심볼릭 링크 대상은 자동 덮어쓰지 않고 오류로 종료한다. 지원되지 않는 TOML 편집 형태도 원본을 보존하고 보고한다. 파일 배포 중 I/O 오류가 나면 일부 파일은 이미 반영되었을 수 있으나 실패한 쓰기는 원본을 보존한다. 모든 파일 배포에 성공한 뒤 대상별 manifest를 원자적으로 갱신한다. 오류를 해결한 뒤 재실행한다. 동시 실행은 잠금으로 차단하고, 설정값은 로그에 출력하지 않는다.

생성기는 원본에서 삭제된 Markdown도 미러에서 정리하며 `agents/openai.yaml` 같은 수동 관리 메타데이터는 보존한다. `--check`는 오래된 내용과 남은 생성물을 모두 검사한다.

Claude 메모리 동기화는 `claude/hooks/memory-sync.sh`가 별도의 개인 메모리 저장소에서 수행한다. 최초 clone·프로젝트 연결·Git 동기화는 백그라운드에서 실행되므로 새 머신에서는 완료 후 메모리 링크를 사용할 수 있다. Git 단계가 실패하면 후속 push를 중단한다. 네트워크 오류는 다음 실행에서 재시도하고, rebase·merge 충돌이 남아 있으면 메모리 저장소에서 해결한 뒤 재시도한다. 이 훅의 자동 커밋·push는 메모리 저장소에 한정되며 프로젝트의 커밋 권한과는 별개다.

Codex의 지침 탐색은 `CODEX_HOME`과 `AGENTS.override.md`의 영향을 받는다. 이 설치기는 `~/.codex`에 배포하므로 별도 `CODEX_HOME`을 쓰는 머신은 실제 로딩 위치를 확인한다. 동기화한 지침은 새 Codex 세션에서 확인한다. [공식 지침 로딩 규칙](https://learn.chatgpt.com/docs/agent-configuration/agents-md)을 참고하라.

스킬은 이름·설명으로 선택되고 본문은 필요할 때 읽힌다. Codex CLI에서는 `/skills` 또는 `$<name>`으로 지정한다. 문서의 `skills/<name>/...` 참조는 세션에 표시된 해당 스킬 경로를 기준으로 해석한다. [공식 스킬 안내](https://learn.chatgpt.com/docs/build-skills)를 참고하라.

## Security

- SSH 키 자동 생성 (RSA + ED25519)
- 민감 파일은 자동으로 `600` 권한 적용
- 기존 파일은 덮어쓰기 전 백업
- [1Password CLI](https://developer.1password.com/docs/cli) 연동으로 SSH 키·AWS 자격 증명을 vault에서 읽어옴

```bash
# SSH config from 1Password
op read op://keys/ssh-config/notesPlain > ~/.ssh/config && chmod 600 ~/.ssh/config

# SSH private keys from 1Password
op read op://keys/nalbam-seoul.pem/notesPlain > ~/.ssh/nalbam-seoul.pem && chmod 600 ~/.ssh/nalbam-seoul.pem

# AWS credentials from 1Password
op read op://keys/aws-config/notesPlain > ~/.aws/config && chmod 600 ~/.aws/config
op read op://keys/aws-credentials/notesPlain > ~/.aws/credentials && chmod 600 ~/.aws/credentials
```

## Documentation

- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) — 설치 플로우, 컴포넌트 다이어그램, 에러 처리 전략
- [docs/README.md](./docs/README.md) — 전체 문서 인덱스
- [CLAUDE.md](./CLAUDE.md) — AI agent가 이 저장소를 다룰 때의 가이드
- [AGENTS.md](./AGENTS.md) — Codex의 저장소 작업 지침

## Contributing

1. Fork
2. Feature branch 생성
3. 변경사항 커밋 (Conventional Commits 권장)
4. Pull Request 생성

## License

MIT License
