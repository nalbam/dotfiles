# dotfiles

개인 개발 환경을 macOS, Linux, Windows에서 일관되게 자동으로 구성하는 스크립트 모음입니다.

한 번의 명령으로 shell, git, SSH, 패키지 매니저, 개발 도구, AI 도구 설정까지 동기화합니다.

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
- **Resilient**: 네트워크 재시도(exponential backoff), 12시간 업데이트 스로틀링, MD5 무결성 체크
- **Organization-aware Git**: 디렉터리별 `includeIf`로 개인/회사 계정 자동 전환
- **AI tools sync**: Claude Code와 Kiro 설정을 여러 머신에서 동일하게 유지
- **Secret-safe**: 1Password CLI 통합으로 자격 증명을 평문 파일 없이 관리

## What Gets Installed

설치 스크립트는 다음을 자동으로 구성합니다.

- **Shell**: ZSH + Oh My ZSH, Dracula 테마, 자동 완성/구문 강조 플러그인
- **Terminal**: iTerm2, Ghostty, tmux (시스템 메트릭 상태바 포함)
- **Cloud/DevOps**: `awscli`, `eksctl`, `kubectl`, `helm`, `argocd`, `k9s`, `tenv`
- **Dev tools**: `git`, `gh`, `jq`, `yq`, `fzf`, `ripgrep`, `httpie`, Go, Node.js (nvm), Python (pyenv)
- **Editors/Apps** (macOS): VS Code, iTerm2, Ghostty, 1Password, Google Drive
- **Fonts**: D2Coding, DejaVu Sans Mono Nerd Font

전체 패키지 목록은 `darwin/Brewfile`, `linux/Brewfile`을 참고하세요.

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
├── kiro/                     # Kiro settings → ~/.kiro/
└── docs/                     # Architecture & deeper documentation
```

## Key Commands & Aliases

설치 후 사용 가능한 주요 단축 명령입니다. 전체 목록은 [`aliases`](./aliases) 파일을 참고하세요.

| Alias | Description |
|-------|-------------|
| `tt` | dotfiles 재설치 |
| `vv` | AI 도구(Claude Code, Kiro) 설정만 동기화 |
| `c <workspace>` | toast-cli 워크스페이스 디렉터리 이동 |
| `av <profile> <cmd>` | aws-vault 프로파일 실행 (e.g. `av n kubectl get pods`) |
| `nn` / `nb` / `nd` / `nk` | Node.js: clean install / build / dev server / kill ports |
| `ss` / `sl` / `sk` | 로컬 HTTP 서버: start / list / kill |
| `tf*` | Terraform: plan/apply/destroy/state |
| `tm*` | tmux: new / attach / list / kill |
| `cc`, `ccc`, `ccu` | Claude Code: 실행 / continue / ccusage |

**한글 키보드 단축키**: `ㅊ` → `c`, `ㅊㅇ` → `cd`, `ㅅㅅ` → `tt`, `ㅍㅍ` → `vv`

## AI Tools Sync

Claude Code와 Kiro의 에이전트·훅·규칙·스킬을 저장소에 버전 관리하고 여러 머신에 배포합니다.

```bash
vv                         # AI 도구 설정만 빠르게 동기화
~/.dotfiles/run.sh --vibe  # 동일 (직접 호출)
```

- `claude/` → `~/.claude/`
- `kiro/` → `~/.kiro/`

변경된 파일만 MD5로 비교해 부분 동기화합니다.

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

## Contributing

1. Fork
2. Feature branch 생성
3. 변경사항 커밋 (Conventional Commits 권장)
4. Pull Request 생성

## License

MIT License
