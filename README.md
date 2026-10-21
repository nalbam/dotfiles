# dotfiles

명령 하나로 머신을 감지해 기본 환경을 설치하고, 다시 실행하면 설치한 도구를 최신으로 유지한다. macOS 워크스테이션, WSL2, DGX Spark, EC2(k3s 노드), Raspberry Pi, 일반 Ubuntu/Debian을 지원한다. 모델 서빙·모니터링 같은 추가 구성은 add-on 모듈로 켠다.

- 처음 설치: [Quick Start](#quick-start)
- 매일 쓰는 명령: [dot 명령](#dot-명령)
- 머신별 동작: [플랫폼과 모듈](#플랫폼과-모듈)
- DGX Spark 모델 서빙: [stacks/dgx-spark](stacks/dgx-spark/README.md)
- AI 지침·스킬 수정 및 배포: [AI Tools Sync](#ai-tools-sync)
- 설계·실패 처리: [Architecture](docs/ARCHITECTURE.md)

## Quick Start

로그인한 일반 사용자로 실행한다. Bash·curl·네트워크가 필요하고, 시스템 변경 단계에서 `sudo` 암호를 물을 수 있다.

```bash
curl -fsSL https://nalbam.github.io/dotfiles/run.sh | bash
```

`run.sh`는 `~/.dotfiles`를 준비한 뒤 `dot up`을 실행한다. Git을 아직 쓸 수 없으면(Command Line Tools가 없는 새 macOS 등) 저장소 압축 파일을 받고, 다음 `dot up`에서 Git checkout으로 바꾼다. 설치가 끝나면 `dot`이 `~/.local/bin/dot`에 연결된다.

완료 요약에 `⚠`나 `✗`가 있으면 해당 모듈의 로그를 확인하고 원인을 해결한 뒤 `dot up`을 다시 실행한다. 새 터미널에서 `dot doctor`로 셸·PATH·도구 상태를 확인한다.

이전 설치기를 쓰던 머신은 같은 명령(`tt`)을 한 번 실행하면 새 구조로 바뀐다. 이전 `~/.toast` 기록은 그대로 이어받으므로 macOS 설정을 다시 적용하지 않는다.

## dot 명령

| 명령 | 동작 |
|------|------|
| `dot` / `dot up` | 저장소를 갱신하고, 프로필과 켠 add-on을 설치한다. 마지막 업그레이드 후 6시간이 지났으면 설치한 도구를 업그레이드한다. |
| `dot up --force` | 6시간 간격을 무시하고 바로 업그레이드한다. |
| `dot list` | 모든 모듈과 이 머신에서의 상태(`profile`·`enabled`·`available`·`disabled`·`unsupported`)를 보여준다. |
| `dot status` | 플랫폼, checkout, 모듈별 마지막 업그레이드 시점과 상태를 보여준다. |
| `dot add MODULE...` | add-on을 켜고 바로 설치한다. 예: `dot add k3s`, `dot add llm monitoring` |
| `dot remove MODULE...` | 모듈 관리를 끈다. 설치된 소프트웨어는 지우지 않는다. 프로필 모듈도 끌 수 있다. |
| `dot run MODULE...` | 지정한 모듈만 실행한다. 예: `dot run shell` |
| `dot vibe` | AI 도구 설정만 배포한다(`dot run ai`). |
| `dot upgrade-system [--yes]` | OS 패키지 업그레이드. `--yes` 없이는 대상만 보여준다. `dot up`은 OS 패키지를 업그레이드하지 않는다. |
| `dot platform [set NAME\|reset]` | 감지된 플랫폼을 보거나 고정한다. |
| `dot doctor` | 셸·PATH·Python·Homebrew·Git 신원을 점검한다. |
| `dot llm ...` | DGX Spark 모델 스택 운영. `dot llm help` 참고. |
| `dot @HOST COMMAND...` | 다른 머신에서 SSH로 `dot`을 실행한다. 예: `dot @spark llm status`, `dot @web-1 up` |
| `dot @HOST bootstrap` | 원격 머신에 dotfiles를 처음 설치한다. |

### 업그레이드 정책

- `dot up`은 사용자 영역 도구(Homebrew 패키지, Node.js, Claude Code, pip 도구, Oh My Zsh, AWS CLI, k3s 등)를 업그레이드한다. 모듈마다 성공한 시점을 기록하고, 6시간이 지나기 전에는 건너뛴다. 실패한 업그레이드는 기록하지 않으므로 다음 실행에서 다시 시도한다.
- 저장소의 설정 원본(Brewfile, 셸 설정, Spark 스택 등)이 바뀌면 6시간 간격과 관계없이 바로 반영한다.
- OS 패키지(`apt upgrade`, macOS 업데이트)는 `dot up`에 포함하지 않는다. 커널·드라이버·Docker가 바뀌면 서비스가 재시작되고 재부팅이 필요할 수 있기 때문이다. 점검 시간에 `dot upgrade-system --yes`로 실행한다.

## 플랫폼과 모듈

`dot`은 로컬 커널·펌웨어 정보만으로 플랫폼을 감지한다(네트워크를 쓰지 않는다). 감지가 맞지 않으면 `dot platform set NAME`으로 고정한다.

| 플랫폼 | 감지 기준 | 기본 프로필 | 주요 add-on |
|--------|-----------|-------------|-------------|
| `macos` | `uname`이 Darwin | base git brew macos node python claude shell terminal ai | nvim |
| `wsl` | `WSL_DISTRO_NAME` 또는 커널 이름의 `microsoft` | base apt git brew node python claude shell ai | nvim |
| `dgx-spark` | `/etc/dgx-release` 또는 DMI 제품명 | base apt git brew node python claude shell ai | llm monitoring vibemon |
| `ec2` | DMI 제조사 `Amazon EC2`, 인스턴스 asset tag, Xen UUID | base apt server git shell ai | k3s docker brew node |
| `rpi` | device tree 모델명 | base apt git python shell ai | node nvim |
| `linux` | 그 밖의 Linux | base apt git brew node python claude shell ai | server docker k3s nvim |

기본 프로필은 [`profiles/`](profiles), 실행 순서와 모듈 계약은 [Architecture](docs/ARCHITECTURE.md#modules)를 따른다. 이미 설치된 add-on(예: Spark에서 이미 운영 중인 모델 스택, EC2의 k3s)은 첫 `dot up`에서 자동으로 켜져 계속 관리된다. `dot remove`로 끈 모듈은 자동으로 다시 켜지지 않는다.

| 모듈 | 설치·업그레이드 내용 |
|------|----------------------|
| `base` | `~/.ssh`(700)·SSH 키·SSH/AWS 템플릿, `~/.local/bin/dot` 링크 |
| `apt` | 필수 APT 패키지. 빠진 패키지가 있을 때만 index를 갱신한다. |
| `server` | 시간대, fail2ban, fstrim, 스왑, AWS CLI v2 |
| `git` | `~/.gitconfig`와 디렉터리별 신원 파일 |
| `brew` | Homebrew와 [`packages/Brewfile.<os>`](packages) |
| `macos` | Command Line Tools, Rosetta 2, 키 바인딩, [시스템 설정](config/macos/defaults.sh) |
| `node` | nvm과 Node.js 24(최신 24.x) |
| `python` | pip 도구(`toast-cli`) |
| `claude` | Claude Code 설치, `claude update` |
| `shell` | Zsh 로그인 셸, Oh My Zsh, Dracula, 셸·Vim·tmux 설정 |
| `terminal` | iTerm2·Ghostty 설정(macOS) |
| `nvim` | [Neovim 설정](config/nvim/README.md) |
| `ai` | Claude Code·Codex·OpenCode·Kiro 설정([AI Tools Sync](#ai-tools-sync)) |
| `docker` | Docker Engine·Compose(Ubuntu 서버). `live-restore`가 켜진 경우에만 업그레이드한다. |
| `k3s` | k3s 서버·에이전트. 업그레이드는 채널의 최신 바이너리를 SHA-256으로 검증한 뒤 교체한다. |
| `llm` | DGX Spark 모델 서빙 스택([stacks/dgx-spark](stacks/dgx-spark/README.md)) |
| `monitoring` | DGX Spark의 Grafana Alloy·DCGM Exporter |
| `vibemon` | DGX Spark의 VibeMon 요약 수집기 |

## 머신별 설정

저장소는 공개 저장소다. 호스트 이름, 계정 ID, 토큰처럼 머신을 식별하는 값은 저장소 밖 `~/.config/dotfiles/`에 둔다.

| 파일 | 용도 |
|------|------|
| `~/.config/dotfiles/local.env` | 모듈 설정 변수. `dot`이 실행할 때마다 읽는다. |
| `~/.config/dotfiles/hosts/<name>.env` | `dot @<name>`의 접속 정보 |
| `~/.config/dotfiles/modules` | 켠 add-on(`name`)과 끈 모듈(`-name`). `dot add`/`dot remove`가 관리한다. |
| `~/.config/dotfiles/platform` | `dot platform set`으로 고정한 플랫폼 |

`local.env`에서 쓰는 주요 변수:

| 변수 | 기본값 | 모듈 |
|------|--------|------|
| `DOT_NODE_VERSION` | `24` | node |
| `DOT_PIP_PACKAGES` | `toast-cli` | python |
| `DOT_TIMEZONE`, `DOT_SWAP_SIZE` | `Asia/Seoul`, `4G` | server |
| `DOT_K3S_CHANNEL` | `stable` | k3s. `v1.33`처럼 minor 버전으로 고정할 수 있다. |
| `DOT_K3S_URL`, `DOT_K3S_TOKEN`, `DOT_K3S_EXEC` | 없음 | k3s 첫 설치. URL이 있으면 에이전트로 설치한다. |
| `DOT_SPARK_DIR` | `~/.config/dgx-spark` | llm·monitoring·vibemon |
| `DOT_BREW_MIN_MEMORY_GIB` | `16` | brew(DGX Spark에서 이보다 여유 메모리가 적으면 업그레이드를 미룬다) |
| `VIBEMON_SOURCE_ID`, `VIBEMON_SOURCE_NAME` | 호스트 이름, `DGX Spark` | vibemon |

원격 호스트 파일 예시(`~/.config/dotfiles/hosts/spark.env`):

```bash
DOT_HOST=spark-01.example.ts.net
DOT_USER=me
DOT_IDENTITY=~/.ssh/id_ed25519
```

파일이 없으면 `dot @NAME`의 `NAME`을 SSH 대상(`~/.ssh/config` 별칭 또는 `user@host`)으로 쓴다. 원격 명령은 그 머신의 `~/.dotfiles`(Git `main`)로 실행한다. 원격에 변경을 반영하려면 먼저 `main`에 merge한 뒤 `dot @HOST up`을 실행한다.

## DGX Spark

`dgx-spark` 프로필은 개발 환경만 설치한다. 모델 서빙·모니터링·VibeMon은 add-on이며, 이미 운영 중이면 첫 `dot up`에서 자동으로 이어받는다. 파일이 저장소와 같으면 컨테이너를 다시 만들지 않는다.

```bash
dot add llm            # 모델 서빙 스택 배포 (기본 모드: models)
dot llm mode flash     # Qwen3.8-Flash-Next 단독 서빙으로 전환
dot add monitoring     # Grafana Cloud 토큰을 묻고 Alloy·DCGM Exporter 기동
dot @spark llm status  # 다른 머신에서 상태 확인
```

모드·API·모니터링 상세는 [stacks/dgx-spark/README.md](stacks/dgx-spark/README.md)를 확인한다. Spark에서 Homebrew 업그레이드는 여유 메모리가 `DOT_BREW_MIN_MEMORY_GIB`보다 적으면 미룬다. 모델 서빙과 메모리를 공유하므로, 소스 빌드가 Flash 메모리 감시를 작동시키지 않게 하기 위해서다.

## EC2 (k3s 노드)

`ec2` 프로필은 서버 기본 구성과 셸만 설치한다. k3s는 add-on이다.

```bash
dot add k3s                                    # 서버
DOT_K3S_URL=https://10.0.0.10:6443 DOT_K3S_TOKEN=... dot add k3s   # 에이전트
```

첫 설치는 [k3s 설치 스크립트](https://docs.k3s.io/installation)를 사용한다. 이후 `dot up`은 `DOT_K3S_CHANNEL`의 최신 릴리스를 확인하고, 바이너리만 교체한 뒤 서비스를 재시작한다. 서비스 정의·플래그·노드 역할은 바뀌지 않는다. 클러스터 전체를 순서대로 올리려면 서버 노드부터 실행한다.

## macOS 설정과 인증

[`config/macos/defaults.sh`](config/macos/defaults.sh)는 소리, 키보드, Finder, Dock, 터미널, 화면 잠금 설정을 적용한다. System Settings를 닫지만 Terminal을 종료하지는 않는다. 즉시 반영되지 않는 UI 설정은 로그아웃하거나 재시작하면 적용된다.

- 키를 길게 누르면 악센트 메뉴 대신 문자를 반복한다. 반복 속도는 `KeyRepeat=2`, 시작 지연은 `InitialKeyRepeat=15`다.
- 자동 대문자 변환은 끄고, 스페이스 두 번으로 마침표 추가는 켠다. Finder에는 경로 막대와 상태 막대를 표시한다.
- 부팅음이 이미 꺼져 있으면 해당 `sudo` 인증을 생략한다.
- 화면 잠금이 즉시 잠금이 아니면 macOS 로그인 암호를 터미널에서 입력받는다. 터미널이 없거나 실제 잠금 시간이 바뀌지 않으면 이 단계는 실패한다. 터미널에서 재실행하거나 System Settings > Lock Screen에서 암호 요구 시간을 즉시로 바꾼다.

적용에 성공한 설정 내용은 `~/.local/state/dotfiles/applied/macos-defaults`에 기록한다. 설정 파일이 바뀌거나 적용에 실패하면 다음 실행에서 다시 시도한다.

## Node.js 버전 확인

`node` 모듈은 nvm의 기본 버전을 Node.js 24로 설정한다. Bash와 Zsh는 공통 설정 `~/.config/dotfiles/nvm.sh`를 읽어 nvm이 선택한 실행 파일을 Homebrew의 Node보다 먼저 찾는다. 터미널 시작 시 Node를 설치하거나 다른 버전을 강제로 선택하지 않는다. 프로젝트가 `.nvmrc`를 제공하면 해당 디렉터리에서 `nvm use`로 버전을 선택한다.

```bash
node --version
command -v node
nvm current
```

다른 버전을 선택하지 않았다면 `v24.x.x`와 nvm 디렉터리의 실행 파일이 표시된다. 기존 터미널에서 Homebrew Node가 계속 실행되면 `nvm deactivate` 후 `nvm use default`를 실행한다. 설치 후 실제 버전이 24가 아니면 모듈은 실패로 끝난다.

## Windows (PowerShell)

저장소를 `$HOME\.dotfiles`에 준비하고, `winget`과 심볼릭 링크 생성 권한이 있는 PowerShell에서 실행한다.

```powershell
& "$HOME\.dotfiles\run.ps1"
```

Git 기본 설정과 디렉터리별 신원 프로필, Vim 설정을 링크한다. 기존 대상 파일이 있으면 링크 생성을 건너뛴다. 링크 생성이나 winget 설치가 실패하면 즉시 중단한다. Zsh·macOS 설정·AI 설정은 다루지 않는다. Windows에서 전체 환경을 쓰려면 WSL에서 `run.sh`를 실행한다.

## Repository Layout

| 경로 | 역할 |
|------|------|
| `run.sh` | 부트스트랩. `~/.dotfiles`를 준비하고 `dot up`을 실행한다. |
| `bin/dot` | CLI 진입점 |
| `lib/` | 공통 함수(출력·재시도·파일 교체·상태), 플랫폼 감지, 모듈 실행기, 저장소 갱신, 원격 실행, Spark 스택 동기화 |
| `modules/` | 모듈 하나당 파일 하나. 설치·업그레이드 로직 |
| `profiles/` | 플랫폼별 기본 모듈 목록 |
| `config/` | 배포하는 설정 원본: 셸, Git, SSH/AWS 템플릿, Vim, tmux, macOS, 터미널, Neovim |
| `packages/` | 플랫폼별 Brewfile |
| `stacks/` | DGX Spark Compose 스택과 Grafana 대시보드 |
| `claude/`, `codex/`, `kiro/`, `opencode/` | AI 도구에 배포할 원본과 생성본 |
| `scripts/` | AI 설정 생성·배포 |
| `tests/` | 임시 홈에서 실행하는 회귀 테스트 |
| `run.ps1` | Windows Git/Vim 링크 |

## Key Commands & Aliases

설치 후 새 셸에서 사용하는 주요 명령이다. 전체 정의는 [`config/shell/aliases`](config/shell/aliases)를 확인한다.

| 명령 | 동작 |
|------|------|
| `tt` | `dot up` 실행. `dot`이 없으면 부트스트랩을 내려받아 실행한다. |
| `c <workspace>` | toast-cli로 워크스페이스 이동 |
| `av <profile> <cmd>` | aws-vault 프로필로 실행. 예: `av n kubectl get pods` |
| `nn` / `nnn` / `nb` | lockfile 유지 재설치 / lockfile 삭제 후 의존성 다시 결정 / build |
| `ss` / `sl` / `sk` | 로컬 서버 시작 / 목록 / 종료. `ss`는 지정 포트의 기존 리스너를 먼저 종료 |
| `tf*` | Terraform plan·apply·destroy·state 등의 별칭 |
| `cc` / `ccc` / `ccu` | Claude Code 시작 / 이어가기 / ccusage |
| `cx` / `cxc` | Codex 시작 / 최근 세션 이어가기 |
| `ccp "prompt"` / `cxp "prompt"` | 프롬프트를 전달해 Claude Code / Codex 시작 |

`nn`과 `nnn`은 `node_modules`와 해당 빌드 출력을 지운다. `nnn`은 lockfile도 지우므로 의존성 버전이 달라질 수 있다. `ss`는 `package.json`이 있으면 Node.js 개발 서버를, 없으면 기본 `docs/` 디렉터리의 Python HTTP 서버를 실행한다. Python 서버는 호스트 이름 조회 없이 실제 포트 바인딩 후 성공을 알리며, 시작·종료 신호 실패는 오류로 반환한다.

서버 도우미는 Python 3와 `lsof`가 필요하다. 목록 조회에 실패하면 오류를 반환하고 등록 정보를 보존한다. 등록 정보 갱신은 파일 잠금으로 직렬화하여 여러 터미널에서 동시에 실행해도 다른 포트의 기록을 보존한다.

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
| `codex/config.toml` | `~/.codex/config.toml` | 승인·권한 선택과 지정한 개발 기능 플래그는 원본 우선, 나머지는 없는 키만 추가 |
| `codex/hooks.json` | `~/.codex/hooks.json` | dotfiles 소유 훅만 갱신하고 다른 훅 유지 |
| `codex/rules/default.rules` | `~/.codex/rules/default.rules` | 관리 마커 내부만 갱신하고 로컬 규칙 유지 |
| `claude/`, `kiro/` | `~/.claude/`, `~/.kiro/` | 각 도구의 지침·설정 |

루트 [AGENTS.md](AGENTS.md)는 이 저장소 작업용이며 `CLAUDE.md`는 이를 가리키는 심볼릭 링크다. 모든 프로젝트에 배포할 지침은 [claude/CLAUDE.md](claude/CLAUDE.md)와 언어·Git·보안 규칙을 담은 [claude/rules/](claude/rules/)에서 수정한다. Codex·OpenCode의 `AGENTS.md`는 이 둘을 합쳐 생성한다.

Codex 기본값은 `approval_policy = "never"`, `default_permissions = ":danger-full-access"`다. 로컬 명령의 승인 프롬프트와 샌드박스 제한을 해제한다. 실행 환경의 강제 정책은 이 설정보다 우선한다. [공식 권한 프로필 안내](https://learn.chatgpt.com/docs/permissions)를 참고한다.

Codex와 Claude는 요청 범위에서 문제가 없음을 검증한 릴리즈·배포를 별도 사용자 승인 없이 수행한다. merge·`main` push·자동 merge 예약은 대상 저장소 소유자에 따라 다르다. 내 소유 저장소(내 계정과 `opspresso` 조직)는 merge 가능 상태이고 필수 검사가 통과하면 바로 merge하고, 내 소유가 아닌 저장소는 해당 PR·MR에 대한 사용자의 명시적 허락이 있을 때만 merge한다. 해당 커밋의 필수 검사·CI·리뷰 통과, 미해결 차단 문제·충돌 부재, 대상과 영향을 확인한다. 릴리즈 완료와 대상 환경의 정상 동작을 확인한 뒤 merge된 해당 작업의 로컬·원격 브랜치를 정리하며, 미반영 작업과 다른 worktree는 보존한다. 상세 조건은 [Git Workflow](claude/rules/git-workflow.md)를 따른다. 이 지침은 Git 서버의 브랜치 보호나 필수 환경 승인을 해제하지 않는다.

기술 문서는 ISO 24495-1처럼 쉽게 찾고 이해하고 사용할 수 있게, ASD-STE100처럼 짧고 명확하며 모호하지 않게 작성한다. 필요한 정보·문서 구조·표현·작업과 판단에 사용할 수 있는 설명을 함께 검토한다. 구체적인 점검 항목은 [docs-sync](claude/skills/docs-sync/SKILL.md#작성-품질)에 있다. 이는 자체 작성 규칙이며 표준 전체 준수 선언은 아니다. [ISO 개요](https://www.iso.org/standard/78907.html)와 [IPLF의 네 원칙 설명](https://www.iplfederation.org/iso-standard/), [ASD-STE100 소개](https://www.asd-ste100.org/about_STE.html)를 참고한다.

### 수정과 검증

작업 중인 checkout의 루트에서 실행한다. 공통 지침은 `claude/CLAUDE.md`·`claude/rules/`, 공유 스킬은 `claude/skills/`, 서브에이전트는 `claude/agents/`, deny 규칙은 `claude/settings.json`을 수정한 뒤 Codex·OpenCode 파일을 재생성한다. [스킬 안내](docs/SKILLS.md)에서 역할과 원본 위치를 확인할 수 있다.

```bash
python3 scripts/gen-ai-tools.py
python3 scripts/gen-ai-tools.py --check
python3 -m unittest discover -s tests -p 'test_ai_tools.py'
bash -n run.sh bin/dot
git diff --check
```

`--check`는 생성 파일의 내용과 오래된 잔여 파일을 검사한다. 생성기는 원본이 바뀌어 변환 규칙이 맞지 않으면 파일을 쓰지 않고 오류로 종료한다. 예를 들어 서브에이전트에 지원하지 않는 frontmatter 필드나 `tools` 이름이 있거나, deny 규칙이 `Bash(...)` 형식이 아니거나, `claude/CLAUDE.md`에서 변환 대상 문장(제목, `rules/` 안내, 스킬 호출 문법)이 바뀐 경우다. 테스트는 임시 홈을 사용하며 실제 설정 배포나 원격 push를 하지 않는다. macOS 모듈을 변경했다면 `python3 -m unittest discover -s tests -p 'test_macos.py'`와 `bash -n config/macos/defaults.sh`도 실행한다.

설치기·셸·플랫폼 설정을 함께 변경했다면 `python3 -m unittest discover -s tests -p 'test_*.py'`로 전체 회귀 검사를 실행한다. 서버 검사는 임시 로컬 HTTP 서버도 실행한다. PowerShell이 없는 환경에서는 Windows 검사만 건너뛰며, 실제 OS 설정 적용과 패키지 설치는 별도 검증이 필요하다.

### 배포와 결과 확인

`dot vibe`는 checkout을 갱신하지 않고, 실행한 `dot`이 속한 checkout(기본 `~/.dotfiles`)을 원본으로 읽는다. 먼저 `dot up`이나 `git -C ~/.dotfiles pull`로 원하는 변경을 반영한다.

```bash
dot vibe
cmp ~/.dotfiles/codex/AGENTS.md ~/.codex/AGENTS.md
cmp ~/.dotfiles/claude/CLAUDE.md ~/.claude/CLAUDE.md
diff -qr ~/.dotfiles/codex/skills ~/.agents/skills
cmp ~/.dotfiles/opencode/AGENTS.md ~/.config/opencode/AGENTS.md
diff -qr ~/.dotfiles/opencode/skills ~/.config/opencode/skills
diff -qr ~/.dotfiles/opencode/agents ~/.config/opencode/agents
```

`cmp`는 파일이 같으면 출력 없이 종료한다. 스킬 비교에서는 저장소 파일의 차이를 확인하고, 배포 대상에만 있는 사용자 설치 스킬·백업은 따로 구분한다.

### 기존 설정 보존과 실패 처리

AI 설정은 병합에 읽은 대상 바이트를 재사용해 결과와 직접 비교하고, 변경된 파일을 원자적으로 교체한다. 덮어쓰기·manifest 기반 삭제 전에는 같은 경로의 `.backup`에 직전 내용을 보관하고 권한을 `600`으로 설정한다. manifest는 이전에 배포한 파일 목록이다. 목록에 없는 파일은 삭제하지 않으며, 원본 디렉터리가 없거나 비어 있으면 해당 대상과 목록을 보존한다.

manifest에는 정규화된 상대 경로만 허용한다. `./config.toml`이나 `rules//default.rules`처럼 같은 파일의 다른 표기는 배포 전에 오류로 처리한다.

Codex 원본에 `default_permissions`가 있으면 승인·권한 선택은 저장소 값을 따른다. `approval_policy`, `approvals_reviewer`, `default_permissions`, `sandbox_mode`, `sandbox_workspace_write`를 원본과 맞추고, 원본에 없는 키는 제거한다. 따라서 기존 설치도 동기화 후 같은 승인 정책을 사용하며, 예전 샌드박스 설정이 새 권한 프로필을 가리지 않는다. 변경 후 새 세션에서 권한 모드를 확인한다.

Codex의 `features.chronicle`과 `features.local_thread_store_compression`은 원본에 있으면 저장소 값을 따른다. 두 개발 단계 기능은 기본적으로 `false`이며, 기존 머신의 `true`도 동기화할 때 교체한다. `features.memories`와 `[memories]` 설정, 기존 세션·메모리 데이터는 유지한다. 반영 후 새 Codex 세션에서 F2를 눌러 시작 경고를 확인한다. 이미 열린 세션의 경고는 설정을 다시 읽기 전까지 남을 수 있다. `suppress_unstable_features_warning`으로 경고를 숨기지는 않는다. [공식 기능 플래그 안내](https://learn.chatgpt.com/docs/cli/reference#codex-features)를 참고한다.

Claude `settings.json`의 `permissions.deny`와 `autoMode`도 원본에 있으면 저장소 값으로 교체한다. `autoMode`는 권한 분류기가 읽는 환경·정책 설명이므로 머신에서 생성된 예전 값이 남으면 안 된다. 머신에서 직접 추가한 deny 규칙은 다음 동기화 때 `.backup`에만 남으므로, 유지할 규칙은 `claude/settings.json`에 추가한다. OpenCode `opencode.json`의 `permissions`도 같은 방식으로 저장소 목록으로 교체한다. 셸 연산자(`|`, `&&`)로 이은 명령은 부분 명령별로 검사되므로 deny 규칙은 부분 명령 하나를 기준으로 쓴다.

Claude·Codex·Kiro의 훅은 이벤트 전체가 아니라 실행 스크립트별로 관리한다. dotfiles가 배포하는 `hooks/` 스크립트의 등록만 원본에 맞춰 갱신한다. 같은 이벤트의 VibeMon·romty·사용자 훅과 matcher는 보존한다. 이벤트 배열이 이미 있거나 비어 있어도 머신에 필요한 훅을 추가하며, 재실행해도 중복 등록하지 않는다. 원본에서 제거한 머신 스크립트는 기존 manifest를 기준으로 훅 등록도 정리한다.

Kiro의 `agents/default.json`은 기존 이벤트 객체형 `hooks`와 새 배열형 `hooks`를 모두 지원한다. 배열형에서는 `action.command`로 dotfiles 소유 훅을 식별하며, 사용자 훅과 에이전트형 action을 보존한다. 원본의 빈 `{}`·`[]`는 로컬 훅 형식을 바꾸지 않는다. 원본과 로컬에 훅이 있고 형식이 서로 다르면 자동 변환하지 않고 배포 전에 중단하므로, 두 설정의 형식을 먼저 맞춘다. 형식은 [Kiro 설정 문서](https://kiro.dev/docs/custom-agents/configuration-reference/#hooks-field)를 참고한다.

OpenCode의 `opencode.jsonc`·`cli.json`·`plugins/`는 배포 대상이 아니다. 모델·provider·자격 증명·플러그인과 머신 전용 권한 규칙은 `opencode.jsonc`에서 관리한다. OpenCode는 같은 디렉터리의 `opencode.json`과 `opencode.jsonc`를 모두 읽고 `permissions` 규칙을 이 순서로 이어 붙인다.

VibeMon 전송·사용량 스크립트와 전용 훅, Claude `statusline.py`는 VibeMon 설치기가 관리한다. dotfiles는 이를 복사하거나 삭제하지 않으며, 과거 manifest에 남은 경로는 파일을 보존하고 목록에서만 제외한다. 공유 JSON 설정과 Codex `config.toml`도 원본에서 빠졌다는 이유로 파일 전체를 삭제하지 않는다. Codex의 일반 `tui.status_line` 기본값은 dotfiles에서 관리하고 기존 머신의 선택은 보존한다.

그 외 Codex TOML, Claude `settings.json`, Kiro `agents/default.json` 설정은 기존 값을 우선하고 없는 키만 채운다. 모델·UI·MCP·신뢰 목록, 일반 배열·명시적 `false`·빈 값도 유지하므로 머신별 설정은 다를 수 있다. Codex 명령 승인 규칙은 관리 블록 밖 내용을 보존한다. 원본 `rules/default.rules`를 제거해도 관리 블록만 지우며, 로컬 규칙이 남은 파일은 보존한다.

VibeMon 저장소가 있으면 두 실제 설치기의 실행 순서·재설치·제거를 임시 홈에서 검증할 수 있다. 이 검사는 네트워크나 실제 머신 설정을 사용하지 않는다.

```bash
DOTFILES_VIBEMON_INSTALLER=/path/to/vibemon-app/public/install/install.py \
  python3 tests/test_vibemon_integration.py
```

[`scripts/sync-ai-tools.py`](scripts/sync-ai-tools.py)는 모든 대상의 병합 결과와 상위 디렉터리 구조를 확인한 뒤 배포한다. 원본 하위 디렉터리를 읽지 못하면 삭제된 파일로 취급하지 않고 배포 전에 중단한다. JSON·TOML 오류, 손상된 규칙 마커, 심볼릭 링크 대상, 지원하지 않는 TOML 편집 형태는 오류로 종료한다. 동시 실행은 잠금으로 차단한다.

파일 배포 중 I/O 오류가 나면 일부 파일이 이미 반영되었을 수 있다. 실패한 쓰기는 원본을 보존하며, 모든 파일 배포가 성공해야 대상별 manifest를 갱신한다. 오류를 해결한 뒤 재실행한다. 생성기는 원본에서 삭제된 Markdown을 미러에서 정리하고, 수동 관리하는 `agents/openai.yaml`은 보존한다.

### 지침 로딩

설치기는 Codex 설정을 `~/.codex`에 배포한다. 별도 `CODEX_HOME`이나 `AGENTS.override.md`를 사용하면 실제 로딩 위치를 확인하고 새 세션에서 지침을 확인한다. [공식 지침 로딩 규칙](https://learn.chatgpt.com/docs/agent-configuration/agents-md)을 참고한다.

Codex CLI에서는 `/skills` 또는 `$<name>`으로 스킬을 지정한다. `skills/<name>/...` 참조는 세션에 표시된 해당 스킬 경로를 기준으로 해석한다. [공식 스킬 안내](https://learn.chatgpt.com/docs/build-skills)를 참고한다.

OpenCode V2는 `AGENTS.md`만 지침으로 읽으며 `CLAUDE.md`와 `~/.claude/rules/`는 읽지 않는다. 설정의 `instructions` 항목도 아직 적용하지 않으므로 공통 지침은 `~/.config/opencode/AGENTS.md`로 배포한다. 같은 이름의 스킬은 `.claude/skills` → `.agents/skills` → `~/.config/opencode/skills` → 프로젝트 `.opencode/skills` 순서로 나중 경로가 우선한다. `.claude/skills`와 `.agents/skills`는 전역 경로 다음에 프로젝트 경로를 읽는다. 따라서 OpenCode 전용 생성본이 Claude·Codex 사본을 대체하고, 프로젝트의 `.opencode/skills`는 생성본보다 우선한다. 스킬은 `@<name>`으로 지정한다. Claude.ai에서 동기화한 `~/.claude/skills/synced/` 스킬도 함께 표시되며 dotfiles는 이를 관리하지 않는다.

OpenCode 서브에이전트는 Claude `tools` 목록을 권한 허용 목록으로 바꾼다. 모든 작업을 거부한 뒤 목록의 도구만 허용하고, `.env` 읽기와 프로젝트 밖 경로는 확인을 요청한다. OpenCode는 에이전트 규칙을 전역 `permissions` 뒤에 적용하고 마지막으로 일치한 규칙을 사용한다. 그래서 생성기는 셸을 허용한 서브에이전트에 `claude/settings.json`의 deny 규칙을 다시 넣는다. `opencode.jsonc`에 추가한 머신 전용 셸 규칙은 셸을 허용한 서브에이전트에 적용되지 않으므로, 모든 도구에 적용할 규칙은 `claude/settings.json`에 추가한다. 변환하는 frontmatter는 `name`(파일명과 일치), `description`, `tools`뿐이다. 설정 위치는 `opencode debug paths`의 `config`로, 배포된 서브에이전트는 `opencode debug agents`로 확인한다. [공식 지침](https://opencode.ai/v2/docs/instructions/), [스킬](https://opencode.ai/v2/docs/skills/), [에이전트](https://opencode.ai/v2/docs/agents/) 문서를 참고한다.

## Security

`base` 모듈은 없는 ED25519 SSH 키를 생성하고 SSH 디렉터리를 `700`으로 설정한다. 설치기가 복사하는 SSH·AWS 파일과 백업에는 `600`을 적용한다. Git 설정은 디렉터리별 프로필을 사용하므로 변경 전 `gitconfig*`의 이름·이메일을 확인한다.

1Password CLI를 통한 자격 증명 가져오기는 수동 작업이다. 다음은 이 저장소 소유자의 vault 경로를 사용하는 예시이며, 자신의 항목으로 바꿔 실행한다. 출력 대상은 로컬 평문 파일이고 기존 내용은 덮어쓴다. 먼저 필요한 백업을 준비하고 값을 로그·Git에 남기지 않는다.

```bash
op read op://keys/ssh-config/notesPlain > ~/.ssh/config && chmod 600 ~/.ssh/config
op read op://keys/nalbam-seoul.pem/notesPlain > ~/.ssh/nalbam-seoul.pem && chmod 600 ~/.ssh/nalbam-seoul.pem
op read op://keys/aws-config/notesPlain > ~/.aws/config && chmod 600 ~/.aws/config
op read op://keys/aws-credentials/notesPlain > ~/.aws/credentials && chmod 600 ~/.aws/credentials
```

## Documentation

[문서 인덱스](docs/README.md)에서 설계, 플랫폼별 추가 설정, AI 지침과 스킬로 이동할 수 있다.

## Contributing

별도 브랜치에서 변경하고 관련 검사를 실행한 뒤 PR을 만든다. 커밋은 Conventional Commits 형식을 권장한다. 에이전트는 요청 범위의 commit·push·PR 생성을 자율 수행하며, merge·기본 브랜치 push·자동 merge 예약은 [Git Workflow](claude/rules/git-workflow.md)의 검증 조건과 저장소 소유 조건을, 릴리즈·배포는 요청 범위와 검증 조건을 충족하면 진행하고 완료 후 브랜치를 정리한다.

## License

MIT License
