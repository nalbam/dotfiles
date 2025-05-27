# zshrc

export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="robbyrussell"
ZSH_THEME="dracula"

ZSH_DISABLE_COMPFIX="true"

plugins=(git kube-ps1)

source $ZSH/oh-my-zsh.sh

# User configuration

OS_ARCH="$(uname -m)"

if [ -f ~/.aliases ]; then
  source ~/.aliases
fi

export PATH="$HOME/.local/bin${PATH+:$PATH}"

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

PS1='$(kube_ps1)'$PS1

[[ $commands[kubectl] ]] && source <(kubectl completion zsh)

if [ -d "${BREWPATH}/share/zsh-autosuggestions" ]; then
  source ${BREWPATH}/share/zsh-autosuggestions/zsh-autosuggestions.zsh
fi

if [ -d "${BREWPATH}/share/zsh-syntax-highlighting" ]; then
  source ${BREWPATH}/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
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
  eval "$(pyenv init -)"
fi

# tfenv
export TFENV_AUTO_INSTALL=true
if [[ "${OS_ARCH}" == "arm64" ]]; then
  export TFENV_ARCH=arm64
fi
if [ -d "$HOME/.tfenv" ]; then
  export TFENV_ROOT="$HOME/.tfenv"
  export PATH="$TFENV_ROOT/bin:$PATH"
fi

# nvm
mkdir -p "$HOME/.nvm"
if [ -d "$HOME/.nvm" ]; then
  export NVM_DIR="$HOME/.nvm"
  [ -s "${BREWPATH}/opt/nvm/nvm.sh" ] && \. "${BREWPATH}/opt/nvm/nvm.sh"  # This loads nvm
  [ -s "${BREWPATH}/opt/nvm/etc/bash_completion.d/nvm" ] && \. "${BREWPATH}/opt/nvm/etc/bash_completion.d/nvm"  # This loads nvm bash_completion
fi

# vscode
[[ "$TERM_PROGRAM" == "vscode" ]] && . "$(code --locate-shell-integration-path zsh)"
