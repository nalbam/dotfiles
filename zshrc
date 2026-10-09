# zshrc

# locale: unset or invalid (e.g. Termius sets en_KR.UTF-8) falls back to ASCII and breaks unicode prompts
if [ "$(locale charmap 2>/dev/null)" != "UTF-8" ]; then
  export LANG="en_US.UTF-8"
fi

export ZSH="$HOME/.oh-my-zsh"

export ZSH_THEME="dracula"

export ZSH_DISABLE_COMPFIX="true"

export plugins=(git kube-ps1)

if [ -r "$ZSH/oh-my-zsh.sh" ]; then
  source "$ZSH/oh-my-zsh.sh"
fi

# User configuration

export OS_ARCH="$(uname -m)"

if [ -f ~/.aliases ]; then
  source ~/.aliases
fi

export PATH="$HOME/.local/bin${PATH:+:$PATH}"

if [ -d "/opt/homebrew/bin" ]; then
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
  export BREWPATH="/opt/homebrew"
elif [ -d "/home/linuxbrew/.linuxbrew/bin" ]; then
  export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"
  export BREWPATH="/home/linuxbrew/.linuxbrew"
else
  export BREWPATH="/usr/local"
fi

if [ -d "${BREWPATH}/opt/gnu-getopt/bin" ]; then
  export PATH="${BREWPATH}/opt/gnu-getopt/bin:$PATH"
fi

# export HOMEBREW_REQUIRE_TAP_TRUST=1

if command -v kube_ps1 >/dev/null 2>&1; then
  export PROMPT='$(kube_ps1)'$PROMPT
fi

# kubectl completion
if command -v kubectl >/dev/null 2>&1; then
  if _kubectl_completion="$(kubectl completion zsh 2>/dev/null)" 2>/dev/null; then
    source <(printf '%s\n' "$_kubectl_completion")
  fi
  unset _kubectl_completion
fi

# zsh-autosuggestions
if [ -r "${BREWPATH}/share/zsh-autosuggestions/zsh-autosuggestions.zsh" ]; then
  source "${BREWPATH}/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
fi

# zsh-syntax-highlighting
if [ -r "${BREWPATH}/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]; then
  source "${BREWPATH}/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
fi

# bun
if [ -d "$HOME/.bun" ]; then
  export BUN_INSTALL="$HOME/.bun"
  export PATH="$BUN_INSTALL/bin:$PATH"
fi

# gopath
if [ -d "$HOME/go" ]; then
  export GOPATH="$HOME/go"
  export PATH="$GOPATH/bin:$PATH"
fi

# pyenv
if [ -d "$HOME/.pyenv" ]; then
  export PYENV_ROOT="$HOME/.pyenv"
  [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
  if command -v pyenv >/dev/null 2>&1; then
    eval "$(pyenv init -)"
  fi
fi

# tfenv
export TFENV_AUTO_INSTALL=true
if [[ "${OS_ARCH}" == "arm64" ]]; then
  export TFENV_ARCH="arm64"
fi
if [ -d "$HOME/.tfenv" ]; then
  export TFENV_ROOT="$HOME/.tfenv"
  export PATH="$TFENV_ROOT/bin:$PATH"
fi

# nvm
if [ -d "$HOME/.nvm" ]; then
  export NVM_DIR="$HOME/.nvm"
  [ -s "${BREWPATH}/opt/nvm/nvm.sh" ] && \. "${BREWPATH}/opt/nvm/nvm.sh"  # This loads nvm
  [ -s "${BREWPATH}/opt/nvm/etc/bash_completion.d/nvm" ] && \. "${BREWPATH}/opt/nvm/etc/bash_completion.d/nvm"  # This loads nvm bash_completion
fi

# Optional editor shell integration.
case "$TERM_PROGRAM" in
  vscode) _editor_cli=code ;;
  kiro) _editor_cli=kiro ;;
  *) _editor_cli= ;;
esac
if [ -n "$_editor_cli" ] && command -v "$_editor_cli" >/dev/null 2>&1; then
  if _editor_integration=$("$_editor_cli" --locate-shell-integration-path zsh) && [ -r "$_editor_integration" ]; then
    . "$_editor_integration"
  fi
fi
unset _editor_cli _editor_integration
